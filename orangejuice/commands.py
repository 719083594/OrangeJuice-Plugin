"""Owner configuration commands use the same catalog and revision checks as the UI."""
import copy,hashlib,json,re
from .auth import Error
from .catalog import MASK,secret_key,field_values

ALIASES={'AI':'AI-Plugin','搜索':'WebSearch-Plugin','系统':'ServerStatus-Plugin','橙汁':'OrangeJuice-Plugin','内置插件':'framework','内置':'framework'}
TITLES={'bot':'机器人与运行日志','group':'群聊与回复','other':'好友与访问权限','db':'数据库','redis':'Redis 连接','server':'HTTP 服务','renderer':'截图渲染器','milky':'Milky 协议连接','satori':'Satori 协议连接'}

def config_title(entry,pid):
    stem=re.sub(r'\.(?:json|ya?ml)$','',entry['id'])
    return TITLES.get(stem,entry['title']) if pid=='framework' and entry['title'] in (stem,entry['id']) else entry['title']

def field_meta(path,fields):
    matches=[f for f in fields if len(str(f.get('path','')).split('.'))==len(path) and all(a=='*' or a==str(b) for a,b in zip(str(f.get('path','')).split('.'),path))]
    return next((f for f in matches if '*' not in f.get('path','')),matches[0] if matches else {})

def options(catalog,pid,labels=None):
    labels=labels or {};result=[]
    for entry in catalog.configs(pid):
        cfg=catalog.config(pid,entry['id']);fields=cfg['fields']
        def visit(value,path=(),trail=(),locked=False):
            meta=field_meta(path,fields);locked=locked or meta.get('readonly',False) or meta.get('status')=='planned'
            if path:
                label=meta.get('label') or labels.get(str(path[-1])) or str(path[-1])
                if isinstance(path[-1],int):label='第 '+str(path[-1]+1)+' 项'+(' · '+str(value.get('name',value.get('title',''))) if isinstance(value,dict) else '')
                trail=trail+(label,)
                token=hashlib.sha256(json.dumps([entry['id'],path],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:12]
                secret=value==MASK or any(secret_key(str(k)) for k in path) or bool(meta.get('secret'))
                result.append({'id':token,'config':entry['id'],'configTitle':config_title(entry,pid),'path':list(path),'label':' / '.join(trail),
                    'value':MASK if secret else copy.deepcopy(value),'secret':secret,'readonly':cfg['readonly'] or locked,
                    'revision':cfg['revision'],'reload':cfg['reload'],'type':meta.get('type') or ('boolean' if isinstance(value,bool) else 'number' if isinstance(value,(int,float)) else 'array' if isinstance(value,list) else 'object' if isinstance(value,dict) else 'string')})
            if isinstance(value,dict) and value!=MASK:
                for key,item in value.items():visit(item,path+(key,),trail,locked)
            elif isinstance(value,list):
                for index,item in enumerate(value):
                    if isinstance(item,dict):visit(item,path+(index,),trail,locked)
        visit(cfg['value'])
    return result

def resolve_plugin(catalog,name):
    pid=ALIASES.get(name,name)
    if pid=='orangejuice' and catalog.configs(pid):return pid
    available={p['id']:p for p in catalog.list()}
    if pid not in available:
        candidates=[p['id'] for p in available.values() if p['title']==name]
        if len(candidates)!=1:raise Error('插件不存在；发送 #橙汁配置 查看名称')
        pid=candidates[0]
    return pid

def run(catalog,payload,labels=None):
    action=payload.get('action');name=str(payload.get('plugin',''))
    if action=='config-list' and not name:
        return {'text':'可配置插件：\n'+'\n'.join(p['title'] for p in catalog.list() if not p['builtin'] or p['id']=='framework')+'\n#橙汁配置 插件名 [搜索词或页码]\n#橙汁设置 插件名 选项编号 @版本 值\n修改仅主人私聊可用；值支持 JSON、文本、开/关。'}
    pid=resolve_plugin(catalog,name);items=options(catalog,pid,labels)
    if action=='config-list':
        query=str(payload.get('query','')).strip();page=int(query) if query.isdigit() else 1
        if not 1<=page<=10000:raise Error('页码无效')
        if query and not query.isdigit():
            query={'角色提示词':'提示词','人设':'提示词'}.get(query,query)
            items=[x for x in items if query.lower() in (x['label']+' '+x['configTitle']).lower()]
        leaf=[x for x in items if x['type']!='object'];page_items=leaf[(page-1)*10:page*10];pages=max(1,(len(leaf)+9)//10)
        lines=[f'{name} 配置 · 第 {page}/{pages} 页 · {len(leaf)} 项']
        for row in page_items:
            value=json.dumps(row['value'],ensure_ascii=False)
            lines.append(row['configTitle']+' · '+row['label']+' = '+value[:160]+('…' if len(value)>160 else ''))
            if not row['readonly']:lines.append(f'#橙汁设置 {name} {row["id"]} @{row["revision"][:16]} 值')
            else:lines.append('只读或计划功能')
        if not page_items:lines.append('没有匹配项；发送 #橙汁配置 '+name+' 查看全部设置。')
        return {'text':'\n'.join(lines)}
    if action!='config-set':raise Error('不支持的配置操作')
    row=next((x for x in items if x['id']==payload.get('option')),None)
    if not row:raise Error('配置项不存在，请重新查看配置列表')
    revision=str(payload.get('revision',''))
    if not (revision=='missing' and row['revision']=='missing') and (len(revision)<16 or not row['revision'].startswith(revision)):raise Error('配置已变化，请重新查看列表后再修改',409)
    if row['readonly']:raise Error('此项只读或尚未实现',403)
    raw=str(payload.get('value',''))
    if len(raw)>20000:raise Error('配置内容过长')
    if raw in ('开','开启','关','关闭'):value=raw in ('开','开启')
    else:
        try:value=json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        except ValueError:
            if row['type']!='string':raise Error('此项需要有效 JSON 数值、数组或对象')
            value=raw
    cfg=catalog.config(pid,row['config']);updated=copy.deepcopy(cfg['value']);parent=updated
    for key in row['path'][:-1]:parent=parent[key]
    parent[row['path'][-1]]=value
    for field in cfg['fields']:
        if not (field.get('readonly') or field.get('status')=='planned'):continue
        parts=str(field.get('path','')).split('.')
        if list(field_values(updated,parts))!=list(field_values(cfg['value'],parts)):raise Error('包含只读或计划字段，不能通过上层配置修改',403)
    result=catalog.save(pid,row['config'],updated,row['revision'])
    return {'text':'已保存：'+row['label']+'。'+('下次使用时生效。' if result['reload']=='live' else '重启相关服务后生效。'),'saved':True,'plugin':pid,'config':row['config']}

def function_control(catalog,payload):
    report=catalog.features();items=[x for x in report['items'] if x['pluginId']=='framework' and x['kind'] not in ('task','module')]
    name=payload.get('name','')
    if not name:
        unique={x['name']:x for x in items}
        return {'text':'内置功能（默认设置；账号或群覆盖单独配置）：\n'+'\n'.join(x['displayName']+'：'+{'enabled':'开','disabled':'关','not-allowed':'不在启用列表'}.get(x['defaultState'],'未配置') for x in unique.values())+'\n#橙汁功能 功能名 开 / 关'}
    matches=[x for x in items if name in (x['name'],x['displayName'])]
    if not matches:raise Error('没有匹配的内置功能；模块和定时任务请在配置项中管理')
    names=set(x['name'] for x in matches)
    state=payload.get('enabled')
    if not isinstance(state,bool):raise Error('请指定开或关')
    cfg=catalog.config('framework','group.yaml');value=copy.deepcopy(cfg['value']);default=value.setdefault('default',{})
    disabled=default.setdefault('disable',[]);enabled=default.setdefault('enable',[])
    if not isinstance(disabled,list) or not isinstance(enabled,list):raise Error('群聊控制列表格式无效')
    default['disable']=[x for x in disabled if x not in names]
    if not state:default['disable']+=sorted(names)
    elif enabled:default['enable']=enabled+sorted(names-set(enabled))
    catalog.save('framework','group.yaml',value,cfg['revision'])
    return {'text':'已'+('开启' if state else '关闭')+'默认内置功能：'+name+'。账号或群单独设置仍优先。','saved':True,'plugin':'framework','config':'group.yaml'}
