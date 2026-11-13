/* Leaflet uchun umumiy sozlama: marker rasmlari va tayl (tile) qatlami.
   project-map.js va project-map-view.js shu faylga tayanadi. */
(function (global) {
  if (typeof L === "undefined") return;

  // Leaflet marker rasm yo'lini leaflet.css dagi url() dan taxmin qiladi va
  // "marker-icon.png" oxirgi qismini kesib tashlaydi. Prod'da ManifestStatic-
  // FilesStorage fayl nomiga hash qo'shadi ("marker-icon.2273e3d8.png"), shu
  // sabab kesish ishlamaydi va marker o'rnida singan rasm chiqadi. Shuning
  // uchun URL'larni shablondan {% static %} orqali olib, ochiq qo'yamiz.
  (function applyIconUrls() {
    var el = document.getElementById("leaflet-asset-urls");
    if (!el) return;
    var urls;
    try {
      urls = JSON.parse(el.textContent || "{}");
    } catch (e) {
      return;
    }
    if (!urls.iconUrl) return;
    L.Icon.Default.prototype.options.iconUrl = urls.iconUrl;
    L.Icon.Default.prototype.options.iconRetinaUrl = urls.iconRetinaUrl || urls.iconUrl;
    L.Icon.Default.prototype.options.shadowUrl = urls.shadowUrl || "";
    // imagePath bo'sh bo'lsa Leaflet yuqoridagi URL'larni o'zgartirmay ishlatadi.
    L.Icon.Default.imagePath = "";
  })();

  // CARTO basemap'lari endi API kalitsiz "API KEY REQUIRED" rasmini qaytaradi
  // (200 status bilan, shuning uchun tileerror ham ishlamaydi). Esri ArcGIS
  // Online taylari kalitsiz ishlaydi; atributsiya ko'rsatilishi shart.
  // tile.openstreetmap.org — ko'ngilli serverlar, ilova trafigini bloklashi
  // mumkin, shuning uchun faqat zaxira sifatida ishlatiladi.
  var ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/";
  var ATTRIBUTION =
    'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors';
  var PRIMARY = {
    light: ESRI + "World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    dark: ESRI + "Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  };
  // Qorong'i fonda nomlar alohida qatlamda keladi.
  var DARK_LABELS = ESRI + "Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}";
  var PRIMARY_OPTS = { maxZoom: 19, attribution: ATTRIBUTION };

  // Esri ochilmasa (tarmoq/DNS), OSM'ga qaytamiz.
  var FALLBACK_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var FALLBACK_OPTS = {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  };

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function addTiles(map) {
    var dark = !global.AP_MAP_TILE_URL && isDark();
    var url = global.AP_MAP_TILE_URL || (dark ? PRIMARY.dark : PRIMARY.light);
    var layer = L.tileLayer(url, PRIMARY_OPTS).addTo(map);
    var labels = dark ? L.tileLayer(DARK_LABELS, { maxZoom: 19 }).addTo(map) : null;

    var errors = 0;
    var swapped = false;
    layer.on("tileerror", function () {
      errors += 1;
      if (swapped || errors < 5) return;
      swapped = true;
      map.removeLayer(layer);
      if (labels) map.removeLayer(labels);
      L.tileLayer(FALLBACK_URL, FALLBACK_OPTS).addTo(map);
    });
    return layer;
  }

  global.APMap = { addTiles: addTiles };
})(window);
