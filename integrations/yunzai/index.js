import fs from 'node:fs'
import path from 'node:path'
import {randomUUID,createHmac,createHash} from 'node:crypto'
import PluginsLoader from '../../lib/plugins/loader.js'
import {rewriteCommand,configurationPayload} from './command-aliases.mjs'
import {featureSnapshot} from './feature-runtime.mjs'
const PluginBase=globalThis.plugin||(await import('../../lib/plugins/plugin.js')).default

const root=path.resolve('data/orangejuice')
let config={publicUrl:'http://127.0.0.1:16080',ipcDirectory:root}
try{Object.assign(config,JSON.parse(fs.readFileSync(new URL('./config/local.json',import.meta.url),'utf8')))}catch(error){if(error.code!=='ENOENT')throw error}
const ipc=path.resolve(config.ipcDirectory)
function atomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=file+'.'+randomUUID()+'.tmp';fs.writeFileSync(temporary,JSON.stringify(value),{mode:0o600});fs.renameSync(temporary,file)}
function mapList(value,convert){if(value instanceof Map)return [...value.values()].slice(0,1000).map(convert);if(Array.isArray(value))return value.slice(0,1000).map(convert);return []}
function publishRuntime(){
  try{
    const source=Bot.bots&&typeof Bot.bots==='object'?Object.entries(Bot.bots):Bot.uin?[[String(Bot.uin),Bot]]:[]
    const bots=source.filter(([id,b])=>b&&typeof b==='object'&&(b.uin!==undefined||b.self_id!==undefined||b.fl instanceof Map||b.gl instanceof Map)).map(([id,b])=>{
      let online=null;try{online=typeof b.isOnline==='function'?b.isOnline():typeof b.isOnline==='boolean'?b.isOnline:typeof b.stat?.online==='boolean'?b.stat.online:null}catch{}
      if(online===null&&typeof b.ws?.readyState==='number')online=b.ws.readyState===1
      const adapter=b.adapter||b.platform;const platform=typeof adapter==='string'?adapter:adapter?.name||adapter?.id||'框架未提供'
      return {id,nickname:b.nickname||b.info?.nickname||'',platform,online,friendCount:b.fl?.size??b.friend_list?.length??null,groupCount:b.gl?.size??b.group_list?.length??null,friends:mapList(b.fl||b.friend_list,x=>({id:String(x.user_id||x.id||''),name:x.nickname||x.remark||''})),groups:mapList(b.gl||b.group_list,x=>({id:String(x.group_id||x.id||''),name:x.group_name||x.name||'',members:x.member_count??null}))}
    })
    const counts=PluginsLoader.pluginCountMap instanceof Map?PluginsLoader.pluginCountMap:null
    const dirs=fs.readdirSync('plugins',{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name)
    const plugins=dirs.map(directory=>({directory,loaded:counts?[...counts.keys()].some(k=>String(k).split('/')[0]===directory):null}))
    atomic(path.join(ipc,'runtime.json'),{timestamp:Date.now()/1000,bots,plugins,nodeVersion:process.version,botRss:process.memoryUsage().rss,botUptime:process.uptime(),loadedFunctions:PluginsLoader.priority?.length??null,featureInventory:featureSnapshot(PluginsLoader)})
  }catch(error){logger.warn('[OrangeJuice] 运行信息同步失败：'+error.message)}
}
async function request(payload){
  const key=fs.readFileSync(path.join(ipc,'bridge.key'),'utf8').trim();const stamp=String(Date.now()/1000)
  const signature=createHmac('sha256',key).update(stamp+'\n'+createHash('sha256').update(JSON.stringify(payload)).digest('hex')).digest('hex')
  const id=randomUUID()+'.json',file=path.join(ipc,'requests',id),response=path.join(ipc,'responses',id)
  atomic(file,{payload,time:stamp,signature})
  try{for(let i=0;i<30;i++){await new Promise(r=>setTimeout(r,200));if(fs.existsSync(response)){const value=JSON.parse(fs.readFileSync(response,'utf8'));fs.unlinkSync(response);if(value.error)throw new Error(value.error);return value}}throw new Error('管理服务没有响应')}
  finally{if(fs.existsSync(file))fs.unlinkSync(file)}
}
export class OrangeJuice extends PluginBase {
  constructor(){super({name:'OrangeJuice-Plugin',dsc:'独立配置平台桥接与主人登录',event:'message',priority:-10000,rule:[{reg:/^[#/]?(?:橙汁|OrangeJuice)(?:登录|登陆|帮助|配置|设置|功能)(?:\s+[\s\S]*)?$/i,fnc:'login',permission:'master'}]})}
  init(){if(globalThis.orangeJuiceRuntimeTimer)clearInterval(globalThis.orangeJuiceRuntimeTimer);publishRuntime();globalThis.orangeJuiceRuntimeTimer=setInterval(publishRuntime,5000);globalThis.orangeJuiceRuntimeTimer.unref()}
  async accept(e){
    let live=config
    try{live={...config,...JSON.parse(fs.readFileSync(new URL('./config/local.json',import.meta.url),'utf8'))}}catch{}
    const rewritten=rewriteCommand(e.msg,live.commandAliases)
    if(rewritten!==String(e.msg||'').trim()){
      e.msg=rewritten
      if(typeof e.raw_message==='string')e.raw_message=rewritten
      if(Array.isArray(e.message)){let changed=false;e.message=e.message.map(s=>s.type==='text'&&!changed?(changed=true,{...s,text:rewritten}):s.type==='text'?{...s,text:''}:s)}
    }
    return false
  }
  async login(e){
    if(!e.isMaster)return true
    if(e.isGroup){await e.reply('请主人私聊使用橙汁登录或配置命令。');return true}
    if(/(?:配置|设置|功能)(?:\s|$)/.test(e.msg)){
      try{const result=await request(configurationPayload(e.msg));await e.reply(result.text)}
      catch(error){await e.reply(error.message)}
      return true
    }
    if(/帮助$/.test(e.msg)){await e.reply('OrangeJuice 管理面板\n#橙汁登录 /橙汁登录：主人临时登录链接，3分钟内一次有效。\n#橙汁功能 [功能名 开/关]：内置功能开关。\n#橙汁配置：插件列表。\n#橙汁配置 插件名 [搜索词或页码]：查询设置。\n#橙汁设置 插件名 选项编号 @版本 值：修改设置，支持 JSON 和开/关。\n仅主人私聊可用，保存会校验并备份。\n面板机器人桥接设置可配置自定义指令。\n网页登录支持账号密码和控制台验证码。');return true}
    try{const {ticket:code}=await request({action:'ticket'});await e.reply(config.publicUrl.replace(/\/$/,'')+'/#/login?ticket='+encodeURIComponent(code))}
    catch(error){logger.warn('[OrangeJuice] '+error.message);await e.reply('管理服务暂时未就绪，请查看 OrangeJuice 服务状态。')}
    return true
  }
}
