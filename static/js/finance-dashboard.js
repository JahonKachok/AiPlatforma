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
      var last = points.length - 1;
      points.forEach(function (p, i) {
        if (i % every !== 0 && i !== last) return;
        // Drop a regular tick that would collide with the always-drawn last one.
        if (i !== last && last - i < every * 0.6) return;
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

  /* ---------- Dropdowns (header "Add operation" + per-row action menus) ---------- */
  function initDropdowns() {
    var roots = document.querySelectorAll(".fin-dd");
    if (!roots.length) return;

    function closeAll(except) {
      Array.prototype.forEach.call(roots, function (r) {
        if (r === except) return;
        var m = r.querySelector(".fin-dd-menu");
        var b = r.querySelector("[data-dd-toggle]");
        if (m) m.setAttribute("data-open", "false");
        if (b) b.setAttribute("aria-expanded", "false");
      });
    }

    Array.prototype.forEach.call(roots, function (root) {
      var btn = root.querySelector("[data-dd-toggle]");
      var menu = root.querySelector(".fin-dd-menu");
      if (!btn || !menu) return;

      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var isOpen = menu.getAttribute("data-open") === "true";
        closeAll(root);
        menu.setAttribute("data-open", isOpen ? "false" : "true");
        btn.setAttribute("aria-expanded", isOpen ? "false" : "true");
      });
      // Items open modals or submit forms — the click must still reach them.
      menu.addEventListener("click", function () {
        menu.setAttribute("data-open", "false");
        btn.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", function (e) {
      var inside = e.target.closest && e.target.closest(".fin-dd");
      closeAll(inside);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAll(null);
    });
  }

  /* ---------- Confirmation dialog for destructive forms ---------- */
  function initConfirm() {
    var modal = document.getElementById("fin-confirm-modal");
    var textEl = document.getElementById("fin-confirm-text");
    var okBtn = document.getElementById("fin-confirm-ok");
    if (!modal || !okBtn) return;
    var pending = null;

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (form.dataset.confirmed === "yes") return;   // second pass, let it through
        e.preventDefault();
        pending = form;
        if (textEl) textEl.textContent = form.getAttribute("data-confirm");
        modal.classList.add("is-open");
        okBtn.focus();
      });
    });

    okBtn.addEventListener("click", function () {
      if (!pending) return;
      pending.dataset.confirmed = "yes";
      modal.classList.remove("is-open");
      pending.submit();
      pending = null;
    });
    modal.addEventListener("click", function (e) { if (e.target === modal) pending = null; });
  }

  /* ---------- Payroll: completion ring, donut, progress bars ---------- */
  function initRings() {
    document.querySelectorAll("[data-ring]").forEach(function (el) {
      var pct = Math.max(0, Math.min(100, parseFloat(el.getAttribute("data-ring")) || 0));
      if (reduceMotion) { el.style.setProperty("--p", pct); return; }
      el.style.setProperty("--p", 0);
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { el.style.setProperty("--p", pct); });
      });
    });
  }

  function initDonut() {
    var ring = document.getElementById("fin-donut-ring");
    if (!ring) return;
    var slices = readJSON("fin-donut-data", []);
    if (!slices.length) return;

    var acc = 0;
    var stops = slices.map(function (s) {
      var from = acc;
      acc += s.pct;
      return s.color + " " + from + "% " + acc + "%";
    });
    // Guard against float drift leaving a sliver of track visible.
    if (acc < 100 && stops.length) {
      stops[stops.length - 1] = slices[slices.length - 1].color + " " +
        (acc - slices[slices.length - 1].pct) + "% 100%";
    }
    var gradient = "conic-gradient(" + stops.join(", ") + ")";
    if (reduceMotion) { ring.style.background = gradient; return; }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { ring.style.background = gradient; });
    });
  }

  function initBars() {
    document.querySelectorAll("[data-bar-pct]").forEach(function (bar) {
      var pct = Math.max(0, Math.min(100, parseFloat(bar.getAttribute("data-bar-pct")) || 0));
      if (reduceMotion) { bar.style.width = pct + "%"; return; }
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { bar.style.width = pct + "%"; });
      });
    });
  }

  /* ---------- Payroll: dependent filter selects ---------- */
  function initPayrollFilters() {
    var form = document.getElementById("payroll-filters");
    if (!form) return;
    var project = document.getElementById("payroll-project");
    var object = document.getElementById("payroll-object");
    var pod = document.getElementById("payroll-pod");
    if (!project || !object || !pod) return;

    function apply() {
      var projectId = project.value;
      Array.prototype.forEach.call(object.options, function (opt) {
        if (!opt.value) return;
        opt.hidden = !!projectId && opt.getAttribute("data-project") !== projectId;
      });
      if (object.selectedOptions[0] && object.selectedOptions[0].hidden) object.value = "";

      var objectId = object.value;
      Array.prototype.forEach.call(pod.options, function (opt) {
        if (!opt.value) return;
        var okProject = !projectId || opt.getAttribute("data-project") === projectId;
        var okParent = !objectId || opt.getAttribute("data-parent") === objectId;
        opt.hidden = !(okProject && okParent);
      });
      if (pod.selectedOptions[0] && pod.selectedOptions[0].hidden) pod.value = "";
    }

    // Narrow the lists on load and whenever the parent choice changes. The form
    // auto-submits on change, so this mainly shapes the options the user sees.
    project.addEventListener("change", apply);
    object.addEventListener("change", apply);
    apply();
  }

  /* ---------- Payroll: 3-series chart ---------- */
  function initPayrollChart() {
    var host = document.getElementById("fin-payroll-chart");
    if (!host) return;
    var points = readJSON("fin-payroll-data", []);
    if (!points.length) return;

    var tip = document.getElementById("fin-payroll-tip");
    UNITS.bn = host.getAttribute("data-unit-bn") || UNITS.bn;
    UNITS.mn = host.getAttribute("data-unit-mn") || UNITS.mn;
    UNITS.k = host.getAttribute("data-unit-k") || UNITS.k;

    var SERIES = [
      { key: "remaining", color: "var(--fin-amber)", grad: "fin-pg-remaining", width: 1.5 },
      { key: "paid", color: "var(--fin-green)", grad: "fin-pg-paid", width: 2 },
      { key: "accrued", color: "var(--fin-accent)", grad: "fin-pg-accrued", width: 2 },
    ];
    var geom = null;

    function draw() {
      var rect = host.getBoundingClientRect();
      var w = Math.max(320, rect.width);
      var h = Math.max(200, rect.height);
      var padL = 58, padR = 16, padT = 16, padB = 28;
      var innerW = w - padL - padR, innerH = h - padT - padB;

      var maxVal = 0;
      points.forEach(function (p) {
        SERIES.forEach(function (s) { maxVal = Math.max(maxVal, p[s.key] || 0); });
      });
      var top = niceCeil(maxVal || 1);

      function xAt(i) { return points.length === 1 ? padL + innerW / 2 : padL + (i / (points.length - 1)) * innerW; }
      function yAt(v) { return padT + (1 - (v || 0) / top) * innerH; }

      var svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, role: "img" });
      svg.setAttribute("aria-label", host.getAttribute("data-a11y-label") || "");

      var defs = svgEl("defs", {});
      SERIES.forEach(function (s) {
        var g = svgEl("linearGradient", { id: s.grad, x1: "0", y1: "0", x2: "0", y2: "1" });
        g.appendChild(svgEl("stop", { offset: "0%", "stop-color": s.color, "stop-opacity": "0.20" }));
        g.appendChild(svgEl("stop", { offset: "100%", "stop-color": s.color, "stop-opacity": "0" }));
        defs.appendChild(g);
      });
      svg.appendChild(defs);

      for (var st = 0; st <= 4; st++) {
        var val = (top / 4) * st, y = yAt(val);
        svg.appendChild(svgEl("line", { x1: padL, y1: y, x2: w - padR, y2: y, class: "fin-grid-line" }));
        var lab = svgEl("text", { x: padL - 10, y: y + 3, class: "fin-axis-text", "text-anchor": "end" });
        lab.textContent = val === 0 ? "0" : shortNum(val);
        svg.appendChild(lab);
      }

      var maxLabels = Math.max(2, Math.floor(innerW / 62));
      var every = Math.ceil(points.length / maxLabels);
      var last = points.length - 1;
      points.forEach(function (p, i) {
        if (i % every !== 0 && i !== last) return;
        // Drop a regular tick that would collide with the always-drawn last one.
        if (i !== last && last - i < every * 0.6) return;
        var t = svgEl("text", { x: xAt(i), y: h - 8, class: "fin-axis-text", "text-anchor": "middle" });
        t.textContent = p.label;
        svg.appendChild(t);
      });

      var seriesPts = {};
      SERIES.forEach(function (s) {
        var pts = points.map(function (p, i) { return { x: xAt(i), y: yAt(p[s.key]) }; });
        seriesPts[s.key] = pts;

        if (pts.length === 1) {
          svg.appendChild(svgEl("circle", { cx: pts[0].x, cy: pts[0].y, r: "4.5", fill: s.color, class: "fin-area" }));
          return;
        }
        var line = smoothPath(pts);
        svg.appendChild(svgEl("path", {
          d: line + " L" + pts[pts.length - 1].x + "," + (padT + innerH) + " L" + pts[0].x + "," + (padT + innerH) + " Z",
          fill: "url(#" + s.grad + ")", stroke: "none", class: "fin-area"
        }));
        var path = svgEl("path", {
          d: line, fill: "none", stroke: s.color, "stroke-width": s.width,
          "stroke-linecap": "round", "stroke-linejoin": "round"
        });
        svg.appendChild(path);
        if (!reduceMotion && path.getTotalLength) {
          try {
            path.style.setProperty("--len", path.getTotalLength());
            path.classList.add("fin-line-draw");
          } catch (e) { /* skip the flourish */ }
        }
      });

      var hover = svgEl("g", { opacity: "0" });
      var hLine = svgEl("line", { y1: padT, y2: padT + innerH, class: "fin-hover-line" });
      hover.appendChild(hLine);
      var dots = {};
      SERIES.forEach(function (s) {
        dots[s.key] = svgEl("circle", { r: "4", fill: s.color, class: "fin-hover-dot" });
        hover.appendChild(dots[s.key]);
      });
      svg.appendChild(hover);
      svg.appendChild(svgEl("rect", {
        x: padL, y: padT, width: innerW, height: innerH, fill: "transparent", style: "cursor:crosshair"
      }));

      host.innerHTML = "";
      host.appendChild(svg);
      geom = { xAt: xAt, seriesPts: seriesPts, hover: hover, hLine: hLine, dots: dots };
    }

    function nearestIndex(clientX) {
      if (!geom) return -1;
      var svg = host.querySelector("svg");
      if (!svg) return -1;
      var rect = host.getBoundingClientRect();
      var scale = rect.width ? svg.viewBox.baseVal.width / rect.width : 1;
      var x = (clientX - rect.left) * scale;
      var best = -1, bestDist = Infinity;
      for (var i = 0; i < points.length; i++) {
        var d = Math.abs(geom.xAt(i) - x);
        if (d < bestDist) { bestDist = d; best = i; }
      }
      return best;
    }

    host.addEventListener("mousemove", function (e) {
      var i = nearestIndex(e.clientX);
      if (!geom || i < 0 || !tip) return;
      var p = points[i];
      geom.hover.setAttribute("opacity", "1");
      geom.hLine.setAttribute("x1", geom.xAt(i));
      geom.hLine.setAttribute("x2", geom.xAt(i));
      SERIES.forEach(function (s) {
        geom.dots[s.key].setAttribute("cx", geom.seriesPts[s.key][i].x);
        geom.dots[s.key].setAttribute("cy", geom.seriesPts[s.key][i].y);
      });
      tip.querySelector("[data-tip-label]").textContent = p.label;
      tip.querySelector("[data-tip-accrued]").textContent = fmt(p.accrued);
      tip.querySelector("[data-tip-paid]").textContent = fmt(p.paid);
      tip.querySelector("[data-tip-remaining]").textContent = fmt(p.remaining);
      tip.setAttribute("data-open", "true");

      var hostRect = host.getBoundingClientRect();
      var tipRect = tip.getBoundingClientRect();
      var left = e.clientX - hostRect.left + 14;
      if (left + tipRect.width > hostRect.width) left = e.clientX - hostRect.left - tipRect.width - 14;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = "12px";
    });
    host.addEventListener("mouseleave", function () {
      if (geom) geom.hover.setAttribute("opacity", "0");
      if (tip) tip.setAttribute("data-open", "false");
    });

    draw();
    var timer;
    window.addEventListener("resize", function () {
      clearTimeout(timer);
      timer = setTimeout(draw, 150);
    });

    // KPI sparklines reuse the same series rather than querying again.
    document.querySelectorAll("[data-spark-key]").forEach(function (el) {
      var key = el.getAttribute("data-spark-key");
      el.setAttribute("data-spark", JSON.stringify(points.map(function (p) { return p[key]; })));
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
    renderChart();
    initPayrollChart();   // fills [data-spark] for the payroll KPIs...
    renderSparklines();   // ...so this must come after it
    initDropdowns();
    initConfirm();
    initProjectToggle();
    initMeter();
    initRings();
    initDonut();
    initBars();
    initPayrollFilters();
  });
})();
