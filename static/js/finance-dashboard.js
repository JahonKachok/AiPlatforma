/* BuildFlow — Finance / General dashboard interactions.
   Pure DOM + inline SVG, no chart library: the app already ships its own
   lightweight renderer (static/js/charts.js) and we keep that constraint.
   All values come from JSON emitted server-side via {{ ... |json_script }}. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function readJSON(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try { return JSON.parse(el.textContent); } catch (e) { return fallback; }
  }

  function fmt(n) {
    var rounded = Math.round(Number(n) || 0);
    return String(rounded).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  /* ---------- Count-up for the headline figures ---------- */
  function animateNumbers() {
    var nodes = document.querySelectorAll("[data-countup]");
    Array.prototype.forEach.call(nodes, function (node) {
      var target = parseFloat(node.getAttribute("data-countup"));
      if (isNaN(target)) return;
      if (reduceMotion || target === 0) { node.textContent = fmt(target); return; }

      var duration = 900;
      var start = performance.now();
      function step(now) {
        var t = Math.min(1, (now - start) / duration);
        var eased = 1 - Math.pow(1 - t, 3);
        node.textContent = fmt(target * eased);
        if (t < 1) requestAnimationFrame(step);
        else node.textContent = fmt(target);
      }
      requestAnimationFrame(step);
    });
  }

  /* ---------- Path helpers ---------- */
  function smoothPath(points) {
    // Monotone cubic Hermite (Fritsch-Carlson). Plain Catmull-Rom overshoots
    // around a spike, which would draw income dipping below zero — impossible
    // for this data. Monotone interpolation cannot overshoot the input values.
    var n = points.length;
    if (!n) return "";
    if (n < 3) {
      return points.map(function (p, i) { return (i ? "L" : "M") + p.x + "," + p.y; }).join(" ");
    }

    var dx = [], dy = [], delta = [], m = [], i;
    for (i = 0; i < n - 1; i++) {
      dx[i] = points[i + 1].x - points[i].x;
      dy[i] = points[i + 1].y - points[i].y;
      delta[i] = dx[i] ? dy[i] / dx[i] : 0;
    }

    m[0] = delta[0];
    for (i = 1; i < n - 1; i++) {
      if (delta[i - 1] * delta[i] <= 0) m[i] = 0;          // local extremum -> flat tangent
      else m[i] = (delta[i - 1] + delta[i]) / 2;
    }
    m[n - 1] = delta[n - 2];

    for (i = 0; i < n - 1; i++) {
      if (delta[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
      var a = m[i] / delta[i];
      var b = m[i + 1] / delta[i];
      var s = a * a + b * b;
      if (s > 9) {
        var tau = 3 / Math.sqrt(s);
        m[i] = tau * a * delta[i];
        m[i + 1] = tau * b * delta[i];
      }
    }

    var d = "M" + points[0].x + "," + points[0].y;
    for (i = 0; i < n - 1; i++) {
      var third = dx[i] / 3;
      d += " C" + (points[i].x + third) + "," + (points[i].y + m[i] * third) +
           " " + (points[i + 1].x - third) + "," + (points[i + 1].y - m[i + 1] * third) +
           " " + points[i + 1].x + "," + points[i + 1].y;
    }
    return d;
  }

  function svgEl(name, attrs) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    return el;
  }

  function niceCeil(value) {
    if (value <= 0) return 1;
    var mag = Math.pow(10, Math.floor(Math.log10(value)));
    var norm = value / mag;
    // Fine-grained steps so a 2.6 max lands on a 3.0 axis, not a half-empty 5.0.
    var steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
    for (var i = 0; i < steps.length; i++) {
      if (norm <= steps[i] + 1e-9) return steps[i] * mag;
    }
    return 10 * mag;
  }

  // Unit suffixes come from the template so they follow the active language.
  var UNITS = { bn: "bn", mn: "mn", k: "k" };

  function shortNum(v) {
    var abs = Math.abs(v);
    if (abs >= 1e9) return (v / 1e9).toFixed(abs >= 1e10 ? 0 : 1) + " " + UNITS.bn;
    if (abs >= 1e6) return (v / 1e6).toFixed(abs >= 1e7 ? 0 : 1) + " " + UNITS.mn;
    if (abs >= 1e3) return Math.round(v / 1e3) + " " + UNITS.k;
    return String(Math.round(v));
  }

  /* ---------- Sparklines (KPI cards) ---------- */
  function renderSparklines() {
    var hosts = document.querySelectorAll("[data-spark]");
    Array.prototype.forEach.call(hosts, function (host) {
      var series;
      try { series = JSON.parse(host.getAttribute("data-spark")); } catch (e) { return; }
      if (!series || series.length < 2) return;

      var w = 100, h = 34, pad = 3;
      var min = Math.min.apply(null, series);
      var max = Math.max.apply(null, series);
      var span = max - min || Math.abs(max) || 1;
      var stroke = host.getAttribute("data-spark-color") || "currentColor";

      var pts = series.map(function (v, i) {
        return {
          x: (i / (series.length - 1)) * w,
          y: pad + (1 - (v - min) / span) * (h - pad * 2)
        };
      });

      var svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, preserveAspectRatio: "none", "aria-hidden": "true", focusable: "false" });
      var uid = "spark-" + Math.random().toString(36).slice(2, 9);

      var grad = svgEl("linearGradient", { id: uid, x1: "0", y1: "0", x2: "0", y2: "1" });
      grad.appendChild(svgEl("stop", { offset: "0%", "stop-color": stroke, "stop-opacity": "0.28" }));
      grad.appendChild(svgEl("stop", { offset: "100%", "stop-color": stroke, "stop-opacity": "0" }));
      var defs = svgEl("defs", {});
      defs.appendChild(grad);
      svg.appendChild(defs);

      var line = smoothPath(pts);
      svg.appendChild(svgEl("path", {
        d: line + " L" + w + "," + h + " L0," + h + " Z",
        fill: "url(#" + uid + ")", stroke: "none"
      }));
      svg.appendChild(svgEl("path", {
        d: line, fill: "none", stroke: stroke, "stroke-width": "1.5",
        "stroke-linecap": "round", "stroke-linejoin": "round", "vector-effect": "non-scaling-stroke"
      }));

      host.innerHTML = "";
      host.appendChild(svg);
    });
  }

  /* ---------- Main income / expense chart ---------- */
  function renderChart() {
    var host = document.getElementById("fin-chart");
    if (!host) return;
    var points = readJSON("fin-chart-data", []);
    if (!points.length) return;

    var tip = document.getElementById("fin-chart-tip");
    var state = { pts: null, geom: null };

    UNITS.bn = host.getAttribute("data-unit-bn") || UNITS.bn;
    UNITS.mn = host.getAttribute("data-unit-mn") || UNITS.mn;
    UNITS.k = host.getAttribute("data-unit-k") || UNITS.k;

    function draw() {
      var rect = host.getBoundingClientRect();
      var w = Math.max(320, rect.width);
      var h = Math.max(200, rect.height);
      var padL = 58, padR = 16, padT = 16, padB = 28;
      var innerW = w - padL - padR;
      var innerH = h - padT - padB;

      var maxVal = 0;
      points.forEach(function (p) { maxVal = Math.max(maxVal, p.income, p.expense); });
      var top = niceCeil(maxVal || 1);

      function xAt(i) {
        return points.length === 1 ? padL + innerW / 2 : padL + (i / (points.length - 1)) * innerW;
      }
      function yAt(v) { return padT + (1 - v / top) * innerH; }

      var incomePts = points.map(function (p, i) { return { x: xAt(i), y: yAt(p.income) }; });
      var expensePts = points.map(function (p, i) { return { x: xAt(i), y: yAt(p.expense) }; });

      var svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, role: "img" });
      svg.setAttribute("aria-label", host.getAttribute("data-a11y-label") || "");

      var defs = svgEl("defs", {});
      [["fin-g-income", "var(--fin-green)"], ["fin-g-expense", "var(--fin-red)"]].forEach(function (pair) {
        var g = svgEl("linearGradient", { id: pair[0], x1: "0", y1: "0", x2: "0", y2: "1" });
        g.appendChild(svgEl("stop", { offset: "0%", "stop-color": pair[1], "stop-opacity": "0.22" }));
        g.appendChild(svgEl("stop", { offset: "100%", "stop-color": pair[1], "stop-opacity": "0" }));
        defs.appendChild(g);
      });
      svg.appendChild(defs);

      // Horizontal grid + value axis
      var steps = 4;
      for (var s = 0; s <= steps; s++) {
        var val = (top / steps) * s;
        var y = yAt(val);
        svg.appendChild(svgEl("line", { x1: padL, y1: y, x2: w - padR, y2: y, class: "fin-grid-line" }));
        var label = svgEl("text", { x: padL - 10, y: y + 3, class: "fin-axis-text", "text-anchor": "end" });
        label.textContent = val === 0 ? "0" : shortNum(val);
        svg.appendChild(label);
      }

      // Date axis — thin out labels so they never collide
      var maxLabels = Math.max(2, Math.floor(innerW / 62));
      var every = Math.ceil(points.length / maxLabels);
      points.forEach(function (p, i) {
        if (i % every !== 0 && i !== points.length - 1) return;
        var t = svgEl("text", { x: xAt(i), y: h - 8, class: "fin-axis-text", "text-anchor": "middle" });
        t.textContent = p.label;
        svg.appendChild(t);
      });

      function addSeries(pts, cls, gradId) {
        // A single bucket has no line to draw — mark the value with a dot instead.
        if (pts.length === 1) {
          var color = cls.indexOf("income") !== -1 ? "var(--fin-green)" : "var(--fin-red)";
          svg.appendChild(svgEl("circle", {
            cx: pts[0].x, cy: pts[0].y, r: "4.5", fill: color, class: "fin-area"
          }));
          return;
        }
        var line = smoothPath(pts);
        var area = svgEl("path", {
          d: line + " L" + pts[pts.length - 1].x + "," + (padT + innerH) + " L" + pts[0].x + "," + (padT + innerH) + " Z",
          fill: "url(#" + gradId + ")", stroke: "none", class: "fin-area"
        });
        svg.appendChild(area);
        var path = svgEl("path", { d: line, class: "fin-line " + cls });
        svg.appendChild(path);
        if (!reduceMotion && path.getTotalLength) {
          try {
            var len = path.getTotalLength();
            path.style.setProperty("--len", len);
            path.classList.add("fin-line-draw");
          } catch (e) { /* getTotalLength can throw on detached nodes — skip the flourish */ }
        }
      }

      addSeries(expensePts, "fin-line-expense", "fin-g-expense");
      addSeries(incomePts, "fin-line-income", "fin-g-income");

      // Hover layer
      var hover = svgEl("g", { opacity: "0" });
      var hLine = svgEl("line", { y1: padT, y2: padT + innerH, class: "fin-hover-line" });
      var dotI = svgEl("circle", { r: "4", fill: "var(--fin-green)", class: "fin-hover-dot" });
      var dotE = svgEl("circle", { r: "4", fill: "var(--fin-red)", class: "fin-hover-dot" });
      hover.appendChild(hLine); hover.appendChild(dotE); hover.appendChild(dotI);
      svg.appendChild(hover);

      var overlay = svgEl("rect", {
        x: padL, y: padT, width: innerW, height: innerH, fill: "transparent", style: "cursor:crosshair"
      });
      svg.appendChild(overlay);

      host.innerHTML = "";
      host.appendChild(svg);

      state.geom = { xAt: xAt, incomePts: incomePts, expensePts: expensePts, hover: hover, hLine: hLine, dotI: dotI, dotE: dotE, padL: padL, innerW: innerW };
    }

    function nearestIndex(clientX) {
      var g = state.geom;
      if (!g) return -1;
      var rect = host.getBoundingClientRect();
      var scale = rect.width ? (host.querySelector("svg").viewBox.baseVal.width / rect.width) : 1;
      var x = (clientX - rect.left) * scale;
      var best = -1, bestDist = Infinity;
      for (var i = 0; i < points.length; i++) {
        var d = Math.abs(g.xAt(i) - x);
        if (d < bestDist) { bestDist = d; best = i; }
      }
      return best;
    }

    function showTip(i, clientX) {
      var g = state.geom;
      if (!g || i < 0 || !tip) return;
      var p = points[i];
      g.hover.setAttribute("opacity", "1");
      g.hLine.setAttribute("x1", g.xAt(i));
      g.hLine.setAttribute("x2", g.xAt(i));
      g.dotI.setAttribute("cx", g.incomePts[i].x); g.dotI.setAttribute("cy", g.incomePts[i].y);
      g.dotE.setAttribute("cx", g.expensePts[i].x); g.dotE.setAttribute("cy", g.expensePts[i].y);

      tip.querySelector("[data-tip-label]").textContent = p.label;
      tip.querySelector("[data-tip-income]").textContent = fmt(p.income);
      tip.querySelector("[data-tip-expense]").textContent = fmt(p.expense);
      tip.setAttribute("data-open", "true");

      var hostRect = host.getBoundingClientRect();
      var tipRect = tip.getBoundingClientRect();
      var left = clientX - hostRect.left + 14;
      if (left + tipRect.width > hostRect.width) left = clientX - hostRect.left - tipRect.width - 14;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = "12px";
    }

    function hideTip() {
      if (state.geom) state.geom.hover.setAttribute("opacity", "0");
      if (tip) tip.setAttribute("data-open", "false");
    }

    host.addEventListener("mousemove", function (e) { showTip(nearestIndex(e.clientX), e.clientX); });
    host.addEventListener("mouseleave", hideTip);

    draw();

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { hideTip(); draw(); }, 150);
    });
  }

  /* ---------- "Add operation" dropdown ---------- */
  function initDropdown() {
    var root = document.getElementById("fin-add-dd");
    if (!root) return;
    var btn = root.querySelector("[data-dd-toggle]");
    var menu = root.querySelector(".fin-dd-menu");
    if (!btn || !menu) return;

    function open() {
      menu.setAttribute("data-open", "true");
      btn.setAttribute("aria-expanded", "true");
    }
    function close() {
      menu.setAttribute("data-open", "false");
      btn.setAttribute("aria-expanded", "false");
    }

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (menu.getAttribute("data-open") === "true") close(); else open();
    });
    // The menu items open modals, which need the click to reach the modal script.
    menu.addEventListener("click", function () { close(); });
    document.addEventListener("click", function (e) { if (!root.contains(e.target)) close(); });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || menu.getAttribute("data-open") !== "true") return;
      close();
      btn.focus();
    });
  }

  /* ---------- Show all projects ---------- */
  function initProjectToggle() {
    var btn = document.getElementById("fin-projects-more");
    if (!btn) return;
    var hidden = document.querySelectorAll("[data-project-extra]");
    if (!hidden.length) { btn.remove(); return; }

    btn.addEventListener("click", function () {
      var expanded = btn.getAttribute("aria-expanded") === "true";
      Array.prototype.forEach.call(hidden, function (row, i) {
        row.hidden = expanded;
        if (!expanded && !reduceMotion) {
          row.style.animation = "none";
          // Restart the rise animation for the rows that just appeared.
          void row.offsetWidth;
          row.style.animation = "fin-rise .4s cubic-bezier(0.22,1,0.36,1) " + Math.min(i * 25, 200) + "ms both";
        }
      });
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      btn.querySelector("[data-more-label]").textContent =
        expanded ? btn.getAttribute("data-label-more") : btn.getAttribute("data-label-less");
    });
  }

  /* ---------- Budget meter ---------- */
  function initMeter() {
    var fill = document.querySelector("[data-meter-to]");
    if (!fill) return;
    var pct = Math.max(0, Math.min(100, parseFloat(fill.getAttribute("data-meter-to")) || 0));
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { fill.style.width = pct + "%"; });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var scope = document.querySelector(".fin-scope");
    if (scope) scope.classList.add("fin-ready");
    animateNumbers();
    renderSparklines();
    renderChart();
    initDropdown();
    initProjectToggle();
    initMeter();
  });
})();
