import React, { useEffect, useState } from 'react'
import { ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, host, usePluginI18n } from '@hermes/plugin-sdk'

// Desktop-only strings. The Python API intentionally returns stable machine-readable
// stage codes and raw diagnostic details; the active UI language never changes a run.
const ID = 'hermes-mtp-lab'
const PREF_KEY = 'hermes-mtp-lab:language'
const STRINGS = {
  ru: {
    language:'Язык', languageAuto:'Авто / Hermes', languageRu:'Русский', languageEn:'English',
    title:'Hermes MTP Lab', intro:'Универсальный локальный A/B-бенчмарк моделей, поддерживающих MTP, через управляемый llama.cpp Hermes. Пользовательские чаты не изменяются.',
    connectTitle:'Python API недоступен', connectHelp:'Desktop-плагин загружен, но Python-бэкенд должен быть разрешён через Hermes CLI. Полностью перезапустите Hermes.',
    checkConnection:'Проверить подключение', notOwner:'Локальный сервер не принадлежит текущему Hermes', notOwnerHelp:'Python API отвечает, но не подтвердил право управлять llama.cpp. Переключение заблокировано, чтобы не затронуть чужие процессы.', refresh:'Обновить статус',
    interrupted:'Обнаружен незавершённый тест — требуется восстановление', interruptedHelp:(flag)=>'Обнаружен аварийный маркер предыдущего запуска. Исходное состояние MTP: '+flag+'. Во время активного теста это предупреждение не показывается.', restore:'Восстановить исходный MTP',
    control:'Управление MTP', flag:'Флаг', owner:'Владелец сервера', currentHermes:'текущий Hermes', unconfirmed:'не подтверждён', toggleHelp:'Переключение перезапускает только управляемый локальный runtime. Завершите генерацию в других чатах.', enable:'Включить MTP', disable:'Отключить MTP',
    compare:'Автоматическое сравнение OFF → ON', compareHelp:'До шести заданий: текст, код, вычисления, рассказ и, при наличии mmproj, две визуальные задачи. Контекст OFF/ON одинаков; не больше 32768 токенов.', quick:'Быстрый тест · 1 проход', full:'Полный тест · 3 прохода', stop:'Остановить после текущего запроса',
    executing:'Тест выполняется', phase:'Фаза', overall:'Всего', completed:'Завершено измерений', count:(done,total,pct)=>`${done} / ${total} измерений завершено${total?' · '+pct+'%':''}`, stageTime:'Время этапа', task:'Задание', repeat:'повтор',
    serverCounter:'Счётчик сервера', tokens:'токенов', limit:'лимит', tokenDisclaimer:'Счётчик генерации не гарантирует процент готовности ответа. При нестриминговом API обновления могут запаздывать.',
    loadingHint:'Модель загружается. Сервер не предоставляет достоверный процент загрузки.', requestHint:'Ожидание счётчиков сервера. Различить подготовку ответа и внутреннее размышление модели невозможно.', otherHint:'Этап выполняется. Достоверный процент внутри этапа недоступен.',
    modesNotice:'Реальные режимы чата Hermes: Auto, Native, Text. Этот бенчмарк НЕ переключает их: категории обозначают типы нагрузок llama.cpp, а не режимы интерфейса.',
    result:'Результаты', workload:'Нагрузка', offSpeed:'OFF ток/с', onSpeed:'ON ток/с', speedup:'Ускорение', accepted:'MTP принято', comparable:'Параметры OFF/ON совпадают', yes:'да', no:'нет / неизвестно', comparableWarning:'Это наблюдаемое ускорение: некоторые параметры OFF/ON различаются либо не подтверждены. Подробности — в summary.md.', reports:'Отчёты', restored:'Исходный MTP восстановлен', restoreCheck:'НЕТ — проверьте журнал и резервную копию', error:'Ошибка',
    stage_idle:'Готов к тестированию', stage_checking:'Проверка окружения', stage_switch:'Переключение MTP и запуск сервера', stage_loading:'Загрузка модели и выделение памяти', stage_warmup:'Прогрев модели', stage_preparing:'Подготовка запроса', stage_request:'Обработка запроса и генерация', stage_restore:'Восстановление настроек', stage_report:'Создание отчётов', stage_finished:'Тест завершён', stage_error:'Тест завершился с ошибкой', stage_cancelled:'Тест остановлен',
    chooseModel:'Модель Hermes', noModel:'— выбери модель —', support:'MTP-совместимость',supported:'Поддержка обнаружена', unsupported:'Нет подтверждённой MTP-конфигурации', headLabel:'MTP-head GGUF (пусто для встроенной MTP)', projLabel:'mmproj GGUF (необязательно)', saveCompanions:'Сохранить связь компаньонов', configHint:'Выбирай точные пути совместимых GGUF. Привязка сохраняется для выбранной модели с резервной копией; Hermes применит её штатно при следующем запуске. Не подбирай файлы по похожему названию.', textOnly:'Только текстовые задания (mmproj отсутствует)', imageEnabled:'Визуальные задания включены', sessionOnly:'Ручное переключение действует в текущем сеансе; для постоянной настройки используй штатные настройки модели Hermes.', group_text:'Текст', group_code:'Код и данные', group_scene:'Описание изображения', group_ground:'Распознавание деталей', open:'Открыть MTP Lab'
  },
  en: {
    language:'Language', languageAuto:'Auto / Hermes', languageRu:'Русский', languageEn:'English',
    title:'Hermes MTP Lab', intro:'Model-agnostic A/B benchmarking for MTP-capable local models through Hermes-managed llama.cpp. Your chats are not modified.',
    connectTitle:'Python API unavailable', connectHelp:'The Desktop extension is loaded, but its Python backend must also be enabled through Hermes CLI. Fully restart Hermes.',
    checkConnection:'Check connection', notOwner:'Local server is not owned by this Hermes process', notOwnerHelp:'The Python API is reachable, but ownership of the running llama.cpp process is not confirmed. Switching is disabled to protect unrelated processes.', refresh:'Refresh status',
    interrupted:'Unfinished previous benchmark — recovery required', interruptedHelp:(flag)=>'A recovery marker was left by an earlier run. Original MTP state: '+flag+'. This warning is hidden during a healthy active run.', restore:'Restore original MTP setting',
    control:'MTP controls', flag:'Flag', owner:'Server owner', currentHermes:'current Hermes', unconfirmed:'not confirmed', toggleHelp:'Switching restarts only the managed local runtime. Finish generation in other chats before switching.', enable:'Enable MTP', disable:'Disable MTP',
    compare:'Automatic OFF → ON comparison', compareHelp:'Up to six tasks: text, code, data, narrative, plus two vision tests when mmproj is available. OFF/ON share a context of at most 32768 tokens.', quick:'Quick test · 1 pass', full:'Full test · 3 passes', stop:'Stop after current request',
    executing:'Benchmark running', phase:'Phase', overall:'Total', completed:'Completed measurements', count:(done,total,pct)=>`${done} / ${total} measurements completed${total?' · '+pct+'%':''}`, stageTime:'Stage elapsed', task:'Task', repeat:'repeat',
    serverCounter:'Server token counter', tokens:'tokens', limit:'limit', tokenDisclaimer:'The generation counter is not a reliable percentage of answer completion. Non-streaming responses may delay metric updates.',
    loadingHint:'The model is loading. The server does not provide a reliable loading percentage.', requestHint:'Waiting for server counters. Answer preparation and internal model reasoning cannot be distinguished reliably.', otherHint:'This stage is active. No reliable internal percentage is available.',
    modesNotice:'Hermes chat modes are Auto, Native and Text. This benchmark does NOT switch among them; groups represent llama.cpp workload types, not chat UI modes.',
    result:'Results', workload:'Workload', offSpeed:'OFF tok/s', onSpeed:'ON tok/s', speedup:'Speedup', accepted:'MTP accepted', comparable:'OFF/ON parameters identical', yes:'yes', no:'no / unknown', comparableWarning:'Speedup is observational: some OFF/ON parameters differ or could not be verified. Details are in summary.md.', reports:'Reports', restored:'Original MTP restored', restoreCheck:'NO — check the log and backup', error:'Error',
    stage_idle:'Ready to benchmark', stage_checking:'Checking environment', stage_switch:'Switching MTP and starting server', stage_loading:'Loading model and allocating memory', stage_warmup:'Warming up model', stage_preparing:'Preparing request', stage_request:'Processing request and generating answer', stage_restore:'Restoring original settings', stage_report:'Writing reports', stage_finished:'Benchmark completed', stage_error:'Benchmark failed', stage_cancelled:'Benchmark stopped',
    chooseModel:'Hermes model', noModel:'— select a model —',support:'MTP compatibility',supported:'Support detected',unsupported:'No confirmed MTP configuration',headLabel:'MTP head GGUF (empty for embedded MTP)',projLabel:'mmproj GGUF (optional)',saveCompanions:'Save companion links',configHint:'Enter exact paths to compatible GGUFs. Links are saved with backup for the selected model; Hermes loads them natively on the next restart. Do not guess compatibility from filenames.',textOnly:'Text-only tasks (no mmproj)',imageEnabled:'Vision tasks enabled',sessionOnly:'Manual toggles affect the current session; use native Hermes model settings for persistent changes.', group_text:'Text', group_code:'Code and data', group_scene:'Image description', group_ground:'Visual details', open:'Open MTP Lab'
  }
}
const GROUPS = {
  'Текст':'group_text', 'Код и данные':'group_code',
  'Описание изображения':'group_scene', 'Распознавание деталей':'group_ground',
  'Text':'group_text', 'Code and data':'group_code',
  'Image description':'group_scene', 'Visual details':'group_ground'
}

function storedLanguage() {
  try {
    const v = localStorage.getItem(PREF_KEY)
    return ['auto','ru','en'].includes(v) ? v : 'auto'
  } catch { return 'auto' }
}
function saveLanguage(language) {
  try { localStorage.setItem(PREF_KEY, language) } catch { /* blocked storage: still works for this session */ }
}
const h = React.createElement
const block = { padding:'14px', border:'1px solid var(--ui-stroke-secondary)', borderRadius:10, marginBottom:12 }
const muted = { color:'var(--ui-text-secondary)', fontSize:12, lineHeight:1.6 }
const btn = { border:'1px solid var(--ui-stroke-secondary)', borderRadius:8, padding:'7px 12px', cursor:'pointer', background:'transparent', color:'inherit', marginRight:7, marginTop:7 }
const pill = { borderRadius:7, border:'1px solid var(--ui-stroke-secondary)', padding:'2px 8px', fontSize:12 }
function fmtSec(n) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '—'
  n = Math.max(0, Math.floor(n))
  return [Math.floor(n/3600),Math.floor((n%3600)/60),n%60].map(v=>String(v).padStart(2,'0')).join(':')
}
function Bar({value,indeterminate=false}) {
  const pct=typeof value==='number'?Math.max(0,Math.min(100,value)):0
  return h('div',{style:{position:'relative',marginTop:6,height:9,borderRadius:20,background:'var(--ui-stroke-secondary)',overflow:'hidden'},role:'progressbar', 'aria-valuemin':0, 'aria-valuemax':100,...(!indeterminate?{'aria-valuenow':Math.round(pct)}:{})},
    h('div',{style:indeterminate?{height:'100%',width:'32%',background:'var(--ui-accent)',animation:'mtp-lab-scan 1.6s ease-in-out infinite'}:{height:'100%',width:pct+'%',background:'var(--ui-accent)',transition:'width .25s'}}))
}
function LabView({ ctx }) {
  const [state, setState] = useState(null)
  const [error, setError] = useState('')
  const [head,setHead]=useState('')
  const [proj,setProj]=useState('')
  const [busy, setBusy] = useState(false)
  const [connected, setConnected] = useState(false)
  const [now, setNow] = useState(Date.now())
  const [language,setLanguage] = useState(storedLanguage)
  // ChatVault also uses the Hermes SDK locale, with an explicit local override.
  const sdkT = usePluginI18n(ID)
  const tr=(key,...args)=>{
    const entry=language==='auto'?sdkT(key,...args):undefined
    if (entry!==undefined && entry!==null && entry!==key) return entry
    const lang=language==='ru'?'ru':language==='en'?'en':'en'
    const value=STRINGS[lang][key] ?? STRINGS.en[key] ?? key
    return typeof value==='function'?value(...args):value
  }
  const groupText=(value)=>tr(GROUPS[value] || value || 'group_text')
  const changeLanguage=(value)=>{if(['auto','ru','en'].includes(value)){setLanguage(value);saveLanguage(value)}}
  const load=async()=>{
    try{setState(await ctx.rest('/status',{timeoutMs:10000}));setConnected(true);setError('')}
    catch(e){setConnected(false);setError(String(e.message||e))}
  }
  useEffect(()=>{
    let alive=true
    const tick=async()=>{
      try{const data=await ctx.rest('/status',{timeoutMs:10000});if(alive){setConnected(true);setState(data);setError('')}}
      catch(e){if(alive){setConnected(false);setError(String(e.message||e))}}
    }
    tick()
    const timer=setInterval(tick,1500)
    const clock=setInterval(()=>setNow(Date.now()),1000)
    return()=>{alive=false;clearInterval(timer);clearInterval(clock)}
  },[])
  async function act(path,body){
    setBusy(true);setError('')
    try{await ctx.rest(path,{method:'POST',body,timeoutMs:30000});await load()}
    catch(e){setError(String(e.message||e))}
    finally{setBusy(false)}
  }
  useEffect(()=>{setHead(state?.selected?.mtp_head||'');setProj(state?.selected?.mmproj||'')},[state?.model])
  const running=state?.state==='running'
  const toggleDisabled=!connected||!state?.owns_router||busy||running||state?.recovery_needed||!state?.selected?.mtp_supported
  const done=state?.done||0, total=state?.total||0
  const stageKind=state?.step_kind||'idle'
  const stageName=tr('stage_'+(running?stageKind:state?.state==='error'?'error':state?.state==='cancelled'?'cancelled':state?.state==='done'?'finished':'idle'))
  const elapsedNow=(field)=>{
    const start=state?.[field]
    return typeof start==='number'?Math.max(0,(now/1000)-start):null
  }
  const runElapsed=elapsedNow('run_started_at'), stageElapsed=elapsedNow('stage_started_at')
  const live=state?.live_tokens
  const hasLive=running&&stageKind==='request'&&typeof live==='number'
  const tokenCap=state?.live_token_limit
  const taskDetails=state?.current_task ? [state.current_task, state?.current_group?'('+groupText(state.current_group)+')':'',state?.trial?'· '+tr('repeat')+' '+state.trial+'/'+state.trials:''].filter(Boolean).join(' ') : ''
  return h('div',{style:{maxWidth:980,padding:'18px 24px',fontSize:14,color:'var(--ui-text-primary)',overflow:'auto',height:'100%'}},
    h('style',{},'@keyframes mtp-lab-scan { 0% { transform:translateX(-120%); } 50% { transform:translateX(150%); } 100% { transform:translateX(360%); } }'),
    h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:16,flexWrap:'wrap'}},
      h('div',{},h('h2',{style:{fontSize:21,fontWeight:700,marginBottom:5}},tr('title')+' · v0.3.0'),h('p',{style:muted},tr('intro'))),
      h('label',{style:{...muted,display:'flex',alignItems:'center',gap:8},htmlFor:'mtp-lab-language'},
        tr('language'),h('select',{id:'mtp-lab-language',value:language,'aria-label':tr('language'),onChange:e=>changeLanguage(e.target.value),style:{...btn,margin:0,minWidth:145}},
          h('option',{value:'auto'},tr('languageAuto')),h('option',{value:'ru'},tr('languageRu')),h('option',{value:'en'},tr('languageEn'))))),
    !connected?h('section',{style:{...block,borderColor:'#d59c45'}},h('strong',{},tr('connectTitle')),h('p',{style:muted},tr('connectHelp')),h('button',{style:btn,onClick:()=>load()},tr('checkConnection'))):null,
    connected&&!state?.owns_router?h('section',{style:{...block,borderColor:'#d59c45'}},h('strong',{},tr('notOwner')),h('p',{style:muted},tr('notOwnerHelp')),h('button',{style:btn,onClick:()=>load()},tr('refresh'))):null,
    state?.recovery_needed&&!running?h('section',{style:{...block,borderColor:'var(--ui-danger, #bf7777)'}},h('strong',{},tr('interrupted')),h('p',{style:muted},tr('interruptedHelp',state.pending_original_mtp?'ON':'OFF')),h('button',{style:btn,disabled:busy,onClick:()=>act('/recover',{})},tr('restore'))):null,
    h('section',{style:block},
      h('label',{style:{display:'block',fontWeight:650}},tr('chooseModel')),
      h('select',{value:state?.model||'',disabled:busy||running||!connected,
        onChange:async e=>{const id=e.target.value;if(id)await act('/select',{model_id:id})},
        style:{...btn,width:'98%',maxWidth:800}},
        h('option',{value:''},tr('noModel')),
        ...(state?.models||[]).map(m=>h('option',{key:m.id,value:m.id},m.id))),
      state?.selected?h('div',{style:{...muted,marginTop:7}},tr('support')+': '+(state.selected.mtp_supported?tr('supported'):tr('unsupported'))+' · '+(state.selected.has_mmproj?tr('imageEnabled'):tr('textOnly'))):null,
      h('p',{style:muted},tr('configHint')),
      h('label',{style:{...muted,display:'block'}},tr('headLabel')),
      h('input',{value:head,onChange:e=>setHead(e.target.value),disabled:busy||running||!state?.model,style:{...btn,width:'98%',maxWidth:800}}),
      h('label',{style:{...muted,display:'block'}},tr('projLabel')),
      h('input',{value:proj,onChange:e=>setProj(e.target.value),disabled:busy||running||!state?.model,style:{...btn,width:'98%',maxWidth:800}}),
      h('button',{style:btn,disabled:busy||running||!state?.owns_router||!state?.model,
        onClick:()=>act('/configure',{mtp_head:head,mmproj:proj})},tr('saveCompanions'))),
    h('section',{style:block},h('div',{style:{fontWeight:650,marginBottom:6}},tr('control')),
      h('div',{},tr('flag')+': ',h('strong',{},state?.mtp_flag===true?'ON':state?.mtp_flag===false?'OFF':'—'),' · '+tr('owner')+': ',h('strong',{},state?.owns_router?tr('currentHermes'):tr('unconfirmed'))),
      h('p',{style:muted},tr('toggleHelp')) ,h('p',{style:muted},tr('sessionOnly')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/toggle',{enabled:true})},tr('enable')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/toggle',{enabled:false})},tr('disable'))),
    h('section',{style:block},h('div',{style:{fontWeight:650,marginBottom:6}},tr('compare')),
      h('p',{style:muted},tr('compareHelp')+' '+(state?.selected?.has_mmproj?'':tr('textOnly'))),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/start',{trials:1})},tr('quick')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/start',{trials:3})},tr('full')),
      h('button',{style:btn,disabled:!running||busy,onClick:()=>act('/cancel',{})},tr('stop')),
      h('div',{style:{marginTop:14,display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}},
        h('strong',{},running?tr('executing'):stageName),
        running?h('span',{style:pill},tr('phase')+' '+(state?.phase||'—')):null,
        running?h('span',{style:pill},tr('overall')+' '+fmtSec(runElapsed)):null),
      h(Bar,{value:total?100*done/total:0}),
      h('div',{style:{...muted,marginTop:5}},tr('count',done,total,total?Math.round(done/total*100):0)),
      running?h('div',{style:{marginTop:12,padding:'12px',border:'1px solid var(--ui-stroke-secondary)',borderRadius:9}},
        h('div',{style:{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}},
          h('strong',{},stageName),h('span',{style:{fontVariantNumeric:'tabular-nums'}},tr('stageTime')+': '+fmtSec(stageElapsed))),
        taskDetails?h('div',{style:{...muted,marginTop:4}},tr('task')+': '+taskDetails):null,
        hasLive?h('div',{style:{marginTop:10}},h('div',{style:muted},tr('serverCounter')+': '+live+' '+tr('tokens')+(typeof tokenCap==='number'?' · '+tr('limit')+' '+tokenCap:'')),
          h(Bar,{value:typeof tokenCap==='number'&&tokenCap>0?100*live/tokenCap:0}),h('div',{style:muted},tr('tokenDisclaimer')))
          :h('div',{style:{marginTop:8}},h(Bar,{indeterminate:true}),h('div',{style:muted},stageKind==='loading'?tr('loadingHint'):stageKind==='request'?tr('requestHint'):tr('otherHint')))
      ):null,
      h('p',{style:{...muted,marginTop:11}},tr('modesNotice'))),
    error?h('div',{style:{...block,color:'var(--ui-danger, #e07575)'}},tr('error')+': '+error):null,
    state?.error?h('div',{style:{...block,color:'var(--ui-danger, #e07575)'}},tr('error')+': '+state.error):null,
    state?.summary?.length?h('section',{style:block},h('div',{style:{fontWeight:700,marginBottom:9}},tr('result')),
      h('div',{style:{overflowX:'auto'}},h('table',{style:{width:'100%',borderCollapse:'collapse',textAlign:'left'}},
        h('thead',{},h('tr',{},['workload','offSpeed','onSpeed','speedup','accepted'].map((key,i)=>h('th',{key:i,style:{padding:7,borderBottom:'1px solid var(--ui-stroke-secondary)'}},tr(key))))),
        h('tbody',{},state.summary.map((s,i)=>h('tr',{key:i},[groupText(s.group),s.off_tps??'—',s.on_tps??'—',s.speedup==null?'—':s.speedup+'×',s.on_accepted+'/'+s.on_drafted].map((v,j)=>h('td',{key:j,style:{padding:7,borderBottom:'1px solid var(--ui-stroke-secondary)'}},v))))))),
      h('p',{style:muted},tr('comparable')+': '+tr(state?.comparable?'yes':'no')),
      !state?.comparable?h('p',{style:{...muted,color:'var(--ui-danger,#b77d4c)'}},tr('comparableWarning')):null,
      h('p',{style:muted},tr('reports')+': '+state?.report_path),
      h('p',{style:muted},tr('restored')+': '+(state?.restored?tr('yes'):tr('restoreCheck')))):null,
    state?.status_warning?h('div',{style:muted},tr('error')+': '+state.status_warning):null
  )
}

export default {
  id:ID,
  name:'MTP Lab — Automatic Benchmark',
  description:'Model-agnostic MTP OFF/ON benchmark with Russian/English UI and live progress.',
  defaultEnabled:false,
  register(ctx) {
    // The same SDK i18n registration and per-plugin override pattern as ChatVault.
    ctx.i18n.register(STRINGS)
    const render=()=>h(LabView,{ctx})
    ctx.registerMany([
      {id:'page',area:ROUTES_AREA,title:'MTP Lab',data:{path:'/mtp-lab'},render},
      {id:'nav',area:SIDEBAR_NAV_AREA,order:55,data:{path:'/mtp-lab',label:'MTP Lab',codicon:'pulse'}},
      {id:'open',area:PALETTE_AREA,data:{id:'mtp-lab.open',label:'MTP Lab',keywords:['mtp','speculative','benchmark','gguf','бенчмарк'],run:()=>host.navigate('/mtp-lab')}}
    ])
    ctx.registerSettingsPage?.({id:'lab',title:'MTP Lab',icon:'pulse',order:20,render})
  }
}
