document.addEventListener("DOMContentLoaded", function () {
  const board = document.querySelector("[data-kanban-board]");
  if (!board) return;

  let draggedCard = null;

  board.querySelectorAll("[data-task-card]").forEach((card) => {
    card.addEventListener("dragstart", () => {
      draggedCard = card;
      card.classList.add("opacity-50");
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("opacity-50");
      draggedCard = null;
    });
  });

  board.querySelectorAll("[data-kanban-column]").forEach((column) => {
    column.addEventListener("dragover", (e) => {
      e.preventDefault();
      column.classList.add("ring-2", "ring-blue-400");
    });
    column.addEventListener("dragleave", () => {
      column.classList.remove("ring-2", "ring-blue-400");
    });
    column.addEventListener("drop", (e) => {
      e.preventDefault();
      column.classList.remove("ring-2", "ring-blue-400");
      if (!draggedCard) return;
      const status = column.dataset.kanbanColumn;
      const taskId = draggedCard.dataset.taskCard;
      const url = draggedCard.dataset.statusUrl;
      const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

      fetch(url, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "status=" + encodeURIComponent(status),
      }).then((res) => {
        if (res.ok) {
          column.querySelector("[data-kanban-cards]").appendChild(draggedCard);
        }
      });
    });
  });
});
