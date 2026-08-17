(function () {
  function digitsOnly(value) {
    return (value || "").replace(/\D/g, "");
  }

  function formatWithSpaces(digits) {
    return digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function handleInput(event) {
    var el = event.target;
    var caretFromEnd = el.value.length - el.selectionStart;
    var digits = digitsOnly(el.value);
    el.value = formatWithSpaces(digits);
    var pos = el.value.length - caretFromEnd;
    el.setSelectionRange(pos, pos);
  }

  function stripSpaces(form) {
    form.querySelectorAll("[data-money-input]").forEach(function (el) {
      el.value = digitsOnly(el.value);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var inputs = document.querySelectorAll("[data-money-input]");
    inputs.forEach(function (el) {
      if (el.value) el.value = formatWithSpaces(digitsOnly(el.value));
      el.addEventListener("input", handleInput);
      var form = el.closest("form");
      if (form && !form.dataset.moneyInputBound) {
        form.dataset.moneyInputBound = "true";
        form.addEventListener("submit", function () {
          stripSpaces(form);
        });
      }
    });
  });
})();
