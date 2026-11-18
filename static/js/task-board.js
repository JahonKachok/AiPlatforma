// «Задачи» doskasi: 8 ta ustun (Черновик → … → Закрыто), kartochkani istalgan
// ustunga surish, kartochkadan o'chirish va sahifani qayta yuklamasdan yangilanish.
document.addEventListener("DOMContentLoaded", function () {
  const board = document.querySelector("[data-kanban-board]");
  if (!board) return;

  const REFRESH_MS = 30000;
  const toastBox = document.querySelector("[data-board-toast]");
  const csrf = () => (document.querySelector("[name=csrfmiddlewaretoken]") || {}).value || "";
  let draggedCard = null;
  let suppressClick = false;
  let busy = 0; // so'rov ketayotganda avtomatik yangilanish kartani joyidan sakratmasin
  let toastTimer = null;
  const placeholder = document.createElement("div");
  placeholder.className = "kb-placeholder";

  function toast(text) {
    if (!toastBox) return;
    toastBox.textContent = text;
    toastBox.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastBox.hidden = true; }, 5000);
  }

  function updateCounts() {
    board.querySelectorAll("[data-kanban-column]").forEach((column) => {
      const cards = column.querySelectorAll("[data-task-card]").length;
      const count = column.querySelector("[data-kanban-count]");
      if (count) count.textContent = cards;
      const empty = column.querySelector("[data-kanban-empty]");
      if (empty) empty.style.display = cards ? "none" : "";
    });
  }

  function getInsertBefore(container, y) {
    const cards = [...container.querySelectorAll("[data-task-card]:not(.kb-dragging)")];
    return cards.find((card) => {
      const rect = card.getBoundingClientRect();
      return y < rect.top + rect.height / 2;
    }) || null;
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf(),
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body: new URLSearchParams(body || {}).toString(),
    });
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok || !data || data.ok === false) throw new Error((data && data.error) || "");
    return data;
  }

  function moveCard(card, column, before) {
    const container = column.querySelector("[data-kanban-cards]");
    const empty = container.querySelector("[data-kanban-empty]");
    if (before && before.parentNode === container) container.insertBefore(card, before);
    else container.insertBefore(card, empty || null);
    updateCounts();
  }

  async function sendMove(card, column, before) {
    const origin = card.closest("[data-kanban-column]");
    const originNext = card.nextElementSibling;
    if (origin === column) return;
    moveCard(card, column, before); // optimistik — server rad etsa qaytariladi
    busy++;
    try {
      const data = await post(card.dataset.moveUrl, { column: column.dataset.kanbanColumn });
      // server boshqa ustunni tanlagan bo'lishi mumkin (masalan, ruxsat etilmagan bosqich)
      const real = data.column && board.querySelector(`[data-kanban-column="${data.column}"]`);
      if (real && real !== column) moveCard(card, real, null);
      refresh();
    } catch (e) {
      const container = origin.querySelector("[data-kanban-cards]");
      if (originNext && originNext.parentNode === container) container.insertBefore(card, originNext);
      else container.insertBefore(card, container.querySelector("[data-kanban-empty]"));
      updateCounts();
      toast(e.message || board.dataset.msgError);
    } finally {
      busy--;
    }
  }

  function bind() {
    board.addEventListener("dragstart", (e) => {
      const card = e.target.closest("[data-task-card][draggable=true]");
      if (!card) return;
      draggedCard = card;
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", card.dataset.taskCard);
      setTimeout(() => card.classList.add("kb-dragging"), 0);
    });

    board.addEventListener("dragend", () => {
      if (draggedCard) draggedCard.classList.remove("kb-dragging");
      draggedCard = null;
      placeholder.remove();
      board.querySelectorAll(".kb-drop-active").forEach((c) => c.classList.remove("kb-drop-active"));
      suppressClick = true;
      setTimeout(() => { suppressClick = false; }, 100);
    });

    board.addEventListener("dragover", (e) => {
      const column = e.target.closest("[data-kanban-column]");
      if (!column || !draggedCard) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      board.querySelectorAll(".kb-drop-active").forEach((c) => { if (c !== column) c.classList.remove("kb-drop-active"); });
      column.classList.add("kb-drop-active");
      const container = column.querySelector("[data-kanban-cards]");
      placeholder.style.height = draggedCard.offsetHeight + "px";
      const before = getInsertBefore(container, e.clientY);
      container.insertBefore(placeholder, before || container.querySelector("[data-kanban-empty]"));
    });

    board.addEventListener("dragleave", (e) => {
      const column = e.target.closest("[data-kanban-column]");
      if (column && !column.contains(e.relatedTarget)) column.classList.remove("kb-drop-active");
    });

    board.addEventListener("drop", (e) => {
      const column = e.target.closest("[data-kanban-column]");
      if (!column || !draggedCard) return;
      e.preventDefault();
      column.classList.remove("kb-drop-active");
      const before = placeholder.nextElementSibling;
      placeholder.remove();
      sendMove(draggedCard, column, before && before.matches("[data-task-card]") ? before : null);
    });

    board.addEventListener("click", async (e) => {
      const del = e.target.closest("[data-delete-url]");
      if (del) {
        e.stopPropagation();
        if (!window.confirm(board.dataset.msgDelete)) return;
        const card = del.closest("[data-task-card]");
        busy++;
        try {
          await post(del.dataset.deleteUrl);
          card.remove();
          updateCounts();
          refresh();
        } catch (err) {
          toast(err.message || board.dataset.msgDeleteError);
        } finally {
          busy--;
        }
        return;
      }
      if (suppressClick) return;
      const card = e.target.closest("[data-task-card]");
      if (card && card.dataset.detailUrl) window.location = card.dataset.detailUrl;
    });

    // Klaviatura: Enter — ochish, ←/→ — qo'shni ustunga o'tkazish
    board.addEventListener("keydown", (e) => {
      const card = e.target.closest("[data-task-card]");
      if (!card || e.target.closest("button")) return;
      if (e.key === "Enter") { window.location = card.dataset.detailUrl; return; }
      if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && card.getAttribute("draggable") === "true") {
        const cols = [...board.querySelectorAll("[data-kanban-column]")];
        const next = cols[cols.indexOf(card.closest("[data-kanban-column]")) + (e.key === "ArrowRight" ? 1 : -1)];
        if (next) { e.preventDefault(); sendMove(card, next, null).then(() => card.focus()); }
      }
    });
  }

  // Ma'lumot boshqa joyda (Состав, Pult, boshqa xodim) o'zgarsa — doska o'zi yangilanadi.
  let refreshing = false;
  async function refresh() {
    if (refreshing || busy || draggedCard || document.hidden) return;
    refreshing = true;
    try {
      const res = await fetch(location.href, { credentials: "same-origin", headers: { "X-Requested-With": "fetch" }, cache: "no-store" });
      if (!res.ok || res.redirected) return;
      const doc = new DOMParser().parseFromString(await res.text(), "text/html");
      const fresh = doc.querySelector("[data-kanban-board]");
      if (!fresh || busy || draggedCard) return;
      const focused = document.activeElement && document.activeElement.closest("[data-task-card]");
      const focusId = focused && focused.dataset.taskCard;
      const scroll = board.scrollLeft;
      board.innerHTML = fresh.innerHTML;
      board.scrollLeft = scroll;
      const stats = document.querySelector("[data-board-stats]"), freshStats = doc.querySelector("[data-board-stats]");
      if (stats && freshStats) stats.innerHTML = freshStats.innerHTML;
      if (focusId) { const again = board.querySelector(`[data-task-card="${focusId}"]`); if (again) again.focus(); }
    } catch (e) {
      /* tarmoq xatosi — keyingi safar */
    } finally {
      refreshing = false;
    }
  }

  bind();
  updateCounts();
  setInterval(refresh, REFRESH_MS);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  window.addEventListener("focus", refresh);
});
