(()=>{
  'use strict';
  if(document.body.dataset.page!=='admin' || window.WongdhenV35) return;

  const SECTION_META={
    v8:{eyebrow:'COMMERCE / OWNER OPERATIONS',lead:'Manage orders, stock, and the services that keep the house running.'},
    menu:{eyebrow:'MENU / CURATION DESK',lead:'Refine published items, verify pricing, and keep the menu commercially presentable.'},
    bookings:{eyebrow:'RESERVATIONS / SERVICE FLOW',lead:'Review guest requests in a cleaner operations workspace designed for real hospitality teams.'},
    inbox:{eyebrow:'GUEST RELATIONS / INBOX',lead:'Handle enquiries in a clearer workspace with better reading rhythm and quicker actions.'},
    settings:{eyebrow:'BRAND & BUSINESS / DETAILS',lead:'Keep the commercial information accurate and elegant without cluttered forms.'},
    staff:{eyebrow:'TEAM ACCESS / OPERATIONS',lead:'Manage staff permissions, roles, and secure access to the house.'},
    default:{eyebrow:'WONGDHEN / OWNER WORKSPACE',lead:'Everything you need to keep service running smoothly.'}
  };

  let observer=null, raf=0;
  const $=(q,root=document)=>root.querySelector(q);
  const $$=(q,root=document)=>[...root.querySelectorAll(q)];

  function currentSection(){return document.querySelector('.admin-actions .active')?.dataset.tab||'default';}
  function metaFor(id){return SECTION_META[id]||SECTION_META.default;}
  function schedule(){cancelAnimationFrame(raf);raf=requestAnimationFrame(enhance);}

  function wrapHero(tab, section){
    if(tab.querySelector(':scope > .v35-section-hero')) return;
    const h2=tab.querySelector(':scope > h2');
    if(!h2) return;
    const p=h2.nextElementSibling && h2.nextElementSibling.matches('p') ? h2.nextElementSibling : null;
    const meta=metaFor(section);
    const hero=document.createElement('section');
    hero.className='v35-section-hero';
    hero.innerHTML=`<div class="v35-hero-copy"><p class="v35-hero-eyebrow">${meta.eyebrow}</p><div class="v35-hero-title"></div><p class="v35-hero-lead"></p></div><div class="v35-hero-mark" aria-hidden="true">W.</div>`;
    const titleHost=hero.querySelector('.v35-hero-title');
    titleHost.appendChild(h2);
    // Move the original node, not its text: export links and event listeners
    // in introductory paragraphs are functional controls, not decoration.
    if(p){ p.classList.add('v35-hero-lead'); hero.querySelector('.v35-hero-lead').replaceWith(p); }
    else hero.querySelector('.v35-hero-lead').textContent=meta.lead;
    tab.prepend(hero);
  }

  function stylizeTopNav(tab){
    const nav=tab.querySelector('.v8-admin-nav, .v7-admin-nav');
    if(nav) nav.classList.add('v35-chip-nav');
  }

  function wrapSurfaceFrom(first,last){
    if(!first||!last||first.parentElement!==last.parentElement) return null;
    const surface=document.createElement('section');
    surface.className='v35-surface';
    first.parentElement.insertBefore(surface, first);
    let node=first;
    while(node){
      const next=node.nextSibling;
      surface.appendChild(node);
      if(node===last) break;
      node=next;
    }
    return surface;
  }

  function groupHeadedContent(container){
    const headingChildren=[...container.children].filter(n=>n.tagName==='H3');
    headingChildren.forEach(h3=>{
      if(h3.closest('.v35-surface')) return;
      let last=h3;
      let node=h3.nextElementSibling;
      while(node && node.tagName!=='H3'){
        const next=node.nextElementSibling;
        if(!node.classList.contains('v35-section-hero') && !node.classList.contains('v35-chip-nav')) last=node;
        node=next;
      }
      wrapSurfaceFrom(h3,last);
    });

    const remaining=[...container.children].filter(n=>!n.classList.contains('v35-section-hero') && !n.classList.contains('v35-chip-nav') && !n.classList.contains('v35-surface'));
    if(remaining.length){
      // Group loose content into a lead surface if it contains meaningful elements.
      const meaningful=remaining.filter(n=>!(n.tagName==='P' && !n.textContent.trim()));
      if(meaningful.length){
        wrapSurfaceFrom(meaningful[0], meaningful[meaningful.length-1])?.classList.add('v35-surface-lead');
      }
    }
  }

  function enhanceStatCards(root){
    $$('.v8-admin-stats',root).forEach(grid=>{
      grid.classList.add('v35-card-grid');
      [...grid.children].forEach(card=>{
        if(card.tagName==='DIV') card.classList.add('v35-stat-card');
      });
    });
  }

  function enhanceLists(root){
    $$('.v8-admin-list,.admin-menu-list',root).forEach(el=>el.classList.add('v35-scroll-card'));
    $$('.v8-stock-row',root).forEach(row=>row.classList.add('v35-split-row'));
    $$('.visit-detail,.v8-order-card,.v23-ops-card,.v22-owner-card',root).forEach(card=>card.classList.add('v35-surface-card'));
    $$('.v9-calendar-grid',root).forEach(grid=>grid.classList.add('v35-card-grid','v35-mini-card-grid'));
    $$('.v9-calendar-day',root).forEach(card=>card.classList.add('v35-stat-card','v35-mini-stat-card'));
  }

  function enhanceForms(root){
    $$('form',root).forEach(form=>form.classList.add('v35-form-stack'));
    $$('label',root).forEach(label=>{
      if(label.closest('.v35-section-hero')) return;
      const hasControl=label.querySelector('input,select,textarea');
      if(hasControl) label.classList.add('v35-field');
    });
    $$('textarea[readonly]',root).forEach(t=>t.classList.add('v35-readonly'));
  }

  function enhanceButtons(root){
    $$('button, .submit-button, .saveitem, .save-table, .toolbtn',root).forEach(btn=>{
      if(btn.closest('.v35-section-hero')) return;
      btn.classList.add('v35-button');
    });
  }

  function enhanceTables(root){
    $$('.admin-table',root).forEach(table=>table.classList.add('v35-data-table'));
  }

  function enhanceSurfaceMeta(root){
    $$('.v35-surface > h3',root).forEach(h=>{
      const lead=h.nextElementSibling;
      if(lead && lead.matches('p') && !h.parentElement.querySelector('.v35-surface-head')){
        const wrap=document.createElement('div');
        wrap.className='v35-surface-head';
        h.parentElement.insertBefore(wrap,h);
        wrap.appendChild(h);
        wrap.appendChild(lead);
      }
    });
  }

  function markSection(tab, section){
    tab.classList.add('v35-admin-page');
    tab.dataset.v35Section=section;
    const panel=$('#v8AdminPanel',tab);
    if(panel) panel.classList.add('v35-subworkspace');
  }

  function markRelease(){
    document.body.classList.add('v35-modern-owner');
  }

  function enhance(){
    const tab=$('#adminTab');
    if(!tab || !document.body.classList.contains('v30-authenticated')) return;
    markRelease();
    const section=currentSection();
    markSection(tab,section);
    // These views already own their layout. Do not rewrap their asynchronous
    // loading/error states or nest their cards inside a second presentation.
    if(['studio','audit','inbox','pulse'].includes(section)) return;
    wrapHero(tab, section);
    stylizeTopNav(tab);
    groupHeadedContent(tab);
    const panel=$('#v8AdminPanel',tab);
    if(panel){
      groupHeadedContent(panel);
      enhanceStatCards(panel);
      enhanceLists(panel);
      enhanceForms(panel);
      enhanceButtons(panel);
      enhanceTables(panel);
      enhanceSurfaceMeta(panel);
    }
    enhanceStatCards(tab);
    enhanceLists(tab);
    enhanceForms(tab);
    enhanceButtons(tab);
    enhanceTables(tab);
    enhanceSurfaceMeta(tab);
  }

  function connect(){
    const host=$('#adminContent') || document.body;
    if(observer) observer.disconnect();
    observer=new MutationObserver(schedule);
    observer.observe(host,{childList:true,subtree:true});
    document.addEventListener('click',e=>{
      if(e.target.closest('.admin-actions button,.v8-admin-nav button,.v7-admin-nav button,.v34-shortcut')) setTimeout(schedule,0);
    },true);
    schedule();
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',connect,{once:true});
  else connect();
  window.WongdhenV35={enhance:schedule};
})();
