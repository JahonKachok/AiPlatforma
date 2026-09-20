/* Sidebar: mobile drawer (hamburger) + desktop collapse/expand.
   Above 768px the drawer classes do nothing — the off-canvas rules live in
   theme.css's mobile media query. Collapse state persists in localStorage and
   is applied before paint by the inline snippet in base.html. */
(function () {
  "use strict";

  var STORAGE_KEY = "ap-sidebar-collapsed";
  var root = document.documentElement;
  var sidebar = document.getElementById("ap-sidebar");
  if (!sidebar) return;

  /* ---------- mobile drawer (unchanged behaviour) ---------- */
  var overlay = document.getElementById("ap-sidebar-overlay");
  var toggle = document.querySelector("[data-sidebar-toggle]");
  if (overlay && toggle) {
    function closeDrawer() {
      sidebar.classList.remove("is-open");
      overlay.classList.remove("is-open");
    }
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("is-open");
      overlay.classList.toggle("is-open");
    });
    overlay.addEventListener("click", closeDrawer);
    sidebar.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeDrawer();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) {
        closeDrawer();
        toggle.focus();
      }
    });
  }

  /* ---------- desktop collapse ---------- */
  var collapseBtn = sidebar.querySelector("[data-sidebar-collapse]");

  function isCollapsed() {
    return root.classList.contains("ap-sb-collapsed");
  }

  function syncButton() {
    if (!collapseBtn) return;
    var collapsed = isCollapsed();
    collapseBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    var label = collapsed
      ? collapseBtn.getAttribute("data-tip-expand")
      : collapseBtn.getAttribute("data-tip-collapse");
    if (label) collapseBtn.setAttribute("aria-label", label);
  }

  if (collapseBtn) {
    collapseBtn.addEventListener("click", function () {
      var collapsed = root.classList.toggle("ap-sb-collapsed");
      try { localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0"); } catch (e) { /* private mode */ }
      syncButton();
      hideTip();
    });
    syncButton();
  }

  /* ---------- tooltip, only while collapsed ---------- */
  var tip = null;

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement("div");
    tip.className = "ap-sb-tip";
    tip.setAttribute("role", "tooltip");
    tip.setAttribute("data-open", "false");
    document.body.appendChild(tip);
    return tip;
  }

  function showTip(target) {
    // Only meaningful when labels are hidden and we're on a desktop layout.
    if (!isCollapsed() || window.innerWidth < 768) return;
    var text = target.getAttribute("data-tip");
    if (!text) return;
    var el = ensureTip();
    el.textContent = text;
    el.setAttribute("data-open", "true");

    var r = target.getBoundingClientRect();
    var tr = el.getBoundingClientRect();
    var top = r.top + r.height / 2 - tr.height / 2;
    top = Math.max(8, Math.min(top, window.innerHeight - tr.height - 8));
    // Anchor to the sidebar's edge, not the link's — the link sits inside the
    // rail's padding, so its own right edge would put the tip over the panel.
    el.style.left = (sidebar.getBoundingClientRect().right + 10) + "px";
    el.style.top = top + "px";
  }

  function hideTip() {
    if (tip) tip.setAttribute("data-open", "false");
  }

  sidebar.querySelectorAll("[data-tip]").forEach(function (node) {
    node.addEventListener("mouseenter", function () { showTip(node); });
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener("focus", function () { showTip(node); });
    node.addEventListener("blur", hideTip);
  });

  window.addEventListener("scroll", hideTip, true);
  window.addEventListener("resize", hideTip);
})();
