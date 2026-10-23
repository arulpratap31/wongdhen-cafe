/* V28 progressive enhancements: no new dependency, no fabricated business data. */
(()=>{'use strict';
const ready=f=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',f,{once:true}):f();
const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
ready(()=>{
  const body=document.body;
  document.querySelectorAll('.v27-foot-label').forEach(n=>n.textContent='V28 • SIGNATURE EXPERIENCE');
  // Brand-new display tokens layer on top of fourteen themes; leave theme choices unchanged.
  document.documentElement.dataset.v28='studio';
  // Group the OVERLAY links without removing a single legacy destination or onclick handler.
  const nav=document.querySelector('#navOverlay .v4-nav-links');
  if(nav&&!nav.dataset.v28Grouped){
    nav.dataset.v28Grouped='true';nav.querySelectorAll('.v27-nav-category').forEach(n=>n.remove());
    const originals=Array.from(nav.querySelectorAll(':scope > a[href]'));
    const groups=[
      ['DISCOVER',['/','/about','/gallery','/lookbook','/photo-book','/journal','/concierge','/tour','/reels']],
      ['FOOD & DRINK',['/menu','/taste-studio','/discover','/compare','/order']],
      ['VISIT & PLAN',['/visit','/reservations','/manage-booking','/queue','/group-events','/contact','/checkin']],
      ['YOUR WONGDHEN',['/account','/rewards']]
    ];
    for(const [name,paths] of groups){
      const section=el('section','v28-nav-group');section.setAttribute('aria-label',name.toLowerCase());
      const heading=el('h2','v28-nav-heading',name);section.append(heading);
      const holder=el('div','v28-nav-links');section.append(holder);
      paths.forEach(path=>{const link=originals.find(a=>a.getAttribute('href')===path);if(link)holder.append(link);});
      if(holder.children.length)nav.append(section);
    }
    const leftovers=originals.filter(a=>a.parentElement===nav);
    if(leftovers.length){const section=el('section','v28-nav-group');section.append(el('h2','v28-nav-heading','MORE'));leftovers.forEach(a=>section.append(a));nav.append(section);}
  }
  // Navigation consistency; old V27 initial state is still honored.
  const current=(location.pathname.replace(/\/$/,'')||'/');
  document.querySelectorAll('nav a[href^="/"]').forEach(a=>{
    if((a.pathname.replace(/\/$/,'')||'/')===current){a.setAttribute('aria-current','page');a.classList.add('v28-active');}
  });
  // Auto-surface the incomplete online-booking status once, without misrepresenting availability.
  if(body.dataset.page==='reservations'){
    const host=document.getElementById('app');
    fetch('/api/v28/public/readiness',{credentials:'same-origin'})
      .then(r=>{if(!r.ok)throw Error('status unavailable');return r.json()})
      .then(info=>{if(!info.online_booking_requests_enabled&&host){
        const notice=el('aside','v28-reservation-status','Online reservation requests are not yet enabled for this café configuration. Please contact the café to confirm arrangements.');
        notice.setAttribute('role','status');host.prepend(notice);
      }}).catch(()=>{/* Retain existing booking interface, which has its own errors. */});
  }
  // Accessible, server-backed, bounded menu browser. It does not replace the menu book.
  if(body.dataset.page==='menu'){
    const directory=document.querySelector('.v27-menu-guide');
    if(directory){
      const panel=el('section','v28-menu-browser');panel.id='v28MenuBrowser';
      const kicker=el('p','v28-eyebrow','A MORE CONVENIENT WAY TO EXPLORE');
      const heading=el('h2','v28-menu-title','Find something wonderful.');
      const desc=el('p','v28-menu-desc','Search the published menu. The original page-turning menu and chapter directory remain available below.');
      const form=el('form','v28-menu-filters');form.setAttribute('role','search');
      const label=el('label','v28-sr-only','Search menu by dish name');label.htmlFor='v28DishSearch';
      const input=el('input','v28-menu-input');input.id='v28DishSearch';input.type='search';input.maxLength=80;input.placeholder='Search dishes, coffee, desserts…';input.autocomplete='off';
      const category=el('select','v28-menu-category');category.id='v28DishCategory';category.setAttribute('aria-label','Filter dishes by category');
      const all=el('option',null,'All menu chapters');all.value='';category.append(all);
      const clear=el('button','v28-menu-reset','RESET');clear.type='button';
      form.append(label,input,category,clear);
      const status=el('p','v28-browser-status','Browse the current published menu transcription.');status.id='v28MenuStatus';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
      const grid=el('div','v28-menu-grid');grid.id='v28MenuResults';
      const pager=el('div','v28-menu-pagination');
      const prev=el('button','v28-menu-prev','← PREVIOUS');prev.type='button';
      const range=el('span','v28-menu-range','');const next=el('button','v28-menu-next','NEXT →');next.type='button';
      pager.append(prev,range,next);
      const foot=el('p','v28-menu-disclaimer','Planning only. The café must confirm current prices, ingredients and availability. No item is ordered by browsing.');
      panel.append(kicker,heading,desc,form,status,grid,pager,foot);
      directory.before(panel);
      let offset=0,sequence=0,timer;
      const size=18;
      const setBusy=b=>{grid.setAttribute('aria-busy',String(b));prev.disabled=b;next.disabled=b;};
      async function refresh(){
        const seq=++sequence;setBusy(true);status.textContent='Looking up published dishes…';
        const params=new URLSearchParams({q:input.value.trim(),category:category.value,limit:String(size),offset:String(offset)});
        try{
          const response=await fetch('/api/v28/menu/browse?'+params,{credentials:'same-origin'});
          if(!response.ok)throw Error('Unable to load dishes right now');
          const data=await response.json();if(seq!==sequence)return;
          grid.replaceChildren();
          for(const item of data.items){
            const card=el('article','v28-dish-card');
            const title=el('h3','',item.name),meta=el('p','v28-dish-category',item.category);
            const price=el('p','v28-dish-price',item.price_display||'Ask the café');
            const link=el('a','v28-dish-link','VIEW DISH ↗');link.href='/menu?item='+encodeURIComponent(item.id);
            const verification=el('small','v28-dish-verification',item.owner_approved?'Owner-reviewed record':'Menu transcription • verify price');
            card.append(meta,title,price,verification,link);grid.append(card);
          }
          if(!data.items.length)grid.append(el('p','v28-empty','No dishes match this search. Try another category or search term.'));
          prev.disabled=offset===0;next.disabled=!data.has_more;
          const from=data.total?offset+1:0;range.textContent=`${from}–${offset+data.items.length} OF ${data.total}`;
          status.textContent=`${data.total} matching published ${data.total===1?'dish':'dishes'}. Results are indicative, not live restaurant stock.`;
        }catch(e){if(seq!==sequence)return;grid.replaceChildren(el('p','v28-empty','The list could not load. The original menu book remains available below.'));status.textContent='Menu lookup temporarily unavailable.';prev.disabled=true;next.disabled=true;range.textContent='';}
        finally{if(seq===sequence)grid.setAttribute('aria-busy','false');}
      }
      const changed=()=>{offset=0;clearTimeout(timer);timer=setTimeout(refresh,200);};
      input.addEventListener('input',changed);category.addEventListener('change',changed);
      form.addEventListener('submit',e=>{e.preventDefault();offset=0;refresh();});
      clear.addEventListener('click',()=>{input.value='';category.value='';offset=0;refresh();input.focus();});
      prev.addEventListener('click',()=>{offset=Math.max(0,offset-size);refresh();panel.scrollIntoView({block:'start',behavior:'auto'});});
      next.addEventListener('click',()=>{offset+=size;refresh();panel.scrollIntoView({block:'start',behavior:'auto'});});
      fetch('/api/v27/menu/categories').then(r=>r.ok?r.json():Promise.reject()).then(d=>{
        (d.categories||[]).forEach(x=>{const opt=el('option',null,x.name);opt.value=x.name;category.append(opt);});
      }).catch(()=>{/* Search still works without category suggestions */});
      refresh();
    }
  }
  // Owner operations: exact blockers, no arbitrary commercial-readiness score.
  const quality=document.getElementById('v27Quality');
  if(quality){
    const section=el('section','v28-owner-quality');
    section.append(el('h2',null,'Launch checklist & next actions'));
    const label=el('p',null,'Checking live configuration, not claiming security certification…');
    const list=el('div','v28-owner-checks');section.append(label,list);
    quality.after(section);
    fetch('/api/v28/admin/readiness',{credentials:'same-origin'}).then(r=>{
      if(!r.ok)throw Error('Owner sign-in required');return r.json();
    }).then(data=>{
      label.textContent=`${data.configured_count} of ${data.total_checks} configuration checks currently pass. This is NOT production approval.`;
      for(const item of data.checks){
        const row=el('article','v28-owner-check');
        const state=el('b',item.configured?'v28-ok':'v28-review',item.configured?'CONFIGURED':'NEEDS REVIEW');
        row.append(state,el('h3',null,item.name),el('p',null,item.detail),el('small',null,item.next_action));list.append(row);
      }
    }).catch(()=>{label.textContent='Launch checklist requires an owner session. The existing operations tools remain available.';});
  }
});
})();
