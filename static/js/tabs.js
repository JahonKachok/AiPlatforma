/* Oddiy tab almashtirgich: [data-tabs] ichidagi [data-tab] tugmalar
   sahifadagi [data-tab-panel] bloklarni ko'rsatadi/yashiradi.
   Tanlangan tab URL hash'ida saqlanadi (forma yuborilgach qaytishda qulay). */
(function () {
  var bar = document.querySelector("[data-tabs]");
  if (!bar) return;
  var buttons = bar.querySelectorAll("[data-tab]");
  var panels = document.querySelectorAll("[data-tab-panel]");

  function activate(name) {
    buttons.forEach(function (b) {
      b.classList.toggle("is-active", b.dataset.tab === name);
    });
    panels.forEach(function (p) {
      p.classList.toggle("hidden", p.dataset.tabPanel !== name);
    });
  }

  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      activate(b.dataset.tab);
      history.replaceState(null, "", "#tab-" + b.dataset.tab);
    });
  });

  var fromHash = (location.hash || "").replace("#tab-", "");
  if (fromHash && bar.querySelector('[data-tab="' + fromHash + '"]')) {
    activate(fromHash);
  }
})();
