import React, { useEffect, useState } from 'react'
import { ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, host, usePluginI18n } from '@hermes/plugin-sdk'

// Desktop-only strings. The Python API intentionally returns stable machine-readable
// stage codes and raw diagnostic details; the active UI language never changes a run.
const ID = 'hermes-mtp-lab'
const PREF_KEY = 'hermes-mtp-lab:language'
const API_VERSION = '0.5.1'
const STRINGS = {
  ru: {
    language:'Язык', languageAuto:'Авто / Hermes', languageRu:'Русский', languageEn:'English',
    title:'Hermes MTP Lab', intro:'Универсальный локальный A/B-бенчмарк моделей, поддерживающих MTP, через управляемый llama.cpp Hermes. Пользовательские чаты не изменяются.',
    connectTitle:'Python API недоступен', connectHelp:'Desktop-плагин загружен, но Python-бэкенд должен быть разрешён через Hermes CLI. Полностью перезапустите Hermes.',
    checkConnection:'Проверить подключение', notOwner:'Локальный сервер не принадлежит текущему Hermes', notOwnerHelp:'Python API отвечает, но не подтвердил право управлять llama.cpp. Переключение заблокировано, чтобы не затронуть чужие процессы.', refresh:'Обновить статус',
    interrupted:'Обнаружен незавершённый тест — требуется восстановление', interruptedHelp:(flag)=>'Обнаружен аварийный маркер предыдущего запуска. Исходное состояние MTP: '+flag+'. Во время активного теста это предупреждение не показывается.', restore:'Восстановить исходный MTP',
    control:'Управление MTP', flag:'Флаг', owner:'Владелец сервера', currentHermes:'текущий Hermes', unconfirmed:'не подтверждён', toggleHelp:'Переключение перезапускает только управляемый локальный runtime. Завершите генерацию в других чатах.', enable:'Включить MTP', disable:'Отключить MTP',
    compare:'Контрольный MTP-бенчмарк', reasoningLabel:'Режим reasoning', reasoningOff:'Без reasoning (для оценки качества; зависит от шаблона модели)', reasoningNative:'Обычный режим модели (измерение с reasoning)', comparableUnknown:'неизвестно (нет части флагов)', comparableMismatch:'нет (известные параметры различаются)', comparableMatched:'да (все проверяемые поля совпадают)', compareHelp:'Каждый цикл: два OFF и два ON на задание; порядок фаз чередуется между циклами. Отдельно сравниваются видимые ответы и reasoning. Фиксированные лимиты 768–1536 токенов, без повторов при обрыве. Может длиться долго, особенно при CPU-offload.', quick:'Контроль · 1 цикл (4×)', full:'Углублённый · 3 цикла (12×)', stop:'Остановить после текущего запроса',
    executing:'Тест выполняется', phase:'Фаза', overall:'Всего', completed:'Завершено измерений', count:(done,total,pct)=>`${done} / ${total} измерений завершено${total?' · '+pct+'%':''}`, stageTime:'Время этапа', task:'Задание', repeat:'повтор',
    serverCounter:'Счётчик сервера', tokens:'токенов', limit:'лимит', tokenDisclaimer:'Счётчик генерации не гарантирует процент готовности ответа. При нестриминговом API обновления могут запаздывать.',
    loadingHint:'Модель загружается. Сервер не предоставляет достоверный процент загрузки.', requestHint:'Ожидание счётчиков сервера. Различить подготовку ответа и внутреннее размышление модели невозможно.', otherHint:'Этап выполняется. Достоверный процент внутри этапа недоступен.',
    modesNotice:'Реальные режимы чата Hermes: Auto, Native, Text. Этот бенчмарк НЕ переключает их: категории обозначают типы нагрузок llama.cpp, а не режимы интерфейса.',
    result:'Результаты', workload:'Нагрузка', offSpeed:'OFF ток/с', onSpeed:'ON ток/с', speedup:'Ускорение', accepted:'MTP принято', comparable:'Параметры OFF/ON совпадают', yes:'да', no:'нет / неизвестно', comparableWarning:'Это наблюдаемое ускорение: некоторые параметры OFF/ON различаются либо не подтверждены. Подробности — в summary.md.', reports:'Отчёты', parityHeading:'Проверка совпадения ответов', parityPair:'Пара', parityVisible:'Совпал видимый текст', parityReasoning:'Совпал reasoning', parityNote:'Несовпадение ответа — диагностический сигнал, а не автоматический провал качества. Полные тексты и оценки — в answers.jsonl и comparisons.json.', qualityHeading:'Проверка качества', hardwareHeading:'Аппаратная диагностика', hardwareNote:'VRAM глобальная по GPU, а не память модели. Фактическое число слоёв на GPU неизвестно без логов загрузки движка.', gpuLayersArg:'Флаг GPU layers', engineVersion:'Версия llama.cpp', qualityNote:'PASS только для проверяемых задач; код запускается исключительно в доступном локальном Docker-песочнике. Без него UNVERIFIED. Творческие и технические тексты требуют ручной оценки.', qualityPass:'Подтверждено', qualityFail:'Не прошло', qualityUnverified:'Не проверено', qualityManual:'Ручная оценка', qualityIncomplete:'Обрезано лимитом', restored:'Исходный MTP восстановлен', restoreCheck:'НЕТ — проверьте журнал и резервную копию', error:'Ошибка',
    stage_idle:'Готов к тестированию', stage_checking:'Проверка окружения', stage_switch:'Переключение MTP и запуск сервера', stage_loading:'Загрузка модели и выделение памяти', stage_warmup:'Прогрев модели', stage_preparing:'Подготовка запроса', stage_request:'Обработка запроса и генерация', stage_restore:'Восстановление настроек', stage_report:'Создание отчётов', stage_finished:'Тест завершён', stage_error:'Тест завершился с ошибкой', stage_cancelled:'Тест остановлен',
    chooseModel:'Модель Hermes', noModel:'— выбери модель —', support:'MTP-совместимость',supported:'Поддержка обнаружена', unsupported:'Нет подтверждённой MTP-конфигурации', embeddedReady:'MTP встроен в GGUF — отдельная MTP-head не требуется', embeddedPreset:'MTP настроена в пресете Hermes; встроенные слои не подтверждены по метаданным GGUF', externalHead:'Внешняя MTP-head привязана (совместимость проверяется тестом)', mtpUnknown:'MTP не обнаружена — необходима совместимая MTP-head', headCandidates:'Найденные MTP-head', headBind:'Привязать выбранную MTP-head', headNone:'Рядом с моделью MTP-head не найдена — укажи файл через «Обзор…»', missingHead:'Привязанная MTP-head отсутствует или недоступна', scanFolder:'Поиск рядом с GGUF из пресета Hermes', versionMismatch:'Интерфейс MTP Lab обновлён, но Python API Hermes использует старую версию. Полностью закрой Hermes, включая трей, и запусти заново. Обновление Desktop-плагина само по себе не перезапускает backend.', candidates:'Найденные mmproj', recommended:'Рекомендован по имени файла — проверь совместимость', maybeCompatible:'Возможный вариант — совместимость не подтверждена', bindProjector:'Привязать выбранный mmproj', browseFile:'Обзор…', filePickerUnavailable:'Текущая версия Hermes Desktop не поддерживает системный диалог открытия файла (ctx.os.pickOpenPath). Обнови Hermes Desktop; папку запрашивать не будем.', invalidFile:'Нужно выбрать файл GGUF (.gguf)', selectedFile:'Файл выбран. Для применения нажми «Сохранить связь компаньонов».', pickHead:'Выбрать файл MTP-head GGUF', pickProjector:'Выбрать файл mmproj GGUF', noCandidates:'Рядом с моделью mmproj не найден — укажи файл через «Обзор…»', folderError:'Не удалось прочитать выбранную папку', compatibilityNote:'Совпадение имени не гарантирует совместимость; выбор требует подтверждения', projectorSaved:'Компаньон сохранён; проверь, что Hermes применил его после перезапуска', headLabel:'MTP-head GGUF (пусто для встроенной MTP)', projLabel:'mmproj GGUF (необязательно)', saveCompanions:'Сохранить связь компаньонов', configHint:'Плагин ищет mmproj и MTP-head рядом с моделью. Кнопки «Обзор…» позволяют выбрать конкретный GGUF-файл; диалог запоминает последнюю папку. Компаньоны подключаются только после подтверждения. После установки нового плагина полностью перезапусти Hermes, чтобы загрузился Python API.', textOnly:'Только текстовые задания (mmproj отсутствует)', imageEnabled:'Визуальные задания включены', sessionOnly:'Ручное переключение действует в текущем сеансе; для постоянной настройки используй штатные настройки модели Hermes.', group_text:'Текст', group_code:'Код и данные', group_scene:'Описание изображения', group_ground:'Распознавание деталей', open:'Открыть MTP Lab'
  },
  en: {
    language:'Language', languageAuto:'Auto / Hermes', languageRu:'Русский', languageEn:'English',
    title:'Hermes MTP Lab', intro:'Model-agnostic A/B benchmarking for MTP-capable local models through Hermes-managed llama.cpp. Your chats are not modified.',
    connectTitle:'Python API unavailable', connectHelp:'The Desktop extension is loaded, but its Python backend must also be enabled through Hermes CLI. Fully restart Hermes.',
    checkConnection:'Check connection', notOwner:'Local server is not owned by this Hermes process', notOwnerHelp:'The Python API is reachable, but ownership of the running llama.cpp process is not confirmed. Switching is disabled to protect unrelated processes.', refresh:'Refresh status',
    interrupted:'Unfinished previous benchmark — recovery required', interruptedHelp:(flag)=>'A recovery marker was left by an earlier run. Original MTP state: '+flag+'. This warning is hidden during a healthy active run.', restore:'Restore original MTP setting',
    control:'MTP controls', flag:'Flag', owner:'Server owner', currentHermes:'current Hermes', unconfirmed:'not confirmed', toggleHelp:'Switching restarts only the managed local runtime. Finish generation in other chats before switching.', enable:'Enable MTP', disable:'Disable MTP',
    compare:'Controlled MTP benchmark', reasoningLabel:'Reasoning mode', reasoningOff:'Request no reasoning (for quality; template-dependent)', reasoningNative:'Native model reasoning (full thinking workload)', comparableUnknown:'unknown (some flags not exposed)', comparableMismatch:'no (known settings differ)', comparableMatched:'yes (all inspected flags matched)', compareHelp:'Each cycle runs two OFF and two ON requests per task; phase order alternates between cycles. Visible output and reasoning are compared separately. Fixed 768–1536-token caps with no adaptive retries on truncation. Can take a long time with CPU offload.', quick:'Control · 1 cycle (4×)', full:'Extended · 3 cycles (12×)', stop:'Stop after current request',
    executing:'Benchmark running', phase:'Phase', overall:'Total', completed:'Completed measurements', count:(done,total,pct)=>`${done} / ${total} measurements completed${total?' · '+pct+'%':''}`, stageTime:'Stage elapsed', task:'Task', repeat:'repeat',
    serverCounter:'Server token counter', tokens:'tokens', limit:'limit', tokenDisclaimer:'The generation counter is not a reliable percentage of answer completion. Non-streaming responses may delay metric updates.',
    loadingHint:'The model is loading. The server does not provide a reliable loading percentage.', requestHint:'Waiting for server counters. Answer preparation and internal model reasoning cannot be distinguished reliably.', otherHint:'This stage is active. No reliable internal percentage is available.',
    modesNotice:'Hermes chat modes are Auto, Native and Text. This benchmark does NOT switch among them; groups represent llama.cpp workload types, not chat UI modes.',
    result:'Results', workload:'Workload', offSpeed:'OFF tok/s', onSpeed:'ON tok/s', speedup:'Speedup', accepted:'MTP accepted', comparable:'OFF/ON parameters identical', yes:'yes', no:'no / unknown', comparableWarning:'Speedup is observational: some OFF/ON parameters differ or could not be verified. Details are in summary.md.', reports:'Reports', parityHeading:'Output reproducibility', parityPair:'Pair', parityVisible:'Visible matches', parityReasoning:'Reasoning matches', parityNote:'A mismatch is a diagnostic signal, not an automatic quality failure. Full texts and checks are in answers.jsonl and comparisons.json.', qualityHeading:'Quality assessment', hardwareHeading:'Hardware diagnostics', hardwareNote:'GPU VRAM shown is system-wide, not per-model. Actual number of GPU-offloaded layers is unknown without engine load logs.', gpuLayersArg:'GPU layers launch flag', engineVersion:'llama.cpp build', qualityNote:'PASS only for reference-checkable tasks; generated code runs only inside a locally cached Docker sandbox. Without it quality stays UNVERIFIED. Open-ended answers need human review.', qualityPass:'Verified', qualityFail:'Failed', qualityUnverified:'Unverified', qualityManual:'Manual review', qualityIncomplete:'Token-limited', restored:'Original MTP restored', restoreCheck:'NO — check the log and backup', error:'Error',
    stage_idle:'Ready to benchmark', stage_checking:'Checking environment', stage_switch:'Switching MTP and starting server', stage_loading:'Loading model and allocating memory', stage_warmup:'Warming up model', stage_preparing:'Preparing request', stage_request:'Processing request and generating answer', stage_restore:'Restoring original settings', stage_report:'Writing reports', stage_finished:'Benchmark completed', stage_error:'Benchmark failed', stage_cancelled:'Benchmark stopped',
    chooseModel:'Hermes model', noModel:'— select a model —',support:'MTP compatibility',supported:'Support detected',unsupported:'No confirmed MTP configuration',embeddedReady:'MTP embedded in GGUF — separate MTP head not required',embeddedPreset:'MTP configured in Hermes preset; embedded layers not confirmed by GGUF metadata',externalHead:'External MTP head linked (test required to verify)',mtpUnknown:'MTP not detected — compatible MTP head required',headCandidates:'Discovered MTP-head files', headBind:'Link selected MTP head', headNone:'No MTP-head found next to the model — select a GGUF with Browse', missingHead:'Linked MTP head is missing or not accessible', scanFolder:'Scanning GGUF folder from Hermes preset', versionMismatch:'MTP Lab Desktop has updated but Hermes Python API is still the previous version. Quit Hermes completely, including the tray, and reopen it. Updating the Desktop plugin does not restart the backend.', candidates:'Discovered mmproj files',recommended:'Best filename match — verify compatibility',maybeCompatible:'Possible match — compatibility not confirmed',bindProjector:'Link selected mmproj',browseFile:'Browse…', filePickerUnavailable:'This Hermes Desktop build does not expose the native open-file dialog (ctx.os.pickOpenPath). Update Hermes Desktop; folder access will not be requested.', invalidFile:'Choose a GGUF (.gguf) file', selectedFile:'File selected. Click Save companion links to apply it.', pickHead:'Select an MTP-head GGUF file', pickProjector:'Select an mmproj GGUF file',noCandidates:'No mmproj found next to the model — select a GGUF with Browse',folderError:'Could not read selected folder',compatibilityNote:'Name matching does not establish compatibility; confirm the selection',projectorSaved:'Companion saved; verify Hermes has loaded it after restart',headLabel:'MTP head GGUF (empty for embedded MTP)',projLabel:'mmproj GGUF (optional)',saveCompanions:'Save companion links',configHint:'Find nearby mmproj and MTP-head files or choose a GGUF file using Browse. The last folder is remembered. Companion links are saved only on confirmation. Fully restart Hermes after installing a plugin update so the Python API reloads.',textOnly:'Text-only tasks (no mmproj)',imageEnabled:'Vision tasks enabled',sessionOnly:'Manual toggles affect the current session; use native Hermes model settings for persistent changes.', group_text:'Text', group_code:'Code and data', group_scene:'Image description', group_ground:'Visual details', open:'Open MTP Lab'
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
const LAST_BROWSE_DIR = 'companionPickerLastDirectory'
// The OS picker returns a full local path. Keep the previous successful directory
// across restarts, regardless of whether the user chose MTP-head or mmproj.
function directoryOf(path) {
  if (typeof path !== 'string') return ''
  const value = path.trim()
  const at = Math.max(value.lastIndexOf('\\'),value.lastIndexOf('/'))
  return at >= 0 ? value.slice(0,at) : ''
}
function pickerStartDir(ctx, selectedPath, modelPath) {
  let remembered = ''
  try { remembered = ctx.storage?.get(LAST_BROWSE_DIR, '') || '' } catch { /* older shell */ }
  return remembered || directoryOf(modelPath) || directoryOf(selectedPath) || undefined
}
function rememberPickerDirectory(ctx, path) {
  const directory = directoryOf(path)
  if (directory) {
    try { ctx.storage?.set(LAST_BROWSE_DIR,directory) } catch { /* selection remains usable */ }
  }
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
  const [projectors,setProjectors]=useState([])
  const [projectorChoice,setProjectorChoice]=useState('')
  const [projectorNotice,setProjectorNotice]=useState('')
  const [busy, setBusy] = useState(false)
  const [connected, setConnected] = useState(false)
  const [now, setNow] = useState(Date.now())
  const [language,setLanguage] = useState(storedLanguage)
  const [reasoningMode,setReasoningMode] = useState('off')
  const [headOptions,setHeadOptions] = useState([])
  const [headChoice,setHeadChoice] = useState('')
  const [fileNotice,setFileNotice] = useState('')
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
    try{
      await ctx.rest(path,{method:'POST',body,timeoutMs:30000})
      if(path==='/configure'){setHead(body.mtp_head||'');setProj(body.mmproj||'');setFileNotice('')}
      await load()
    }
    catch(e){setError(String(e.message||e))}
    finally{setBusy(false)}
  }
  useEffect(()=>{setHead(state?.selected?.mtp_head||'');setProj(state?.selected?.mmproj||'');setFileNotice('')},[state?.model])
  // Projector and head candidates arrive with /status, which exists in every
  // supported backend. No extra /projectors endpoint that an old gateway 404s.
  const apiReady = state?.api_version === API_VERSION
  useEffect(()=>{
    setProjectors(apiReady && Array.isArray(state?.projector_candidates)?state.projector_candidates:[])
    setHeadOptions(apiReady && Array.isArray(state?.head_candidates)?state.head_candidates:[])
    const candidates=apiReady && Array.isArray(state?.projector_candidates)?state.projector_candidates:[]
    const good=candidates.filter(x=>x.recommendation==='strong')
    setProjectorChoice(good.length===1?good[0].path:'')
    setHeadChoice('')
    setProjectorNotice('')
  },[state?.model,state?.api_version])
  async function browseCompanionFile(kind){
    // A GGUF path is required by the Hermes backend, not a folder capability.
    // pickOpenPath returns a native absolute path and supports defaultPath.
    // Do not use requestFolder(): it displays a misleading permission grant.
    if(typeof ctx.os?.pickOpenPath!=='function'){
      setError(tr('filePickerUnavailable'));return
    }
    setBusy(true);setError('')
    try {
      const current=kind==='head'?head:proj
      const defaultPath=pickerStartDir(ctx,current,state?.selected?.model_path)
      const selected=await ctx.os.pickOpenPath({
        title:tr(kind==='head'?'pickHead':'pickProjector'),
        ...(defaultPath?{defaultPath}:{}),
        filters:[{name:'GGUF',extensions:['gguf']}]
      })
      // A cancel (null/empty) never clears an existing selection.
      if(!selected)return
      if(typeof selected!=='string'||!selected.toLowerCase().endsWith('.gguf')||!directoryOf(selected)){
        throw new Error(tr('invalidFile'))
      }
      rememberPickerDirectory(ctx,selected)
      if(kind==='head'){
        setHead(selected);setHeadChoice('')
      }else{
        setProj(selected);setProjectorChoice('');setProjectorNotice('')
      }
      setFileNotice(tr('selectedFile'))
    }catch(e){setError(String(e.message||e))}
    finally{setBusy(false)}
  }

  const running=state?.state==='running'
  const toggleDisabled=!connected||!apiReady||!state?.owns_router||busy||running||state?.recovery_needed||!state?.selected?.mtp_supported
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
  const taskDetails=state?.current_task ? [state.current_task, state?.current_group?'('+groupText(state.current_group)+')':'',state?.trial?'· '+tr('repeat')+' '+state.trial+'/'+state.trials:'', state?.replica?'· #'+state.replica+'/2':''].filter(Boolean).join(' ') : ''
  return h('div',{style:{maxWidth:980,padding:'18px 24px',fontSize:14,color:'var(--ui-text-primary)',overflow:'auto',height:'100%'}},
    h('style',{},'@keyframes mtp-lab-scan { 0% { transform:translateX(-120%); } 50% { transform:translateX(150%); } 100% { transform:translateX(360%); } }'),
    h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:16,flexWrap:'wrap'}},
      h('div',{},h('h2',{style:{fontSize:21,fontWeight:700,marginBottom:5}},tr('title')+' · v0.5.1'),h('p',{style:muted},tr('intro'))),
      h('label',{style:{...muted,display:'flex',alignItems:'center',gap:8},htmlFor:'mtp-lab-language'},
        tr('language'),h('select',{id:'mtp-lab-language',value:language,'aria-label':tr('language'),onChange:e=>changeLanguage(e.target.value),style:{...btn,margin:0,minWidth:145}},
          h('option',{value:'auto'},tr('languageAuto')),h('option',{value:'ru'},tr('languageRu')),h('option',{value:'en'},tr('languageEn'))))),
    !connected?h('section',{style:{...block,borderColor:'#d59c45'}},h('strong',{},tr('connectTitle')),h('p',{style:muted},tr('connectHelp')),h('button',{style:btn,onClick:()=>load()},tr('checkConnection'))):null,
    connected&&!state?.owns_router?h('section',{style:{...block,borderColor:'#d59c45'}},h('strong',{},tr('notOwner')),h('p',{style:muted},tr('notOwnerHelp')),h('button',{style:btn,onClick:()=>load()},tr('refresh'))):null,
    connected&&!apiReady?h('section',{style:{...block,borderColor:'#d59c45'}},h('strong',{},tr('versionMismatch'))):null,
    state?.recovery_needed&&!running?h('section',{style:{...block,borderColor:'var(--ui-danger, #bf7777)'}},h('strong',{},tr('interrupted')),h('p',{style:muted},tr('interruptedHelp',state.pending_original_mtp===true?'ON':state.pending_original_mtp===false?'OFF':'—')),h('button',{style:btn,disabled:busy,onClick:()=>act('/recover',{})},tr('restore'))):null,
    h('section',{style:block},
      h('label',{style:{display:'block',fontWeight:650}},tr('chooseModel')),
      h('select',{value:state?.model||'',disabled:busy||running||!connected||!apiReady,
        onChange:async e=>{const id=e.target.value;if(id)await act('/select',{model_id:id})},
        style:{...btn,width:'98%',maxWidth:800}},
        h('option',{value:''},tr('noModel')),
        ...(state?.models||[]).map(m=>h('option',{key:m.id,value:m.id},m.id))),
      state?.selected?h('div',{style:{...muted,marginTop:7}},
        h('span',{style:{color:state.selected.embedded_verified?'#16834d':state.selected.mtp_kind==='unsupported'?'var(--ui-danger,#b77d4c)':'var(--ui-text-secondary)',fontWeight:state.selected.embedded_verified?700:500}},
          state.selected.embedded_verified?tr('embeddedReady'):
          state.selected.mtp_kind==='external'?(state.selected.mtp_supported?tr('externalHead'):tr('missingHead')):
          state.selected.mtp_kind==='embedded'?tr('embeddedPreset'):tr('mtpUnknown')),
        ' · '+(state.selected.has_mmproj?tr('imageEnabled'):tr('textOnly'))):null,
      state?.selected?.model_path?h('p',{style:muted},tr('scanFolder')+': '+state.selected.model_path.replace(/[\\/][^\\/]+$/,'')):null,
      h('p',{style:muted},tr('configHint')),
      h('label',{style:{...muted,display:'block'}},tr('headLabel')),
      h('div',{style:{display:'flex',gap:6,alignItems:'center',maxWidth:800,flexWrap:'wrap'}},
        h('input',{value:head,onChange:e=>{setHead(e.target.value);setFileNotice('')},disabled:busy||running||!state?.model,style:{...btn,marginRight:0,flex:'1 1 320px',minWidth:180}}),
        h('button',{style:{...btn,marginRight:0},disabled:busy||running||!apiReady||!state?.model,onClick:()=>browseCompanionFile('head')},tr('browseFile'))),
      h('div',{style:{display:'flex',alignItems:'center',flexWrap:'wrap',gap:6,marginTop:5}},
        h('span',{style:{...muted,fontWeight:650}},tr('headCandidates'))),
      headOptions.length?h('div',{},
        h('select',{value:headChoice,disabled:busy||running,onChange:e=>setHeadChoice(e.target.value),style:{...btn,width:'71%',maxWidth:680},'aria-label':tr('headCandidates')},
          h('option',{value:''},'—'),...headOptions.map(c=>h('option',{key:c.path,value:c.path},c.name+(c.recommendation==='strong'?' ★':'')))),
        h('button',{style:btn,disabled:busy||running||!apiReady||!state?.owns_router||!headChoice,
          onClick:()=>act('/configure',{mtp_head:headChoice,mmproj:proj})},tr('headBind'))):
        h('p',{style:muted},tr('headNone')),

      h('div',{style:{display:'flex',alignItems:'center',flexWrap:'wrap',gap:6,marginTop:5}},
        h('span',{style:{...muted,fontWeight:650}},tr('candidates'))),
      projectors.length?h('div',{},
        h('select',{value:projectorChoice,disabled:busy||running,onChange:e=>setProjectorChoice(e.target.value),style:{...btn,width:'71%',maxWidth:680},'aria-label':tr('candidates')},
          h('option',{value:''},'—'),...projectors.map(c=>h('option',{key:c.path,value:c.path},c.name+(c.recommendation==='strong'?' ★':'')))),
        h('button',{style:btn,disabled:busy||running||!apiReady||!state?.owns_router||!projectorChoice,
          onClick:()=>act('/configure',{mtp_head:head,mmproj:projectorChoice})},tr('bindProjector')),
        h('p',{style:muted},tr('compatibilityNote'))):
        h('p',{style:muted},projectorNotice||tr('noCandidates')),
      h('label',{style:{...muted,display:'block'}},tr('projLabel')),
      h('div',{style:{display:'flex',gap:6,alignItems:'center',maxWidth:800,flexWrap:'wrap'}},
        h('input',{value:proj,onChange:e=>{setProj(e.target.value);setFileNotice('')},disabled:busy||running||!state?.model,style:{...btn,marginRight:0,flex:'1 1 320px',minWidth:180}}),
        h('button',{style:{...btn,marginRight:0},disabled:busy||running||!apiReady||!state?.model,onClick:()=>browseCompanionFile('projector')},tr('browseFile'))),
      fileNotice?h('p',{style:{...muted,color:'var(--ui-accent)'}},fileNotice):null,
      h('button',{style:btn,disabled:busy||running||!apiReady||!state?.owns_router||!state?.model,
        onClick:()=>act('/configure',{mtp_head:head,mmproj:proj})},tr('saveCompanions'))),
    h('section',{style:block},h('div',{style:{fontWeight:650,marginBottom:6}},tr('control')),
      h('div',{},tr('flag')+': ',h('strong',{},state?.mtp_flag===true?'ON':state?.mtp_flag===false?'OFF':'—'),' · '+tr('owner')+': ',h('strong',{},state?.owns_router?tr('currentHermes'):tr('unconfirmed'))),
      h('p',{style:muted},tr('toggleHelp')) ,h('p',{style:muted},tr('sessionOnly')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/toggle',{enabled:true})},tr('enable')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/toggle',{enabled:false})},tr('disable'))),
    h('section',{style:block},h('div',{style:{fontWeight:650,marginBottom:6}},tr('compare')),
      h('p',{style:muted},tr('compareHelp')+' '+(state?.selected?.has_mmproj?'':tr('textOnly'))),
      h('label',{style:{...muted,display:'flex',alignItems:'center',gap:8,marginBottom:10}},
        tr('reasoningLabel'),
        h('select',{value:reasoningMode,onChange:e=>setReasoningMode(e.target.value),
          disabled:running||busy,style:{...btn,maxWidth:610,width:'75%'}},
          h('option',{value:'off'},tr('reasoningOff')),
          h('option',{value:'native'},tr('reasoningNative')))),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/start',{trials:1,reasoning_mode:reasoningMode})},tr('quick')),
      h('button',{style:btn,disabled:toggleDisabled,onClick:()=>act('/start',{trials:3,reasoning_mode:reasoningMode})},tr('full')),
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
      h('p',{style:muted},tr('comparable')+': '+tr(state?.comparability?.status==='matched'?'comparableMatched':state?.comparability?.status==='mismatch'?'comparableMismatch':'comparableUnknown')),
      state?.comparability?.status!=='matched'?h('p',{style:{...muted,color:'var(--ui-danger,#b77d4c)'}},
        tr('comparableWarning')+' '+(state?.comparability?.unknown_fields||[]).join(', ')+
        ' '+Object.keys(state?.comparability?.differences||{}).join(', ')):null,
      h('p',{style:muted},tr('reports')+': '+state?.report_path),
      h('p',{style:muted},tr('restored')+': '+(state?.restored?tr('yes'):tr('restoreCheck'))),
      state?.parity?h('div',{style:{marginTop:12}},
        h('strong',{},tr('parityHeading')),
        h('table',{style:{width:'100%',marginTop:5,textAlign:'left'}},
          h('thead',{},h('tr',{},[tr('parityPair'),tr('parityVisible'),tr('parityReasoning')].map((x,i)=>h('th',{key:i,style:{padding:5}},x)))),
          h('tbody',{},Object.entries(state.parity).map(([k,v])=>h('tr',{key:k},
            [k,(v.same_visible||0)+'/'+(v.pairs||0),(v.same_reasoning||0)+'/'+(v.pairs||0)].map((x,i)=>h('td',{key:i,style:{padding:5}},x)))))),
        h('p',{style:muted},tr('parityNote'))):null,
      state?.quality_counts?h('div',{style:{marginTop:12}},h('strong',{},tr('qualityHeading')),
        h('p',{style:muted},[tr('qualityPass')+': '+(state.quality_counts.pass||0),
          tr('qualityFail')+': '+(state.quality_counts.fail||0),
          tr('qualityUnverified')+': '+(state.quality_counts.unverified||0),
          tr('qualityManual')+': '+(state.quality_counts.manual_review||0),
          tr('qualityIncomplete')+': '+(state.quality_counts.incomplete||0)].join(' · ')),
        h('p',{style:muted},tr('qualityNote'))):null,
      state?.hardware_info?h('div',{style:{marginTop:12}},h('strong',{},tr('hardwareHeading')),
        h('p',{style:muted},tr('engineVersion')+': '+(state.hardware_info.engine_version||'—')+' · '+tr('gpuLayersArg')+': '+(state.hardware_info.gpu_layers_arg||'—')),
        ...(state.hardware_info.gpu?.gpus||[]).map((g,i)=>h('p',{key:i,style:muted},g.name+': '+(g.vram_used_global_mib??'—')+'/'+(g.vram_total_mib??'—')+' MiB · GPU '+(g.utilization_gpu_pct??'—')+'%')),
        h('p',{style:muted},tr('hardwareNote'))):null):null,
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
