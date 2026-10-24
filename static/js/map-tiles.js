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

  var ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
    '&copy; <a href="https://carto.com/attributions">CARTO</a>';

  // CARTO basemap'lari OSM ma'lumotidan quriladi, lekin CDN orqali tarqatiladi.
  // tile.openstreetmap.org — ko'ngilli serverlar; ular ilova trafigini bloklab,
  // taylar o'rniga "403 Access blocked" rasmini qaytaradi (403 bo'lsa ham brauzer
  // uni oddiy rasm sifatida chizadi, shuning uchun tileerror ham ishlamaydi).
  var PRIMARY = {
    light: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  };
  var PRIMARY_OPTS = { subdomains: "abcd", maxZoom: 20, attribution: ATTRIBUTION };

  // CDN umuman ochilmasa (tarmoq/DNS), OSM'ga qaytamiz — u yerda tayl kelmasa
  // hech bo'lmasa xarita bo'sh emas, eski holicha ishlaydi.
  var FALLBACK_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var FALLBACK_OPTS = {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  };

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function addTiles(map) {
    var url = (global.AP_MAP_TILE_URL || (isDark() ? PRIMARY.dark : PRIMARY.light));
    var layer = L.tileLayer(url, PRIMARY_OPTS).addTo(map);

    var errors = 0;
    var swapped = false;
    layer.on("tileerror", function () {
      errors += 1;
      if (swapped || errors < 5) return;
      swapped = true;
      map.removeLayer(layer);
      L.tileLayer(FALLBACK_URL, FALLBACK_OPTS).addTo(map);
    });
    return layer;
  }

  global.APMap = { addTiles: addTiles };
})(window);
