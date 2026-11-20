/* AnglerMap Territory Manager — interfaz aislada, datos locales de demostración.
   No altera geometrías oficiales ni concede derechos de acceso. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  if (!$("profileSelect") || typeof map === "undefined") return;

  const STORE = "anglerMapTerritoryManagerV1";
  const read = () => {
    try { return JSON.parse(localStorage.getItem(STORE)) || { territories: [], rules: [], requests: [] }; }
    catch (_) { return { territories: [], rules: [], requests: [] }; }
  };
  const save = data => {
    try { localStorage.setItem(STORE, JSON.stringify(data)); return true; }
    catch (_) { alert("No se pudieron guardar los datos en este navegador."); return false; }
  };
  let data = read(), tab = "overview", draft = null, draftLayer = null;

  const style = document.createElement("style");
  style.textContent = `
  #tm-shell{position:absolute;z-index:820;inset:0;background:#071522eF;backdrop-filter:blur(9px);display:none;color:#edf5f8;font:13px Inter,system-ui,sans-serif}
  #tm-shell.open{display:flex;flex-direction:column}
  .tm-head{height:58px;flex-shrink:0;display:flex;align-items:center;gap:14px;padding:0 20px;background:#0b1d2b;border-bottom:1px solid #294456}
  .tm-brand{font-weight:850;font-size:16px;letter-spacing:.6px}.tm-brand span{color:#55d9e8}
  .tm-head small{color:#91a9b8;font-size:10px}.tm-head button{margin-left:auto}
  .tm-close,.tm-btn{border:1px solid #35566a;background:#173448;color:#edf5f8;border-radius:9px;padding:9px 12px;cursor:pointer}
  .tm-btn.primary{background:#167789;border-color:#2999aa}.tm-btn.subtle{background:transparent}
  .tm-layout{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:0;flex:1}
  .tm-nav{padding:18px 12px;border-right:1px solid #294456;background:#0b1b28}
  .tm-nav-label{font-size:9px;letter-spacing:1.5px;color:#7895a6;padding:8px 10px}
  .tm-nav button{display:flex;width:100%;gap:10px;align-items:center;text-align:left;padding:11px 12px;border:1px solid transparent;border-radius:9px;background:transparent;color:#c6d8e1;margin:3px 0;cursor:pointer}
  .tm-nav button.active,.tm-nav button:hover{background:#15384b;border-color:#2a4e62;color:#fff}
  .tm-nav button.active{color:#55d9e8}
  .tm-main{padding:24px clamp(16px,3vw,42px);overflow:auto;max-width:1240px;width:100%;margin:0 auto}
  .tm-kicker{font-size:9px;letter-spacing:1.6px;color:#55d9e8;font-weight:800}
  .tm-title{font-size:25px;font-weight:760;margin:7px 0 5px}.tm-desc{color:#9bb1be;line-height:1.6;margin:0 0 20px;max-width:760px}
  .tm-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}
  .tm-card{background:#102638;border:1px solid #29485b;border-radius:12px;padding:16px}
  .tm-card small{display:block;color:#91a9b8;font-size:10px;margin-bottom:10px}
  .tm-value{font-size:25px;font-weight:800}.tm-card p{color:#a9bdc8;font-size:11px;line-height:1.55;margin:8px 0 0}
  .tm-section{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:24px 0 10px}
  .tm-section h3{font-size:14px;margin:0}.tm-list{display:grid;gap:9px}
  .tm-row{display:flex;align-items:center;gap:14px;padding:13px;background:#0e2433;border:1px solid #29485b;border-radius:10px}
  .tm-row-main{min-width:0;flex:1}.tm-row strong{display:block;font-size:12px}.tm-row p{margin:5px 0 0;color:#91a9b8;font-size:10px;line-height:1.5}
  .tm-tag{font-size:9px;border:1px solid #5b543b;color:#e8bd70;padding:5px 8px;border-radius:20px;white-space:nowrap}
  .tm-empty{padding:24px;border:1px dashed #3b5a6d;border-radius:12px;color:#9bb1be;line-height:1.7;text-align:center}
  .tm-note{padding:12px 14px;border:1px solid #655337;background:#2a261d;border-radius:10px;color:#e5d2a8;font-size:10px;line-height:1.6;margin:15px 0}
  .tm-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:760px}
  .tm-field{display:grid;gap:6px}.tm-field.full{grid-column:1/-1}.tm-field label{font-size:10px;color:#a9bdc8}
  .tm-field input,.tm-field select,.tm-field textarea{width:100%;padding:11px;border:1px solid #35566a;border-radius:8px;background:#0a1b28;color:#edf5f8}
  .tm-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
  @media(max-width:760px){.tm-layout{grid-template-columns:1fr}.tm-nav{display:flex;overflow-x:auto;gap:4px;padding:8px;border-right:0;border-bottom:1px solid #294456}.tm-nav-label{display:none}.tm-nav button{width:auto;white-space:nowrap;padding:9px}.tm-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tm-main{padding:18px 13px}.tm-head{height:52px;padding:0 12px}.tm-head small{display:none}.tm-title{font-size:21px}}
  @media(max-width:420px){.tm-form{grid-template-columns:1fr}.tm-field.full{grid-column:auto}.tm-row{align-items:flex-start;flex-wrap:wrap}.tm-tag{margin-left:auto}}
  `;
  document.head.appendChild(style);

  const shell = document.createElement("section");
  shell.id = "tm-shell";
  shell.innerHTML = `
    <header class="tm-head"><div class="tm-brand">ANGLER<span>MAP</span></div><small>· TERRITORY MANAGER</small><button class="tm-close" id="tm-close">Volver al mapa ×</button></header>
    <div class="tm-layout">
      <nav class="tm-nav" aria-label="Administración territorial">
        <div class="tm-nav-label">GESTIÓN TERRITORIAL</div>
        <button data-tm-tab="overview" class="active">⌂ Resumen</button>
        <button data-tm-tab="territories">▱ Territorios</button>
        <button data-tm-tab="access">◇ Accesos y reglas</button>
        <button data-tm-tab="requests">⇄ Solicitudes</button>
        <button data-tm-tab="content">▤ Información</button>
      </nav>
      <main class="tm-main" id="tm-content" tabindex="-1"></main>
    </div>`;
  document.querySelector(".map-area").appendChild(shell);

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const heading = (k,t,d) => `<div class="tm-kicker">${k}</div><h1 class="tm-title">${t}</h1><p class="tm-desc">${d}</p>`;
  const empty = (symbol, message) => `<div class="tm-empty">${symbol}<br>${message}</div>`;
  const tag = text => `<span class="tm-tag">${esc(text)}</span>`;
  const row = (title, desc, status) => `<div class="tm-row"><div class="tm-row-main"><strong>${esc(title)}</strong><p>${esc(desc)}</p></div>${tag(status)}</div>`;

  function render() {
    data = read();
    document.querySelectorAll("[data-tm-tab]").forEach(b => b.classList.toggle("active", b.dataset.tmTab === tab));
    const root = $("tm-content");
    if (tab === "overview") {
      root.innerHTML = heading("CENTRO DE CONTROL", "Tu territorio, bajo control.", "Administra sectores, condiciones de acceso e información compartida desde una vista conectada al mapa.") +
        `<div class="tm-grid">
          <div class="tm-card"><small>Territorios registrados</small><div class="tm-value">${data.territories.length}</div><p>Áreas incorporadas a este espacio.</p></div>
          <div class="tm-card"><small>Reglas de acceso</small><div class="tm-value">${data.rules.length}</div><p>Condiciones guardadas localmente.</p></div>
          <div class="tm-card"><small>Solicitudes</small><div class="tm-value">${data.requests.length}</div><p>Registros de prueba recibidos.</p></div>
          <div class="tm-card"><small>Estado de cuenta</small><div class="tm-value" style="font-size:17px">Local</div><p>Sin autenticación ni sincronización.</p></div>
        </div>
        <div class="tm-note">MODO DE DEMOSTRACIÓN: los datos se guardan solo en este navegador. Aún no existe verificación de titularidad, usuarios, backend ni validez jurídica. Los datos de esta vista no modifican la cartografía oficial.</div>
        <div class="tm-section"><h3>Actividad reciente</h3><button class="tm-btn subtle" data-go="territories">Ver territorios →</button></div>
        ${data.territories.length ? data.territories.slice(-3).reverse().map(t=>row(t.name, t.commune+" · "+t.points.length+" vértices", "Borrador local")).join("") : empty("⌂","Todavía no hay territorios incorporados. Comienza creando un borrador desde el mapa.")}`;
    } else if (tab === "territories") {
      root.innerHTML = heading("DELIMITACIÓN Y FICHAS", "Territorios", "Crea borradores de áreas de gestión y organiza sus sectores. La geometría que dibujes aquí es privada y no reemplaza límites ni capas oficiales.") +
        `<div class="tm-actions"><button class="tm-btn primary" id="tm-draw">＋ Delimitar en el mapa</button><button class="tm-btn" id="tm-manual">Crear ficha sin polígono</button></div>
        <div class="tm-note" id="tm-draw-note">Para delimitar, activa la herramienta y marca al menos tres vértices en el mapa. El polígono quedará guardado como borrador local, pendiente de revisión.</div>
        <div class="tm-section"><h3>Mis territorios</h3>${tag(data.territories.length+" registros")}</div>
        <div class="tm-list">${data.territories.length ? data.territories.map((t,i)=>row(t.name,t.commune+" · "+(t.points.length>=3?"Polígono local":"Sin geometría") , "Pendiente de validar")+`<div class="tm-actions"><button class="tm-btn subtle" data-remove-territory="${i}">Eliminar borrador</button></div>`).join("") : empty("▱","Aún no has registrado territorios.")}</div>`;
      $("tm-draw").onclick = startDrawing;
      $("tm-manual").onclick = () => createTerritory([]);
      root.querySelectorAll("[data-remove-territory]").forEach(b=>b.onclick=()=>{data.territories.splice(Number(b.dataset.removeTerritory),1);save(data);render();});
    } else if (tab === "access") {
      root.innerHTML = heading("CONTROL DE INGRESO", "Accesos y reglas", "Registra condiciones operativas para tus sectores. Una regla documentada en esta demo no constituye autorización legal ni acredita un derecho de acceso.") +
        `<form id="tm-rule-form" class="tm-form">
          <div class="tm-field"><label for="tm-sector">Sector o territorio</label><input id="tm-sector" required maxlength="90" placeholder="Nombre del sector"></div>
          <div class="tm-field"><label for="tm-type">Tipo de condición</label><select id="tm-type"><option>Acceso autorizado</option><option>Acceso restringido</option><option>Requiere coordinación previa</option><option>Acceso público por verificar</option></select></div>
          <div class="tm-field"><label for="tm-season">Vigencia o temporada</label><input id="tm-season" maxlength="80" placeholder="Ej. Octubre–abril"></div>
          <div class="tm-field"><label for="tm-capacity">Cupo diario (opcional)</label><input id="tm-capacity" type="number" min="0" max="999" placeholder="Sin definir"></div>
          <div class="tm-field full"><label for="tm-notes">Instrucciones y observaciones</label><textarea id="tm-notes" rows="3" maxlength="500" placeholder="Condiciones de coordinación, estacionamiento, bioseguridad…"></textarea></div>
          <div class="tm-field full"><div class="tm-actions"><button class="tm-btn primary" type="submit">Guardar regla local</button></div></div>
        </form>
        <div class="tm-section"><h3>Reglas registradas</h3>${tag(data.rules.length+" reglas")}</div>
        <div class="tm-list">${data.rules.length ? data.rules.map((r,i)=>row(r.sector,r.type+" · "+(r.season||"Sin vigencia")+(r.notes?" · "+r.notes:""),"Borrador local")+ `<button class="tm-btn subtle" data-remove-rule="${i}">Eliminar</button>`).join("") : empty("◇","No hay condiciones registradas.")}</div>`;
      $("tm-rule-form").onsubmit=e=>{e.preventDefault();data.rules.push({sector:$("tm-sector").value.trim(),type:$("tm-type").value,season:$("tm-season").value.trim(),capacity:$("tm-capacity").value,notes:$("tm-notes").value.trim()});if(save(data))render();};
      root.querySelectorAll("[data-remove-rule]").forEach(b=>b.onclick=()=>{data.rules.splice(Number(b.dataset.removeRule),1);save(data);render();});
    } else if (tab === "requests") {
      root.innerHTML = heading("COORDINACIÓN", "Solicitudes", "Este espacio está preparado para revisar solicitudes de ingreso, coordinación con guías y disponibilidad. La recepción real requiere cuentas y un servicio backend.") +
        `<div class="tm-note">Las solicitudes que aparecen aquí son registros locales de demostración; no se envían a propietarios ni a terceros.</div>
        <div class="tm-section"><h3>Bandeja de solicitudes</h3>${tag(data.requests.length+" solicitudes")}</div>
        ${data.requests.length ? data.requests.map(r=>row(r.name,r.date+" · "+r.message,r.status)).join("") : empty("⇄","No hay solicitudes. La bandeja se habilitará cuando exista el sistema de cuentas y reservas.")}`;
    } else {
      root.innerHTML = heading("CONTENIDO TERRITORIAL", "Información y validación", "Mantén información útil para visitantes y guías: instrucciones, observaciones de terreno, condiciones y referencias verificables.") +
        `<div class="tm-grid">
          <div class="tm-card"><small>Información pública</small><div class="tm-value">01</div><p>Fichas y descripciones territoriales.</p></div>
          <div class="tm-card"><small>Validación documental</small><div class="tm-value">—</div><p>Pendiente de identidad y respaldo documental.</p></div>
        </div>
        <div class="tm-note">Las fuentes oficiales (DGA, MOP y otras) se mantienen como capas de referencia independientes. Un administrador territorial no podrá editar ni sobrescribir sus nombres o geometrías.</div>
        ${row("Ficha territorial","Descripción, normas operativas, temporadas y observaciones.","Diseño pendiente")}
        ${row("Registro de cambios","Autor, fecha, motivo y estado de revisión.","Backend pendiente")}
        ${row("Evidencia y documentos","Acreditación de representación, permisos y autorizaciones.","Verificación pendiente")}`;
    }
    root.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>{tab=b.dataset.go;render();});
  }

  function open() { shell.classList.add("open"); $("adminSection").hidden=false; render(); }
  function close() { shell.classList.remove("open"); if(draft){draft=null; if(draftLayer){map.removeLayer(draftLayer);draftLayer=null;}} }
  function createTerritory(points) {
    const name=prompt("Nombre del territorio o sector:");
    if(!name || !name.trim()) return;
    const commune=prompt("Comuna:", "Por definir") || "Por definir";
    data=read(); data.territories.push({name:name.trim(),commune:commune.trim(),points:points.map(p=>[p.lat,p.lng]),createdAt:new Date().toISOString(),status:"draft"});
    save(data); draft=null; if(draftLayer){map.removeLayer(draftLayer);draftLayer=null;} tab="territories";render();
  }
  function startDrawing() {
    if(draft){draft=null;if(draftLayer){map.removeLayer(draftLayer);draftLayer=null;}}
    draft=[]; $("tm-draw-note").textContent="Modo de delimitación activo: haz clic en el mapa para agregar vértices. Se requieren tres o más puntos. Pulsa «Finalizar» cuando termines.";
    const finish=document.createElement("button");finish.className="tm-btn primary";finish.id="tm-finish";finish.textContent="Finalizar polígono";$("tm-draw-note").appendChild(finish);
    finish.onclick=()=>{if(!draft||draft.length<3){alert("Marca al menos tres vértices.");return;}createTerritory(draft);};
    const cancel=document.createElement("button");cancel.className="tm-btn";cancel.textContent="Cancelar";cancel.style.marginLeft="8px";$("tm-draw-note").appendChild(cancel);
    cancel.onclick=()=>{draft=null;if(draftLayer){map.removeLayer(draftLayer);draftLayer=null;}render();};
  }
  map.on("click", e=>{
    if(!draft || !shell.classList.contains("open") || tab!=="territories") return;
    draft.push(e.latlng);
    if(draftLayer)map.removeLayer(draftLayer);
    draftLayer=(draft.length>=3?L.polygon(draft,{color:"#55d9e8",weight:2,dashArray:"6 5",fillColor:"#258ba8",fillOpacity:.18}):L.polyline(draft,{color:"#55d9e8",weight:2,dashArray:"6 5"})).addTo(map);
    if(draft.length>1)map.fitBounds(draftLayer.getBounds(),{padding:[80,80],maxZoom:13});
  });

  shell.querySelectorAll("[data-tm-tab]").forEach(b=>b.addEventListener("click",()=>{tab=b.dataset.tmTab;render();}));
  $("tm-close").onclick=close;
  $("profileSelect").addEventListener("change",e=>{
    if(e.target.value==="admin")open(); else close();
  });
  $("territoryBtn").onclick=()=>{tab="territories";open();};
  $("accessBtn").onclick=()=>{tab="access";open();};
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&shell.classList.contains("open"))close();});
  console.info("AnglerMap Territory Manager: interfaz demo cargada; sin backend ni permisos reales.");
})();