// One exact prefix rewrite per message. The target plugin keeps its permission checks.
export function rewriteCommand(message,aliases=[]){
  const text=String(message||'').trim()
  for(const row of aliases){
    if(!row||typeof row.alias!=='string'||typeof row.target!=='string')continue
    const alias=row.alias.trim(),target=row.target.trim()
    if(!alias||!target||alias===target||alias.length>100||target.length>200)continue
    if(text===alias||text.startsWith(alias+' '))return target+text.slice(alias.length)
  }
  return text
}
export function configurationPayload(message){
  const match=String(message||'').trim().match(/^[#/]?(?:橙汁|OrangeJuice)(配置|设置|功能)(?:\s+(.*))?$/is)
  if(!match)return null
  const body=match[2]||''
  if(match[1]==='功能'){
    if(!body.trim())return {action:'function-control'}
    const m=body.trim().match(/^(.+?)\s+(开|关|开启|关闭)$/)
    if(!m)throw new Error('用法：#橙汁功能 功能名 开 / 关')
    return {action:'function-control',name:m[1],enabled:m[2]==='开'||m[2]==='开启'}
  }
  if(match[1]==='配置'){
    const [plugin='',...query]=body.trim().split(/\s+/)
    return {action:'config-list',plugin,query:query.join(' ')}
  }
  const set=body.match(/^(\S+)\s+([a-f0-9]{12})\s+@([a-f0-9]{16,64}|missing)\s+([\s\S]+)$/)
  if(!set)throw new Error('用法：#橙汁设置 插件名 选项编号 @版本 值。先发送 #橙汁配置 插件名 查看。')
  return {action:'config-set',plugin:set[1],option:set[2],revision:set[3],value:set[4]}
}
