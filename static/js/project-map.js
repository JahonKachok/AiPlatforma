(function () {
  function init() {
    var mapEl = document.getElementById("project-map");
    if (!mapEl || typeof L === "undefined") return;

    var latInput = document.getElementById("id_latitude");
    var lngInput = document.getElementById("id_longitude");
    var regionSelect = document.getElementById("id_region");
    var regionCenters = window.REGION_CENTERS || {};

    var initialLat = parseFloat(latInput.value);
    var initialLng = parseFloat(lngInput.value);
    var hasInitial = !isNaN(initialLat) && !isNaN(initialLng);
    var defaultCenter = [41.2995, 69.2401]; // Tashkent shahri
    var startCenter = hasInitial ? [initialLat, initialLng] : defaultCenter;

    var map = L.map(mapEl).setView(startCenter, hasInitial ? 14 : 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    var marker = hasInitial ? L.marker(startCenter, { draggable: true }).addTo(map) : null;

    function setMarker(latlng) {
      if (marker) {
        marker.setLatLng(latlng);
      } else {
        marker = L.marker(latlng, { draggable: true }).addTo(map);
        marker.on("dragend", function () {
          updateInputs(marker.getLatLng());
        });
      }
      updateInputs(latlng);
    }

    function updateInputs(latlng) {
      latInput.value = latlng.lat.toFixed(6);
      lngInput.value = latlng.lng.toFixed(6);
    }

    map.on("click", function (e) {
      setMarker(e.latlng);
    });

    if (marker) {
      marker.on("dragend", function () {
        updateInputs(marker.getLatLng());
      });
    }

    if (regionSelect) {
      regionSelect.addEventListener("change", function () {
        var center = regionCenters[regionSelect.value];
        if (center) {
          map.setView(center, 10);
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
