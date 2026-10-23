/* Wongdhen V10 — progressive, keyboard-accessible photography experiences.
   Does not intercept booking, ordering, menu verification or existing gallery viewer. */
(()=>{'use strict';
const path='/static/v10/';
const $=(s,root=document)=>root.querySelector(s), $$=(s,root=document)=>[...root.querySelectorAll(s)];
const clean=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const less=()=>matchMedia('(prefers-reduced-motion:reduce)').matches||document.documentElement.classList.contains('v4-motion-off');
const photo=(id,label,cls='')=>`<img class="${cls}" src="${path}thumb/${id}.webp" srcset="${path}thumb/${id}.webp 520w, ${path}large/${id}.webp 1400w" sizes="(max-width:720px) 90vw, 48vw" alt="${clean(label)}" loading="lazy" decoding="async" width="720" height="760">`;
const imgLink=(id,label,href,title,cls='')=>`<a class="v10-editorial-card ${cls}" href="${href}">${photo(id,label)}<span>${title} <b aria-hidden="true">↗</b></span></a>`;
const localURL=()=>new URL(location.href);
const request=async(url,opts={})=>{const response=await fetch(url,{credentials:'same-origin',...opts});if(!response.ok)throw new Error(`Photo service unavailable (${response.status})`);return response.json()};
const catName={'':'All Photos',food:'Food',drinks:'Drinks & Coffee',desserts:'Bakery & Desserts',interiors:'Interiors',ambience:'Café Ambience',exterior:'Exterior & Terrace',branding:'Branding & Promotions'};
const coverData=[['P0256','Pizza presentation','/gallery?category=food','A TASTE OF WONGDHEN'],['P0194','Iced café beverage','/gallery?category=drinks','A MOMENT TO SIP'],['P0382','Layered café dessert','/gallery?category=desserts','THE SWEET EDIT'],['P0270','Wongdhen café entrance','/gallery?category=exterior','COME ON IN']];
function pages(){const root=$('#app');if(!root||document.documentElement.dataset.v13==='true')return;const name=document.body.dataset.page;
 if(name==='home'){
  const guide=`<section class="v10-editorial" aria-label="Wongdhen in photographs"><div class="v10-editorial-heading"><p>THE CAFÉ, IN FOUR ACTS / 2026</p><h2>The flavour of <em>being here.</em></h2><span>Discover the café through its real food, coffee, desserts and entrance.</span></div><div class="v10-editorial-grid">${coverData.map(([id,label,href,title],i)=>imgLink(id,'Wongdhen Café — '+label,href,`${String(i+1).padStart(2,'0')} / ${title}`,i===0?'large':'' )).join('')}</div><a class="v10-archive-link" href="/gallery">EXPLORE THE COMPLETE PHOTO JOURNAL <span aria-hidden="true">↗</span></a></section>`;
  ($('.v4-coffee-editorial')||$('.v4-introduction'))?.insertAdjacentHTML('afterend',guide);
  const story=`<section class="v10-story-band" aria-label="A glimpse of the café"><div>${photo('P0214','Warm Wongdhen Café interior with glowing café sign')}</div><div class="v10-story-copy"><span>LOOK INSIDE / THE WONGDHEN EXPERIENCE</span><h2>Spaces that <em>stay with you.</em></h2><p>A gallery of lived-in corners, warm pendants and tables waiting for conversation.</p><a href="/gallery?category=interiors">EXPLORE THE SPACES ↗</a></div></section>`;
  ($('.v4-introduction'))?.insertAdjacentHTML('afterend',story);
 }
 if(name==='about'){
  root.insertAdjacentHTML('beforeend',`<section class="v10-about-gallery"><span class="v10-eyebrow">A PHOTOGRAPHIC STORY</span><h2>Textures, rituals, <em>little details.</em></h2><div class="v10-about-grid">${[['P0244','Wongdhen name on the wall','A SIGNATURE'],['P0235','Bakery display with pastries and cakes','THE BAKERY'],['P0141','Café latte in a cup','COFFEE HOURS'],['P0273','Warm café furniture and interior','THE SPACE']].map(([id,alt,label])=>`<figure>${photo(id,alt)}<figcaption>${label}</figcaption></figure>`).join('')}</div></section>`);
 }
 if(name==='visit'){
  root.insertAdjacentHTML('beforeend',`<section class="v10-visit-photos"><div class="v10-visit-intro"><span>ARRIVE · TAKE A SEAT · STAY A WHILE</span><h2>Find your <em>favourite corner.</em></h2><p>Real views of the café exterior and seating. Photographs do not indicate table availability.</p></div><div class="v10-visit-grid">${imgLink('P0270','Wongdhen Café entrance','/gallery?category=exterior','THE ENTRANCE')}${imgLink('P0205','Balcony seating with a view','/gallery?category=exterior','THE TERRACE')}${imgLink('P0354','Light-toned indoor seating','/gallery?category=interiors','INDOOR SEATING')}</div></section>`);
 }
 if(name==='menu'){
  const catalog=`<section class="v10-menu-editorial" aria-label="Visual food inspiration"><div><span>VISUAL TASTING NOTES / ORIGINAL PHOTOGRAPHS</span><h2>See what’s <em>cooking.</em></h2><p>Browse atmospheric food photographs by category. Individual menu items show a photograph only when that exact dish has been verified.</p></div><div>${[['P0256','Food','food'],['P0184','Coffee','drinks'],['P0221','Desserts','desserts']].map(([id,t,cat])=>`<a href="/gallery?category=${cat}">${photo(id,'Wongdhen — '+t+' photograph')}<span>${t} ↗</span></a>`).join('')}</div></section>`;
  // Menu is loaded asynchronously by V6; mount once without interfering with its controls.
  const observer=new MutationObserver(()=>{const list=$('.v6-menu-list');if(list&&!$('#v10MenuCovers')){list.insertAdjacentHTML('beforebegin',`<div id="v10MenuCovers">${catalog}</div>`);observer.disconnect()}});
  if($('.v6-menu-list'))$('.v6-menu-list').insertAdjacentHTML('beforebegin',`<div id="v10MenuCovers">${catalog}</div>`);
  else{observer.observe(root,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),15000)}
 }
 if(name==='reels'){
  const stories=`<section class="v10-stories" aria-label="Photographic food stories"><span class="v10-eyebrow">STILL PHOTOGRAPHY · NOT VIDEOS</span><h2>The visual <em>journal.</em></h2><p>These are photographs from the café, not moving video reels.</p><div class="v10-stories-grid">${[['P0256','FOOD'],['P0194','DRINKS'],['P0382','DESSERTS']].map(([id,label])=>`<a href="/gallery?category=${label==='FOOD'?'food':label==='DRINKS'?'drinks':'desserts'}">${photo(id,'Café '+label.toLowerCase()+' photography')}<span>${label} ↗</span></a>`).join('')}</div></section>`;
  const ob=new MutationObserver(()=>{const section=$('#v7ReelRoot');if(section&&!$('#v10PhotoStories')){const slot=document.createElement('div');slot.id='v10PhotoStories';slot.innerHTML=stories;root.appendChild(slot);ob.disconnect()}});
  if($('#v7ReelRoot')){const slot=document.createElement('div');slot.id='v10PhotoStories';slot.innerHTML=stories;root.appendChild(slot)}else{ob.observe(root,{childList:true,subtree:true});setTimeout(()=>ob.disconnect(),15000)}
 }
}

// Catalogue is paginated server-side. URL state is shareable and back-button aware.
window.initV10Gallery=async function(){
 const app=$('#app');if(!app)return;
 let currentCategory='',page=1,query='',items=[],count=0,loading=false,serial=0;
 const params=new URLSearchParams(location.search);currentCategory=catName.hasOwnProperty(params.get('category'))?params.get('category'):'';
 page=Math.max(1,Math.min(100000,Number(params.get('page'))||1));
 app.innerHTML=`<section class="v10-gallery-hero"><span>THE WONGDHEN PHOTOGRAPHY ARCHIVE · V10</span><h1>Moments worth <em>keeping.</em></h1><p>Food, coffee, corners and everyday life — an editorial photo book of Wongdhen Café.</p><a href="#photoArchive">EXPLORE PHOTOGRAPHS ↓</a></section><section class="v10-gallery" id="photoArchive"><div class="v10-gallery-intro"><span>THE PHOTO JOURNAL / 483 ORIGINAL IMAGES</span><h2>A gallery to <em>get lost in.</em></h2><p>Use the categories to explore the complete collection. Older promotional graphics are archival, not current offers.</p></div><div id="v10GalleryControls" class="v10-gallery-controls"><div class="v10-cat-list" role="group" aria-label="Photo categories">${Object.entries(catName).map(([id,name])=>`<button type="button" data-category="${id}" aria-pressed="false">${name}</button>`).join('')}</div><div class="v10-view-actions"><label class="v10-search">SEARCH PHOTOS<input id="v10Search" type="search" placeholder="Photo ID or subject" maxlength="100"></label><button id="v10BookOpen" type="button">OPEN PHOTO BOOK ↗</button></div></div><div class="v10-gallery-status" id="v10GalleryStatus" role="status" aria-live="polite">Loading photographs…</div><div class="v10-masonry" id="v10GalleryGrid"></div><nav class="v10-page-controls" aria-label="Photo archive pages"><button id="v10Previous" type="button">← PREVIOUS</button><span id="v10Pager"></span><button id="v10Next" type="button">NEXT →</button></nav><aside class="v10-legacy" id="v10Legacy" hidden></aside></section>`;
 const grid=$('#v10GalleryGrid'),status=$('#v10GalleryStatus'),prev=$('#v10Previous'),next=$('#v10Next');
 const updateURL=()=>{const url=localURL();if(currentCategory)url.searchParams.set('category',currentCategory);else url.searchParams.delete('category');if(page>1)url.searchParams.set('page',String(page));else url.searchParams.delete('page');history.pushState({v10:true},'',url)};
 async function fetchPage(target,replace=true){
  const req=++serial;loading=true;status.textContent='Loading photographs…';grid.setAttribute('aria-busy','true');
  const qs=new URLSearchParams({page:String(target),page_size:'24'});if(currentCategory)qs.set('category',currentCategory);if(query)qs.set('q',query);
  try{
   const result=await request('/api/v10/photos?'+qs);if(req!==serial)return;
   items=result.items;page=result.page;count=result.total;
   status.textContent=`${count} photographs ${currentCategory?'in '+catName[currentCategory]:'in the archive'} · page ${page} of ${Math.max(1,Math.ceil(count/24))}`;
   grid.innerHTML=items.length?items.map((x,i)=>`<button type="button" class="v10-gallery-tile" data-index="${i}" aria-label="View photo ${x.id}: ${clean(x.caption)}"><img src="${x.thumb}" alt="${clean(x.alt)}" width="${x.width}" height="${x.height}" loading="lazy" decoding="async" style="object-position:${x.focal_point};"><span><strong>${x.id}</strong> / ${clean(x.caption)}${x.archival_only?' · Archival graphic':''}</span></button>`).join(''):'<p>No photographs match this filter.</p>';
   prev.disabled=page<=1;next.disabled=!result.has_more;$('#v10Pager').textContent=`${page} / ${Math.max(1,Math.ceil(count/24))}`;
   $$('[data-category]',app).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.category===currentCategory)));
   $('#v10BookOpen').disabled=!items.length;
   if(page===1&&!currentCategory&&!query)loadEarlierPhotos();else $('#v10Legacy').hidden=true;
  }catch(err){if(req===serial){status.textContent=err.message;grid.innerHTML='<p>Photographs could not be loaded. Retry with a category.</p>'}}
  finally{if(req===serial){loading=false;grid.setAttribute('aria-busy','false')}}
 }
 async function loadEarlierPhotos(){
  const zone=$('#v10Legacy');try{const r=await request('/api/gallery');if(!r.images?.length)return;
  zone.hidden=false;zone.innerHTML=`<h3>From the earlier Wongdhen gallery</h3><p>Existing photographs and published owner uploads remain accessible.</p><div class="v10-legacy-grid">${r.images.map((p,i)=>`<button type="button" data-legacy="${i}"><img src="${clean(p.path)}" alt="${clean(p.caption)}" loading="lazy"><span>${clean(p.caption)}</span></button>`).join('')}</div>`;
  zone.querySelectorAll('[data-legacy]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.legacy),p=r.images[i];if(typeof openLightbox==='function')openLightbox(p.path,p.caption,r.images,i)})
  }catch{zone.hidden=true}
 }
 grid.addEventListener('click',e=>{const btn=e.target.closest('[data-index]');if(!btn)return;const i=Number(btn.dataset.index),x=items[i];if(typeof openLightbox==='function')openLightbox(x.path,x.caption,items.map(p=>({path:p.path,caption:p.caption})),i)});
 $('#v10GalleryControls').addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(!b||loading)return;currentCategory=b.dataset.category;page=1;updateURL();fetchPage(1)});
 prev.onclick=()=>{if(!loading&&page>1){updatePage(page-1)}};
 next.onclick=()=>{if(!loading&&page<Math.ceil(count/24)){updatePage(page+1)}};
 function updatePage(n){page=n;updateURL();fetchPage(n);$('#photoArchive').scrollIntoView({behavior:less()?'instant':'smooth'})}
 let timer;$('#v10Search').addEventListener('input',e=>{clearTimeout(timer);query=e.target.value.trim();timer=setTimeout(()=>{page=1;updateURL();fetchPage(1)},270)});
 window.addEventListener('popstate',()=>{const p=new URLSearchParams(location.search);const nextCat=p.get('category')||'';currentCategory=Object.hasOwn(catName,nextCat)?nextCat:'';page=Math.max(1,Number(p.get('page'))||1);fetchPage(page)});
 $('#v10BookOpen').onclick=()=>bookOpen(0);
 let book=null,bookKey=null;
 function bookOpen(index){if(!items.length)return;let i=index,locked=false,el=document.createElement('div'),lastFocus=document.activeElement,disposed=false,startedPage=page;
  el.className='v10-book-backdrop';el.setAttribute('role','dialog');el.setAttribute('aria-modal','true');el.setAttribute('aria-label','Café photography book');
  el.innerHTML=`<div class="v10-book"><div class="v10-book-top"><span>WONGDHEN · THE PHOTOGRAPHIC EDITION</span><button class="v10-book-close" aria-label="Close photo book" type="button">CLOSE ×</button></div><div class="v10-book-stage"><div class="v10-book-page v10-book-left"><img id="v10BookPrimary" alt=""><p id="v10BookCaption"></p></div><div class="v10-book-page v10-book-right"><img id="v10BookSecondary" alt=""><p id="v10BookSecondaryCaption"></p></div><div class="v10-turn-leaf" aria-hidden="true"><img id="v10LeafImage" alt=""></div></div><div class="v10-book-bar"><button id="v10BookPrev" type="button">← PREVIOUS</button><span id="v10BookCounter" aria-live="polite"></span><button id="v10BookZoom" type="button">VIEW LARGE ↗</button><button id="v10BookNext" type="button">NEXT →</button></div></div>`;
  document.body.appendChild(el);document.body.classList.add('v10-book-open');el.querySelector('.v10-book-close').focus();
  const first=$('#v10BookPrimary',el),second=$('#v10BookSecondary',el),leaf=$('.v10-turn-leaf',el);
  function render(){const p=items[i],after=items[i+1]||null;if(!p)return;
   first.src=p.path;first.alt=p.alt;first.style.objectPosition=p.focal_point;$('#v10BookCaption',el).textContent=`${p.id} · ${p.caption}`;
   if(after){second.src=after.path;second.alt=after.alt;second.style.objectPosition=after.focal_point;$('#v10BookSecondaryCaption',el).textContent=`${after.id} · ${after.caption}`}
   else{second.removeAttribute('src');second.alt='';$('#v10BookSecondaryCaption',el).textContent='CONTINUE TURNING →'}
   $('#v10BookCounter',el).textContent=`PHOTO ${(page-1)*24+i+1} / ${count}`;
   $('#v10BookPrev',el).disabled=page===1&&i===0;$('#v10BookNext',el).disabled=page>=Math.ceil(count/24)&&i>=items.length-1;
   if(items[i+2]){const preload=new Image();preload.src=items[i+2].path}
  }
  const hide=()=>{if(disposed)return;disposed=true;el.remove();document.body.classList.remove('v10-book-open');document.removeEventListener('keydown',bookKey);if(page!==startedPage)fetchPage(page);lastFocus?.focus({preventScroll:true})};
  async function move(step){if(disposed||locked)return;locked=true;const nextIndex=i+step;
   if(nextIndex>=items.length||nextIndex<0){const target=page+(step>0?1:-1);
    const q=new URLSearchParams({page:String(target),page_size:'24'});if(currentCategory)q.set('category',currentCategory);if(query)q.set('q',query);
    try{const result=await request('/api/v10/photos?'+q);if(disposed)return;if(result.items.length){page=target;items=result.items;count=result.total;i=step>0?0:items.length-1;updateURL();render()}}
    catch(err){$('#v10BookCounter',el).textContent=err.message}
    locked=false;return;
   }
   if(!less()){
    const old=items[i];$('#v10LeafImage',el).src=old.path;leaf.classList.remove('v10-is-flipping');void leaf.offsetWidth;leaf.classList.add('v10-is-flipping');
    await new Promise(resolve=>setTimeout(resolve,610));if(disposed)return;leaf.classList.remove('v10-is-flipping');
   }
   i=nextIndex;render();locked=false;
  }
  $('#v10BookPrev',el).onclick=()=>move(-1);$('#v10BookNext',el).onclick=()=>move(1);$('.v10-book-close',el).onclick=hide;
  $('#v10BookZoom',el).onclick=()=>{const p=items[i];hide();if(typeof openLightbox==='function')openLightbox(p.path,p.caption,items.map(x=>({path:x.path,caption:x.caption})),i)};
  el.addEventListener('click',e=>{if(e.target===el)hide()});
  bookKey=e=>{if(disposed)return;if(e.key==='Escape'){e.preventDefault();hide()}else if(e.key==='ArrowRight'){e.preventDefault();move(1)}else if(e.key==='ArrowLeft'){e.preventDefault();move(-1)}else if(e.key==='Tab'){
   const focusable=$$('button:not([disabled])',el),start=focusable[0],end=focusable.at(-1);if(e.shiftKey&&document.activeElement===start){e.preventDefault();end.focus()}else if(!e.shiftKey&&document.activeElement===end){e.preventDefault();start.focus()}
  }};document.addEventListener('keydown',bookKey);
  let touchStart=null;el.addEventListener('touchstart',e=>touchStart=[e.changedTouches[0].clientX,e.changedTouches[0].clientY],{passive:true});el.addEventListener('touchend',e=>{if(!touchStart)return;const dx=e.changedTouches[0].clientX-touchStart[0],dy=e.changedTouches[0].clientY-touchStart[1];if(Math.abs(dx)>65&&Math.abs(dx)>1.5*Math.abs(dy))move(dx<0?1:-1);touchStart=null},{passive:true});render();
 }
 await fetchPage(page);
};

// Owner/editor administrative catalog controls; keep existing secure login and media upload panel.
window.showV10MediaCatalog=async function(){
 const root=$('#adminTab');if(!root)return;let page=1,category='';
 root.innerHTML=`<h2>V10 PHOTO CATALOG</h2><p>Curate imported photos without changing original files or verified menu item photos. The selected cover photos and category archive remain separate from existing uploads.</p><label>FILTER <select id="v10AdminCat"><option value="">All</option>${Object.entries(catName).filter(([k])=>k).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><p id="v10AdminStatus" role="status" aria-live="polite"></p><div id="v10AdminGrid" class="v10-admin-grid"></div><div class="v10-admin-nav"><button id="v10AdminPrev">←</button><span id="v10AdminPage"></span><button id="v10AdminNext">→</button></div>`;
 async function load(){const status=$('#v10AdminStatus');status.textContent='Loading…';try{
  const qs=new URLSearchParams({page:String(page),page_size:'16'});if(category)qs.set('category',category);
  const d=await adminFetch('/api/v10/admin/photos?'+qs);status.textContent=`${d.total} catalog entries`;
  $('#v10AdminGrid').innerHTML=d.items.map(x=>`<article class="v10-admin-card" data-id="${x.id}"><img src="${x.thumb}" alt="${clean(x.alt)}" loading="lazy" title="Click the photo to reposition its focal point" style="cursor:crosshair;object-fit:cover;object-position:${x.focal_point}"><div><strong>${x.id} · ${x.category}</strong><label>CAPTION<input name="caption" value="${clean(x.caption)}" maxlength="240"></label><label>ALT TEXT<input name="alt_text" value="${clean(x.alt)}" maxlength="280"></label><label>FOCAL POINT (X% Y%) — CLICK PREVIEW TO SELECT<input name="focal_point" value="${x.focal_point}" maxlength="24"></label><label>ORDER<input name="display_order" type="number" min="0" max="999999" value="${x.display_order}"></label><label><input name="published" type="checkbox" ${x.published?'checked':''}> PUBLIC</label><label><input name="featured" type="checkbox" ${x.featured?'checked':''}> FEATURED</label><button class="v10-save" type="button">SAVE PHOTO</button><span class="v10-card-message" role="status"></span></div></article>`).join('');
  $('#v10AdminPage').textContent=`${page} / ${Math.max(1,Math.ceil(d.total/16))}`;$('#v10AdminPrev').disabled=page===1;$('#v10AdminNext').disabled=!d.has_more;
 }catch(e){status.textContent=e.message}}
 root.addEventListener('input',e=>{if(!e.target.matches('input[name="focal_point"]'))return;
  const card=e.target.closest('.v10-admin-card');const img=card?.querySelector('img');
  if(img&&/^((100|[0-9]{1,2})%) ((100|[0-9]{1,2})%)$/.test(e.target.value))img.style.objectPosition=e.target.value;
 });
 root.addEventListener('click',async e=>{
  const preview=e.target.closest('.v10-admin-card > img');
  if(preview){
   const rect=preview.getBoundingClientRect(),card=preview.closest('.v10-admin-card');
   const clamp=n=>Math.max(0,Math.min(100,Math.round(n)));
   const pos=`${clamp(100*(e.clientX-rect.left)/rect.width)}% ${clamp(100*(e.clientY-rect.top)/rect.height)}%`;
   card.querySelector('input[name="focal_point"]').value=pos;
   preview.style.objectPosition=pos;
   card.querySelector('.v10-card-message').textContent='Preview updated. Select SAVE PHOTO to publish.';
   return;
  }
  const btn=e.target.closest('.v10-save');if(!btn)return;
  const card=btn.closest('[data-id]'),val=n=>card.querySelector(`[name="${n}"]`),m=$('.v10-card-message',card);btn.disabled=true;m.textContent='Saving…';
  try{const payload={caption:val('caption').value,alt_text:val('alt_text').value,focal_point:val('focal_point').value,display_order:Number(val('display_order').value),published:val('published').checked,featured:val('featured').checked};
   await adminFetch('/api/v10/admin/photos/'+card.dataset.id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});m.textContent='Saved';}
  catch(e){m.textContent=e.message}finally{btn.disabled=false}
 });
 $('#v10AdminCat').onchange=e=>{category=e.target.value;page=1;load()};$('#v10AdminPrev').onclick=()=>{page=Math.max(1,page-1);load()};$('#v10AdminNext').onclick=()=>{page++;load()};await load();
};
document.addEventListener('DOMContentLoaded',pages);
})();
