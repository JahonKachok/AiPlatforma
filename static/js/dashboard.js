/* BuildFlow — dashboard entrance animation, KPI count-up and progress fills.
 *
 * Everything here is first-paint only: it runs once, animates from a neutral
 * start value to the real value already present in the markup, and then does
 * nothing. There is no polling and no re-render — without JS the page still
 * shows every final figure, because the numbers are rendered server-side and
 * only overwritten while the count-up is in flight.
 *
 * Only `transform`, `opacity` and the conic-gradient/width of the progress
 * indicators change, so the work stays on the compositor.
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function animate(duration, onStep) {
    var start = null;
    function frame(timestamp) {
      if (start === null) start = timestamp;
      var t = Math.min(1, (timestamp - start) / duration);
      // easeOutCubic — quick to start, settles gently.
      onStep(1 - Math.pow(1 - t, 3), t === 1);
      if (t < 1) window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  /* ------------------------- Staggered entrance ------------------------- */

  function reveal() {
    var items = document.querySelectorAll(".dsh-reveal");
    if (!items.length) return;
    if (reduceMotion.matches) return; // markup is already in its final state

    Array.prototype.forEach.call(items, function (el, index) {
      // Order comes from data-dsh-order so the sequence is header → KPIs →
      // main content → AI/activity regardless of DOM order.
      var order = parseInt(el.getAttribute("data-dsh-order") || index, 10);
      el.style.setProperty("--dsh-delay", Math.min(order * 45, 360) + "ms");
      el.classList.add("is-armed");
    });

    // Two frames: one to apply `is-armed`, one to flip to `is-in` so the
    // transition actually runs instead of being collapsed into the initial paint.
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        Array.prototype.forEach.call(items, function (el) {
          el.classList.add("is-in");
        });
      });
    });
  }

  /* --------------------------- KPI count-up ---------------------------- */

  function countUp() {
    var values = document.querySelectorAll("[data-dsh-count]");
    Array.prototype.forEach.call(values, function (el) {
      var target = parseInt(el.getAttribute("data-dsh-count"), 10);
      if (isNaN(target)) return;
      if (reduceMotion.matches || target === 0) {
        el.textContent = String(target);
        return;
      }
      el.textContent = "0";
      animate(750, function (eased, done) {
        el.textContent = done ? String(target) : String(Math.round(target * eased));
      });
    });
  }

  /* ------------------- Progress bars and circular rings ------------------- */

  function fillProgress() {
    var bars = document.querySelectorAll("[data-dsh-bar]");
    Array.prototype.forEach.call(bars, function (el) {
      var pct = parseFloat(el.getAttribute("data-dsh-bar")) || 0;
      if (reduceMotion.matches) {
        el.style.width = pct + "%";
        return;
      }
      // The CSS transition on width does the work; one frame of delay lets the
      // browser register the 0% starting point first.
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () { el.style.width = pct + "%"; });
      });
    });

    var rings = document.querySelectorAll("[data-dsh-ring]");
    Array.prototype.forEach.call(rings, function (el) {
      var pct = parseFloat(el.getAttribute("data-dsh-ring")) || 0;
      if (reduceMotion.matches) {
        el.style.setProperty("--ring-pct", pct);
        return;
      }
      // conic-gradient does not interpolate reliably across browsers, so the
      // sweep is stepped manually — still just a paint of one element.
      animate(900, function (eased, done) {
        el.style.setProperty("--ring-pct", done ? pct : (pct * eased).toFixed(1));
      });
    });
  }

  /* ---------------------------- Sparklines ---------------------------- */

  function drawSparklines() {
    var sparks = document.querySelectorAll(".dsh-kpi-spark");
    Array.prototype.forEach.call(sparks, function (svg) {
      var line = svg.querySelector("polyline");
      if (!line) return;
      var length;
      try {
        length = line.getTotalLength();
      } catch (err) {
        return; // hidden or not laid out yet — leave the line drawn as-is
      }
      if (!length) return;
      if (reduceMotion.matches) {
        svg.style.setProperty("--spark-len", "0");
        svg.classList.add("is-drawn");
        return;
      }
      svg.style.setProperty("--spark-len", length);
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () { svg.classList.add("is-drawn"); });
      });
    });
  }

  /* ----------------------- Thumbnail error fallback ----------------------- */

  function initThumbs() {
    var images = document.querySelectorAll(".dsh-thumb img");
    Array.prototype.forEach.call(images, function (img) {
      img.addEventListener("error", function () {
        // Never a broken-image icon: fall back to the shared blueprint tile.
        var thumb = img.closest(".dsh-thumb");
        if (!thumb) return;
        img.remove();
        var tpl = document.getElementById("dsh-thumb-placeholder");
        if (tpl && tpl.content && !thumb.querySelector(".dsh-thumb-placeholder")) {
          thumb.appendChild(tpl.content.cloneNode(true));
        }
      });
    });
  }

  function init() {
    reveal();
    countUp();
    fillProgress();
    drawSparklines();
    initThumbs();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
