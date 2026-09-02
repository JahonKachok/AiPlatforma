/* BuildFlow — project card 3D tilt, image parallax and cursor glare.
 *
 * Design notes:
 *  - Nothing is animated in JS. The pointer position is written into CSS
 *    custom properties once per animation frame and the compositor does the
 *    rest, so only `transform`/`opacity` ever change (no layout, no paint).
 *  - Writes are coalesced through requestAnimationFrame: however many
 *    pointermove events fire, at most one style update happens per frame.
 *  - Devices without a real pointer, and users who asked for reduced motion,
 *    get no 3D at all — the CSS already neutralises the transforms, and we
 *    skip binding the listeners entirely.
 */
(function () {
  "use strict";

  var MAX_TILT = 5;      // degrees — the spec's 4–6° "premium, not gimmicky" range
  var IMAGE_SHIFT = 10;  // px — the image travels further than the card, giving depth
  var TRACK_MS = "120ms"; // follow-the-cursor easing; rest state is 420ms via CSS

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

  function tiltEnabled() {
    return finePointer.matches && !reduceMotion.matches;
  }

  function bindCard(wrap) {
    var card = wrap.querySelector(".prj-card");
    if (!card) return;

    var frame = null;
    var pending = null;

    function apply() {
      frame = null;
      if (!pending) return;
      var s = card.style;
      s.setProperty("--prj-rx", pending.rx.toFixed(2) + "deg");
      s.setProperty("--prj-ry", pending.ry.toFixed(2) + "deg");
      s.setProperty("--prj-px", pending.px.toFixed(2) + "px");
      s.setProperty("--prj-py", pending.py.toFixed(2) + "px");
      s.setProperty("--prj-gx", pending.gx.toFixed(2) + "%");
      s.setProperty("--prj-gy", pending.gy.toFixed(2) + "%");
      pending = null;
    }

    function onMove(event) {
      var rect = card.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      // -0.5 … 0.5 relative to the card's centre.
      var nx = (event.clientX - rect.left) / rect.width - 0.5;
      var ny = (event.clientY - rect.top) / rect.height - 0.5;

      pending = {
        // Cursor above centre tips the card back, cursor left tips it left.
        rx: -ny * MAX_TILT * 2,
        ry: nx * MAX_TILT * 2,
        // The image drifts the opposite way, which reads as parallax depth.
        px: -nx * IMAGE_SHIFT,
        py: -ny * IMAGE_SHIFT,
        gx: (nx + 0.5) * 100,
        gy: (ny + 0.5) * 100
      };
      if (frame === null) frame = window.requestAnimationFrame(apply);
    }

    function onEnter() {
      card.style.setProperty("--prj-dur", TRACK_MS);
    }

    function onLeave() {
      if (frame !== null) {
        window.cancelAnimationFrame(frame);
        frame = null;
      }
      pending = null;
      var s = card.style;
      // Drop --prj-dur so the CSS default (420ms) eases the card back to rest.
      s.removeProperty("--prj-dur");
      s.removeProperty("--prj-rx");
      s.removeProperty("--prj-ry");
      s.removeProperty("--prj-px");
      s.removeProperty("--prj-py");
    }

    wrap.addEventListener("pointerenter", onEnter);
    wrap.addEventListener("pointermove", onMove);
    wrap.addEventListener("pointerleave", onLeave);

    wrap._prjUnbind = function () {
      wrap.removeEventListener("pointerenter", onEnter);
      wrap.removeEventListener("pointermove", onMove);
      wrap.removeEventListener("pointerleave", onLeave);
      onLeave();
    };
    wrap._prjBound = true;
  }

  function unbindCard(wrap) {
    if (wrap._prjBound && wrap._prjUnbind) {
      wrap._prjUnbind();
      wrap._prjBound = false;
    }
  }

  function syncTilt() {
    var wraps = document.querySelectorAll("[data-prj-tilt]");
    var on = tiltEnabled();
    Array.prototype.forEach.call(wraps, function (wrap) {
      if (on && !wrap._prjBound) bindCard(wrap);
      else if (!on) unbindCard(wrap);
    });
  }

  /* ---------------- Image loading: shimmer, fade-in, fallback ---------------- */

  function markReady(media) {
    media.classList.add("is-ready");
  }

  function showPlaceholder(media) {
    // The <img> failed — swap in the same blueprint placeholder every
    // image-less project already uses, never a broken-image icon.
    var img = media.querySelector("img");
    if (img) img.remove();
    if (!media.querySelector(".prj-media-placeholder")) {
      var tpl = document.getElementById("prj-placeholder-template");
      if (tpl && tpl.content) media.appendChild(tpl.content.cloneNode(true));
    }
    markReady(media);
  }

  function initImages(root) {
    var images = (root || document).querySelectorAll(".prj-media img, .prj-thumb img");
    Array.prototype.forEach.call(images, function (img) {
      var media = img.closest(".prj-media") || img.closest(".prj-thumb");
      if (!media || media._prjImgBound) return;
      media._prjImgBound = true;

      if (img.complete && img.naturalWidth > 0) {
        img.classList.add("is-loaded");
        markReady(media);
        return;
      }
      if (img.complete && img.naturalWidth === 0) {
        showPlaceholder(media);
        return;
      }
      img.addEventListener("load", function () {
        img.classList.add("is-loaded");
        markReady(media);
      });
      img.addEventListener("error", function () {
        showPlaceholder(media);
      });
    });
  }

  /* ---------------------------- ⋮ card menu ---------------------------- */

  function closeAllMenus(except) {
    var open = document.querySelectorAll(".prj-menu.is-open");
    Array.prototype.forEach.call(open, function (menu) {
      if (menu !== except) {
        menu.classList.remove("is-open");
        var btn = menu.querySelector(".prj-menu-btn");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function initMenus() {
    document.addEventListener("click", function (event) {
      var btn = event.target.closest(".prj-menu-btn");
      if (btn) {
        // The card itself is a stretched link; the menu must not navigate.
        event.preventDefault();
        event.stopPropagation();
        var menu = btn.closest(".prj-menu");
        var willOpen = !menu.classList.contains("is-open");
        closeAllMenus(menu);
        menu.classList.toggle("is-open", willOpen);
        btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
        return;
      }
      if (!event.target.closest(".prj-menu-list")) closeAllMenus(null);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeAllMenus(null);
    });
  }

  function init() {
    syncTilt();
    initImages(document);
    initMenus();

    // Preference changes (OS motion setting, plugging in a mouse) are applied live.
    var onPrefChange = function () { syncTilt(); };
    if (reduceMotion.addEventListener) {
      reduceMotion.addEventListener("change", onPrefChange);
      finePointer.addEventListener("change", onPrefChange);
    } else if (reduceMotion.addListener) {
      reduceMotion.addListener(onPrefChange);
      finePointer.addListener(onPrefChange);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
