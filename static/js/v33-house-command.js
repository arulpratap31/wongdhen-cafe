/* Wongdhen V33 — House Command. Real records, progressive enhancement, no mock data. */
(() => {
  'use strict';
  if (document.body.dataset.page !== 'admin') return;
  const esc = input => String(input ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const panel = () => document.getElementById('adminTab');
  const active = id => !!document.querySelector(`.admin-actions [data-tab="${id}"].active`);
  const num = n => Number(n || 0).toLocaleString('en-IN');
  const dateText = s => s ? new Date(s.slice(0,10)+'T12:00:00').toLocaleDateString('en-IN',{month:'short',day:'numeric'}) : '—';
  const stamp = s => s ? esc(String(s).replace('T', ' ').slice(0,16)) : '—';
  const fetchJson = async url => {
    const res = await fetch(url, {credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'});
    if (!res.ok) throw new Error(res.status===401?'Your session has expired. Please sign in again.':res.status===403?'This section requires owner access.':'Unable to retrieve the latest records.');
    return res.json();
  };
  const error = (e, retry) => {const el=panel(); if(!el)return;el.replaceChildren();const box=document.createElement('div');box.className='v33-error';
    const head=document.createElement('h2');head.textContent='The connection needs attention.';
    const note=document.createElement('p');note.textContent=e?.message||'Unable to load this section';
    const btn=document.createElement('button');btn.type='button';btn.textContent='TRY AGAIN ↗';btn.addEventListener('click',retry);
    box.append(head,note,btn);el.append(box);};
  const go = target => document.querySelector(`.admin-actions [data-tab="${target}"]`)?.click();
  const card = (eyebrow,value,note,action) => `<article class="v33-metric"><span class="v33-metric-label">${esc(eyebrow)}</span><strong>${num(value)}</strong><p>${esc(note)}</p><button type="button" data-v33-go="${esc(action)}" aria-label="Open ${esc(action)} management">EXPLORE <span aria-hidden="true">↗</span></button></article>`;
  const eventHandlers = root => root.querySelectorAll('[data-v33-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.v33Go)));
  const digit = x => Number.isFinite(Number(x))?Number(x):0;
  let studioLoad = 0;
  async function studio(days=7) {
    const ticket=++studioLoad;
    const root=panel();if(!root)return;
    root.innerHTML='<div class="v33-loading" role="status"><span class="v33-spinner" aria-hidden="true"></span>Reading service records…</div>';
    try {
      const data=await fetchJson('/api/v33/admin/command?days='+days);
      if(!active('studio')||ticket!==studioLoad || !root.isConnected) return;
      const s=data.summary||{}, daily=data.daily||[], max=Math.max(1,...daily.map(x=>digit(x.count)));
      const ticks=daily.map((d,i) => `<div class="v33-chart-day" title="${esc(d.date)}: ${num(d.count)} reservations">
        <span class="v33-bar-count">${num(d.count)}</span><div class="v33-chart-track"><i style="--bar-height:${Math.max(0,Math.min(100,digit(d.count)/max*100))}%"></i></div>
        <span>${days===30?(i%5===0||i===29?dateText(d.date):''):dateText(d.date)}</span></div>`).join('');
      const times=(data.next_reservations||[]).map(b => `<tr><td><strong>${esc(b.reference)}</strong><small>${dateText(b.visit_at)} · ${esc(String(b.visit_at).slice(11,16))}</small></td><td>${esc(b.guest)}</td><td>${num(b.party_size)}</td><td><span class="v33-status" data-state="${esc(b.status)}">${esc(b.status)}</span></td></tr>`).join('');
      const checks=data.configuration||{};
      const attention=[
        ['New guest messages',s.new_enquiries,'inbox','Every enquiry deserves a follow-up.'],
        ['Unverified menu entries',s.menu_awaiting_approval,'menu','Review prices and published information.'],
        ['Reservation configuration',checks.booking_enabled&&checks.booking_owner_verified?'Ready':'Needs review','policy','Confirm hours, verification and the booking policy.']
      ];
      const activity=(data.activity||[]).map(a=>`<li><i aria-hidden="true"></i><div><strong>${esc(a.action)}</strong><small>${stamp(a.at)}</small></div></li>`).join('');
      root.innerHTML=`<div class="v33-command">
        <section class="v33-hero"><div class="v33-hero-copy"><span class="v33-eyebrow">WONGDHEN / THE PRIVATE HOUSE · ${esc(data.date)}</span><h2>Everything in its<br><em>right place.</em></h2><p>Your service, people and priorities—together. A considered, data-backed way to run the café.</p><div class="v33-hero-tools"><button type="button" data-v33-go="bookings">MANAGE RESERVATIONS <span>↗</span></button><button type="button" data-v33-go="inbox">OPEN GUEST INBOX <span>↗</span></button></div></div><div class="v33-hero-seal" aria-hidden="true">W<span>HOUSE COMMAND</span></div></section>
        <div class="v33-section-head"><div><span class="v33-eyebrow">01 / THE DAILY PICTURE</span><h3>At a glance</h3></div><div class="v33-toolbar"><label for="v33Range">SERVICE WINDOW</label><select id="v33Range"><option value="7" ${days===7?'selected':''}>Last 7 days</option><option value="14" ${days===14?'selected':''}>Last 14 days</option><option value="30" ${days===30?'selected':''}>Last 30 days</option></select><button type="button" id="v33Refresh" aria-label="Refresh command center">↻ REFRESH</button></div></div>
        <div class="v33-metrics">${card('Reservations in period',s.reservations_period,'All recorded statuses · '+days+' days','bookings')}${card('Visits scheduled today',s.reservations_today,'All statuses, including cancellations','calendar')}${card('Open guest enquiries',s.open_enquiries,'New and in-progress messages','inbox')}${card('Awaiting menu approval',s.menu_awaiting_approval,'Published entries requiring verification','menu')}</div>
        <div class="v33-data-grid"><section class="v33-surface v33-graph-panel"><div class="v33-card-title"><div><span class="v33-eyebrow">02 / RESERVATIONS</span><h3>Service rhythm</h3></div><span class="v33-quiet">${days}-DAY VIEW</span></div><div class="v33-chart" role="img" aria-label="Recorded reservation totals for each of the last ${days} days">${ticks}</div><p class="v33-fineprint">Includes pending, confirmed, cancelled and all other recorded statuses—not attendance or revenue.</p><div class="v33-legend">${Object.entries(data.status_totals||{}).map(([key,value])=>`<span>${esc(key.replace(/_/g,' '))} <b>${num(value)}</b></span>`).join('')||'<span>No reservations recorded during this period</span>'}</div></section>
          <section class="v33-surface v33-attention"><div class="v33-card-title"><div><span class="v33-eyebrow">03 / THE PRIORITY DESK</span><h3>Needs your attention</h3></div></div>${attention.map(([title,count,target,caption],idx)=>`<button type="button" class="v33-attention-row" data-v33-go="${esc(target)}"><span class="v33-attention-index">0${idx+1}</span><span><strong>${esc(title)}</strong><small>${esc(caption)}</small></span><b>${typeof count==='number'?num(count):esc(count)}</b><span aria-hidden="true">↗</span></button>`).join('')}</section></div>
        <div class="v33-data-grid v33-bottom-grid"><section class="v33-surface"><div class="v33-card-title"><div><span class="v33-eyebrow">04 / ARRIVALS AHEAD</span><h3>Upcoming reservations</h3></div><button type="button" class="v33-link" data-v33-go="bookings">VIEW ALL ↗</button></div><div class="v33-table-wrap"><table class="v33-table"><thead><tr><th>REFERENCE / TIME</th><th>GUEST</th><th>PARTY</th><th>STATE</th></tr></thead><tbody>${times||'<tr><td colspan="4">No non-cancelled reservations are scheduled in the next 8 days.</td></tr>'}</tbody></table></div></section>
          <section class="v33-surface"><div class="v33-card-title"><div><span class="v33-eyebrow">05 / ACCOUNTABILITY</span><h3>Recent actions</h3></div><button type="button" class="v33-link" data-v33-go="audit">AUDIT LOG ↗</button></div><ol class="v33-activity">${activity||'<li>No recorded administrative actions yet.</li>'}</ol></section></div>
        <p class="v33-disclaimer">${esc(data.disclaimer)} All details are restricted to the café owner.</p>
      </div>`;
      eventHandlers(root);root.querySelector('#v33Range').addEventListener('change',e=>studio(Number(e.target.value)));
      root.querySelector('#v33Refresh').addEventListener('click',()=>studio(days));
    }catch(e){if(active('studio')&&ticket===studioLoad)error(e,()=>studio(days));}
  }
  let inboxId=0;let inboxState={status:'all',q:'',offset:0};
  const statuses=['new','in_progress','replied','archived'];
  const option = (v,selected,label) => `<option value="${v}" ${v===selected?'selected':''}>${esc(label||v.replace('_',' '))}</option>`;
  async function inbox(adminWrite, patch={}) {
    const restoreFocus=Object.prototype.hasOwnProperty.call(patch,'q');
    inboxState={...inboxState,...patch}; const state={...inboxState};const id=++inboxId;
    const root=panel();if(!root)return;
    root.innerHTML='<div class="v33-loading" role="status"><span class="v33-spinner"></span>Opening guest correspondence…</div>';
    try{
      const query=new URLSearchParams({status:state.status,q:state.q,offset:String(state.offset),limit:'12'});
      const data=await fetchJson('/api/v33/admin/enquiries?'+query);
      if(id!==inboxId||!active('inbox'))return;
      const cards=data.items.map(item=>`<article class="v33-mail" data-id="${item.id}"><div class="v33-mail-top"><span>MESSAGE #${item.id} · ${stamp(item.received_at)}</span><span class="v33-status" data-state="${esc(item.status)}">${esc(item.status.replace('_',' '))}</span></div><h3>${esc(item.subject)}</h3><p class="v33-mail-name">${esc(item.name)} · <a href="mailto:${encodeURIComponent(item.email)}">${esc(item.email)}</a></p><p class="v33-mail-message">${esc(item.message)}</p><div class="v33-mail-footer"><label for="v33-status-${item.id}">FOLLOW-UP STATUS</label><select id="v33-status-${item.id}" data-current="${esc(item.status)}" data-change="${item.id}">${statuses.map(s=>option(s,item.status)).join('')}</select><span role="status" class="v33-mail-result"></span></div></article>`).join('');
      root.innerHTML=`<div class="v33-inbox"><header class="v33-inbox-hero"><div><span class="v33-eyebrow">WONGDHEN / GUEST RELATIONS</span><h2>Every guest<br><em>deserves a reply.</em></h2><p>Search, review, and follow up on genuine enquiries. Changes are written to the audit trail.</p></div><span class="v33-inbox-tally">${num(data.total)}<small>MATCHING MESSAGES</small></span></header><div class="v33-inbox-toolbar"><label>SEARCH MESSAGES<input id="v33EnquirySearch" type="search" maxlength="100" value="${esc(state.q)}" placeholder="Guest, email or subject"></label><label>STATUS<select id="v33EnquiryFilter">${['all',...statuses].map(s=>option(s,state.status,s==='all'?'All messages':s)).join('')}</select></label><a class="v33-export" href="/api/v33/admin/enquiries.csv?status=${encodeURIComponent(state.status)}&q=${encodeURIComponent(state.q)}" download>EXPORT CSV ↓</a></div><div class="v33-inbox-list">${cards||'<div class="v33-empty">No enquiries match these filters.</div>'}</div><footer class="v33-pagination"><span>${data.total?`${data.offset+1}–${Math.min(data.offset+data.limit,data.total)}`:'0'} of ${num(data.total)} messages</span><div><button type="button" data-v33-page="previous" ${state.offset<=0?'disabled':''}>← PREVIOUS</button><button type="button" data-v33-page="next" ${state.offset+data.limit>=data.total?'disabled':''}>NEXT →</button></div></footer><p class="v33-disclaimer">Guest details are sensitive. Export only when required; store files securely and follow your retention policy.</p></div>`;
      const search=root.querySelector('#v33EnquirySearch');if(restoreFocus){search.focus({preventScroll:true});search.setSelectionRange(search.value.length,search.value.length);}let debounce;
      search.addEventListener('input',()=>{clearTimeout(debounce);const term=search.value;debounce=setTimeout(()=>inbox(adminWrite,{q:term,offset:0}),400)});
      root.querySelector('#v33EnquiryFilter').addEventListener('change',e=>inbox(adminWrite,{status:e.target.value,offset:0}));
      root.querySelectorAll('[data-v33-page]').forEach(b=>b.addEventListener('click',()=>inbox(adminWrite,{offset:Math.max(0,state.offset+(b.dataset.v33Page==='next'?12:-12))})));
      root.querySelectorAll('[data-change]').forEach(el=>el.addEventListener('change',async e=>{
        const input=e.target, original=input.dataset.current, target=input.value;
        const wrap=input.closest('.v33-mail'), result=wrap.querySelector('.v33-mail-result');
        input.disabled=true;result.textContent='Saving…';
        try{
          await adminWrite('/api/v33/admin/enquiries/'+input.dataset.change,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:target,expected_status:original})});
          input.dataset.current=target;result.textContent='Updated & logged';wrap.querySelector('.v33-status').dataset.state=target;wrap.querySelector('.v33-status').textContent=target.replace('_',' ');
          if(inboxState.status!=='all'&&target!==inboxState.status)inbox(adminWrite);
        }catch(err){input.value=original;result.textContent=err.message||'Unable to save';}finally{input.disabled=false;}
      }));
    }catch(e){if(active('inbox')&&id===inboxId)error(e,()=>inbox(adminWrite));}
  }
  let auditId=0;let auditState={q:'',offset:0};
  async function audit(stateChange={}) {
    auditState={...auditState,...stateChange};const state={...auditState};const id=++auditId, root=panel();if(!root)return;
    root.innerHTML='<div class="v33-loading" role="status">Reading the owner activity trail…</div>';
    try{
      const params=new URLSearchParams({q:state.q,offset:String(state.offset),limit:'25'});
      const data=await fetchJson('/api/v33/admin/audit?'+params);
      if(id!==auditId||!active('audit'))return;
      const rows=data.items.map(a=>`<tr><td><span class="v33-monospaced">#${a.id}</span></td><td><strong>${esc(a.action)}</strong></td><td>${esc(a.detail)}</td><td>${stamp(a.at)}</td></tr>`).join('');
      root.innerHTML=`<section class="v33-audit"><div class="v33-audit-head"><div><span class="v33-eyebrow">WONGDHEN / AUDIT & ACCOUNTABILITY</span><h2>The house remembers.</h2><p>Read-only history of recorded administrative actions.</p></div><span class="v33-audit-count">${num(data.total)} EVENTS</span></div><label class="v33-audit-search">SEARCH ACTION TYPE<input id="v33AuditSearch" type="search" maxlength="80" value="${esc(state.q)}" placeholder="menu, staff, enquiry…"></label><div class="v33-table-wrap"><table class="v33-table"><thead><tr><th>ID</th><th>ACTION</th><th>DETAIL</th><th>RECORDED</th></tr></thead><tbody>${rows||'<tr><td colspan="4">No matching recorded events.</td></tr>'}</tbody></table></div><footer class="v33-pagination"><span>${data.total?`${data.offset+1}–${Math.min(data.offset+data.limit,data.total)}`:'0'} of ${num(data.total)} entries</span><div><button type="button" id="v33AuditPrev" ${state.offset<=0?'disabled':''}>← PREVIOUS</button><button type="button" id="v33AuditNext" ${state.offset+data.limit>=data.total?'disabled':''}>NEXT →</button></div></footer></section>`;
      let timer;const field=root.querySelector('#v33AuditSearch');field.addEventListener('input',()=>{clearTimeout(timer);const q=field.value;timer=setTimeout(()=>audit({q,offset:0}),400)});
      root.querySelector('#v33AuditPrev').addEventListener('click',()=>audit({offset:Math.max(0,state.offset-25)}));
      root.querySelector('#v33AuditNext').addEventListener('click',()=>audit({offset:state.offset+25}));
    }catch(e){if(active('audit')&&id===auditId)error(e,()=>audit());}
  }
  window.WongdhenV33={studio,inbox,audit};
})();
