import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {buildCommandTable,commandMessages,replyCommandTable,readPluginJSON} from '../integrations/yunzai/command-table.mjs'
const docs=JSON.parse(fs.readFileSync(new URL('../integrations/yunzai/command-docs.json',import.meta.url),'utf8'))
const entry=(key,name,rules,methods={})=>({key,plugin:{name,event:'message',rule:rules,...methods}})
const rule=(reg,fnc,permission='all')=>({reg,fnc,permission})
const entries=[
 entry('AI-Plugin/index.js','AI-Plugin',[rule('.*','handle')]),
 entry('WebSearch-Plugin/index.js','实时联网搜索',[rule(/^[#/](?:搜索|搜图|搜文|搜索帮助|搜索诊断)(?:\s|$)/,'search')]),
 entry('ServerStatus-Plugin/index.js','服务器状态',[rule(/^[#\/](?:系统|服务器|资源|存储|插件|服务|系统帮助)\s*$/,'status','master')]),
 entry('OrangeJuice-Plugin/index.js','OrangeJuice-Plugin',[rule(/^[#/](?:指令|指令表)\s*$/,'commands'),rule(/^[#/]?(?:橙汁|OrangeJuice)(?:登录|登陆|帮助|配置|设置|功能)(?:\s+[\s\S]*)?$/i,'login','master')]),
 entry('system/recallReply.js','回复撤回',[rule(/^#?撤回$/,'recall')]),
 entry('other/update.js','更新',[rule(/^#更新日志/,'updateLog'),rule(/^#(安?静)?(强制)?更新/,'update'),rule(/^#全部(安?静)?(强制)?更新$/,'updateAll','master')]),
 entry('system/status.js','状态统计',[rule(/^#(状态|统计)/,'status')]),
 entry('system/status.js','状态统计',[rule(/^#(状态|统计)/,'status')]),
 entry('system/add.js','添加消息',[rule(/^#(全局)?添加/,'add'),rule(/^#(全局)?删除/,'del'),rule(/^#(全局)?(消息|词条)/,'list')]),
]
test('group scope including master hides rule and handler protected commands; private owner sees all',()=>{
 const group=buildCommandTable({priority:entries},{isGroup:true,isMaster:true},{docs})
 const ordinary=buildCommandTable({priority:entries},{isMaster:false},{docs})
 const owner=buildCommandTable({priority:entries},{isMaster:true},{docs})
 for(const table of [group,ordinary]){
  assert(!table.rows.some(x=>x.permission==='master'))
  for(const text of ['#系统','#搜索诊断','#橙汁登录','#AI备份','#更新 /','#撤回','#全局添加'])assert(!commandMessages(table).join('\n').includes(text),text)
  assert(table.rows.some(x=>x.title==='统一指令表'))
  assert(table.rows.some(x=>x.title==='联网搜索'))
 }
 for(const title of ['系统总览','搜索诊断','打开橙汁面板','备份与清理','更新源码','撤回引用消息'])assert(owner.rows.some(x=>x.title===title),title)
 assert.equal(owner.rows.filter(x=>x.title==='查看框架统计').length,1)
 assert(owner.rows.some(x=>x.command.includes('#全局添加')))
 assert.equal(owner.unparsed,0)
  assert(group.rows.some(x=>x.title==='删除关键词回复'&&x.command==='#删除 关键词'))
  assert(!group.rows.find(x=>x.title==='删除关键词回复').command.includes('全局'))
 assert(owner.rows.every(x=>x.category&&!x.category.includes('Plugin')))
})
test('live registry removes absent/unloaded commands; group controls, event rules, registration changes and unknown handlers',()=>{
 const extra=entry('Sample-Plugin/index.js','测试天气',[rule(/^#天气\s+(.+)$/,'weather'),rule(/^#私密$/,'secret'),{...rule(/^#通知$/,'notice'),event:'notice.group'}],{secret:function(e){if(!e.isMaster)return false}})
 const table=buildCommandTable({priority:[extra]},{isGroup:true},{docs})
 assert.equal(table.rows.length,1);assert(table.rows[0].command.includes('天气'));assert.equal(table.unparsed,1)
 assert.equal(buildCommandTable({priority:[extra]},{isGroup:true},{docs,groupConfig:{disable:['测试天气']}}).rows.length,0)
 assert.equal(buildCommandTable({priority:[extra]},{isGroup:true},{docs,groupConfig:{enable:['其他功能']}}).rows.length,0)
 assert.equal(buildCommandTable({priority:[extra]},{isMaster:true},{docs}).rows.length,2)
 assert.equal(buildCommandTable({priority:[]},{isMaster:true},{docs}).rows.length,0)
  const keywords=entries.filter(x=>x.key==='system/add.js')
  const table2=buildCommandTable({priority:keywords},{isGroup:true},{docs,groupConfig:{addLimit:2}})
  assert(!table2.rows.some(x=>['add','del'].includes(x.handler)))
  assert(table2.rows.some(x=>x.command.includes('#全局词条')))
})
test('plugin hints and real config prefixes/flags are read without importing code; aliases inherit permission',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'orange-command-table-'))
 try{
  const put=(directory,file,data)=>{const target=path.join(root,directory,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,JSON.stringify(data))}
  put('AI-Plugin','config/local.json',{basic:{commandPrefix:'/小星',triggerMode:'both',triggerPrefix:'#聊'},presets:[{prefix:'星：',enabled:true},{prefix:'隐藏：',enabled:false}]})
  put('Sample-Plugin','orangejuice.plugin.json',{commandTable:[{title:'天气查询',command:'#天气 城市',description:'查询实时天气',permission:'all'}]})
  const loader={priority:[...entries,entry('Sample-Plugin/index.js','天气',[rule(/^#天气\s+.+$/,'weather')])]}
  const aliases=[{alias:'/查',target:'#搜索'},{alias:'/看服务器',target:'#系统'},{alias:'/错',target:'#没注册'}]
  let table=buildCommandTable(loader,{isGroup:true},{docs,pluginsRoot:root,aliases})
  assert(table.rows.some(x=>x.command.includes('/小星帮助')))
  assert(table.rows.some(x=>x.command.includes('星： 提问')&&!x.command.includes('隐藏：')))
  assert(table.rows.some(x=>x.command==='#天气 城市'))
  assert(table.rows.some(x=>x.command.startsWith('/查 ')))
  assert(!table.rows.some(x=>x.command.startsWith('/看服务器')||x.command.startsWith('/错')))
  table=buildCommandTable(loader,{isMaster:true},{docs,pluginsRoot:root,aliases});assert(table.rows.some(x=>x.command.startsWith('/看服务器')))
  put('WebSearch-Plugin','config/plugin.json',{masterOnly:true})
  put('AI-Plugin','config/local.json',{basic:{enabled:false}})
  table=buildCommandTable(loader,{isGroup:true},{docs,pluginsRoot:root})
  assert(!table.rows.some(x=>x.directory==='AI-Plugin'||x.directory==='WebSearch-Plugin'))
  assert.deepEqual(readPluginJSON(root,'../outside.json'),{})
 }finally{fs.rmSync(root,{recursive:true,force:true})}
})
test('categorized forwarding and text fallback keep every command; no dependency on management server',async()=>{
 const table=buildCommandTable({priority:entries},{isMaster:true},{docs}),messages=commandMessages(table,600),texts=[]
 assert(messages.length>4);assert(messages.every(x=>x.length<3500))
 await replyCommandTable({isGroup:false,user_id:'fixture',friend:{makeForwardMsg:async()=>{throw Error('unsupported')}},reply:async x=>texts.push(x)},table)
 assert.equal(texts.join('\n'),commandMessages(table).join('\n'))
 let nodes
 const replies=[]
 await replyCommandTable({isGroup:true,self_id:'bot',group:{makeForwardMsg:async value=>(nodes=value,{type:'forward'})},reply:async x=>replies.push(x)},table)
 assert.equal(replies.length,1);assert.equal(nodes.length,commandMessages(table).length)
 assert.equal(nodes.map(x=>x.message).join('\n'),commandMessages(table).join('\n'))
})
test('group command forwarding does not leave a standalone quoted message in OneBot',async()=>{
 const table=buildCommandTable({priority:entries},{isGroup:true},{docs}),sent=[]
 const e={
  isGroup:true,self_id:'bot',message_id:'command-message',
  group:{makeForwardMsg:async nodes=>({type:'node',data:nodes})},
  // Yunzai prepends a reply segment; OneBot sends nodes separately from regular segments.
  reply:async(value,quote=false)=>{
   const segments=Array.isArray(value)?[...value]:[value]
   if(quote)segments.unshift({type:'reply',data:{id:'command-message'}})
   const nodes=segments.filter(x=>x.type==='node').flatMap(x=>x.data)
   const message=segments.filter(x=>x.type!=='node')
   if(nodes.length)sent.push({type:'forward',nodes})
   if(message.length)sent.push({type:'message',message})
   return {message_id:'sent'}
  }
 }
 assert.equal(await replyCommandTable(e,table),true)
 assert.equal(sent.length,1,'the command must send only its forward card, without a quote-only bubble')
 assert.equal(sent[0].type,'forward')
 assert.deepEqual(sent[0].nodes.map(x=>x.message),commandMessages(table))
})
