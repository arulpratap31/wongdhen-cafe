/* V19 Signature — global owner-managed themes and reliable visual appearance. */
(()=>{'use strict';if(document.documentElement.dataset.v21==='studio')return;
const themes={burgundy:{name:'BLACK BURGUNDY',tone:'#160d12'},emerald:{name:'MIDNIGHT EMERALD',tone:'#0a1715'},ivory:{name:'IVORY GOLD',tone:'#f7f1e8'},terracotta:{name:'SANDSTONE TERRACOTTA',tone:'#f4ece1'}};
const root=document.documentElement;
const saved=()=>{try{return localStorage.getItem('wongdhen-v19-theme')}catch{return null}};
let policy={default_theme:'burgundy',allow_visitor_switch:true};
const apply=(name,{persist=false}={})=>{
 if(!themes[name])name='burgundy';root.dataset.siteTheme=name;root.dataset.siteMode=['burgundy','emerald'].includes(name)?'dark':'light';
 const meta=document.querySelector('meta[name="theme-color"]');if(meta)meta.setAttribute('content',themes[name].tone);
 document.querySelectorAll('[data-v19-theme]').forEach(btn=>{btn.setAttribute('aria-pressed',String(btn.dataset.v19Theme===name))});
 const display=document.querySelector('#v19ThemeCurrent');if(display)display.textContent=themes[name].name;
 if(persist){try{localStorage.setItem('wongdhen-v19-theme',name)}catch{}}
};
const configure=cfg=>{
 if(!themes[cfg.default_theme])return;
 policy={default_theme:cfg.default_theme,allow_visitor_switch:!!cfg.allow_visitor_switch};
 const dock=document.querySelector('.v19-appearance-dock');if(dock)dock.hidden=!policy.allow_visitor_switch;
 const preference=policy.allow_visitor_switch?saved():null;
 apply(preference&&themes[preference]?preference:policy.default_theme);
};
const load=async()=>{try{const r=await fetch('/api/v19/appearance',{cache:'no-store'});if(r.ok)configure(await r.json());else apply(root.dataset.siteTheme)}catch{apply(root.dataset.siteTheme)}};
function adminPanel(adminFetch){
 const host=document.querySelector('#adminTab');if(!host)return;
 const rows=Object.entries(themes).map(([key,value])=>`<label class="v19-admin-choice"><input type="radio" name="default_theme" value="${key}" ${policy.default_theme===key?'checked':''}/><span class="v19-admin-swatch v19-admin-${key}" aria-hidden="true"></span><span><strong>${value.name}</strong><small>${['burgundy','emerald'].includes(key)?'DARK':'LIGHT'} · complete website palette</small></span></label>`).join('');
 host.innerHTML=`<div class="v19-admin-appearance"><p class="v13-small-label">OWNER SETTINGS / APPEARANCE</p><h2>Set the mood.</h2><p>Choose the default theme for new visitors. Visitors may optionally keep their own appearance preference on their device. This setting changes real site colors, not booking or menu records.</p><form id="v19AdminThemeForm"><fieldset><legend>DEFAULT WEBSITE THEME</legend><div class="v19-admin-options">${rows}</div></fieldset><label class="v19-admin-allow"><input type="checkbox" name="allow_visitor_switch" ${policy.allow_visitor_switch?'checked':''}/> Allow visitors to change the palette</label><button type="submit" class="submit-button">SAVE WEBSITE APPEARANCE →</button><p role="status" id="v19AdminThemeStatus" aria-live="polite"></p></form></div>`;
 const form=host.querySelector('form');form.addEventListener('submit',async event=>{event.preventDefault();const status=host.querySelector('#v19AdminThemeStatus');status.textContent='Saving…';const data={default_theme:form.elements.default_theme.value,allow_visitor_switch:form.elements.allow_visitor_switch.checked};try{const result=await adminFetch('/api/admin/appearance',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});configure(result);status.textContent='Saved to the website database. New visitors will see '+themes[result.default_theme].name+'.';}catch(e){status.textContent='Could not save: '+e.message}});
}
window.WongdhenV19={adminPanel,applyTheme:apply,loadAppearance:load};
const dock=document.querySelector('.v19-appearance-dock');
const toggle=document.querySelector('#v19AppearanceToggle');
const options=document.querySelector('#v19AppearanceOptions');
const setOpen=open=>{if(!toggle||!options)return;options.hidden=!open;toggle.setAttribute('aria-expanded',String(open));dock?.classList.toggle('v19-open',open)};
toggle?.addEventListener('click',()=>setOpen(toggle.getAttribute('aria-expanded')!=='true'));
dock?.addEventListener('click',event=>{const button=event.target.closest('button[data-v19-theme]');if(button&&policy.allow_visitor_switch){apply(button.dataset.v19Theme,{persist:true});setOpen(false);toggle?.focus()}});
document.addEventListener('pointerdown',event=>{if(dock&&!dock.contains(event.target))setOpen(false)});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&toggle?.getAttribute('aria-expanded')==='true'){setOpen(false);toggle.focus()}});
window.addEventListener('storage',event=>{if(event.key==='wongdhen-v19-theme'&&policy.allow_visitor_switch&&themes[event.newValue])apply(event.newValue)});
apply(root.dataset.siteTheme||'burgundy');load();
})();
