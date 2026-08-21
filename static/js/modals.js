(function () {
  "use strict";

  function initModals() {
    var modals = document.querySelectorAll(".ap-modal-backdrop");
    if (!modals.length) return;

    document.querySelectorAll("[data-modal-open]").forEach(function (btn) {
      var target = document.getElementById(btn.getAttribute("data-modal-open"));
      if (!target) return;
      btn.addEventListener("click", function () {
        target.classList.add("is-open");
        target.dispatchEvent(new CustomEvent("ap-modal-opened", { detail: { trigger: btn } }));
      });
    });

    modals.forEach(function (modal) {
      modal.querySelectorAll("[data-modal-close]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          modal.classList.remove("is-open");
        });
      });
      modal.addEventListener("click", function (e) {
        if (e.target === modal) modal.classList.remove("is-open");
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        modals.forEach(function (modal) {
          modal.classList.remove("is-open");
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", initModals);
})();
