/* V40 — Canonical multi-portal route map and contextual navigation.
   These URLs never grant access: FastAPI permission checks remain authoritative. */
(()=>{'use strict';
 const home={admin:'/owner',manager:'/manager',booking_staff:'/staff/reservations',kitchen_staff:'/staff/kitchen',content_editor:'/staff/content'};
 const routes={
 admin:{'owner-desk':'/owner','owner-finance':'/owner/finance','owner-growth':'/owner/growth','owner-customers':'/owner/customers','staff':'/owner/team','owner-editorial':'/owner/editorial',bookings:'/owner/reservations',menu:'/owner/menu',audit:'/owner/audit'},
 manager:{'manager-desk':'/manager','manager-standards':'/manager/daily',bookings:'/manager/reservations',calendar:'/manager/calendar',kitchen:'/manager/kitchen',menu:'/manager/menu',inbox:'/manager/inbox',walkins:'/manager/queue'},
 booking_staff:{'staff-desk':'/staff/reservations',bookings:'/staff/reservations/bookings',calendar:'/staff/reservations/calendar',waitlist:'/staff/reservations/waitlist',walkins:'/staff/reservations/queue'},
 kitchen_staff:{'staff-desk':'/staff/kitchen',kitchen:'/staff/kitchen/orders'},
 content_editor:{'staff-desk':'/staff/content',menu:'/staff/content/menu','v10-media':'/staff/content/photos',media:'/staff/content/upload'}
 };
 const headings={admin:['OWNER OFFICE','Private financial and business intelligence'],manager:['MANAGEMENT OFFICE','Daily service and guest operations'],booking_staff:['RESERVATIONS DESK','Bookings and guest arrival'],kitchen_staff:['KITCHEN STATION','Order preparation and fulfilment'],content_editor:['CREATIVE STUDIO','Menu and approved media']};
 const navigation={
 admin:[['/owner','Overview'],['/owner/finance','Finance'],['/owner/growth','Growth'],['/owner/customers','Customers'],['/owner/team','Team'],['/owner/audit','Audit']],
 manager:[['/manager','Overview'],['/manager/daily','Daily service'],['/manager/reservations','Reservations'],['/manager/calendar','Calendar'],['/manager/kitchen','Kitchen']],
 booking_staff:[['/staff/reservations','My desk'],['/staff/reservations/bookings','Bookings'],['/staff/reservations/calendar','Calendar'],['/staff/reservations/waitlist','Waitlist']],
 kitchen_staff:[['/staff/kitchen','My desk'],['/staff/kitchen/orders','Orders']],
 content_editor:[['/staff/content','My desk'],['/staff/content/menu','Menu'],['/staff/content/photos','Photos'],['/staff/content/upload','Uploads']]
 };
 function routeForTab(role,tab){return routes[role]?.[tab]||`${home[role]||'/admin'}?section=${encodeURIComponent(tab)}`;}
 function tabFromLocation(role){
   const match=Object.entries(routes[role]||{}).find(([,path])=>path===location.pathname);
   // A section query is used only for tools without a dedicated subpage.
   const fromQuery=new URLSearchParams(location.search).get('section');
   return fromQuery||match?.[0]||'staff-desk';
 }
 function decorate(root,role){
   const ws=root.querySelector('.v30-workspace'),stage=root.querySelector('.v30-stage');
   if(!ws||!stage)return;
   const [name,subtitle]=headings[role]||['TEAM WORKSPACE','Authorized access'];
   const mast=document.createElement('div');mast.className='v40-portal-mast';
   const mark=document.createElement('div');mark.className='v40-portal-mark';mark.textContent=role==='admin'?'W.':role==='manager'?'M.':role==='kitchen_staff'?'K.':role==='booking_staff'?'R.':'C.';
   const title=document.createElement('div');title.className='v40-portal-name';
   const strong=document.createElement('strong');strong.textContent=name;
   const small=document.createElement('span');small.textContent=subtitle;
   title.append(strong,small);
   const links=document.createElement('nav');links.className='v40-portal-links';links.setAttribute('aria-label',`${name} sections`);
   for(const [url,label] of navigation[role]||[]){
     const a=document.createElement('a');a.href=url;a.textContent=label;
     if(url===location.pathname){a.classList.add('active');a.setAttribute('aria-current','page');}
     links.append(a);
   }
   mast.append(mark,title,links);stage.prepend(mast);
   root.querySelector('.v30-logo small').textContent=name;
   const foot=root.querySelector('.v30-workspace-footer span:last-child');if(foot)foot.textContent=role==='admin'?'Private business information · Owner-only access':'Assigned permissions · Service records only';
   const friendlyName=role==='admin'?'Owner':role==='manager'?'Manager':role==='booking_staff'?'Reception':role==='kitchen_staff'?'Kitchen':'Creative';
   const rolePill=root.querySelector('#v30RoleBadge');if(rolePill)rolePill.textContent=friendlyName.toUpperCase();
   // As the existing in-page sidebar changes sections, keep the shortcut strip accurate.
   root.addEventListener('click',e=>{const tab=e.target.closest('[data-tab]');if(!tab)return;
     const dest=routeForTab(role,tab.dataset.tab);
     links.querySelectorAll('a').forEach(a=>{
       const active=a.getAttribute('href')===dest;
       a.classList.toggle('active',active);
       if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
     });
   });
 }
 window.WongdhenV40={home,routeForTab,tabFromLocation,decorate};
})();
