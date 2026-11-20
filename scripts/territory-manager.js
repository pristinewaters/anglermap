/* AnglerMap Territory Manager — interfaz aislada, datos locales de demostración.
   No altera geometrías oficiales ni concede derechos de acceso. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  if (!$("profileSelect") || typeof map === "undefined") return;

  const STORE = "anglerMapTerritoryManagerV1";
  const read = () => {
    try {
      const value = JSON.parse(localStorage.getItem(STORE)) || {};
      return { territories: [], rules: [], requests: [], imports: [], pilot: {sections:[],accessPoints:[],bookings:[],operators:[],policies:[]}, ...value,
        territories: Array.isArray(value.territories) ? value.territories.map((t,i)=>({...t,id:t.id||"legacy-"+i})) : [],
        imports: Array.isArray(value.imports) ? value.imports : [],
        pilot: {sections:[],accessPoints:[],bookings:[],operators:[],policies:[],...(value.pilot||{})} };
    } catch (_) { return { territories: [], rules: [], requests: [], imports: [] }; }
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
  .tm-import{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:15px;background:#0e2433;border:1px solid #29485b;border-radius:10px;margin:14px 0}
  .tm-import input{max-width:100%;color:#c6d8e1;font-size:11px}.tm-import small{display:block;color:#91a9b8;line-height:1.5;margin-top:4px}
  .tm-import-list{display:grid;gap:8px;margin-top:10px}.tm-import-item{display:flex;align-items:center;gap:12px;padding:12px;background:#0e2433;border:1px solid #29485b;border-radius:9px}
  .tm-import-item strong{display:block;font-size:11px}.tm-import-item small{color:#91a9b8;font-size:10px}
  .tm-import-item button{margin-left:auto}
  .tm-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:760px}
  .tm-field{display:grid;gap:6px}.tm-field.full{grid-column:1/-1}.tm-field label{font-size:10px;color:#a9bdc8}
  .tm-field input,.tm-field select,.tm-field textarea{width:100%;padding:11px;border:1px solid #35566a;border-radius:8px;background:#0a1b28;color:#edf5f8}
  .tm-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
  .tm-pilot-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(260px,1fr);gap:14px}
  .tm-pilot-panel{background:#0e2433;border:1px solid #29485b;border-radius:12px;padding:15px;margin:12px 0}
  .tm-pilot-panel h3{font-size:13px;margin:0 0 10px}
  .tm-pilot-metric{font-size:24px;font-weight:800}
  .tm-pilot-muted{color:#91a9b8;font-size:10px;line-height:1.5}
  .tm-pilot-list{display:grid;gap:8px}
  .tm-pilot-item{padding:11px;border:1px solid #29485b;border-radius:9px;background:#102638}
  .tm-pilot-item strong{font-size:12px}.tm-pilot-item small{display:block;color:#91a9b8;margin-top:4px;line-height:1.5}
  .tm-pilot-item button{margin:8px 5px 0 0}
  .tm-pilot-checks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .tm-pilot-checks label{display:flex;gap:8px;align-items:flex-start;color:#c6d8e1;font-size:11px}
  .tm-pilot-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .tm-pilot-form .full{grid-column:1/-1}
  .tm-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0 18px}
  .tm-toolbar-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .tm-icon-btn{width:40px;height:40px;border:1px solid #35566a;border-radius:11px;background:#173448;color:#eaf5f8;font-size:19px;cursor:pointer}
  .tm-hero{padding:20px;border:1px solid #2b596b;border-radius:16px;background:linear-gradient(120deg,#12374a,#102638 65%,#142d40);display:flex;justify-content:space-between;gap:16px;align-items:center}
  .tm-hero h2{font-size:20px;margin:5px 0}.tm-hero p{color:#b2c7d1;margin:0;line-height:1.5;font-size:11px}
  .tm-metric{border-left:3px solid #55d9e8}.tm-metric.good{border-left-color:#48c78e}.tm-metric.warn{border-left-color:#e8bd70}.tm-metric.full{border-left-color:#e66c6c}
  .tm-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}
  .tm-day{border:1px solid #29485b;border-radius:9px;background:#102638;color:#dceaf0;padding:9px 4px;text-align:center;cursor:pointer;min-height:62px}
  .tm-day small{display:block;color:#91a9b8;font-size:9px;margin-top:5px}.tm-day.selected{outline:2px solid #55d9e8;background:#15384b}
  .tm-day.busy{border-bottom:3px solid #e8bd70}.tm-day.full{border-bottom:3px solid #e66c6c}.tm-day.free{border-bottom:3px solid #48c78e}
  .tm-availability{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .tm-slot{padding:12px;border:1px solid #29485b;border-radius:10px;background:#102638;cursor:pointer;text-align:left;color:#edf5f8}
  .tm-slot strong{display:block;font-size:12px}.tm-slot small{display:block;color:#a9bdc8;margin-top:5px}
  .tm-status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#48c78e}.tm-status.warn{background:#e8bd70}.tm-status.full{background:#e66c6c}
  .tm-modal{padding:16px;background:#132f42;border:1px solid #55d9e8;border-radius:13px;margin:14px 0}
  .tm-operator-card{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}
  .tm-legend{display:flex;gap:14px;flex-wrap:wrap;color:#a9bdc8;font-size:10px}
  @media(max-width:760px){.tm-hero{align-items:flex-start;flex-direction:column}.tm-calendar{gap:3px}.tm-day{padding:7px 2px}.tm-availability{grid-template-columns:1fr}}
  @media(max-width:760px){.tm-pilot-grid{grid-template-columns:1fr}.tm-pilot-checks{grid-template-columns:1fr}}

  @media(max-width:760px){.tm-layout{grid-template-columns:1fr}.tm-nav{display:flex;overflow-x:auto;gap:4px;padding:8px;border-right:0;border-bottom:1px solid #294456}.tm-nav-label{display:none}.tm-nav button{width:auto;white-space:nowrap;padding:9px}.tm-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.tm-main{padding:18px 13px}.tm-head{height:52px;padding:0 12px}.tm-head small{display:none}.tm-title{font-size:21px}}
  @media(max-width:420px){.tm-form{grid-template-columns:1fr}.tm-field.full{grid-column:auto}.tm-row{align-items:flex-start;flex-wrap:wrap}.tm-tag{margin-left:auto}}

  /* Navegación agrupada: etiquetas cortas, estados claros y adaptación móvil. */
  .tm-nav{overflow:auto;scrollbar-width:thin;scrollbar-color:#29485b transparent}
  .tm-nav-group{margin:0 0 13px}
  .tm-nav-label{padding:10px 10px 6px;font-size:9px;letter-spacing:1.2px;color:#7895a6;font-weight:800}
  .tm-nav button{min-height:40px;font-size:12px}
  .tm-nav button:focus-visible,.tm-btn:focus-visible,.tm-close:focus-visible{outline:3px solid #7ce7f2;outline-offset:2px}
  .tm-nav button.active{box-shadow:inset 3px 0 #55d9e8}
  .tm-main{scroll-behavior:smooth}
  @media(max-width:760px){.tm-nav{position:sticky;top:0;z-index:5;align-items:center;scroll-snap-type:x proximity}.tm-nav-group{display:flex;gap:4px;align-items:center;flex-shrink:0;margin:0}.tm-nav-group .tm-nav-label{display:none}.tm-nav button{scroll-snap-align:start;min-height:38px}.tm-nav button span{display:inline}.tm-nav button.active{box-shadow:inset 0 -3px #55d9e8}}
  `;

  style.textContent += `
/* Territory Manager redesign: task navigation across the top, spacious work area */
  #tm-shell{background:#071521f7;backdrop-filter:blur(16px)}
  .tm-head{height:66px;padding:0 clamp(14px,2.5vw,34px);gap:14px;background:#081a28;border-bottom:1px solid #203d50}
  .tm-brand{font-size:17px;letter-spacing:1.2px}
  .tm-head small{font-size:9px;letter-spacing:1.25px;text-transform:uppercase}
  .tm-head .tm-icon-btn{margin-left:auto}
  .tm-close{font-size:11px;padding:10px 14px;border-radius:10px;background:#15384b}
  .tm-layout{display:flex;flex-direction:column;min-height:0;flex:1}
  .tm-nav{display:flex;align-items:center;gap:5px;padding:8px clamp(12px,2.5vw,34px);border-right:0;border-bottom:1px solid #203d50;background:#0a1d2b;overflow-x:auto;scrollbar-width:thin}
  .tm-nav-group{display:flex;align-items:center;gap:4px;margin:0;flex-shrink:0}
  .tm-nav-label{display:none}
  .tm-nav button{width:auto;min-height:39px;margin:0;padding:9px 13px;white-space:nowrap;border-radius:9px;font-size:11px}
  .tm-nav button.active{background:#173d51;border-color:#2c5b72;box-shadow:inset 0 -2px #55d9e8;color:#e9fbff}
  .tm-main{max-width:1500px;padding:clamp(18px,2.5vw,34px);overflow:auto}
  .tm-kicker{font-size:9px;letter-spacing:1.8px}
  .tm-title{font-size:clamp(24px,2.3vw,32px);letter-spacing:-.5px;margin:6px 0 4px}
  .tm-desc{font-size:11px;line-height:1.45;margin:0 0 14px;max-width:680px;color:#91a9b8}
  .tm-toolbar{margin:4px 0 14px}
  .tm-hero{min-height:112px;padding:22px 24px;border-radius:15px;background:linear-gradient(110deg,#123b50 0%,#102a3c 56%,#102537 100%);border-color:#2a566c}
  .tm-hero h2{font-size:22px;letter-spacing:-.3px}
  .tm-hero p{font-size:10px}
  .tm-grid{gap:9px;margin:13px 0}
  .tm-card{padding:13px 15px;border-radius:11px;background:#0e2332;border-color:#203f52}
  .tm-card small{font-size:9px;margin-bottom:7px;color:#91a9b8}
  .tm-value{font-size:23px;letter-spacing:-.5px}
  .tm-card p{font-size:9px;margin-top:5px;color:#809aaa}
  .tm-pilot-grid{grid-template-columns:minmax(0,1.55fr) minmax(290px,.9fr);gap:12px}
  .tm-pilot-panel{padding:15px;border-radius:12px;background:#0b2030;border-color:#203f52}
  .tm-pilot-panel h3,.tm-section h3{font-size:12px;letter-spacing:.1px}
  .tm-calendar{gap:5px}
  .tm-day{min-height:54px;padding:7px 3px;border-radius:8px;background:#10283a;border-color:#25465a}
  .tm-day strong{font-size:12px}
  .tm-day small{font-size:8px}
  .tm-slot{padding:10px 11px;border-radius:9px;background:#10283a;border-color:#25465a}
  .tm-slot strong{font-size:11px}
  .tm-slot small{font-size:9px}
  .tm-pilot-item{padding:10px;border-radius:9px;background:#10283a;border-color:#25465a}
  .tm-pilot-item strong{font-size:11px}
  .tm-pilot-item small{font-size:9px}
  .tm-btn{font-size:10px;padding:9px 11px;border-radius:9px}
  .tm-btn.primary{background:#12657a;border-color:#258da2}
  .tm-note{font-size:9px;padding:9px 12px;margin:12px 0;border-radius:9px}
  .tm-row{padding:11px 12px;border-radius:9px;background:#0d2332;border-color:#203f52}
  .tm-empty{padding:20px;border-radius:10px;font-size:11px}
  .tm-import{border-radius:10px;background:#0d2332;border-color:#203f52}
  .tm-form{gap:10px}
  .tm-field input,.tm-field select,.tm-field textarea{border-radius:9px;background:#091b29;border-color:#2a4b60;font-size:11px}
  .tm-tag{font-size:8px;letter-spacing:.3px}
  @media(max-width:760px){
    .tm-head{height:55px;padding:0 10px;gap:8px}
    .tm-brand{font-size:14px}
    .tm-head small{display:none}
    .tm-close{padding:8px 10px;font-size:9px}
    .tm-nav{padding:7px 8px;gap:4px}
    .tm-nav button{min-height:36px;padding:8px 10px;font-size:10px}
    .tm-main{padding:16px 11px}
    .tm-grid{gap:7px}
    .tm-card{padding:11px}
    .tm-value{font-size:20px}
    .tm-pilot-grid{grid-template-columns:1fr}
    .tm-hero{padding:17px}
    .tm-hero h2{font-size:19px}
  }
  @media(max-width:420px){
    .tm-title{font-size:22px}
    .tm-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
    .tm-nav button{padding:7px 9px}
  }
  `;


  /* Territory Manager · sistema visual claro y coherente con el explorador */
  #tm-shell{background:#f5f7fa!important;color:#172b3d!important;backdrop-filter:none!important}
  #tm-shell .tm-head{background:#fff!important;border-bottom:1px solid #dce4ec!important;color:#172b3d!important}
  #tm-shell .tm-brand{color:#17334a!important}.tm-brand span{color:#1683b8!important}
  #tm-shell .tm-head small{color:#718397!important}
  #tm-shell .tm-nav{background:#fff!important;border-bottom:1px solid #dce4ec!important}
  #tm-shell .tm-nav button{color:#526a7d!important;background:transparent!important;border-color:transparent!important}
  #tm-shell .tm-nav button:hover,#tm-shell .tm-nav button.active{background:#edf6fb!important;border-color:#d7e8f3!important;color:#145d8b!important;box-shadow:inset 0 -2px #1683b8!important}
  #tm-shell .tm-main{color:#172b3d!important}
  #tm-shell .tm-kicker{color:#1683b8!important}
  #tm-shell .tm-title,#tm-shell .tm-section h3,#tm-shell .tm-pilot-panel h3{color:#172b3d!important}
  #tm-shell .tm-desc,#tm-shell .tm-pilot-muted,#tm-shell .tm-row p,#tm-shell .tm-card p{color:#64788a!important}
  #tm-shell .tm-card,#tm-shell .tm-pilot-panel,#tm-shell .tm-row,#tm-shell .tm-import,#tm-shell .tm-import-item,#tm-shell .tm-pilot-item{background:#fff!important;border-color:#dce4ec!important;color:#172b3d!important;box-shadow:0 2px 8px #1d355008!important}
  #tm-shell .tm-card small,#tm-shell .tm-import-item small,#tm-shell .tm-pilot-item small{color:#718397!important}
  #tm-shell .tm-value,#tm-shell .tm-pilot-metric,#tm-shell .tm-row strong,#tm-shell .tm-pilot-item strong{color:#172b3d!important}
  #tm-shell .tm-hero{background:#edf6fb!important;border-color:#d7e8f3!important;color:#172b3d!important}
  #tm-shell .tm-hero h2{color:#17334a!important}#tm-shell .tm-hero p{color:#526a7d!important}
  #tm-shell .tm-btn,#tm-shell .tm-close{background:#f4f8fb!important;border-color:#dce4ec!important;color:#31536d!important}
  #tm-shell .tm-btn.primary{background:#176eaa!important;border-color:#176eaa!important;color:#fff!important}
  #tm-shell .tm-btn.subtle{background:#fff!important;color:#526a7d!important}
  #tm-shell .tm-icon-btn{background:#f4f8fb!important;border-color:#dce4ec!important;color:#31536d!important}
  #tm-shell .tm-tag{background:#f5f8fb!important;border-color:#dce4ec!important;color:#526a7d!important}
  #tm-shell .tm-empty{background:#fff!important;border-color:#dce4ec!important;color:#718397!important}
  #tm-shell .tm-note{background:#fff8eb!important;border-color:#f0dfbd!important;color:#765a2c!important}
  #tm-shell .tm-field label,#tm-shell .tm-pilot-checks label{color:#526a7d!important}
  #tm-shell .tm-field input,#tm-shell .tm-field select,#tm-shell .tm-field textarea,#tm-shell .tm-import input{background:#fff!important;border-color:#dce4ec!important;color:#172b3d!important}
  #tm-shell .tm-day,#tm-shell .tm-slot{background:#fff!important;border-color:#dce4ec!important;color:#31536d!important}
  #tm-shell .tm-day.selected{outline-color:#1683b8!important;background:#edf6fb!important}
  #tm-shell .tm-modal{background:#edf6fb!important;border-color:#d7e8f3!important;color:#31536d!important}
  #tm-shell .tm-status{background:#29966b!important}
  #tm-shell button:focus-visible,#tm-shell input:focus-visible,#tm-shell select:focus-visible{outline:3px solid #1683b8!important;outline-offset:2px!important}
  @media(max-width:760px){#tm-shell .tm-nav{background:#fff!important}#tm-shell .tm-nav button.active{box-shadow:inset 0 -3px #1683b8!important}}

  document.head.appendChild(style);

  const shell = document.createElement("section");
  shell.id = "tm-shell";
  shell.innerHTML = `
    <header class="tm-head"><div class="tm-brand">ANGLER<span>MAP</span></div><small>· TERRITORY MANAGER</small><button class="tm-icon-btn" id="tm-settings" title="Configuración del territorio" aria-label="Configuración">⚙</button><button class="tm-close" id="tm-close">Volver al mapa ×</button></header>
    <div class="tm-layout">
      <nav class="tm-nav" aria-label="Administración territorial">
        <div class="tm-nav-group"><div class="tm-nav-label">INICIO</div><button data-tm-tab="overview" class="active" title="Resumen general">⌂ <span>Resumen</span></button></div>
        <div class="tm-nav-group"><div class="tm-nav-label">MI TERRITORIO</div><button data-tm-tab="rio-medio" title="Administrar Río del Medio">〰 <span>Río del Medio</span></button><button data-tm-tab="territories" title="Territorios y sectores">▱ <span>Territorios</span></button><button data-tm-tab="access" title="Accesos y condiciones">◇ <span>Accesos y reglas</span></button></div>
        <div class="tm-nav-group"><div class="tm-nav-label">OPERACIÓN</div><button data-tm-tab="requests" title="Solicitudes de ingreso">⇄ <span>Solicitudes</span></button><button data-tm-tab="operators" title="Operadores y convenios">♧ <span>Operadores</span></button><button data-tm-tab="team" title="Equipo de trabajo">♙ <span>Equipo</span></button></div>
        <div class="tm-nav-group"><div class="tm-nav-label">EXPERIENCIA DE USUARIOS</div><button data-tm-tab="angler-portal" title="Vista del pescador">⌖ <span>Vista pescador</span></button><button data-tm-tab="operator-portal" title="Vista del operador">▣ <span>Vista operador</span></button><button data-tm-tab="content" title="Información pública">▤ <span>Información pública</span></button></div>
        <div class="tm-nav-group"><div class="tm-nav-label">PREFERENCIAS</div><button data-tm-tab="settings" title="Configuración">⚙ <span>Configuración</span></button></div>
      </nav>
      <main class="tm-main" id="tm-content" tabindex="-1"></main>
    </div>`;
  document.querySelector(".map-area").appendChild(shell);

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const heading = (k,t,d) => `<div class="tm-page-heading"><div class="tm-kicker">${k}</div><h1 class="tm-title">${t}</h1><p class="tm-desc">${d}</p></div>`;
  const empty = (symbol, message) => `<div class="tm-empty">${symbol}<br>${message}</div>`;
  const tag = text => `<span class="tm-tag">${esc(text)}</span>`;
  const row = (title, desc, status) => `<div class="tm-row"><div class="tm-row-main"><strong>${esc(title)}</strong><p>${esc(desc)}</p></div>${tag(status)}</div>`;

  function render() {
    data = read();
    document.querySelectorAll("[data-tm-tab]").forEach(b => b.classList.toggle("active", b.dataset.tmTab === tab));
    const root = $("tm-content");
    if (tab === "overview") {
      const p=pilotData(), bookings=p.bookings||[], today=new Date().toISOString().slice(0,10);
      const confirmed=bookings.filter(b=>b.status==="confirmed"), pending=bookings.filter(b=>b.status==="pending");
      const revenue=confirmed.reduce((n,b)=>n+Number(b.totalAmount||0),0);
      const selectedDate=window.tmSelectedDate||today;
      const week=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()+i);return d.toISOString().slice(0,10);});
      const occupancyFor=date=>p.sections.reduce((n,sec)=>n+pilotCount(p,sec.id,date),0);
      const calendar=week.map(date=>{const used=occupancyFor(date),cap=p.sections.length*4,cls=!cap||!used?"free":used>=cap?"full":"busy";return '<button class="tm-day '+cls+' '+(date===selectedDate?'selected':'')+'" data-dashboard-date="'+date+'"><strong>'+date.slice(8,10)+'</strong><small>'+date.slice(5,7)+' · '+(cap?used+'/'+cap:'Sin sectores')+'</small></button>';}).join("");
      const slots=p.sections.map(sec=>{const used=pilotCount(p,sec.id,selectedDate),left=Math.max(0,4-used),cls=left===0?"full":used?"warn":"";return '<button class="tm-slot" data-dashboard-section="'+esc(sec.id)+'"><strong><span class="tm-status '+cls+'"></span>'+esc(sec.name)+'</strong><small>'+left+' de 4 cupos disponibles · '+used+' reservados</small></button>';}).join("");
      root.innerHTML=heading("PANEL DE CONTROL","La operación de tu territorio","Una vista rápida de reservas, ocupación y actividad. Entra solo cuando haya algo que gestionar.")+
      '<div class="tm-toolbar"><div class="tm-pilot-muted">RESUMEN OPERATIVO · '+new Date().toLocaleDateString("es-CL")+'</div><div class="tm-toolbar-actions"><button class="tm-btn" data-go="requests">Ver reservas</button><button class="tm-icon-btn" data-go="settings" title="Configuración">⚙</button></div></div>'+
      '<div class="tm-hero"><div><div class="tm-kicker">TERRITORIO ACTIVO</div><h2>Río del Medio</h2><p>'+p.sections.length+' sectores configurados · '+p.operators.length+' operadores con convenio · temporada '+esc(p.seasonStart)+' a '+esc(p.seasonEnd)+'</p></div><button class="tm-btn primary" id="tm-dashboard-map">Ver territorio en el mapa ↗</button></div>'+
      '<div class="tm-grid"><div class="tm-card tm-metric warn"><small>Solicitudes por revisar</small><div class="tm-value">'+pending.length+'</div><p>Requieren una decisión.</p></div><div class="tm-card tm-metric good"><small>Reservas confirmadas</small><div class="tm-value">'+confirmed.length+'</div><p>Reservas aprobadas.</p></div><div class="tm-card tm-metric"><small>Operadores activos</small><div class="tm-value">'+p.operators.length+'</div><p>Convenios registrados.</p></div><div class="tm-card tm-metric"><small>Ingresos comprometidos</small><div class="tm-value">$'+revenue.toLocaleString("es-CL")+'</div><p>Estimación de reservas confirmadas.</p></div></div>'+
      '<div class="tm-pilot-grid"><div class="tm-pilot-panel"><div class="tm-section" style="margin-top:0"><h3>Disponibilidad · próximos 7 días</h3><span class="tm-pilot-muted">Selecciona una fecha</span></div><div class="tm-calendar">'+calendar+'</div><div class="tm-section"><h3>Sectores · '+selectedDate+'</h3></div><div class="tm-availability">'+(slots||empty("〰","Agrega sectores para ver su disponibilidad."))+'</div><div class="tm-legend" style="margin-top:13px"><span><i class="tm-status"></i>Disponible</span><span><i class="tm-status warn"></i>Con reservas</span><span><i class="tm-status full"></i>Completo</span></div></div>'+
      '<div class="tm-pilot-panel"><h3>Atención requerida</h3>'+(pending.length?pending.slice(0,4).map(b=>'<div class="tm-pilot-item"><strong>'+esc(b.operator||b.anglerName||"Solicitud")+'</strong><small>'+esc(b.date)+' · '+esc(b.sectionName)+' · '+b.anglers+' pescador(es)</small><button class="tm-btn primary" data-go="requests">Revisar solicitud</button></div>').join(""):empty("✓","No tienes solicitudes pendientes."))+'<div class="tm-section"><h3>Accesos rápidos</h3></div><div class="tm-actions"><button class="tm-btn" data-go="operators">＋ Nuevo operador</button><button class="tm-btn" data-go="team">Gestionar equipo</button><button class="tm-btn" data-go="rio-medio">Administrar sectores</button></div></div></div>'+
      '<div class="tm-note">DEMO LOCAL: los indicadores se calculan con los registros de este navegador. Los ingresos son estimaciones, no pagos recibidos. La disponibilidad real compartida requiere backend.</div>';
      root.querySelectorAll("[data-dashboard-date]").forEach(b=>b.onclick=()=>{window.tmSelectedDate=b.dataset.dashboardDate;render();});
      root.querySelectorAll("[data-dashboard-section]").forEach(b=>b.onclick=()=>{tab="rio-medio";render();});
      root.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>{tab=b.dataset.go;render();});
      $("tm-dashboard-map").onclick=()=>{close();showAvailabilityMap(selectedDate);};
    } else if (tab === "territories") {
      root.innerHTML = heading("DELIMITACIÓN Y FICHAS", "Territorios", "Crea borradores de áreas de gestión y organiza sus sectores. La geometría que dibujes aquí es privada y no reemplaza límites ni capas oficiales.") +
        `<div class="tm-actions"><button class="tm-btn primary" id="tm-draw">＋ Delimitar en el mapa</button><button class="tm-btn" id="tm-manual">Crear ficha sin polígono</button></div>
        <div class="tm-note" id="tm-draw-note">Para delimitar, activa la herramienta y marca al menos tres vértices en el mapa. El polígono quedará guardado como borrador local, pendiente de revisión.</div>
        <div class="tm-section"><h3>Cartografía de referencia</h3>${tag(data.imports.length+" archivos")}</div>
        <div class="tm-import"><div><strong>Incorporar límites prediales o de estancias</strong><small>Formatos admitidos: GeoJSON (.geojson/.json) y KML (.kml). Máximo 10 MB y 10.000 elementos por archivo.</small></div><input id="tm-import-file" type="file" accept=".geojson,.json,.kml,application/geo+json,application/json,application/vnd.google-earth.kml+xml"><button class="tm-btn primary" id="tm-import-btn">Importar archivo</button></div>
        <div class="tm-note">Los archivos importados se guardan solo en este navegador. Se muestran como referencia pendiente de validación; no acreditan propiedad, deslindes vigentes, titularidad ni derechos de acceso. Se conserva el nombre del archivo y la fuente declarada.</div>
        <div class="tm-import-list">${data.imports.length ? data.imports.map((item,i)=>`<div class="tm-import-item"><div><strong>${esc(item.name)}</strong><small>${esc(item.fileName)} · ${esc(item.format)} · ${item.featureCount} elementos · Fuente: ${esc(item.source||"No declarada")} · Pendiente de validar</small></div><button class="tm-btn subtle" data-zoom-import="${i}">Ver en mapa</button><button class="tm-btn subtle" data-remove-import="${i}">Quitar</button></div>`).join("") : empty("▧","Todavía no has importado archivos geográficos.")}</div>
        <div class="tm-section"><h3>Mis territorios</h3>${tag(data.territories.length+" registros")}</div>
        <div class="tm-list">${data.territories.length ? data.territories.map((t,i)=>row(t.name,(t.waterbody||"Cuerpo de agua por asociar")+" · "+t.commune+" · "+(t.points.length>=3?"Polígono local":"Sin geometría") , "Pendiente de validar")+`<div class="tm-actions"><button class="tm-btn subtle" data-remove-territory="${i}">Eliminar borrador</button></div>`).join("") : empty("▱","Aún no has registrado territorios.")}</div>`;
      $("tm-draw").onclick = startDrawing;
      $("tm-manual").onclick = () => createTerritory([]);
      $("tm-import-btn").onclick = importTerritoryFile;
      root.querySelectorAll("[data-remove-import]").forEach(b=>b.onclick=()=>{data.imports.splice(Number(b.dataset.removeImport),1);save(data);refreshImportedLayers();render();});
      root.querySelectorAll("[data-zoom-import]").forEach(b=>b.onclick=()=>zoomImported(Number(b.dataset.zoomImport)));
      root.querySelectorAll("[data-remove-territory]").forEach(b=>b.onclick=()=>{data.territories.splice(Number(b.dataset.removeTerritory),1);save(data);render();});
    } else if (tab === "access") {
      root.innerHTML = heading("CONTROL DE INGRESO", "Accesos y reglas", "Registra condiciones operativas para tus sectores. Una regla documentada en esta demo no constituye autorización legal ni acredita un derecho de acceso.") +
        `<form id="tm-rule-form" class="tm-form">
          <div class="tm-field"><label for="tm-territory">Territorio relacionado</label><select id="tm-territory"><option value="">Regla general · sin vincular</option>${data.territories.map(t=>'<option value="'+esc(t.id||"")+'">'+esc(t.name)+" · "+esc(t.commune)+'</option>').join("")}</select></div>
          <div class="tm-field"><label for="tm-sector">Sector o referencia</label><input id="tm-sector" required maxlength="90" placeholder="Ej. Acceso por portón norte"></div>
          <div class="tm-field"><label for="tm-type">Tipo de condición</label><select id="tm-type"><option>Acceso autorizado</option><option>Acceso restringido</option><option>Requiere coordinación previa</option><option>Acceso público por verificar</option></select></div>
          <div class="tm-field"><label for="tm-season">Vigencia o temporada</label><input id="tm-season" maxlength="80" placeholder="Ej. Octubre–abril"></div>
          <div class="tm-field"><label for="tm-capacity">Cupo diario (opcional)</label><input id="tm-capacity" type="number" min="0" max="999" placeholder="Sin definir"></div>
          <div class="tm-field full"><label for="tm-notes">Instrucciones y observaciones</label><textarea id="tm-notes" rows="3" maxlength="500" placeholder="Condiciones de coordinación, estacionamiento, bioseguridad…"></textarea></div>
          <div class="tm-field full"><div class="tm-actions"><button class="tm-btn primary" type="submit">Guardar regla local</button></div></div>
        </form>
        <div class="tm-section"><h3>Reglas registradas</h3>${tag(data.rules.length+" reglas")}</div>
        <div class="tm-list">${data.rules.length ? data.rules.map((r,i)=>row(r.sector,(r.territoryId ? (data.territories.find(t=>t.id===r.territoryId)?.name||"Territorio no disponible")+" · " : "Sin territorio vinculado · ")+r.type+" · "+(r.season||"Sin vigencia")+(r.notes?" · "+r.notes:""),"Borrador local")+ `<button class="tm-btn subtle" data-remove-rule="${i}">Eliminar</button>`).join("") : empty("◇","No hay condiciones registradas.")}</div>`;
      $("tm-rule-form").onsubmit=e=>{e.preventDefault();data.rules.push({territoryId:$("tm-territory").value||null,sector:$("tm-sector").value.trim(),type:$("tm-type").value,season:$("tm-season").value.trim(),capacity:$("tm-capacity").value,notes:$("tm-notes").value.trim()});if(save(data))render();};
      root.querySelectorAll("[data-remove-rule]").forEach(b=>b.onclick=()=>{data.rules.splice(Number(b.dataset.removeRule),1);save(data);render();});
    } else if (tab === "rio-medio") {
      renderRioMedio(root);
    } else if (tab === "requests") {
      const p=pilotData(),items=p.bookings.slice().reverse();
      root.innerHTML=heading("CENTRO DE OPERACIONES","Solicitudes y reservas","Bandeja unificada de solicitudes de operadores y pescadores. Revisa cupos, acepta o rechaza y conserva el historial.")+
      '<div class="tm-note">DEMO LOCAL: los registros se guardan en este navegador. La aprobación no procesa pagos ni autoriza por sí sola el ingreso.</div>'+
      '<div class="tm-grid"><div class="tm-card"><small>Pendientes</small><div class="tm-value">'+items.filter(x=>x.status==="pending").length+'</div><p>Requieren revisión.</p></div><div class="tm-card"><small>Confirmadas</small><div class="tm-value">'+items.filter(x=>x.status==="confirmed").length+'</div><p>Reservas aprobadas en demo.</p></div><div class="tm-card"><small>Rechazadas</small><div class="tm-value">'+items.filter(x=>x.status==="rejected").length+'</div><p>Historial de decisiones.</p></div><div class="tm-card"><small>Cupo máximo</small><div class="tm-value">4</div><p>Por sección y jornada.</p></div></div>'+
      '<div class="tm-section"><h3>Bandeja de solicitudes</h3>'+tag(items.length+" registros")+'</div><div class="tm-list">'+(items.length?items.map((r,rev)=>{const i=p.bookings.length-1-rev;return '<div class="tm-row"><div class="tm-row-main"><strong>'+esc(r.source==="angler"?"Pescador recreativo":"Operador turístico")+' · '+esc(r.operator||r.anglerName||"Solicitante")+'</strong><p>'+esc(r.date)+' · '+esc(r.sectionName)+' · '+r.anglers+' pescador(es) · '+esc(r.contact||r.email||"Sin contacto")+'</p><p>Estado: '+(r.status==="confirmed"?"Confirmada":r.status==="rejected"?"Rechazada":"Pendiente de aprobación")+' · $'+Number(r.totalAmount||0).toLocaleString("es-CL")+'</p></div>'+tag(r.status==="confirmed"?"Confirmada":r.status==="rejected"?"Rechazada":"Pendiente")+(r.status==="pending"?'<button class="tm-btn primary" data-unified-approve="'+i+'">Aprobar</button><button class="tm-btn subtle" data-unified-reject="'+i+'">Rechazar</button>':"")+'</div>';}).join(""):empty("⇄","Todavía no hay solicitudes. Prueba los portales de operador y pescador."))+'</div>';
      root.querySelectorAll("[data-unified-approve]").forEach(b=>b.onclick=()=>{const booking=p.bookings[Number(b.dataset.unifiedApprove)];if(!booking)return;const left=4-pilotCount(p,booking.sectionId,booking.date);if(booking.anglers>left){alert("Cupo insuficiente: quedan "+left+" plazas.");return;}booking.status="confirmed";booking.reviewedAt=new Date().toISOString();data.pilot=p;save(data);render();});
      root.querySelectorAll("[data-unified-reject]").forEach(b=>b.onclick=()=>{const booking=p.bookings[Number(b.dataset.unifiedReject)];if(booking){booking.status="rejected";booking.reviewedAt=new Date().toISOString();data.pilot=p;save(data);render();}});
    } else if (tab === "operators") {
      const p=pilotData();
      root.innerHTML=heading("RELACIONES COMERCIALES","Operadores turísticos","Crea convenios de acceso, define sus condiciones y mantén a la vista su vigencia.")+
      '<div class="tm-hero"><div><div class="tm-kicker">CONVENIOS Y COLABORADORES</div><h2>'+p.operators.length+' operadores registrados</h2><p>Registra una empresa una sola vez y luego podrá solicitar cupos dentro de los sectores autorizados.</p></div><button class="tm-btn primary" id="tm-new-operator">＋ <span aria-hidden="true">♙</span> Nuevo operador</button></div>'+
      '<div id="tm-operator-create" class="tm-modal" hidden><div class="tm-section" style="margin-top:0"><h3>Nuevo convenio con operador turístico</h3><button class="tm-btn subtle" id="tm-cancel-operator">Cerrar ×</button></div><form id="tm-operator-form" class="tm-form"><div class="tm-field"><label>Razón social / nombre comercial</label><input id="tm-op-name" required maxlength="100" placeholder="Empresa de turismo"></div><div class="tm-field"><label>RUT / identificación tributaria (opcional)</label><input id="tm-op-tax" maxlength="30" placeholder="Identificación"></div><div class="tm-field"><label>Representante / contacto responsable</label><input id="tm-op-contact" required maxlength="100"></div><div class="tm-field"><label>Correo de contacto</label><input id="tm-op-email" type="email" required></div><div class="tm-field"><label>Teléfono / WhatsApp</label><input id="tm-op-phone" required></div><div class="tm-field"><label>Convenio vigente hasta</label><input id="tm-op-until" type="date"></div><div class="tm-field"><label>Sectores autorizados</label><input id="tm-op-sections" placeholder="Sector 1, Sector 3 o Todos"></div><div class="tm-field"><label>Tarifa / comisión acordada (CLP por pescador)</label><input id="tm-op-rate" type="number" min="0" step="1000" placeholder="Opcional"></div><div class="tm-field full"><label>Condiciones comerciales y operativas</label><textarea id="tm-op-terms" rows="3" maxlength="700" placeholder="Tarifas, forma de pago, responsabilidades, cancelaciones…"></textarea></div><div class="tm-field full"><label><input type="checkbox" id="tm-op-accept" required> Confirmo que las condiciones del convenio fueron acordadas con el operador.</label></div><div class="tm-field full"><button class="tm-btn primary" type="submit">Guardar convenio</button></div></form></div>'+
      '<div class="tm-section"><h3>Convenios registrados</h3>'+tag(p.operators.length+" operadores")+'</div><div class="tm-list">'+(p.operators.length?p.operators.map((o,i)=>'<div class="tm-row tm-operator-card"><div class="tm-row-main"><strong>♙ '+esc(o.name)+'</strong><p>'+esc(o.contact)+' · '+esc(o.email)+' · '+esc(o.phone)+'</p><p>Vigencia: '+esc(o.until||"No definida")+' · Sectores: '+esc(o.sections||"Por definir")+'</p><p>'+esc(o.terms||"Sin condiciones comerciales")+'</p></div>'+tag(o.status||"Convenio en borrador")+'<button class="tm-btn subtle" data-op-delete="'+i+'">Eliminar</button></div>').join(""):empty("♙","Aún no hay operadores. Usa «Nuevo operador» para crear el primer convenio."))+'</div>';
      $("tm-new-operator").onclick=()=>{$("tm-operator-create").hidden=false;$("tm-op-name").focus();};
      $("tm-cancel-operator").onclick=()=>{$("tm-operator-create").hidden=true;};
      $("tm-operator-form").onsubmit=e=>{e.preventDefault();p.operators.push({id:"op-"+Date.now(),name:$("tm-op-name").value.trim(),taxId:$("tm-op-tax").value.trim(),contact:$("tm-op-contact").value.trim(),email:$("tm-op-email").value.trim(),phone:$("tm-op-phone").value.trim(),until:$("tm-op-until").value,sections:$("tm-op-sections").value.trim(),rate:$("tm-op-rate").value,terms:$("tm-op-terms").value.trim(),status:"Convenio registrado · pendiente de validación documental"});data.pilot=p;if(save(data))render();};
      root.querySelectorAll("[data-op-delete]").forEach(b=>b.onclick=()=>{if(confirm("¿Eliminar este operador del registro local?")){p.operators.splice(Number(b.dataset.opDelete),1);data.pilot=p;save(data);render();}});
    } else if (tab === "team") {
      const p=pilotData();
      root.innerHTML=heading("USUARIOS Y PERMISOS","Equipo administrativo","Registra responsables y distribuye tareas. En producción cada miembro tendrá cuenta autenticada y permisos aplicados en servidor.")+
      '<form id="tm-staff-form" class="tm-form"><div class="tm-field"><label>Nombre completo</label><input id="tm-staff-name" required maxlength="100"></div><div class="tm-field"><label>Correo de usuario</label><input id="tm-staff-email" type="email" required></div><div class="tm-field"><label>Función</label><select id="tm-staff-role"><option>Administrador principal</option><option>Encargado de reservas</option><option>Encargado de accesos</option><option>Supervisor operativo</option><option>Consulta de reportes</option></select></div><div class="tm-field"><label>Territorio asignado</label><select id="tm-staff-territory"><option>Río del Medio</option>'+data.territories.map(t=>'<option>'+esc(t.name)+'</option>').join("")+'</select></div><div class="tm-field full"><button class="tm-btn primary">Agregar al equipo</button></div></form><div class="tm-section"><h3>Equipo registrado</h3>'+tag(p.staff.length+" usuarios")+'</div><div class="tm-list">'+(p.staff.length?p.staff.map((u,i)=>'<div class="tm-row"><div class="tm-row-main"><strong>'+esc(u.name)+'</strong><p>'+esc(u.email)+' · '+esc(u.role)+' · '+esc(u.territory)+'</p></div>'+tag("Acceso demo")+'<button class="tm-btn subtle" data-staff-delete="'+i+'">Quitar</button></div>').join(""):empty("♙","Aún no hay miembros del equipo."))+'</div>';
      $("tm-staff-form").onsubmit=e=>{e.preventDefault();p.staff.push({id:"staff-"+Date.now(),name:$("tm-staff-name").value.trim(),email:$("tm-staff-email").value.trim(),role:$("tm-staff-role").value,territory:$("tm-staff-territory").value});data.pilot=p;if(save(data))render();};
      root.querySelectorAll("[data-staff-delete]").forEach(b=>b.onclick=()=>{p.staff.splice(Number(b.dataset.staffDelete),1);data.pilot=p;save(data);render();});
    } else if (tab === "angler-portal") {
      renderAnglerPortal(root);
    } else if (tab === "operator-portal") {
      renderOperatorPortal(root);
    } else if (tab === "settings") {
      const p=pilotData();
      root.innerHTML=heading("PREFERENCIAS DEL TERRITORIO","Configuración","Ajusta reglas generales, temporada y condiciones comerciales. Estos controles no estarán mezclados con la operación diaria.")+
      '<div class="tm-pilot-panel"><h3>Temporada y capacidad</h3><form id="tm-settings-form" class="tm-pilot-form"><div class="tm-field"><label>Inicio de temporada</label><input id="tm-set-start" type="date" value="'+esc(p.seasonStart)+'"></div><div class="tm-field"><label>Término de temporada</label><input id="tm-set-end" type="date" value="'+esc(p.seasonEnd)+'"></div><div class="tm-field"><label>Tarifa base por pescador (CLP)</label><input id="tm-set-price" type="number" min="0" step="1000" value="'+esc(p.price)+'"></div><div class="tm-field"><label>Capacidad máxima por sector / día</label><input value="4" disabled></div><div class="tm-field"><label>Medio de pago preferente</label><select id="tm-set-payment">'+["Transferencia bancaria","Pago en línea","Efectivo al ingreso","Acuerdo directo con administrador"].map(x=>'<option '+(p.paymentMethod===x?"selected":"")+'>'+x+'</option>').join("")+'</select></div><div class="tm-field"><label>Modalidad de cobro</label><select id="tm-set-mode">'+["Pago total al confirmar","Abono para reservar + saldo previo al ingreso","Pago al llegar","Facturación a operador"].map(x=>'<option '+(p.paymentMode===x?"selected":"")+'>'+x+'</option>').join("")+'</select></div><div class="tm-field full"><label>Condiciones de pago</label><textarea id="tm-set-terms" rows="3">'+esc(p.paymentTerms)+'</textarea></div><div class="tm-field full"><button class="tm-btn primary">Guardar configuración</button></div></form></div>'+
      '<div class="tm-pilot-panel"><h3>Preferencias de operación</h3><p class="tm-pilot-muted">Las reglas de conservación, accesos y sectores se administran en sus respectivas secciones. En producción se podrán definir alertas, aprobaciones automáticas y responsables del equipo.</p><div class="tm-actions"><button class="tm-btn" data-go="access">Editar accesos y reglas</button><button class="tm-btn" data-go="team">Administrar equipo</button><button class="tm-btn" data-go="operators">Convenios de operadores</button></div></div>';
      $("tm-settings-form").onsubmit=e=>{e.preventDefault();p.seasonStart=$("tm-set-start").value;p.seasonEnd=$("tm-set-end").value;p.price=$("tm-set-price").value;p.paymentMethod=$("tm-set-payment").value;p.paymentMode=$("tm-set-mode").value;p.paymentTerms=$("tm-set-terms").value.trim();if(p.seasonStart&&p.seasonEnd&&p.seasonEnd<p.seasonStart){alert("El término de temporada debe ser posterior al inicio.");return;}data.pilot=p;if(save(data))alert("Configuración guardada en este navegador.");};
      root.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>{tab=b.dataset.go;render();});
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


  let pilotMapAction = null, pilotRiverLayer = null, pilotSectionLayer = null, pilotAccessLayer = null;
  const pilotDefaults = [
    {id:"catch-release",label:"Pesca exclusivamente catch & release",enabled:true},
    {id:"no-fire",label:"Prohibido encender fuego",enabled:true},
    {id:"stay-area",label:"Permanecer dentro del sector delimitado y autorizado",enabled:true},
    {id:"fences",label:"Prohibido abrir, forzar o dañar portones y alambrados",enabled:true},
    {id:"entry-exit",label:"Ingresar y salir únicamente por los puntos indicados",enabled:true},
    {id:"waste",label:"Retirar todos los residuos",enabled:true},
    {id:"vehicles",label:"No circular en vehículo fuera de caminos autorizados",enabled:true}
  ];
  function pilotData() {
    data=read();
    const p=data.pilot||{};
    if(!Array.isArray(p.sections))p.sections=[];
    if(!Array.isArray(p.accessPoints))p.accessPoints=[];
    if(!Array.isArray(p.bookings))p.bookings=[];
    if(!Array.isArray(p.operators))p.operators=[];
    if(!Array.isArray(p.staff))p.staff=[];
    if(!Array.isArray(p.policies)||!p.policies.length)p.policies=pilotDefaults.map(x=>({...x}));
    p.seasonStart=p.seasonStart||"2026-10-01";
    p.seasonEnd=p.seasonEnd||"2027-04-30";
    p.price=p.price||"";
    p.paymentMethod=p.paymentMethod||"Transferencia bancaria";
    p.paymentMode=p.paymentMode||"Pago total al confirmar";
    p.paymentTerms=p.paymentTerms||"Reserva sujeta a confirmación del administrador";
    data.pilot=p;
    return p;
  }
  function pilotRiverMatches() {
    if(typeof RIVERS==="undefined")return [];
    return RIVERS.filter(w=>amCatalogNormalize(w.name)==="rio del medio"&&w.category==="river"&&Array.isArray(w.communes)&&w.communes.includes("Laguna Blanca"));
  }
  function pilotLayers() {
    if(!pilotRiverLayer)pilotRiverLayer=L.layerGroup();
    if(!pilotSectionLayer)pilotSectionLayer=L.layerGroup();
    if(!pilotAccessLayer)pilotAccessLayer=L.layerGroup();
    pilotRiverLayer.addTo(map);pilotSectionLayer.addTo(map);pilotAccessLayer.addTo(map);
  }
  function showPilotRiver() {
    const matches=pilotRiverMatches();
    if(!matches.length){alert("Río del Medio no está disponible en el catálogo hidrográfico cargado. No se dibujará una geometría aproximada.");return;}
    pilotLayers();pilotRiverLayer.clearLayers();
    matches.forEach(w=>L.geoJSON({type:"FeatureCollection",features:w.features},{style:{color:"#39b9d2",weight:5,opacity:.95}}).bindPopup("<b>Río del Medio</b><br>Geometría hidrográfica de referencia · DGA").addTo(pilotRiverLayer));
    const bounds=pilotRiverLayer.getBounds();if(bounds.isValid())map.fitBounds(bounds,{padding:[55,55],maxZoom:13});
  }
  function showAvailabilityMap(date) {
    const matches=pilotRiverMatches(),p=pilotData();
    if(matches.length){pilotLayers();pilotRiverLayer.clearLayers();matches.forEach(w=>L.geoJSON({type:"FeatureCollection",features:w.features},{style:{color:"#55d9e8",weight:5,opacity:.95}}).addTo(pilotRiverLayer));}
    pilotLayers();pilotSectionLayer.clearLayers();
    p.sections.forEach(sec=>{const used=pilotCount(p,sec.id,date),left=Math.max(0,4-used),color=left===0?"#e66c6c":used?"#e8bd70":"#48c78e";if(sec.coordinates?.length>1)L.polyline(sec.coordinates,{color,weight:8,opacity:.95}).bindPopup("<b>"+esc(sec.name)+"</b><br>"+left+" de 4 cupos disponibles · "+date).addTo(pilotSectionLayer);});
    const bounds=L.featureGroup(pilotSectionLayer.getLayers()).getBounds();const riverBounds=L.featureGroup(pilotRiverLayer.getLayers()).getBounds();if(bounds.isValid())map.fitBounds(bounds,{padding:[60,60],maxZoom:14});else if(riverBounds.isValid())map.fitBounds(riverBounds,{padding:[60,60],maxZoom:13});
  }
  function drawPilotRecords() {
    pilotLayers();pilotSectionLayer.clearLayers();pilotAccessLayer.clearLayers();
    const p=pilotData();
    p.sections.forEach(s=>{
      if(s.coordinates&&s.coordinates.length>1)L.polyline(s.coordinates,{color:"#e8bd70",weight:5,opacity:.9}).bindPopup("<b>"+esc(s.name)+"</b><br>Capacidad máxima: 4 pescadores por jornada").addTo(pilotSectionLayer);
    });
    p.accessPoints.forEach(a=>{
      if(a.lat!=null&&a.lng!=null)L.marker([a.lat,a.lng]).bindPopup("<b>"+esc(a.name)+"</b><br>"+esc(a.kind==="entry"?"Ingreso":"Salida")+" · Punto operativo definido por administrador").addTo(pilotAccessLayer);
    });
  }
  function pilotCount(p,sectionId,date) {
    return p.bookings.filter(b=>b.sectionId===sectionId&&b.date===date&&b.status==="confirmed").reduce((n,b)=>n+Number(b.anglers||0),0);
  }
  function renderAnglerPortal(root) {
    const p=pilotData(),sections=p.sections,today=new Date().toISOString().slice(0,10);
    root.innerHTML=heading("EXPERIENCIA PÚBLICA","Encuentra tu próxima jornada","Explora un territorio administrado, revisa sus reglas y solicita acceso.")+
    '<div class="tm-note">DEMO: la solicitud queda pendiente de aprobación. No genera pago real ni autorización de ingreso.</div>'+
    '<div class="tm-pilot-grid"><div class="tm-pilot-panel"><h3>Solicitar acceso · Río del Medio</h3><form id="tm-angler-form" class="tm-pilot-form">'+
    '<div class="tm-field"><label>Nombre completo</label><input id="tm-ang-name" required></div><div class="tm-field"><label>Correo</label><input id="tm-ang-email" type="email" required></div>'+
    '<div class="tm-field"><label>Teléfono / WhatsApp</label><input id="tm-ang-phone" required></div><div class="tm-field"><label>Fecha de pesca</label><input id="tm-ang-date" type="date" min="'+today+'" required></div>'+
    '<div class="tm-field"><label>Sector</label><select id="tm-ang-section" required><option value="">Seleccionar</option>'+sections.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+'</option>').join("")+'</select></div>'+
    '<div class="tm-field"><label>Número de pescadores</label><select id="tm-ang-count">'+[1,2,3,4].map(n=>'<option>'+n+'</option>').join("")+'</select></div>'+
    '<div class="tm-field full"><label>Licencia / pasapescadores de cada integrante (uno por línea)</label><textarea id="tm-ang-licenses" rows="3" required placeholder="Una licencia por pescador"></textarea></div>'+
    '<div class="tm-field full"><label><input type="checkbox" id="tm-ang-accept" required> Acepto las condiciones de ingreso y conservación.</label></div>'+
    '<div class="tm-field full"><button class="tm-btn primary" '+(!sections.length?"disabled":"")+' type="submit">Enviar solicitud</button></div></form><div id="tm-ang-result"></div></div>'+
    '<div class="tm-pilot-panel"><h3>Condiciones publicadas</h3><div class="tm-pilot-list">'+p.policies.filter(x=>x.enabled).map(x=>'<div class="tm-pilot-item">'+esc(x.label)+'</div>').join("")+'</div></div></div>';
    $("tm-angler-form").onsubmit=e=>{e.preventDefault();const section=p.sections.find(x=>x.id===$("tm-ang-section").value),date=$("tm-ang-date").value,count=Number($("tm-ang-count").value),licenses=$("tm-ang-licenses").value.split(/\n|,/).map(x=>x.trim()).filter(Boolean);if(!section)return;if(licenses.length!==count){alert("Ingresa exactamente una licencia por cada pescador ("+count+").");return;}if(p.seasonStart&&date<p.seasonStart||p.seasonEnd&&date>p.seasonEnd){alert("Fecha fuera de temporada.");return;}const left=4-pilotCount(p,section.id,date);if(count>left){alert("Cupo insuficiente. Disponibles: "+left+".");return;}p.bookings.push({id:"rm-"+Date.now(),source:"angler",sectionId:section.id,sectionName:section.name,date,anglers:count,anglerName:$("tm-ang-name").value.trim(),contact:$("tm-ang-phone").value.trim(),email:$("tm-ang-email").value.trim(),licenses,acceptedPolicies:p.policies.filter(x=>x.enabled).map(x=>x.id),status:"pending",pricePerAngler:Number(p.price)||0,totalAmount:(Number(p.price)||0)*count,createdAt:new Date().toISOString()});data.pilot=p;if(save(data)){$("tm-ang-result").innerHTML='<div class="tm-note">Solicitud recibida. Pendiente de aprobación. Total referencial: $'+((Number(p.price)||0)*count).toLocaleString("es-CL")+' CLP. No autoriza el ingreso.</div>';e.target.reset();}};
  }
  function renderOperatorPortal(root) {
    const p=pilotData(),sections=p.sections,today=new Date().toISOString().slice(0,10);
    root.innerHTML=heading("ESPACIO DE OPERADORES","Solicitar cupos para tus clientes","Gestiona solicitudes para sectores de un territorio con el que mantienes una relación comercial.")+
    '<div class="tm-note">DEMO LOCAL: las solicitudes se incorporan a la bandeja del administrador de este navegador.</div>'+
    '<div class="tm-pilot-panel"><form id="tm-operator-request" class="tm-pilot-form"><div class="tm-field"><label>Operador / empresa</label><select id="tm-portal-operator" required><option value="">Seleccionar operador</option>'+p.operators.map(o=>'<option>'+esc(o.name)+'</option>').join("")+'</select></div><div class="tm-field"><label>Contacto responsable</label><input id="tm-portal-contact" required></div>'+
    '<div class="tm-field"><label>Fecha</label><input id="tm-portal-date" type="date" min="'+today+'" required></div><div class="tm-field"><label>Sector</label><select id="tm-portal-section" required><option value="">Seleccionar</option>'+sections.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+'</option>').join("")+'</select></div>'+
    '<div class="tm-field"><label>Pescadores</label><select id="tm-portal-count">'+[1,2,3,4].map(n=>'<option>'+n+'</option>').join("")+'</select></div><div class="tm-field"><label>Forma de pago</label><select id="tm-portal-payment"><option>Facturación a operador</option><option>Transferencia bancaria</option><option>Pago en línea</option></select></div>'+
    '<div class="tm-field full"><label>Datos del grupo / observaciones</label><textarea id="tm-portal-notes" rows="2"></textarea></div><div class="tm-field full"><button class="tm-btn primary" '+(!sections.length?"disabled":"")+' type="submit">Solicitar sector</button></div></form></div>';
    $("tm-operator-request").onsubmit=e=>{e.preventDefault();const op=$("tm-portal-operator").value,section=p.sections.find(x=>x.id===$("tm-portal-section").value),date=$("tm-portal-date").value,count=Number($("tm-portal-count").value);if(!op){alert("Registra y selecciona un operador con convenio.");return;}if(!section)return;const agreement=p.operators.find(x=>x.name===op);if(agreement?.sections&&!agreement.sections.toLowerCase().includes(section.name.toLowerCase())&&!agreement.sections.toLowerCase().includes("todos")){alert("El sector no figura entre los autorizados en el convenio.");return;}if(count>4-pilotCount(p,section.id,date)){alert("Cupo insuficiente para esa fecha.");return;}p.bookings.push({id:"rm-"+Date.now(),source:"operator",sectionId:section.id,sectionName:section.name,date,anglers:count,operator:op,contact:$("tm-portal-contact").value.trim(),payment:$("tm-portal-payment").value,message:$("tm-portal-notes").value.trim(),pricePerAngler:Number(p.price)||0,totalAmount:(Number(p.price)||0)*count,status:"pending",createdAt:new Date().toISOString()});data.pilot=p;if(save(data)){alert("Solicitud incorporada a la bandeja del administrador.");e.target.reset();}};
  }

  function renderRioMedio(root) {
    const p=pilotData(),matches=pilotRiverMatches();
    const today=new Date().toISOString().slice(0,10);
    const sections=p.sections;
    const confirmed=p.bookings.filter(b=>b.status==="confirmed").length;
    const pending=p.bookings.filter(b=>b.status==="pending").length;
    root.innerHTML=heading("TERRITORIO PILOTO · LAGUNA BLANCA","Río del Medio","Prototipo operativo para administrar sectores de pesca, accesos, cupos, reglas de conservación y solicitudes de operadores turísticos.")+
      '<div class="tm-note">La línea azul corresponde a la geometría hidrográfica de referencia disponible. Las secciones y puntos de ingreso/salida deben ser definidos por el administrador en terreno. No se presume autorización de acceso ni titularidad.</div>'+
      '<div class="tm-actions"><button class="tm-btn primary" id="tm-rm-show-river">Localizar Río del Medio en el mapa</button><button class="tm-btn" id="tm-rm-draw-section">＋ Delimitar sección</button><button class="tm-btn" id="tm-rm-entry">＋ Marcar ingreso</button><button class="tm-btn" id="tm-rm-exit">＋ Marcar salida</button></div>'+
      '<div class="tm-grid">'+
      '<div class="tm-card"><small>Secciones definidas</small><div class="tm-value">'+sections.length+'</div><p>Tramos operativos delimitados por el administrador.</p></div>'+
      '<div class="tm-card"><small>Cupo por sección</small><div class="tm-value">4</div><p>Máximo de pescadores confirmados por jornada.</p></div>'+
      '<div class="tm-card"><small>Reservas confirmadas</small><div class="tm-value">'+confirmed+'</div><p>Reservas aceptadas por el administrador.</p></div>'+
      '<div class="tm-card"><small>Solicitudes pendientes</small><div class="tm-value">'+pending+'</div><p>Requieren revisión antes de confirmar.</p></div></div>'+
      '<div class="tm-pilot-grid"><div>'+
      '<div class="tm-pilot-panel"><h3>1 · Secciones de pesca</h3><p class="tm-pilot-muted">Cada sección debe tener una geometría propia, límites visibles, capacidad fija de cuatro pescadores por jornada y accesos vinculados.</p><div class="tm-pilot-list">'+(sections.length?sections.map((s,i)=>'<div class="tm-pilot-item"><strong>'+esc(s.name)+'</strong><small>'+((s.coordinates||[]).length)+' puntos de trazado · Máximo 4 pescadores/día · '+(s.notes?esc(s.notes):"Sin observaciones")+'</small><button class="tm-btn subtle" data-rm-zoom="'+i+'">Ver sección</button><button class="tm-btn subtle" data-rm-delete-section="'+i+'">Eliminar</button></div>').join(""):empty("〰","Todavía no hay secciones delimitadas. Usa «Delimitar sección» y marca el recorrido sobre el mapa."))+'</div></div>'+
      '<div class="tm-pilot-panel"><h3>2 · Puntos de ingreso y salida</h3><p class="tm-pilot-muted">Registrar coordenadas exactas y asociarlas a instrucciones de llegada. Los puntos deben verificarse con el administrador del predio.</p><div class="tm-pilot-list">'+(p.accessPoints.length?p.accessPoints.map((a,i)=>'<div class="tm-pilot-item"><strong>'+esc(a.name)+'</strong><small>'+(a.kind==="entry"?"Ingreso":"Salida")+' · '+Number(a.lat).toFixed(5)+', '+Number(a.lng).toFixed(5)+' · '+esc(a.notes||"Sin instrucciones")+'</small><button class="tm-btn subtle" data-rm-zoom-access="'+i+'">Ver punto</button><button class="tm-btn subtle" data-rm-delete-access="'+i+'">Eliminar</button></div>').join(""):empty("⌖","No hay accesos registrados. Marca en el mapa el punto de ingreso y el punto de salida autorizados."))+'</div></div>'+
      '<div class="tm-pilot-panel"><h3>3 · Condiciones de ingreso</h3><p class="tm-pilot-muted">Reglas propuestas para aprobación del administrador. Se mostrarán antes de solicitar o confirmar una reserva.</p><div class="tm-pilot-checks">'+p.policies.map((x,i)=>'<label><input type="checkbox" data-rm-policy="'+i+'" '+(x.enabled?"checked":"")+'> '+esc(x.label)+'</label>').join("")+'</div><div class="tm-actions"><button class="tm-btn primary" id="tm-rm-save-policies">Guardar condiciones</button></div></div>'+
      '</div><div>'+
      '<div class="tm-pilot-panel"><h3>4 · Temporada y condiciones comerciales</h3><form id="tm-rm-settings" class="tm-pilot-form">'+
      '<div class="tm-field"><label>Inicio de temporada</label><input type="date" id="tm-rm-start" value="'+esc(p.seasonStart)+'"></div><div class="tm-field"><label>Término de temporada</label><input type="date" id="tm-rm-end" value="'+esc(p.seasonEnd)+'"></div>'+
      '<div class="tm-field"><label>Tarifa por pescador (CLP)</label><input type="number" min="0" step="1000" id="tm-rm-price" value="'+esc(p.price)+'" placeholder="Por definir"></div>'+
      '<div class="tm-field"><label>Medio de pago</label><select id="tm-rm-payment">'+["Transferencia bancaria","Pago en línea","Efectivo al ingreso","Acuerdo directo con administrador"].map(x=>'<option '+(p.paymentMethod===x?"selected":"")+'>'+x+'</option>').join("")+'</select></div>'+
      '<div class="tm-field"><label>Modalidad de cobro</label><select id="tm-rm-payment-mode">'+["Pago total al confirmar","Abono para reservar + saldo previo al ingreso","Pago al llegar","Facturación a operador"].map(x=>'<option '+(p.paymentMode===x?"selected":"")+'>'+x+'</option>').join("")+'</select></div>'+
      '<div class="tm-field full"><label>Condiciones de pago</label><textarea id="tm-rm-terms" rows="2" maxlength="500">'+esc(p.paymentTerms)+'</textarea></div><div class="tm-field full"><button class="tm-btn primary">Guardar configuración</button></div></form></div>'+
      '<div class="tm-pilot-panel"><h3>5 · Solicitudes de operadores</h3><p class="tm-pilot-muted">Los operadores pueden solicitar cupos para sus clientes. La solicitud queda pendiente y no bloquea disponibilidad hasta ser aprobada.</p><div class="tm-pilot-list">'+(p.bookings.length?p.bookings.slice().reverse().map((b,rev)=>{const i=p.bookings.length-1-rev;return '<div class="tm-pilot-item"><strong>'+esc(b.operator)+' · '+esc(b.sectionName)+'</strong><small>'+esc(b.date)+' · '+b.anglers+' pescador(es) · '+esc(b.contact)+' · '+esc(b.payment||"Pago por coordinar")+'</small><small>Estado: '+(b.status==="confirmed"?"Confirmada":b.status==="rejected"?"Rechazada":"Pendiente")+' · '+(b.totalAmount?("Total estimado: $"+Number(b.totalAmount).toLocaleString("es-CL")+" CLP"):"Tarifa por confirmar")+' · '+esc(b.paymentMode||"Modalidad por coordinar")+'</small>'+(b.status==="pending"?'<button class="tm-btn primary" data-rm-approve="'+i+'">Aprobar reserva</button><button class="tm-btn subtle" data-rm-reject="'+i+'">Rechazar</button>':"")+'</div>';}).join(""):empty("▤","Aún no hay solicitudes de reserva."))+'</div></div>'+
      '</div></div>'+
      '<div class="tm-pilot-panel"><h3>6 · Vista de disponibilidad para operadores</h3><div class="tm-field" style="max-width:260px"><label>Consultar fecha</label><input type="date" id="tm-rm-date" value="'+today+'"></div><div id="tm-rm-availability" class="tm-grid"></div></div>'+
      '<div class="tm-pilot-panel"><h3>7 · Portal de operadores turísticos</h3><p class="tm-pilot-muted">Simulación del flujo de reserva: elegir fecha y sector, revisar cupos, informar tamaño del grupo, contacto y forma de pago. La reserva se confirma solo después de la aprobación del administrador.</p>'+
      '<form id="tm-rm-request" class="tm-pilot-form">'+
      '<div class="tm-field"><label>Operador / empresa</label><input id="tm-rm-operator" required maxlength="100" placeholder="Nombre del operador"></div><div class="tm-field"><label>Contacto responsable</label><input id="tm-rm-contact" required maxlength="100" placeholder="Nombre y teléfono"></div>'+
      '<div class="tm-field"><label>Fecha solicitada</label><input type="date" id="tm-rm-book-date" required min="'+today+'"></div><div class="tm-field"><label>Sección</label><select id="tm-rm-section" required><option value="">Seleccionar sección</option>'+sections.map(s=>'<option value="'+esc(s.id)+'">'+esc(s.name)+'</option>').join("")+'</select></div>'+
      '<div class="tm-field"><label>Número de pescadores (máx. 4)</label><select id="tm-rm-anglers">'+[1,2,3,4].map(n=>'<option>'+n+'</option>').join("")+'</select></div><div class="tm-field"><label>Forma de pago propuesta</label><select id="tm-rm-book-payment">'+["Transferencia bancaria","Pago en línea","Efectivo al ingreso","Acuerdo directo"].map(x=>'<option>'+x+'</option>').join("")+'</select></div>'+
      '<div class="tm-field full"><label>Observaciones / requerimientos</label><textarea id="tm-rm-message" rows="2" maxlength="500" placeholder="Nombres de pescadores, guía responsable, horario estimado, requerimientos especiales…"></textarea></div>'+
      '<div class="tm-field full"><label><input type="checkbox" id="tm-rm-accept" required> Declaro que el grupo acepta las condiciones de ingreso publicadas para este territorio.</label></div><div class="tm-field full"><button class="tm-btn primary" '+(!sections.length?"disabled":"")+'>Enviar solicitud de disponibilidad</button></div></form></div>'+
      '<div class="tm-note">DEMO LOCAL: las solicitudes, reservas, reglas y configuraciones se guardan únicamente en este navegador. No se envían correos, no se procesa dinero y no existe bloqueo compartido de cupos entre usuarios. Antes de operar con terceros se requiere backend, autenticación, trazabilidad y mecanismo de pago.</div>';
    drawPilotRecords();
    const avail=$("tm-rm-availability");
    const drawAvailability=()=>{const date=$("tm-rm-date").value;avail.innerHTML=sections.length?sections.map(s=>{const used=pilotCount(p,s.id,date),left=Math.max(0,4-used);return '<div class="tm-card"><small>'+esc(s.name)+'</small><div class="tm-value">'+left+' / 4</div><p>'+used+' pescador(es) confirmados · '+(left?"Cupos disponibles":"Completo")+'</p></div>';}).join(""):empty("▤","Primero delimita una o más secciones.");};
    drawAvailability();$("tm-rm-date").onchange=drawAvailability;
    $("tm-rm-show-river").onclick=showPilotRiver;
    $("tm-rm-draw-section").onclick=()=>startPilotMapAction("section");
    $("tm-rm-entry").onclick=()=>startPilotMapAction("entry");
    $("tm-rm-exit").onclick=()=>startPilotMapAction("exit");
    $("tm-rm-settings").onsubmit=e=>{e.preventDefault();p.seasonStart=$("tm-rm-start").value;p.seasonEnd=$("tm-rm-end").value;p.price=$("tm-rm-price").value;p.paymentMethod=$("tm-rm-payment").value;p.paymentMode=$("tm-rm-payment-mode").value;p.paymentTerms=$("tm-rm-terms").value.trim();if(p.seasonStart&&p.seasonEnd&&p.seasonEnd<p.seasonStart){alert("El término de temporada debe ser posterior al inicio.");return;}data.pilot=p;save(data);alert("Configuración guardada en este navegador.");};
    $("tm-rm-save-policies").onclick=()=>{root.querySelectorAll("[data-rm-policy]").forEach(el=>p.policies[Number(el.dataset.rmPolicy)].enabled=el.checked);data.pilot=p;save(data);alert("Condiciones guardadas.");};
    $("tm-rm-request").onsubmit=e=>{e.preventDefault();const section=p.sections.find(s=>s.id===$("tm-rm-section").value);if(!section){alert("Selecciona una sección válida.");return;}const date=$("tm-rm-book-date").value,anglers=Number($("tm-rm-anglers").value);if(p.seasonStart&&date<p.seasonStart||p.seasonEnd&&date>p.seasonEnd){alert("La fecha está fuera de la temporada configurada.");return;}const remaining=4-pilotCount(p,section.id,date);if(anglers>remaining){alert("No hay cupos suficientes. Disponibles: "+remaining+".");return;}if(!p.accessPoints.some(a=>a.kind==="entry")||!p.accessPoints.some(a=>a.kind==="exit")){if(!confirm("Falta registrar ingreso y/o salida autorizados. ¿Deseas guardar la solicitud como pendiente de coordinación?"))return;}p.bookings.push({id:"rm-"+Date.now(),sectionId:section.id,sectionName:section.name,date,anglers,operator:$("tm-rm-operator").value.trim(),contact:$("tm-rm-contact").value.trim(),payment:$("tm-rm-book-payment").value,message:$("tm-rm-message").value.trim(),status:"pending",pricePerAngler:Number(p.price)||null,totalAmount:(Number(p.price)||0)*anglers||null,paymentTerms:p.paymentTerms,paymentMode:p.paymentMode,status:"pending",createdAt:new Date().toISOString()});data.pilot=p;if(save(data)){render();alert("Solicitud guardada. Queda pendiente de aprobación del administrador.");}};
    root.querySelectorAll("[data-rm-approve]").forEach(b=>b.onclick=()=>{const booking=p.bookings[Number(b.dataset.rmApprove)];if(!booking)return;const available=4-pilotCount(p,booking.sectionId,booking.date);if(booking.anglers>available){alert("No se puede aprobar: quedan "+available+" cupos en esta sección para esa fecha.");return;}booking.status="confirmed";data.pilot=p;save(data);render();});
    root.querySelectorAll("[data-rm-reject]").forEach(b=>b.onclick=()=>{const booking=p.bookings[Number(b.dataset.rmReject)];if(booking){booking.status="rejected";data.pilot=p;save(data);render();}});
    root.querySelectorAll("[data-rm-delete-section]").forEach(b=>b.onclick=()=>{const s=p.sections[Number(b.dataset.rmDeleteSection)];if(s&&confirm("¿Eliminar esta sección? Las reservas históricas permanecerán registradas.")){p.sections.splice(Number(b.dataset.rmDeleteSection),1);data.pilot=p;save(data);render();}});
    root.querySelectorAll("[data-rm-delete-access]").forEach(b=>b.onclick=()=>{p.accessPoints.splice(Number(b.dataset.rmDeleteAccess),1);data.pilot=p;save(data);render();});
    root.querySelectorAll("[data-rm-zoom]").forEach(b=>b.onclick=()=>{const s=p.sections[Number(b.dataset.rmZoom)];if(s?.coordinates?.length)map.fitBounds(L.latLngBounds(s.coordinates),{padding:[50,50]});});
    root.querySelectorAll("[data-rm-zoom-access]").forEach(b=>b.onclick=()=>{const a=p.accessPoints[Number(b.dataset.rmZoomAccess)];if(a)map.setView([a.lat,a.lng],15);});
  }
  function startPilotMapAction(type) {
    pilotMapAction={type,points:[]};
    const labels={section:"DELIMITAR SECCIÓN",entry:"MARCAR PUNTO DE INGRESO",exit:"MARCAR PUNTO DE SALIDA"};
    alert(type==="section"?"Haz clic en el mapa para marcar al menos dos puntos siguiendo el cauce. Pulsa «Finalizar trazado» cuando termines.": "Haz clic en el mapa en la ubicación exacta del "+(type==="entry"?"ingreso":"salida")+" autorizado.");
    if(type!=="section")return;
    const note=document.createElement("div");note.id="tm-rm-draw-controls";note.style.cssText="position:absolute;z-index:1000;top:72px;left:50%;transform:translateX(-50%);background:#102638;border:1px solid #55d9e8;border-radius:10px;padding:10px;color:#fff";
    note.innerHTML=labels[type]+' · <button class="tm-btn primary" id="tm-rm-finish">Finalizar trazado</button> <button class="tm-btn" id="tm-rm-cancel">Cancelar</button>';
    shell.appendChild(note);
    $("tm-rm-finish").onclick=()=>{if(!pilotMapAction||pilotMapAction.points.length<2){alert("Marca al menos dos puntos.");return;}const name=prompt("Nombre de la sección (ej. Sección Alta):");if(!name||!name.trim())return;const p=pilotData();p.sections.push({id:"rms-"+Date.now(),name:name.trim(),coordinates:pilotMapAction.points.map(x=>[x.lat,x.lng]),capacity:4,notes:"Geometría trazada en demo; pendiente de validación en terreno"});data.pilot=p;save(data);cancelPilotMapAction();render();};
    $("tm-rm-cancel").onclick=()=>{cancelPilotMapAction();render();};
  }
  function cancelPilotMapAction() {
    pilotMapAction=null;
    const n=$("tm-rm-draw-controls");if(n)n.remove();
    if(pilotSectionLayer)pilotSectionLayer.clearLayers();
    drawPilotRecords();
  }
  function handlePilotMapClick(e) {
    if(!pilotMapAction)return false;
    const p=pilotData(),type=pilotMapAction.type;
    if(type==="section"){pilotMapAction.points.push(e.latlng);pilotLayers();pilotSectionLayer.clearLayers();L.polyline(pilotMapAction.points,{color:"#e8bd70",weight:5,dashArray:"6 5"}).addTo(pilotSectionLayer);return true;}
    const name=prompt("Nombre o referencia del punto de "+(type==="entry"?"ingreso":"salida")+":",type==="entry"?"Ingreso autorizado":"Salida autorizada");
    if(name&&name.trim()){p.accessPoints.push({id:"rma-"+Date.now(),name:name.trim(),kind:type,lat:e.latlng.lat,lng:e.latlng.lng,notes:"Pendiente de validación por el administrador"});data.pilot=p;save(data);}
    pilotMapAction=null;render();return true;
  }

  let importedLayer = L.layerGroup().addTo(map);
  function refreshImportedLayers() {
    if (importedLayer) importedLayer.clearLayers();
    const current = read();
    current.imports.forEach((item,index) => {
      try {
        L.geoJSON(item.geojson, {
          style: () => ({color:"#e8bd70",weight:2,dashArray:"7 5",fillColor:"#d4a64f",fillOpacity:.12}),
          pointToLayer: (_feature,latlng) => L.circleMarker(latlng,{radius:5,color:"#e8bd70",weight:2,fillOpacity:.75}),
          onEachFeature: (feature,featureLayer) => {
            const props = feature.properties || {};
            const details = Object.entries(props).slice(0,8).map(([k,v])=>"<b>"+esc(k)+":</b> "+esc(typeof v==="object"?JSON.stringify(v):v)).join("<br>");
            featureLayer.bindPopup("<b>"+esc(item.name)+"</b><br><small>Cartografía importada · pendiente de validar</small>"+(details?"<hr>"+details:""));
          }
        }).addTo(importedLayer);
      } catch(error) { console.warn("No se pudo dibujar una capa importada",index,error); }
    });
  }
  function zoomImported(index) {
    const item=read().imports[index]; if(!item)return;
    try { const bounds=L.geoJSON(item.geojson).getBounds(); if(bounds.isValid()){shell.classList.remove("open");map.fitBounds(bounds,{padding:[45,45],maxZoom:13});} }
    catch(error) { alert("No se pudo localizar la geometría importada."); }
  }
  function parseKml(text) {
    const xml=new DOMParser().parseFromString(text,"application/xml");
    if(xml.querySelector("parsererror")) throw new Error("El archivo KML no tiene XML válido.");
    const features=[];
    const coords=node=>node.textContent.trim().split(/\s+/).filter(Boolean).map(pair=>{const p=pair.split(",").map(Number);return [p[0],p[1],...(p.length>2?[p[2]]:[])];});
    xml.querySelectorAll("Placemark").forEach(pm=>{
      const properties={}; const name=pm.querySelector(":scope > name"); if(name)properties.name=name.textContent.trim();
      pm.querySelectorAll("ExtendedData Data").forEach(d=>{const k=d.getAttribute("name"),v=d.querySelector("value");if(k&&v)properties[k]=v.textContent.trim();});
      pm.querySelectorAll("Point,LineString,Polygon").forEach(g=>{
        let geometry=null;
        if(g.tagName==="Point"){const c=g.querySelector("coordinates");if(c)geometry={type:"Point",coordinates:coords(c)[0]};}
        if(g.tagName==="LineString"){const c=g.querySelector("coordinates");if(c)geometry={type:"LineString",coordinates:coords(c)};}
        if(g.tagName==="Polygon"){const rings=[...g.querySelectorAll(":scope > outerBoundaryIs coordinates, :scope > innerBoundaryIs coordinates")].map(coords);if(rings.length)geometry={type:"Polygon",coordinates:rings};}
        if(geometry)features.push({type:"Feature",properties:{...properties},geometry});
      });
    });
    if(!features.length)throw new Error("El KML no contiene puntos, líneas o polígonos compatibles.");
    return {type:"FeatureCollection",features};
  }
  async function importTerritoryFile() {
    const input=$("tm-import-file"),file=input.files&&input.files[0]; if(!file){alert("Selecciona primero un archivo GeoJSON o KML.");return;}
    if(file.size>10*1024*1024){alert("El archivo supera el límite de 10 MB.");return;}
    const ext=file.name.split(".").pop().toLowerCase(); if(!["geojson","json","kml"].includes(ext)){alert("Formato no admitido. Usa GeoJSON o KML.");return;}
    try {
      const raw=await file.text(),geojson=ext==="kml"?parseKml(raw):JSON.parse(raw);
      const collection=geojson.type==="FeatureCollection"?geojson:geojson.type==="Feature"?{type:"FeatureCollection",features:[geojson]}:null;
      if(!collection||!Array.isArray(collection.features)||!collection.features.length)throw new Error("El archivo debe contener un Feature o FeatureCollection GeoJSON.");
      if(collection.features.length>10000)throw new Error("El archivo supera el límite de 10.000 elementos.");
      const valid=collection.features.filter(f=>f&&f.type==="Feature"&&f.geometry&&["Point","MultiPoint","LineString","MultiLineString","Polygon","MultiPolygon","GeometryCollection"].includes(f.geometry.type));
      if(!valid.length)throw new Error("No se encontraron geometrías compatibles.");
      const name=prompt("Nombre de esta capa (por ejemplo, Catastro predial SAG):",file.name.replace(/\.[^.]+$/,"")); if(!name||!name.trim())return;
      const source=prompt("Fuente o institución de origen (si se desconoce, dejar en blanco):","No declarada")||"No declarada";
      const current=read(); current.imports.push({id:"imp-"+Date.now(),name:name.trim(),fileName:file.name,format:ext.toUpperCase(),source:source.trim(),featureCount:valid.length,importedAt:new Date().toISOString(),status:"pending-validation",geojson:{type:"FeatureCollection",features:valid}});
      if(save(current)){data=current;refreshImportedLayers();render();alert("Importación local completada. La capa queda pendiente de validación.");}
    } catch(error) { alert("No se pudo importar el archivo: "+error.message); }
  }

  function open() { shell.classList.add("open"); $("adminSection").hidden=false; refreshImportedLayers(); render(); }
  function close() { shell.classList.remove("open"); pilotMapAction=null; const controls=$("tm-rm-draw-controls");if(controls)controls.remove(); if(importedLayer)importedLayer.clearLayers(); if(pilotRiverLayer)pilotRiverLayer.clearLayers(); if(pilotSectionLayer)pilotSectionLayer.clearLayers(); if(pilotAccessLayer)pilotAccessLayer.clearLayers(); if(draft){draft=null; if(draftLayer){map.removeLayer(draftLayer);draftLayer=null;}} }
  function createTerritory(points) {
    const name=prompt("Nombre del territorio o sector:");
    if(!name || !name.trim()) return;
    const commune=prompt("Comuna:", "Por definir") || "Por definir";
    const waterbody=prompt("Cuerpo de agua asociado (río, lago o laguna):","Por definir") || "Por definir";
    data=read(); data.territories.push({id:"ter-"+Date.now(),name:name.trim(),commune:commune.trim(),waterbody:waterbody.trim(),points:points.map(p=>[p.lat,p.lng]),createdAt:new Date().toISOString(),status:"draft"});
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
    if(!shell.classList.contains("open")) return;
    if(tab==="rio-medio" && handlePilotMapClick(e)) return;
    if(!draft || tab!=="territories") return;
    draft.push(e.latlng);
    if(draftLayer)map.removeLayer(draftLayer);
    draftLayer=(draft.length>=3?L.polygon(draft,{color:"#55d9e8",weight:2,dashArray:"6 5",fillColor:"#258ba8",fillOpacity:.18}):L.polyline(draft,{color:"#55d9e8",weight:2,dashArray:"6 5"})).addTo(map);
    if(draft.length>1)map.fitBounds(draftLayer.getBounds(),{padding:[80,80],maxZoom:13});
  });

  shell.querySelectorAll("[data-tm-tab]").forEach(b=>b.addEventListener("click",()=>{tab=b.dataset.tmTab;render();}));
  $("tm-close").onclick=close;
  $("tm-settings").onclick=()=>{tab="settings";render();};
  $("profileSelect").onchange=e=>{
    if(e.target.value==="admin"){tab="overview";open();} else if(e.target.value==="operator"){tab="operator-portal";open();} else if(e.target.value==="angler"){tab="angler-portal";open();} else close();
  };
  $("territoryBtn").onclick=()=>{tab="territories";open();};
  $("accessBtn").onclick=()=>{tab="access";open();};
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&shell.classList.contains("open"))close();});
  const requestedProfile=new URLSearchParams(location.search).get("profile");
  if(["admin","operator","angler"].includes(requestedProfile)){ $("profileSelect").value=requestedProfile; tab=requestedProfile==="admin"?"overview":requestedProfile==="operator"?"operator-portal":"angler-portal"; open(); }
  console.info("AnglerMap Territory Manager: interfaz demo cargada; sin backend ni permisos reales.");
})();