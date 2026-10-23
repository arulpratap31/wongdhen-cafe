/* V26 incremental interface. Uses only published dish IDs; no order or payment flow. */
(()=>{'use strict';
 const ready=fn=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',fn):fn();
 ready(()=>{
  const root=document.documentElement;
  const offlineBadge=document.getElementById('v26OfflineNotice');
  const updateNetwork=()=>{if(offlineBadge){offlineBadge.hidden=navigator.onLine;offlineBadge.textContent='Offline mode: cached menu prices may be out of date.';}};
  window.addEventListener('offline',updateNetwork);window.addEventListener('online',updateNetwork);updateNetwork();
  if('serviceWorker' in navigator && (location.protocol==='https:'||['127.0.0.1','localhost'].includes(location.hostname)))navigator.serviceWorker.register('/service-worker.js').catch(()=>{});
  const ambience=document.getElementById('v26AmbienceToggle');
  try{if(localStorage.getItem('wongdhen-v26-light')==='evening')root.dataset.v26Ambience='evening';}catch(e){}
  const renderLight=()=>{if(ambience){const evening=root.dataset.v26Ambience==='evening';ambience.setAttribute('aria-pressed',String(evening));ambience.textContent=evening?'DAYLIGHT':'EVENING LIGHT';}};renderLight();
  ambience?.addEventListener('click',()=>{root.dataset.v26Ambience=root.dataset.v26Ambience==='evening'?'day':'evening';try{localStorage.setItem('wongdhen-v26-light',root.dataset.v26Ambience);}catch(e){}renderLight();});
  const lite=document.getElementById('v26LiteMode');
  try{if(localStorage.getItem('wongdhen-v26-lite')==='on'){root.dataset.v26Data='lite';if(lite)lite.checked=true;}}catch(e){}
  lite?.addEventListener('change',()=>{root.dataset.v26Data=lite.checked?'lite':'full';try{localStorage.setItem('wongdhen-v26-lite',lite.checked?'on':'off');}catch(e){}});
  const dialog=document.getElementById('v26PlannerDialog'),open=document.getElementById('v26PlannerOpen');
  if(!dialog||!open)return;
  const search=document.getElementById('v26PlanSearch'),results=document.getElementById('v26PlanResults'),chosen=document.getElementById('v26PlanChosen'),status=document.getElementById('v26PlanStatus'),share=document.getElementById('v26PlanShare');
  const close=()=>dialog.close();
  document.getElementById('v26PlanClose')?.addEventListener('click',close);
  open.addEventListener('click',()=>{dialog.showModal();search?.focus();refresh();});
  dialog.addEventListener('click',e=>{if(e.target===dialog)close();});
  let rows=[],sel=[];
  try{const stored=JSON.parse(localStorage.getItem('wongdhen-v26-plan')||'[]');if(Array.isArray(stored))sel=stored.filter(Number.isInteger).slice(0,12);}catch(e){}
  const parsed=new URLSearchParams(location.search).get('plan');
  if(parsed && /^\d{1,6}(?:,\d{1,6}){0,11}$/.test(parsed))sel=[...new Set(parsed.split(',').map(Number))];
  const persist=()=>{try{localStorage.setItem('wongdhen-v26-plan',JSON.stringify(sel));}catch(e){}};
  const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const render=()=>{
    if(!rows.length){chosen.textContent='Open the menu online once to build a shortlist.';return;}
    sel=sel.filter(id=>rows.some(x=>x.id===id));persist();
    if(!sel.length){chosen.textContent='No dishes selected. Choose from the published menu below.';status.textContent='A shortlist is for planning only. No order is placed.';return;}
    chosen.innerHTML=sel.map(id=>{const r=rows.find(x=>x.id===id);return `<div class="v26-picked"><span><b>${esc(r.name)}</b><small>${esc(r.price_display)} · original menu transcription</small></span><button data-v26-remove="${r.id}" type="button" aria-label="Remove ${esc(r.name)}">REMOVE</button></div>`}).join('');
    chosen.querySelectorAll('[data-v26-remove]').forEach(btn=>btn.addEventListener('click',()=>{sel=sel.filter(id=>id!==Number(btn.dataset.v26Remove));render();}));
    status.textContent='Checking the selected dishes…';
    fetch('/api/v26/menu/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({item_ids:sel})}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
      status.textContent=d.all_prices_unambiguous?`Indicative subtotal ₹${d.subtotal_inr} for ${sel.length} dishes. Not a quote; taxes/charges not included or verified.`:`Some dishes have multiple price variants. Partial simple-price total ₹${d.partial_known_total_inr}; choose options with café staff before estimating.`;
    }).catch(()=>{status.textContent='Price estimator unavailable offline. List remains available on this device.';});
  };
  const refresh=()=>{if(rows.length){render();return;}fetch('/api/menu',{cache:'no-store'}).then(r=>r.json()).then(d=>{rows=Array.isArray(d.items)?d.items:[];if(d.offline_snapshot)status.textContent='This menu is an offline snapshot — prices may be outdated.';render();lookup();}).catch(()=>{status.textContent='Menu unavailable. Connect to the internet to begin.';});};
  const lookup=()=>{const term=search.value.trim().toLocaleLowerCase();const filtered=rows.filter(x=>x.name.toLocaleLowerCase().includes(term)||x.category.toLocaleLowerCase().includes(term)).slice(0,15);
    results.innerHTML=filtered.map(x=>`<button type="button" data-v26-add="${x.id}"><span>${esc(x.name)} <small>${esc(x.category)}</small></span><span>${esc(x.price_display)}</span></button>`).join('')||'<p>No matching published dishes.</p>';
    results.querySelectorAll('[data-v26-add]').forEach(btn=>btn.addEventListener('click',()=>{const id=Number(btn.dataset.v26Add);if(sel.includes(id))return;if(sel.length>=12){status.textContent='Maximum 12 dishes per plan.';return;}sel.push(id);render();}));
  };
  search.addEventListener('input',lookup);
  share.addEventListener('click',()=>{if(!sel.length){status.textContent='Add dishes before sharing.';return;}const url=new URL('/menu',location.href);url.searchParams.set('plan',sel.join(','));const txt=url.toString();if(navigator.share)navigator.share({title:'Wongdhen Café dining shortlist',url:txt}).catch(()=>{});else if(navigator.clipboard)navigator.clipboard.writeText(txt).then(()=>{status.textContent='Read-only planning link copied. It contains dish IDs, not account data.';}).catch(()=>{status.textContent=txt;});else status.textContent=txt;});
  if(parsed){open.setAttribute('aria-label','Open shared Wongdhen shortlist');}
 });
})();
