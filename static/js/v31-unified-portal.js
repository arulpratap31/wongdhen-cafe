/* V31 unified local portal: accessible administrative presentation helpers only.
   All operations still run through the existing authenticated API and role checks. */
(() => {
  'use strict';
  if (document.body.dataset.page !== 'admin') return;
  const esc = s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const origin = 'http://127.0.0.1:8765';
  function addLoginEnhancement(){
    const form = document.querySelector('#adminLogin');
    if (!form || form.dataset.v31Enhanced) return;
    form.dataset.v31Enhanced = 'true';
    const password = form.querySelector('input[type=password]');
    if (password) {
      const toggle = document.createElement('button');
      toggle.className='v31-password-toggle';toggle.type='button';toggle.setAttribute('aria-label','Show password');
      toggle.setAttribute('aria-pressed','false');toggle.textContent='SHOW PASSWORD';
      password.insertAdjacentElement('afterend', toggle);
      toggle.addEventListener('click', () => {
        const show=password.type==='password';password.type=show?'text':'password';
        toggle.textContent=show?'HIDE PASSWORD':'SHOW PASSWORD';
        toggle.setAttribute('aria-label',show?'Hide password':'Show password');
        toggle.setAttribute('aria-pressed',String(show));password.focus();
      });
    }
    const status = document.createElement('div');status.className='v31-login-access';
    status.innerHTML=`<span class="v31-portal-label">ROLE-BASED TEAM PORTALS · ${esc(origin)}</span><p>Staff accounts use your café-issued credentials. Customer Google accounts are separate and available at <a href="/account">My Wongdhen</a> once Google Cloud is configured.</p><p>Need staff access? Ask the café owner to create an account. Never share an owner's password.</p>`;
    form.insertAdjacentElement('afterend',status);
  }
  function refresh(){addLoginEnhancement();}
  const target=document.getElementById('app');
  if(!target)return;
  // App is dynamically replaced on successful staff login; attach enhancements at both stages.
  let scheduled=false;
  new MutationObserver(()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;refresh();});}).observe(target,{childList:true,subtree:true});
  refresh();
})();
