(function () {
  "use strict";

  var data = window.TASK_FORM_CASCADE;
  var projectSelect = document.getElementById("id_project");
  var sectionSelect = document.getElementById("id_section");
  var assigneeSelect = document.getElementById("id_assignee");
  var objectSelect = document.getElementById("task-object-select");
  var podSelect = document.getElementById("task-pod-select");
  if (!data || !projectSelect || !sectionSelect || !assigneeSelect || !objectSelect || !podSelect) return;

  var subObjectById = {};
  data.subObjects.forEach(function (so) { subObjectById[so.id] = so; });
  var sectionById = {};
  data.sections.forEach(function (s) { sectionById[s.id] = s; });

  var allSectionOptions = Array.prototype.slice.call(sectionSelect.options);
  var allAssigneeOptions = Array.prototype.slice.call(assigneeSelect.options);

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

  function filterSectionOptions(scopeObjectId) {
    var current = sectionSelect.value;
    sectionSelect.innerHTML = "";
    allSectionOptions.forEach(function (opt) {
      if (!opt.value) {
        sectionSelect.appendChild(opt);
        return;
      }
      var section = sectionById[opt.value];
      if (!scopeObjectId || (section && section.sub_object_id === scopeObjectId)) {
        sectionSelect.appendChild(opt);
      }
    });
    var stillPresent = Array.prototype.some.call(sectionSelect.options, function (o) { return o.value === current; });
    sectionSelect.value = stillPresent ? current : "";
  }

  // Ijrochi ro'yxati: faqat loyiha tarkibiga biriktirilganlar, bo'lim tanlansa —
  // shu bo'lim fani bo'yicha. Avval tanlangan odam (tahrirlashda) doim qoladi.
  var hint = document.getElementById("task-assignee-hint");
  var projectMembers = data.projectMembers || {};
  var currentDisciplineId = null;

  function setHint(key) {
    if (!hint) return;
    hint.textContent = key ? hint.dataset[key] || "" : "";
  }

  function filterAssigneeOptions(disciplineId) {
    if (disciplineId !== undefined) currentDisciplineId = disciplineId;
    var current = assigneeSelect.value;
    var members = {};
    (projectMembers[projectSelect.value] || []).forEach(function (id) { members[id] = true; });
    var byDiscipline = null;
    if (currentDisciplineId) {
      byDiscipline = {};
      (data.disciplineUsers[currentDisciplineId] || []).forEach(function (u) { byDiscipline[u.id] = true; });
    }
    assigneeSelect.innerHTML = "";
    allAssigneeOptions.forEach(function (opt) {
      if (!opt.value) { assigneeSelect.appendChild(opt); return; }
      var fits = members[opt.value] && (!byDiscipline || byDiscipline[opt.value]);
      // tanlangan odam (masalan, tahrirlanayotgan vazifaning ijrochisi) yo'qolib qolmasin
      if (fits || opt.value === current) assigneeSelect.appendChild(opt);
    });
    assigneeSelect.value = current;
    if (!projectSelect.value) setHint(null);
    else if (!Object.keys(members).length) setHint("msgEmpty");
    else setHint("msgMembers");
  }

  // --- initial state (handles the edit form, which loads with values already set) ---
  var initialSectionId = sectionSelect.value;
  var initialSection = sectionById[initialSectionId];
  var initialSubObject = initialSection ? subObjectById[initialSection.sub_object_id] : null;
  var initialObjectId = initialSubObject ? (initialSubObject.parent_id || initialSubObject.id) : "";
  var initialPodId = initialSubObject && initialSubObject.parent_id ? initialSubObject.id : "";

  populateObjectSelect(projectSelect.value, initialObjectId);
  populatePodSelect(initialObjectId, initialPodId);
  filterSectionOptions(initialPodId || initialObjectId || null);
  filterAssigneeOptions(initialSection ? initialSection.discipline_id : null);

  // --- cascading behavior ---
  projectSelect.addEventListener("change", function () {
    // boshqa loyiha tarkibida yo'q ijrochi tanlovdan olib tashlanadi
    if ((projectMembers[projectSelect.value] || []).indexOf(assigneeSelect.value) === -1) assigneeSelect.value = "";
    populateObjectSelect(projectSelect.value, null);
    populatePodSelect(null, null);
    filterSectionOptions(null);
    filterAssigneeOptions(null);
  });

  objectSelect.addEventListener("change", function () {
    populatePodSelect(objectSelect.value, null);
    filterSectionOptions(objectSelect.value || null);
    filterAssigneeOptions(null);
  });

  podSelect.addEventListener("change", function () {
    filterSectionOptions(podSelect.value || objectSelect.value || null);
    filterAssigneeOptions(null);
  });

  sectionSelect.addEventListener("change", function () {
    var section = sectionById[sectionSelect.value];
    filterAssigneeOptions(section ? section.discipline_id : null);
  });
})();
