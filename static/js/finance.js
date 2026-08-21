(function () {
  "use strict";

  function initTransactionModal() {
    var modal = document.getElementById("transaction-modal");
    if (!modal) return;
    var typeInput = document.getElementById("id_type");
    var title = document.getElementById("transaction-modal-title");
    var submit = document.getElementById("transaction-modal-submit");
    var projectSelect = document.getElementById("id_project");
    var subObjectSelect = document.getElementById("id_sub_object");
    var categorySelect = document.getElementById("id_category");
    var podObjectSelect = document.getElementById("id_pod_object");
    var podObjectWrapper = document.getElementById("id_pod_object_wrapper");

    function filterSubObjects() {
      if (!projectSelect || !subObjectSelect) return;
      var projectId = projectSelect.value;
      var currentValue = subObjectSelect.value;
      var stillVisible = false;
      Array.prototype.forEach.call(subObjectSelect.options, function (opt) {
        if (!opt.value) return; // always keep the blank placeholder
        var matches = opt.getAttribute("data-project") === projectId;
        opt.hidden = !matches;
        if (matches && opt.value === currentValue) stillVisible = true;
      });
      if (!stillVisible) subObjectSelect.value = "";
    }

    function filterPodObjects() {
      if (!subObjectSelect || !podObjectSelect) return;
      var subObjectId = subObjectSelect.value;
      var currentValue = podObjectSelect.value;
      var stillVisible = false;
      Array.prototype.forEach.call(podObjectSelect.options, function (opt) {
        if (!opt.value) return;
        var matches = subObjectId !== "" && opt.getAttribute("data-parent") === subObjectId;
        opt.hidden = !matches;
        if (matches && opt.value === currentValue) stillVisible = true;
      });
      if (!stillVisible) podObjectSelect.value = "";
    }

    function toggleCategoryFields() {
      if (!categorySelect || !podObjectWrapper) return;
      var isSalary = categorySelect.value === "salary";
      podObjectWrapper.classList.toggle("hidden", !isSalary);
      if (!isSalary && podObjectSelect) podObjectSelect.value = "";
      if (isSalary) filterPodObjects();
    }

    if (projectSelect) {
      projectSelect.addEventListener("change", function () {
        filterSubObjects();
        filterPodObjects();
      });
    }
    if (subObjectSelect) subObjectSelect.addEventListener("change", filterPodObjects);
    if (categorySelect) categorySelect.addEventListener("change", toggleCategoryFields);

    modal.addEventListener("ap-modal-opened", function (e) {
      var btn = e.detail && e.detail.trigger;
      filterSubObjects();
      toggleCategoryFields();
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

  function initEmployeeContractModal() {
    var modal = document.getElementById("employee-contract-modal");
    if (!modal) return;
    var projectSelect = document.getElementById("id_project");
    var subObjectSelect = document.getElementById("id_sub_object");
    var podObjectSelect = document.getElementById("id_pod_object");
    if (!projectSelect || !subObjectSelect || !podObjectSelect) return;

    function filterSubObjects() {
      var projectId = projectSelect.value;
      var currentValue = subObjectSelect.value;
      var stillVisible = false;
      Array.prototype.forEach.call(subObjectSelect.options, function (opt) {
        if (!opt.value) return;
        var matches = opt.getAttribute("data-project") === projectId;
        opt.hidden = !matches;
        if (matches && opt.value === currentValue) stillVisible = true;
      });
      if (!stillVisible) subObjectSelect.value = "";
    }

    function filterPodObjects() {
      var subObjectId = subObjectSelect.value;
      var currentValue = podObjectSelect.value;
      var stillVisible = false;
      Array.prototype.forEach.call(podObjectSelect.options, function (opt) {
        if (!opt.value) return;
        var matches = subObjectId !== "" && opt.getAttribute("data-parent") === subObjectId;
        opt.hidden = !matches;
        if (matches && opt.value === currentValue) stillVisible = true;
      });
      if (!stillVisible) podObjectSelect.value = "";
    }

    projectSelect.addEventListener("change", function () {
      filterSubObjects();
      filterPodObjects();
    });
    subObjectSelect.addEventListener("change", filterPodObjects);

    modal.addEventListener("ap-modal-opened", function () {
      filterSubObjects();
      filterPodObjects();
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

  function initFilterPanels() {
    function setupFilterToggle(toggleId, panelId) {
      var btn = document.getElementById(toggleId);
      var panel = document.getElementById(panelId);
      if (!btn || !panel) return;
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        panel.classList.toggle("hidden");
      });
    }

    setupFilterToggle("payroll-filter-toggle", "payroll-filter-panel");
    setupFilterToggle("cashflow-filter-toggle", "cashflow-filter-panel");
    setupFilterToggle("admin-filter-toggle", "admin-filter-panel");
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTransactionModal();
    initEmployeeContractModal();
    initPayModal();
    initFilterPanels();
  });
})();

