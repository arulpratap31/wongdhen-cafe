/* Wongdhen Café V9 — Himalayan Nocturne visual layer.
   Zero remote JS dependencies; the parametric artwork is genuine local WebGL 3D.
   All core transactions remain handled by the original V8/V7/V3 application. */
(() => {
'use strict';
const qs=(s,r=document)=>r.querySelector(s);
const all=(s,r=document)=>[...r.querySelectorAll(s)];
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const coarse=matchMedia('(pointer: coarse)');
const motionOff=()=>{
  try{return reduced.matches||sessionStorage.getItem('wongdhen-motion')==='off'}
  catch{return reduced.matches}
};
const safeStored=(key)=>{try{return localStorage.getItem(key)}catch{return null}};
const setStored=(key,value)=>{try{localStorage.setItem(key,value)}catch{}};
const body=document.body;

function initTheme(){
 const btn=qs('#v9Theme');if(!btn)return;
 const theme=safeStored('wongdhen-v9-theme')||'nocturne';
 const useDay=(day)=>{body.classList.toggle('v9-day',day);btn.setAttribute('aria-pressed',String(day));btn.setAttribute('aria-label',day?'Switch to evening appearance':'Switch to daytime appearance');btn.setAttribute('title',day?'Evening appearance':'Daytime appearance');btn.textContent=day?'☀':'◐';document.querySelector('meta[name="theme-color"]')?.setAttribute('content',day?'#e9d8c4':'#201915');};
 useDay(theme==='day');btn.onclick=()=>{let day=!body.classList.contains('v9-day');useDay(day);setStored('wongdhen-v9-theme',day?'day':'nocturne')};
}
function initScrollHeader(){
 let raf=0;const refresh=()=>{raf=0;body.classList.toggle('v9-scrolled',scrollY>125)};
 addEventListener('scroll',()=>{if(!raf)raf=requestAnimationFrame(refresh)},{passive:true});refresh();
}
function initReveals(){
 if(motionOff()||!('IntersectionObserver' in window))return;
 const targets=all('[data-v9-reveal]');if(!targets.length)return;
 // Add script-enabled hidden states only immediately before observation.
 targets.forEach(el=>{if(el.getBoundingClientRect().top < innerHeight*.88)el.classList.add('v9-visible')});
 document.documentElement.classList.add('v9-ready');
 const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('v9-visible');observer.unobserve(entry.target)}}),{threshold:.08,rootMargin:'0px 0px 50px 0px'});
 targets.forEach(el=>observer.observe(el));
}
function initCarousel(){
 const stage=qs('#v9Frames');if(!stage)return;
 const cards=all('.v9-frame',stage),count=qs('#v9FrameCount');let current=1;
 const sync=()=>{cards.forEach((card,i)=>{const active=i===current;card.classList.toggle('v9-active',active);const narrow=matchMedia('(max-width:760px)').matches;card.tabIndex=(narrow&&!active)?-1:0;card.setAttribute('aria-hidden',String(narrow&&!active))});count.textContent=`${String(current+1).padStart(2,'0')} / ${String(cards.length).padStart(2,'0')}`};
 const move=(step)=>{current=(current+step+cards.length)%cards.length;sync()};
 qs('#v9FramePrev')?.addEventListener('click',()=>move(-1));qs('#v9FrameNext')?.addEventListener('click',()=>move(1));
 stage.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();move(e.key==='ArrowLeft'?-1:1);cards[current].focus()}});
 let origin=null;stage.addEventListener('touchstart',e=>{origin={x:e.touches[0].clientX,y:e.touches[0].clientY}},{passive:true});
 stage.addEventListener('touchend',e=>{if(!origin)return;let dx=e.changedTouches[0].clientX-origin.x,dy=e.changedTouches[0].clientY-origin.y;if(Math.abs(dx)>65&&Math.abs(dx)>Math.abs(dy)*1.25)move(dx<0?1:-1);origin=null},{passive:true});
 addEventListener('resize',sync,{passive:true});sync();
}
function initLightboxZoom(){
 const button=qs('#v9LightboxZoom'),viewer=qs('#lightbox'),photo=qs('#lightboxImage');if(!button||!photo||!viewer)return;
 const reset=()=>{photo.classList.remove('v9-zoomed');button.textContent='ZOOM +';button.setAttribute('aria-pressed','false')};
 button.addEventListener('click',()=>{const on=photo.classList.toggle('v9-zoomed');button.textContent=on?'FIT PHOTO −':'ZOOM +';button.setAttribute('aria-pressed',String(on))});
 for(const id of ['#lightboxClose','#lightboxPrev','#lightboxNext'])qs(id)?.addEventListener('click',reset);
 document.addEventListener('keydown',e=>{if(viewer.hidden)return;if(e.key.toLowerCase()==='z'){e.preventDefault();button.click()}else if(e.key==='Escape')reset()});
}
function initPageArt(){
 // Existing transactional forms, menus and system statuses are never intercepted.
 // A document-level intersection observer adds an accessible, CSS-only entrance treatment to actual image sections.
 if(motionOff()||!('IntersectionObserver' in window))return;
 const sceneTargets=all('.v4-hero .hero-content,.v4-intro-copy,.v4-coffee-top,.v4-story-copy,.v4-gallery-heading');
 const watcher=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('v9-section-in');watcher.unobserve(e.target)}}),{threshold:.08});
 sceneTargets.forEach(el=>watcher.observe(el));
}
function initMenuCategoryRail(){
 if(document.body.dataset.page!=='menu')return;
 const menu=qs('#menuCategory'),list=qs('#menuItems');if(!menu||!list)return;
 let applied=false;const attach=()=>{
  if(applied||menu.options.length<3)return;
  applied=true;const categories=[...menu.options].filter(x=>x.value);
  const rail=document.createElement('section');rail.className='v9-category-section';rail.setAttribute('aria-label','Browse menu by category');
  const h=document.createElement('h2');h.textContent='Find your flavour.';
  const hint=document.createElement('p');hint.textContent='A closer look at the Wongdhen menu. Explore a collection, or see everything.';
  const buttons=document.createElement('div');buttons.className='v9-category-rail';buttons.setAttribute('role','group');buttons.setAttribute('aria-label','Food and drink categories');
  rail.append(h,hint,buttons);
  const items=[{value:'',text:'EVERYTHING'},...categories.slice(0,11).map(x=>({value:x.value,text:x.textContent}))];
  const drawActive=()=>all('button',buttons).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.category===menu.value)));
  for(const [index,item] of items.entries()){
    const b=document.createElement('button');b.type='button';b.className='v9-category-chip';b.dataset.category=item.value;
    const number=document.createElement('small');number.textContent=String(index+1).padStart(2,'0');
    const label=document.createElement('span');label.textContent=item.text;
    const arrow=document.createElement('i');arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');
    b.append(number,label,arrow);b.addEventListener('click',()=>{menu.value=item.value;menu.dispatchEvent(new Event('change',{bubbles:true}));drawActive()});buttons.append(b);
  }
  menu.addEventListener('change',drawActive);drawActive();
  const target=qs('.v6-menu-list')?.parentElement||list.parentElement;
  target?.insertBefore(rail,list);
  watcher.disconnect();
 };
 const watcher=new MutationObserver(attach);watcher.observe(menu,{childList:true});attach();
}
function initHeroAtmosphere(){
 const hero=qs('.v4-hero');if(!hero||motionOff()||coarse.matches)return;
 let raf=0,tx=0,ty=0;
 hero.addEventListener('pointermove',e=>{
  const rect=hero.getBoundingClientRect();tx=(e.clientX-rect.left)/rect.width*100;ty=(e.clientY-rect.top)/rect.height*100;
  if(!raf)raf=requestAnimationFrame(()=>{raf=0;hero.style.setProperty('--v9-hero-x',tx.toFixed(2)+'%');hero.style.setProperty('--v9-hero-y',ty.toFixed(2)+'%')});
 },{passive:true});
 hero.addEventListener('pointerleave',()=>{hero.style.removeProperty('--v9-hero-x');hero.style.removeProperty('--v9-hero-y')},{passive:true});
}
function initMagneticActions(){
 if(motionOff()||coarse.matches)return;
 for(const el of all('.hero-actions .v4-pill,.v9-atelier-links a,.v9-manifesto>a')){
  el.classList.add('v9-magnetic');let raf=0,x=0,y=0;
  el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();x=(e.clientX-r.left-r.width/2)*.045;y=(e.clientY-r.top-r.height/2)*.06;
   if(!raf)raf=requestAnimationFrame(()=>{raf=0;el.style.setProperty('--v9-mx',Math.max(-5,Math.min(5,x))+'px');el.style.setProperty('--v9-my',Math.max(-4,Math.min(4,y))+'px')})},{passive:true});
  el.addEventListener('pointerleave',()=>{el.style.removeProperty('--v9-mx');el.style.removeProperty('--v9-my')},{passive:true});
 }
}
function initReelProgress(){
 if(body.dataset.page!=='reels')return;
 const root=qs('#v7ReelRoot');if(!root)return;
 let current=null,cleanup=()=>{};
 const sync=()=>{const video=qs('video',root);if(video===current)return;cleanup();current=video;if(!video)return;
  const line=document.createElement('div');line.className='v9-reel-progress';line.setAttribute('aria-hidden','true');
  const fill=document.createElement('i');line.append(fill);video.parentElement.append(line);
  const update=()=>{const r=video.duration?video.currentTime/video.duration:0;fill.style.transform=`scaleX(${Math.min(1,Math.max(0,r))})`};
  video.addEventListener('timeupdate',update);video.addEventListener('loadedmetadata',update);
  cleanup=()=>{video.removeEventListener('timeupdate',update);video.removeEventListener('loadedmetadata',update);line.remove()};
 };
 const observer=new MutationObserver(sync);observer.observe(root,{childList:true,subtree:false});sync();
}
function initBrand3D(){
 const canvas=qs('#v9Sculpture'),stage=qs('.v9-sculpture-stage');
 if(!canvas||!stage||motionOff())return;
 if(coarse.matches&&innerWidth<600)return; // mobile has authored CSS-dimensional fallback artwork
 let gl;try{gl=canvas.getContext('webgl',{alpha:true,antialias:true,depth:true,premultipliedAlpha:false})}catch{}
 if(!gl){canvas.dataset.v9Status='fallback';return}
 function compile(type,source){const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){const msg=gl.getShaderInfoLog(shader);gl.deleteShader(shader);throw new Error(msg)}return shader}
 const vert=`
 attribute vec3 position;attribute vec3 normal;
 uniform float spin;uniform float tilt;uniform float scrollAngle;uniform float ratio;
 varying vec3 vNormal;varying vec3 vPos;
 void main(){
  float sy=sin(spin),cy=cos(spin),sx=sin(tilt+scrollAngle),cx=cos(tilt+scrollAngle);
  mat3 ry=mat3(cy,0.0,-sy,0.0,1.0,0.0,sy,0.0,cy);
  mat3 rx=mat3(1.0,0.0,0.0,0.0,cx,sx,0.0,-sx,cx);
  vec3 p=rx*ry*position;
  vNormal=normalize(rx*ry*normal);vPos=p;
  float depth=4.9-p.z;
  float factor=2.45/depth;
  gl_Position=vec4(p.x*factor/ratio,p.y*factor,0.45+(p.z/14.0),1.0);
 }`;
 const frag=`
 precision mediump float;varying vec3 vNormal;varying vec3 vPos;
 void main(){
   vec3 n=normalize(vNormal);
   vec3 light1=normalize(vec3(-.53,.71,1.0)),light2=normalize(vec3(.81,-.15,.48));
   float lambert=max(dot(n,light1),0.0);
   float fill=max(dot(n,light2),0.0);
   float rim=pow(1.0-abs(n.z),2.6);
   float spec=pow(max(dot(reflect(-light1,n),vec3(0.0,0.0,1.0)),0.0),19.0);
   vec3 shadow=vec3(.31,.137,.075),bronze=vec3(.68,.378,.20),gold=vec3(.98,.755,.49);
   vec3 color=mix(shadow,bronze,clamp(lambert*.9+fill*.26+.14,0.0,1.0));
   color=mix(color,gold,clamp(spec*.85+rim*.31,0.0,1.0));
   color+=vec3(.08,.053,.021)*fill;
   gl_FragColor=vec4(color,1.0);
 }`;
 let program,posBuffer,normBuffer,idxBuffer,indexCount=0;
 try{
  program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vert));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,frag));gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
  const n=240,m=18,vertices=[],normals=[],indices=[];const PI=Math.PI;
  const curve=t=>{let a=2*t,b=3*t,r=1.23+.38*Math.cos(b);return [r*Math.cos(a),r*Math.sin(a),.52*Math.sin(b)]};
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const unit=a=>{let len=Math.hypot(...a)||1;return a.map(v=>v/len)};
  for(let i=0;i<=n;i++){
    const t=i/n*PI*2, center=curve(t),ahead=curve(t+.003),behind=curve(t-.003);
    const tangent=unit(ahead.map((v,k)=>v-behind[k]));
    const guide=Math.abs(tangent[2])>.89?[0,1,0]:[0,0,1];
    const normal=unit(cross(tangent,guide)),side=unit(cross(tangent,normal));
    for(let j=0;j<=m;j++){
      let a=j/m*PI*2;let dir=normal.map((v,k)=>v*Math.cos(a)+side[k]*Math.sin(a));
      vertices.push(...center.map((v,k)=>v+dir[k]*.245));normals.push(...dir);
    }
  }
  for(let i=0;i<n;i++)for(let j=0;j<m;j++){
    const a=i*(m+1)+j,b=a+(m+1);indices.push(a,a+1,b,b,a+1,b+1);
  }
  indexCount=indices.length;
  posBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,posBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
  normBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,normBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(normals),gl.STATIC_DRAW);
  idxBuffer=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,idxBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
 }catch(e){canvas.dataset.v9Status='fallback';if(program)gl.deleteProgram(program);return}
 const attach=(buffer,attribute)=>{let location=gl.getAttribLocation(program,attribute);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.vertexAttribPointer(location,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(location)};
 gl.useProgram(program);attach(posBuffer,'position');attach(normBuffer,'normal');gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,idxBuffer);
 gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.clearColor(0,0,0,0);
 const uniform={spin:gl.getUniformLocation(program,'spin'),tilt:gl.getUniformLocation(program,'tilt'),scrollAngle:gl.getUniformLocation(program,'scrollAngle'),ratio:gl.getUniformLocation(program,'ratio')};
 let visible=false,raf=0,angle=0,pointerX=0,pointerY=0,targetX=0,targetY=0,scrollFactor=0,drag=false,lastX=0,dragAngle=0,prevTime=0;
 const resize=()=>{const d=Math.min(devicePixelRatio||1,1.6);canvas.width=Math.max(2,Math.round(canvas.clientWidth*d));canvas.height=Math.max(2,Math.round(canvas.clientHeight*d));gl.viewport(0,0,canvas.width,canvas.height)};
 const observer=new IntersectionObserver(es=>{visible=!!es[0]?.isIntersecting;if(visible){prevTime=0;start()}else stop()},{threshold:.07});
 const stop=()=>{if(raf){cancelAnimationFrame(raf);raf=0}};
 const start=()=>{if(!raf&&visible&&!document.hidden&&!motionOff())raf=requestAnimationFrame(render)};
 const render=time=>{
  raf=0;if(!visible||document.hidden||motionOff())return;
  if(!canvas.width||!canvas.height)resize();
  let dt=prevTime?Math.min((time-prevTime)/1000,.06):0;prevTime=time;angle+=dt*.23;
  pointerX+=(targetX-pointerX)*.04;pointerY+=(targetY-pointerY)*.04;
  gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.uniform1f(uniform.spin,angle+pointerX*.21+dragAngle);
  gl.uniform1f(uniform.tilt,.21+pointerY*.17);
  gl.uniform1f(uniform.scrollAngle,scrollFactor*.52);
  gl.uniform1f(uniform.ratio,canvas.width/canvas.height);
  gl.drawElements(gl.TRIANGLES,indexCount,gl.UNSIGNED_SHORT,0);
  start();
 };
 function move(e){const box=stage.getBoundingClientRect();targetX=((e.clientX-box.left)/box.width-.5)*2;targetY=((e.clientY-box.top)/box.height-.5)*2;
  if(drag){dragAngle+=(e.clientX-lastX)*.01;lastX=e.clientX}}
 stage.addEventListener('pointermove',move,{passive:true});stage.addEventListener('pointerleave',()=>{targetX=0;targetY=0},{passive:true});
 canvas.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'||e.pointerType==='pen'){drag=true;lastX=e.clientX;canvas.setPointerCapture(e.pointerId)}});
 canvas.addEventListener('pointerup',()=>{drag=false});canvas.addEventListener('pointercancel',()=>{drag=false});
 function onScroll(){const r=stage.getBoundingClientRect();scrollFactor=Math.max(-1,Math.min(1,(innerHeight/2-r.top-r.height/2)/Math.max(1,innerHeight)))};
 addEventListener('scroll',onScroll,{passive:true});addEventListener('resize',resize,{passive:true});
 document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
 reduced.addEventListener?.('change',()=>motionOff()?stop():start());
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();stop();stage.classList.remove('v9-webgl-ready');canvas.dataset.v9Status='lost'});
 onScroll();resize();canvas.dataset.v9Status='ready';stage.classList.add('v9-webgl-ready');observer.observe(stage);
 window.WongdhenV9=Object.freeze({renderMode:'webgl',sculptureVertices:241*19,sculptureTriangles:indexCount/3});
}
function init(){initTheme();initScrollHeader();initReveals();initCarousel();initLightboxZoom();initPageArt();initMenuCategoryRail();initHeroAtmosphere();initMagneticActions();initReelProgress();initBrand3D();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
