/* V32 Signature House: progressive luxury motion and authentic operational intelligence.
   The booking, account and menu engines remain the originals and are not simulated. */
(() => {
  'use strict';
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const motionReduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
    document.documentElement.classList.contains('v4-motion-off') ||
    (()=>{try{return sessionStorage.getItem('wongdhen-motion')==='off'}catch{return false}})();
  const page = document.body.dataset.page;
  const admin = page === 'admin';

  // An unobtrusive reading-position indicator. Never blocks scrolling or pointer input.
  if (!admin) {
    const rail = document.createElement('div');rail.className='v32-reading-rail';rail.setAttribute('aria-hidden','true');
    rail.innerHTML='<span></span>';document.body.append(rail);
    const fill=rail.firstElementChild;let scheduled=false;
    function updateScroll(){scheduled=false;const doc=document.documentElement;
      const range=Math.max(1,doc.scrollHeight-window.innerHeight);
      fill.style.transform=`scaleX(${Math.min(1,Math.max(0,window.scrollY/range))})`;
    }
    addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(updateScroll)}},{passive:true});
    addEventListener('resize',updateScroll,{passive:true});updateScroll();
    // Decorative effects never obscure actual image content or intercept links.
    const main=$('#app');
    const enhance=()=>{
      const hero=$('.hero, .v13-home-hero, .v13-home-intro, .page-hero',main);
      if(hero&&!$('.v32-hero-signature',hero)){
        const tag=document.createElement('span');tag.className='v32-hero-signature';tag.textContent='W / NEW DELHI';
        tag.setAttribute('aria-hidden','true');hero.appendChild(tag);
      }
      // The source homepage is asynchronously assembled by the original V13 gallery.
      // Insert the Signature Edition once, without replacing any source content or navigation.
      if(page==='home' && !$('#v32Invitation',main)){
        const anchor=$('.v13-home-story',main);
        if(anchor){
          const section=document.createElement('section');section.id='v32Invitation';section.className='v32-invitation';
          section.setAttribute('aria-label','Three ways to experience Wongdhen');
          section.innerHTML=`<div class="v32-invitation-top"><div><span class="v32-invitation-label">WONGDHEN / THE SIGNATURE EDITION</span><h2>Stay a little.<br/><em>Feel a lot.</em></h2></div><div class="v32-invitation-desc"><p>From the first sip to the last conversation, every corner has a story. Discover the food, the atmosphere and the moments waiting here.</p><a href="/about">DISCOVER OUR STORY <span aria-hidden="true">↗</span></a></div></div><div class="v32-invitation-grid">
          <a class="v32-invitation-card" href="/menu"><div class="v32-invitation-photo"><img src="/static/images/v10-food.webp" loading="lazy" decoding="async" alt="Original Wongdhen Café food photography"></div><span>01 / THE FLAVOURS <b aria-hidden="true">↗</b></span></a>
          <a class="v32-invitation-card" href="/gallery"><div class="v32-invitation-photo"><img src="/static/images/v10-interior.webp" loading="lazy" decoding="async" alt="Original Wongdhen Café interior photography"></div><span>02 / THE ATMOSPHERE <b aria-hidden="true">↗</b></span></a>
          <a class="v32-invitation-card" href="/visit"><div class="v32-invitation-photo"><img src="/static/images/v10-dessert.webp" loading="lazy" decoding="async" alt="A dessert photographed at Wongdhen Café"></div><span>03 / YOUR NEXT VISIT <b aria-hidden="true">↗</b></span></a>
          </div>`;
          anchor.insertAdjacentElement('afterend',section);
        }
      }
      if(motionReduced())return;
      $$('section:not(.v32-observed):not(.hero),.v13-collage:not(.v32-observed),.v13-frame:not(.v32-observed)',main)
        .slice(0,130).forEach(el=>{el.classList.add('v32-observed');observer?.observe(el)});
    };
    const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries=>{
      entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('v32-arrived');observer.unobserve(e.target)}});
    },{threshold:0.035,rootMargin:'80px 0px -35px 0px'}):null;
    if(observer){const changes=new MutationObserver(()=>{if(!scheduledEnhance){scheduledEnhance=true;requestAnimationFrame(()=>{scheduledEnhance=false;enhance()})}});
      let scheduledEnhance=false;changes.observe(main,{childList:true,subtree:false});
    }
    enhance();
  }

  function renderPulse(data){
    const series=Array.isArray(data.seven_day_reservations)?data.seven_day_reservations:[];
    const max=Math.max(1,...series.map(d=>Number(d.count)||0));
    const stat=(label,value,sub,tab)=>`<article class="v32-stat"><span>${escape(label)}</span><strong>${Number(value).toLocaleString('en-IN')}</strong><small>${escape(sub)}</small><button type="button" data-v32-tab="${escape(tab)}">OPEN SECTION <b aria-hidden="true">↗</b></button></article>`;
    const statuses=Object.entries(data.status_counts||{});
    const activity=Array.isArray(data.recent_activity)?data.recent_activity:[];
    return `<section class="v32-pulse">
      <header class="v32-pulse-cover"><div><span class="v32-overline">OWNER INTELLIGENCE / ${escape(data.day)} · IST</span><h2>Every detail.<br/><em>In its place.</em></h2><p>Operational clarity for the people who run the house. Every number is sourced from actual records.</p></div><div class="v32-pulse-seal" aria-hidden="true">W<span>32</span></div></header>
      <div class="v32-section-label"><span>01 / SERVICE AT A GLANCE</span><span>RECORDED COUNTS, NOT ESTIMATES</span></div>
      <div class="v32-stat-grid">${stat('Reservations today',data.today_reservations,'Requests across all recorded states','bookings')}${stat('Enquiries to review',data.unreviewed_enquiries,'Guest messages marked new','inbox')}${stat('Menu approvals',data.pending_menu_approvals,'Published entries awaiting owner verification','menu')}${stat('Configured tables',data.active_tables,'Active inventory only','tables')}</div>
      <div class="v32-pulse-panels"><section class="v32-pulse-panel"><div class="v32-section-label"><span>02 / SEVEN-DAY RESERVATION VOLUME</span><span>ACTUAL RECORDS</span></div>
       <div class="v32-bars" role="img" aria-label="Reservations recorded per day for the past seven days">${series.map(row=>`<div class="v32-bar-col" title="${escape(row.date)}: ${Number(row.count)} reservations"><span>${Number(row.count)}</span><div class="v32-bar-track"><i style="height:${Math.max(0,Math.min(100,(Number(row.count)/max)*100))}%"></i></div><small>${escape(row.date.slice(5))}</small></div>`).join('')}</div>
       <p class="v32-help">Counts include every reservation status, including requests and cancellations. Not a measure of occupied tables.</p>
       <div class="v32-statuses">${statuses.length?statuses.map(([name,count])=>`<span>${escape(name.replaceAll('_',' '))} <b>${Number(count)}</b></span>`).join(''):'<span>No reservations recorded for today.</span>'}</div></section>
       <section class="v32-pulse-panel"><div class="v32-section-label"><span>03 / RECENT OPERATIONS</span><span>AUDIT TRAIL</span></div><ol class="v32-activity">${activity.length?activity.map(a=>`<li><span class="v32-activity-dot" aria-hidden="true"></span><span><strong>${escape(a.action)}</strong><small>${escape(a.at?.replace('T',' ').slice(0,19) || 'Recorded activity')}</small></span></li>`).join(''):'<li><span>There are no recorded owner actions yet.</span></li>'}</ol></section></div>
       <p class="v32-data-disclaimer">${escape(data.notice)}</p>
    </section>`;
  }
  async function showPulse(){
    const panel=$('#adminTab');if(!panel)return;
    panel.innerHTML='<div class="v32-pulse-loading" role="status">Loading actual service records…</div>';
    try{
      const response=await fetch('/api/v32/admin/pulse',{credentials:'same-origin',headers:{Accept:'application/json'}});
      if(!response.ok)throw Error(response.status===403?'Owner-only access':response.status===401?'Please sign in again':'Service data unavailable');
      const data=await response.json();if(!$('.admin-actions [data-tab="pulse"].active'))return;
      panel.innerHTML=renderPulse(data);
      $$('[data-v32-tab]',panel).forEach(el=>el.addEventListener('click',()=>{
        $('.admin-actions [data-tab="'+el.dataset.v32Tab+'"]')?.click();
      }));
    }catch(e){panel.innerHTML='<div class="v32-pulse-error" role="alert"><h3>Unable to display live records</h3><p></p><button type="button">RETRY LOADING ↗</button></div>';
      $('.v32-pulse-error p',panel).textContent=e.message;$('.v32-pulse-error button',panel).addEventListener('click',showPulse);}
  }
  window.WongdhenV32={showPulse};

})();
