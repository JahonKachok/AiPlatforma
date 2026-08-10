(function () {
  "use strict";

  var data = window.APPROVAL_SUBMIT_CASCADE;
  var projectSelect = document.getElementById("id_project");
  var subObjectInput = document.getElementById("id_sub_object");
  var objectSelect = document.getElementById("approval-object-select");
  var podSelect = document.getElementById("approval-pod-select");
  if (!data || !projectSelect || !subObjectInput || !objectSelect || !podSelect) return;

  var subObjectById = {};
  data.subObjects.forEach(function (so) { subObjectById[so.id] = so; });

  function clearSelect(select, placeholderText) {
    select.innerHTML = "";
    var opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholderText;
    select.appendChild(opt);
  }

  function populateObjectSelect(projectId, selectedId) {
    clearSelect(objectSelect, objectSelect.dataset.placeholder || "");
    data.subObjects
      .filter(function (so) { return so.project_id === projectId && !so.parent_id; })
      .sort(function (a, b) { return a.name.localeCompare(b.name); })
      .forEach(function (so) {
        var opt = document.createElement("option");
        opt.value = so.id;
        opt.textContent = so.name;
        objectSelect.appendChild(opt);
      });
    objectSelect.value = selectedId || "";
  }

  function populatePodSelect(objectId, selectedId) {
    clearSelect(podSelect, "—");
    if (objectId) {
      data.subObjects
        .filter(function (so) { return so.parent_id === objectId; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); })
        .forEach(function (so) {
          var opt = document.createElement("option");
          opt.value = so.id;
          opt.textContent = so.name;
          podSelect.appendChild(opt);
        });
    }
    podSelect.value = selectedId || "";
  }

  function syncHiddenField() {
    subObjectInput.value = podSelect.value || objectSelect.value || "";
  }

  var initialSubObjectId = subObjectInput.value;
  var initialSubObject = subObjectById[initialSubObjectId];
  var initialObjectId = initialSubObject ? (initialSubObject.parent_id || initialSubObject.id) : "";
  var initialPodId = initialSubObject && initialSubObject.parent_id ? initialSubObject.id : "";

  populateObjectSelect(projectSelect.value, initialObjectId);
  populatePodSelect(initialObjectId, initialPodId);

  projectSelect.addEventListener("change", function () {
    populateObjectSelect(projectSelect.value, null);
    populatePodSelect(null, null);
    syncHiddenField();
  });

  objectSelect.addEventListener("change", function () {
    populatePodSelect(objectSelect.value, null);
    syncHiddenField();
  });

  podSelect.addEventListener("change", syncHiddenField);
})();
