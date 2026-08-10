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

  function initTransactionModal() {
    var modal = document.getElementById("transaction-modal");
    if (!modal) return;
    var typeInput = document.getElementById("id_type");
    var title = document.getElementById("transaction-modal-title");
    var submit = document.getElementById("transaction-modal-submit");

    modal.addEventListener("ap-modal-opened", function (e) {
      var btn = e.detail && e.detail.trigger;
      if (!btn) return;
      var type = btn.getAttribute("data-transaction-type");
      if (type && typeInput) typeInput.value = type;
      var label = btn.getAttribute("data-transaction-title");
      if (label) {
        if (title) title.textContent = label;
        if (submit) submit.textContent = label;
      }
    });
  }

  function initPayModal() {
    var modal = document.getElementById("employee-contract-pay-modal");
    if (!modal) return;
    var select = document.getElementById("id_employee_contract");
    if (!select) return;

    modal.addEventListener("ap-modal-opened", function (e) {
      var btn = e.detail && e.detail.trigger;
      var contractId = btn && btn.getAttribute("data-contract-id");
      if (contractId) select.value = contractId;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initModals();
    initTransactionModal();
    initPayModal();
  });
})();
