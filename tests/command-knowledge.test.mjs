import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {commandCatalog,publishCommandCatalog} from '../integrations/yunzai/command-knowledge.mjs'
test('command documents follow live registrations, edits, aliases and removal without rewriting unchanged snapshots',t=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'orange-knowledge-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}))
 const bridge=path.join(root,'bridge'),plugins=path.join(root,'plugins'),ipc=path.join(root,'ipc');fs.mkdirSync(path.join(plugins,'Weather'),{recursive:true});fs.mkdirSync(path.join(bridge,'config'),{recursive:true})
 const manifest=path.join(plugins,'Weather/orangejuice.plugin.json');const put=title=>fs.writeFileSync(manifest,JSON.stringify({commandTable:[{title,command:'#天气 城市',description:'查询天气',permission:'all'},{title:'维护',command:'#重启',permission:'master'}]}))
 put('天气');const loader={priority:[{key:'Weather/index.js',plugin:{name:'天气',event:'message',rule:[{reg:/^#天气/},{reg:/^#重启/}]}}]};const options={bridgeRoot:bridge,pluginsRoot:plugins}
 assert.equal(publishCommandCatalog(loader,ipc,options),true);const file=path.join(ipc,'command-catalog.json'),first=fs.readFileSync(file,'utf8')
 assert.equal(JSON.parse(first).rows.length,2);assert.equal(commandCatalog(loader,{isGroup:true},options).rows.length,1)
 assert.equal(publishCommandCatalog(loader,ipc,options),false);assert.equal(fs.readFileSync(file,'utf8'),first)
 put('最新天气');assert.equal(publishCommandCatalog(loader,ipc,options),true);assert(JSON.parse(fs.readFileSync(file)).rows.some(row=>row.title==='最新天气'))
 fs.writeFileSync(path.join(bridge,'config/local.json'),JSON.stringify({commandAliases:[{alias:'/查天气',target:'#天气'}]}));assert.equal(publishCommandCatalog(loader,ipc,options),true);assert(commandCatalog(loader,{},options).rows.some(row=>row.command.startsWith('/查天气')))
 assert.equal(commandCatalog(loader,{isGroup:true},{...options,groupConfig:{disable:['天气']}}).rows.length,0)
 loader.priority=[];assert.equal(publishCommandCatalog(loader,ipc,options),true);assert.equal(JSON.parse(fs.readFileSync(file)).rows.length,0)
})
