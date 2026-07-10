document.addEventListener("DOMContentLoaded", function () {
  const board = document.querySelector("[data-kanban-board]");
  if (!board) return;

  let draggedCard = null;
  let suppressClick = false;
  const placeholder = document.createElement("div");
  placeholder.className = "kb-placeholder";

  function updateCounts() {
    board.querySelectorAll("[data-kanban-column]").forEach((column) => {
      const cards = column.querySelectorAll("[data-task-card]").length;
      const count = column.querySelector("[data-kanban-count]");
      if (count) count.textContent = cards;
      const empty = column.querySelector("[data-kanban-empty]");
      if (empty) empty.style.display = cards ? "none" : "";
    });
  }

  // Insert placeholder before the card whose midpoint is below the cursor.
  function getInsertBefore(container, y) {
    const cards = [...container.querySelectorAll("[data-task-card]:not(.kb-dragging)")];
    return cards.find((card) => {
      const rect = card.getBoundingClientRect();
      return y < rect.top + rect.height / 2;
    }) || null;
  }

  board.addEventListener("dragstart", (e) => {
    const card = e.target.closest("[data-task-card]");
    if (!card) return;
    draggedCard = card;
    e.dataTransfer.effectAllowed = "move";
    // Delay so the browser captures the drag image before the card fades.
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
    board.querySelectorAll(".kb-drop-active").forEach((c) => {
      if (c !== column) c.classList.remove("kb-drop-active");
    });
    column.classList.add("kb-drop-active");
    const container = column.querySelector("[data-kanban-cards]");
    placeholder.style.height = draggedCard.offsetHeight + "px";
    const before = getInsertBefore(container, e.clientY);
    if (before) container.insertBefore(placeholder, before);
    else container.appendChild(placeholder);
  });

  board.addEventListener("dragleave", (e) => {
    const column = e.target.closest("[data-kanban-column]");
    if (column && !column.contains(e.relatedTarget)) {
      column.classList.remove("kb-drop-active");
    }
  });

  board.addEventListener("drop", (e) => {
    const column = e.target.closest("[data-kanban-column]");
    if (!column || !draggedCard) return;
    e.preventDefault();
    column.classList.remove("kb-drop-active");

    const card = draggedCard;
    const status = column.dataset.kanbanColumn;
    const url = card.dataset.statusUrl;
    const originColumn = card.closest("[data-kanban-column]");
    const originNext = card.nextElementSibling;

    // Optimistic move; revert if the server rejects it.
    if (placeholder.parentNode) placeholder.parentNode.insertBefore(card, placeholder);
    placeholder.remove();
    updateCounts();

    if (originColumn === column) return;

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "status=" + encodeURIComponent(status),
    })
      .then((res) => { if (!res.ok) throw new Error(); })
      .catch(() => {
        const originContainer = originColumn.querySelector("[data-kanban-cards]");
        if (originNext) originContainer.insertBefore(card, originNext);
        else originContainer.appendChild(card);
        updateCounts();
      });
  });

  // Click opens the task, but not right after a drag.
  board.addEventListener("click", (e) => {
    if (suppressClick) return;
    const card = e.target.closest("[data-task-card]");
    if (card && card.dataset.detailUrl) window.location = card.dataset.detailUrl;
  });

  updateCounts();
});
