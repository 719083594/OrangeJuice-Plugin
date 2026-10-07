import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {fileURLToPath,pathToFileURL} from 'node:url'
import {helpTopics,HELP_TEXT} from '../integrations/yunzai/help-content.mjs'

const source=fileURLToPath(new URL('../integrations/yunzai/',import.meta.url))
const key=Symbol.for('orangejuice.fixed-help-test')
async function fixture(t,{service=true}={}){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'orangejuice-fixed-help-'))
  const bridge=path.join(root,'plugins/OrangeJuice-Plugin')
  fs.mkdirSync(bridge,{recursive:true})
  fs.writeFileSync(path.join(root,'package.json'),'{"type":"module"}')
  for(const name of ['index.js','package.json','command-aliases.mjs','feature-runtime.mjs','command-table.mjs','command-knowledge.mjs','help-content.mjs'])fs.copyFileSync(path.join(source,name),path.join(bridge,name))
  for(const [name,content] of [['lib/plugins/loader.js','export default {priority:[]}'],['lib/config/config.js','export default {getGroup(){return {}}}']]){
    const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,content)
  }
  const trace={loads:0,factories:[],requests:[],mode:'success'}
  globalThis[key]=trace
  const previousPlugin=globalThis.plugin
  globalThis.plugin=class{constructor(options){Object.assign(this,options)}}
  if(service){
    const file=path.join(root,'plugins/AI-Plugin/src/rendering/index.mjs')
    fs.mkdirSync(path.dirname(file),{recursive:true})
    fs.writeFileSync(file,`const trace=globalThis[Symbol.for('orangejuice.fixed-help-test')];trace.loads++;
export function createFixedHelpDelivery(options){trace.factories.push(options);return async(e,topic)=>{
trace.requests.push(topic);if(trace.mode==='missing')return false;
if(trace.mode==='partial')throw new Error('STATIC_HELP_SEND_INCOMPLETE');
await e.reply({type:'image',topic},Boolean(e.isGroup||e.group_id));return true;
}}`)
  }
  const {OrangeJuice}=await import(pathToFileURL(path.join(bridge,'index.js')))
  const plugin=new OrangeJuice()
  t.after(()=>{if(previousPlugin===undefined)delete globalThis.plugin;else globalThis.plugin=previousPlugin;delete globalThis[key];fs.rmSync(root,{recursive:true,force:true})})
  const replies=[]
  const run=async(extra={})=>{replies.length=0;return plugin.login({msg:'#橙汁帮助',isMaster:true,isGroup:false,reply:async(value,quote)=>{replies.push({value,quote});return {message_id:1}},...extra})}
  return {bridge,plugin,trace,replies,run}
}

test('固定帮助定义只有命令说明，不包含真实入口、票据或运行配置',()=>{
  assert.deepEqual(Object.keys(helpTopics),['orangejuice-help'])
  const help=helpTopics['orangejuice-help'],text=JSON.stringify(help)
  assert.equal(help.theme,'dark')
  assert(text.includes('仅机器人主人私聊'))
  assert(text.includes('#橙汁帮助 文字'))
  for(const value of ['http://','https://','?ticket=','bridge.key','127.0.0.1'])assert(!text.includes(value))
  assert(HELP_TEXT.includes('OrangeJuice 管理面板'))
})

test('真实平铺adapter布局懒读固定帮助；先校验主人与私聊，文字入口不读图',async t=>{
  const f=await fixture(t)
  assert.equal(f.trace.loads,0)
  await f.run({isMaster:false})
  assert.equal(f.replies.length,0);assert.equal(f.trace.loads,0)
  await f.run({isGroup:true})
  assert.match(f.replies[0].value,/请主人私聊/);assert.equal(f.trace.loads,0)
  await f.run({isGroup:false,group_id:'200000001'})
  assert.match(f.replies[0].value,/请主人私聊/);assert.equal(f.trace.loads,0)
  await f.run({msg:'#橙汁帮助 文字'})
  assert.equal(f.replies[0].value,HELP_TEXT);assert.equal(f.trace.loads,0)
  await f.run()
  assert.equal(f.trace.loads,1)
  assert.deepEqual(f.trace.factories,[{root:f.bridge+path.sep}])
  assert.deepEqual(f.trace.requests,['orangejuice-help'])
  assert.deepEqual(f.replies,[{value:{type:'image',topic:'orangejuice-help'},quote:false}])
  await f.run({msg:'/OrangeJuice帮助'})
  assert.equal(f.trace.loads,1);assert.equal(f.trace.factories.length,1)
  assert.deepEqual(f.trace.requests,['orangejuice-help','orangejuice-help'])
})

test('缺图回退文字，部分页发送失败不重放完整文字',async t=>{
  const f=await fixture(t)
  f.trace.mode='missing'
  await f.run()
  assert.deepEqual(f.replies,[{value:HELP_TEXT,quote:undefined}])
  f.trace.mode='partial'
  await assert.rejects(f.run(),/STATIC_HELP_SEND_INCOMPLETE/)
  assert.equal(f.replies.length,0)
})

test('未安装可选共享服务仍可私聊查看帮助，未访问IPC票据请求',async t=>{
  const f=await fixture(t,{service:false})
  await f.run()
  assert.deepEqual(f.replies,[{value:HELP_TEXT,quote:undefined}])
  assert.equal(f.trace.loads,0)
})
