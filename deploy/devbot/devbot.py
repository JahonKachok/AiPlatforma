#!/usr/bin/env python3
"""AiPlatforma devbot — Telegram orqali platforma kodini o'zgartirish.

Serverda (Docker'dan tashqarida) systemd xizmati sifatida ishlaydi.

  * Sozlamalar (bot tokeni, username, Claude kaliti, model) platformaning
    "Integratsiyalar" sahifasidan olinadi:
    `docker exec <web> python manage.py devbot_config`. Buyruqni faqat
    Telegram'i ulangan faol adminlar bera oladi.
  * Har vazifa alohida git klonda (`bot/<sana>` branch) bajariladi.
    Claude Code izolyatsiyalangan runner konteynerida ishlaydi: shell bor
    (testlar, makemigrations, tailwind), lekin .env, baza, docker socket va
    ishlab turgan papka yo'q.
  * Jarayon Telegram'da jonli ko'rinadi (⏹ to'xtatish mumkin), rasm
    yuborish mumkin, javob yozsangiz Claude o'sha sessiyada davom etadi.
  * 🚀 Deploy bosilgandagina o'zgarish ishlab turgan papkaga fast-forward
    qilinadi va `docker compose up -d --build` bajariladi; web sog'lom
    bo'lmasa — avtomatik orqaga qaytariladi.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

VERSION = "2"


def _env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"{name} muhit o'zgaruvchisi berilmagan")
    return value


PROD_DIR = Path(_env("DEVBOT_PROD_DIR", required=True)).resolve()
STATE_DIR = Path(_env("DEVBOT_STATE_DIR", str(Path.home() / ".aiplatforma-devbot")))
WORK_DIR = Path(_env("DEVBOT_WORK_DIR", str(STATE_DIR / "work")))
CLAUDE_HOME = STATE_DIR / "claude-home"  # Claude sessiyalari va xotirasi
STATE_FILE = STATE_DIR / "state.json"
RUNNER_DIR = Path(_env("DEVBOT_RUNNER_DIR", str(Path(__file__).resolve().parent)))
RUNNER_IMAGE = _env("DEVBOT_RUNNER_IMAGE", "aiplatforma-devbot-runner")
RUNNER_MEMORY = _env("DEVBOT_RUNNER_MEMORY", "1g")
RUNNER_CPUS = _env("DEVBOT_RUNNER_CPUS", "1.5")
MAIN_BRANCH = _env("DEVBOT_MAIN_BRANCH", "main")
BASE = f"origin/{MAIN_BRANCH}"  # ishchi klonda: ishlab turgan main
WEB_CONTAINER = _env("DEVBOT_WEB_CONTAINER", "aiplatforma_web")
MAX_TURNS = int(_env("DEVBOT_MAX_TURNS", "120"))
CLAUDE_TIMEOUT = int(_env("DEVBOT_CLAUDE_TIMEOUT", "2700"))
HEALTH_TIMEOUT = int(_env("DEVBOT_HEALTH_TIMEOUT", "300"))
BUILD_TIMEOUT = int(_env("DEVBOT_BUILD_TIMEOUT", "1800"))
RUN_TESTS = _env("DEVBOT_RUN_TESTS", "1") == "1"
PUSH_TO_ORIGIN = _env("DEVBOT_PUSH_TO_ORIGIN", "0") == "1"
CONFIG_POLL = 30
# Ixtiyoriy zaxira (panel ishlamay qolsa): .env dagi qiymatlar.
ENV_FALLBACK = {
    "telegram_token": _env("DEVBOT_TELEGRAM_TOKEN", ""),
    "anthropic_api_key": _env("ANTHROPIC_API_KEY", ""),
    "claude_model": _env("DEVBOT_CLAUDE_MODEL", ""),
}
EXTRA_USER_IDS = {int(x) for x in re.split(r"[,\s]+", _env("DEVBOT_ALLOWED_USER_IDS", "")) if x}

SYSTEM_PROMPT = """\
Siz AiPlatforma loyihasida ishlayapsiz. Vazifa Telegram orqali admindan
keldi. Siz izolyatsiyalangan konteynerdasiz: /work — loyihaning git klonidagi
alohida branch. Bu yerda .env, haqiqiy baza va ishlab turgan server YO'Q;
o'zgarishlaringiz admin "Deploy" tugmasini bosgandagina saytga chiqadi.

Imkoniyatlar: Bash bor. Testlar: `python manage.py test apps.<app>` (SQLite,
SECRET_KEY va sozlamalar tayyor). Migratsiya: `python manage.py makemigrations`.
Tarjima: locale/uz va locale/ru .po fayllari (`python manage.py compilemessages`
bilan tekshirish mumkin). CSS: shablonlarga yangi Tailwind klass qo'shsangiz
`tailwindcss -i static/css/src/input.css -o static/css/tailwind.css --minify`.

Qoidalar:
- Vazifa noaniq bo'lsa va taxmin xavfli bo'lsa — kodni o'zgartirmasdan
  savolingizni yozib to'xtang; admin javob beradi va siz shu sessiyada
  davom etasiz. Kichik noaniqliklarda oqilona qaror qilib, hisobotda ayting.
- Faqat vazifaga tegishli fayllarni o'zgartiring.
- docker-compose.yml, Dockerfile, deploy/, nginx/, xavfsizlik sozlamalarini
  faqat aniq so'ralganda o'zgartiring. Maxfiy kalit/parol yozmang.
- git commit/push, docker buyruqlarini ishlatmang — buni bot qiladi.
- Ish oxirida o'zgargan qismga tegishli testlarni ishga tushiring.
- Rasm ilova qilingan bo'lsa, uni Read tool bilan oching.

Oxirida o'zbek tilida qisqa hisobot: nima o'zgardi, qaysi fayllar, testlar
natijasi, deploydan keyin nimani qo'lda tekshirish kerak."""

log = logging.getLogger("devbot")
BUSY = asyncio.Lock()
CFG = {"telegram_token": "", "anthropic_api_key": "", "claude_model": "", "admin_ids": [],
       "telegram_username": ""}
RUNTIME = {"task": "", "container": None, "stopped": False, "restart": False, "username": ""}


# --------------------------------------------------------------------------
# Yordamchilar
# --------------------------------------------------------------------------

class CmdError(RuntimeError):
    pass


def child_env(extra=None):
    """Bola jarayonlar uchun muhit: DEVBOT_* va kalitlar uzatilmaydi."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("DEVBOT_") and k != "ANTHROPIC_API_KEY"}
    env.update(extra or {})
    return env


async def run(cmd, cwd=None, timeout=600, merge=True, env=None):
    proc = await asyncio.create_subprocess_exec(
        *map(str, cmd),
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT if merge else asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
        env=env or child_env(),
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, f"Vaqt tugadi ({timeout} s)", ""
    return proc.returncode, out.decode(errors="replace"), (err or b"").decode(errors="replace")


async def git(*args, cwd=None, check=True):
    rc, out, _ = await run(["git", "-c", "safe.directory=*", *args], cwd=cwd or WORK_DIR, timeout=300)
    if check and rc != 0:
        raise CmdError(f"git {' '.join(args)}:\n{out.strip()}")
    return out.strip()


def tail(text, limit=3000):
    text = (text or "").strip()
    return text if len(text) <= limit else "…\n" + text[-limit:]


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"pending": None, "deploys": []}


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_FILE)


def allowed(update: Update) -> bool:
    user, chat = update.effective_user, update.effective_chat
    if not (user and chat and chat.type == "private"):
        return False
    return user.id in set(CFG.get("admin_ids") or []) | EXTRA_USER_IDS


async def say(app, chat_id, text, **kw):
    """parse_mode ataylab yo'q — diff/log belgilari formatlashni buzmasin."""
    for i in range(0, max(len(text), 1), 4000):
        last = i + 4000 >= len(text)
        await app.bot.send_message(chat_id, text[i:i + 4000] or "—", **(kw if last else {}))


# --------------------------------------------------------------------------
# Platformadan sozlamalar
# --------------------------------------------------------------------------

def fetch_config(heartbeat=None):
    """Platformadan sozlamalarni oladi (sinxron; web ishlamasa — None)."""
    cmd = ["docker", "exec", WEB_CONTAINER, "python", "manage.py", "devbot_config"]
    if heartbeat is not None:
        cmd += ["--heartbeat", json.dumps(heartbeat)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=child_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("devbot_config: %s", exc)
        return None
    if res.returncode != 0:
        log.warning("devbot_config xato: %s", tail(res.stderr or res.stdout, 500))
        return None
    try:
        data = json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        log.warning("devbot_config JSON emas: %s", tail(res.stdout, 300))
        return None
    for key, value in ENV_FALLBACK.items():
        data[key] = data.get(key) or value
    return data


def heartbeat_payload():
    return {"busy": BUSY.locked(), "task": RUNTIME["task"][:200], "version": VERSION,
            "username": RUNTIME["username"]}


async def config_watcher(app):
    while True:
        await asyncio.sleep(CONFIG_POLL)
        data = await asyncio.to_thread(fetch_config, heartbeat_payload())
        if not data:
            continue
        new_token = data.get("telegram_token")
        CFG.update(data)
        if new_token and new_token != app.bot.token and not BUSY.locked():
            log.info("Bot tokeni panelda o'zgardi — qayta ishga tushirilmoqda")
            RUNTIME["restart"] = True
            app.stop_running()
            return


# --------------------------------------------------------------------------
# Ishchi klon va runner konteyner
# --------------------------------------------------------------------------

async def ensure_workdir():
    if (WORK_DIR / ".git").is_file():  # eski versiyadagi worktree
        await git("worktree", "remove", "--force", str(WORK_DIR), cwd=PROD_DIR, check=False)
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    if not (WORK_DIR / ".git").is_dir():
        WORK_DIR.parent.mkdir(parents=True, exist_ok=True)
        await git("clone", "-q", str(PROD_DIR), str(WORK_DIR), cwd=WORK_DIR.parent)
        (WORK_DIR / ".git" / "info").mkdir(exist_ok=True)
        (WORK_DIR / ".git" / "info" / "exclude").write_text(".devbot/\n")
    await git("fetch", "-q", "origin")


async def ensure_runner(app, chat_id):
    """Runner image'ini web image'i asosida quradi (web yangilansa — qayta)."""
    rc, base_name, _ = await run(["docker", "inspect", "-f", "{{.Config.Image}}", WEB_CONTAINER])
    rc2, base_id, _ = await run(["docker", "inspect", "-f", "{{.Image}}", WEB_CONTAINER])
    if rc or rc2:
        raise CmdError(f"{WEB_CONTAINER} konteyneri topilmadi — platforma ishlayaptimi?")
    base_name, base_id = base_name.strip(), base_id.strip()
    _, current, _ = await run(["docker", "image", "inspect", "-f",
                               '{{index .Config.Labels "devbot.base"}}', RUNNER_IMAGE])
    if current.strip() == base_id:
        return
    await say(app, chat_id, "🔧 Runner konteyneri tayyorlanmoqda (bir marta, ~2 daqiqa)…")
    rc, out, _ = await run([
        "docker", "build", "-q", "-t", RUNNER_IMAGE,
        "--build-arg", f"BASE_IMAGE={base_name}", "--label", f"devbot.base={base_id}",
        "-f", RUNNER_DIR / "Dockerfile.runner", RUNNER_DIR,
    ], timeout=BUILD_TIMEOUT)
    if rc != 0:
        raise CmdError(f"Runner image qurilmadi:\n{tail(out, 1500)}")


def runner_user():
    """Konteyner ichidagi foydalanuvchi. Devbot root bo'lsa — 1000 (Claude
    Code root ostida --dangerously-skip-permissions'ni rad etadi), fayllar
    shu foydalanuvchiga beriladi."""
    CLAUDE_HOME.mkdir(parents=True, exist_ok=True)
    if os.getuid() != 0:
        return f"{os.getuid()}:{os.getgid()}"
    subprocess.run(["chown", "-R", "1000:1000", str(WORK_DIR), str(CLAUDE_HOME)], check=False)
    return "1000:1000"


def runner_cmd(name, *cmd, network=True, extra_env=()):
    args = [
        "docker", "run", "--rm", "--name", name,
        "-u", runner_user(),
        "--memory", RUNNER_MEMORY, "--cpus", RUNNER_CPUS, "--pids-limit", "512",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "-v", f"{WORK_DIR}:/work", "-v", f"{CLAUDE_HOME}:/home/runner", "-w", "/work",
    ]
    if not network:
        args += ["--network", "none"]
    for key in extra_env:
        args += ["-e", key]  # qiymat docker mijozining muhitidan olinadi
    return args + [RUNNER_IMAGE, *cmd]


async def runner(*cmd, timeout=900, network=False):
    name = f"devbot-{int(time.time() * 1000)}"
    rc, out, _ = await run(runner_cmd(name, *cmd, network=network), timeout=timeout)
    if rc == 124:
        await run(["docker", "kill", name])
    return rc, out


# --------------------------------------------------------------------------
# Claude: jonli jarayon
# --------------------------------------------------------------------------

def _short(path):
    return str(path or "").removeprefix("/work/")


def describe_tool(name, inp):
    inp = inp or {}
    if name == "Read":
        return f"📖 {_short(inp.get('file_path'))}"
    if name in ("Edit", "MultiEdit"):
        return f"✏️ {_short(inp.get('file_path'))}"
    if name == "Write":
        return f"📝 {_short(inp.get('file_path'))}"
    if name == "Bash":
        return f"💻 {(inp.get('description') or inp.get('command') or '')[:90]}"
    if name in ("Grep", "Glob"):
        return f"🔎 {(inp.get('pattern') or '')[:60]}"
    if name in ("WebSearch", "WebFetch"):
        return f"🌐 {(inp.get('query') or inp.get('url') or '')[:80]}"
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate"):
        return "📋 reja yangilandi"
    if name in ("Task", "Agent"):
        return f"🤖 {(inp.get('description') or '')[:60]}"
    return f"🔧 {name}"


class Progress:
    """Bitta Telegram xabarini jarayon bilan yangilab turadi."""

    def __init__(self, app, chat_id):
        self.app, self.chat_id = app, chat_id
        self.steps, self.msg, self.started = [], None, time.monotonic()
        self.last_edit, self.dirty = 0.0, False
        self.markup = InlineKeyboardMarkup([[InlineKeyboardButton("⏹ To'xtatish", callback_data="stop")]])

    def text(self, done=False):
        m, s = divmod(int(time.monotonic() - self.started), 60)
        head = f"{'✔️ Tugadi' if done else '⏳ Claude ishlayapti'} ({m}:{s:02d})"
        return head + "\n\n" + ("\n".join(self.steps[-15:]) or "…")

    async def start(self):
        self.msg = await self.app.bot.send_message(self.chat_id, self.text(), reply_markup=self.markup)

    def add(self, line):
        self.steps.append(line)
        self.dirty = True

    async def flush(self, force=False, done=False):
        if not self.msg or not (self.dirty or done):
            return
        if not force and time.monotonic() - self.last_edit < 4:
            return
        self.dirty, self.last_edit = False, time.monotonic()
        try:
            await self.msg.edit_text(self.text(done), reply_markup=None if done else self.markup)
        except BadRequest as exc:  # "message is not modified" va h.k.
            log.debug("progress edit: %s", exc)


async def run_claude(app, chat_id, prompt, session_id=None):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--dangerously-skip-permissions", "--max-turns", str(MAX_TURNS),
           "--append-system-prompt", SYSTEM_PROMPT]
    if CFG.get("claude_model"):
        cmd += ["--model", CFG["claude_model"]]
    if session_id:
        cmd += ["--resume", session_id]
    if not CFG.get("anthropic_api_key"):
        raise CmdError("Claude API kaliti yo'q — platformadagi Integratsiyalar sahifasida kiriting.")

    name = f"devbot-claude-{int(time.time())}"
    RUNTIME.update(container=name, stopped=False)
    progress = Progress(app, chat_id)
    await progress.start()
    result = {"ok": False, "text": "", "session_id": session_id, "cost": 0}

    proc = await asyncio.create_subprocess_exec(
        *runner_cmd(name, *cmd, network=True, extra_env=("ANTHROPIC_API_KEY",)),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL, limit=32 * 1024 * 1024,
        env=child_env({"ANTHROPIC_API_KEY": CFG["anthropic_api_key"]}),
    )

    stderr_task = asyncio.create_task(proc.stderr.read())

    async def read_events():
        while line := await proc.stdout.readline():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "system" and ev.get("session_id"):
                result["session_id"] = ev["session_id"]
            elif kind == "assistant":
                for item in (ev.get("message") or {}).get("content") or []:
                    if item.get("type") == "tool_use":
                        progress.add(describe_tool(item.get("name"), item.get("input")))
                    elif item.get("type") == "text" and item.get("text", "").strip():
                        progress.add("💬 " + item["text"].strip().splitlines()[0][:150])
            elif kind == "result":
                result.update(
                    ok=not ev.get("is_error"),
                    text=ev.get("result") or ev.get("subtype") or "",
                    session_id=ev.get("session_id") or result["session_id"],
                    cost=ev.get("total_cost_usd") or 0,
                )
            await progress.flush()

    try:
        await asyncio.wait_for(read_events(), CLAUDE_TIMEOUT)
    except asyncio.TimeoutError:
        progress.add(f"⌛ Vaqt tugadi ({CLAUDE_TIMEOUT // 60} daqiqa)")
        await run(["docker", "kill", name])
    stderr = (await stderr_task).decode(errors="replace")
    await proc.wait()
    RUNTIME["container"] = None
    await progress.flush(force=True, done=True)

    if RUNTIME["stopped"]:
        result.update(ok=False, text="⏹ Siz to'xtatdingiz. Shu paytgacha qilingan o'zgarishlar saqlandi.")
    elif not result["text"] and proc.returncode:
        raise CmdError(f"Claude ishlamadi (kod {proc.returncode}):\n{tail(stderr, 1500)}")
    return result


# --------------------------------------------------------------------------
# Vazifani bajarish
# --------------------------------------------------------------------------

async def commit_if_changed(message):
    await git("add", "-A")
    rc, _, _ = await run(["git", "-c", "safe.directory=*", "diff", "--cached", "--quiet"], cwd=WORK_DIR)
    if rc == 0:
        return False
    await git("-c", "user.name=AiPlatforma devbot", "-c", "user.email=devbot@localhost",
              "commit", "-q", "-m", message)
    return True


async def ahead_count():
    return int(await git("rev-list", "--count", f"{BASE}..HEAD"))


async def process(app, chat_id, prompt, pending):
    await ensure_runner(app, chat_id)
    RUNTIME["task"] = pending["task"]
    res = await run_claude(app, chat_id, prompt, pending.get("session_id"))
    pending["session_id"] = res["session_id"]
    pending["cost"] = (pending.get("cost") or 0) + (res["cost"] or 0)

    title = pending["task"].strip().splitlines()[0][:70]
    await commit_if_changed(f"devbot: {title}")

    notes = []
    if await ahead_count():
        changed = await git("diff", "--name-only", f"{BASE}...HEAD")
        if re.search(r"^(templates/|static/css/src/|apps/.*\.(html|py)$)", changed, re.M):
            rc, out = await runner("tailwindcss", "-i", "static/css/src/input.css",
                                   "-o", "static/css/tailwind.css", "--minify")
            if rc == 0 and await commit_if_changed(f"devbot: tailwind.css ({title})"):
                notes.append("🎨 tailwind.css qayta qurildi.")
            elif rc != 0:
                notes.append(f"⚠️ Tailwind xatosi:\n{tail(out, 500)}")
        if RUN_TESTS:
            rc, out = await runner("python", "manage.py", "makemigrations", "--noinput")
            if rc == 0 and await commit_if_changed(f"devbot: migratsiyalar ({title})"):
                notes.append("🗂 Yetishmagan migratsiya yaratildi.")
            elif rc != 0:
                notes.append(f"⚠️ makemigrations xatosi:\n{tail(out, 800)}")
            await say(app, chat_id, "🧪 Yakuniy tekshiruv: barcha testlar…")
            rc, out = await runner("python", "manage.py", "test", "--noinput", timeout=1800)
            pending["tests_ok"] = rc == 0
            notes.append("✅ Barcha testlar o'tdi." if rc == 0 else f"❌ Testlar yiqildi:\n{tail(out, 1500)}")

    RUNTIME["task"] = ""
    save_state({**load_state(), "pending": pending})
    await report(app, chat_id, pending, res, notes)


async def report(app, chat_id, pending, res, notes):
    ahead = await ahead_count()
    stat = await git("diff", "--stat", f"{BASE}...HEAD") if ahead else ""
    cost = f"\n💵 Jami sarf: ${pending['cost']:.2f}" if pending.get("cost") else ""
    head = "🤖 Claude:" if res["ok"] else "⚠️ Claude:"
    text = f"{head}\n{tail(res['text'], 2500)}\n\n📂 {pending['branch']}\n"
    text += (stat or "Kodda o'zgarish yo'q.") + cost
    if notes:
        text += "\n\n" + "\n\n".join(notes)
    text += "\n\nDavom ettirish yoki javob berish uchun shunchaki yozing (rasm ham mumkin)."

    buttons = []
    if ahead:
        buttons.append([InlineKeyboardButton("🚀 Deploy", callback_data="deploy"),
                        InlineKeyboardButton("📄 Diff", callback_data="diff")])
    buttons.append([InlineKeyboardButton("🗑 Bekor qilish", callback_data="cancel")])
    await say(app, chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))


def clear_uploads():
    shutil.rmtree(WORK_DIR / ".devbot", ignore_errors=True)


async def new_task(app, chat_id, text):
    state = load_state()
    old = state.get("pending")
    await ensure_workdir()
    await git("reset", "--hard", "-q")
    await git("clean", "-fdq")
    branch = f"bot/{time.strftime('%Y%m%d-%H%M%S')}"
    await git("checkout", "-q", "-B", branch, BASE)
    if old and old["branch"] != branch:
        await git("branch", "-D", old["branch"], check=False)
    pending = {"branch": branch, "task": text, "session_id": None, "cost": 0}
    save_state({**state, "pending": pending})
    await process(app, chat_id, text, pending)


async def refine(app, chat_id, text):
    pending = load_state()["pending"]
    await ensure_workdir()
    await git("checkout", "-q", pending["branch"])
    pending["task"] += "\n+ " + text
    await process(app, chat_id, text, pending)


# --------------------------------------------------------------------------
# Deploy va rollback
# --------------------------------------------------------------------------

async def wait_healthy():
    deadline, status = time.monotonic() + HEALTH_TIMEOUT, ""
    while time.monotonic() < deadline:
        _, status, _ = await run(["docker", "inspect", "-f", "{{.State.Health.Status}}", WEB_CONTAINER])
        status = status.strip()
        if status in ("healthy", "unhealthy"):
            return status == "healthy", status
        await asyncio.sleep(5)
    return False, status or "vaqt tugadi"


async def rebuild(app, chat_id):
    await say(app, chat_id, "🔨 docker compose up -d --build …")
    rc, out, _ = await run(["docker", "compose", "up", "-d", "--build"], cwd=PROD_DIR, timeout=BUILD_TIMEOUT)
    if rc != 0:
        return False, tail(out, 1500)
    ok, status = await wait_healthy()
    return ok, f"web holati: {status}"


async def prod_ready():
    branch = await git("rev-parse", "--abbrev-ref", "HEAD", cwd=PROD_DIR)
    if branch != MAIN_BRANCH:
        raise CmdError(f"Ishlab turgan papka '{branch}' branch'da, '{MAIN_BRANCH}' kerak.")
    dirty = await git("status", "--porcelain", "--untracked-files=no", cwd=PROD_DIR)
    if dirty:
        raise CmdError(f"Ishlab turgan papkada commit qilinmagan o'zgarishlar bor:\n{dirty}")


async def deploy(app, chat_id):
    state = load_state()
    pending = state.get("pending")
    if not pending:
        return await say(app, chat_id, "Deploy qilinadigan o'zgarish yo'q.")
    await prod_ready()
    prev = await git("rev-parse", "HEAD", cwd=PROD_DIR)
    await git("fetch", "-q", str(WORK_DIR), pending["branch"], cwd=PROD_DIR)
    rc, out, _ = await run(["git", "-c", "safe.directory=*", "merge", "--ff-only", "FETCH_HEAD"], cwd=PROD_DIR)
    if rc != 0:
        return await say(app, chat_id,
                         f"❌ {MAIN_BRANCH} bu orada o'zgargan, fast-forward bo'lmadi.\n"
                         f"/new bilan vazifani qaytadan bering.\n{tail(out, 800)}")
    new = await git("rev-parse", "HEAD", cwd=PROD_DIR)

    RUNTIME["task"] = "deploy: " + pending["task"]
    ok, info = await rebuild(app, chat_id)
    RUNTIME["task"] = ""
    if not ok:
        await say(app, chat_id, f"❌ Deploy muvaffaqiyatsiz ({info}). Orqaga qaytarilmoqda…")
        await git("reset", "--hard", prev, cwd=PROD_DIR)
        ok2, info2 = await rebuild(app, chat_id)
        return await say(app, chat_id,
                         ("↩️ Oldingi versiya tiklandi. " if ok2 else "🆘 Tiklash ham ishlamadi! ")
                         + info2 + "\nBranch saqlanib qoldi — tuzatishni yozishingiz mumkin.")

    state["deploys"] = (state.get("deploys") or [])[-19:] + [{
        "from": prev, "to": new, "branch": pending["branch"],
        "task": pending["task"][:200], "time": time.strftime("%Y-%m-%d %H:%M"),
    }]
    state["pending"] = None
    save_state(state)
    clear_uploads()

    msg = f"✅ Deploy qilindi: {new[:8]}\n{info}"
    if PUSH_TO_ORIGIN:
        rc, out, _ = await run(["git", "-c", "safe.directory=*", "push", "origin", MAIN_BRANCH],
                               cwd=PROD_DIR, timeout=120)
        msg += "\n⬆️ GitHub'ga push qilindi." if rc == 0 else f"\n⚠️ Push xatosi:\n{tail(out, 500)}"
    await say(app, chat_id, msg + "\n\nMuammo bo'lsa: /rollback")


async def rollback(app, chat_id):
    state = load_state()
    deploys = state.get("deploys") or []
    if not deploys:
        return await say(app, chat_id, "Orqaga qaytariladigan deploy yo'q.")
    last = deploys[-1]
    await prod_ready()
    head = await git("rev-parse", "HEAD", cwd=PROD_DIR)
    if head != last["to"]:
        return await say(app, chat_id,
                         f"Ishlab turgan versiya ({head[:8]}) oxirgi bot deployi ({last['to'][:8]}) emas — "
                         "kod qo'lda o'zgargan. Rollback'ni serverda qo'lda qiling.")
    await git("reset", "--hard", last["from"], cwd=PROD_DIR)
    ok, info = await rebuild(app, chat_id)
    deploys.pop()
    save_state(state)
    await say(app, chat_id,
              (f"↩️ {last['from'][:8]} versiyasiga qaytildi. " if ok else "🆘 Rollback'dan keyin web sog'lom emas! ")
              + info + "\n⚠️ Baza migratsiyalari avtomatik qaytarilmaydi.")


async def cancel_pending(app, chat_id):
    state = load_state()
    pending = state.get("pending")
    if not pending:
        return await say(app, chat_id, "Bekor qilinadigan narsa yo'q.")
    await ensure_workdir()
    await git("reset", "--hard", "-q")
    await git("checkout", "-q", "--detach", BASE)
    await git("branch", "-D", pending["branch"], check=False)
    clear_uploads()
    state["pending"] = None
    save_state(state)
    await say(app, chat_id, f"🗑 {pending['branch']} bekor qilindi.")


async def send_diff(app, chat_id):
    pending = load_state().get("pending")
    if not pending:
        return await say(app, chat_id, "Kutilayotgan o'zgarish yo'q.")
    _, diff, _ = await run(["git", "-c", "safe.directory=*", "diff", f"{BASE}...{pending['branch']}"], cwd=WORK_DIR)
    await app.bot.send_document(
        chat_id, InputFile(diff.encode(), filename=f"{pending['branch'].replace('/', '-')}.diff"))


# --------------------------------------------------------------------------
# Telegram handlerlari
# --------------------------------------------------------------------------

def background(context, chat_id, coro_factory):
    """Uzoq ishni fonda bajaradi; bir vaqtda faqat bitta ish."""
    app = context.application

    async def job():
        if BUSY.locked():
            return await say(app, chat_id, "⏳ Hozir boshqa ish bajarilyapti (/status, ⏹ To'xtatish).")
        async with BUSY:
            try:
                await coro_factory(app)
            except CmdError as exc:
                await say(app, chat_id, f"❌ {exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("devbot job failed")
                await say(app, chat_id, f"❌ Kutilmagan xato: {exc!r}")
            finally:
                RUNTIME["task"] = ""

    app.create_task(job())


def start_or_refine(context, chat_id, text, attach=None):
    async def go(app):
        await ensure_workdir()
        # Rasm .devbot/ ga (git e'tiborsiz qoldiradi) saqlanadi — reset,
        # clean va checkout unga tegmaydi.
        prompt = f"{text}\n\n{await attach()}" if attach else text
        if load_state().get("pending"):
            await refine(app, chat_id, prompt)
        else:
            await new_task(app, chat_id, prompt)

    background(context, chat_id, go)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    start_or_refine(context, update.effective_chat.id, update.message.text.strip())


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    msg = update.message
    file_obj = msg.photo[-1] if msg.photo else msg.document

    async def attach():
        uploads = WORK_DIR / ".devbot" / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        suffix = Path(getattr(file_obj, "file_name", None) or "rasm.jpg").suffix or ".jpg"
        path = uploads / f"{int(time.time())}{suffix}"
        tg_file = await file_obj.get_file()
        await tg_file.download_to_drive(path)
        return f"[Ilova qilingan rasm: /work/.devbot/uploads/{path.name} — Read tool bilan oching]"

    text = (msg.caption or "").strip() or "Ilova qilingan rasmga qarang va kerakli o'zgarishni qiling."
    start_or_refine(context, update.effective_chat.id, text, attach=attach)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        return await update.message.reply_text("Foydalanish: /new <vazifa matni>")
    chat_id = update.effective_chat.id
    background(context, chat_id, lambda app: new_task(app, chat_id, text))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        user = update.effective_user
        if user and update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text(
                "Bu bot faqat platforma adminlari uchun. Telegram'ni platformadagi profilingizga ulang "
                f"(sizning ID: {user.id}).")
        return
    await update.message.reply_text(
        "AiPlatforma devbot.\n\n"
        "Vazifani matn (yoki izohli rasm) bilan yozing — Claude kodni o'zgartiradi, testlarni "
        "o'tkazadi va natijani yuboradi. 🚀 Deploy bosilmaguncha saytga hech narsa tegmaydi.\n\n"
        "Kutilayotgan o'zgarish bo'lsa, yangi xabar uni davom ettiradi (Claude savol bersa — "
        "shunchaki javob yozing).\n\n"
        "/new <matn> — yangi vazifa (kutilayotganini bekor qilib)\n"
        "/stop — ishlayotgan Claude'ni to'xtatish\n"
        "/status — holat\n/log — oxirgi commitlar\n"
        "/rollback — oxirgi bot deployini qaytarish\n/cancel — kutilayotganini bekor qilish"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    state = load_state()
    head = await git("log", "-1", "--format=%h %s (%cr)", cwd=PROD_DIR)
    lines = [f"🟢 Ishlab turgan: {head}",
             f"⏳ Ishlayapti: {RUNTIME['task'][:200]}" if BUSY.locked() else "💤 Bo'sh"]
    if p := state.get("pending"):
        lines.append(f"📝 Kutilmoqda: {p['branch']}\n{p['task'][:300]}")
    for d in (state.get("deploys") or [])[-3:]:
        lines.append(f"🚀 {d['time']} {d['to'][:8]} — {d['task'][:80]}")
    await update.message.reply_text("\n\n".join(lines))


async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text(await git("log", "--oneline", "-15", cwd=PROD_DIR) or "—")


async def stop_current():
    name = RUNTIME.get("container")
    if not name:
        return False
    RUNTIME["stopped"] = True
    await run(["docker", "kill", name])
    return True


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text("⏹ To'xtatilmoqda…" if await stop_current() else "Ishlayotgan Claude yo'q.")


async def cmd_rollback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    deploys = load_state().get("deploys") or []
    if not deploys:
        return await update.message.reply_text("Orqaga qaytariladigan deploy yo'q.")
    last = deploys[-1]
    await update.message.reply_text(
        f"Oxirgi deploy ({last['time']}):\n{last['task']}\n\n{last['to'][:8]} → {last['from'][:8]} qaytarilsinmi?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("↩️ Ha, qaytarish", callback_data="rollback"),
            InlineKeyboardButton("Yo'q", callback_data="noop"),
        ]]),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    chat_id = update.effective_chat.id
    background(context, chat_id, lambda app: cancel_pending(app, chat_id))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not allowed(update):
        return await query.answer()
    chat_id = update.effective_chat.id
    action = query.data
    if action == "stop":
        await query.answer("To'xtatilmoqda…" if await stop_current() else "Ishlayotgan Claude yo'q.")
        return
    await query.answer()
    await query.edit_message_reply_markup(None)
    if action == "deploy":
        background(context, chat_id, lambda app: deploy(app, chat_id))
    elif action == "diff":
        await send_diff(context.application, chat_id)
        if load_state().get("pending"):
            await query.edit_message_reply_markup(InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Deploy", callback_data="deploy"),
                InlineKeyboardButton("🗑 Bekor qilish", callback_data="cancel"),
            ]]))
    elif action == "cancel":
        background(context, chat_id, lambda app: cancel_pending(app, chat_id))
    elif action == "rollback":
        background(context, chat_id, lambda app: rollback(app, chat_id))


async def post_init(app):
    me = await app.bot.get_me()
    RUNTIME["username"] = me.username or ""
    await app.bot.set_my_commands([
        ("new", "Yangi vazifa"), ("stop", "Claude'ni to'xtatish"), ("status", "Holat"),
        ("log", "Oxirgi commitlar"), ("rollback", "Oxirgi deployni qaytarish"),
        ("cancel", "Kutilayotganini bekor qilish"), ("help", "Yordam"),
    ])
    app.create_task(config_watcher(app))
    log.info("devbot @%s ishga tushdi: prod=%s", me.username, PROD_DIR)


def wait_for_config():
    """Panelda token kiritilguncha kutadi (holatni panelga yuborib turadi)."""
    warned = False
    while True:
        data = fetch_config({"busy": False, "task": "", "version": VERSION, "username": ""})
        if data and data.get("telegram_token"):
            return data
        if not warned:
            log.info("Bot tokeni hali kiritilmagan — platforma → Integratsiyalar → Devbot")
            warned = True
        time.sleep(CONFIG_POLL)


def main():
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)
    CFG.update(wait_for_config())

    app = Application.builder().token(CFG["telegram_token"]).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("rollback", cmd_rollback))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    if RUNTIME["restart"]:
        sys.exit(3)  # systemd (Restart=always) yangi token bilan qayta yoqadi


if __name__ == "__main__":
    main()
