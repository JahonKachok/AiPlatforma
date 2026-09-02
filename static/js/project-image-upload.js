/* BuildFlow — project image upload widget.
 *
 * Progressive enhancement over a plain <input type="file">: without JS the
 * field still works, the browser just shows its native picker. With JS you get
 * click-to-upload, drag & drop, a live preview, replace and remove.
 *
 * Removal is expressed through the form's hidden `remove_image` field, which
 * ProjectForm.save() reads — no extra endpoint, no second request.
 */
(function () {
  "use strict";

  var ALLOWED = ["image/jpeg", "image/png", "image/webp"];
  var ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;
  var MAX_BYTES = 8 * 1024 * 1024; // mirrors MaxFileSizeValidator(8) on the model

  function humanSize(bytes) {
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function init(root) {
    var input = root.querySelector(".prj-upload-input");
    var dropzone = root.querySelector(".prj-dropzone");
    var preview = root.querySelector(".prj-preview");
    var previewImg = preview ? preview.querySelector("img") : null;
    var nameEl = root.querySelector(".prj-preview-name");
    var errorEl = root.querySelector(".prj-upload-error");
    var removeFlag = document.querySelector(root.dataset.removeField || "");
    var replaceBtn = root.querySelector("[data-prj-replace]");
    var removeBtn = root.querySelector("[data-prj-remove]");
    if (!input || !dropzone || !preview) return;

    // Remembered so "remove" can fall back to the image already on the server.
    var originalSrc = previewImg ? previewImg.getAttribute("src") : "";
    var originalName = nameEl ? nameEl.textContent : "";
    var objectUrl = null;

    function setError(message) {
      if (!errorEl) return;
      errorEl.textContent = message || "";
      errorEl.classList.toggle("prj-upload-hidden", !message);
    }

    function showPreview(src, label) {
      if (previewImg) previewImg.setAttribute("src", src);
      if (nameEl) nameEl.textContent = label || "";
      preview.classList.remove("prj-upload-hidden");
      dropzone.classList.add("prj-upload-hidden");
    }

    function showDropzone() {
      preview.classList.add("prj-upload-hidden");
      dropzone.classList.remove("prj-upload-hidden");
    }

    function releaseObjectUrl() {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
    }

    function accept(file) {
      if (!file) return false;
      var typeOk = ALLOWED.indexOf(file.type) !== -1 || ALLOWED_EXT.test(file.name);
      if (!typeOk) {
        setError(root.dataset.errorType || "Unsupported file type.");
        return false;
      }
      if (file.size > MAX_BYTES) {
        setError(
          (root.dataset.errorSize || "File is too large.") + " (" + humanSize(file.size) + ")"
        );
        return false;
      }
      setError("");
      return true;
    }

    function useFile(file) {
      if (!accept(file)) return;
      releaseObjectUrl();
      objectUrl = URL.createObjectURL(file);
      showPreview(objectUrl, file.name);
      // Choosing a new file always wins over a pending removal.
      if (removeFlag) removeFlag.value = "";
    }

    input.addEventListener("change", function () {
      if (input.files && input.files.length) useFile(input.files[0]);
    });

    dropzone.addEventListener("click", function () { input.click(); });
    dropzone.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });

    ["dragenter", "dragover"].forEach(function (type) {
      dropzone.addEventListener(type, function (event) {
        event.preventDefault();
        dropzone.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (type) {
      dropzone.addEventListener(type, function (event) {
        event.preventDefault();
        dropzone.classList.remove("is-dragover");
      });
    });
    dropzone.addEventListener("drop", function (event) {
      var files = event.dataTransfer && event.dataTransfer.files;
      if (!files || !files.length) return;
      // Assigning to input.files is what makes the dropped file part of the
      // normal multipart POST — no separate upload request is needed.
      try {
        var dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
      } catch (err) {
        // Very old browsers: fall back to the picker rather than failing quietly.
        setError(root.dataset.errorDrop || "");
        input.click();
        return;
      }
      useFile(files[0]);
    });

    if (replaceBtn) {
      replaceBtn.addEventListener("click", function (event) {
        event.preventDefault();
        input.click();
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", function (event) {
        event.preventDefault();
        var confirmText = root.dataset.confirmRemove;
        if (originalSrc && confirmText && !window.confirm(confirmText)) return;
        releaseObjectUrl();
        input.value = "";
        if (removeFlag) removeFlag.value = originalSrc ? "1" : "";
        if (previewImg) previewImg.removeAttribute("src");
        if (nameEl) nameEl.textContent = originalName;
        setError("");
        showDropzone();
      });
    }

    window.addEventListener("pagehide", releaseObjectUrl);
  }

  function boot() {
    var widgets = document.querySelectorAll("[data-prj-upload]");
    Array.prototype.forEach.call(widgets, init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
