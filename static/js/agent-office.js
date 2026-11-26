/* Orthographic cutaway. Furniture and hit targets share one world coordinate system. */
(() => {
  const root = document.getElementById("office");
  if (!root) return;
  const canvas = document.getElementById("office-scene");
  const ctx = canvas.getContext("2d");
  const agentFloor = root.dataset.floor === "agents";
  const positions = {director:[3.6,2.7], sales:[13.7,2.9], marketing:[2.8,7.35], analyst:[8.1,7.7],
    dispatcher:[2.1,2.5], kpi:[5.6,2.5], treasurer:[9.2,2.5], quartermaster:[12.9,2.5], archivist:[16.6,2.5],
    translator:[2.1,7.2], printer:[5.6,7.2], gost:[9.2,7.2], norm_control:[12.9,7.2], secretary:[16.6,7.2]};
  const palette = {director:"#386d82",sales:"#b76347",marketing:"#78649a",analyst:"#3f8670"};
  const initial = JSON.parse(document.getElementById("office-data").textContent);
  let stations = agentFloor ? initial.stations : initial.employees;
  const groups = [...new Set(stations.map(s=>s.group))];
  const tint = s => palette[s.key] || Object.values(palette)[groups.indexOf(s.group)];
  let boardCounts = agentFloor ? [] : [initial.today.results, initial.leads.length, initial.tasks.length];
  let selected = null, zoom = 1, panX = 0, panY = 0;
  let width = 0, height = 0, scale = 1, originY = 0, visible = true;
  const angle = .58, cos = Math.cos(angle), sin = Math.sin(angle);
  let hits = [], faces = [], currentKey = null;
  const elevation = .48, vertical = Math.sqrt(1 - elevation * elevation);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const clamp = (v, low, high) => Math.max(low, Math.min(high, v));
  const shadeCache = new Map();
  function shade(hex, factor) {
    const key = hex + factor;
    if (!shadeCache.has(key)) {
      const rgb = [1,3,5].map(i => Math.min(255, Math.round(parseInt(hex.slice(i, i + 2),16) * factor)));
      shadeCache.set(key, "rgb(" + rgb.join(",") + ")");
    }
    return shadeCache.get(key);
  }
  function project([x,y,z]) {
    x -= 9.25; z -= 5.1;
    return [width / 2 + panX + (x * cos - z * sin) * scale,
      originY + panY + ((x * sin + z * cos) * elevation - y * vertical) * scale];
  }
  function polygon(points, fill, stroke) {
    ctx.beginPath();
    points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
    ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = .7; ctx.stroke(); }
  }
  function face(points, fill) {
    const depth = points.reduce((sum,[x,y,z]) => sum + vertical * (x*sin+z*cos) + elevation*y, 0) / points.length;
    faces.push({points, fill, depth, key:currentKey});
  }
  function screen(x,z,index) {
    const left=x-.58, front=z-.263, base=1.39, w=1.16, h=.58;
    // One display surface contains its own graphics so fine marks stay above the glass.
    const panel=[[left,base,front],[left+w,base,front],[left+w,base+h,front],[left,base+h,front]];
    face(panel,"#254d5b");
    const surface=faces[faces.length-1];
    surface.depth+=.15;
    surface.graphic=()=>{
      const [px,py]=project([left,base+h,front]);
      ctx.save();ctx.transform(cos*scale,sin*elevation*scale,0,vertical*scale,px,py);
      ctx.fillStyle="#9bd4c5";ctx.fillRect(.07,.065,.50,.035);
      if (index%3===0) {
        ctx.fillStyle="#e3b17b";
        for(let i=0;i<6;i++) {
          const bar=.08+((i*7+index)%5)*.055;
          ctx.fillRect(.1+i*.155,.49-bar,.095,bar);
        }
      } else if(index%3===1) {
        ctx.strokeStyle="#a3cdd2";ctx.lineWidth=.025;
        ctx.strokeRect(.13,.18,.80,.29);ctx.strokeRect(.14,.18,.36,.15);
        ctx.beginPath();ctx.moveTo(.7,.18);ctx.lineTo(.7,.46);ctx.stroke();
      } else {
        for(let i=0;i<3;i++) {
          ctx.fillStyle=i===1?"#e0c798":"#98bdca";
          ctx.fillRect(.09,.18+i*.11,.78-i*.15,.035);
        }
      }
      ctx.restore();
    };
  }
  function paint() {
    faces.sort((a,b) => a.depth-b.depth);
    for (const f of faces) {
      const points = f.points.map(project);
      polygon(points, f.fill);
      if(f.graphic) f.graphic();
      if (f.key) hits.push({key:f.key, points});
    }
    faces = [];
  }
  function box(x,y,z,w,h,d,color) {
    const r=x+w, t=y+h, f=z+d;
    face([[x,t,z],[r,t,z],[r,t,f],[x,t,f]],shade(color,1.07));
    face([[x,y,f],[x,t,f],[r,t,f],[r,y,f]],color);
    face([[r,y,z],[r,y,f],[r,t,f],[r,t,z]],shade(color,.81));
  }
  function floorRect(x,z,w,d,y,fill) {
    polygon([[x,y,z],[x+w,y,z],[x+w,y,z+d],[x,y,z+d]].map(project),fill);
  }
  function wallSign(x,y,z,text,size) {
    const [a,b] = project([x,y,z]);
    ctx.save(); ctx.transform(cos, sin*elevation, 0,vertical,a,b);
    ctx.font = "bold " + (size*scale) + "px ui-monospace, monospace";
    ctx.fillStyle = "#285363"; ctx.fillText(text,0,0); ctx.restore();
  }
  function shell() {
    // Floor slab and the two back walls are painted first so furnishings can occlude them.
    floorRect(-.08,.28,19.15,10.4,-.42,"#96aba94d");
    box(-.15,-.44,-.15,19,.44,10.6,"#8b9b9d"); paint();
    floorRect(0,0,18.7,10.3,.01,"#dacbb5");
    for(let z=0;z<10.2;z+=.62) {
      floorRect(0,z,18.7,.022,.025,"#c7b8a4");
      const offset = (Math.round(z/.62)%3)*1.2;
      for(let x=offset;x<18.5;x+=3.7) floorRect(x,z,.022,.61,.025,"#c7b8a4");
    }
    box(-.15,0,-.18,18.95,3.28,.22,"#d8e2dc"); paint();
    box(-.18,0,0,.22,3.28,10.3,"#b2c9c4"); paint();
    box(.05,.04,.04,18.65,.14,.075,"#7d9493");
    box(.04,.04,.05,.075,.14,10.18,"#829a98"); paint();
    // Warm window reveals, distant city silhouettes, narrow glazing bars.
    for(const x of [1.25,4.15,10.9,13.8]) {
      box(x,.98,.05,2.65,1.88,.12,"#617e81"); paint();
      box(x+.07,1.06,.18,2.51,1.71,.04,"#a6cdd4"); paint();
      for(let i=0;i<6;i++) box(x+.1+i*.4,1.07,.225,.35,.25+(i%3)*.18,.015,"#91b5bd");
      paint();
      box(x+1.27,1.05,.25,.055,1.74,.05,"#f0ebe0");
      box(x+.06,1.87,.25,2.53,.06,.05,"#e9e9de");
      box(x-.08,.92,.05,2.83,.1,.36,"#ece4d6"); paint();
    }
    // Color-coded cards are visible on the wall even at the overview scale.
    if(agentFloor) wallSign(7.28,1.86,.11,"GASTEC",.64);
    else {
    currentKey="board";
    box(7.02,1.06,.10,3.64,1.99,.12,"#52716b"); paint();
    box(7.12,1.16,.24,3.44,1.79,.05,"#f2eee0"); paint();
    for(let col=0;col<3;col++) {
      const x=7.28+col*1.08;
      wallSign(x,2.6,.33,["Bugun","Lidlar","Vazifalar"][col],.19);
      box(x,2.00,.32,.80,.43,.035,["#e3b764","#81bda4","#91b7cc"][col]);paint();
      wallSign(x+.12,2.09,.37,String(boardCounts[col]),.27);
      if(boardCounts[col]) box(x,1.55,.32,.80,.3,.035,["#ecd2a1","#a5cbb8","#aecbd8"][col]);
    }
    paint();currentKey=null;
    }
    // Pinboard and a sectional door on the return wall.
    box(.05,1.04,1.4,.13,1.48,2.75,"#a5815f");
    for(let i=0;i<4;i++) box(.19,1.3+(i%2)*.36,1.64+i*.57,.025,.59,.42,i%2?"#f1ddd0":"#e4ebe0");
    box(.05,.02,6.8,.14,2.55,1.55,"#6a827c");
    box(.2,.04,6.88,.04,2.42,1.38,"#c4ab8c");
    box(.25,1.12,7.94,.08,.08,.16,"#526569"); paint();
  }
  function plant(x,z,h=1) {
    box(x-.29,0,z-.29,.58,.49,.58,"#d2a785");
    box(x-.34,.46,z-.34,.68,.09,.68,"#e9c9a9");
    box(x-.045,.55,z-.045,.09,.8*h,.09,"#6e7553");
    for(let i=0;i<7;i++) {
      const a=i*2.4, dx=Math.cos(a), dz=Math.sin(a), base=.65+i*.075*h;
      const leaf=[[x,base,z],[x+dx*.29-dz*.15,base+.22*h,z+dz*.29+dx*.15],
        [x+dx*.58,base+.48*h,z+dz*.58],[x+dx*.29+dz*.13,base+.26*h,z+dz*.29-dx*.13]];
      face(leaf,["#446e50","#608c63","#78966a"][i%3]);
    }
  }
  function shelf(x,z) {
    box(x,0,z,2.25,2.1,.14,"#92765f");
    for(const u of [0,2.14]) box(x+u,0,z,.11,2.13,.64,"#ba997a");
    for(const y of [.12,.78,1.43,2.06]) box(x,y,z,2.25,.1,.66,"#c9aa87");
    const books=["#617e8c","#cc9773","#b7b69a","#688b78","#e0c09b"];
    for(let j=0;j<3;j++) for(let i=0;i<7;i++) {
      box(x+.18+i*.23,.22+j*.65,z+.19,.16,.35+((j+i)%3)*.065,.35,books[(i+j)%5]);
    }
  }
  function avatar(x,z,index,accent,working,phase) {
    const skin=["#c78b68","#e3af8a","#ad7658","#d59e78"][index%4];
    const hair=["#493e39","#5c4637","#393e45","#8b5a41"][index%4];
    const nod=working && !reduced.matches ? Math.sin(phase+index)*.035 : 0;
    // The chair faces the screen, with elbows resting near the keyboard.
    box(x-.33,.51,z-.35,.66,.13,.68,"#445e65");
    box(x-.30,.6,z+.22,.60,.62,.10,"#55717a");
    box(x-.09,.12,z-.06,.18,.42,.18,"#58666a");
    box(x-.34,.09,z-.07,.7,.07,.13,"#59676a");
    for(const side of [-1,1]) {
      box(x+side*.16-.09,.22,z-.46,.2,.4,.23,"#42505e");
      box(x+side*.16-.11,.16,z-.60,.23,.15,.37,"#38454a");
    }
    box(x-.26,.64,z-.25,.52,.62,.4,accent);
    for(const side of [-1,1]) {
      box(x+side*.31-.09,.92,z-.31,.19,.27,.23,accent);
      box(x+side*.31-.075,.93+nod,z-.58,.15,.15,.31,skin);
    }
    box(x-.21,1.25+nod,z-.22,.42,.42,.38,skin);
    box(x-.23,1.56+nod,z-.23,.46,.17,.42,hair);
    box(x-.22,1.36+nod,z+.065,.44,.27,.15,hair);
    if(index%3===1) box(x-.16,1.3+nod,z+.17,.31,.29,.19,hair);
    if(accent===palette.sales) {
      box(x+.20,1.42+nod,z-.12,.085,.17,.16,"#384754");
      box(x+.24,1.39+nod,z-.28,.045,.045,.19,"#384754");
    } else if(accent===palette.marketing) {
      box(x-.15,1.59+nod,z+.13,.28,.24,.23,hair);
    } else if(accent===palette.analyst) {
      box(x+.20,1.47+nod,z-.23,.04,.06,.21,"#36474b");
    }
  }
  function station(s,index,phase) {
    const [x,z]=positions[s.key], accent=tint(s);
    const wood="#cfad86";
    currentKey=s.key;
    for(const dx of [-1.13,1.04]) for(const dz of [-.49,.38])
      box(x+dx,0,z+dz,.11,.94,.11,"#586c6b");
    box(x-1.25,.92,z-.6,2.5,.14,1.2,wood);
    box(x+.64,.21,z-.39,.48,.65,.69,"#b5ac99");
    {
      box(x-.32,1.07,z-.27,.64,.055,.31,"#626e70");
      box(x-.065,1.11,z-.21,.13,.32,.12,"#626e70");
      box(x-.65,1.33,z-.38,1.3,.7,.105,"#384c55");
      screen(x,z,index);
      box(x-.41,1.065,z+.17,.82,.035,.25,"#586769");
      box(x+.54,1.07,z+.17,.13,.06,.2,"#748080");
      box(x-.98,1.07,z+.08,.16,.18,.16,accent);
      if(index%2===0) box(x+.66,1.067,z-.36,.43,.035,.44,index>3?"#b4d7dc":"#f5eed8");
      avatar(x,z+.95,index,accent,s.state==="working"||s.state==="running",phase);
    }
    currentKey=null;
  }
  function fit() {

    const bounds=[[0,3.4,0],[18.9,3.4,0],[0,3.4,10.6],[0,-.45,0],[18.9,-.45,10.6]];
    const y=bounds.map(([x,h,z])=>((x-9.25)*sin+(z-5.1)*cos)*elevation-h*vertical);
    const min=Math.min(...y), max=Math.max(...y);
    scale=Math.min((width-32)/(19.5*cos+11*sin),(height-112)/(max-min))*zoom;
    originY=height/2-2-(min+max)*scale/2;
  }

  function glass(x,z,w,d) {
    const h=1.56;
    face([[x,.1,z],[x+w,.1,z+d],[x+w,h,z+d],[x,h,z]],"rgba(108,184,190,.24)");
    const t=.065;
    box(x,0,z,w+t,.095,d+t,"#859e9b");
    box(x,h,z,w+t,.06,d+t,"#abc1be");
    for(const f of [0,.5,1]) box(x+w*f,.08,z+d*f,t,h,t,"#92aaa7");
  }
  function meeting() {
    floorRect(11,5.65,6.9,4,.04,"#c0bca7");
    for(const x of [13.2,15.7]) for(const z of [6.25,8.45]) {
      box(x-.34,.12,z-.2,.68,.45,.5,"#718b79");
      box(x-.35,.57,z-.27,.7,.12,.62,"#76917d");
      box(x-.35,.65,z+(z<7?-.29:.24),.7,.58,.1,"#779782");
    }
    box(12.9,.08,7.1,.25,.85,.6,"#806d57");box(15.9,.08,7.1,.25,.85,.6,"#806d57");
    box(12.15,.93,6.65,4.7,.16,1.5,"#c69b70");
    box(14.15,1.1,7.11,.7,.04,.48,"#e9e6d7");
  }
  const pinLayer=document.getElementById("scene-pins");
  const states={idle:"Bo‘sh",new:"Yangi",working:"Ishlayapti",ready:"Tayyor",error:"Xatolik",
    running:"Ishlayapti",waiting:"Kutilmoqda",quiet:"Faol yozuv yo‘q",offline:"Ishchi kompyuter ulanmagan"};
  const pins=new Map();
  function pick(key) { root.dispatchEvent(new CustomEvent("office-pick",{detail:key})); }
  function makePin(key,name) {
    const button=document.createElement("button");
    button.type="button"; button.className="station-pin";button.dataset.station=key;
    const title=document.createElement("b"), status=document.createElement("small");
    title.textContent=name;button.append(title,status);button.addEventListener("click",()=>pick(key));
    pinLayer.append(button);pins.set(key,button);
  }
  stations.forEach((s,i)=>{makePin(s.key,s.name);pins.get(s.key).dataset.number=i+1;});
  if(!agentFloor) makePin("board","Ish doskasi");
  function pinAt(key,point) {
    const [x,y]=project(point);
    const pin=pins.get(key);
    pin.style.left=x+"px";pin.style.top=y+"px";
  }
  function updatePins() {
    for(const s of stations) {
      const pin=pins.get(s.key);
      pin.dataset.state=s.state;pin.classList.toggle("selected",s.key===selected);
      pin.lastChild.textContent=states[s.state];pin.setAttribute("aria-label",s.name+" · "+(s.group||s.role)+" · "+states[s.state]);
    }
  }
  function roomLabel(point,text) {
    const [x,y]=project(point);
    const size=clamp(scale*.30,10,15);
    ctx.save();ctx.font="600 "+size+"px system-ui";
    const w=ctx.measureText(text).width+12,px=clamp(x,w/2+3,width-w/2-3);
    ctx.fillStyle="#f4f4e9ee";ctx.beginPath();ctx.roundRect(px-w/2,y-size,w,size+5,4);ctx.fill();
    ctx.fillStyle="#354e44";ctx.textAlign="center";ctx.fillText(text,px,y);ctx.restore();
  }
  function draw(time=0) {
    if(!ctx||!width) return;
    fit();hits=[];ctx.clearRect(0,0,width,height);shell();
    floorRect(.5,1,6.25,3.5,.04,"#c1c7b1");
    floorRect(10.65,1.25,6.15,3.35,.04,"#d4bcaa");
    floorRect(.7,6,8.95,3.55,.04,"#cec3c9");
    if(!agentFloor) meeting();
    shelf(.6,.25);plant(6.9,.73,1.35);plant(17.7,3.5);plant(.95,8.55);plant(17.65,9.45);
    glass(7.45,.15,0,3.65);glass(.15,5.25,5.8,0);glass(9.4,5.25,5.7,0);
    glass(16.7,5.25,1.7,0);glass(10.6,6.3,0,3.65);
    stations.forEach((s,i)=>station(s,i,time/350));paint();
    if(!agentFloor) {
      roomLabel([2.4,3.55,.2],"Rahbar xonasi");roomLabel([15.7,3.55,.2],"Savdo bo‘limi");
      roomLabel([5.3,-.48,10.6],"Marketing bo‘limi");roomLabel([14.8,-.48,10.6],"Yig‘ilish xonasi");
    }
    for(const s of stations) {
      const [x,z]=positions[s.key];pinAt(s.key,[x,2.08,z+.6]);
    }
    if(!agentFloor) pinAt("board",[8.8,3.25,.2]);
  }
  let drag=null, suppressClick=false;
  function camera(nextZoom, x=width/2, y=height/2) {
    const next=clamp(nextZoom,.7,2.5), ratio=next/zoom;
    panX=(panX+width/2-x)*ratio+x-width/2;
    panY=(panY+height/2-y)*ratio+y-height/2;
    zoom=next;draw();
  }
  root.querySelector(".office-tools").addEventListener("click",e=>{
    const action=e.target.closest("button")?.dataset.camera;
    if(action==="reset") { zoom=1;panX=0;panY=0;draw(); }
    if(action==="in") camera(zoom*1.2);
    if(action==="out") camera(zoom/1.2);
  });
  canvas.addEventListener("wheel",e=>{
    e.preventDefault();const rect=canvas.getBoundingClientRect();
    camera(zoom*Math.exp(-clamp(e.deltaY,-200,200)*.002),e.clientX-rect.left,e.clientY-rect.top);
  },{passive:false});
  canvas.addEventListener("pointerdown",e=>{
    if(!e.isPrimary||e.button!==0) return;
    suppressClick=false;
    drag={x:e.clientX,y:e.clientY,px:panX,py:panY,moved:false};
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove",e=>{
    if(!drag||!e.isPrimary) return;
    const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
    if(Math.hypot(dx,dy)>4) drag.moved=true;
    if(drag.moved) {panX=drag.px+dx;panY=drag.py+dy;draw();}
  });
  canvas.addEventListener("pointercancel",()=>{drag=null;});
  canvas.addEventListener("pointerup",e=>{
    if(!drag||!e.isPrimary) return;
    suppressClick=drag.moved;drag=null;
  });
  // Open the panel on the native click. On touch, opening it at pointerup
  // can deliver the subsequent synthetic click to a newly inserted button.
  canvas.addEventListener("click",e=>{
    if(!suppressClick && ctx) {
      const rect=canvas.getBoundingClientRect();
      const x=e.clientX-rect.left,y=e.clientY-rect.top;
      const hit=hits.findLast(({points})=>{
        const path=new Path2D();points.forEach(([a,b],i)=>i?path.lineTo(a,b):path.moveTo(a,b));path.closePath();
        return ctx.isPointInPath(path,x*canvas.width/width,y*canvas.height/height);
      });
      if(hit) pick(hit.key);
    }
  });
  new ResizeObserver(()=>{
    width=canvas.clientWidth;height=canvas.clientHeight;
    const ratio=Math.min(devicePixelRatio||1,2);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    if(ctx) ctx.setTransform(ratio,0,0,ratio,0,0);draw();
  }).observe(canvas);
  root.addEventListener("office-change",e=>{
    stations=e.detail.employees;selected=e.detail.selected;boardCounts=e.detail.boardCounts;
    updatePins();draw();
  });
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;}).observe(canvas);
  setInterval(()=>{if(visible&&!document.hidden&&!reduced.matches&&stations.some(s=>s.state==="working"||s.state==="running")) draw(performance.now());},180);
  updatePins();
})();
