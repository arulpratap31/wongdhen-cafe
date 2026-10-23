/* V25 GRAND MAISON: public universal discovery, optional reading controls, and progressive navigation. */
(() => {
 'use strict';
 const byId = id => document.getElementById(id);
 const searchDialog = byId('v25SearchDialog');
 const displayDialog = byId('v25DisplayDialog');
 const input = byId('v25SearchField');
 const results = byId('v25Results');
 const status = byId('v25SearchStatus');
 const scopes = [...document.querySelectorAll('[data-v25-scope]')];
 const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 const RECENT_KEY = 'wongdhen-v25-recent';
 const DISPLAY_KEY = 'wongdhen-v25-display';
 const supported = typeof HTMLDialogElement !== 'undefined';
 let scope = 'all', current = [], selected = -1, requestSerial = 0, debounce;
 const publicLinks = new Set(['/','/about','/menu','/gallery','/photo-book','/journal','/visit','/reservations','/concierge','/account','/discover']);
 const recent = () => {try { const x=JSON.parse(localStorage.getItem(RECENT_KEY)||'[]');return Array.isArray(x)?x.filter(item=>publicLinks.has(item.url)).slice(0,5):[] }catch{return []}};
 function remember(url) {
   if(!publicLinks.has(url))return;
   const list=[{url, label: document.title.split('—')[0].trim() || url},...recent().filter(x=>x.url!==url)].slice(0,5);
   try{localStorage.setItem(RECENT_KEY,JSON.stringify(list))}catch{}
 }
 // Record only simple public page visits, locally, without uploading activity or personal details.
 remember(location.pathname);
 function openDialog(dialog){if(!supported){dialog.setAttribute('open','');dialog.hidden=false;return}if(!dialog.open)dialog.showModal()}
 function closeDialog(dialog){if(supported&&dialog.open)dialog.close();else {dialog.removeAttribute('open');dialog.hidden=true}}
 function renderEmpty(){const items = recent();current=items.map(i=>({title:i.label,subtitle:'Recently visited on this device',href:i.url,kind:'recent'}));
   if (!items.length) { results.innerHTML='<p class="v25-empty">Explore our menu, photography, table reservations or the House Guide.</p>';status.textContent='Search our published content.';input.setAttribute('aria-expanded','false');return }
   draw();status.textContent='Recently visited pages on this device. You can clear this history at any time.';
 }
 function draw(){selected=-1;input.removeAttribute('aria-activedescendant');
   results.innerHTML=current.length ? current.map((r,i)=>{
     const photo=r.thumbnail ? `<img src="${esc(r.thumbnail)}" alt="" loading="lazy">` : `<span aria-hidden="true" class="v25-result-symbol">${r.kind==='dish'?'◈':r.kind==='page'?'↗':'◉'}</span>`;
     // URLs originate from the server but still validate against known internal path prefixes.
     const destination = safeDestination(r.href);
     return `<a id="v25Result${i}" role="option" aria-selected="false" class="v25-result" href="${esc(destination)}" data-v25-index="${i}">${photo}<span class="v25-result-copy"><strong>${esc(r.title)}</strong><small>${esc(r.subtitle)}</small></span><span class="v25-result-type">${esc(r.kind||'page')}</span></a>`;
   }).join(''):'<p class="v25-empty">No published matches. Try another word or a different category.</p>';
   input.setAttribute('aria-expanded',String(current.length>0));
 }
 function safeDestination(value){try{const url=new URL(String(value||'/'),location.origin);if(url.origin!==location.origin)return '/'; if(!url.pathname.startsWith('/'))return '/';return url.pathname + url.search;}catch{return '/'}}
 function highlight(i){if(!current.length)return;selected=(i+current.length)%current.length;results.querySelectorAll('[role="option"]').forEach((n,x)=>{n.setAttribute('aria-selected',String(x===selected));n.classList.toggle('active',x===selected)}); const row=byId('v25Result'+selected);if(row){input.setAttribute('aria-activedescendant',row.id);row.scrollIntoView({block:'nearest'})}}
 async function search(){const term=input.value.trim();const serial=++requestSerial; if(!term){renderEmpty();return}if(term.length<2){current=[];draw();status.textContent='Type at least two characters.';return}
   status.textContent='Searching…';try{const response=await fetch('/api/v25/search?'+new URLSearchParams({q:term,scope,limit:'8'}),{credentials:'same-origin'});
     if(!response.ok)throw new Error('Search unavailable');const data=await response.json();if(serial!==requestSerial)return;
     current=data.results||[];draw();status.textContent=current.length?`${current.length} matching items. Menu prices may need owner verification.`:'No matching published content found.';
   }catch{if(serial!==requestSerial)return;current=[];draw();status.textContent='Search is temporarily unavailable.'}}
 function showSearch(){openDialog(searchDialog);input.value='';scope='all';for(const b of scopes){const chosen=b.dataset.v25Scope==='all';b.classList.toggle('active',chosen);b.setAttribute('aria-pressed',String(chosen))}renderEmpty();input.focus()}
 byId('v25SearchOpen')?.addEventListener('click',showSearch);
 searchDialog?.querySelector('[data-v25-close-search]')?.addEventListener('click',()=>closeDialog(searchDialog));
 searchDialog?.addEventListener('click',event=>{if(event.target===searchDialog)closeDialog(searchDialog)});
 input?.addEventListener('input',()=>{clearTimeout(debounce);const s=++requestSerial;debounce=setTimeout(()=>{if(s===requestSerial)search()},160)});
 input?.addEventListener('keydown',event=>{if(event.key==='ArrowDown'){event.preventDefault();highlight(selected+1)}else if(event.key==='ArrowUp'){event.preventDefault();highlight(selected<0?current.length-1:selected-1)}else if(event.key==='Enter'&&selected>=0){event.preventDefault();byId('v25Result'+selected)?.click()} });
 scopes.forEach(button=>button.addEventListener('click',()=>{scope=button.dataset.v25Scope;scopes.forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});search()}));
 byId('v25ClearHistory')?.addEventListener('click',()=>{try{localStorage.removeItem(RECENT_KEY)}catch{}renderEmpty()});
 document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(searchDialog.open)closeDialog(searchDialog);else showSearch()}});
 const scale=byId('v25TextSize'),scaleOutput=byId('v25TextValue'),contrast=byId('v25HighContrast');
 let displayInMemory={};
 function restoreDisplay(){let saved=displayInMemory;try{saved=JSON.parse(localStorage.getItem(DISPLAY_KEY)||'{}')}catch{}
   const pct=Math.min(130,Math.max(100,Number(saved.textSize)||100));const high=!!saved.highContrast;
   document.documentElement.style.setProperty('--v25-text-scale',String(pct/100));
   document.documentElement.dataset.v25Highcontrast=high?'on':'off';
   if(scale)scale.value=String(pct);if(scaleOutput)scaleOutput.textContent=pct+'%';if(contrast)contrast.checked=high;
 }
 function saveDisplay(){let settings={textSize:Number(scale.value),highContrast:contrast.checked};displayInMemory=settings;try{localStorage.setItem(DISPLAY_KEY,JSON.stringify(settings))}catch{}restoreDisplay()}
 scale?.addEventListener('input',saveDisplay);contrast?.addEventListener('change',saveDisplay);
 byId('v25ResetDisplay')?.addEventListener('click',()=>{displayInMemory={};try{localStorage.removeItem(DISPLAY_KEY)}catch{}restoreDisplay()});
 byId('v25DisplayOpen')?.addEventListener('click',()=>openDialog(displayDialog));
 displayDialog?.querySelectorAll('[data-v25-close-display]').forEach(b=>b.addEventListener('click',()=>closeDialog(displayDialog)));
 displayDialog?.addEventListener('click',e=>{if(e.target===displayDialog)closeDialog(displayDialog)});
 restoreDisplay();
 // The optional first-visit guide is a normal route, never a blocking overlay.
 if(document.body.dataset.page==='home'){
   const intro=document.querySelector('.hero-actions');
   if(intro&&!intro.querySelector('.v25-brand-guide'))intro.insertAdjacentHTML('beforeend','<a class="v25-brand-guide" href="/concierge">THE HOUSE EXPERIENCE <span aria-hidden="true">↗</span></a>');
   // The existing V13 homepage loads asynchronously; enhance it after its actual content arrives.
   const stage=byId('app');
   function addEditorial(){if(byId('v25HomeAtelier'))return true;
     const destination=stage?.querySelector('.v18-discovery-band');if(!destination)return false;
     destination.insertAdjacentHTML('afterend',`<section id="v25HomeAtelier" class="v25-atelier-triptych" aria-labelledby="v25HomeAtelierTitle">
       <div class="v25-atelier-heading"><div><span>AN EDITORIAL GUIDE / GRAND MAISON</span><h2 id="v25HomeAtelierTitle">A place to <em>linger.</em></h2></div><p>Three little windows into Wongdhen Café, photographed at the real venue. Explore its food, spaces and visiting details.</p></div>
       <div class="v25-atelier-tiles">
        <a href="/menu"><img src="/static/v10/large/P0195.webp" alt="Original Wongdhen food photograph" width="720" height="900" loading="lazy"><span><b>01 / FOOD</b><strong>The flavours.</strong><small>EXPLORE THE MENU ↗</small></span></a>
        <a href="/gallery"><img src="/static/v10/large/P0273.webp" alt="Warm Wongdhen café dining interior with tables" width="720" height="900" loading="lazy"><span><b>02 / THE SPACE</b><strong>The atmosphere.</strong><small>EXPLORE PHOTOGRAPHS ↗</small></span></a>
        <a href="/visit"><img src="/static/v10/large/P0222.webp" alt="Photograph of covered Wongdhen outdoor terrace seating" width="720" height="900" loading="lazy"><span><b>03 / THE VISIT</b><strong>Come on in.</strong><small>PLAN YOUR VISIT ↗</small></span></a>
       </div><p class="v25-atelier-foot">ORIGINAL CAFÉ PHOTOGRAPHY · DIGITAL EDITORIAL COMPOSITION, NOT AN ADVERTISED FACILITY OR HOTEL RATING</p>
     </section>`);
     return true;
   }
   if(!addEditorial()&&stage){const watcher=new MutationObserver(()=>{if(addEditorial())watcher.disconnect()});watcher.observe(stage,{childList:true,subtree:false});setTimeout(()=>watcher.disconnect(),20000)}
 }
})();
