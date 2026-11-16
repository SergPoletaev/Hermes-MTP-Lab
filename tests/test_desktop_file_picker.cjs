/** Regression tests for native GGUF file-picker UX (no Hermes runtime required). */
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path')
const src=fs.readFileSync(path.join(__dirname,'../desktop/plugin.js'),'utf8')
assert(!src.includes('ctx.files.requestFolder('),'GGUF chooser may not request folder grants')
const stripped=src.replace(/^import .*?\n/gm,'').replace('export default {','globalThis.TEST_PLUGIN = {')+'\nglobalThis.TEST_LABVIEW = LabView;'
const persisted=new Map(),calls=[]
const stored={get:(key,fallback)=>persisted.get(key)??fallback,set:(key,val)=>persisted.set(key,val)}
const state={api_version:'0.5.1',state:'idle',model:'Test-Q4',owns_router:true,
  models:[{id:'Test-Q4'}],selected:{id:'Test-Q4',model_path:'E:\\AI\\Models\\Test-Q4.gguf',mtp_kind:'external',mtp_supported:true,has_mmproj:false,mtp_head:'',mmproj:''}}
let response=null, updates={}, picks=[],language='ru'
const ctx={i18n:{register(){}},storage:stored,os:{async pickOpenPath(options){picks.push(options);return response}},rest:async()=>state,
 registerMany(){},registerSettingsPage(){}}
const React={createElement:(...xs)=>({type:xs[0],props:xs[1]||{},children:xs.slice(2)})}
const sandbox={React,useEffect(){},useState(initial){const index=sandbox.counter++;
 const value=index===0?state:index===8?true:index===10?language:initial
 return[value,value=>{updates[index]=value}]},usePluginI18n:()=>key=>key,
 localStorage:{getItem:()=>null,setItem(){}},ROUTES_AREA:'routes',SIDEBAR_NAV_AREA:'nav',PALETTE_AREA:'palette',host:{navigate(){}},Date,setInterval(){},clearInterval(){}}
vm.runInNewContext(stripped,sandbox,{filename:'plugin.js'})
function visit(node,fn,result=[]){if(!node||typeof node!=='object')return result;
 if(fn(node))result.push(node);
 for(const child of node.children||[])visit(child,fn,result);
 return result}
function text(node){if(node==null)return '';if(typeof node==='string')return node;if(Array.isArray(node))return node.map(text).join(' ');return text(node.children)}
function buttons(){updates={};sandbox.counter=0;const tree=sandbox.TEST_LABVIEW({ctx});return visit(tree,n=>n.type==='button'&&text(n).includes(language==='ru'?'Обзор…':'Browse…'))}
async function run(){
  let b=buttons();assert.strictEqual(b.length,2,'exactly 2 direct file buttons')
  response='D:\\LLM\\MTP\\head.Q8_0.gguf';await b[0].props.onClick()
  assert.strictEqual(picks[0].defaultPath,'E:\\AI\\Models','first picker must open selected model folder')
  assert.deepStrictEqual(Array.from(picks[0].filters[0].extensions),['gguf'])
  assert.strictEqual(updates[2],response,'MTP-head field must receive file path')
  assert.strictEqual(persisted.get('companionPickerLastDirectory'),'D:\\LLM\\MTP','successful directory must persist')
  b=buttons();response='D:\\LLM\\Projectors\\mmproj.gguf';await b[1].props.onClick()
  assert.strictEqual(picks[1].defaultPath,'D:\\LLM\\MTP','mmproj chooser must reopen last used directory')
  assert.strictEqual(updates[3],response,'mmproj field must receive file path')
  assert.strictEqual(persisted.get('companionPickerLastDirectory'),'D:\\LLM\\Projectors')
  b=buttons();response=null;await b[0].props.onClick()
  assert.strictEqual(updates[2],undefined,'cancel must not clear existing MTP path')
  assert.strictEqual(updates[3],undefined,'cancel must not clear existing mmproj path')
  assert.strictEqual(persisted.get('companionPickerLastDirectory'),'D:\\LLM\\Projectors')
  b=buttons();response='D:\\LLM\\readme.txt';await b[0].props.onClick()
  assert.strictEqual(updates[2],undefined,'non-GGUF path cannot be accepted')
  assert(/GGUF/.test(updates[1]),'invalid file must report a visible error')
  delete ctx.os.pickOpenPath;b=buttons();await b[0].props.onClick()
  assert(/Hermes Desktop/.test(updates[1]),'unsupported Desktop must explain native dialog API requirement')
  assert(!ctx.files,'a folder access fallback must not be required')
  console.log('PASS: native MTP/mmproj GGUF pickers, model-folder default, persisted last directory, cancel, validation, unsupported host')
}
run().catch(e=>{console.error(e);process.exitCode=1})
