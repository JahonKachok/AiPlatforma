(() => {
  const $ = id => document.getElementById(id);
  const root = $("office"), panel = $("employee-panel"), board = $("board-dialog"), dialog = $("form-dialog");
  let state = JSON.parse($("office-data").textContent), selected = null, tab = "today";
  let editing = null, changes = 0, pendingRequests = 0, noticeTimer;
  const generating = new Set();
  const taskStates = {new:"Yangi",working:"Ishlayapti",ready:"Tayyor",error:"Xatolik"};
  const leadStates = {new:"Yangi",contacted:"Bog‘lanildi"};
  const commands = {sales:"Javob tayyorla",marketing:"Post tayyorla",analyst:"Hisobot tayyorla",director:"Reja tayyorla"};
  const employee = key => state.employees.find(e => e.key === key);
  const taskById = id => state.tasks.find(t => t.id === id);
  const leadById = id => state.leads.find(l => l.id === id);
  function el(tag,text,cls) {
    const node = document.createElement(tag);
    if(text !== undefined) node.textContent = text;
    if(cls) node.className = cls;
    return node;
  }
  function btn(text,fn,cls="secondary") {
    const b=el("button",text,cls); b.type="button";
    b.onclick=async () => {
      if(b.disabled) return;
      b.disabled=true;
      try { await fn(); } catch(e) { notify(e.message); } finally { b.disabled=false; }
    };
    return b;
  }
  function notify(text) {
    $("notice").textContent=text;clearTimeout(noticeTimer);
    noticeTimer=setTimeout(()=>$("notice").textContent="",5500);
  }
  function group(...nodes) {const g=el("div",undefined,"row-actions");g.append(...nodes);return g;}
  function empty(text) {return el("p",text,"empty");}
  function choice(items,value) {
    const s=el("select");
    for(const [key,name] of items) s.add(new Option(name,key));
    s.value=value;return s;
  }
  async function post(action, values) {
    changes++;pendingRequests++;
    try {
      const res=await fetch(root.dataset.action.replace("ACTION",action),{method:"POST",
        headers:{"X-CSRFToken":root.querySelector("[name=csrfmiddlewaretoken]").value},
        body:new URLSearchParams(values)});
      if(!res.headers.get("content-type")?.includes("application/json")) throw Error("Serverga ulanishni va hisobga kirganingizni tekshiring.");
      const data=await res.json();
      if(!res.ok) throw Error(data.error||"Amal bajarilmadi.");
      state=data.office;render();return data.created;
    } finally {changes++;pendingRequests--;}
  }
  async function refresh() {
    if(document.hidden||pendingRequests) return;
    const version=changes;
    try {
      const res=await fetch(root.dataset.source,{cache:"no-store"});
      if(!res.ok) throw Error();
      const data=await res.json();
      if(version===changes && JSON.stringify(data)!==JSON.stringify(state)) {state=data;render();}
    } catch {notify("Ofis yangilanmadi. Internet aloqasini tekshiring.");}
  }
  async function generate(id) {
    if(generating.has(id)) return;
    generating.add(id);render();
    try {
      await post("generate",{id});
      const t=taskById(id);
      notify(t.status==="error"?"Javob olinmadi. Topshiriq saqlandi.":t.status==="ready"?"Natija tayyor.":"Topshiriq bajarilmoqda.");
    } finally {generating.delete(id);render();}
  }
  function field(label,control,name) {
    const wrapper=el("label",label);control.name=name;wrapper.append(control);return wrapper;
  }
  function showForm(kind,opts={}) {
    editing={kind,...opts};
    const f=$("form-fields"); f.replaceChildren();
    const save=$("entry-form").querySelector("[type=submit]");save.textContent="Saqlash";
    $("entry-form").querySelector(".form-error").textContent="";
    if(kind==="result") {
      const t=taskById(opts.id);editing.updated=t.updated;
      $("form-title").textContent="Natijani tahrirlash";
      const area=el("textarea");area.rows=8;area.required=true;area.maxLength=16000;area.value=t.body;
      f.append(field("Natija matni",area,"body"));
    } else {
      const lead=kind==="lead";
      $("form-title").textContent=lead?"Yangi lid":"Topshiriq berish";
      const who=choice(state.employees.map(e=>[e.key,e.name+" · "+e.role]),opts.employee||(lead?"sales":"marketing"));
      const area=el("textarea");area.required=true;area.rows=4;area.maxLength=3000;
      area.placeholder=lead?"Aziza Telegram orqali ingliz tili kursining narxini so‘radi":"Xodim bajarishi kerak bo‘lgan ishni yozing.";
      f.append(field("Mas’ul xodim",who,"employee"),field(lead?"Lid murojaati":"Vazifa matni",area,"brief"));
      if(lead) {
        const price=el("input");price.type="number";price.min=0;price.max=999999999999;price.placeholder="Ma’lum bo‘lsa";
        f.append(field("Tasdiqlangan narx, so‘m (ixtiyoriy)",price,"price"));
      } else if(opts.run) {
        save.textContent=commands[who.value];who.onchange=()=>save.textContent=commands[who.value];
      }
    }
    dialog.showModal();
    f.querySelector("textarea")?.focus();
  }
  $("entry-form").onsubmit=async e=>{
    e.preventDefault();
    const form=e.currentTarget, save=form.querySelector("[type=submit]");
    if(save.disabled) return;
    const values=Object.fromEntries(new FormData(form)), opts=editing;
    save.disabled=true;
    try {
      if(opts.kind==="result") await post("result-edit",{...values,id:opts.id,updated:opts.updated});
      else {
        const id=await post(opts.kind==="lead"?"lead-add":"task-add",values);
        if(opts.kind==="task"&&opts.run) {dialog.close();await generate(id);return;}
      }
      dialog.close();notify("Saqlandi.");
    } catch(err) {form.querySelector(".form-error").textContent=err.message;if(!dialog.open) notify(err.message);}
    finally {save.disabled=false;}
  };
  function statusSelect(type,row,labels) {
    const options=Object.entries(labels).filter(([key])=>key!=="error"||row.status==="error");
    const s=choice(options,row.status);s.setAttribute("aria-label",type==="lead"?"Lid holati":"Vazifa holati");
    s.disabled=Boolean(row.busy||generating.has(row.id)&&type==="task");
    s.onchange=async ()=>{
      s.disabled=true;
      try {await post(type+"-status",{id:row.id,status:s.value});}
      catch(err){s.value=row.status;notify(err.message);}finally{s.disabled=false;}
    };
    return s;
  }
  function leadRow(l) {
    const row=el("article",undefined,"entry");row.dataset.lead=l.id;
    row.append(el("span","Lid №"+l.id+" · "+employee(l.employee_id).name,"meta"),el("p",l.brief));
    if(l.price!==null) row.append(el("small",l.price.toLocaleString("uz")+" so‘m"));
    const reply=state.tasks.find(t=>t.lead===l.id && t.employee==="sales");
    const actions=group(statusSelect("lead",l,leadStates));
    if(!reply) actions.append(btn("Javob tayyorla",async ()=>{
      const id=await post("task-add",{employee:"sales",lead:l.id,brief:l.brief});
      await generate(id);
    },"primary"));
    else if(reply.body) actions.append(btn("Javobni ochish",()=>showForm("result",{id:reply.id})));
    else actions.append(runButton(reply));
    row.append(actions);return row;
  }
  function runButton(t) {
    const busy=t.busy||generating.has(t.id);
    const b=btn(busy?"Tayyorlanmoqda…":t.status==="error"?"Qayta urinish":commands[t.employee],()=>generate(t.id),"primary");
    b.disabled=busy;return b;
  }
  async function copy(t) {
    try {await navigator.clipboard.writeText(t.body);notify("Matn nusxalandi.");}
    catch {
      showForm("result",{id:t.id});$("form-fields").querySelector("textarea").select();
      if(document.execCommand("copy")) {dialog.close();notify("Matn nusxalandi.");}
      else notify("Matn tanlandi. Nusxalash buyrug‘idan foydalaning.");
    }
  }
  function taskRow(t,controls=false) {
    const row=el("article",undefined,"entry");row.dataset.task=t.id;
    row.append(el("span",employee(t.employee).name+" · "+taskStates[t.status],"meta"),el("p",t.brief));
    const actions=group();
    if(t.body) {
      row.append(el("p",t.body,"result-body"));
      actions.append(btn("Tahrirlash",()=>showForm("result",{id:t.id})),btn("Nusxalash",()=>copy(t)));
    }
    if(t.status!=="ready") actions.append(runButton(t));
    if(controls) actions.append(statusSelect("task",t,taskStates));
    row.append(actions);return row;
  }
  function list(container,rows,mapper,message) {
    if(!rows.length) container.append(empty(message));else rows.forEach(r=>container.append(mapper(r)));
  }
  function renderPanel() {
    panel.hidden=!selected;
    if(!selected) return;
    const e=employee(selected), here=$("employee-content");
    here.replaceChildren(el("span",e.role,"eyebrow"),el("h2",e.name),el("p",e.description,"sub"));
    const actions=group(btn("Topshiriq berish",()=>showForm("task",{employee:e.key,run:true}),"primary"));
    if(e.key==="sales") actions.prepend(btn("Lid qo‘shish",()=>showForm("lead",{employee:e.key})));
    here.append(actions);
    const own=state.tasks.filter(t=>t.employee===e.key);
    here.append(el("h3","Joriy topshiriqlar"));
    list(here,own.filter(t=>t.status!=="ready"),t=>taskRow(t),"Hozircha ochiq topshiriq yo‘q.");
    if(e.key==="sales"||state.leads.some(l=>l.employee_id===e.key)) {
      here.append(el("h3","Biriktirilgan lidlar"));
      list(here,state.leads.filter(l=>l.employee_id===e.key),leadRow,"Yangi murojaatni lid sifatida kiriting.");
    }
    here.append(el("h3","Oldingi natijalar"));
    list(here,own.filter(t=>t.body),t=>taskRow(t),"Hali natija tayyorlanmagan.");
    if(e.key==="director") {
      here.append(el("h3","Jamoa vazifalari"));
      list(here,state.tasks,t=>taskRow(t,true),"Jamoaga vazifa biriktirilmagan.");
    }
  }
  function renderBoard() {
    for(const b of $("board-tabs").children) b.setAttribute("aria-pressed",String(b.dataset.tab===tab));
    const here=$("board-content");here.replaceChildren();
    if(tab==="today") {
      const stats=el("div",undefined,"stats");
      for(const [key,label] of [["leads","Bugungi lidlar"],["tasks","Bugungi vazifalar"],["results","Bugungi natijalar"]]) {
        const cell=el("div");cell.dataset.metric=key;cell.append(el("b",state.today[key]),el("span",label));stats.append(cell);
      }
      here.append(stats);
    }
    const actions=group();
    if(tab!=="tasks") actions.append(btn("Lid qo‘shish",()=>showForm("lead",{employee:"sales"}),"primary"));
    if(tab!=="leads") actions.append(btn("Vazifa qo‘shish",()=>showForm("task")));
    here.append(actions);
    if(tab==="leads") list(here,state.leads,leadRow,"Hali lidlar yo‘q.");
    if(tab==="tasks") list(here,state.tasks,t=>taskRow(t,true),"Hali vazifalar yo‘q.");
  }
  function render() {
    renderPanel();if(board.open) renderBoard();
    root.dispatchEvent(new CustomEvent("office-change",{detail:{employees:state.employees,selected,
      boardCounts:[state.today.results,state.leads.length,state.tasks.length]}}));
  }
  function openBoard() {tab="today";renderBoard();board.showModal();}
  root.addEventListener("office-pick",e=>{
    if(e.detail==="board") openBoard();
    else {selected=e.detail;render();panel.scrollTop=0;panel.querySelector(".close").focus({preventScroll:true});}
  });
  function closePanel() {
    const previous=selected;selected=null;render();
    root.querySelector('[data-station="'+previous+'"]')?.focus({preventScroll:true});
  }
  root.querySelector("[data-close-panel]").onclick=closePanel;
  root.querySelector("[data-open-board]").onclick=openBoard;
  root.querySelectorAll("[data-dismiss]").forEach(b=>b.onclick=()=>b.closest("dialog").close());
  $("board-tabs").onclick=e=>{if(e.target.dataset.tab){tab=e.target.dataset.tab;renderBoard();}};
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&selected&&!dialog.open&&!board.open) closePanel();});
  setInterval(refresh,12000);document.addEventListener("visibilitychange",()=>{if(!document.hidden) refresh();});
  render();
})();
