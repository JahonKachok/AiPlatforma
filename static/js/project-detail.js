/* Project overview: progress ring, bar fills and the progress-mode switch.
   No values are computed here — every number is rendered by Django and read
   back off the DOM, so the ring, the mini cards and the statistics card can
   never disagree. The switch only picks which of the two figures the project
   already has (tasks completed / weighted disciplines) the ring shows. */
(function () {
  "use strict";

  var root = document.getElementById("pd-progress");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- bar fills (progress rows + finance) ---------- */
  var bars = document.querySelectorAll("[data-bar]");
  function fillBars() {
    bars.forEach(function (bar) {
      var pct = parseFloat(bar.getAttribute("data-bar"));
      if (isNaN(pct)) pct = 0;
      bar.style.width = Math.max(0, Math.min(100, pct)) + "%";
    });
  }
  if (reduced) {
    fillBars();
  } else {
    bars.forEach(function (bar) { bar.style.width = "0%"; });
    requestAnimationFrame(function () { requestAnimationFrame(fillBars); });
  }

  if (!root) return;

  /* ---------- ring ---------- */
  var ring = root.querySelector("[data-ring]");
  var valueEl = root.querySelector("[data-ring-value]");
  var captionEl = root.querySelector("[data-ring-caption]");
  var button = root.querySelector("[data-progress-mode]");
  var labelEl = root.querySelector("[data-progress-mode-label]");
  if (!ring || !valueEl) return;

  var CIRC = 2 * Math.PI * 64; // r=64 in the SVG viewBox
  ring.setAttribute("stroke-dasharray", CIRC.toFixed(2));

  function readPct(name) {
    var raw = root.getAttribute("data-" + name + "-pct");
    if (raw === null || raw === "") return null;
    var n = parseFloat(raw);
    return isNaN(n) ? null : Math.max(0, Math.min(100, n));
  }

  var modes = [
    { key: "tasks", pct: readPct("tasks") },
    { key: "sections", pct: readPct("sections") }
  ].filter(function (m) { return m.pct !== null; });

  if (!modes.length) {
    ring.setAttribute("stroke-dashoffset", CIRC.toFixed(2));
    valueEl.textContent = "0%";
    if (button) button.disabled = true;
    return;
  }

  var index = 0;
  var countTimer = null;

  function labelFor(key) {
    if (!button) return "";
    return button.getAttribute("data-label-" + key) || "";
  }

  function countTo(target) {
    if (countTimer) { cancelAnimationFrame(countTimer); countTimer = null; }
    if (reduced) { valueEl.textContent = Math.round(target) + "%"; return; }
    var from = parseFloat(valueEl.textContent) || 0;
    var start = null;
    var duration = 900;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      valueEl.textContent = Math.round(from + (target - from) * eased) + "%";
      if (t < 1) countTimer = requestAnimationFrame(step);
    }
    countTimer = requestAnimationFrame(step);
  }

  function render() {
    var mode = modes[index];
    var offset = CIRC * (1 - mode.pct / 100);
    ring.setAttribute("stroke-dashoffset", offset.toFixed(2));
    countTo(mode.pct);
    var label = labelFor(mode.key);
    if (captionEl && label) captionEl.textContent = label;
    if (labelEl && label) labelEl.textContent = label;
  }

  if (button) {
    if (modes.length < 2) {
      button.disabled = true;
    } else {
      button.addEventListener("click", function () {
        index = (index + 1) % modes.length;
        render();
      });
    }
  }

  if (reduced) {
    render();
  } else {
    // Let the browser paint the empty ring first so the sweep is visible.
    requestAnimationFrame(function () { requestAnimationFrame(render); });
  }
})();
