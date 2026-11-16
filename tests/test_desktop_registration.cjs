const fs=require('fs'), vm=require('vm'), assert=require('assert')
const src=fs.readFileSync(require('path').join(__dirname,'../desktop/plugin.js'),'utf8')
assert(src.includes("from '@hermes/plugin-sdk'"),'official SDK import missing')
assert(src.includes('usePluginI18n'),'Hermes localization hook missing')
assert(src.includes('export default {'),'default export missing')
const stripped=src.replace(/^import .*?\n/gm,'').replace('export default {','globalThis.TEST_PLUGIN = {')+'\nglobalThis.TEST_LABVIEW = LabView;'
const contributions=[],settings=[]
let translations=null,language='ru'
const store=new Map()
const ctx={registerMany(x){contributions.push(...x)},registerSettingsPage(x){settings.push(x)},i18n:{register(x){translations=x}}}
const React={createElement:(...args)=>({type:args[0],props:args[1]||{},children:args.slice(2)})}
const sandbox={React,useEffect(){},useState(){return [null,()=>{}]},
  usePluginI18n(){return(key,...args)=>{const entry=translations[language][key];return typeof entry==='function'?entry(...args):(entry??key)}},
  localStorage:{getItem(k){return store.get(k)||null},setItem(k,v){store.set(k,v)}},
  ROUTES_AREA:'routes',SIDEBAR_NAV_AREA:'sidebar.nav',PALETTE_AREA:'palette',host:{navigate(){}},
  setInterval(){},clearInterval(){},Date
}
vm.runInNewContext(stripped,sandbox,{filename:'plugin.js'})
assert(sandbox.TEST_PLUGIN.id==='hermes-mtp-lab')
sandbox.TEST_PLUGIN.register(ctx)
assert(translations&&translations.ru&&translations.en,'English and Russian translation registration missing')
const page=contributions.find(c=>c.area==='routes'&&c.data.path==='/mtp-lab')
const nav=contributions.find(c=>c.area==='sidebar.nav'&&c.data.path==='/mtp-lab')
assert(page,'Missing full-page route')
assert(nav&&nav.data.label==='MTP Lab','Missing sidebar navigation')
assert(typeof page.render==='function'&&page.render(),'Missing route render')
assert(settings.length===1&&typeof settings[0].render==='function','Settings entry missing')
function treeText(node){
  if(node==null)return ''
  if(typeof node==='string'||typeof node==='number')return String(node)
  if(Array.isArray(node))return node.map(treeText).join(' ')
  return treeText(node.children)
}
function findNode(node,fn){
  if(!node||typeof node!=='object')return null
  if(fn(node))return node
  for(const n of node.children||[]){const result=findNode(n,fn);if(result)return result}
  return null
}
function renderFor(state,selected='ru',sdkLocale='ru'){
  language=sdkLocale;let k=0
  sandbox.useState=()=>{const i=k++;const values=[state,'','','',[], '', '',false,true,Date.now(),selected,'off',[],''];return[values[i],()=>{}]}
  return sandbox.TEST_LABVIEW({ctx:{rest:async()=>state}})
}
const running={state:'running',recovery_needed:true,phase:'OFF',step_kind:'loading',stage:'Загрузка модели',done:0,total:12,run_started_at:Date.now()/1000-13,stage_started_at:Date.now()/1000-3}
const ruTree=renderFor(running)
const ru=treeText(ruTree)
assert(!ru.includes('Обнаружен незавершённый тест'),'false interrupted warning during active run')
assert(ru.includes('Загрузка модели'),'Russian load stage not displayed')
assert(ru.includes('Время этапа'),'Russian stage timer missing')
assert(ru.includes('Auto, Native, Text'),'actual Hermes chat modes not identified')
assert(!ru.includes('Vision-Image'),'nonexistent UI mode leaked')
const crashedRu=treeText(renderFor({state:'idle',recovery_needed:true,pending_original_mtp:true}))
assert(crashedRu.includes('Обнаружен незавершённый тест'),'genuine interruption warning missing')
const en=treeText(renderFor(running,'en','ru'))
assert(en.includes('Loading model and allocating memory'),'English load stage missing')
assert(en.includes('Stage elapsed'),'English stage timer missing')
assert(!en.includes('Загрузка модели'),'Russian runtime stage leaked into English display')
const enCrash=treeText(renderFor({state:'idle',recovery_needed:true,pending_original_mtp:true},'en','ru'))
assert(enCrash.includes('Unfinished previous benchmark'),'English interrupted-run message missing')
const autoEnglish=treeText(renderFor(running,'auto','en'))
assert(autoEnglish.includes('Loading model'),'Auto mode does not follow Hermes English locale')
const autoRussian=treeText(renderFor(running,'auto','ru'))
assert(autoRussian.includes('Загрузка модели'),'Auto mode does not follow Hermes Russian locale')
const sel=findNode(renderFor(running,'ru'),node=>node.type==='select'&&node.props.id==='mtp-lab-language')
assert(sel&&sel.props.value==='ru','Language selector not present')
sel.props.onChange({target:{value:'en'}})
assert(store.get('hermes-mtp-lab:language')==='en','Manual language was not persisted')
const sumState={state:'done',done:12,total:12,comparable:false,restored:true,
  summary:[{group:'Описание изображения',off_tps:30.76,on_tps:80.74,speedup:2.625,on_accepted:175,on_drafted:250}]}
const summaryEn=treeText(renderFor(sumState,'en'))
assert(summaryEn.includes('Image description'),'English workload names not localized')
assert(summaryEn.includes('Speedup'),'Results headings not translated')
assert(!summaryEn.includes('Описание изображения'),'Raw Russian group name leaked in English')
const advancedState={...sumState,api_version:'0.5.0',parity:{'OFF/OFF':{pairs:4,same_visible:3,same_reasoning:2},'ON/ON':{pairs:4,same_visible:4,same_reasoning:1},'OFF/ON':{pairs:8,same_visible:2,same_reasoning:1}},quality_counts:{pass:5,fail:2,unverified:3,manual_review:6,incomplete:0},hardware_info:{engine_version:'llama.cpp b12292',gpu_layers_arg:'auto',gpu:{gpus:[{name:'NVIDIA RTX mock',vram_used_global_mib:12000,vram_total_mib:16000,utilization_gpu_pct:34}]}}}
const advancedText=treeText(renderFor(advancedState,'en'))
assert(advancedText.includes('Output reproducibility'),'Parity overview is missing')
assert(advancedText.includes('Quality assessment'),'Quality overview is missing')
assert(advancedText.includes('Hardware diagnostics'),'Hardware metrics overview missing')
assert(advancedText.includes('Unverified'),'Unverified code verdict must be visible')
const genericState={api_version:'0.5.0',state:'idle',model:'My-MoE-Q5_K_M',models:[{id:'My-MoE-Q5_K_M',mtp_supported:true}],
 selected:{id:'My-MoE-Q5_K_M',model_path:'E:/Models/My-MoE-Q5_K_M.gguf',mtp_kind:'external',mtp_supported:true,has_mmproj:false,mtp_head:'',mmproj:''},owns_router:true,tasks_per_phase:4}
const genericTree=renderFor(genericState,'en')
assert(treeText(genericTree).includes('My-MoE-Q5_K_M'),'Model picker must list arbitrary installed GGUF models')
assert(treeText(genericTree).includes('Reasoning mode'),'Reasoning selector label must be translated')
assert(treeText(genericTree).includes('Request no reasoning'),'No-thinking benchmark option missing')
assert(treeText(genericTree).includes('Native model reasoning'),'Native reasoning benchmark option missing')
assert(treeText(genericTree).includes('Text-only tasks'),'Absent mmproj should be shown as text-only')
const modelSelector=findNode(genericTree,node=>node.type==='select'&&node.props.value==='My-MoE-Q5_K_M')
assert(modelSelector,'Arbitrary model must be selectable in desktop UI')
assert(treeText(genericTree).includes('MTP head GGUF'),'External MTP-head picker input must be shown')
assert(treeText(genericTree).includes('Browse folder'),'Native folder browse control missing')
assert(treeText(genericTree).includes('Discovered MTP-head files'),'MTP-head native folder browser missing')
assert(treeText(genericTree).includes('E:/Models'),'The exact preset-based scanned folder should be visible')
function countNodes(node,fn){if(!node||typeof node!=='object')return 0;return (fn(node)?1:0)+(node.children||[]).reduce((n,x)=>n+countNodes(x,fn),0)}
assert(countNodes(genericTree,n=>n.type==='button'&&treeText(n).includes('Browse folder'))===2,'Both MTP-head and mmproj need independent folder pickers')
assert(!treeText(genericTree).includes('Desktop has updated but Hermes Python API'),'Synchronized backend must not show mismatch banner')
const oldTree=renderFor({...genericState,api_version:'0.3.2'},'en')
assert(treeText(oldTree).includes('Desktop has updated but Hermes Python API'),'Old backend must trigger version mismatch instead of a raw 404')
assert(!src.includes("ctx.rest('/projectors'"),'Obsolete /projectors request would cause 404 after hot reload')
assert(src.includes('API_VERSION'),'Backend version synchronization guard missing')
const embeddedTree=renderFor({...genericState,selected:{...genericState.selected,mtp_kind:'embedded',embedded_verified:true,mtp_head:''}},'en')
assert(treeText(embeddedTree).includes('MTP embedded in GGUF'),'Verified embedded MTP needs explicit green status')
const green=findNode(embeddedTree,node=>node.type==='span'&&node.props.style?.color==='#16834d')
assert(green,'Embedded GGUF verification must produce a green status')
const presetOnlyTree=renderFor({...genericState,selected:{...genericState.selected,mtp_kind:'embedded',embedded_verified:false,mtp_head:''}},'en')
assert(treeText(presetOnlyTree).includes('not confirmed by GGUF metadata'),'Preset-only MTP must not be labelled verified')
console.log('PASS: plugin route, i18n registration, RU/EN and Auto UI, persistent selection, stage, errors, results')
