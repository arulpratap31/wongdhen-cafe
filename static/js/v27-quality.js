/* V27: progressive UI consolidation. No changes to bookings, account identity, or prices. */
(()=>{'use strict';
const ready=cb=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',cb,{once:true}):cb();
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
ready(()=>{
 const root=document.documentElement,body=document.body;
 const path=(body.dataset.page ? (body.dataset.page==='home'?'/':'/'+body.dataset.page) : location.pathname).replace(/\/$/,'')||'/';
 // Consistent wayfinding: mark current link throughout primary, overlay and quick nav.
 document.querySelectorAll('nav a[href], .header a[href]').forEach(a=>{
   const target=a.getAttribute('href');if(!target||!target.startsWith('/'))return;
   const normalized=target.split('?')[0].replace(/\/$/,'')||'/';
   if(normalized===path){a.setAttribute('aria-current','page');a.classList.add('v27-current');}
 });
 // Keep the original navigation destinations but make 20+ links understandable.
 const expanded=document.querySelector('#navOverlay .v4-nav-links');
 if(expanded){
   const headings={'/':'THE ESSENTIALS','/photo-book':'PHOTO STORIES','/discover':'MORE TO EXPLORE'};
   expanded.querySelectorAll('a[href]').forEach(a=>{
     const text=headings[a.getAttribute('href')];if(!text)return;
     const label=document.createElement('p');label.className='v27-nav-category';label.textContent=text;
     label.setAttribute('aria-hidden','true');a.before(label);
   });
 }
 const navButton=document.getElementById('navToggle');
 const navOverlay=document.getElementById('navOverlay');
 if(navButton&&navOverlay){
   // Do not duplicate the existing nav open/close logic; complement keyboard access.
   document.addEventListener('keydown',e=>{
     if(navButton.getAttribute('aria-expanded')!=='true')return;
     if(e.key==='Escape'){e.preventDefault();navButton.click();navButton.focus();}
     if(e.key==='Tab'){
       const focusable=[navButton,...navOverlay.querySelectorAll('a[href],button:not([disabled])')]
         .filter(x=>x.getClientRects().length&&getComputedStyle(x).visibility!=='hidden');
       if(!focusable.length)return;
       if(e.shiftKey&&document.activeElement===focusable[0]){e.preventDefault();focusable[focusable.length-1].focus();}
       else if(!e.shiftKey&&document.activeElement===focusable[focusable.length-1]){e.preventDefault();focusable[0].focus();}
     }
   });
 }
 // Small non-obtrusive reading position bar, disabled for reduced-motion visitors.
 const bar=document.createElement('div');bar.className='v27-reading-progress';bar.setAttribute('aria-hidden','true');
 bar.innerHTML='<span></span>';document.body.appendChild(bar);
 let scheduled=false;
 const onScroll=()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{
    scheduled=false;const max=Math.max(1,document.documentElement.scrollHeight-innerHeight);
    bar.firstElementChild.style.transform=`scaleX(${Math.min(1,Math.max(0,scrollY/max))})`;
 });};window.addEventListener('scroll',onScroll,{passive:true});onScroll();
 // Menu-only chapters: a compact accessible index of REAL published categories.
 if(path==='/menu'){
   const host=document.getElementById('app');
   const section=document.createElement('aside');section.className='v27-menu-guide';
   section.innerHTML='<details><summary><span>THE MENU DIRECTORY</span><span class="v27-guide-hint">Discover dishes by chapter <span aria-hidden="true">↗</span></span></summary><div class="v27-category-list" id="v27Categories" role="group" aria-label="Published menu chapters"><p>Loading chapters…</p></div><p class="v27-guide-note">Dish names and prices come from the supplied café menu. Confirm current availability and pricing with staff.</p></details>';
   if(host){host.before(section);}
   fetch('/api/v27/menu/categories').then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{
      const el=document.getElementById('v27Categories');if(!el)return;
      el.innerHTML=data.categories.map((c,i)=>`<button type="button" data-category="${safe(c.name)}" aria-label="Explore ${safe(c.name)}, ${c.count} dishes"><span>${String(i+1).padStart(2,'0')}</span><strong>${safe(c.name)}</strong><small>${c.count} dishes</small></button>`).join('');
      el.querySelectorAll('[data-category]').forEach(btn=>btn.addEventListener('click',()=>showCategory(btn.dataset.category)));
   }).catch(()=>{const el=document.getElementById('v27Categories');if(el)el.textContent='Directory unavailable; you can still browse the complete book below.';});
   async function showCategory(category){
     const el=document.getElementById('v27Categories');if(!el)return;
     el.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.category===category)));
     let results=document.getElementById('v27CategoryResults');
     if(!results){results=document.createElement('div');results.id='v27CategoryResults';results.className='v27-category-results';results.setAttribute('aria-live','polite');el.after(results);}
     results.textContent='Finding published dishes…';
     try{
       const r=await fetch('/api/menu?'+new URLSearchParams({category,limit:'250'}),{cache:'no-store'});if(!r.ok)throw Error();
       const data=await r.json();const rows=data.items||[];
       results.innerHTML=`<h3>${safe(category)} <span>${rows.length} dishes</span></h3><div class="v27-dish-grid">${rows.map(x=>`<a href="/menu?item=${encodeURIComponent(x.id)}"><strong>${safe(x.name)}</strong><span>${safe(x.price_display)} <small>VIEW ↗</small></span></a>`).join('')}</div>`;
     }catch{results.textContent='Could not load this chapter. The original menu book is still available.';}
   }
 }
 // Consolidated version label in site footer without claiming external integrations.
 const foot=document.querySelector('.footer-bottom');if(foot){const label=document.createElement('span');label.className='v27-foot-label';label.textContent='V27 • SIGNATURE QUALITY';foot.append(label);}
 const lowData=document.getElementById('v26LiteMode');
 if(lowData)lowData.setAttribute('aria-label','Reduce visual motion and data usage');
 // Make all images from the gallery resilient to partial failure, without hiding captions.
 document.addEventListener('error',e=>{const im=e.target;
   if(im instanceof HTMLImageElement&&!im.dataset.v27Fallback){im.dataset.v27Fallback='true';im.classList.add('v27-image-error');im.alt=im.alt||'Photograph unavailable';}
 },true);
});
})();
