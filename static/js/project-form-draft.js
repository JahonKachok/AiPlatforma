(function () {
  var form = document.querySelector("form[data-draft-key]");
  if (!form) return;
  var storageKey = form.dataset.draftKey;

  function fields() {
    return form.querySelectorAll("input[name], select[name], textarea[name]");
  }

  function saveDraft() {
    var data = {};
    fields().forEach(function (field) {
      if (field.name === "csrfmiddlewaretoken") return;
      data[field.name] = field.type === "checkbox" || field.type === "radio" ? field.checked : field.value;
    });
    try {
      localStorage.setItem(storageKey, JSON.stringify(data));
    } catch (e) {}
  }

  function restoreDraft() {
    var raw;
    try {
      raw = localStorage.getItem(storageKey);
    } catch (e) {
      return;
    }
    if (!raw) return;
    var data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      return;
    }
    fields().forEach(function (field) {
      if (!(field.name in data) || field.value) return;
      if (field.type === "checkbox" || field.type === "radio") {
        field.checked = !!data[field.name];
      } else {
        field.value = data[field.name];
      }
    });
  }

  restoreDraft();

  form.addEventListener("input", saveDraft);
  form.addEventListener("change", saveDraft);
  var mapWatcher = window.setInterval(saveDraft, 2000);
  form.addEventListener("submit", function () {
    window.clearInterval(mapWatcher);
    try {
      localStorage.removeItem(storageKey);
    } catch (e) {}
  });
})();
