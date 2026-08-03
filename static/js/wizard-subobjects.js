(function () {
  "use strict";

  const listEl = document.getElementById("subobject-list");
  if (!listEl) return;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : "";
  }
  const csrfToken = getCookie("csrftoken");

  function post(url, data) {
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      body: data,
    }).then(function (resp) { return resp.json().then(function (json) { return { ok: resp.ok, json: json }; }); });
  }

  function formToData(form) {
    return new FormData(form);
  }

  // ---------- Add sub-object ----------
  const addBtn = document.getElementById("subobject-add-btn");
  if (addBtn) {
    addBtn.addEventListener("click", function () {
      post(addBtn.dataset.createUrl, new FormData()).then(function (result) {
        if (result.json.html) {
          listEl.insertAdjacentHTML("beforeend", result.json.html);
        }
      });
    });
  }

  // ---------- Delegated events ----------
  document.addEventListener("change", function (event) {
    const subForm = event.target.closest(".subobject-fields-form");
    if (subForm) {
      post(subForm.dataset.url, formToData(subForm)).then(function (result) {
        if (result.ok) {
          const card = subForm.closest(".subobject-card");
          const bar = card.querySelector(".subobject-progress-bar");
          if (bar) bar.style.width = result.json.progress + "%";
        }
      });
      return;
    }
    const taskForm = event.target.closest(".task-fields-form");
    if (taskForm) {
      const details = taskForm.closest(".task-item");
      post(details.dataset.updateUrl, formToData(taskForm)).then(function (result) {
        if (result.ok) {
          const titleInput = taskForm.querySelector('[name="title"]');
          if (titleInput) {
            details.querySelector(".task-title-display").textContent = titleInput.value;
          }
          if (result.json.progress !== null && result.json.progress !== undefined) {
            const card = details.closest(".subobject-card");
            const bar = card && card.querySelector(".subobject-progress-bar");
            if (bar) bar.style.width = result.json.progress + "%";
          }
        }
      });
    }
  });

  document.addEventListener("click", function (event) {
    // Delete sub-object
    const deleteBtn = event.target.closest(".subobject-delete-btn");
    if (deleteBtn) {
      if (!confirm("O'chirilsinmi?")) return;
      const card = deleteBtn.closest(".subobject-card");
      post(deleteBtn.dataset.url, new FormData()).then(function () { card.remove(); });
      return;
    }

    // Duplicate sub-object
    const dupBtn = event.target.closest(".subobject-duplicate-btn");
    if (dupBtn) {
      const card = dupBtn.closest(".subobject-card");
      post(dupBtn.dataset.url, new FormData()).then(function (result) {
        if (result.json.html) card.insertAdjacentHTML("afterend", result.json.html);
      });
      return;
    }

    // Remove worker
    const workerRemoveBtn = event.target.closest(".worker-remove-btn");
    if (workerRemoveBtn) {
      const chip = workerRemoveBtn.closest(".worker-chip");
      const section = workerRemoveBtn.closest(".workers-section");
      const url = section.dataset.removeUrlTemplate.replace(
        "00000000-0000-0000-0000-000000000000", chip.dataset.workerId,
      );
      post(url, new FormData()).then(function () { chip.remove(); });
      return;
    }

    // Add task
    const taskAddBtn = event.target.closest(".task-add-btn");
    if (taskAddBtn) {
      const section = taskAddBtn.closest(".tasks-section");
      post(section.dataset.createUrl, new FormData()).then(function (result) {
        if (result.json.html) {
          section.querySelector(".task-list").insertAdjacentHTML("beforeend", result.json.html);
          const card = section.closest(".subobject-card");
          const bar = card && card.querySelector(".subobject-progress-bar");
          if (bar && result.json.progress !== undefined) bar.style.width = result.json.progress + "%";
        }
      });
      return;
    }

    // Delete task
    const taskDeleteBtn = event.target.closest(".task-delete-btn");
    if (taskDeleteBtn) {
      event.preventDefault();
      if (!confirm("O'chirilsinmi?")) return;
      const details = taskDeleteBtn.closest(".task-item");
      const card = details.closest(".subobject-card");
      post(details.dataset.deleteUrl, new FormData()).then(function (result) {
        details.remove();
        const bar = card && card.querySelector(".subobject-progress-bar");
        if (bar && result.json.progress !== null && result.json.progress !== undefined) {
          bar.style.width = result.json.progress + "%";
        }
      });
      return;
    }

    // Add checklist item
    const checklistAddBtn = event.target.closest(".checklist-add-btn");
    if (checklistAddBtn) {
      const section = checklistAddBtn.closest(".checklist-section");
      const input = section.querySelector(".checklist-new-input");
      const text = input.value.trim();
      if (!text) return;
      const details = checklistAddBtn.closest(".task-item");
      const formData = new FormData();
      formData.append("text", text);
      post(details.dataset.checklistAddUrl, formData).then(function (result) {
        if (result.json.html) {
          section.querySelector(".checklist-list").insertAdjacentHTML("beforeend", result.json.html);
          input.value = "";
        }
      });
      return;
    }

    // Delete checklist item
    const checklistDeleteBtn = event.target.closest(".checklist-delete-btn");
    if (checklistDeleteBtn) {
      const li = checklistDeleteBtn.closest(".checklist-item");
      const details = checklistDeleteBtn.closest(".task-item");
      const url = details.dataset.checklistDeleteUrlTemplate.replace(
        "00000000-0000-0000-0000-000000000000", li.dataset.itemId,
      );
      post(url, new FormData()).then(function () { li.remove(); });
      return;
    }

    // Worker search result pick
    const resultRow = event.target.closest(".worker-search-result");
    if (resultRow) {
      const section = resultRow.closest(".workers-section");
      const formData = new FormData();
      formData.append("user", resultRow.dataset.userId);
      formData.append("role", "engineer");
      formData.append("status", "pending");
      post(section.dataset.addUrl, formData).then(function (result) {
        if (result.json.html) {
          section.querySelector(".worker-chips").insertAdjacentHTML("beforeend", result.json.html);
          section.querySelector(".worker-search-input").value = "";
          section.querySelector(".worker-search-results").classList.add("hidden");
        }
      });
    }
  });

  document.addEventListener("input", function (event) {
    const searchInput = event.target.closest(".worker-search-input");
    if (!searchInput) return;
    const section = searchInput.closest(".workers-section");
    const resultsBox = section.querySelector(".worker-search-results");
    const query = searchInput.value.trim();
    clearTimeout(searchInput._debounce);
    searchInput._debounce = setTimeout(function () {
      const subId = section.closest(".subobject-card").dataset.subId;
      fetch(section.dataset.searchUrl + "?q=" + encodeURIComponent(query) + "&sub_object=" + subId)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.results.length) {
            resultsBox.classList.add("hidden");
            resultsBox.innerHTML = "";
            return;
          }
          resultsBox.innerHTML = data.results.map(function (r) {
            return '<div class="worker-search-result cursor-pointer px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700" data-user-id="' + r.id + '">' + r.label + "</div>";
          }).join("");
          resultsBox.classList.remove("hidden");
        });
    }, 200);
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".worker-search")) {
      document.querySelectorAll(".worker-search-results").forEach(function (box) {
        box.classList.add("hidden");
      });
    }
  });

  document.addEventListener("change", function (event) {
    const checkbox = event.target.closest(".checklist-toggle");
    if (!checkbox) return;
    const li = checkbox.closest(".checklist-item");
    const details = checkbox.closest(".task-item");
    const url = details.dataset.checklistToggleUrlTemplate.replace(
      "00000000-0000-0000-0000-000000000000", li.dataset.itemId,
    );
    post(url, new FormData()).then(function (result) {
      const text = li.querySelector(".checklist-text");
      if (result.json.is_done) {
        text.classList.add("text-gray-400", "line-through");
      } else {
        text.classList.remove("text-gray-400", "line-through");
      }
    });
  });

  // ---------- Drag & drop reordering ----------
  function enableSortable(container, itemSelector, reorderUrl, dragHandleSelector) {
    let dragged = null;
    container.addEventListener("dragstart", function (event) {
      const item = event.target.closest(itemSelector);
      if (!item || (dragHandleSelector && !event.target.closest(dragHandleSelector))) return;
      dragged = item;
      event.dataTransfer.effectAllowed = "move";
    });
    container.addEventListener("dragover", function (event) {
      event.preventDefault();
      const target = event.target.closest(itemSelector);
      if (!target || target === dragged || !dragged || target.parentElement !== container) return;
      const rect = target.getBoundingClientRect();
      const after = (event.clientY - rect.top) / rect.height > 0.5;
      container.insertBefore(dragged, after ? target.nextSibling : target);
    });
    container.addEventListener("drop", function (event) {
      event.preventDefault();
      if (!dragged) return;
      const ids = Array.prototype.map.call(
        container.querySelectorAll(itemSelector), function (el) { return el.dataset.subId || el.dataset.taskId; },
      );
      const formData = new FormData();
      ids.forEach(function (id) { formData.append("order[]", id); });
      post(reorderUrl, formData);
      dragged = null;
    });
  }

  enableSortable(listEl, ".subobject-card", listEl.dataset.reorderUrl, ".subobject-drag-handle");

  function bindTaskListSortable(card) {
    const section = card.querySelector(".tasks-section");
    if (!section) return;
    const taskList = section.querySelector(".task-list");
    enableSortable(taskList, ".task-item", section.dataset.reorderUrl, ".task-drag-handle");
  }

  document.querySelectorAll(".subobject-card").forEach(bindTaskListSortable);

  // Re-bind task sortable whenever a new sub-object card is inserted.
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) {
        if (node.nodeType === 1 && node.classList && node.classList.contains("subobject-card")) {
          bindTaskListSortable(node);
        }
      });
    });
  });
  observer.observe(listEl, { childList: true });
})();
