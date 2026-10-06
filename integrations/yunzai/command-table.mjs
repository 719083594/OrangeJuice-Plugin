// Use registered instances only. This module never imports or instantiates another plugin.
import fs from 'node:fs'
import path from 'node:path'
import {rewriteCommand} from './command-aliases.mjs'

const categories = [
  ['聊天与角色', /聊天|角色|预设|对话|接话|提问/],
  ['搜索与资料', /搜索|查询|查找|资料|知识|翻译/],
  ['图片与媒体', /图片|头像|视频|音频|语音|音乐|画图/],
  ['记忆与词条', /记忆|词条|关键词|添加消息|删除消息/],
  ['群聊与消息', /群聊|群成员|欢迎|退群|撤回|复读|好友|消息/],
  ['系统与状态', /系统|服务器|资源|存储|状态|统计|运行服务/],
  ['配置与管理', /配置|设置|登录|面板|管理|验证码|主人|开关|指令|帮助/],
  ['维护与更新', /备份|清理|恢复|重启|停止|关机|源码|更新|安装|日志|上线|下线|连接验证/],
]
export function categoryFor(row) {
  const words = `${row.title} ${row.command}`
  // Maintenance descriptions can mention settings without being configuration functions.
  if (/备份|清理|恢复|重启|停止|关机|更新|安装|日志|上线|下线|连接验证/.test(row.title)) return '维护与更新'
  return categories.find(([,test]) => test.test(words))?.[0] || '其他功能'
}
const clean = (value, max = 1500) => String(value ?? '').replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g,'').slice(0,max)
export function readPluginJSON(root, file) {
  try {
    const base=fs.realpathSync(root), target=path.resolve(base,file)
    if (!target.startsWith(base+path.sep) || fs.lstatSync(target).isSymbolicLink()) return {}
    const real=fs.realpathSync(target)
    if (!real.startsWith(base+path.sep) || fs.statSync(real).size>1024*1024) return {}
    const value=JSON.parse(fs.readFileSync(real,'utf8').replace(/^\uFEFF/,''))
    return value && typeof value==='object' && !Array.isArray(value) ? value : {}
  } catch { return {} }
}
function sourceOf(key) {
  const value=String(key||'').replaceAll('\\','/').replace(/^plugins\//,'')
  if (!value || value.includes(':') || value.startsWith('/') || value.split('/').some(p=>!p||p==='.'||p==='..')) return ''
  return value.includes('/') ? value : value+'/index.js'
}
function regexOf(rule) {
  try { return rule.reg instanceof RegExp ? new RegExp(rule.reg.source,rule.reg.flags.replace(/[gy]/g,'')) : new RegExp(rule.reg) }
  catch { return null }
}
function samples(command) {
  return String(command).split(/\s+\/\s+/).map(s=>s.split(/[；（]/)[0].trim().replace(/<[^>]+>/g,'插件').replace(/账号/g,'1').replace(/验证内容/g,'123'))
}
function accepts(rule, command) {
  const reg=regexOf(rule)
  return reg && samples(command).some(sample=>reg.test(sample) || reg.test(sample.split(/\s+/)[0]))
}
const ownerOnly = value => /仅主人|主人专用|主人获取|主人权限|^主人|only.?owner|master/i.test(String(value||''))
function protectedPermission(rule,p,doc,known) {
  if (ownerOnly(rule.permission)||ownerOnly(doc.permission)||ownerOnly(doc.description)) return 'master'
  // Unknown handler guards are conservatively treated as owner-only. Known mixed
  // dispatchers have per-operation documentation instead of hiding public branches.
  if (!known && /(?:isMaster|isOwner|\.masterQQ|permission\s*===?\s*['"]master)/.test(String(p[rule.fnc]||''))) return 'master'
  return ['owner','admin'].includes(rule.permission) ? rule.permission : ['owner','admin'].includes(doc.permission) ? doc.permission : 'all'
}
export function visible(row,event) { return row.permission !== 'master' || event.isMaster === true && !event.isGroup && !event.group_id }
export function buildCommandTable(loader, event={}, options={}) {
  const docs=options.docs||{}, root=options.pluginsRoot||'plugins', rows=[], seen=new Set(), inspected=new Set()
  let unparsed=0
  const add=(row)=>{
    row={...row,title:clean(row.title,160),command:clean(row.command,3000),description:clean(row.description,1000),permission:row.permission||'all'}
    if (!row.command || !visible(row,event)) return
    const key=`${row.title}\n${row.command}\n${row.permission}`
    if (seen.has(key)) return
    seen.add(key);rows.push({...row,category:categoryFor(row)})
  }
  for (const entry of Array.isArray(loader?.priority)?loader.priority:[]) {
    const p=entry?.plugin, source=sourceOf(entry?.key)
    if (!p || !source || !(String(p.event||'message').startsWith('message'))) continue
    const directory=source.split('/')[0]
    inspected.add(directory)
    const group=options.groupConfig||{}
    if (group.disable?.includes(p.name) || group.enable?.length && !group.enable.includes(p.name)) continue
    const pluginRoot=path.join(root,directory), manifest=readPluginJSON(pluginRoot,'orangejuice.plugin.json')
    let extension=Array.isArray(manifest.commandTable)?manifest.commandTable:docs.extensions?.[directory]
    const ai=directory==='AI-Plugin'?readPluginJSON(pluginRoot,'config/local.json'):null
    const search=directory==='WebSearch-Plugin'?readPluginJSON(pluginRoot,'config/plugin.json'):null
    if (ai?.basic?.enabled===false) continue
    for (const rule of Array.isArray(p.rule)?p.rule:[]) {
      if (!rule || rule.event && !String(rule.event).startsWith('message')) continue
      const note=docs.builtins?.[source+'::'+rule.fnc]
      const known=Boolean(note||extension)
      const candidates=note?[note]:Array.isArray(extension)?extension:[]
      let handled=false
      for (const raw of candidates) {
        if (!raw || typeof raw.command!=='string') continue
        let doc={...raw}
        if (directory==='AI-Plugin') {
          const prefix=ai.basic?.commandPrefix||'#AI'
          doc.command=doc.command.replaceAll('#AI',prefix)
          if (prefix.toLowerCase()!=='#ai' && raw.command.includes('#AI')) doc.command+=' / '+raw.command
          if (doc.title==='普通聊天' && (event.isGroup?ai.chat?.groupEnabled===false:ai.chat?.privateEnabled===false)) continue
          if (doc.title==='普通聊天') {
            const triggers=(Array.isArray(ai.presets)?ai.presets:[]).filter(x=>x.enabled!==false&&x.prefix).map(x=>clean(x.prefix,100)+' 提问')
            if(ai.basic?.triggerPrefix && ['prefix','both'].includes(ai.basic.triggerMode))triggers.push(clean(ai.basic.triggerPrefix,100)+' 提问')
            if(triggers.length)doc.command+=' / '+triggers.join(' / ')
          }
          if(doc.title==='切换角色')doc.command+=' / #切换预设 名称 / #chatgpt切换预设 名称'
          if(doc.title==='当前角色')doc.command+=' / #当前预设 / #chatgpt当前预设'
          if(doc.title==='结束对话')doc.command+=' / #结束对话 / #chatgpt结束对话'
        }
        if (!accepts(rule,doc.command) && !(directory==='AI-Plugin' && doc.title==='普通聊天')) continue
        handled=true
        let permission=protectedPermission(rule,p,doc,known)
        if (search?.masterOnly===true) permission='master'
        if (directory==='OrangeJuice-Plugin' && doc.title!=='统一指令表') permission='master'
        // Global keyword modification is owner-only even though the dispatcher is public.
        if (source==='system/add.js' && ['add','del'].includes(rule.fnc)) {
          // The note mentions owner-only GLOBAL operations; local operations use
          // group permissions and must not inherit that global restriction.
          permission=ownerOnly(rule.permission)?'master':'all'
          if(group.addLimit===2)permission='master'
          else if(group.addLimit===1)permission='admin'
          if(!visible({permission:'master'},event)){
            if(!event.isGroup && group.addPrivate!==1)continue
            doc.command=samples(doc.command).filter(s=>!s.includes('全局')).join(' / ')
            if (!doc.command) continue
          }
        }
        add({...doc,permission,source,directory,handler:rule.fnc})
      }
      if (handled) continue
      const pattern=rule.reg instanceof RegExp?rule.reg.source:String(rule.reg||'')
      if (!pattern || ['.*','^.*$','(.*)','^(.*)$','(?:)'].includes(pattern)) continue
      const fallback=clean(rule.command || rule.example || '')
      add({title:clean(rule.title||rule.dsc||p.name||'其他指令',160),command:fallback || '触发规则：/'+pattern+'/',description:clean(rule.description||p.dsc||'按注册规则触发；参数以插件帮助为准'),permission:protectedPermission(rule,p,{},false),source,directory,handler:rule.fnc})
      if (!fallback && visible({permission:protectedPermission(rule,p,{},false)},event)) unparsed++
    }
  }
  // Aliases use the permission of the resolved target; unknown targets are omitted.
  for (const alias of Array.isArray(options.aliases)?options.aliases:[]) {
    if (!alias || typeof alias.alias!=='string' || typeof alias.target!=='string') continue
    const rewritten=rewriteCommand(alias.alias,[alias])
    const target=rows.find(row=>samples(row.command).some(s=>s===rewritten || s.startsWith(rewritten+' ')))
    if (target) add({...target,title:target.title+'（自定义指令）',command:clean(alias.alias,200)+' [原指令参数]',description:'等同 '+clean(alias.target,200)+'；'+target.description})
  }
  const order=[...categories.map(x=>x[0]),'其他功能']
  rows.sort((a,b)=>order.indexOf(a.category)-order.indexOf(b.category)||a.title.localeCompare(b.title,'zh-CN')||a.command.localeCompare(b.command,'zh-CN'))
  return {rows,pluginCount:inspected.size,unparsed,complete:Boolean(event.isMaster&&!event.isGroup&&!event.group_id)}
}
export function commandMessages(table, maxLength=2800) {
  const header=`功能指令表 · ${table.rows.length}项\n${table.complete?'主人私聊完整表':'公开指令表（隐藏仅主人指令）'}\n已遍历${table.pluginCount}个已加载的消息插件；按功能分类。`
  const blocks=[header], groups=new Map()
  for(const row of table.rows) {
    if(!groups.has(row.category))groups.set(row.category,[])
    const permission=row.permission==='master'?'仅主人':row.permission==='admin'?'群管理员':row.permission==='owner'?'群主':''
    groups.get(row.category).push(`${row.title}${permission?' · '+permission:''}\n${row.command}\n${row.description}`)
  }
  for(const [category,rows] of groups) {
    let block=`【${category}】`
    for(const row of rows) {
      if(block.length+row.length+2>maxLength && block.length>category.length+2){blocks.push(block);block=`【${category} · 续】`}
      block+='\n\n'+row
    }
    blocks.push(block)
  }
  if(table.unparsed)blocks.push(`${table.unparsed}项插件未提供指令示例，已显示实际注册触发规则。`)
  return blocks
}
export async function replyCommandTable(e,table,{forward=true}={}) {
  const messages=commandMessages(table)
  const maker=e.group?.makeForwardMsg || e.friend?.makeForwardMsg || e.bot?.makeForwardMsg
  const context=e.group?.makeForwardMsg?e.group:e.friend?.makeForwardMsg?e.friend:e.bot
  if(forward && maker) {
    try {
      const nodes=messages.map(message=>({user_id:e.self_id||e.bot?.uin||e.user_id,nickname:'功能指令表',message}))
      const value=await maker.call(context,nodes)
      if(value){const receipt=await e.reply(value,Boolean(e.isGroup));if(receipt!==false && !receipt?.error && !(receipt?.retcode>0))return true}
    } catch { /* Adapters without forwarded messages receive the same complete text. */ }
  }
  for(const message of messages)await e.reply(message,Boolean(e.isGroup))
  return true
}
