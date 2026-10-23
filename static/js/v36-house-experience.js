/* V36 / House in Motion — progressive immersive photography, no external 3D libraries.
 * Photographs remain authentic stills; this is an interactive 3D photo installation,
 * not a panoramic/360 capture or a claim about table availability. */
(() => {
  'use strict';
  if (window.WongdhenV36) return;
  const d = document, page = d.body?.dataset.page;
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  const smallData = navigator.connection?.saveData === true;
  const motionOff = () => media.matches || smallData || d.documentElement.classList.contains('v4-motion-off') ||
    (() => { try { return sessionStorage.getItem('wongdhen-motion') === 'off'; } catch { return false; } })();
  const $ = (s, r=d) => r.querySelector(s);
  const photos = [
    {src:'/static/images/v10-entrance.webp', title:'The entrance', category:'01 / OUTSIDE', description:'Your first glimpse of the house.'},
    {src:'/static/images/interior-day.webp', title:'Natural light', category:'02 / INSIDE', description:'A quieter look at the café by day.'},
    {src:'/static/images/hero-night.webp', title:'After dark', category:'03 / ATMOSPHERE', description:'The café under its evening lights.'},
    {src:'/static/images/coffee-art.webp', title:'The ritual', category:'04 / COFFEE', description:'Beautiful small moments, one cup at a time.'},
    {src:'/static/images/v10-food.webp', title:'The table', category:'05 / FOOD', description:'A taste of Wongdhen in a photograph.'}
  ];
  function installHouse(main) {
    if (!main || $('#v36House', main)) return;
    const anchor = $('.v13-home-story', main) || $('.v4-introduction', main);
    if (!anchor) return;
    const section = d.createElement('section');
    section.className = 'v36-house'; section.id = 'v36House';
    section.setAttribute('aria-labelledby', 'v36HouseTitle');
    section.innerHTML = `
      <div class="v36-house-heading">
        <div class="v36-overline"><span class="v36-flower" aria-hidden="true">✳</span> 02 / AN IMMERSIVE PHOTO EDITION</div>
        <div class="v36-house-heading-grid"><h2 id="v36HouseTitle">A place to<br><em>step into.</em></h2>
          <div class="v36-house-intro"><p>Five real photographs. One new perspective. Wander from the entrance to the interiors, then stay for the details.</p>
          <a href="/gallery">EXPLORE THE FULL GALLERY <span aria-hidden="true">↗</span></a></div></div>
      </div>
      <div class="v36-stage" tabindex="0" role="region" aria-roledescription="3D photographic carousel" aria-label="Explore five café photographs. Use left and right arrow keys to change the view.">
        <div class="v36-light v36-light-a" aria-hidden="true"></div><div class="v36-light v36-light-b" aria-hidden="true"></div>
        <div class="v36-rings" aria-hidden="true"><i></i><i></i><i></i></div>
        <div class="v36-orbit" aria-hidden="true">${photos.map((p,i) => `
           <figure class="v36-panel" style="--v36-panel-angle:${i * 72}deg" aria-hidden="${i ? 'true' : 'false'}">
             <img src="${p.src}" alt="${p.title} at Wongdhen Café" ${i ? 'loading="lazy"' : 'loading="eager"'} decoding="async">
             <figcaption><span>${p.category}</span><b>${p.title}</b></figcaption>
           </figure>`).join('')}</div>
        <span class="v36-ground" aria-hidden="true"></span>
      </div>
      <div class="v36-house-controls"><div class="v36-photo-caption" aria-live="polite" aria-atomic="true"><span id="v36Count">01 — 05</span><strong id="v36Name">The entrance</strong><small id="v36Description">Your first glimpse of the house.</small></div>
      <div class="v36-house-nav"><button type="button" id="v36Prev" aria-label="Previous photograph">←</button><button type="button" id="v36Next" aria-label="Next photograph">→</button></div></div>
      <p class="v36-photo-note">Original café photographs in an illustrative 3D arrangement. Not a navigable 360° scan.</p>
      <div class="v36-pair"><a href="/visit" class="v36-pair-card v36-pair-outside"><div class="v36-pair-image"><img src="/static/images/v10-entrance.webp" alt="Photographed Wongdhen Café entrance" loading="lazy"></div><div class="v36-pair-copy"><span>01 / THE FIRST HELLO</span><h3>Outside the <em>ordinary.</em></h3><span>PLAN YOUR VISIT ↗</span></div></a>
      <a href="/about" class="v36-pair-card v36-pair-inside"><div class="v36-pair-image"><img src="/static/images/interior-day.webp" alt="Photographed Wongdhen Café interior" loading="lazy"></div><div class="v36-pair-copy"><span>02 / COME ON IN</span><h3>Inside the <em>moment.</em></h3><span>DISCOVER OUR STORY ↗</span></div></a></div>`;
    anchor.insertAdjacentElement('afterend',section);
    const stage = $('.v36-stage', section), orbit = $('.v36-orbit', section);
    const panels = [...section.querySelectorAll('.v36-panel')];
    let index = 0, pointerDown = null, floating = false;
    function move(delta) {
      index = (index + delta + photos.length) % photos.length;
      orbit.style.setProperty('--v36-rotation', `${-72 * index}deg`);
      panels.forEach((p, i) => p.setAttribute('aria-hidden', String(i !== index)));
      $('#v36Count',section).textContent = `${String(index+1).padStart(2,'0')} — 05`;
      $('#v36Name',section).textContent = photos[index].title;
      $('#v36Description',section).textContent = photos[index].description;
    }
    $('#v36Prev',section).addEventListener('click', () => move(-1));
    $('#v36Next',section).addEventListener('click', () => move(1));
    stage.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); move(event.key === 'ArrowRight' ? 1 : -1); }
    });
    stage.addEventListener('pointerdown', event => { if (event.isPrimary) pointerDown={x:event.clientX,y:event.clientY}; });
    stage.addEventListener('pointerup', event => {
      if (!pointerDown) return;
      const dx=event.clientX-pointerDown.x,dy=event.clientY-pointerDown.y;pointerDown=null;
      if (Math.abs(dx)>48 && Math.abs(dx)>Math.abs(dy)) move(dx<0?1:-1);
    });
    stage.addEventListener('pointercancel', () => {pointerDown=null;});
    if (!motionOff() && window.matchMedia('(pointer: fine)').matches) {
      stage.addEventListener('pointermove', event => {
        if (floating) return;
        floating=true;
        requestAnimationFrame(() => {
          const rect=stage.getBoundingClientRect(),x=(event.clientX-rect.left)/rect.width,y=(event.clientY-rect.top)/rect.height;
          stage.style.setProperty('--v36-x',`${Math.max(0,Math.min(100,x*100))}%`);
          stage.style.setProperty('--v36-y',`${Math.max(0,Math.min(100,y*100))}%`);
          floating=false;
        });
      },{passive:true});
    }
    // Once visible, reveal the installation; no background animation loops are needed.
    const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { section.classList.add('v36-seen'); observer.disconnect(); }
    }, {threshold:0.08}) : null;
    if (observer) observer.observe(section); else section.classList.add('v36-seen');
  }
  if (page === 'home') {
    const main = $('#app');
    let queued = false;
    const tryInstall = () => { queued=false; installHouse(main); };
    if (main) {
      const obs=new MutationObserver(() => {
        if ($('#v36House',main)) {obs.disconnect();return;}
        if (!queued) { queued=true;requestAnimationFrame(tryInstall); }
      });
      obs.observe(main,{childList:true});tryInstall();
    }
  }
  if (page === 'admin') {
    // Admin keeps genuine owner data and existing workflows; styling is intentionally non-invasive.
    d.body.classList.add('v36-owner-edition');
  }
  window.WongdhenV36={version:'36',interactiveGallery:true};
})();
