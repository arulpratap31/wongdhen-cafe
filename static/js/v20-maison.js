/* Wongdhen Café V20 Maison — customer-first enhancements only.
   No modification of reservations, payments, or staff authorization. */
(()=>{'use strict';
const app=document.querySelector('#app');
const PHOTO='/static/v10/large/';
const markup=`<section class="v20-journey" aria-label="Explore Wongdhen Café your way">
  <span class="v20-eyebrow">THE WONGDHEN EXPERIENCE / 01 — 03</span>
  <div class="v20-journey-header"><h2>Come for<br><em>the feeling.</em></h2><p>Three ways to get to know Wongdhen: browse the actual menu, step inside through genuine café photography, and find your way to Majnu Ka Tila.</p></div>
  <div class="v20-journey-grid">
    <a class="v20-journey-card" href="/menu"><img src="${PHOTO}P0195.webp" loading="lazy" decoding="async" alt="Food and drink photography from Wongdhen Café"/><div class="v20-card-copy"><small>01 / THE FLAVOURS</small><strong>Explore<br>the menu.</strong><span>Turn through the interactive book and discover the café's selection.</span><b>OPEN THE MENU ↗</b></div></a>
    <a class="v20-journey-card" href="/gallery"><img src="${PHOTO}P0214.webp" loading="lazy" decoding="async" alt="Warm interior of Wongdhen Café"/><div class="v20-card-copy"><small>02 / THE ATMOSPHERE</small><strong>Find your<br>corner.</strong><span>See the spaces through genuine café photographs.</span><b>EXPLORE THE GALLERY ↗</b></div></a>
    <a class="v20-journey-card" href="/visit"><img src="${PHOTO}P0222.webp" loading="lazy" decoding="async" alt="Wongdhen Café outdoor terrace"/><div class="v20-card-copy"><small>03 / THE VISIT</small><strong>Stay a<br>little longer.</strong><span>Find the café, check visitor information and plan your visit.</span><b>PLAN YOUR VISIT ↗</b></div></a>
  </div><div class="v20-journey-note"><span>THE CAFÉ · THE FOOD · THE PEOPLE</span><span>REAL PHOTOGRAPHY / NO STOCK IMAGERY</span></div>
</section>`;
const useful=`<section class="v20-useful" aria-label="Quick ways to explore"><div><span class="v20-eyebrow">GOOD TO KNOW</span><h2>Everything<br><em>in reach.</em></h2><p>From choosing something to eat to finding the café, the essentials should be simple. Reservation availability is not shown as confirmed until the owner activates the live booking service.</p></div><nav class="v20-useful-links" aria-label="Essential café links"><a href="/menu">Browse the menu <span aria-hidden="true">↗</span></a><a href="/visit">Find Wongdhen <span aria-hidden="true">↗</span></a><a href="/contact">Contact the café <span aria-hidden="true">↗</span></a></nav></section>`;
function enhance(){if(!app||document.body.dataset.page!=='home')return;
 const story=app.querySelector('.v13-home-story');
 if(story&&!app.querySelector('.v20-journey'))story.insertAdjacentHTML('afterend',markup);
 const final=app.querySelector('.v13-home-final');
 if(final&&!app.querySelector('.v20-useful'))final.insertAdjacentHTML('beforebegin',useful);
 // Avoid misleading certainty: the current reservation page explicitly declares bookings unavailable.
 const hero=app.querySelector('.v13-home-hero .v13-actions a[href="/reservations"]');
 if(hero){hero.href='/visit';hero.textContent='PLAN YOUR VISIT ↗';}
}
if(app){enhance();const observer=new MutationObserver(()=>{enhance()});observer.observe(app,{childList:true});}
document.querySelectorAll('.desktop-nav a,.v20-mobile-actions a').forEach(a=>{if(a.pathname===location.pathname)a.setAttribute('aria-current','page')});
})();
/* Buyer-value readiness review: live data checks, not a fake certification. */
window.WongdhenV20={showReadiness:async()=>{
 const host=document.querySelector('#adminTab');if(!host)return;
 host.innerHTML='<div class="v20-readiness"><p>Checking business and menu records…</p></div>';
 const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const read=async path=>{try{const r=await fetch(path,{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('Not available');return await r.json()}catch{return null}};
 const [settings,menu,appearance]=await Promise.all([read('/api/settings'),read('/api/admin/menu'),read('/api/v21/appearance')]);
 const items=Array.isArray(menu?.items)?menu.items:[];
 const approved=items.filter(x=>x.approved).length;
 const published=items.filter(x=>x.published).length;
 const rows=[
 ['Published contact details',!!(settings?.phone&&settings?.address&&settings?.hours),'Confirm the correct address, telephone number, and opening hours','settings'],
 ['Menu owner verification',items.length>0&&approved===items.length,`${approved} / ${items.length} accessible admin menu items owner-approved; ${published} published. The full PDF also needs an owner review.`,'menu'],
 ['Site appearance configured',!!appearance?.default_theme,appearance?.default_theme?`Default color palette: ${safe(appearance.default_theme)}.`:'Choose a website default theme.','appearance'],
 ['Real reservation availability',false,'Owner table inventory, operating hours, concurrency, notification delivery and live booking tests require explicit sign-off.','bookings'],
 ['Production infrastructure',false,'Domain, HTTPS, monitoring, secure secrets, backup restoration and rollback require live infrastructure testing.',null],
 ['Business acceptance',false,'Owner must approve current prices, contact channels, imagery rights, booking rules, and the final live walkthrough.',null]
 ];
 host.innerHTML=`<section class="v20-readiness"><span class="v20-eyebrow">OWNER OPERATIONS / HANDOVER</span><h2>Before you go live.</h2><p>These checks help prepare the website for a paying hospitality client. A green check verifies only the stated local condition. It is not proof of live deployment or legal compliance.</p><div class="v20-readiness-score"><strong>${rows.filter(x=>x[1]).length} / ${rows.length}</strong><span>READINESS CHECKS CURRENTLY SATISFIED</span></div><div class="v20-readiness-list">${rows.map(([label,ok,detail,tab])=>`<article><b class="${ok?'v20-ready':'v20-pending'}">${ok?'✓ LOCAL CHECK PASSED':'! ACTION REQUIRED'}</b><h3>${safe(label)}</h3><p>${safe(detail)}</p>${tab?`<button type="button" data-v20-admin-jump="${safe(tab)}">OPEN ${safe(tab).toUpperCase()} →</button>`:''}</article>`).join('')}</div><p><strong>Release rule:</strong> Do not call this website fully live-ready until reservation, infrastructure, and owner acceptance checks have actually been completed.</p></section>`;
 host.querySelectorAll('[data-v20-admin-jump]').forEach(button=>button.addEventListener('click',()=>{const tab=document.querySelector(`.admin-actions button[data-tab="${button.dataset.v20AdminJump}"]`);tab?.click()}));
}};
