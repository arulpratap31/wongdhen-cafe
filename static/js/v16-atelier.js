/* Wongdhen V16 Atelier: lightweight navigation polish; original interactions stay authoritative. */
(()=>{'use strict';
 const root=document.documentElement;
 const setScroll=()=>root.classList.toggle('v16-scrolled',window.scrollY>42);
 setScroll();window.addEventListener('scroll',setScroll,{passive:true});
 const updateInView=()=>{
   const sections=document.querySelectorAll('.v13-home-spread,.v13-editorial-chapter');
   if(!('IntersectionObserver' in window))return;
   const observer=new IntersectionObserver(es=>es.forEach(e=>{
     if(e.isIntersecting){e.target.classList.add('v16-section-visible');observer.unobserve(e.target)}
   }),{threshold:.04,rootMargin:'70px'});
   sections.forEach(section=>observer.observe(section));
 };
 const app=document.getElementById('app');
 if(app&&'MutationObserver' in window){let pending=false;const observer=new MutationObserver(()=>{
   if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;updateInView()});
 });observer.observe(app,{childList:true});}
 updateInView();
})();
