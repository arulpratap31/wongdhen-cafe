/* V34 Owner Atelier: accessible spacious workspace, persistent display preferences. */
(()=>{
 'use strict';
 if(document.body.dataset.page!=='admin')return;
 const KEY='wongdhen-v34-admin-layout';
 const SECTIONS=[['studio','Command'],['bookings','Reservations'],['inbox','Guest inbox'],['menu','Menu']];
 let mounted=null;
 const get=id=>document.getElementById(id);
 const root=()=>document.querySelector('.v30-shell');
 const canNav=id=>!!document.querySelector(`.admin-actions [data-tab="${id}"]`);
 const stored=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch{return {}}};
 const persist=patch=>{try{localStorage.setItem(KEY,JSON.stringify({...stored(),...patch}))}catch{}};
 const navigate=id=>document.querySelector(`.admin-actions [data-tab="${id}"]`)?.click();
 const updateButtons=()=>{
   document.querySelectorAll('[data-v34-density]').forEach(b=>b.setAttribute('aria-pressed',String((b.dataset.v34Density==='comfort')===document.body.classList.contains('v34-comfortable'))));
   get('v34Focus')?.setAttribute('aria-pressed',String(document.body.classList.contains('v34-focus-mode')));
 };
 function changeDensity(mode){document.body.classList.toggle('v34-comfortable',mode==='comfort');persist({density:mode});updateButtons();}
 function focusMode(next){document.body.classList.toggle('v34-focus-mode',next);persist({focus:next});updateButtons();}
 function makeNavGroups(shell){
   shell.querySelectorAll('.v30-navigation-group').forEach((section,index)=>{
     const heading=section.querySelector('.v30-group-heading');
     if(!heading||section.querySelector('.v34-group-trigger'))return;
     const name=heading.textContent.trim();
     const links=document.createElement('div');links.className='v34-group-links';
     const id='v34-group-'+index;links.id=id;
     const controls=[...section.querySelectorAll('.v30-side-link')];
     controls.forEach(link=>links.append(link));
     const toggle=document.createElement('button');toggle.type='button';toggle.className='v34-group-trigger';
     toggle.setAttribute('aria-controls',id);
     const label=document.createElement('span');label.textContent=name;
     const count=document.createElement('span');count.className='v34-group-count';count.textContent=String(controls.length);count.setAttribute('aria-label',controls.length+' sections');
     const arrow=document.createElement('span');arrow.className='v34-group-chevron';arrow.textContent='⌄';arrow.setAttribute('aria-hidden','true');
     toggle.append(label,count,arrow);heading.replaceWith(toggle);section.append(links);
     let open=controls.some(b=>b.classList.contains('active'))||index===0;
     const remembered=stored().groups;
     if(remembered&&typeof remembered[id]==='boolean')open=remembered[id];
     const change=(value,save=false)=>{
       links.hidden=!value;toggle.setAttribute('aria-expanded',String(value));
       if(save)persist({groups:{...(stored().groups||{}),[id]:value}});
     };
     change(open);
     toggle.addEventListener('click',()=>change(links.hidden,true));
   });
 }
 function makeDeck(shell){
   const stage=shell.querySelector('.v30-stage');
   if(!stage||get('v34NavigationDeck'))return;
   const deck=document.createElement('nav');deck.id='v34NavigationDeck';deck.className='v34-navigation-deck';
   deck.setAttribute('aria-label','Quick management navigation and display settings');
   const shortcuts=document.createElement('div');shortcuts.className='v34-shortcuts';
   const label=document.createElement('span');label.textContent='Go straight to';shortcuts.append(label);
   SECTIONS.filter(([id])=>canNav(id)).forEach(([id,name])=>{
      const b=document.createElement('button');b.type='button';b.className='v34-shortcut';
      b.dataset.v34Go=id;b.textContent=name;b.addEventListener('click',()=>navigate(id));shortcuts.append(b);
   });
   deck.append(shortcuts);
   const tools=document.createElement('div');tools.className='v34-layout-tools';
   const caption=document.createElement('span');caption.className='v34-tools-caption';caption.textContent='Workspace spacing';tools.append(caption);
   [['space','Spacious'],['comfort','Comfortable']].forEach(([id,name])=>{
     const b=document.createElement('button');b.type='button';b.className='v34-tool';b.dataset.v34Density=id;
     b.textContent=name;b.addEventListener('click',()=>changeDensity(id));tools.append(b);
   });
   const focus=document.createElement('button');focus.type='button';focus.id='v34Focus';focus.className='v34-tool';
   focus.textContent='Distraction-free view';focus.title='Hide the desktop sidebar; quick navigation remains available';
   focus.addEventListener('click',()=>focusMode(!document.body.classList.contains('v34-focus-mode')));
   tools.append(focus);deck.append(tools);
   const intro=stage.querySelector('.v30-stage-intro');intro?.insertAdjacentElement('afterend',deck);
   updateButtons();
 }
 function onSectionChange(id){
   document.querySelectorAll('.v34-shortcut').forEach(b=>{
     if(b.dataset.v34Go===id)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
   });
   const link=document.querySelector(`.v30-navigation-group [data-tab="${id}"]`);
   const group=link?.closest('.v30-navigation-group');
   const list=group?.querySelector('.v34-group-links'),trigger=group?.querySelector('.v34-group-trigger');
   if(list&&trigger){list.hidden=false;trigger.setAttribute('aria-expanded','true');}
 }
 function mount(){
   const shell=root();if(!shell||shell===mounted)return;
   mounted=shell;
   makeNavGroups(shell);makeDeck(shell);
   const cfg=stored();changeDensity(cfg.density==='comfort'?'comfort':'space');focusMode(cfg.focus===true);
   onSectionChange(shell.querySelector('.admin-actions .active')?.dataset.tab||'studio');
   shell.dataset.v34='admin-atelier';
 }
 // Routed through the authenticated V30 workspace mount. Do not run on the sign-in form.
 window.WongdhenV34={mount,onSectionChange};
})();
