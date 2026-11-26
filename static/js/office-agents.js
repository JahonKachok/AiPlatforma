(() => {
  const root = document.getElementById("office");
  const panel = document.getElementById("employee-panel");
  const content = document.getElementById("employee-content");
  const close = panel.querySelector("[data-close-panel]");
  let data = JSON.parse(document.getElementById("office-data").textContent);
  let selected = null, opener = null, refreshing = false;
  function element(tag, text, style) {
    const item = document.createElement(tag);
    item.textContent = text;
    if (style) item.className = style;
    return item;
  }
  function render() {
    const s = data.stations.find(station => station.key === selected);
    panel.hidden = !s;
    if (s) {
      const state = {quiet:"Faol ish qayd etilmagan",running:"Ishlayapti",waiting:"Kutilmoqda",offline:"Ishchi kompyuter ulanmagan"};
      content.replaceChildren(element("span",s.group,"eyebrow"),element("h2",s.name),
        element("span",state[s.state],"pill"),element("p",s.description,"sub"));
      const list = document.createElement("dl");
      for (const [label, value] of [["24 soatda AI chaqiruvlari",s.calls],["Navbatda",s.queued],
        ["Bajarilmoqda",s.running],["Tasdiq kutilmoqda",s.pending]]) {
        const line = element("div","","metric-line");
        line.append(element("dt",label),element("dd",value)); list.append(line);
      }
      content.append(list);
      if (s.link) {
        const link = element("a","Yozuvlarni ko‘rish","secondary");
        link.href = s.link; content.append(link);
      }
    }
    root.dispatchEvent(new CustomEvent("office-change",{detail:{employees:data.stations,selected,boardCounts:[]}}));
  }
  function pick(key, button) {
    selected = key; opener = button; render();close.focus({preventScroll:true});
  }
  root.addEventListener("office-pick", e => pick(e.detail,root.querySelector('[data-station="'+e.detail+'"]')));
  root.querySelectorAll("[data-roster]").forEach(b=>b.addEventListener("click",()=>pick(b.dataset.roster,b)));
  close.onclick = () => {selected=null;render();opener?.focus({preventScroll:true});};
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&selected) close.click();});
  async function refresh() {
    if(document.hidden || refreshing) return;
    refreshing=true;
    try {
      const response=await fetch(root.dataset.source,{cache:"no-store"});
      if(!response.ok) throw Error();
      data=await response.json();render();document.getElementById("notice").textContent="";
    } catch { document.getElementById("notice").textContent="Agentlar holatini yangilab bo‘lmadi."; }
    finally {refreshing=false;}
  }
  setInterval(refresh,30000);
  document.addEventListener("visibilitychange",refresh);
})();
