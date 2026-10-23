/* Wongdhen V3 — real, owner-controlled reservation UX. No invented slots. */
const V3='/api/v3';
const fmt=key=>key.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const reqJSON=(method,obj)=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});
const formObject=form=>Object.fromEntries(new FormData(form));
const inputDate=()=>{const p=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());const get=x=>p.find(a=>a.type===x).value;return `${get('year')}-${get('month')}-${get('day')}`;};

async function v3Reservations(){
  app.innerHTML=genericHero('BOOK A TABLE','YOUR TABLE<br/>AT WONGDHEN.','Choose an available slot based on the café’s verified seating configuration.')+
  `<section class="booking-shell"><div id="bookingApp" class="booking-card" aria-live="polite">Checking restaurant booking configuration…</div></section>`;
  const root=$('#bookingApp');
  try{
    const p=await api(`${V3}/booking/config`);
    if(!p.enabled){root.innerHTML=`<div class="section-tag">RESERVATIONS · NOT YET LIVE</div><h2>Reservations will open here.</h2><p>${safe(p.note)}</p><p>For current enquiries, please contact the café directly. No booking has been made.</p><a href="/contact" class="submit-button booking-inline-link">CONTACT WONGDHEN ↗</a>`;return;}
    root.innerHTML=`<div class="booking-intro"><span class="section-tag">SELECT AN AVAILABLE TIME</span><p>Times shown in India Standard Time (Asia/Kolkata). All submissions are <b>requests pending staff confirmation</b>. Email notifications are not yet configured.</p></div>
    <form id="bookingForm" class="booking-form">
      <div class="booking-fields"><label>Date<input name="visit_date" id="bookingDate" type="date" required min="${inputDate()}" /></label>
      <label>Number of guests<select name="party_size" id="bookingParty">${Array.from({length:Math.min(30,p.max_party_size)},(_,i)=>`<option value="${i+1}" ${i===1?'selected':''}>${i+1} ${i===0?'guest':'guests'}</option>`).join('')}</select></label></div>
      <fieldset class="booking-slot-fieldset"><legend>Available slots</legend><div id="bookingSlots" class="booking-slots">Choose a date to check availability.</div></fieldset><section id="v7TableZone" class="v7-table-zone" aria-live="polite"></section>
      <div class="booking-fields"><label>Full name<input name="name" minlength="2" maxlength="120" autocomplete="name" required/></label><label>Email<input name="email" type="email" maxlength="200" autocomplete="email" required/></label><label>Phone number<input name="phone" type="tel" maxlength="30" autocomplete="tel" required/></label><label>Optional notes<textarea name="notes" maxlength="500" rows="2" placeholder="Relevant accessibility or seating requests"></textarea></label></div>
      <label class="booking-consent"><input name="consent" type="checkbox" required/> I agree to the café storing my details to handle this reservation request.</label>
      <input name="website" tabindex="-1" aria-hidden="true" style="display:none"/>
      <button type="submit" class="submit-button">REQUEST RESERVATION ↗</button><p id="bookingResult" role="status" aria-live="polite"></p>
    </form><p class="booking-footnote">A request does not guarantee a table. The café must approve it before it is confirmed.</p>`;
    const f=$('#bookingForm'), slots=$('#bookingSlots'),result=$('#bookingResult');let selected='';let selectedTableId=null;window.WongdhenV4?.initBooking(f,p);
    $('#bookingDate').value=inputDate();
    const attachWaitlist=()=>{const b=slots.querySelector('.waitlist-trigger');if(!b)return;b.onclick=async()=>{if(!f.reportValidity())return;const data=formObject(f);try{const d=await api(`${V3}/booking/waitlist`,reqJSON('POST',{visit_date:data.visit_date,preferred_time:'',party_size:Number(data.party_size),name:data.name,email:data.email,phone:data.phone,consent:f.elements.consent.checked}));root.innerHTML=`<h2>Waitlist request received.</h2><p>Reference ${safe(d.reference)}</p><p>${safe(d.message)} Staff notifications are not yet configured.</p><a href="/visit" class="booking-inline-link">VISIT INFORMATION ↗</a>`;}catch(e){result.textContent=e.message}}};
    const update=async()=>{
      window.v7InvalidateTables?.();selected='';selectedTableId=null;const tableZone=$('#v7TableZone');if(tableZone)tableZone.replaceChildren();slots.innerHTML='<span class="v4-slot-loading" role="status">Checking live availability…</span>';
      try{
        const d=await api(`${V3}/booking/availability?visit_date=${encodeURIComponent(f.elements.visit_date.value)}&party_size=${f.elements.party_size.value}`);
        if(!d.slots.length){slots.innerHTML='No bookable times remain for this date. <button type="button" class="waitlist-trigger">JOIN WAITLIST ↗</button>';attachWaitlist();return;}
        slots.innerHTML=d.slots.map(s=>`<button type="button" class="booking-slot" data-time="${safe(s.time)}" ${s.available?'':'disabled'} aria-pressed="false">${safe(s.time)} ${s.available?'':'· Full'}</button>`).join('');
        slots.querySelectorAll('button:not([disabled])').forEach(b=>b.onclick=()=>{selected=b.dataset.time;slots.querySelectorAll('button.booking-slot').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b))});window.v7TablesForBooking?.(f,b.dataset.time,tableId=>{selectedTableId=tableId})});if(d.slots.every(x=>!x.available)){slots.insertAdjacentHTML('beforeend','<p>All available tables are already requested for these times.</p><button type="button" class="waitlist-trigger">JOIN WAITLIST ↗</button>');attachWaitlist();}
      }catch(e){slots.textContent=e.message}
    };
    $('#bookingDate').onchange=update;$('#bookingParty').onchange=update;await update();window.WongdhenV4?.refreshBookingStage();
    f.onsubmit=async e=>{
      e.preventDefault();result.textContent='';
      if(!selected){result.textContent='Select an available time.';return;}
      const payload={...formObject(f),party_size:Number(f.elements.party_size.value),visit_time:selected,table_id:selectedTableId,consent:f.elements.consent.checked};
      const btn=f.querySelector('button[type="submit"]');btn.disabled=true;btn.textContent='SUBMITTING…';
      try{
        const d=await api(`${V3}/booking/reservations`,reqJSON('POST',payload));
        sessionStorage.setItem('wongdhenBookingToken',d.manage_token);
        const manageLink=`${location.origin}/manage-booking#token=${encodeURIComponent(d.manage_token)}`;
        root.innerHTML=`<div class="v4-receipt"><div class="section-tag">REQUEST RECEIVED · PENDING APPROVAL</div><h2>Thank you, ${safe(d.booking.name)}.</h2><p>Reference <strong>${safe(d.booking.reference)}</strong></p><p>${safe(d.message)}</p><p>Requested for ${safe(d.booking.visit_date)} at ${safe(d.booking.visit_time)} (India time), ${d.booking.party_size} guests.</p><p><strong>Status: PENDING STAFF CONFIRMATION</strong></p><p>Save the secure management link below. It is the only way to check or cancel this booking online in the current staging build.</p><button id="copyBooking" class="submit-button">COPY MANAGEMENT LINK</button><a href="/manage-booking" class="booking-inline-link">CHECK YOUR REQUEST ↗</a><section id="v7Occasion" class="v7-occasion"></section></div>`;window.v7OccasionForm?.(d.manage_token);
        $('#copyBooking').onclick=async()=>{try{await navigator.clipboard.writeText(manageLink);toast('Private management link copied')}catch{prompt('Copy your private management URL',manageLink)}};
      }catch(err){result.textContent=err.message;await update();}finally{btn.disabled=false;btn.textContent='REQUEST RESERVATION ↗';}
    };
  }catch(e){root.textContent='Booking information could not be loaded: '+e.message}
}

async function v3Manage(){
  app.innerHTML=genericHero('YOUR RESERVATION','MANAGE<br/>YOUR VISIT.','Check the status of your request or cancel an eligible reservation.')+
    `<section class="booking-shell"><div class="booking-card"><form id="manageForm" class="booking-form"><label>Private booking access token<input name="token" type="text" required minlength="32" placeholder="Paste your secure booking token" autocomplete="off" /></label><p class="booking-footnote">Your booking link contains this token after #token=. Do not share it publicly.</p><button class="submit-button">CHECK STATUS</button><p id="manageResult" role="status"></p></form><div id="manageDetails"></div></div></section>`;
  const f=$('#manageForm');
  const saved=location.hash.startsWith('#token=')?decodeURIComponent(location.hash.slice(7)):(sessionStorage.getItem('wongdhenBookingToken')||'');
  f.elements.token.value=saved;
  f.onsubmit=async e=>{
    e.preventDefault();$('#manageResult').textContent='Looking up request…';$('#manageDetails').replaceChildren();
    const token=f.elements.token.value.trim();
    try{
      const d=await api(`${V3}/booking/manage`,reqJSON('POST',{token}));
      const b=d.booking;
      $('#manageResult').textContent='Your booking request has been found.';
      $('#manageDetails').innerHTML=`<div class="booking-confirmation"><h2>${safe(b.reference)}</h2><p><strong>Status:</strong> ${safe(b.status.toUpperCase())}</p><p><strong>Date and time:</strong> ${safe(b.visit_date)} at ${safe(b.visit_time)} IST</p><p><strong>Guests:</strong> ${b.party_size}</p>${['pending','confirmed'].includes(b.status)?'<button id="cancelThisBooking" class="submit-button">CANCEL RESERVATION</button>':''}${b.status==='confirmed'?'<button type="button" id="v8CheckinPass" class="submit-button">GET CHECK-IN PASS</button><div id="v8CheckinResult"></div>':''}${['pending','confirmed'].includes(b.status)?`<form id="rescheduleForm" class="booking-form"><h3>Change your reservation time</h3><label>New visit date<input id="rescheduleDate" name="visit_date" type="date" min="${inputDate()}" value="${safe(b.visit_date)}" required/></label><label>Available times<select id="rescheduleTime" name="visit_time" required></select></label><button class="submit-button" type="submit">RESCHEDULE ↗</button><p id="rescheduleResult" role="status"></p></form>`:'<p>Online rescheduling is unavailable for this reservation state.</p>'}</div>`;
      const rf=$('#rescheduleForm');if(rf){
        const dateInput=$('#rescheduleDate'),timeSelect=$('#rescheduleTime'),msg=$('#rescheduleResult');
        const loadTimes=async()=>{timeSelect.disabled=true;timeSelect.replaceChildren();msg.textContent='Checking genuine availability…';try{
          const list=await api(`${V3}/booking/availability?visit_date=${encodeURIComponent(dateInput.value)}&party_size=${b.party_size}`);
          const options=list.slots.filter(s=>s.available||s.time===b.visit_time&&dateInput.value===b.visit_date);
          options.forEach(x=>{const op=document.createElement('option');op.value=x.time;op.textContent=x.time+(x.available?'':' (current)');timeSelect.appendChild(op)});
          timeSelect.disabled=!options.length;msg.textContent=options.length?'Choose a new time. Existing status is preserved.':'No available times on this date.';
        }catch(error){msg.textContent=error.message}};
        dateInput.addEventListener('change',loadTimes);await loadTimes();
        rf.onsubmit=async ev=>{ev.preventDefault();msg.textContent='Checking and updating…';try{
          const result=await api(`${V3}/booking/reschedule`,reqJSON('POST',{token,visit_date:dateInput.value,visit_time:timeSelect.value}));
          msg.textContent=result.message;f.requestSubmit();
        }catch(error){msg.textContent=error.message;await loadTimes()}};
      }
      const pass=$('#v8CheckinPass');if(pass)pass.onclick=async()=>{
        const area=$('#v8CheckinResult');area.textContent='Preparing secure pass…';
        try{const r=await api('/api/v8/booking/checkin-pass',reqJSON('POST',{token}));
          area.innerHTML=`<p><strong>Present this pass at the café.</strong> Staff must verify it before entry is marked checked in.</p>${r.qr_data_url?`<img alt="Secure reservation check-in QR code" width="230" height="230" src="${r.qr_data_url}"/>`:''}<label>Backup code <input readonly value="${safe(r.checkin_code)}" aria-label="Secure check-in code"/></label>`;
        }catch(error){area.textContent=error.message}
      };
      const cancel=$('#cancelThisBooking');if(cancel)cancel.onclick=async()=>{
        if(!confirm('Cancel this reservation request? This action cannot be undone.'))return;
        try{const result=await api(`${V3}/booking/cancel`,reqJSON('POST',{token}));toast(result.message);f.requestSubmit()}catch(err){toast(err.message)}
      };
    }catch(err){$('#manageResult').textContent=err.message;}
  };
  if(saved)f.requestSubmit();
}

async function showAdminBookings(){
  const t=$('#adminTab');t.textContent='Loading reservations…';
  try{
    const [data, tables]=await Promise.all([api(`${V3}/admin/booking/reservations`),api(`${V3}/admin/booking/tables`)]);
    const rows=data.reservations;
    t.innerHTML=`<h2>Reservation requests (${rows.length})</h2><p class="section-text">Only genuinely received requests appear here. Changing a status is saved immediately and does not send an email; notifications are not connected.</p>
    <div class="admin-menu-list"><table class="admin-table"><thead><tr><th>DATE · TIME</th><th>GUEST</th><th>PARTY</th><th>TABLE</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>
    ${rows.map(r=>`<tr data-booking="${r.id}"><td>${safe(r.visit_date)}<br>${safe(r.visit_time)}–${safe(r.end_time)}<br><small>${safe(r.reference)}</small></td><td>${safe(r.name)}<br><small>${safe(r.email)}</small><br><small>${safe(r.phone)}</small>${r.notes?`<p>${safe(r.notes)}</p>`:''}</td><td>${r.party_size}</td><td><select class="booking-edit-table">${tables.tables.map(x=>`<option value="${x.id}" ${x.id===r.table_id?'selected':''}>${safe(x.label)} (${x.seats})</option>`).join('')}</select></td><td><select class="booking-edit-status">${['pending','confirmed','checked_in','seated','completed','cancelled','declined','no_show'].map(s=>`<option value="${s}" ${r.status===s?'selected':''}>${fmt(s)}</option>`).join('')}</select></td><td><button class="booking-save">SAVE</button></td></tr>`).join('')}
    </tbody></table></div><p id="bookingAdminResult" class="form-status" aria-live="polite">${rows.length?'':'No reservations yet.'}</p>`;
    t.querySelectorAll('.booking-save').forEach(btn=>btn.onclick=async()=>{
      const tr=btn.closest('tr');const id=Number(tr.dataset.booking);
      try{await adminFetch(`${V3}/admin/booking/reservations/${id}`,reqJSON('PATCH',{status:tr.querySelector('.booking-edit-status').value,table_id:Number(tr.querySelector('.booking-edit-table').value)}));toast('Reservation updated');showAdminBookings()}catch(e){$('#bookingAdminResult').textContent=e.message}
    });
  }catch(e){t.textContent=e.message}
}

async function showAdminTables(){
  const t=$('#adminTab');t.textContent='Loading table inventory…';
  try{
    const d=await api(`${V3}/admin/booking/tables`);
    t.innerHTML=`<h2>Actual table inventory</h2><p class="section-text">Enter the real tables and capacities verified by the owner. No fictitious seating data is preloaded.</p>
    <form id="createTable" class="admin-menu-form"><label>Table identifier<input name="label" required placeholder="Actual table label" maxlength="50" /></label><label>Seats<input name="seats" type="number" min="1" max="50" required/></label><label>Real seating area<input name="area" value="Main dining" required maxlength="100"/></label><button class="submit-button">ADD VERIFIED TABLE</button></form>
    <div class="admin-menu-list"><table class="admin-table"><thead><tr><th>TABLE</th><th>AREA</th><th>CAPACITY</th><th>ACTIVE</th><th>ACTION</th></tr></thead><tbody>${d.tables.map(x=>`<tr data-id="${x.id}"><td><input class="tb-label" value="${safe(x.label)}" /></td><td><input class="tb-area" value="${safe(x.area)}" /></td><td><input class="tb-seats" type="number" min="1" max="50" value="${x.seats}"/></td><td><input class="tb-active" type="checkbox" ${x.active?'checked':''}/></td><td><button class="save-table">SAVE</button></td></tr>`).join('')}</tbody></table></div><p id="tableResult" aria-live="polite">${d.tables.length?'':'No actual tables configured yet.'}</p>`;
    $('#createTable').onsubmit=async e=>{e.preventDefault();const p=formObject(e.target);p.seats=Number(p.seats);p.active=true;try{await adminFetch(`${V3}/admin/booking/tables`,reqJSON('POST',p));showAdminTables()}catch(e){$('#tableResult').textContent=e.message}};
    t.querySelectorAll('.save-table').forEach(b=>b.onclick=async()=>{const tr=b.closest('tr'),p={label:tr.querySelector('.tb-label').value,seats:Number(tr.querySelector('.tb-seats').value),area:tr.querySelector('.tb-area').value,active:tr.querySelector('.tb-active').checked};try{await adminFetch(`${V3}/admin/booking/tables/${tr.dataset.id}`,reqJSON('PUT',p));toast('Table saved');showAdminTables()}catch(e){$('#tableResult').textContent=e.message}})
  }catch(e){t.textContent=e.message}
}

async function showAdminBookingPolicy(){
 const t=$('#adminTab');t.textContent='Loading booking rules…';
 try{
  const d=await api(`${V3}/admin/booking/policy`);
  const fields=[['opening','Opening (HH:MM)','text'],['closing','Closing (HH:MM)','text'],['slot_minutes','Slot interval (minutes)','number'],['duration_minutes','Table duration (minutes)','number'],['minimum_notice_minutes','Minimum notice (minutes)','number'],['horizon_days','Advance booking days','number'],['max_party_size','Maximum party size','number'],['closed_weekdays','Closed weekdays (Monday=0, Sunday=6)','text'],['blackout_dates','Blocked dates (YYYY-MM-DD, comma separated)','text']];
  t.innerHTML=`<h2>Owner booking policies</h2><p class="section-text">Bookings are OFF by default. Enter actual opening hours, real tables, and verified policies before switching them on. Existing booking requests remain stored when disabled.</p><form id="bookingPolicy" class="admin-settings-grid">
  ${fields.map(([key,title,type])=>`<label>${safe(title)}<input name="${key}" type="${type}" value="${safe(d[key])}" ${['opening','closing','slot_minutes','duration_minutes','horizon_days','max_party_size'].includes(key)?'required':''}/></label>`).join('')}
  <label class="booking-consent"><input type="checkbox" name="owner_verified" ${d.owner_verified?'checked':''}/> Owner has verified opening hours, reservation policies, and actual capacity</label><label class="booking-consent"><input type="checkbox" name="enabled" ${d.enabled?'checked':''}/> Enable live public booking requests</label>
  <button class="submit-button">SAVE BOOKING CONFIGURATION</button><p id="policyResult" role="status"></p></form>`;
  $('#bookingPolicy').onsubmit=async e=>{e.preventDefault();const f=e.target,p=formObject(f);for(const key of ['slot_minutes','duration_minutes','minimum_notice_minutes','horizon_days','max_party_size'])p[key]=Number(p[key]);p.enabled=f.elements.enabled.checked;p.owner_verified=f.elements.owner_verified.checked;try{const saved=await adminFetch(`${V3}/admin/booking/policy`,reqJSON('PUT',p));$('#policyResult').textContent=`Saved. Public reservations: ${saved.enabled?'enabled':'disabled'}.`}catch(err){$('#policyResult').textContent=err.message}};
 }catch(e){t.textContent=e.message}
}

async function showAdminWaitlist(){
 const t=$('#adminTab');try{const r=await api(`${V3}/admin/booking/waitlist`);t.innerHTML=`<h2>Waitlist (${r.waitlist.length})</h2><p>Waitlisted customers are not booked. Contact them manually; automated notifications are not configured.</p>${r.waitlist.map(x=>`<div class="visit-detail" data-id="${x.id}"><small>${safe(x.reference)} · ${safe(x.date)} ${safe(x.time)} · ${x.party_size} guests</small><p>${safe(x.name)} · ${safe(x.email)} · ${safe(x.phone)}</p><select class="wl-status">${['waiting','contacted','closed'].map(s=>`<option value="${s}" ${x.status===s?'selected':''}>${fmt(s)}</option>`).join('')}</select> <button class="wl-save">UPDATE</button></div>`).join('')}`;t.querySelectorAll('.wl-save').forEach(btn=>btn.onclick=async()=>{const card=btn.closest('[data-id]');try{await adminFetch(`${V3}/admin/booking/waitlist/${card.dataset.id}`,reqJSON('PATCH',{status:card.querySelector('select').value}));toast('Waitlist updated')}catch(e){toast(e.message)}})}catch(e){t.textContent=e.message}
}

async function showAdminWalkins(){
 const t=$('#adminTab');try{const r=await api(`${V3}/admin/booking/walkins`);t.innerHTML=`<h2>Walk-in queue</h2><p class="section-text">Staff-only queue log. This is not yet linked to live occupancy or table inventory.</p><form id="walkinForm" class="admin-menu-form"><label>Name<input name="name" required minlength="2"/></label><label>Party size<input name="party_size" required type="number" min="1" max="100"/></label><label>Phone (optional)<input name="phone"/></label><button class="submit-button">ADD WALK-IN</button></form>${r.walkins.map(x=>`<div class="visit-detail" data-id="${x.id}"><p>${safe(x.name)} · ${x.party_size} guests · ${safe(x.phone)}</p><select class="walkin-status">${['waiting','seated','cancelled'].map(s=>`<option value="${s}" ${x.status===s?'selected':''}>${fmt(s)}</option>`).join('')}</select> <button class="walkin-save">UPDATE</button></div>`).join('')}`;$('#walkinForm').onsubmit=async e=>{e.preventDefault();const p=formObject(e.target);p.party_size=Number(p.party_size);try{await adminFetch(`${V3}/admin/booking/walkins`,reqJSON('POST',p));showAdminWalkins()}catch(e){toast(e.message)}};t.querySelectorAll('.walkin-save').forEach(b=>b.onclick=async()=>{const el=b.closest('[data-id]');try{await adminFetch(`${V3}/admin/booking/walkins/${el.dataset.id}`,reqJSON('PATCH',{status:el.querySelector('select').value}));toast('Walk-in updated')}catch(e){toast(e.message)}})}catch(e){t.textContent=e.message}
}


/* V23 — real-data day operations and owner-set holiday / special-hours UI. */
async function showV23DayBoard(){
 const root=$('#adminTab');
 root.innerHTML=`<h2>DAY OPERATIONS</h2><p>Actual reservation records and real seating inventory. Pending requests are <strong>not confirmed</strong>. No SMS or email is sent by status changes.</p>
  <label class="v23-date-pick">Visit date <input type="date" id="v23DayDate" value="${inputDate()}"/></label>
  <div id="v23DayContent" role="status">Loading operational board…</div>`;
 const date=$('#v23DayDate'),target=$('#v23DayContent');
 const load=async()=>{
  target.textContent='Loading real table inventory…';
  try{
   const data=await api(`${V3}/admin/booking/day-board?visit_date=${encodeURIComponent(date.value)}`);
   const status=data.hours.closed?'CLOSED':`${safe(data.hours.opening)}–${safe(data.hours.closing)}`;
   target.innerHTML=`<div class="v23-summary">
    <div><small>OWNER-CONFIGURED HOURS</small><strong>${status}</strong><span>${safe(data.hours.source)}</span></div>
    <div><small>ACTIVE TABLES</small><strong>${data.table_count}</strong><span>${data.seats_total} total seats</span></div>
    <div><small>PENDING REQUESTS</small><strong>${data.pending}</strong><span>Approval required</span></div>
    <div><small>CONFIRMED</small><strong>${data.confirmed}</strong><span>Stored in booking system</span></div>
   </div><p>${data.bookings_enabled?'Booking configuration is enabled. Confirm owner-verified operating hours and policies.':'Public reservation requests are currently disabled.'}</p>
   <div class="v23-board">${data.tables.map(t=>`<article class="v23-table-card">
     <header><strong>${safe(t.label)}</strong><span>${safe(t.area)} · ${t.seats} seats ${t.active?'':'· INACTIVE'}</span></header>
     ${t.bookings.length?t.bookings.map(b=>`<p class="v23-row"><span><b>${safe(b.start)}–${safe(b.end)}</b> · ${safe(b.guest)} · ${b.party_size} guests</span><em>${safe(b.status)}</em></p>`).join(''):'<p class="v23-empty">No reservations recorded for this table today.</p>'}
    </article>`).join('')}</div>
   <button id="v23ManageBookings" type="button" class="submit-button">REVIEW RESERVATION REQUESTS →</button>`;
   $('#v23ManageBookings').onclick=()=>document.querySelector('[data-tab="bookings"]')?.click();
  }catch(e){target.textContent=e.message}
 };
 date.addEventListener('change',load);await load();
}

async function showV23DateExceptions(){
 const root=$('#adminTab');
 root.innerHTML=`<h2>HOLIDAYS & SPECIAL HOURS</h2>
 <p>Manage real café date exceptions. Bookings are not automatically activated. Changes that would displace an active reservation are rejected.</p>
 <form id="v23HoursForm" class="v23-hours-form">
  <label>Date <input type="date" name="date" value="${inputDate()}" required /></label>
  <label>Opening (24-hour) <input type="time" name="opening" value="12:00"/></label>
  <label>Closing (24-hour) <input type="time" name="closing" value="21:00"/></label>
  <label>Staff note (internal) <input name="note" maxlength="180" placeholder="Optional reason for this exception"/></label>
  <label class="v23-check"><input type="checkbox" name="closed"/> Closed all day</label>
  <label class="v23-check"><input type="checkbox" name="verified" required /> I have verified these hours with the café owner</label>
  <button type="submit" class="submit-button">SAVE DATE EXCEPTION</button>
 </form><p id="v23HoursResult" role="status"></p><div id="v23HoursList" role="region" aria-label="Existing special hours"></div>`;
 const form=$('#v23HoursForm'),notice=$('#v23HoursResult'),list=$('#v23HoursList');
 const updateMode=()=>{form.elements.opening.disabled=form.elements.closed.checked;form.elements.closing.disabled=form.elements.closed.checked};
 form.elements.closed.onchange=updateMode;
 const render=async()=>{
  try{
   const data=await api(`${V3}/admin/booking/date-exceptions`);
   list.innerHTML=`<h3>Saved exceptions (${data.dates.length})</h3>`+(data.dates.length?data.dates.map(x=>`
   <div class="v23-exception" data-date="${safe(x.date)}">
    <span><b>${safe(x.date)}</b> · ${x.closed?'Closed':safe(x.opening)+'–'+safe(x.closing)}${x.note?' · '+safe(x.note):''}</span>
    <button type="button" class="v23-delete">REMOVE</button>
   </div>`).join(''):'<p>No special dates saved yet.</p>');
   list.querySelectorAll('.v23-delete').forEach(button=>button.onclick=async()=>{
    const dateValue=button.closest('[data-date]').dataset.date;
    if(!confirm(`Remove the ${dateValue} special-hours rule? Existing bookings will be checked.`))return;
    try{
     await adminFetch(`${V3}/admin/booking/date-exceptions/${encodeURIComponent(dateValue)}`,{method:'DELETE'});
     notice.textContent=`Removed exception for ${dateValue}.`;await render();
    }catch(err){notice.textContent=err.message}
   });
  }catch(err){list.textContent=err.message}
 };
 form.onsubmit=async event=>{
  event.preventDefault();
  const day=form.elements.date.value,closed=form.elements.closed.checked;
  notice.textContent='Saving owner-verified special hours…';
  try{
   const payload={closed,opening:closed?'':form.elements.opening.value,
       closing:closed?'':form.elements.closing.value,note:form.elements.note.value};
   await adminFetch(`${V3}/admin/booking/date-exceptions/${encodeURIComponent(day)}`,reqJSON('PUT',payload));
   notice.textContent=`Saved special hours for ${day}. These do not enable public reservations by themselves.`;
   form.elements.verified.checked=false;await render();
  }catch(err){notice.textContent=err.message}
 };
 await render();
}

if(page==='reservations')v3Reservations();
if(page==='manage-booking')v3Manage();
