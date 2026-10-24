(function () {
  function init() {
    var mapEl = document.getElementById("project-overview-map");
    if (!mapEl || typeof L === "undefined" || !window.APMap) return;

    var lat = parseFloat(mapEl.dataset.lat);
    var lng = parseFloat(mapEl.dataset.lng);
    if (isNaN(lat) || isNaN(lng)) return;

    var map = L.map(mapEl, {
      zoomControl: true,
      dragging: true,
      scrollWheelZoom: false,
    }).setView([lat, lng], 15);

    window.APMap.addTiles(map);

    var marker = L.marker([lat, lng]).addTo(map);
    if (mapEl.dataset.address) {
      marker.bindPopup(mapEl.dataset.address);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
