document.addEventListener("DOMContentLoaded", function () {
  const bell = document.querySelector("[data-notification-bell]");
  if (!bell || !window.NOTIFICATIONS_URLS) return;

  const toggle = bell.querySelector("[data-bell-toggle]");
  const dropdown = bell.querySelector("[data-bell-dropdown]");
  const content = bell.querySelector("[data-bell-content]");
  const badge = bell.querySelector("[data-unread-badge]");

  function refreshCount() {
    fetch(window.NOTIFICATIONS_URLS.unreadCount, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((data) => {
        if (data.count > 0) {
          badge.textContent = data.count > 9 ? "9+" : data.count;
          badge.classList.remove("hidden");
        } else {
          badge.classList.add("hidden");
        }
      })
      .catch(() => {});
  }

  function loadRecent() {
    fetch(window.NOTIFICATIONS_URLS.recent, { credentials: "same-origin" })
      .then((r) => r.text())
      .then((html) => {
        content.innerHTML = html;
      })
      .catch(() => {});
  }

  toggle.addEventListener("click", function (e) {
    e.stopPropagation();
    const isHidden = dropdown.classList.contains("hidden");
    dropdown.classList.toggle("hidden");
    if (isHidden) {
      loadRecent();
    }
  });

  document.addEventListener("click", function (e) {
    if (!bell.contains(e.target)) {
      dropdown.classList.add("hidden");
    }
  });

  refreshCount();
  setInterval(refreshCount, 15000);
});
