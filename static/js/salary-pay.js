/* BuildFlow — "Give salary" modal.
   Currency toggle, live UZS<->USD conversion, summary and client-side guards.
   Everything here is convenience only: apps/finance/views.employee_contract_pay
   re-validates the contract, the balance and the rate server-side. */
(function () {
  "use strict";

  var form = document.getElementById("fin-pay-form");
  if (!form) return;

  function readJSON(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try { return JSON.parse(el.textContent); } catch (e) { return fallback; }
  }

  var CONTRACTS = readJSON("fin-pay-contracts", {});
  var ACCOUNT_CUR = readJSON("fin-account-currencies", {});
  var RATE = (readJSON("fin-pay-meta", {}) || {}).rate || 0;

  // Scope field lookups to this form: the transaction modal on the same page
  // renders its own field with id="id_account", so getElementById would hit it.
  var select = form.querySelector('[name="employee_contract"]');
  var accountSelect = form.querySelector('[name="account"]');
  var uzsInput = document.getElementById("fin-pay-uzs");
  var usdInput = document.getElementById("fin-pay-usd");
  var hidden = document.getElementById("fin-pay-amount");
  var submit = document.getElementById("fin-pay-submit");
  var errorEl = document.getElementById("fin-pay-error");
  var infoEl = document.getElementById("fin-pay-info");
  var balanceEl = document.getElementById("fin-pay-balance");
  var balanceAltEl = document.getElementById("fin-pay-balance-alt");
  var summaryEl = document.getElementById("fin-pay-summary");
  var sumBefore = document.getElementById("fin-sum-before");
  var sumAmount = document.getElementById("fin-sum-amount");
  var sumAfter = document.getElementById("fin-sum-after");
  var options = Array.prototype.slice.call(document.querySelectorAll(".fin-curr-opt"));

  var currency = "UZS";      // selected payment currency
  var contract = null;       // {balance, currency, ...}

  var T = {
    exceeds: form.getAttribute("data-msg-exceeds") || "Сумма выплаты превышает остаток к выплате.",
    noRate: form.getAttribute("data-msg-norate") || "Не удалось получить текущий курс доллара.",
    available: form.getAttribute("data-msg-available") || "Доступно",
    entered: form.getAttribute("data-msg-entered") || "Введено",
  };

  /* ---------- formatting ---------- */
  function groupInt(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }
  function fmtUZS(v) {
    return groupInt(Math.round(Number(v) || 0)) + " UZS";
  }
  function fmtUSD(v) {
    var n = Number(v) || 0;
    var parts = n.toFixed(2).split(".");
    return groupInt(parts[0]) + "." + parts[1] + " USD";
  }
  function fmtIn(v, cur) { return cur === "USD" ? fmtUSD(v) : fmtUZS(v); }

  function parseNum(raw) {
    if (raw == null) return NaN;
    // Accept "12 700 000", "12700000", "500.50", "500,50"
    var cleaned = String(raw).replace(/[\s ]/g, "").replace(",", ".");
    if (cleaned === "") return NaN;
    if (!/^\d*\.?\d*$/.test(cleaned)) return NaN;
    return parseFloat(cleaned);
  }

  /* ---------- conversion ---------- */
  function toUZS(v) { return v * RATE; }
  function toUSD(v) { return RATE ? v / RATE : NaN; }

  // Value in the contract's own currency, which is what the balance moves by.
  function inContractCurrency(value, cur) {
    if (!contract) return NaN;
    if (cur === contract.currency) return value;
    if (cur === "USD" && contract.currency === "UZS") return toUZS(value);
    if (cur === "UZS" && contract.currency === "USD") return toUSD(value);
    return NaN;
  }

  /* ---------- state ---------- */
  function currentAmount() {
    return parseNum(currency === "USD" ? usdInput.value : uzsInput.value);
  }

  function syncMirror() {
    var v = currentAmount();
    if (isNaN(v)) {
      (currency === "USD" ? uzsInput : usdInput).value = "";
      return;
    }
    if (currency === "USD") {
      uzsInput.value = RATE ? groupInt(Math.round(toUZS(v))) : "";
    } else {
      usdInput.value = RATE ? toUSD(v).toFixed(2) : "";
    }
  }

  function setError(msg) {
    if (!errorEl) return;
    if (msg) {
      errorEl.textContent = msg;
      errorEl.hidden = false;
    } else {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
  }

  function refresh() {
    var v = currentAmount();
    var valid = true;
    var msg = "";

    if (!contract) {
      valid = false;
    } else if (currency !== contract.currency && !RATE) {
      valid = false;
      msg = T.noRate;
    } else if (isNaN(v) || v <= 0) {
      valid = false;
    } else {
      var applied = inContractCurrency(v, currency);
      if (isNaN(applied)) {
        valid = false;
        msg = T.noRate;
      } else if (applied > contract.balance + 0.005) {
        valid = false;
        msg = T.exceeds + "  " + T.available + ": " + fmtIn(contract.balance, contract.currency) +
              " · " + T.entered + ": " + fmtIn(applied, contract.currency);
      }
    }

    setError(msg);
    if (submit) submit.disabled = !valid;

    // Summary
    if (contract && !isNaN(v) && v > 0 && !msg) {
      var applied2 = inContractCurrency(v, currency);
      summaryEl.hidden = false;
      sumBefore.textContent = fmtIn(contract.balance, contract.currency);
      sumAmount.textContent = currency === contract.currency
        ? fmtIn(v, currency)
        : fmtIn(v, currency) + "  =  " + fmtIn(applied2, contract.currency);
      sumAfter.textContent = fmtIn(contract.balance - applied2, contract.currency);
    } else if (summaryEl) {
      summaryEl.hidden = true;
    }

    // Post the amount in the selected currency, unformatted.
    if (hidden) hidden.value = isNaN(v) ? "" : String(v);
  }

  /* ---------- contract selection ---------- */
  function onContractChange() {
    var id = select ? select.value : "";
    contract = CONTRACTS[id] || null;
    if (infoEl) infoEl.hidden = !contract;
    if (contract) {
      balanceEl.textContent = fmtIn(contract.balance, contract.currency);
      if (balanceAltEl) {
        if (contract.currency === "UZS" && RATE) {
          balanceAltEl.textContent = "≈ " + fmtUSD(toUSD(contract.balance));
        } else if (contract.currency === "USD" && RATE) {
          balanceAltEl.textContent = "≈ " + fmtUZS(toUZS(contract.balance));
        } else {
          balanceAltEl.textContent = "";
        }
      }
    }
    refresh();
  }

  /* ---------- currency toggle ---------- */
  function selectCurrency(next, keepValue) {
    var previous = currency;
    currency = next;

    options.forEach(function (opt) {
      var on = opt.getAttribute("data-currency") === next;
      opt.classList.toggle("is-active", on);
      var radio = opt.querySelector("input");
      if (radio) radio.checked = on;
    });

    form.querySelectorAll(".fin-amount-side").forEach(function (side) {
      side.classList.toggle("is-primary", side.getAttribute("data-side") === next);
    });
    uzsInput.readOnly = next !== "UZS";
    usdInput.readOnly = next !== "USD";

    // Switching currency keeps the money the user already typed (spec 25):
    // the mirrored field becomes the input, so its value is already correct.
    if (!keepValue && previous !== next) {
      var mirrored = parseNum(next === "USD" ? usdInput.value : uzsInput.value);
      if (!isNaN(mirrored)) {
        (next === "USD" ? usdInput : uzsInput).value =
          next === "USD" ? mirrored.toFixed(2) : groupInt(Math.round(mirrored));
      }
    }

    filterAccounts();
    syncMirror();
    refresh();
  }

  // Only accounts held in the chosen currency may be picked.
  function filterAccounts() {
    if (!accountSelect) return;
    var firstMatch = null;
    Array.prototype.forEach.call(accountSelect.options, function (opt) {
      if (!opt.value) return;
      var match = ACCOUNT_CUR[opt.value] === currency;
      opt.hidden = !match;
      opt.disabled = !match;
      if (match && firstMatch === null) firstMatch = opt.value;
    });
    var chosen = accountSelect.options[accountSelect.selectedIndex];
    if (!chosen || chosen.disabled || !chosen.value) accountSelect.value = firstMatch || "";
  }

  /* ---------- input guards ---------- */
  function bindInput(input, cur) {
    input.addEventListener("input", function () {
      if (input.readOnly) return;
      var raw = input.value;
      // UZS is whole som; USD allows two decimals.
      var cleaned = cur === "USD"
        ? raw.replace(/[^\d.,]/g, "").replace(",", ".")
        : raw.replace(/[^\d\s ]/g, "");
      if (cur === "USD") {
        var bits = cleaned.split(".");
        if (bits.length > 2) cleaned = bits[0] + "." + bits.slice(1).join("");
        var d = cleaned.split(".");
        if (d[1] && d[1].length > 2) cleaned = d[0] + "." + d[1].slice(0, 2);
      } else {
        var digits = cleaned.replace(/[\s ]/g, "");
        cleaned = digits ? groupInt(digits.replace(/^0+(?=\d)/, "")) : "";
      }
      if (cleaned !== raw) {
        input.value = cleaned;
      }
      syncMirror();
      refresh();
    });
  }

  bindInput(uzsInput, "UZS");
  bindInput(usdInput, "USD");

  options.forEach(function (opt) {
    opt.addEventListener("click", function () {
      selectCurrency(opt.getAttribute("data-currency"), false);
    });
    var radio = opt.querySelector("input");
    if (radio) {
      radio.addEventListener("change", function () {
        if (radio.checked) selectCurrency(opt.getAttribute("data-currency"), false);
      });
    }
  });

  if (select) select.addEventListener("change", onContractChange);

  form.addEventListener("submit", function (e) {
    refresh();
    if (submit && submit.disabled) {
      e.preventDefault();
      return;
    }
    submit.disabled = true;                       // no double submit
    submit.classList.add("is-loading");
  });

  // Re-seed each time the dialog opens (a row action may preselect a contract).
  var modal = document.getElementById("employee-contract-pay-modal");
  if (modal) {
    modal.addEventListener("ap-modal-opened", function () {
      // finance.js sets the select from data-contract-id on the same event;
      // defer so we read the value after it has been applied.
      setTimeout(function () {
        if (submit) { submit.disabled = false; submit.classList.remove("is-loading"); }
        selectCurrency("UZS", true);
        uzsInput.value = "";
        usdInput.value = "";
        onContractChange();
      }, 0);
    });
  }

  selectCurrency("UZS", true);
  onContractChange();
})();
