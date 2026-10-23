/* Wongdhen V26 PWA. No customer, booking, authentication or owner responses cached. */
const VERSION='wc-v37-living-house-1';
const SHELL=['/offline','/static/v26/icon-192.png','/static/v26/icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(VERSION).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const key of await caches.keys())if(key.startsWith('wc-v')&&key!==VERSION)await caches.delete(key);await self.clients.claim();})()));
self.addEventListener('fetch', event=>{
 const req=event.request, url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin)return;
 // Revalidate code online; never prefer a cached script over current files.
 // Exact content-fingerprinted URLs retain offline support for the public menu.
 // No authenticated HTML or API responses enter this cache.
 if(url.pathname.startsWith('/static/') && /\.(?:js|css)$/.test(url.pathname)){
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     try{
       const response=await fetch(req,{cache:'no-cache'});
       if(response.ok&&!response.headers.has('set-cookie'))await cache.put(req,response.clone());
       return response;
     }catch(error){return await cache.match(req)||Response.error();}
   })());return;
 }
 // A deliberately tiny allowlist: no cookies or private account/booking/admin responses ever cached.
 if(url.pathname==='/api/menu' && !url.search) {
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     try{
       const r=await fetch(req,{cache:'no-store'});
       if(r.ok && !r.headers.has('set-cookie')){
         const data=await r.clone().json();
         const snapshot={...data,offline_snapshot:true,snapshot_saved_at:new Date().toISOString(),
           offline_notice:'Cached menu snapshot. Prices and availability must be verified directly with the café.'};
         await cache.put('/api/menu',new Response(JSON.stringify(snapshot),{headers:{'Content-Type':'application/json'}}));
       }
       return r;
     }catch(err){return await cache.match('/api/menu')||new Response(JSON.stringify({items:[],offline_snapshot:true,offline_notice:'No menu has been cached on this device.'}),{status:503,headers:{'Content-Type':'application/json'}});}
   })());return;
 }
 if(url.pathname==='/menu'){
   event.respondWith((async()=>{try{const r=await fetch(req);if(r.ok&&!r.headers.has('set-cookie')){const cache=await caches.open(VERSION);await cache.put('/menu',r.clone());}return r;}catch(err){return await(await caches.open(VERSION)).match('/menu')||await caches.match('/offline');}})());return;
 }
 if(url.pathname.startsWith('/static/') || SHELL.includes(url.pathname)){
   event.respondWith((async()=>{const cache=await caches.open(VERSION);const stored=await cache.match(req);if(stored)return stored;try{const r=await fetch(req);if(r.ok&&!r.headers.has('set-cookie'))await cache.put(req,r.clone());return r;}catch(err){return Response.error();}})());
 }
});
