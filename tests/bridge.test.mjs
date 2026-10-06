import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {pathToFileURL,fileURLToPath} from 'node:url'
import {EventEmitter} from 'node:events'
import test from 'node:test'

test('TRSS registry metadata is excluded; classic bot and unknown status remain honest',async()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'orangejuice-bridge-')),previous=process.cwd()
  try{
    fs.mkdirSync(path.join(root,'plugins/OrangeJuice-Plugin'),{recursive:true});fs.mkdirSync(path.join(root,'lib/plugins'),{recursive:true});fs.mkdirSync(path.join(root,'lib/config'),{recursive:true})
    fs.writeFileSync(path.join(root,'lib/config/config.js'),"export default {getGroup:()=>({})}")
    fs.writeFileSync(path.join(root,'package.json'),'{"type":"module"}')
    fs.writeFileSync(path.join(root,'lib/plugins/loader.js'),"export default {pluginCountMap:new Map([['OrangeJuice-Plugin',1]]),priority:[{}]}")
    fs.writeFileSync(path.join(root,'lib/plugins/plugin.js'),"export default class {constructor(options){Object.assign(this,options)}}")
    const source=fileURLToPath(new URL('../integrations/yunzai/index.js',import.meta.url)),target=path.join(root,'plugins/OrangeJuice-Plugin/index.js');fs.copyFileSync(source,target);fs.copyFileSync(fileURLToPath(new URL('../integrations/yunzai/feature-runtime.mjs',import.meta.url)),path.join(root,'plugins/OrangeJuice-Plugin/feature-runtime.mjs'))
    fs.copyFileSync(fileURLToPath(new URL('../integrations/yunzai/command-aliases.mjs',import.meta.url)),path.join(root,'plugins/OrangeJuice-Plugin/command-aliases.mjs'));process.chdir(root);globalThis.plugin=class{constructor(options){Object.assign(this,options)}};globalThis.logger={warn:()=>{}}
    for(const file of ['command-table.mjs','command-docs.json','command-knowledge.mjs'])fs.copyFileSync(fileURLToPath(new URL('../integrations/yunzai/'+file,import.meta.url)),path.join(root,'plugins/OrangeJuice-Plugin',file))
    const registry=new EventEmitter();registry.url='metadata';registry.demo={uin:'demo',nickname:'fixture',adapter:{name:'OneBotv11'},ws:{readyState:1},fl:new Map([['friend',{user_id:'fixture',nickname:'sample'}]]),gl:new Map()};globalThis.Bot={bots:registry}
    const {OrangeJuice}=await import(pathToFileURL(target));const bridge=new OrangeJuice();bridge.init()
    let runtime=JSON.parse(fs.readFileSync('data/orangejuice/runtime.json','utf8'));assert.equal(runtime.bots.length,1);assert.equal(runtime.bots[0].platform,'OneBotv11');assert.equal(runtime.bots[0].online,true);assert.equal(runtime.plugins[0].loaded,true)
    let replies=[];await bridge.login({isMaster:false,isGroup:false,msg:'#橙汁登录',reply:async x=>replies.push(x)});assert.equal(replies.length,0)
    assert.equal(bridge.rule.filter(r=>r.reg.test('#指令表')).length,1)
    assert.equal(bridge.rule[0].permission,'all')
    await bridge.commands({self_id:'demo',user_id:'reader',isMaster:false,isGroup:true,msg:'#指令表',reply:async x=>replies.push(x)});assert.equal(replies.length,1);assert(replies[0].includes('公开指令表'));replies=[]
    await bridge.login({isMaster:false,isGroup:false,msg:'#橙汁设置 AI abcdef012345 @abcdef0123456789 20',reply:async x=>replies.push(x)});assert.equal(replies.length,0)
    await bridge.login({isMaster:true,isGroup:true,msg:'#橙汁配置 AI',reply:async x=>replies.push(x)});assert.equal(replies.length,1);assert(replies[0].includes('私聊'));replies=[]
    fs.mkdirSync(path.join(root,'plugins/OrangeJuice-Plugin/config'),{recursive:true});fs.writeFileSync(path.join(root,'plugins/OrangeJuice-Plugin/config/local.json'),JSON.stringify({commandAliases:[{alias:'/查询',target:'#搜索'}]}))
    const event={msg:'/查询 北京天气',raw_message:'/查询 北京天气',message:[{type:'text',text:'/查询 北京天气'}]};await bridge.accept(event);assert.equal(event.msg,'#搜索 北京天气');assert.equal(event.message[0].text,'#搜索 北京天气')
    await bridge.login({isMaster:true,isGroup:true,msg:'#橙汁登录',reply:async x=>replies.push(x)});assert.equal(replies.length,1);assert(!replies[0].includes('ticket='))
    globalThis.Bot={uin:'classic',nickname:'demo',isOnline:true,fl:new Map(),gl:new Map()};bridge.init();runtime=JSON.parse(fs.readFileSync('data/orangejuice/runtime.json','utf8'));assert.equal(runtime.bots[0].online,true)
    globalThis.Bot={bots:{unknown:{uin:'unknown',fl:new Map()}}};bridge.init();runtime=JSON.parse(fs.readFileSync('data/orangejuice/runtime.json','utf8'));assert.equal(runtime.bots[0].online,null)
    delete globalThis.plugin;const classicModule=path.join(root,'plugins/OrangeJuice-Plugin/classic.js');fs.copyFileSync(source,classicModule);const {OrangeJuice:ClassicBridge}=await import(pathToFileURL(classicModule));assert.equal(new ClassicBridge().name,'OrangeJuice-Plugin')
  }finally{clearInterval(globalThis.orangeJuiceRuntimeTimer);process.chdir(previous);fs.rmSync(root,{recursive:true,force:true})}
})
