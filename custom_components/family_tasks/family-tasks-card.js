class FamilyTasksBaseCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this.editId=''; this.message=''; }
  setConfig(config) { this.config=config; this.render(); }
  set hass(hass) { this._hass=hass; const state=hass.states[this.config?.catalog_entity || 'sensor.family_tasks_catalog']; const stamp=JSON.stringify(state?.attributes || {}); if(stamp!==this._stamp){this._stamp=stamp;this.render();} }
  getCardSize(){return this.mode === 'people' ? 3 : 6;}
  render(){
    if(!this.shadowRoot)return;
    const catalog=this._hass?.states[this.config?.catalog_entity || 'sensor.family_tasks_catalog'];
    const people=catalog?.attributes.people || [], tasks=catalog?.attributes.tasks || [];
    const editing=tasks.find(t=>t.id===this.editId);
    const peopleOnly=this.mode==='people';
    const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const personName=id=>people.find(p=>p.id===id)?.name || '?';
    const option=(value,label,selected)=>`<option value="${esc(value)}" ${value===selected?'selected':''}>${esc(label)}</option>`;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;font-family:var(--primary-font-family,Arial)}ha-card{display:block;padding:18px;color:var(--primary-text-color);background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,12px);box-shadow:var(--ha-card-box-shadow,0 2px 4px #0002)}h2{margin:0 0 14px;font-size:20px}h3{font-size:16px}label{display:block;margin:10px 0 4px}input,select{box-sizing:border-box;width:100%;padding:10px;border:1px solid var(--divider-color,#aaa);border-radius:7px;background:var(--card-background-color,#fff);color:var(--primary-text-color)}button{cursor:pointer;border:0;border-radius:8px;padding:10px 13px;margin:6px 5px 0 0;background:var(--primary-color,#03a9f4);color:white}button.secondary{background:var(--secondary-background-color,#ddd);color:var(--primary-text-color)}.item{border-top:1px solid var(--divider-color,#ddd);padding:10px 0}.small{font-size:12px;color:var(--secondary-text-color)}.days{display:flex;flex-wrap:wrap;gap:9px}.days label{margin:0}.days input{width:auto}.error{color:var(--error-color,#d32f2f)}
      </style><ha-card><h2>${peopleOnly?'Familienmitglieder verwalten':'Familienaufgaben verwalten'}</h2>${!catalog?'<p class="error">Katalogsensor nicht gefunden. Integration und Dashboard-Ressource prüfen.</p>':''}
      ${peopleOnly?`<form id="person"><label>Familienmitglied hinzufügen</label><input name="name" maxlength="60" required placeholder="Name"><button>Person hinzufügen</button></form><h3>Vorhandene Personen</h3>${people.length?people.map(p=>`<div class="item">${esc(p.name)}</div>`).join(''):'<p>Noch keine Personen angelegt.</p>'}<p class="small">Personen können in dieser Version hinzugefügt werden. Umbenennen und Löschen ist noch nicht vorgesehen.</p>`:''}
      ${peopleOnly?'':`<hr><h3>${editing?'Aufgabe bearbeiten':'Neue Aufgabe'}</h3><form id="task"><label>Aufgabe</label><input name="title" maxlength="120" required value="${esc(editing?.title)}" placeholder="z. B. Spülmaschine ausräumen"><label>Zuständig</label><select name="person" required><option value="">Bitte wählen</option>${people.map(p=>option(p.name,p.name,personName(editing?.person_id))).join('')}</select><label>Tageszeit</label><select name="time_of_day">${[['morning','🌅 Morgens'],['daytime','☀️ Tagsüber'],['evening','🌙 Abends'],['anytime','Ohne Zuordnung']].map(([v,l])=>option(v,l,editing?.time_of_day || 'anytime')).join('')}</select><label>Wenn nicht erledigt</label><select name="missed_behavior">${[['discard','Verwerfen'],['archive','Archivieren'],['keep','Offen lassen']].map(([v,l])=>option(v,l,editing?.missed_behavior || (editing?'archive':'discard'))).join('')}</select><label>Wiederholung</label><select name="frequency">${[['daily','Täglich'],['weekly','Wöchentlich'],['monthly','Monatlich'],['yearly','Jährlich']].map(([v,l])=>option(v,l,editing?.frequency || 'daily')).join('')}</select><div id="weekly"><label>Wochentage</label><div class="days">${['Mo','Di','Mi','Do','Fr','Sa','So'].map((d,i)=>`<label><input type="checkbox" name="weekday" value="${i}" ${editing?.weekdays?.includes(i)?'checked':''}>${d}</label>`).join('')}</div></div><div id="monthly"><label>Tag des Monats</label><select name="day">${Array.from({length:31},(_,i)=>option(String(i+1),String(i+1),String(editing?.day || 1))).join('')}</select></div><div id="yearly"><label>Jährlich am</label><select name="year_month">${['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'].map((name,i)=>option(String(i+1),name,String(editing?.month || (editing?.start ? Number(editing.start.slice(5,7)) : new Date().getMonth()+1)))) .join('')}</select><label>Tag</label><select name="year_day">${Array.from({length:31},(_,i)=>option(String(i+1),String(i+1),String(editing?.frequency === 'yearly' ? editing?.day : new Date().getDate()))).join('')}</select></div><button ${!people.length?'disabled':''}>${editing?'Änderungen speichern':'Aufgabe anlegen'}</button>${editing?'<button type="button" class="secondary" id="cancel">Abbrechen</button>':''}</form><p id="message" role="status">${esc(this.message)}</p><hr><h3>Aufgabendefinitionen</h3>${tasks.length?tasks.map(t=>`<div class="item"><b>${esc(t.title)}</b><div class="small">${esc(personName(t.person_id))} · ${esc(({morning:'🌅 Morgens',daytime:'☀️ Tagsüber',evening:'🌙 Abends',anytime:'Ohne Zuordnung'})[t.time_of_day||'anytime'])} · ${esc(t.frequency)}</div><button class="secondary" data-edit="${esc(t.id)}">Bearbeiten</button><button class="secondary" data-delete="${esc(t.id)}">Löschen</button></div>`).join(''):'<p>Noch keine Aufgaben angelegt.</p>'}`}</ha-card>`;
    const personForm=this.shadowRoot.querySelector('#person');
    if(personForm)personForm.onsubmit=async e=>{e.preventDefault();const name=e.target.elements.name.value.trim();if(name)await this.call('add_person',{name});};
    if(peopleOnly)return;
    const form=this.shadowRoot.querySelector('#task'), freq=form.elements.frequency;
    const toggle=()=>{this.shadowRoot.querySelector('#weekly').hidden=freq.value!=='weekly';this.shadowRoot.querySelector('#monthly').hidden=freq.value!=='monthly';this.shadowRoot.querySelector('#yearly').hidden=freq.value!=='yearly';};freq.addEventListener('change',toggle);toggle();
    form.onsubmit=async e=>{e.preventDefault();const f=e.target,frequency=f.elements.frequency.value;const weekdays=[...f.querySelectorAll('[name=weekday]:checked')].map(x=>x.value).join(',');if(frequency==='weekly'&&!weekdays){this.note('Bitte mindestens einen Wochentag auswählen.');return;}const data={title:f.elements.title.value.trim(),person:f.elements.person.value,frequency,time_of_day:f.elements.time_of_day.value,missed_behavior:f.elements.missed_behavior.value};if(frequency==='weekly')data.weekdays=weekdays;if(frequency==='monthly')data.day=Number(f.elements.day.value);if(frequency==='yearly'){data.month=Number(f.elements.year_month.value);data.day=Number(f.elements.year_day.value);}if(this.editId)data.task_id=this.editId;await this.call(this.editId?'update_task':'add_task',data);};
    this.shadowRoot.querySelector('#cancel')?.addEventListener('click',()=>{this.editId='';this.render();});
    this.shadowRoot.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{this.editId=b.dataset.edit;this.message='';this.render();});
    this.shadowRoot.querySelectorAll('[data-delete]').forEach(b=>b.onclick=async()=>{if(confirm('Aufgabendefinition löschen? Historische Einträge bleiben gespeichert.'))await this.call('delete_task',{task_id:b.dataset.delete});});
  }
  note(message){this.message=message;const el=this.shadowRoot.querySelector('#message');if(el)el.textContent=message;}
  async call(action,data){try{await this._hass.callService('family_tasks',action,data);this.editId='';this.note('Gespeichert.');}catch(e){this.note('Fehler: '+(e.message||String(e)));}}
}
class FamilyTasksCard extends FamilyTasksBaseCard { get mode(){return 'tasks';} }
class FamilyTasksPeopleCard extends FamilyTasksBaseCard { get mode(){return 'people';} }
customElements.define('family-tasks-card',FamilyTasksCard);
customElements.define('family-tasks-people-card',FamilyTasksPeopleCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'family-tasks-card',name:'Family Tasks Verwaltung',description:'Wiederkehrende Aufgaben verwalten'});

window.customCards.push({type:'family-tasks-people-card',name:'Family Tasks Personen',description:'Familienmitglieder separat verwalten'});


class FamilyTasksBoardCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.busy=new Set();}
  setConfig(config){this.config=config||{};this.render();}
  set hass(hass){
    this._hass=hass;
    const entity=this.config?.catalog_entity||'sensor.family_tasks_catalog';
    const state=hass.states[entity];
    const stamp=JSON.stringify(state?.attributes||{});
    const day=new Date().toLocaleDateString('en-CA');
    if(stamp!==this._stamp||day!==this._day){this._stamp=stamp;this._day=day;this.render();}
  }
  getCardSize(){return 8;}
  render(){
    if(!this.shadowRoot)return;
    const catalog=this._hass?.states[this.config?.catalog_entity||'sensor.family_tasks_catalog'];
    const people=catalog?.attributes.people||[];
    const tasks=catalog?.attributes.tasks||[];
    const history=catalog?.attributes.history||[];
    const taskMap=new Map(tasks.map(t=>[t.id,t]));
    const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','"':'&quot;',"'":'&#39;'}[c]));
    const today=new Date().toLocaleDateString('en-CA');
    const current=history.filter(i=>(i.date===today || (i.date<today && i.status==='open')) && taskMap.has(i.task_id) && (i.status==='open'||i.status==='done'));
    const grouped=new Map(people.map(p=>[p.id,[]]));
    current.forEach(i=>grouped.get(taskMap.get(i.task_id).person_id)?.push({...i,task:taskMap.get(i.task_id)}));
    const cols=Number(this.config?.columns||0);
    const minWidth=Math.max(180,Number(this.config?.min_column_width||260));
    const style=cols>0?`grid-template-columns:repeat(${Math.min(12,Math.max(1,cols))},minmax(0,1fr))`:`grid-template-columns:repeat(auto-fit,minmax(min(100%,${minWidth}px),1fr))`;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;min-width:0;color:var(--primary-text-color);font-family:var(--primary-font-family,Arial,sans-serif)}
      *{box-sizing:border-box}
      ha-card{display:block;padding:clamp(14px,2vw,26px);background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:20px}
      .board-top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:20px}
      h2{margin:0 0 5px;font-size:clamp(22px,2.4vw,30px);font-weight:800;letter-spacing:-.025em}
      .sub{font-size:14px;color:var(--secondary-text-color)}
      .today-pill{border-radius:999px;padding:9px 14px;background:var(--secondary-background-color,#edf2f7);font-weight:700;font-size:13px;white-space:nowrap}
      .grid{display:grid;gap:clamp(10px,1.3vw,18px);${style}}
      .person{--accent:#4196c9;--accent-bg:rgba(65,150,201,.10);min-width:0;padding:clamp(12px,1.5vw,18px);background:var(--card-background-color,var(--ha-card-background,#fff));border:1px solid var(--divider-color,#ddd);border-top:5px solid var(--accent);border-radius:17px;box-shadow:0 4px 18px rgba(0,0,0,.045)}
      .person:nth-child(5n + 2){--accent:#ac79d8;--accent-bg:rgba(172,121,216,.11)}
      .person:nth-child(5n + 3){--accent:#24a795;--accent-bg:rgba(36,167,149,.11)}
      .person:nth-child(5n + 4){--accent:#e19a3c;--accent-bg:rgba(225,154,60,.11)}
      .person:nth-child(5n + 5){--accent:#dc7c9c;--accent-bg:rgba(220,124,156,.11)}
      .head{display:flex;flex-direction:column;gap:10px;margin-bottom:15px}
      .head-line{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
      h3{margin:0;font-size:clamp(18px,1.6vw,23px);font-weight:800;overflow-wrap:anywhere}
      .count{white-space:nowrap;font-size:12px;color:var(--secondary-text-color);font-weight:700}
      .progress{width:100%;height:8px;overflow:hidden;border-radius:999px;background:var(--divider-color,#e2e8f0)}
      .progress-fill{height:100%;background:var(--accent);border-radius:inherit;transition:width .25s ease}
      .period{margin-top:13px}.period-title{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:800;color:var(--secondary-text-color);padding:6px 2px 9px;text-transform:uppercase;letter-spacing:.055em}
      .task{display:flex;align-items:center;gap:12px;min-height:52px;padding:10px 11px;margin-bottom:7px;border-radius:12px;background:var(--accent-bg);cursor:pointer;line-height:1.35;transition:filter .15s ease,transform .15s ease}
      .task:hover{filter:brightness(.97)}.task:active{transform:scale(.99)}
      .task input{width:27px;height:27px;flex:none;accent-color:var(--accent);cursor:pointer;margin:0}
      .task-text{font-size:clamp(14px,1.1vw,16px);font-weight:600;overflow-wrap:anywhere;min-width:0}
      .task.done{background:var(--secondary-background-color,rgba(128,128,128,.09))}
      .task.done .task-text{text-decoration:line-through;opacity:.57}
      .overdue{display:block;color:var(--error-color,#d32f2f);font-size:12px;font-weight:700;margin-top:4px}
      .empty{color:var(--secondary-text-color);font-size:14px;padding:18px 0;text-align:center}
      .error{color:var(--error-color,#d32f2f)}
      @media(max-width:700px){.grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))!important}.person{padding:13px}}
      @media(max-width:480px){ha-card{padding:12px}.grid{grid-template-columns:1fr!important;gap:12px}.board-top{margin-bottom:14px}.task{min-height:56px}}
      @media(prefers-reduced-motion:reduce){.task,.progress-fill{transition:none}}
    </style><ha-card><header class="board-top"><div><h2>${esc(this.config?.title||'Unsere Familienaufgaben')}</h2><div class="sub">${esc(new Date().toLocaleDateString('de-DE',{weekday:'long',day:'numeric',month:'long',year:'numeric'}))}</div></div><div class="today-pill">Heute im Blick</div></header>
    ${!catalog?'<p class="error">Katalogsensor nicht gefunden.</p>':''}
    <div class="grid">${people.map(person=>{
      const items=grouped.get(person.id)||[];
      const done=items.filter(i=>i.status==='done').length;
      const percent=items.length?Math.round(done/items.length*100):0;
      return `<section class="person"><div class="head"><div class="head-line"><h3>${esc(person.name)}</h3><div class="count">${done} von ${items.length} erledigt</div></div><div class="progress" role="progressbar" aria-label="Fortschritt ${esc(person.name)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><div class="progress-fill" style="width:${percent}%"></div></div></div>
      ${items.length?[['morning','🌅 Morgens'],['daytime','☀️ Tagsüber'],['evening','🌙 Abends'],['anytime','📌 Ohne Zuordnung']].map(([key,label])=>{const group=items.filter(i=>(i.task.time_of_day||'anytime')===key).sort((a,b)=>Number(a.status==='done')-Number(b.status==='done')||a.task.title.localeCompare(b.task.title));return group.length?`<div class="period"><div class="period-title">${label}</div>${group.map(i=>`<label class="task ${i.status==='done'?'done':''}"><input type="checkbox" data-uid="${esc(i.id)}" ${i.status==='done'?'checked':''} ${this.busy.has(i.id)?'disabled':''}><span class="task-text">${esc(i.task.title)}${i.date<today?` <small class="overdue">Überfällig seit ${esc(new Date(i.date+'T12:00:00').toLocaleDateString('de-DE'))}</small>`:''}</span></label>`).join('')}</div>`:''}).join(''):'<div class="empty">Heute keine Aufgaben ✨</div>'}</section>`;
    }).join('')}</div><p id="board-error" class="error" role="status"></p></ha-card>`;
    this.shadowRoot.querySelectorAll('input[data-uid]').forEach(input=>input.onchange=async()=>{
      const uid=input.dataset.uid, checked=input.checked;
      input.disabled=true;this.busy.add(uid);
      try {
        await this._hass.callService('todo','update_item',{
          entity_id:this.config?.todo_entity||'todo.family_tasks',
          item:uid,status:checked?'completed':'needs_action'
        });
      }catch(e){
        input.checked=!checked;
        this.shadowRoot.querySelector('#board-error').textContent='Speichern fehlgeschlagen: '+(e.message||String(e));
      }finally{this.busy.delete(uid);input.disabled=false;}
    });
  }
}
customElements.define('family-tasks-board-card',FamilyTasksBoardCard);
window.customCards.push({type:'family-tasks-board-card',name:'Family Tasks Familienübersicht',description:'Heutige Aufgaben nebeneinander nach Person, für Tablet-Dashboards'});
