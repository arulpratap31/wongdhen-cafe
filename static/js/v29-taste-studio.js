/* V29 – published-menu discovery & planning. No guest tracking or fabricated stock. */
(()=>{'use strict';
const ready=fn=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',fn,{once:true}):fn();
const e=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
const get=(id)=>document.getElementById(id);
const endpoints={topics:'/api/v29/taste/topics',items:'/api/v29/taste/items',shortlist:'/api/v29/taste/shortlist',visit:'/api/v29/visit/essentials'};
async function api(url){const r=await fetch(url,{credentials:'same-origin',headers:{'Accept':'application/json'}});if(!r.ok)throw Error('Service unavailable ('+r.status+')');return r.json();}
function smallButton(text,cls,action){const b=e('button',cls,text);b.type='button';b.addEventListener('click',action);return b;}
function homeInvitation(){
 const app=get('app');if(!app||get('v29HomeInvitation'))return;
 const hero=app.querySelector('.v13-home-hero');if(!hero)return;
 const section=e('section','v29-home-invite');section.id='v29HomeInvitation';section.setAttribute('aria-label','Plan your Wongdhen visit');
 section.innerHTML='<div class="v29-home-image"><img src="/static/images/v10-food.webp" loading="lazy" alt="Real café food photograph"/></div><div class="v29-home-copy"><span class="v29-kicker">THE WONGDHEN EXPERIENCE / NEW</span><h2>From first craving <em>to favourite moment.</em></h2><p>Find dishes from our published menu, make your own shortlist, and explore how to visit—before you arrive.</p><div class="v29-home-actions"><a class="v29-primary-link" href="/taste-studio">EXPLORE THE TASTE STUDIO <span aria-hidden="true">↗</span></a><a class="v29-secondary-link" href="/reservations">RESERVATION INFORMATION</a></div><small>No account required to make a shortlist. Current prices and table availability must be confirmed with the café.</small></div>';
 hero.after(section);
}
function renderStudio(){
 const app=get('app');if(!app)return;
 app.replaceChildren();
 const root=e('section','v29-studio');root.id='v29Studio';
 root.innerHTML=`
  <section class="v29-hero"><div class="v29-hero-art" aria-hidden="true"><img src="/static/images/v10-interior.webp" alt=""/><img src="/static/images/coffee-art.webp" alt=""/></div>
  <div class="v29-hero-content"><p class="v29-kicker">WONGDHEN CAFÉ / YOUR PERSONAL GUIDE</p><h1>A table full of <em>possibilities.</em></h1><p class="v29-hero-lead">Discover the menu at your pace. Collect ideas for your visit, then share your shortlist with friends.</p><div class="v29-hero-actions"><a href="#v29Explore" class="v29-primary-link">EXPLORE THE MENU <span aria-hidden="true">↗</span></a><a href="#v29Visit" class="v29-secondary-link">PLAN YOUR VISIT</a></div><p class="v29-hero-note">Discover, save, and share. Browsing does not place an order or reserve a table.</p></div></section>
  <div class="v29-editorial-bar" aria-label="Explore, save and visit"><span><b>01</b> DISCOVER</span><span><b>02</b> SHORTLIST</span><span><b>03</b> VISIT</span></div>
  <section class="v29-explore" id="v29Explore" aria-labelledby="v29ExploreTitle"><div class="v29-explore-top"><div><p class="v29-kicker">01 / THE TASTE EDIT</p><h2 id="v29ExploreTitle">Explore what <em>sounds good.</em></h2><p>Search genuine published menu entries. These groupings use dish names and menu chapters, not dietary or allergen assumptions.</p></div><div class="v29-mini-photo"><img src="/static/images/coffee-dessert.webp" loading="lazy" alt="Café coffee and dessert"/></div></div>
  <div id="v29TopicChips" class="v29-chips" role="group" aria-label="Filter the menu by interest"><span>Loading published menu categories…</span></div>
  <form id="v29SearchForm" class="v29-search" role="search"><label for="v29SearchInput">Find a dish by name</label><div><input id="v29SearchInput" type="search" placeholder="Try momo, coffee, pasta…" maxlength="70" autocomplete="off"/><button type="submit">SEARCH <span aria-hidden="true">↗</span></button></div></form>
  <p id="v29ResultsStatus" class="v29-status" role="status" aria-live="polite">Loading dishes…</p>
  <div class="v29-results-layout"><div><div id="v29DishGrid" class="v29-dish-grid" aria-busy="true"></div><div class="v29-pages"><button type="button" id="v29Prev" disabled>← PREVIOUS</button><span id="v29Range"></span><button type="button" id="v29Next" disabled>NEXT →</button></div></div><aside class="v29-selection" id="v29Shortlist" aria-labelledby="v29SelectionTitle"><div class="v29-selection-head"><span class="v29-kicker">02 / YOUR SELECTION</span><h3 id="v29SelectionTitle">Your dining <em>shortlist.</em></h3><p>Keep up to eight ideas. Saved locally on this device unless you choose to share a link.</p></div><div id="v29Saved" aria-live="polite"><p>Choose a dish to begin your collection.</p></div><div id="v29Subtotal" class="v29-subtotal" role="status"></div><div class="v29-shortlist-actions"><button type="button" id="v29Share" disabled>SHARE SHORTLIST ↗</button><button type="button" id="v29Clear">CLEAR</button></div><p id="v29ShareStatus" class="v29-caption" role="status" aria-live="polite"></p></aside></div>
  <p class="v29-disclaimer">Menu transcription only. Staff must verify current pricing, ingredients, allergens, and availability. Some dishes offer several price variants; estimates omit uncertain prices.</p></section>
  <section class="v29-visit" id="v29Visit" aria-labelledby="v29VisitTitle"><div class="v29-visit-photo"><img src="/static/images/v10-entrance.webp" loading="lazy" alt="Wongdhen Café entrance photograph"/></div><div class="v29-visit-content"><p class="v29-kicker">03 / THE VISIT</p><h2 id="v29VisitTitle">See you <em>at Wongdhen.</em></h2><p>From the menu to the café, everything in one place.</p><div id="v29VisitFacts" aria-live="polite"><p>Checking the published visiting information…</p></div><div class="v29-visit-actions"><a class="v29-primary-link" href="/visit">EXPLORE LOCATION & PHOTOS ↗</a><a class="v29-secondary-link" href="/reservations">VIEW BOOKING OPTIONS</a></div><p class="v29-caption">Contact the café to confirm the latest hours, current menu and table arrangements.</p></div></section>`;
 app.append(root);
 let topic='all', offset=0, searchSeq=0, debounce, saved=new Map(), itemsOnPage=[];
 const size=12,maxSaved=8,key='wongdhen-v29-local-shortlist';
 const status=get('v29ResultsStatus'),grid=get('v29DishGrid'),chips=get('v29TopicChips'),search=get('v29SearchInput');
 const persist=()=>{try{localStorage.setItem(key,JSON.stringify([...saved.keys()]));}catch(_){/* may be disabled */}};
 try {const raw=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(raw))raw.filter(Number.isSafeInteger).slice(0,maxSaved).forEach(id=>{if(id>0)saved.set(id,null)});}catch(_){}
 try {const url=new URL(location.href);const shared=url.searchParams.get('selected');if(shared&&/^\d+(,\d+){0,7}$/.test(shared)) {saved.clear();shared.split(',').map(Number).filter(Number.isSafeInteger).slice(0,maxSaved).forEach(id=>{if(id>0)saved.set(id,null)});}}
 catch(_){}
 async function refreshShortlist(){
  const host=get('v29Saved'),subtotal=get('v29Subtotal'),share=get('v29Share');
  host.replaceChildren();if(!saved.size){host.append(e('p','v29-empty-saved','Your shortlist is empty. Select any published dish to begin.'));subtotal.textContent='';share.disabled=true;return;}
  const requested=[...saved.keys()].slice(0,maxSaved);
  try{
   const data=await api(endpoints.shortlist+'?'+new URLSearchParams({ids:requested.join(',')}));
   if(requested.join(',')!==[...saved.keys()].join(','))return;
   for(const id of data.missing_ids||[])saved.delete(id);
   for(const item of data.items){saved.set(item.id,item);const row=e('div','v29-saved-item');const text=e('div');text.append(e('strong',null,item.name),e('small',null,item.price_display||'Price to confirm'));row.append(text,smallButton('×','v29-remove',()=>{saved.delete(item.id);persist();refreshShortlist();updateActiveCards();}));host.append(row);}
   if(!saved.size)host.append(e('p',null,'No longer published. Please add another dish.'));
   subtotal.textContent=data.estimate_complete?`Indicative published-price subtotal: ₹${data.estimated_subtotal_rupees}`:'Exact subtotal unavailable where price variants exist. Please confirm at the café.';
   share.disabled=!saved.size;persist();updateActiveCards();
  }catch(_){host.append(e('p',null,'Your shortlist could not be checked. Please try again.'));subtotal.textContent='Price estimate unavailable.';share.disabled=true;}
 }
 function updateActiveCards(){grid.querySelectorAll('button[data-v29-id]').forEach(b=>{const on=saved.has(Number(b.dataset.v29Id));b.textContent=on?'SAVED ✓':'ADD TO SHORTLIST +';b.setAttribute('aria-pressed',String(on));});}
 async function loadItems(){
  const seq=++searchSeq;grid.setAttribute('aria-busy','true');status.textContent='Finding dishes in the published menu…';get('v29Prev').disabled=get('v29Next').disabled=true;
  try{
   const params=new URLSearchParams({topic,q:search.value.trim(),limit:String(size),offset:String(offset)});
   const data=await api(endpoints.items+'?'+params);if(seq!==searchSeq)return;
   itemsOnPage=data.items;grid.replaceChildren();
   for(const item of data.items){
    const card=e('article','v29-dish');
    card.append(e('p','v29-dish-cat',item.category),e('h3',null,item.name));
    const value=e('span','v29-dish-price',item.price_display?'₹ '+item.price_display:'Confirm price');
    const row=e('div','v29-dish-bottom');row.append(value);
    const details=e('a','v29-details','MENU DETAILS ↗');details.href='/menu?item='+encodeURIComponent(item.id);
    const button=smallButton(saved.has(item.id)?'SAVED ✓':'ADD TO SHORTLIST +','v29-add',()=>{
      if(saved.has(item.id))saved.delete(item.id);
      else if(saved.size>=maxSaved){get('v29ShareStatus').textContent='You can save up to eight dishes. Remove one before adding another.';return;}
      else saved.set(item.id,item);
      persist();updateActiveCards();refreshShortlist();
    });button.dataset.v29Id=String(item.id);button.setAttribute('aria-pressed',String(saved.has(item.id)));
    card.append(row,details,button,e('small','v29-verification',item.owner_approved?'Owner-reviewed menu record':'Published menu transcription • confirm current price'));grid.append(card);
   }
   if(!data.items.length)grid.append(e('p','v29-no-results','No published dishes found. Try another word or choose “Everything”.'));
   get('v29Prev').disabled=offset===0;get('v29Next').disabled=!data.has_more;
   get('v29Range').textContent=`${data.total?offset+1:0}–${offset+data.items.length} OF ${data.total}`;
   status.textContent=`${data.total} published menu ${data.total===1?'entry':'entries'} found. Results do not reflect live availability.`;
  }catch(_){if(seq!==searchSeq)return;grid.replaceChildren(e('p','v29-no-results','The menu lookup is temporarily unavailable. You can still open the original menu book.'));status.textContent='Could not load the menu.';get('v29Range').textContent='';}
  finally{if(seq===searchSeq)grid.setAttribute('aria-busy','false');}
 }
 function changed(){offset=0;clearTimeout(debounce);debounce=setTimeout(loadItems,220);}
 get('v29SearchForm').addEventListener('submit',ev=>{ev.preventDefault();offset=0;loadItems();});
 search.addEventListener('input',changed);
 get('v29Prev').addEventListener('click',()=>{offset=Math.max(0,offset-size);loadItems();get('v29Explore').scrollIntoView({block:'start'});});
 get('v29Next').addEventListener('click',()=>{offset+=size;loadItems();get('v29Explore').scrollIntoView({block:'start'});});
 get('v29Clear').addEventListener('click',()=>{saved.clear();persist();refreshShortlist();updateActiveCards();get('v29ShareStatus').textContent='Shortlist cleared.';});
 get('v29Share').addEventListener('click',async()=>{
  const u=new URL('/taste-studio',location.origin);u.searchParams.set('selected',[...saved.keys()].join(','));
  try{if(!navigator.clipboard?.writeText)throw Error();await navigator.clipboard.writeText(u.href);get('v29ShareStatus').textContent='Link copied. Anyone with it can view these published menu items, not your account.';}
  catch(_){get('v29ShareStatus').textContent='Copy this link: '+u.href;}
 });
 api(endpoints.topics).then(data=>{chips.replaceChildren();for(const item of data.topics){const b=smallButton(item.name+' · '+item.count,'v29-chip',()=>{topic=item.id;offset=0;chips.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));loadItems();});b.setAttribute('aria-pressed',String(item.id===topic));chips.append(b);}}).catch(()=>{chips.textContent='All published dishes are available in the menu search.';});
 api(endpoints.visit).then(data=>{const facts=get('v29VisitFacts');facts.replaceChildren();facts.append(e('p','v29-visit-location',data.neighborhood));if(data.address)facts.append(e('p',null,'Recorded address: '+data.address));if(data.phone){const p=e('p');p.append(e('span',null,'Café contact: '));const a=e('a',null,data.phone);a.href='tel:'+data.phone.replace(/[^+\d]/g,'');p.append(a);facts.append(p);}if(data.hours)facts.append(e('p',null,'Published hours (verify): '+data.hours));else facts.append(e('p',null,'Opening hours: please confirm directly with the café.'));}).catch(()=>{get('v29VisitFacts').textContent='The latest visiting details are unavailable. Open the Visit page for directions.';});
 refreshShortlist();loadItems();
}
ready(()=>{
 document.documentElement.dataset.v29='taste-studio';
 if(document.body.dataset.page==='taste-studio'){renderStudio();return;}
 if(document.body.dataset.page==='home'){
  homeInvitation();if(!get('v29HomeInvitation')){
   const host=get('app');if(host){const observer=new MutationObserver(()=>{homeInvitation();if(get('v29HomeInvitation'))observer.disconnect();});observer.observe(host,{childList:true});}
  }
 }
 if(document.body.dataset.page==='menu'){
  const anchor=document.querySelector('.v28-menu-browser');if(anchor&&!get('v29MenuInvite')){
   const p=e('aside','v29-menu-invite');p.id='v29MenuInvite';
   p.innerHTML='<div><strong>Not sure what to choose?</strong><p>Build a shareable shortlist before your visit—using real published menu entries.</p></div><a href="/taste-studio">OPEN TASTE STUDIO ↗</a>';
   anchor.prepend(p);
  }
 }
});
})();
