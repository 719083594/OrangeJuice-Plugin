// Read registration metadata only: do not instantiate plugins or execute rules.
const builtin = new Set(['system', 'other', 'example', 'adapter'])
const text = (value, limit = 500) => typeof value === 'string' ? value.slice(0, limit) : ''
function sourceOf(key) {
  const value = text(key, 500).replaceAll('\\', '/').replace(/^plugins\//, '')
  if (!value || value.startsWith('/') || value.includes(':') || value.split('/').some(x => !x || x === '.' || x === '..')) return ''
  return value.includes('/') ? value : value + '/index.js'
}
function origin(source) { return source ? builtin.has(source.split('/')[0]) ? 'framework' : 'extension' : 'unknown' }
export function featureSnapshot(loader = {}) {
  const features = [], files = new Map(); let bytes = 0, truncated = false
  const add = item => {
    const size = Buffer.byteLength(JSON.stringify(item))
    if (features.length >= 2000 || bytes + size > 600000) { truncated = true; return }
    bytes += size; features.push(item)
  }
  const file = (key, count = null) => {
    const source = sourceOf(key); if (!source) return ''
    if (!files.has(source) && files.size < 1500) files.set(source, {source, directory:source.split('/')[0], origin:origin(source), importedClasses:count, featureCount:0})
    else if (!files.has(source)) truncated = true
    return source
  }
  if (loader.pluginCountMap instanceof Map) for (const [key, count] of loader.pluginCountMap) file(key, Number.isInteger(count) && count >= 0 ? count : null)
  for (const [index, entry] of (Array.isArray(loader.priority) ? loader.priority : []).entries()) {
    if (!entry?.plugin) continue
    const p = entry.plugin, source = file(entry.key), event = text(p.event, 160) || 'message'
    const rawRules = Array.isArray(p.rule) ? p.rule : [], rules = rawRules.slice(0, 80).filter(rule => rule && typeof rule === 'object').map(rule => ({
      pattern:rule.reg instanceof RegExp ? rule.reg.source.slice(0, 2000) : text(rule.reg, 2000),
      flags:rule.reg instanceof RegExp ? rule.reg.flags : '', handler:text(rule.fnc, 160),
      permission:text(rule.permission, 100) || 'all', event:text(rule.event, 160) || event
    }))
    if (rawRules.length > rules.length) truncated = true
    if (rawRules.some(rule => (rule?.reg instanceof RegExp ? rule.reg.source : text(rule?.reg, 100000)).length > 2000)) truncated = true
    const hooks = ['accept', 'getContext'].filter(name => typeof p[name] === 'function')
    const handlers = (Array.isArray(p.handler) ? p.handler : p.handler && typeof p.handler === 'object' ? Object.values(p.handler) : []).slice(0, 80).map(item => text(item?.key, 160)).filter(Boolean)
    add({id:(source || 'unknown')+'::'+text(entry.class?.name, 160)+'::'+index, name:text(p.name || entry.name, 160) || '未命名功能', description:text(p.dsc, 1000), source, directory:source.split('/')[0], origin:origin(source),
      kind:event.startsWith('notice') ? 'notice' : rules.length ? 'command' : hooks.length ? 'hook' : 'integration', event, rules, hooks, handlers,
      priority:Number.isFinite(entry.priority) ? entry.priority : null, registered:true})
  }
  const taskSources = new Map()
  if (loader.taskMap instanceof Map) for (const [key, tasks] of loader.taskMap) if (tasks && typeof tasks[Symbol.iterator] === 'function') for (const task of tasks) taskSources.set(task, file(key))
  for (const [index, task] of (Array.isArray(loader.task) ? loader.task : []).entries()) {
    if (!task || typeof task !== 'object') continue
    const source = taskSources.get(task) || ''
    add({id:(source || 'unknown')+'::task::'+index, name:text(task.name, 160) || '未命名定时任务', description:'按框架计划执行', source, directory:source.split('/')[0], origin:origin(source), kind:'task', event:'schedule', cron:text(task.cron, 200), scheduled:Boolean(task.job), rules:[], hooks:[], handlers:[], priority:null, registered:true})
  }
  const withEntries = new Set(features.map(item => item.source))
  for (const info of files.values()) if (!withEntries.has(info.source)) add({id:info.source+'::module', name:info.source.split('/').at(-1).replace(/\.[^.]+$/, ''), description:'框架模块登记；没有已注册消息处理器或定时任务', source:info.source, directory:info.directory, origin:info.origin, kind:'module', event:'initialization', rules:[], hooks:[], handlers:[], priority:null, registered:null})
  for (const item of features) if (files.has(item.source)) files.get(item.source).featureCount++
  return {schemaVersion:1, features, files:[...files.values()], truncated}
}
