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

  function setUploadedState(card, documentId, fileName) {
    card.querySelector(".upload-drop-state").classList.add("hidden");
    const fileState = card.querySelector(".upload-file-state");
    fileState.classList.remove("hidden");
    fileState.dataset.documentId = documentId;
    card.querySelector(".upload-file-name").textContent = fileName;
    card.querySelector(".upload-progress-bar").style.width = "100%";
    card.querySelector(".upload-progress-pct").textContent = "100%";
  }

  function setEmptyState(card) {
    card.querySelector(".upload-file-state").classList.add("hidden");
    card.querySelector(".upload-drop-state").classList.remove("hidden");
    card.querySelector(".upload-progress-bar").style.width = "0%";
    card.querySelector(".upload-progress-pct").textContent = "";
    card.querySelector(".upload-file-input").value = "";
  }

  function uploadFile(card, file) {
    clearError(card);
    const docType = card.dataset.docType;
    const fileState = card.querySelector(".upload-file-state");
    const dropState = card.querySelector(".upload-drop-state");
    dropState.classList.add("hidden");
    fileState.classList.remove("hidden");
    card.querySelector(".upload-file-name").textContent = file.name;
    card.querySelector(".upload-progress-bar").style.width = "0%";
    card.querySelector(".upload-progress-pct").textContent = "0%";

    const formData = new FormData();
    formData.append("doc_type", docType);
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", uploadUrl, true);
    xhr.setRequestHeader("X-CSRFToken", csrfToken);

    xhr.upload.addEventListener("progress", function (event) {
      if (!event.lengthComputable) return;
      const pct = Math.round((event.loaded / event.total) * 100);
      card.querySelector(".upload-progress-bar").style.width = pct + "%";
      card.querySelector(".upload-progress-pct").textContent = pct + "%";
    });

    xhr.addEventListener("load", function () {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (e) { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300 && data.id) {
        setUploadedState(card, data.id, data.name);
      } else {
        setEmptyState(card);
        showError(card, data.error || "Yuklashda xatolik yuz berdi.");
      }
    });

    xhr.addEventListener("error", function () {
      setEmptyState(card);
      showError(card, "Tarmoq xatoligi — qayta urinib ko'ring.");
    });

    xhr.send(formData);
  }

  function deleteFile(card) {
    const fileState = card.querySelector(".upload-file-state");
    const documentId = fileState.dataset.documentId;
    if (!documentId) {
      setEmptyState(card);
      return;
    }
    const url = deleteUrlTemplate.replace(PLACEHOLDER_UUID, documentId);
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
    }).then(function () {
      setEmptyState(card);
    });
  }

  grid.querySelectorAll(".upload-card").forEach(function (card) {
    const input = card.querySelector(".upload-file-input");
    const dropLabel = card.querySelector(".upload-drop");
    const deleteBtn = card.querySelector(".upload-delete-btn");

    input.addEventListener("change", function () {
      if (input.files && input.files[0]) uploadFile(card, input.files[0]);
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
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (file) uploadFile(card, file);
    });

    deleteBtn.addEventListener("click", function () {
      deleteFile(card);
    });
  });
})();
