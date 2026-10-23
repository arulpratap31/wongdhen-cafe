/* V30 — Owner Command Centre. Presentation-only upgrade; permission checks remain server-side. */
(() => {
  'use strict';
  if (document.body.dataset.page !== 'admin') return;
  const tabs = {
    'owner-desk':['Owner dashboard','OVERVIEW','Sales, registered guests, team access and business intelligence — reserved for the owner.','✦'],
    'owner-editorial':['Editorial & reviews','CONTENT','Owner moderation, featured imagery and anonymous aggregate engagement.','✶'],
    'owner-finance':['Sales & finances','BUSINESS','Owner-confidential financial ledger and recorded net position.','₹'],
    'owner-customers':['Customer accounts','BUSINESS','Private customer directory available only to the owner.','♙'],
    'manager-desk':['Manager dashboard','OVERVIEW','Service performance, reservations, kitchen flow and daily priorities.','◈'],
    'staff-desk':['My staff dashboard','OVERVIEW','Your assigned operational responsibilities in one tidy workspace.','✳'],
    studio:['Dashboard','OVERVIEW','A thoughtful overview of your house, your guests, and today’s priorities.','✦'],
    audit:['Audit & activity','BUSINESS','Owner-only history of recorded management actions.','▤'],
    pulse:['House pulse','OVERVIEW','Verified reservation patterns, open enquiries, and recent staff actions.','◈'],
    launch:['Launch readiness','OVERVIEW','Production configuration and outstanding launch requirements.','◈'],
    'v25-brief':['Today’s brief','OVERVIEW','Real activity from current operational records.','◷'],
    operations:['Imperial operations','OVERVIEW','Staff handovers and daily service issues.','✳'],
    bookings:['Reservations','SERVICE','Requests, confirmations, and guest arrival planning.','▤'],
    calendar:['Booking calendar','SERVICE','See genuine reservations across service dates.','▦'],
    'day-board':['Day operations','SERVICE','Manage the floor during live service.','◉'],
    'special-hours':['Special hours','SERVICE','Closures, exceptions, and holiday opening.','☼'],
    tables:['Table inventory','SERVICE','Manage real seating areas and table capacity.','▣'],
    policy:['Booking rules','SERVICE','Verified availability and capacity policies.','⚑'],
    waitlist:['Waitlist','SERVICE','Track actual customers waiting for a table.','◴'],
    walkins:['Walk-in queue','SERVICE','Manage arrivals without bookings.','↳'],
    kitchen:['Kitchen orders','SERVICE','Handle real orders and fulfilment states.','♨'],
    menu:['Menu manager','CONTENT','Update published dishes, pricing, and approvals.','▰'],
    'dish-details':['Dish photo & details','CONTENT','Verify real photography, ingredients and dish data.','◫'],
    'v10-media':['Photo library','CONTENT','Curate the café’s authentic image collection.','▧'],
    media:['Upload photography','CONTENT','Add approved imagery with confirmed usage rights.','⊕'],
    appearance:['Theme studio','CONTENT','Shape the public café’s visual identity.','◐'],
    inbox:['Guest relations','BUSINESS','Search, review and follow up on actual messages.','✉'],
    settings:['Business details','BUSINESS','Manage owner-confirmed contact and venue details.','⚙'],
    staff:['Team access','BUSINESS','Manage staff roles and account security.','♙'],
    v7:['Guest experiences','BUSINESS','Manage queue, rewards and occasions.','◇'],
    v8:['Commerce & insights','BUSINESS','Manage optional ordering and verified engagement.','▥']
  };
  const groups = ['OVERVIEW','SERVICE','CONTENT','BUSINESS'];
  const descriptions = {OVERVIEW:'THE CONTROL ROOM',SERVICE:'OPERATIONS & GUESTS',CONTENT:'MENU & CREATIVE',BUSINESS:'HOUSE MANAGEMENT'};
  const escape = value => String(value ?? '').replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const get = id => document.getElementById(id);
  let selected = -1;
  let filtered = [];
  let focusBeforeDialog = null;
  let lastMainFocus = null;
  let mobileFocusBefore = null;
  let root = null;
  const buttons = () => [...(root?.querySelectorAll('.admin-actions [data-tab]')||[])];
  const current = () => root?.querySelector('.admin-actions [data-tab].active');
  const select = id => buttons().find(b => b.dataset.tab === id);
  const safeCount = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN') : '—';
  const closeDrawer = () => {
    document.body.classList.remove('v30-sidebar-open');
    get('v30MenuToggle')?.setAttribute('aria-expanded','false');
    const back = get('v30Backdrop');if(back) back.hidden=true;
    const sidebar=get('v30Sidebar');
    const compact=window.matchMedia('(max-width:1000px)').matches;
    if(sidebar){sidebar.inert=compact;if(compact)sidebar.setAttribute('aria-hidden','true');else sidebar.removeAttribute('aria-hidden');}
  };
  const openDrawer = () => {
    mobileFocusBefore = document.activeElement;
    document.body.classList.add('v30-sidebar-open');
    const sidebar=get('v30Sidebar');if(sidebar){sidebar.inert=false;sidebar.removeAttribute('aria-hidden');}
    get('v30MenuToggle')?.setAttribute('aria-expanded','true');
    const back = get('v30Backdrop');if(back) back.hidden=false;
    const focusTarget = current()||buttons()[0];focusTarget?.focus();
  };
  function setActive(id) {
    const detail=tabs[id]||[id,'WORKSPACE','Manage the current section.','◇'];
    for(const b of buttons()) {
      const active=b.dataset.tab===id;b.classList.toggle('active',active);
      if(active){b.setAttribute('aria-current','page');} else {b.removeAttribute('aria-current');}
    }
    const title=get('v30PageTitle'),desc=get('v30PageDesc'),group=get('v30PageGroup'),crumb=get('v30CurrentSection');
    if(title)title.textContent=detail[0];
    if(desc)desc.textContent=detail[2];
    if(group)group.textContent='YOUR WORKSPACE / '+detail[1];
    if(crumb)crumb.textContent=detail[0].toUpperCase();
    closeDrawer();
    if(!window.matchMedia('(max-width:1000px)').matches)select(id)?.scrollIntoView({block:'nearest',behavior:'instant'});
    window.scrollTo({top:0,behavior:'instant'});
    if(lastMainFocus){lastMainFocus=null;title?.setAttribute('tabindex','-1');title?.focus({preventScroll:true});}
  }
  function navTo(id) {
    const b=select(id);if(b){lastMainFocus=true;b.click();closeCommand();}
  }
  function createGroups() {
    const nav=root.querySelector('.admin-actions');
    for(const group of groups) {
      const controls=buttons().filter(b=>(tabs[b.dataset.tab]?.[1]||'BUSINESS')===group);
      if(!controls.length)continue;
      const section=document.createElement('div');section.className='v30-navigation-group';
      const heading=document.createElement('p');heading.className='v30-group-heading';heading.textContent=descriptions[group]||group;
      section.append(heading);
      controls.forEach(b=>{
        const conf=tabs[b.dataset.tab]||[b.dataset.tab,'BUSINESS','', '◇'];
        b.classList.add('v30-side-link');
        b.innerHTML=`<span class="v30-link-icon" aria-hidden="true">${escape(conf[3])}</span><span class="v30-link-name">${escape(conf[0])}</span><span class="v30-link-arrow" aria-hidden="true">↗</span>`;
        b.setAttribute('title',conf[0]);
        section.append(b);
      });
      nav.append(section);
    }
  }
  function renderCommands(query=''){
    filtered=buttons().filter(b=>(tabs[b.dataset.tab]?.[0]||'').toLowerCase().includes(query.toLowerCase().trim()));
    selected=filtered.length?0:-1;
    const results=get('v30CommandResults');if(!results)return;
    results.innerHTML=filtered.length ? filtered.map((b,i)=>{
      const d=tabs[b.dataset.tab];return `<button type="button" class="v30-command-result${i===selected?' selected':''}" role="option" aria-selected="${i===selected}" data-v30-result="${escape(b.dataset.tab)}"><span>${escape(d?.[3]||'◇')}</span><span>${escape(d?.[0]||b.dataset.tab)}<small>${escape(d?.[1]||'MANAGE')}</small></span><span aria-hidden="true">↗</span></button>`;
    }).join(''):'<p class="v30-search-empty">No matching tools available to your account.</p>';
    results.querySelectorAll('[data-v30-result]').forEach(b=>b.addEventListener('click',()=>navTo(b.dataset.v30Result)));
  }
  function openCommand() {
    const dialog=get('v30Command');if(!dialog||!buttons().length)return;
    focusBeforeDialog=document.activeElement;
    if(!dialog.open)dialog.showModal();
    const search=get('v30CommandSearch');search.value='';renderCommands();search.focus();
  }
  function closeCommand(){const d=get('v30Command');if(d?.open)d.close();focusBeforeDialog?.focus?.();focusBeforeDialog=null;}
  function mount(target, role) {
    root=target;
    createGroups();
    window.matchMedia('(max-width:1000px)').addEventListener('change',closeDrawer);
    const pill=get('v30RoleBadge');if(pill)pill.textContent=role==='admin'?'OWNER':role.replace(/_/g,' ').toUpperCase();
    const mobile=get('v30MenuToggle');mobile?.addEventListener('click',()=>document.body.classList.contains('v30-sidebar-open')?closeDrawer():openDrawer());
    get('v30Backdrop')?.addEventListener('click',()=>{closeDrawer();mobileFocusBefore?.focus?.();});
    get('v30CloseMenu')?.addEventListener('click',()=>{closeDrawer();mobileFocusBefore?.focus?.();});
    get('v30CommandOpen')?.addEventListener('click',openCommand);
    get('v30CommandClose')?.addEventListener('click',closeCommand);
    get('v30CommandSearch')?.addEventListener('input',e=>renderCommands(e.target.value));
    get('v30CommandSearch')?.addEventListener('keydown',e=>{
      if(e.key==='Escape'){e.preventDefault();closeCommand();return;}
      if(!filtered.length)return;
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){
        e.preventDefault();selected=(selected+(e.key==='ArrowDown'?1:-1)+filtered.length)%filtered.length;
        const rows=get('v30CommandResults')?.querySelectorAll('.v30-command-result')||[];
        rows.forEach((r,i)=>{r.classList.toggle('selected',i===selected);r.setAttribute('aria-selected',String(i===selected));});
        rows[selected]?.scrollIntoView({block:'nearest'});
      }else if(e.key==='Enter'){e.preventDefault();navTo(filtered[selected].dataset.tab);}
    });
    const modal=get('v30Command');modal?.addEventListener('click',e=>{if(e.target===modal)closeCommand()});
    modal?.addEventListener('cancel',e=>{e.preventDefault();closeCommand()});
    modal?.addEventListener('close',()=>{focusBeforeDialog?.focus?.();focusBeforeDialog=null;});
    document.addEventListener('keydown', e=>{
      if(!document.body.classList.contains('v30-authenticated'))return;
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){
        e.preventDefault();e.stopImmediatePropagation();if(get('v30Command')?.open)closeCommand();else openCommand();
      }
      if(e.key==='Escape'&&document.body.classList.contains('v30-sidebar-open'))closeDrawer();
    },true);
    const appearance=get('v30Appearance');
    try {if(localStorage.getItem('wongdhen-admin-appearance')==='light')document.body.classList.add('v30-admin-light');}catch{}
    const updateAppearance=()=>appearance?.setAttribute('aria-pressed',String(document.body.classList.contains('v30-admin-light')));
    appearance?.addEventListener('click',()=>{
      document.body.classList.toggle('v30-admin-light');
      const light=document.body.classList.contains('v30-admin-light');
      try{localStorage.setItem('wongdhen-admin-appearance',light?'light':'dark');}catch{}
      updateAppearance();
    });updateAppearance();
    // Avoid a stale aria-current inherited from another render.
    setActive(buttons()[0]?.dataset.tab||'studio');
  }
  function enhanceMenuTable(tab) {
    const table=tab.querySelector('.admin-menu-list table');if(!table)return;
    const rows=[...table.querySelectorAll('tbody tr')];
    if(!rows.length)return;
    const bar=document.createElement('div');bar.className='v30-menu-toolbar';
    bar.innerHTML='<label>FIND AN ITEM<input id="v30MenuSearch" type="search" placeholder="Search menu names & categories" maxlength="80" autocomplete="off"/></label><label>VERIFICATION<select id="v30MenuStatus"><option value="all">All menu items</option><option value="pending">Awaiting approval</option><option value="approved">Approved prices</option><option value="unpublished">Unpublished items</option></select></label><div class="v30-menu-pager"><span id="v30MenuCount" role="status"></span><button type="button" id="v30MenuPrevious" aria-label="Previous menu page">←</button><button type="button" id="v30MenuNext" aria-label="Next menu page">→</button></div>';
    tab.querySelector('.admin-menu-list').before(bar);
    const search=get('v30MenuSearch'),status=get('v30MenuStatus');let pg=0;const size=28;
    function draw(){
      const q=search.value.trim().toLowerCase(),st=status.value;
      const visible=rows.filter(r=>{
        const name=r.cells[0]?.textContent.toLowerCase()||'';
        if(q&&!name.includes(q))return false;
        const approved=r.querySelector('.itemapproved')?.checked||false;
        const published=r.querySelector('.itempublished')?.checked||false;
        return st==='all'||(st==='approved'&&approved)||(st==='pending'&&!approved)||(st==='unpublished'&&!published);
      });
      const totalPages=Math.max(1,Math.ceil(visible.length/size));pg=Math.min(pg,totalPages-1);
      const slice=new Set(visible.slice(pg*size,(pg+1)*size));rows.forEach(r=>{r.hidden=!slice.has(r)});
      get('v30MenuCount').textContent=`${visible.length===0?'0':`${pg*size+1}–${Math.min((pg+1)*size,visible.length)}`} of ${visible.length} items`;
      get('v30MenuPrevious').disabled=pg===0;get('v30MenuNext').disabled=pg+1>=totalPages;
    }
    search.addEventListener('input',()=>{pg=0;draw()});status.addEventListener('change',()=>{pg=0;draw()});
    get('v30MenuPrevious').addEventListener('click',()=>{pg--;draw()});get('v30MenuNext').addEventListener('click',()=>{pg++;draw()});draw();
  }
  window.WongdhenV30={mount,setActive,enhanceMenuTable,openCommand};
})();
