/* Lightweight chart renderer — no external libraries.
   [data-donut]  : element with data-segments='[{"color":"#hex","value":N}, ...]'
                   painted as a conic-gradient ring.
   [data-bar-to] : bar fill animated to the given percentage on load. */
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-donut]").forEach(function (el) {
    var segments;
    try { segments = JSON.parse(el.dataset.segments || "[]"); } catch (e) { return; }
    var total = segments.reduce(function (sum, s) { return sum + s.value; }, 0);
    if (!total) return;
    var stops = [];
    var acc = 0;
    segments.forEach(function (s) {
      if (!s.value) return;
      var from = (acc / total) * 360;
      acc += s.value;
      var to = (acc / total) * 360;
      stops.push(s.color + " " + from + "deg " + to + "deg");
    });
    el.style.background = "conic-gradient(" + stops.join(", ") + ")";
  });

  document.querySelectorAll("[data-bar-to]").forEach(function (bar) {
    var pct = parseFloat(bar.dataset.barTo) || 0;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { bar.style.width = pct + "%"; });
    });
  });
});
