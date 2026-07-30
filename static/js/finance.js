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

  function initPaymentRequestModal() {
    var modal = document.getElementById("payment-request-modal");
    if (!modal) return;

    var amountInput = document.getElementById("id_amount");
    var retainagePreview = document.getElementById("payment-retainage-preview");
    var netPreview = document.getElementById("payment-net-preview");
    var stage3 = document.getElementById("payment-stage-3");
    var stage3Note = document.getElementById("payment-stage-3-note");
    var stage3NoteDefault = stage3Note ? stage3Note.textContent : "";
    var threshold = parseFloat(modal.getAttribute("data-manager-threshold")) || 10000;
    var RETAINAGE_RATE = 0.05;

    function formatNumber(n) {
      return Math.round(n).toLocaleString("en-US").replace(/,/g, " ");
    }

    function recalc() {
      if (!amountInput) return;
      var amount = parseFloat(amountInput.value.replace(/[^0-9.]/g, "")) || 0;
      var retainage = amount * RETAINAGE_RATE;
      if (retainagePreview) retainagePreview.value = formatNumber(retainage);
      if (netPreview) netPreview.textContent = formatNumber(amount - retainage);

      if (stage3) {
        var circle = stage3.querySelector("span");
        if (amount >= threshold) {
          circle.classList.remove("ap-dashed", "border-gray-300", "dark:border-gray-600", "text-gray-400");
          circle.classList.add("text-blue-600", "dark:text-blue-400");
          circle.style.borderColor = "var(--ap-primary)";
          if (stage3Note) stage3Note.textContent = stage3Note.dataset.labelRequired || "Required";
        } else {
          circle.classList.add("ap-dashed", "border-gray-300", "dark:border-gray-600", "text-gray-400");
          circle.classList.remove("text-blue-600", "dark:text-blue-400");
          circle.style.borderColor = "";
          if (stage3Note) stage3Note.textContent = stage3NoteDefault;
        }
      }
    }

    if (amountInput) {
      amountInput.addEventListener("input", recalc);
      recalc();
    }
  }

  function initCashFlowChart() {
    var svg = document.getElementById("cash-flow-chart");
    var dataEl = document.getElementById("cash-flow-data");
    if (!svg || !dataEl) return;

    var data;
    try {
      data = JSON.parse(dataEl.textContent);
    } catch (e) {
      return;
    }
    var months = data.months || [];
    var max = data.max || 1;
    if (!months.length) return;

    var W = 260, H = 160, padB = 18, padT = 4;
    var plotH = H - padT - padB;
    var groupW = W / months.length;
    var barW = Math.min(14, groupW / 3);

    var ns = "http://www.w3.org/2000/svg";
    function el(tag, attrs) {
      var e = document.createElementNS(ns, tag);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      return e;
    }

    var successColor = getComputedStyle(document.documentElement).getPropertyValue("--ap-success").trim() || "#4ade80";
    var dangerColor = getComputedStyle(document.documentElement).getPropertyValue("--ap-danger").trim() || "#f87171";

    svg.innerHTML = "";
    svg.appendChild(el("line", { x1: 0, y1: H - padB, x2: W, y2: H - padB, stroke: "#cbd5e1", "stroke-width": 1 }));

    months.forEach(function (m, i) {
      var cx = groupW * i + groupW / 2;
      var incH = max ? (m.income / max) * plotH : 0;
      var expH = max ? (m.expense / max) * plotH : 0;

      svg.appendChild(el("rect", {
        x: cx - barW - 1, y: H - padB - incH, width: barW, height: Math.max(incH, 1),
        rx: 2, fill: successColor,
      }));
      svg.appendChild(el("rect", {
        x: cx + 1, y: H - padB - expH, width: barW, height: Math.max(expH, 1),
        rx: 2, fill: dangerColor,
      }));

      var label = el("text", {
        x: cx, y: H - 4, "text-anchor": "middle", "font-size": 9, fill: "#94a3b8",
      });
      label.textContent = m.label;
      svg.appendChild(label);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initModals();
    initPaymentRequestModal();
    initCashFlowChart();
  });
})();
