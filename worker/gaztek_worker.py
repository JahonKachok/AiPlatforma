"""Gaztek Pult — ishchi kompyuter agenti (Windows, AutoCAD/Word/Excel o'rnatilgan).

Server bilan aloqa faqat chiquvchi HTTPS: kompyuter navbatdan ish oladi, faylni
yuklab oladi, bajaradi va natijani qaytaradi. Claude kaliti shu yerda turmaydi:
AI kerak bo'lsa server proksisi (/api/worker/ai/) chaqiriladi.

Ishga tushirish:  python -m worker.gaztek_worker  (sozlama: worker/worker.ini)
"""
import configparser
import json
import logging
import shutil
import socket
import sys
import time
import traceback
from pathlib import Path

import requests

from . import handlers
from .common import RetryableError
from .localarchive import place

VERSION = "1.0"
log = logging.getLogger("gaztek_worker")


class Context:
    """Handler'larga: AI proksi va ish ma'lumotlari."""

    def __init__(self, client, job, workdir):
        self.client, self.job, self.workdir = client, job, workdir

    def ai(self, agent, payload):
        response = self.client.post("ai/", json={"job": self.job["id"], "agent": agent, "input": payload}, timeout=300)
        if response.status_code == 503:
            raise RetryableError("AI unavailable")
        response.raise_for_status()
        return response.json()["data"]


class Client:
    def __init__(self, server, token):
        self.base = server.rstrip("/") + "/api/worker/"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def post(self, path, **kw):
        return self.session.post(self.base + path, **kw)

    def get(self, path, **kw):
        return self.session.get(self.base + path, **kw)


def load_config(path=None):
    cfg = configparser.ConfigParser()
    cfg.read(path or Path(__file__).with_name("worker.ini"), encoding="utf-8")
    s = cfg["worker"]
    profile = Path(s["gost_profile"]) if s.get("gost_profile") else None
    kinds = [k.strip() for k in s.get("kinds", ",".join(handlers.HANDLERS)).split(",") if k.strip()]
    if "gost_format" in kinds and not (profile and profile.is_file()):
        kinds.remove("gost_format")
    if not kinds:
        raise ValueError("No configured worker job types")
    return {
        "server": s["server"], "token": s["token"], "name": s.get("name", socket.gethostname()),
        "workdir": Path(s.get("workdir", r"C:\GaztekWorker\jobs")),
        "out_dir": Path(s["out_dir"]) if s.get("out_dir") else None,
        "poll": s.getint("poll_seconds", 10),
        "kinds": kinds, "gost_profile": profile,
    }


def run_job(client, cfg, job):
    jobdir = cfg["workdir"] / job["id"]
    jobdir.mkdir(parents=True, exist_ok=True)
    source = jobdir / job["file_name"]  # fayl nomi o'zgartirilmaydi
    with client.get(f"jobs/{job['id']}/input/", stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(source, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    ctx = Context(client, job, jobdir)
    ctx.gost_profile = cfg.get("gost_profile")
    try:
        output = handlers.HANDLERS[job["kind"]](job, source, ctx)
    except Exception as exc:  # noqa: BLE001 — har qanday xato serverga qaytadi
        log.exception("job %s failed", job["id"])
        client.post(f"jobs/{job['id']}/result/", data={
            "ok": "0", "error": "".join(traceback.format_exception_only(type(exc), exc))[-3000:],
            "result": json.dumps({"retry": isinstance(exc, RetryableError)}),
        }, timeout=120)
        return False
    files = {}
    handles = []
    for key, path in (("file", output.file), ("source", output.source)):
        if path:
            fh = open(path, "rb")
            handles.append(fh)
            files[key] = (Path(path).name, fh)
    try:
        r = client.post(f"jobs/{job['id']}/result/", data={"ok": "1", "result": json.dumps(output.result, ensure_ascii=False)},
                        files=files or None, timeout=600)
        r.raise_for_status()
    finally:
        for fh in handles:
            fh.close()
    if cfg["out_dir"]:  # lokal nusxa: Loyiha/Obyekt/Intizom, eskisi «Old»ga
        for path in (output.file, output.source):
            if path:
                place(Path(path), cfg["out_dir"], [job.get("project"), job.get("object"), job.get("discipline")])
    shutil.rmtree(jobdir, ignore_errors=True)
    return True


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(argv[1] if argv and len(argv) > 1 else None)
    client = Client(cfg["server"], cfg["token"])
    log.info("worker %s started, kinds=%s", cfg["name"], cfg["kinds"])
    while True:
        try:
            r = client.post("claim/", json={"worker": cfg["name"], "kinds": cfg["kinds"], "version": VERSION}, timeout=60)
            r.raise_for_status()
            job = r.json().get("job")
            if job is None:
                time.sleep(cfg["poll"])
                continue
            log.info("job %s %s %s", job["id"], job["kind"], job["file_name"])
            run_job(client, cfg, job)
        except requests.RequestException as exc:
            log.warning("server unreachable: %s", exc)
            time.sleep(max(cfg["poll"], 30))


if __name__ == "__main__":
    main(sys.argv)
