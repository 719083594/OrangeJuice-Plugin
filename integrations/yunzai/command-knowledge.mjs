import fs from 'node:fs'
import path from 'node:path'
import {createHash,randomUUID} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import {buildCommandTable,readPluginJSON} from './command-table.mjs'

// The same registry and documents as #指令表; never load a plugin to discover it.
export function commandCatalog(loader,event={isMaster:true},options={}) {
  const bridge=options.bridgeRoot||fileURLToPath(new URL('.',import.meta.url))
  const live=readPluginJSON(bridge,'config/local.json')
  const docs=readPluginJSON(bridge,'command-docs.json')
  const table=buildCommandTable(loader,event,{...options,docs,aliases:live.commandAliases||options.aliases})
  return {schema:1,source:'OrangeJuice #指令表',...table}
}
export function publishCommandCatalog(loader,directory,options={}) {
  const catalog=commandCatalog(loader,{isMaster:true},options)
  const hash=createHash('sha256').update(JSON.stringify(catalog)).digest('hex')
  const file=path.join(directory,'command-catalog.json')
  try { if(JSON.parse(fs.readFileSync(file,'utf8')).hash===hash)return false }catch{}
  fs.mkdirSync(directory,{recursive:true})
  const temporary=file+'.'+randomUUID()+'.tmp'
  try { fs.writeFileSync(temporary,JSON.stringify({...catalog,hash,updatedAt:new Date().toISOString()},null,2)+'\n',{mode:0o600});fs.renameSync(temporary,file) }
  finally { if(fs.existsSync(temporary))fs.unlinkSync(temporary) }
  return true
}
