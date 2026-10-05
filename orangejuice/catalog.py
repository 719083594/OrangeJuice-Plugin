import copy,hashlib,json,math,os,re,secrets,shutil,subprocess,threading,time
from pathlib import Path
import yaml
from .auth import Error,atomic

MASK='••••••••'
SECRET=re.compile(r'password|passwd|token|secret|api.?key|authorization|cookie|private.?key|credential|^auth$',re.I)
PUBLIC_TOKEN_FIELDS={'maxtoken','maxtokens','maxoutputtokens','inputtokens','outputtokens','totaltokens','cachedtokens','reasoningtokens','tokenbudget','tokenlimit','maxcontexttokens','usetoken'}
BLOCKED={'__proto__','constructor','prototype'}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def read_document(path):
    raw=path.read_bytes()
    if len(raw)>1024*1024:raise Error('配置文件超过1MB')
    value=json.loads(raw) if path.suffix=='.json' else yaml.safe_load(raw)
    return ({} if value is None else value),digest(raw)
def secret_key(key):return bool(SECRET.search(key)) and re.sub(r'[_\-]','',key.lower()) not in PUBLIC_TOKEN_FIELDS
def mask(value,key=''):
    if secret_key(key) and value not in (None,'',{},[]):return MASK
    if isinstance(value,dict):return {k:mask(v,str(k)) for k,v in value.items()}
    if isinstance(value,list):return [mask(v,key) for v in value]
    return value
def restore_mask(value,original,key=''):
    if isinstance(value,str) and value==MASK:return copy.deepcopy(original)
    if secret_key(key) and isinstance(original,(dict,list)) and value==MASK:return copy.deepcopy(original)
    if isinstance(value,dict):
        if any(str(k) in BLOCKED for k in value):raise Error('配置包含保留字段')
        return {k:restore_mask(v,original.get(k) if isinstance(original,dict) else None,str(k)) for k,v in value.items()}
    if isinstance(value,list):
        before=original if isinstance(original,list) else []
        def masked(v):
            if isinstance(v,str):return v==MASK
            if isinstance(v,dict):return any(masked(x) for x in v.values())
            if isinstance(v,list):return any(masked(x) for x in v)
            return False
        masked_ids=[item['id'] for item in value if isinstance(item,dict) and item.get('id') and masked(item)]
        if len(masked_ids)!=len(set(map(str,masked_ids))):raise Error('含密钥的数组项标识不能重复')
        restored=[]
        for i,item in enumerate(value):
            previous=before[i] if i<len(before) else None
            if isinstance(item,dict) and masked(item):
                matches=[old for old in before if isinstance(old,dict) and old.get('id')==item['id']] if item.get('id') else [old for old in before if mask(old)==item]
                if len(matches)!=1:raise Error('含密钥的数组项需保留唯一标识；新项请填写密钥，勿复制遮罩')
                previous=matches[0]
            restored.append(restore_mask(item,previous,key))
        return restored
    return value

def field_values(value,parts,path=()):
    """Expand declared wildcard fields without executing plugin code."""
    if not parts:
        yield path,value;return
    part,*remaining=parts
    if part=='*':
        children=enumerate(value) if isinstance(value,list) else value.items() if isinstance(value,dict) else []
        for key,item in children:yield from field_values(item,remaining,path+(key,))
    elif isinstance(value,dict):
        yield from field_values(value.get(part),remaining,path+(part,))
    elif isinstance(value,list) and part.isdigit() and int(part)<len(value):
        index=int(part);yield from field_values(value[index],remaining,path+(index,))
    else:
        yield path+(part,),None

def mask_fields(value,fields):
    result=mask(value)
    for field in fields:
        if not field.get('secret'):continue
        for path,current in field_values(value,str(field.get('path','')).split('.')):
            if not path or current in (None,'',{},[]):continue
            parent=result
            try:
                for key in path[:-1]:parent=parent[key]
                parent[path[-1]]=MASK
            except (KeyError,IndexError,TypeError):pass
    return result

class Catalog:
    def __init__(self,settings,data):
        self.settings=settings;self.data=Path(data);self.lock=threading.RLock();self.root=Path(settings.get('pluginsDirectory','plugins')).resolve()
        self.framework=Path(settings.get('frameworkRoot',self.root.parent)).resolve()
        self.backups=self.data/'backups';self.backups.mkdir(parents=True,exist_ok=True)
    def runtime(self):
        try:
            p=Path(self.settings.get('runtimeFile',self.data/'runtime.json'));raw=p.read_bytes()
            if len(raw)>2_000_000:return {}
            result=json.loads(raw);result['stale']=time.time()-result.get('timestamp',0)>30;return result
        except (OSError,ValueError):return {'stale':True,'bots':[],'plugins':[]}
    def safe(self,path,root):
        root=Path(root).resolve();p=Path(path)
        if p.is_symlink() or not p.resolve().is_relative_to(root):raise Error('配置路径不允许访问',403)
        return p.resolve()
    def plugin(self,pid):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',pid):raise Error('无效插件名称')
        p=self.safe(self.root/pid,self.root)
        if not p.is_dir():raise Error('插件不存在',404)
        return p
    def manifest(self,root):
        p=root/'orangejuice.plugin.json'
        if p.is_file():
            try:
                value=json.loads(p.read_text(encoding='utf-8'));return value if isinstance(value,dict) else {}
            except (OSError,ValueError):pass
        return {}
    def capabilities(self,root,manifest):
        declared=manifest.get('capabilities')
        if not declared:return []
        if isinstance(declared,str):
            p=self.safe(root/declared,root)
            if p.suffix!='.json' or not p.is_file():return []
            declared=read_document(p)[0]
        if isinstance(declared,dict):declared=declared.get('capabilities',[])
        if not isinstance(declared,list):return []
        result=[]
        for item in declared[:100]:
            if not isinstance(item,dict):continue
            result.append({k:str(item.get(k,''))[:2000] for k in ('id','title','description','status','reason')})
        return result
    def list(self):
        result=[];runtime=self.runtime();loaded={x.get('directory'):x for x in runtime.get('plugins',[])}
        self.root.mkdir(parents=True,exist_ok=True)
        for root in sorted(self.root.iterdir(),key=lambda p:p.name.lower()):
            if root.is_symlink() or not root.is_dir() or root.name.startswith('.'):continue
            pkg={}
            try:pkg=json.loads((root/'package.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
            manifest=self.manifest(root);author=pkg.get('author','未提供')
            overrides=self.settings.get('pluginMetadata',{}).get(root.name,{})
            presentation={**manifest,**{k:v for k,v in overrides.items() if k in ('title','description','author','version','repository','homepage','commands')}} if isinstance(overrides,dict) else manifest
            author=presentation.get('author',author)
            if isinstance(author,dict):author=author.get('name','未提供')
            try:configs=self.configs(root.name);config_error=None
            except (Error,OSError,ValueError,TypeError):configs=[];config_error='配置清单无效，请检查插件声明'
            title=presentation.get('title') or {'chatgpt-plugin':'ChatGPT-Plugin','deployment-admin':'DeploymentAdmin','OrangeJuice-Plugin':'OrangeJuice-Plugin'}.get(root.name,pkg.get('displayName',root.name))
            repository=presentation.get('repository',pkg.get('repository',{}))
            if isinstance(repository,dict):repository=repository.get('url','')
            if not isinstance(repository,str) or not repository.startswith(('https://github.com/','https://gitee.com/')):repository=''
            item={'id':root.name,'title':title,'description':presentation.get('description',pkg.get('description','未提供功能介绍')),'author':str(author),'version':presentation.get('version',pkg.get('version','未提供')),'repository':repository.removesuffix('.git'),'native':bool(manifest),'configCount':len(configs),'builtin':root.name in ('adapter','system','other','example'),'readonly':root.name in self.settings.get('readonlyPlugins',[]),'loaded':loaded.get(root.name,{}).get('loaded'),'icon':any((root/p).is_file() for p in ['resources/icon.png','resources/icon.svg']),'homepage':presentation.get('homepage'),'commands':presentation.get('commands',[])}
            item['configError']=config_error
            item['managementPanel']=manifest.get('managementPanel') if isinstance(manifest.get('managementPanel'),str) else None
            try:item['capabilities']=self.capabilities(root,manifest)
            except (Error,OSError,ValueError,TypeError):item['capabilities']=[]
            result.append(item)
        return result
    def configs(self,pid):
        if pid=='framework':
            directory=self.safe(Path(self.settings.get('frameworkConfigsDirectory',self.framework/'config/config')),self.framework)
            return [{'id':p.name,'title':p.stem,'path':p,'root':directory,'readonly':False,'fields':[],'reload':'restart'} for p in sorted(directory.glob('*')) if p.suffix in ('.json','.yaml','.yml') and not p.is_symlink()]
        root=self.plugin(pid);manifest=self.manifest(root);entries=[];seen=set()
        readonly=pid in self.settings.get('readonlyPlugins',[])
        for i,cfg in enumerate(manifest.get('configs',[])):
            p=self.safe(root/cfg.get('file',''),root)
            if p.suffix not in ('.json','.yaml','.yml'):continue
            default=cfg.get('defaults',{});example=cfg.get('example')
            if not p.exists() and example:
                try:default=read_document(self.safe(root/example,root))[0]
                except (OSError,ValueError):pass
            entries.append({'id':str(cfg.get('id',i)),'title':cfg.get('title',p.stem),'path':p,'root':root,'readonly':readonly or cfg.get('readonly',False),'ownerOnly':bool(cfg.get('ownerOnly',False)),'fields':cfg.get('fields',[]),'defaults':default,'reload':cfg.get('reload','restart')});seen.add(p)
        capabilities_path=manifest.get('capabilities')
        if isinstance(capabilities_path,str):seen.add(self.safe(root/capabilities_path,root))
        for directory in [root,root/'config',root/'data']:
            if not directory.is_dir() or directory.is_symlink():continue
            for p in sorted(directory.iterdir()):
                if p.is_symlink() or not p.is_file() or p.suffix not in ('.json','.yaml','.yml') or p in seen:continue
                if p.name in ('package.json','package-lock.json','pnpm-lock.yaml','orangejuice.plugin.json') or re.search(r'example|sample|test|verification|schema|lock',p.name,re.I):continue
                if directory.name=='data' and p.name!='config.json':continue
                p=self.safe(p,root);entries.append({'id':'file:'+p.relative_to(root).as_posix(),'title':p.relative_to(root).as_posix(),'path':p,'root':root,'readonly':readonly,'fields':[],'reload':'restart'});seen.add(p)
        for cfg in self.settings.get('extraConfigs',[]):
            if cfg.get('plugin')==pid:
                p=Path(cfg['path']).resolve();entries.append({'id':cfg['id'],'title':cfg.get('title',p.name),'path':p,'root':p.parent,'readonly':readonly or cfg.get('readonly',False),'ownerOnly':bool(cfg.get('ownerOnly',False)),'fields':cfg.get('fields',[]),'reload':cfg.get('reload','restart')})
        return entries
    def entry(self,pid,cid):
        item=next((x for x in self.configs(pid) if x['id']==cid),None)
        if not item:raise Error('配置项不存在',404)
        self.safe(item['path'],item['root']);return item
    def config(self,pid,cid):
        item=self.entry(pid,cid);p=item['path'];value,revision=read_document(p) if p.exists() else (item.get('defaults',{}),'missing')
        return {'id':cid,'title':item['title'],'value':mask_fields(value,item['fields']),'revision':revision,'readonly':item['readonly'],'ownerOnly':item.get('ownerOnly',False),'fields':item['fields'],'reload':item['reload'],'format':p.suffix.removeprefix('.')}
    def validate(self,value,fields):
        for field in fields:
            for _,current in field_values(value,str(field.get('path','')).split('.')):
                if current is None:
                    if field.get('required'):raise Error(field.get('label',field['path'])+'不能为空')
                    continue
                kind=field.get('type');types={'boolean':bool,'number':(int,float),'integer':int,'string':str,'array':list,'object':dict}
                if kind in types and (not isinstance(current,types[kind]) or kind in ('number','integer') and isinstance(current,bool)):raise Error(field.get('label',field['path'])+'类型不正确')
                if isinstance(current,(int,float)) and not isinstance(current,bool):
                    if 'min' in field and current<field['min'] or 'max' in field and current>field['max']:raise Error(field.get('label',field['path'])+'超出允许范围')
                if 'enum' in field and current not in field['enum']:raise Error(field.get('label',field['path'])+'不是有效选项')
    def save(self,pid,cid,value,revision):
        with self.lock:
            item=self.entry(pid,cid)
            if item['readonly']:raise Error('此插件配置当前为只读',403)
            p=item['path'];original,current=read_document(p) if p.exists() else (item.get('defaults',{}),'missing')
            if revision!=current:raise Error('配置已被其他操作更新，请重新读取后保存',409)
            if not isinstance(value,(dict,list)):raise Error('配置应为对象或数组')
            value=restore_mask(value,original);self.validate(value,item['fields'])
            def finite(v):
                if isinstance(v,float) and not math.isfinite(v):raise Error('数值必须有限')
                if isinstance(v,dict):
                    for k,x in v.items():
                        if not isinstance(k,str):raise Error('配置字段名称必须为字符串')
                        finite(x)
                elif isinstance(v,list):
                    for x in v:finite(x)
            finite(value)
            # A generic editor must not silently change the types of existing leaves.
            def types(a,b):
                if isinstance(a,dict) and isinstance(b,dict):
                    for k in a.keys()&b.keys():types(a[k],b[k])
                elif a is not None and b is not None and not isinstance(a,(dict,list)):
                    if isinstance(a,bool)!=isinstance(b,bool) or isinstance(a,(int,float)) and not isinstance(b,(int,float)) or isinstance(a,str) and not isinstance(b,str):raise Error('已有配置字段的类型不能改变')
            types(original,value)
            if p.exists():
                backup_id=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(5)
                folder=self.backups/backup_id;folder.mkdir(mode=0o700);shutil.copy2(p,folder/'content');os.chmod(folder/'content',0o600)
                atomic(folder/'meta.json',{'id':backup_id,'plugin':pid,'config':cid,'time':time.time(),'revision':current})
            raw=json.dumps(value,ensure_ascii=False,indent=2)+'\n' if p.suffix=='.json' else yaml.safe_dump(value,allow_unicode=True,sort_keys=False)
            p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+secrets.token_hex(4)+'.tmp');tmp.write_text(raw,encoding='utf-8');os.chmod(tmp,0o600);os.replace(tmp,p)
            backups=sorted(self.backups.iterdir(),key=lambda x:x.name)
            for folder in backups[:-100]:shutil.rmtree(folder)
            return {'revision':digest(p.read_bytes()),'reload':item['reload'],'saved':True}
    def backup_list(self):
        result=[]
        for p in sorted(self.backups.glob('*/meta.json'),reverse=True):
            try:result.append(json.loads(p.read_text(encoding='utf-8')))
            except (OSError,ValueError):pass
        return result[:100]
    def restore(self,bid,revision):
        if not re.fullmatch(r'[A-Za-z0-9-]{1,80}',bid):raise Error('无效备份名称')
        folder=self.safe(self.backups/bid,self.backups)
        if not (folder/'meta.json').exists():raise Error('备份不存在',404)
        meta=json.loads((folder/'meta.json').read_text(encoding='utf-8'));item=self.entry(meta['plugin'],meta['config'])
        raw=(folder/'content').read_bytes();value=json.loads(raw) if item['path'].suffix=='.json' else yaml.safe_load(raw)
        return self.save(meta['plugin'],meta['config'],value,revision)
    def readme(self,pid):
        root=self.plugin(pid)
        for name in ['README.md','readme.md','README.MD']:
            p=root/name
            if p.is_file() and not p.is_symlink():return p.read_text(encoding='utf-8',errors='replace')[:200000]
        return '此插件没有提供 README。'
    def mutate_plugin(self,action,payload):
        if action=='install':
            name=payload.get('name','');url=payload.get('url','')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',name):raise Error('安装目录名称不正确')
            if not re.fullmatch(r'https://(?:github\.com|gitee\.com)/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',url):raise Error('仅支持 GitHub/Gitee 的 HTTPS 仓库地址')
            target=self.safe(self.root/name,self.root)
            if target.exists():raise Error('安装目录已存在',409)
            temp=self.root/('.install-'+secrets.token_hex(8))
            try:
                run=subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--depth','1','--',url,str(temp)],capture_output=True,text=True,timeout=90,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
                if run.returncode:raise Error('Git 下载失败，请检查网络或仓库地址',502)
                temp.rename(target)
            finally:
                if temp.exists():shutil.rmtree(temp)
            return {'installed':name,'reload':'restart'}
        name=payload.get('plugin','');root=self.plugin(name)
        if name in self.settings.get('readonlyPlugins',[]) or name in ('OrangeJuice-Plugin','system','adapter','other','example','deployment-admin'):raise Error('此组件不允许通过面板更新或卸载',403)
        if action=='remove':
            folder=self.data/'removed'/time.strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=True);root.rename(folder/name);return {'removed':name,'reload':'restart'}
        if action=='update':
            if not (root/'.git').is_dir():raise Error('此插件不是 Git 安装，请使用完整安装包更新')
            git=lambda *args:subprocess.run(['git','-c','core.hooksPath=/dev/null','-C',str(root),*args],capture_output=True,text=True,timeout=90,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
            if git('status','--porcelain').stdout.strip():raise Error('插件有本地修改，请先备份并处理，面板不会强制覆盖',409)
            remote=git('remote','get-url','origin').stdout.strip()
            if not re.fullmatch(r'https://(?:github\.com|gitee\.com)/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',remote):raise Error('仓库来源不在允许范围内')
            result=git('pull','--ff-only')
            if result.returncode:raise Error('更新失败，请检查网络或分支状态',502)
            return {'updated':name,'reload':'restart'}
        raise Error('不支持的操作')
