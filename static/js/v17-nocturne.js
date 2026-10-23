/* V17 visual-only enhancements. No changes to menu/booking/business state. */
(()=>{'use strict';
 const root=document.documentElement;
 const reveal=()=>{
  if(!('IntersectionObserver' in window))return;
  const els=document.querySelectorAll('.v17-book-feature,.v17-book-copy,.v13-home-story,.v13-spread-heading,.v13-chapter-head');
  const observer=new IntersectionObserver(entries=>entries.forEach(({target,isIntersecting})=>{
   if(isIntersecting){target.classList.add('v17-visible');observer.unobserve(target)}
  }),{rootMargin:'120px 0px',threshold:0.02});
  els.forEach(el=>observer.observe(el));
 };
 const app=document.getElementById('app');
 if(app){let request=false;const watcher=new MutationObserver(()=>{
  if(request)return;request=true;requestAnimationFrame(()=>{request=false;reveal()});
 });watcher.observe(app,{childList:true,subtree:false});}
 reveal();
 // Route-aware navigation highlighting is visual only and remains keyboard accessible.
 document.querySelectorAll('.desktop-nav a').forEach(link=>{
  if(link.pathname===location.pathname)link.setAttribute('aria-current','page');
 });
})();
