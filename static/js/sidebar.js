/* Mobil sidebar (hamburger) boshqaruvi. 768px dan keng ekranlarda sidebar
   doimiy ko'rinadi va bu skript hech narsa qilmaydi — ochish/yopish
   klasslari faqat theme.css dagi mobil media query ichida ishlaydi. */
(function () {
  var sidebar = document.getElementById("ap-sidebar");
  var overlay = document.getElementById("ap-sidebar-overlay");
  var toggle = document.querySelector("[data-sidebar-toggle]");
  if (!sidebar || !overlay || !toggle) return;

  function close() {
    sidebar.classList.remove("is-open");
    overlay.classList.remove("is-open");
  }

  toggle.addEventListener("click", function () {
    sidebar.classList.toggle("is-open");
    overlay.classList.toggle("is-open");
  });
  overlay.addEventListener("click", close);
  sidebar.addEventListener("click", function (e) {
    if (e.target.closest("a")) close();
  });
})();
