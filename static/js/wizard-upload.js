(function () {
  "use strict";

  const grid = document.getElementById("wizard-upload-grid");
  if (!grid) return;

  const uploadUrl = grid.dataset.uploadUrl;
  const deleteUrlTemplate = grid.dataset.deleteUrlTemplate;
  const csrfToken = grid.dataset.csrf;
  const PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000000";

  function showError(card, message) {
    const errorEl = card.querySelector(".upload-error");
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearError(card) {
    const errorEl = card.querySelector(".upload-error");
    errorEl.classList.add("hidden");
    errorEl.textContent = "";
  }

  function addFileRow(card, documentId, fileName) {
    const list = card.querySelector(".upload-file-list");
    const row = document.createElement("div");
    row.className = "upload-file-state flex items-center gap-3";
    row.dataset.documentId = documentId;
    row.innerHTML =
      '<span class="text-2xl">📄</span>' +
      '<div class="min-w-0 flex-1">' +
      '<p class="upload-file-name truncate text-sm"></p>' +
      '<div class="mt-1 h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700">' +
      '<div class="upload-progress-bar h-1.5 rounded-full bg-blue-500 transition-all duration-300" style="width: 100%"></div>' +
      "</div></div>" +
      '<span class="upload-progress-pct text-xs text-gray-500 dark:text-gray-400">100%</span>' +
      '<button type="button" class="upload-delete-btn text-red-500 hover:text-red-700" aria-label="O’chirish">✕</button>';
    row.querySelector(".upload-file-name").textContent = fileName;
    row.querySelector(".upload-delete-btn").addEventListener("click", function () {
      deleteFile(card, row);
    });
    list.classList.add("mt-2");
    list.appendChild(row);
    return row;
  }

  function uploadFiles(card, fileList) {
    const files = Array.prototype.slice.call(fileList);
    if (!files.length) return;
    clearError(card);
    const docType = card.dataset.docType;

    const formData = new FormData();
    formData.append("doc_type", docType);
    files.forEach(function (file) { formData.append("file", file); });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", uploadUrl, true);
    xhr.setRequestHeader("X-CSRFToken", csrfToken);

    xhr.addEventListener("load", function () {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (e) { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300 && data.documents) {
        data.documents.forEach(function (doc) { addFileRow(card, doc.id, doc.name); });
      } else {
        showError(card, data.error || "Yuklashda xatolik yuz berdi.");
      }
    });

    xhr.addEventListener("error", function () {
      showError(card, "Tarmoq xatoligi — qayta urinib ko'ring.");
    });

    xhr.send(formData);
  }

  function deleteFile(card, row) {
    const documentId = row.dataset.documentId;
    if (!documentId) {
      row.remove();
      return;
    }
    const url = deleteUrlTemplate.replace(PLACEHOLDER_UUID, documentId);
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
    }).then(function () {
      row.remove();
    });
  }

  grid.querySelectorAll(".upload-card").forEach(function (card) {
    const input = card.querySelector(".upload-file-input");
    const dropLabel = card.querySelector(".upload-drop");

    input.addEventListener("change", function () {
      if (input.files && input.files.length) uploadFiles(card, input.files);
      input.value = "";
    });

    dropLabel.addEventListener("dragover", function (event) {
      event.preventDefault();
      dropLabel.classList.add("upload-drop-active");
    });
    dropLabel.addEventListener("dragleave", function () {
      dropLabel.classList.remove("upload-drop-active");
    });
    dropLabel.addEventListener("drop", function (event) {
      event.preventDefault();
      dropLabel.classList.remove("upload-drop-active");
      if (event.dataTransfer.files && event.dataTransfer.files.length) {
        uploadFiles(card, event.dataTransfer.files);
      }
    });

    card.querySelectorAll(".upload-delete-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        deleteFile(card, btn.closest(".upload-file-state"));
      });
    });
  });
})();
