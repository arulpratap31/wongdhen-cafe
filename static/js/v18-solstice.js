/* V18 Solstice — route-safe thematic styling and real-photography lookbook.
   No modifications to reservation, payment, menu, or administrative state. */
(()=>{'use strict';
  const root=document.documentElement;
  const valid=['verdigris','ember','orchid'];
  let chosen='verdigris';
  try {const saved=localStorage.getItem('wongdhen-v18-palette');if(valid.includes(saved))chosen=saved;}catch(e){}
  const apply=theme=>{
    if(!valid.includes(theme))return;
    root.dataset.v18Theme=theme;
    document.querySelectorAll('[data-v18-choice]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.v18Choice===theme)));
    const meta=document.querySelector('meta[name="theme-color"]');if(meta)meta.content={verdigris:'#123a34',ember:'#472622',orchid:'#26213a'}[theme];
    try {localStorage.setItem('wongdhen-v18-palette',theme)}catch(e){}
  };
  document.querySelector('.v18-palette-dock')?.addEventListener('click',e=>{const b=e.target.closest('[data-v18-choice]');if(b)apply(b.dataset.v18Choice)});
  apply(chosen);
  if(document.body.dataset.page!=='lookbook')return;
  const app=document.getElementById('app');if(!app)return;
  app.innerHTML='<p role="status" class="v13-loading">Preparing the editorial photo collection…</p>';
  fetch('/static/v18/lookbook-manifest.json').then(r=>{if(!r.ok)throw new Error('Unable to load the photographic collection');return r.json()}).then(data=>{
    if(!Array.isArray(data.spreads))throw new Error('The collection has no usable spreads');
    const escape=t=>String(t||'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    app.innerHTML=`<div class="v18-lookbook"><header class="v18-lookbook-hero"><p>WONGDHEN CAFÉ · THE EDITORIAL ARCHIVE</p><h1>The <em>Atelier.</em></h1><span>Photographic compositions made from genuine Wongdhen Café images. Browse a visual study of spaces, textures, dishes and everyday moments.</span></header><div class="v18-lookbook-intro">A collection of ${data.spreads.length} original editorial spreads, each crafted from real café photographs. The original photo subjects are preserved; the compositions are new.</div><div class="v18-lookbook-grid">${data.spreads.map((spread,i)=>`<article><img src="${escape(spread.web)}" alt="Editorial Wongdhen Café photography spread ${i+1}" loading="lazy" decoding="async" width="${spread.width}" height="${spread.height}"/><p><span>ATELIER / ${String(i+1).padStart(3,'0')}</span><small>${escape(spread.chapter)}</small></p></article>`).join('')}</div></div>`;
  }).catch(err=>{app.innerHTML='<div class="v13-load-error" role="alert"><h1>Collection unavailable</h1><p>'+String(err.message).replace(/[<>]/g,'')+'</p><a href="/gallery">EXPLORE THE ORIGINAL GALLERY ↗</a></div>'});
})();
