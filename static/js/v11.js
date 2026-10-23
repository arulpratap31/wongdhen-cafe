/* Wongdhen V11 — all 483 curated image placements, image-first navigation.
   Uses existing V10 publication metadata; does not alter reservation/menu data. */
(()=>{'use strict';if(document.documentElement.dataset.v13==='true')return;
const CATS={'':'All photographs',food:'Food',drinks:'Drinks & coffee',desserts:'Bakery & desserts',interiors:'Interiors',ambience:'Café ambience',exterior:'Exterior & terrace',branding:'Branding & promotions'};
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
const esc=(v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const noMotion=()=>matchMedia('(prefers-reduced-motion:reduce)').matches||document.documentElement.classList.contains('v4-motion-off');
const PHOTO_API='/api/v11/photos';
const api=async(params)=>{const url=new URL(PHOTO_API,location.origin);Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!=='')url.searchParams.set(k,String(v))});const res=await fetch(url,{credentials:'same-origin'});if(!res.ok)throw Error('Photography collection could not be loaded ('+res.status+').');return res.json()};
const label=p=>p.archival_only?'Archive image · '+CATS[p.category]:CATS[p.category];
const img=(p,priority=false)=>`<img src="${esc(p.thumb)}" srcset="${esc(p.thumb)} 520w,${esc(p.path)} 1400w" sizes="(max-width:650px) 92vw,(max-width:1050px) 48vw,28vw" loading="${priority?'eager':'lazy'}" ${priority?'fetchpriority="high"':''} decoding="async" width="${p.width}" height="${p.height}" alt="${esc(p.alt)}" style="object-position:${esc(p.focal_point)}"/>`;
const card=(p,i=0)=>`<button type="button" class="v11-tile" data-photo="${esc(p.id)}" aria-label="Open photograph ${esc(p.id)}, ${esc(label(p))}">${img(p,i===0)}<span><b>${esc(p.id)}</b> · ${esc(label(p))}</span></button>`;
const title=(eyebrow,h,sub)=>`<div class="v11-heading"><p class="v11-eyebrow">${eyebrow}</p><h2>${h}</h2><p>${sub}</p></div>`;

// One shared full-resolution photo viewer. On the gallery page, arrows traverse page boundaries.
let currentViewer=null;
function openViewer(records,index,options={}){
 if(!records.length)return;
 if(currentViewer)currentViewer.close();
 let list=records.slice(),i=index,pg=options.page||1,per=options.pageSize||list.length,total=options.total||list.length,fetcher=options.fetcher||null, busy=false;
 const focusBefore=document.activeElement;
 const modal=document.createElement('div');modal.className='v11-lightbox';modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-label','Wongdhen photograph viewer');
 modal.innerHTML='<div class="v11-lightbox-toolbar"><span class="v11-viewer-number" aria-live="polite"></span><a class="v11-image-link" target="_blank" rel="noopener" href="#">VIEW ORIGINAL SIZE ↗</a><button type="button" class="v11-close" aria-label="Close photograph viewer">CLOSE ×</button></div><button class="v11-arrow v11-arrow-left" aria-label="Previous photograph" type="button">←</button><figure><img alt=""/><figcaption></figcaption></figure><button class="v11-arrow v11-arrow-right" aria-label="Next photograph" type="button">→</button>';
 document.body.append(modal);document.body.classList.add('v11-modal-open');
 const image=$('figure img',modal),caption=$('figcaption',modal),number=$('.v11-viewer-number',modal),link=$('.v11-image-link',modal);
 function render(){const x=list[i];if(!x)return;image.src=x.path;image.alt=x.alt||CATS[x.category];caption.textContent=x.id+' · '+label(x);number.textContent='PHOTOGRAPH '+((pg-1)*per+i+1)+' / '+total;link.href=x.path;$('.v11-arrow-left',modal).disabled=(pg===1&&i===0);$('.v11-arrow-right',modal).disabled=((pg-1)*per+i>=total-1)}
 async function shift(direction){if(busy)return;let n=i+direction,p=pg;if(n<0||n>=list.length){if(!fetcher||((pg===1&&direction<0)||((pg-1)*per+i>=total-1&&direction>0)))return;
   p=pg+direction;busy=true;try{const d=await fetcher(p);if(!modal.isConnected||!d.items.length)return;list=d.items;pg=p;n=direction<0?list.length-1:0;total=d.total;}catch(e){caption.textContent=e.message}finally{busy=false}
 }
 i=n;render();}
 const close=()=>{modal.remove();document.body.classList.remove('v11-modal-open');document.removeEventListener('keydown',onKeys);focusBefore?.focus({preventScroll:true});currentViewer=null};
 function onKeys(e){if(e.key==='Escape'){e.preventDefault();close()}else if(e.key==='ArrowLeft'){e.preventDefault();shift(-1)}else if(e.key==='ArrowRight'){e.preventDefault();shift(1)}else if(e.key==='Tab'){const focus=$$('button:not([disabled]),a[href]',modal);const first=focus[0],last=focus.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}}
 $('.v11-close',modal).onclick=close;$('.v11-arrow-left',modal).onclick=()=>shift(-1);$('.v11-arrow-right',modal).onclick=()=>shift(1);
 modal.addEventListener('click',e=>{if(e.target===modal)close()});document.addEventListener('keydown',onKeys);
 let start=null;modal.addEventListener('touchstart',e=>{start=[e.changedTouches[0].clientX,e.changedTouches[0].clientY]},{passive:true});modal.addEventListener('touchend',e=>{if(!start)return;const dx=e.changedTouches[0].clientX-start[0],dy=e.changedTouches[0].clientY-start[1];if(Math.abs(dx)>70&&Math.abs(dx)>Math.abs(dy)*1.5)shift(dx<0?1:-1);start=null},{passive:true});
 currentViewer={close};render();$('.v11-close',modal).focus();}
function bindCards(root,records,opts={}){root.addEventListener('click',e=>{const b=e.target.closest('[data-photo]');if(!b||!root.contains(b))return;const idx=records.findIndex(p=>p.id===b.dataset.photo);if(idx>=0)openViewer(records,idx,opts)})}

function collectionSection(section,heading,sub,classes=''){
 return `<section class="v11-collection ${classes}" data-v11-section="${section}">${title('WONGDHEN · PHOTOGRAPHY EDITION',heading,sub)}<div class="v11-loading" role="status">Loading photographs…</div><div class="v11-grid"></div></section>`;
}
async function mountSingle(section,selector,options={}){
 const host=document.querySelector(selector);if(!host)return;
 try{const d=await api({section,page:1,page_size:options.limit||60});const grid=$('.v11-grid',host),status=$('.v11-loading',host);grid.innerHTML=d.items.map((p,i)=>card(p,i)).join('');if(status)status.textContent=d.total+' photographs · Select any image to explore';bindCards(grid,d.items)}
 catch(e){const s=$('.v11-loading',host);if(s)s.textContent=e.message}
}

async function mountHome(){
 const place=$('.v4-marquee')||$('#app > section');if(!place)return;
 place.insertAdjacentHTML('afterend',`<section class="v11-home-experience" id="v11HomeExperience">
 <div class="v11-home-intro"><p class="v11-eyebrow">01 / THE COMPLETE PHOTOGRAPHIC EXPERIENCE</p><h2>See the café.<br/><em>Feel the moment.</em></h2><p>Forty original photographs across food, coffee, atmosphere and signature details.</p></div>
 <div class="v11-home-hero" id="v11Hero"><div class="v11-home-slides" role="region" aria-label="Featured café photographs"></div><div class="v11-home-slide-ui"><span id="v11HeroStatus" aria-live="polite">01 / 06</span><div><button type="button" data-v11-slide="prev" aria-label="Previous featured photo">←</button><button type="button" data-v11-slide="next" aria-label="Next featured photo">→</button></div></div></div>
 ${collectionSection('home-food','The kitchen <em>in pictures.</em>','Ten food photographs presented as a visual tasting collection.','v11-home-collection')}
 ${collectionSection('home-atmosphere','A space to <em>stay awhile.</em>','Ten photographs of interiors, textures and café ambience.','v11-home-collection')}
 ${collectionSection('home-drinks','Sips & <em>sweet moments.</em>','Eight drinks and dessert photographs to explore.','v11-home-collection')}
 ${collectionSection('home-featured','The final <em>details.</em>','Six more photographs, handpicked for the café experience.','v11-home-collection')}
 <div class="v11-cta"><p>DISCOVER ALL 483 PHOTOGRAPHS ACROSS THE WEBSITE</p><a href="/gallery">EXPLORE 300 GALLERY PHOTOS ↗</a><a href="/photo-book">TURN THE PHOTO BOOK ↗</a><a href="/journal">EXPLORE THE VISUAL JOURNAL ↗</a></div>
 </section>`);
 try{const d=await api({section:'home',page_size:40});const items=d.items;if(items.length!==40)throw Error('This collection currently has '+items.length+' published photos; the expected count is 40.');
 const hero=items.slice(0,6),groups=[['home-food',items.slice(6,16)],['home-atmosphere',items.slice(16,26)],['home-drinks',items.slice(26,34)],['home-featured',items.slice(34,40)]];
 groups.forEach(([section,arr])=>{const host=$(`[data-v11-section="${section}"]`),grid=$('.v11-grid',host);grid.innerHTML=arr.map((p,i)=>card(p,i)).join('');$('.v11-loading',host).textContent=arr.length+' photographs · Click to view full size';bindCards(grid,arr)});
 let current=0,autoplay=null;const box=$('#v11Hero'),slides=$('.v11-home-slides',box),status=$('#v11HeroStatus');
 slides.innerHTML=hero.map((p,i)=>`<button type="button" class="v11-slide ${i===0?'active':''}" data-photo="${p.id}" aria-label="Open featured photograph ${p.id}" aria-hidden="${i!==0}" tabindex="${i===0?'0':'-1'}">${img(p,i===0)}<span>${esc(label(p))} <b>${esc(p.id)}</b></span></button>`).join('');
 bindCards(slides,hero);
 const draw=()=>{$$('.v11-slide',box).forEach((el,i)=>{el.classList.toggle('active',i===current);el.setAttribute('aria-hidden',String(i!==current));el.tabIndex=i===current?0:-1});status.textContent=String(current+1).padStart(2,'0')+' / 06'};
 const turn=step=>{current=(current+step+6)%6;draw()};
 box.addEventListener('click',e=>{const b=e.target.closest('[data-v11-slide]');if(b)turn(b.dataset.v11Slide==='next'?1:-1)});
 const start=()=>{if(autoplay||noMotion()||document.hidden)return;autoplay=setInterval(()=>{if(!currentViewer&&document.visibilityState==='visible')turn(1)},6200)};
 const stop=()=>{if(autoplay){clearInterval(autoplay);autoplay=null}};
 box.addEventListener('mouseenter',stop);box.addEventListener('mouseleave',start);box.addEventListener('focusin',stop);box.addEventListener('focusout',e=>{if(!box.contains(e.relatedTarget))start()});document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
 if('IntersectionObserver' in window){const obs=new IntersectionObserver(es=>es.forEach(e=>e.isIntersecting?start():stop()),{threshold:.2});obs.observe(box)}else start();
 }catch(e){const hero=$('#v11Hero');if(hero)hero.textContent=e.message}
}

async function mountEditorial(section,heading,description){const app=$('#app');if(!app)return;const id='v11'+section[0].toUpperCase()+section.slice(1);
 app.insertAdjacentHTML('beforeend',`<div id="${id}">${collectionSection(section,heading,description)}</div>`);
 await mountSingle(section,'#'+id+' [data-v11-section]');
}
function mountMenu(){
 const app=$('#app');if(!app)return;
 const doIt=()=>{if($('#v11MenuCollection'))return true;const anchor=$('.v6-menu-list')||$('.menu-page');if(!anchor)return false;
 const container=document.createElement('div');container.id='v11MenuCollection';container.innerHTML=`${collectionSection('menu','Fifty visual <em>flavours.</em>','Fifty genuine Wongdhen food, drink and dessert photographs. These are category inspiration images, not verified photographs of specific named menu items.')}`;
 anchor.insertAdjacentElement('afterend',container);mountSingle('menu','#v11MenuCollection [data-v11-section]',{limit:50});return true};
 if(doIt())return;const observer=new MutationObserver(()=>{if(doIt())observer.disconnect()});observer.observe(app,{subtree:true,childList:true});setTimeout(()=>observer.disconnect(),20000);
}

async function browseGallery(){const app=$('#app');if(!app)return;
 let category='',query='',page=1,serial=0,records=[],last=null;
 const search=new URLSearchParams(location.search);category=Object.hasOwn(CATS,search.get('category'))?search.get('category'):'';page=Math.max(1,Math.min(10,Number(search.get('page'))||1));
 app.innerHTML=`<section class="v11-gallery-intro"><p class="v11-eyebrow">WONGDHEN CAFÉ / THE PHOTOGRAPHY ARCHIVE</p><h1>300 stories,<br/><em>one café.</em></h1><p>Explore 300 original photographs in a browsable archive. Every image opens at high resolution. The other 183 photographs appear on our other pages.</p><div class="v11-gallery-links"><a href="/photo-book">INTERACTIVE PHOTO BOOK ↗</a><a href="/journal">VISUAL JOURNAL ↗</a><a href="/menu">FOOD & DRINKS ↗</a></div></section>
 <section class="v11-gallery-shell" id="v11GalleryShell"><div class="v11-controls"><div class="v11-filter-row" role="group" aria-label="Filter gallery photographs">${Object.entries(CATS).map(([key,name])=>`<button type="button" data-v11-category="${key}" aria-pressed="false">${name}</button>`).join('')}</div><label class="v11-search-label">SEARCH BY PHOTO ID OR CATEGORY CAPTION <input type="search" id="v11PhotoSearch" placeholder="e.g. P0214, food, interior" maxlength="100"/></label></div><p id="v11GalleryStatus" role="status" aria-live="polite">Loading 300 photographs…</p><div class="v11-grid v11-gallery-grid" id="v11GalleryGrid" aria-busy="true"></div><nav class="v11-pagination" id="v11Pagination" aria-label="Gallery photo pages"></nav></section>`;
 const grid=$('#v11GalleryGrid'),status=$('#v11GalleryStatus'),pagination=$('#v11Pagination');
 const params=pg=>({section:'gallery',page:pg,page_size:30,category,q:query});
 const setURL=()=>{const u=new URL(location.href);if(page>1)u.searchParams.set('page',page);else u.searchParams.delete('page');if(category)u.searchParams.set('category',category);else u.searchParams.delete('category');if(query)u.searchParams.set('q',query);else u.searchParams.delete('q');history.pushState({v11:true},'',u)};
 function controls(d){const n=d.pages;pagination.innerHTML=`<button type="button" data-page="${page-1}" ${page===1?'disabled':''} aria-label="Previous gallery page">← PREVIOUS</button><span class="v11-page-buttons">${Array.from({length:n},(_,i)=>`<button type="button" data-page="${i+1}" ${i+1===page?'aria-current="page"':''} aria-label="Page ${i+1}">${i+1}</button>`).join('')}</span><button type="button" data-page="${page+1}" ${page===n?'disabled':''} aria-label="Next gallery page">NEXT →</button>`;
 $$('.v11-filter-row button',app).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v11Category===category)))}
 async function load(target){const req=++serial;grid.setAttribute('aria-busy','true');status.textContent='Loading gallery page '+target+'…';
 try{const d=await api(params(target));if(req!==serial)return;last=d;page=d.page;records=d.items;grid.innerHTML=records.map((p,i)=>card(p,i)).join('')||'<p>No photographs match this selection.</p>';status.textContent=d.total+' photographs '+(category?'in '+CATS[category]:'in this collection')+' · page '+page+' of '+d.pages;controls(d)}
 catch(e){if(req===serial){status.textContent=e.message;grid.innerHTML='<p>Please refresh to retry loading the gallery.</p>'}}
 finally{if(req===serial)grid.setAttribute('aria-busy','false')}}
 grid.addEventListener('click',e=>{const b=e.target.closest('[data-photo]');if(!b||!last)return;const i=records.findIndex(p=>p.id===b.dataset.photo);if(i<0)return;const f=(pg)=>api(params(pg));openViewer(records,i,{page,pageSize:30,total:last.total,fetcher:f})});
 pagination.addEventListener('click',e=>{const b=e.target.closest('[data-page]');if(!b||b.disabled)return;const to=Number(b.dataset.page);if(to<1||to>(last?.pages||1))return;page=to;setURL();load(to);$('#v11GalleryShell')?.scrollIntoView({behavior:noMotion()?'instant':'smooth'})});
 $('.v11-filter-row',app).addEventListener('click',e=>{const b=e.target.closest('[data-v11-category]');if(!b)return;category=b.dataset.v11Category;page=1;setURL();load(1)});
 let timer;$('#v11PhotoSearch').addEventListener('input',e=>{clearTimeout(timer);timer=setTimeout(()=>{query=e.target.value.trim();page=1;setURL();load(1)},280)});
 window.addEventListener('popstate',()=>{const p=new URLSearchParams(location.search);category=Object.hasOwn(CATS,p.get('category'))?p.get('category'):'';query=p.get('q')||'';$('#v11PhotoSearch').value=query;load(Math.max(1,Number(p.get('page'))||1))});
 query=search.get('q')||'';$('#v11PhotoSearch').value=query;await load(page);
}

async function photoBook(){const app=$('#app');if(!app)return;
 app.innerHTML=`<section class="v11-book-page-root"><div class="v11-book-header">${title('WONGDHEN · PHOTO BOOK / 24 PHOTOGRAPHS','Turn the <em>pages.</em>','Twenty-four original photographs in a curated café photo book. Use the arrows to turn the page, or open any image in full size.')}</div><div class="v11-book-stage" role="region" aria-label="Interactive 24-image photo book"><div class="v11-book-paper"><button type="button" class="v11-book-image" id="v11BookImage" aria-label="Enlarge current photograph"><img id="v11BookMain" alt=""/><span id="v11BookCaption"></span></button><div class="v11-book-preview"><img id="v11BookNextImage" alt="" aria-hidden="true"/><span>NEXT MOMENT →</span></div></div></div><div class="v11-book-controls"><button id="v11BookPrev">← PREVIOUS</button><span id="v11BookCount" aria-live="polite">01 / 24</span><button id="v11BookNext">NEXT →</button></div><p class="v11-photo-note">Turn with arrow keys or swipe left and right. Reduced-motion settings disable page-flip animation.</p><a class="v11-back-photos" href="/gallery">VIEW 300 PHOTOGRAPHS IN THE MAIN GALLERY ↗</a></section>`;
 try{const d=await api({section:'photo-book',page_size:24}),p=d.items;let at=0,moving=false;
 const main=$('#v11BookMain'),next=$('#v11BookNextImage'),book=$('.v11-book-paper'),caption=$('#v11BookCaption'),count=$('#v11BookCount');
 function draw(){const x=p[at],n=p[at+1];main.src=x.path;main.alt=x.alt;caption.textContent=x.id+' · '+label(x);if(n){next.src=n.thumb;next.alt=''}else next.removeAttribute('src');count.textContent=String(at+1).padStart(2,'0')+' / '+d.total;$('#v11BookPrev').disabled=at===0;$('#v11BookNext').disabled=at===p.length-1}
 async function turn(step){if(moving||at+step<0||at+step>=p.length)return;moving=true;if(!noMotion()){book.classList.add('turning');await new Promise(r=>setTimeout(r,240))}at+=step;draw();book.classList.remove('turning');moving=false}
 $('#v11BookPrev').onclick=()=>turn(-1);$('#v11BookNext').onclick=()=>turn(1);$('#v11BookImage').onclick=()=>openViewer(p,at);
 document.addEventListener('keydown',e=>{if(currentViewer||e.target.closest('input,textarea'))return;if(e.key==='ArrowRight')turn(1);if(e.key==='ArrowLeft')turn(-1)});
 let start=null;book.addEventListener('touchstart',e=>start=[e.changedTouches[0].clientX,e.changedTouches[0].clientY],{passive:true});book.addEventListener('touchend',e=>{if(!start)return;const dx=e.changedTouches[0].clientX-start[0],dy=e.changedTouches[0].clientY-start[1];if(Math.abs(dx)>65&&Math.abs(dx)>Math.abs(dy)*1.5)turn(dx<0?1:-1);start=null},{passive:true});
 draw();}catch(e){$('.v11-book-header',app).insertAdjacentText('beforeend',e.message)}
}
async function visualJournal(){const app=$('#app');if(!app)return;app.innerHTML=`<div class="v11-journal-root">${collectionSection('journal','The Wongdhen <em>visual journal.</em>','Twenty-four editorial photographs from the café collection. Archival graphics, where present, are not current promotional offers.')}<a class="v11-back-photos" href="/gallery">RETURN TO THE MAIN PHOTO GALLERY ↗</a></div>`;await mountSingle('journal','.v11-journal-root [data-v11-section]',{limit:24})}
window.initV10Gallery=browseGallery;
window.initV11Collection=(name)=>name==='photo-book'?photoBook():visualJournal();
document.addEventListener('DOMContentLoaded',()=>{
 const name=document.body.dataset.page;
 if(name==='home')mountHome();
 if(name==='about')mountEditorial('about','Made of <em>small moments.</em>','Twenty original photographs featuring Wongdhen’s interiors and atmosphere.');
 if(name==='visit')mountEditorial('visit','Find your <em>favourite corner.</em>','Twenty-five photographs of the café environment; images do not represent reservable tables.');
 if(name==='menu')mountMenu();
});
})();
