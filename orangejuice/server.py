import argparse,base64,hashlib,hmac,http.cookies,http.server,io,json,mimetypes,os,secrets,subprocess,sys,threading,time,urllib.parse,urllib.request
from pathlib import Path
from .auth import Auth,Error,atomic
from .catalog import Catalog,mask
from .system import Monitor

WEB=Path(__file__).resolve().parent.parent/'web'
VERSION='1.3.0'

class App:
    def __init__(self,settings,data):
        self.settings=settings;self.data=Path(data);self.auth=Auth(self.data);self.catalog=Catalog(settings,self.data);self.monitor=Monitor();self.action_lock=threading.Lock()
    def audit(self,user,action,target='',ok=True):
        path=self.data/'audit.jsonl'
        if path.exists() and path.stat().st_size>2_000_000:os.replace(path,self.data/'audit.previous.jsonl')
        with path.open('a',encoding='utf-8') as f:f.write(json.dumps({'time':time.time(),'user':user,'action':action,'target':target,'ok':ok},ensure_ascii=False)+'\n')
        os.chmod(path,0o600)
    def activities(self):
        path=self.data/'audit.jsonl'
        if not path.exists():return []
        return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()[-100:]][::-1]
    def action(self,name):
        action=next((x for x in self.settings.get('actions',[]) if x.get('id')==name),None)
        if not action:raise Error('此操作未由部署管理员启用',403)
        args=action.get('command')
        if not isinstance(args,list) or not args or any(not isinstance(x,str) for x in args):raise Error('操作配置无效')
        if not self.action_lock.acquire(False):raise Error('已有服务操作正在执行',409)
        try:
            result=subprocess.run(args,capture_output=True,text=True,timeout=60,shell=False)
            if result.returncode:raise Error('操作未成功，请查看服务日志',502)
            return {'ok':True,'message':'操作已完成'}
        except subprocess.TimeoutExpired:raise Error('操作等待超时，请检查服务状态',504)
        finally:self.action_lock.release()

class Handler(http.server.BaseHTTPRequestHandler):
    server_version='OrangeJuice';sys_version=''
    @property
    def app(self):return self.server.app
    def log_message(self,*args):pass
    def headers_base(self,kind='application/json; charset=utf-8'):
        self.send_header('Content-Type',kind);self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    def output(self,data,status=200,cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.headers_base();self.send_header('Content-Length',str(len(raw)))
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(raw)
    def json_body(self):
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:raise Error('请求长度不正确')
        if not 0<length<=1_000_000:raise Error('请求内容为空或过大',413)
        try:body=json.loads(self.rfile.read(length),parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except (ValueError,UnicodeError):raise Error('请求不是有效JSON')
        if not isinstance(body,dict):raise Error('请求应为对象')
        return body
    def same_origin(self):
        origin=self.headers.get('Origin')
        expected=('https://' if self.app.settings.get('secureCookies') else 'http://')+self.headers.get('Host','')
        if origin and origin!=expected and origin not in self.app.settings.get('allowedOrigins',[]):raise Error('请求来源不允许',403)
    def session(self,write=False):
        cookie=http.cookies.SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except http.cookies.CookieError:raise Error('登录凭据无效',401)
        sid=cookie['oj_session'].value if 'oj_session' in cookie else ''
        session=self.app.auth.get(sid)
        if write:
            self.same_origin()
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):raise Error('请求校验失败，请刷新后重试',403)
        return sid,session
    def signed(self,body):
        timestamp=self.headers.get('X-OJ-Time','');signature=self.headers.get('X-OJ-Signature','')
        try:
            if abs(time.time()-float(timestamp))>30:return False
        except ValueError:return False
        digest=hashlib.sha256(body).hexdigest();expected=hmac.new(self.app.auth.bridge_key.encode(),(timestamp+'\n'+digest).encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature,expected)
    def cookie(self,sid):return 'oj_session='+sid+'; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200'+('; Secure' if self.app.settings.get('secureCookies') else '')
    def login_response(self,result):
        sid,session=result;self.app.audit(session['username'],'login');self.output({'user':{k:v for k,v in session.items() if k!='expires'},'expires':session['expires']},cookie=self.cookie(sid))
    def do_GET(self):self.dispatch('GET')
    def do_POST(self):self.dispatch('POST')
    def do_PUT(self):self.dispatch('PUT')
    def do_DELETE(self):self.dispatch('DELETE')
    def dispatch(self,method):
        try:self.route(method)
        except Error as error:self.output({'error':str(error)},error.status)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as error:
            print('request failed: '+type(error).__name__,flush=True)
            self.output({'error':'操作未完成，请检查配置格式和服务日志'},500)
    def route(self,method):
        parsed=urllib.parse.urlsplit(self.path);path=parsed.path;query=urllib.parse.parse_qs(parsed.query)
        arg=lambda key:query.get(key,[''])[0]
        if path=='/healthz':return self.output({'ok':True,'name':'OrangeJuice-Plugin','version':VERSION})
        if not path.startswith('/api/'):
            if method!='GET':raise Error('方法不允许',405)
            rel=urllib.parse.unquote(path).lstrip('/') or 'index.html';p=(WEB/rel).resolve()
            if not p.is_relative_to(WEB.resolve()) or not p.is_file() or p.is_symlink():raise Error('页面不存在',404)
            raw=p.read_bytes();self.send_response(200);self.headers_base(mimetypes.guess_type(p.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(raw)));self.end_headers();return self.wfile.write(raw)
        if path=='/api/internal/ticket' and method=='POST':
            body=self.json_body()
            # The bridge and CLI use signed local requests. Browser sessions cannot call it.
            raw=json.dumps(body,separators=(',',':')).encode()
            if not self.signed(raw):raise Error('内部请求认证失败',403)
            return self.output({'ticket':self.app.auth.ticket()})
        if path in ('/api/auth/login','/api/auth/ticket','/api/auth/code','/api/auth/request-code') and method=='POST':
            self.same_origin();body=self.json_body();peer=self.client_address[0]
            if path=='/api/auth/login':return self.login_response(self.app.auth.login(body.get('username',''),body.get('password',''),peer))
            if path=='/api/auth/ticket':return self.login_response(self.app.auth.consume(body.get('ticket',''),peer))
            if path=='/api/auth/code':return self.login_response(self.app.auth.consume(body.get('code',''),peer,'code'))
            if path=='/api/auth/request-code':
                code=self.app.auth.code(peer);print('OrangeJuice 控制台登录验证码（5分钟一次有效）: '+code,flush=True);return self.output({'ok':True,'message':'验证码已写入服务控制台'})
        sid,session=self.session(method!='GET');role=session['role'];user=session['username']
        def config_summary(entry):
            result={k:v for k,v in entry.items() if k in ('id','title','readonly','reload','ownerOnly')}
            result['readonly']=entry.get('readonly',False) or entry.get('ownerOnly',False) and role!='owner'
            return result
        if path=='/api/me' and method=='GET':return self.output({'username':user,'role':role,'csrf':session['csrf'],'version':VERSION})
        if path=='/api/auth/logout' and method=='POST':self.app.auth.sessions.pop(sid,None);return self.output({'ok':True},cookie='oj_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
        if path=='/api/auth/password' and method=='POST':
            body=self.json_body();self.app.auth.change_password(session,body.get('old',''),body.get('password',''));self.app.audit(user,'password-change');return self.output({'ok':True},cookie='oj_session=; Path=/; Max-Age=0')
        if path=='/api/system' and method=='GET':return self.output(self.app.monitor.snapshot())
        if path=='/api/services' and method=='GET':return self.output(self.app.monitor.services())
        if path=='/api/runtime' and method=='GET':return self.output(self.app.catalog.runtime())
        if path=='/api/features' and method=='GET':return self.output(self.app.catalog.features())
        if path=='/api/plugins' and method=='GET':return self.output(self.app.catalog.list())
        if path=='/api/plugin' and method=='GET':
            pid=arg('id');item=next((p for p in self.app.catalog.list() if p['id']==pid),None)
            if not item:raise Error('插件不存在',404)
            item['readme']=self.app.catalog.readme(pid);item['configs']=[config_summary(c) for c in self.app.catalog.configs(pid)];return self.output(item)
        if path=='/api/icon' and method=='GET':
            root=self.app.catalog.plugin(arg('plugin'))
            p=next((root/name for name in ['resources/icon.png','resources/icon.svg'] if (root/name).is_file() and not (root/name).is_symlink()),None)
            if not p:raise Error('图标不存在',404)
            raw=p.read_bytes();self.send_response(200);self.headers_base(mimetypes.guess_type(p.name)[0]);self.send_header('Content-Length',str(len(raw)));self.end_headers();return self.wfile.write(raw)
        if path=='/api/configs' and method=='GET':return self.output([config_summary(c) for c in self.app.catalog.configs(arg('plugin'))])
        if path=='/api/config' and method=='GET':
            result=self.app.catalog.config(arg('plugin'),arg('id'))
            result['readonly']=result['readonly'] or result.get('ownerOnly',False) and role!='owner'
            return self.output(result)
        if path=='/api/config' and method=='PUT':
            self.app.auth.require(session)
            if self.app.catalog.entry(arg('plugin'),arg('id')).get('ownerOnly',False):self.app.auth.require(session,('owner',))
            if arg('plugin')=='OrangeJuice-Plugin' or arg('plugin')=='framework' and arg('id') in ('other.yaml','server.yaml','redis.yaml','db.yaml'):self.app.auth.require(session,('owner',))
            body=self.json_body();result=self.app.catalog.save(arg('plugin'),arg('id'),body.get('value'),body.get('revision'));self.app.audit(user,'config-save',arg('plugin')+'/'+arg('id'));return self.output(result)
        if path=='/api/backups' and method=='GET':self.app.auth.require(session);return self.output(self.app.catalog.backup_list())
        if path=='/api/backups/restore' and method=='POST':
            self.app.auth.require(session,('owner',));body=self.json_body();result=self.app.catalog.restore(body.get('id',''),body.get('revision'));self.app.audit(user,'config-restore',body.get('id',''));return self.output(result)
        if path=='/api/audit' and method=='GET':self.app.auth.require(session);return self.output(self.app.activities())
        if path=='/api/users':
            self.app.auth.require(session,('owner',))
            if method=='GET':return self.output(self.app.auth.public_users())
            if method=='POST':
                body=self.json_body();self.app.auth.user_update(session,body);self.app.audit(user,'account-save',body.get('username',''));return self.output({'ok':True})
            if method=='DELETE':
                name=self.json_body().get('username','');self.app.auth.user_delete(session,name);self.app.audit(user,'account-delete',name);return self.output({'ok':True})
        if path=='/api/actions' and method=='GET':return self.output([{k:v for k,v in a.items() if k in ('id','label','description')} for a in self.app.settings.get('actions',[])])
        if path=='/api/action' and method=='POST':
            self.app.auth.require(session,('owner',));name=self.json_body().get('id','');result=self.app.action(name);self.app.audit(user,'service-action',name);return self.output(result)
        if path=='/api/external/open' and method=='POST':
            self.app.auth.require(session,('owner',));name=self.json_body().get('id','')
            panel=next((p for p in self.app.settings.get('externalPanels',[]) if p.get('id')==name),None)
            if not panel:raise Error('管理入口不存在',404)
            url=panel.get('url','')
            if panel.get('command'):
                result=subprocess.run(panel['command'],capture_output=True,text=True,timeout=15,shell=False)
                if result.returncode:raise Error('暂时无法生成登录入口',502)
                url=result.stdout.strip()
            parsed_url=urllib.parse.urlsplit(url)
            if parsed_url.scheme not in ('http','https') or parsed_url.hostname not in ('127.0.0.1','localhost'):raise Error('管理入口地址不在允许范围内',403)
            return self.output({'url':url})
        if path.startswith('/api/plugins/') and method=='POST':
            self.app.auth.require(session,('owner',));action=path.rsplit('/',1)[-1];body=self.json_body();result=self.app.catalog.mutate_plugin(action,body);self.app.audit(user,'plugin-'+action,body.get('plugin',body.get('name','')));return self.output(result)
        if path=='/api/settings' and method=='GET':
            return self.output({'name':'OrangeJuice-Plugin','version':VERSION,'framework':self.app.settings.get('frameworkName','通用文件适配器'),'externalPanels':[{k:v for k,v in p.items() if k in ('id','title','url')} for p in self.app.settings.get('externalPanels',[])],'readonlyPlugins':self.app.settings.get('readonlyPlugins',[]),'credits':[{'name':'Guoba-Plugin','url':'https://github.com/guoba-yunzai/guoba-plugin','use':'管理流程与接口研究参考；未复制代码和界面素材'},{'name':'TRSS-Yunzai','url':'https://github.com/TimeRainStarSky/Yunzai','use':'可选机器人适配器运行环境'},{'name':'ChatGPT-Plugin','url':'https://github.com/ikechan8370/chatgpt-plugin','use':'现有 AI 面板独立入口与只读配置'},{'name':'psutil','url':'https://github.com/giampaolo/psutil','use':'跨平台系统状态采集'},{'name':'PyYAML','url':'https://github.com/yaml/pyyaml','use':'YAML 配置解析'}]})
        raise Error('接口不存在',404)

def serve(settings,data):
    app=App(settings,data);server=http.server.ThreadingHTTPServer((settings.get('host','127.0.0.1'),int(settings.get('port',15082))),Handler);server.app=app;server.daemon_threads=True
    ipc=Path(settings.get('bridgeDirectory',app.data/'bridge'));ipc.mkdir(parents=True,exist_ok=True)
    key=ipc/'bridge.key'
    if not key.exists():key.write_text(app.auth.bridge_key,encoding='ascii');os.chmod(key,0o600)
    elif key.read_text(encoding='utf-8').strip()!=app.auth.bridge_key:raise RuntimeError('Bridge key mismatch')
    # File IPC allows a Docker bot to connect without opening a host network port.
    requests=ipc/'requests';responses=ipc/'responses';requests.mkdir(exist_ok=True);responses.mkdir(exist_ok=True)
    def worker():
        while not getattr(server,'stopping',False):
            for p in list(requests.glob('*.json'))[:20]:
                try:
                    if p.is_symlink() or p.stat().st_size>4096:p.unlink();continue
                    req=json.loads(p.read_text(encoding='utf-8'));payload=req.get('payload',{});raw=json.dumps(payload,separators=(',',':')).encode();stamp=str(req.get('time',''))
                    expected=hmac.new(app.auth.bridge_key.encode(),(stamp+'\n'+hashlib.sha256(raw).hexdigest()).encode(),hashlib.sha256).hexdigest()
                    if abs(time.time()-float(stamp))>30 or not hmac.compare_digest(req.get('signature',''),expected):continue
                    if payload.get('action')=='ticket':atomic(responses/p.name,{'ticket':app.auth.ticket(),'expires':time.time()+180})
                except (OSError,ValueError,TypeError):pass
                finally:p.unlink(missing_ok=True)
            for p in responses.glob('*.json'):
                try:
                    if time.time()-p.stat().st_mtime>180:p.unlink(missing_ok=True)
                except FileNotFoundError:pass
            time.sleep(0.3)
    threading.Thread(target=worker,daemon=True).start();print('OrangeJuice-Plugin ready; '+str(server.server_address),flush=True)
    server.serve_forever()

def cli():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['serve','ticket','diagnose']);parser.add_argument('--config',default='config/local.json');parser.add_argument('--data',default='data');args=parser.parse_args()
    settings=json.loads(Path(args.config).read_text(encoding='utf-8'));data=Path(args.data).resolve()
    if args.action=='serve':return serve(settings,data)
    if args.action=='diagnose':return print(json.dumps({'python':sys.version.split()[0],'yaml':True,'psutil':True,'pluginsDirectoryExists':Path(settings.get('pluginsDirectory','plugins')).is_dir(),'webAssets':(WEB/'index.html').exists()}))
    key=(data/'bridge.key').read_text(encoding='utf-8').strip();raw=b'{}';stamp=str(time.time());signature=hmac.new(key.encode(),(stamp+'\n'+hashlib.sha256(raw).hexdigest()).encode(),hashlib.sha256).hexdigest()
    request=urllib.request.Request('http://127.0.0.1:'+str(settings.get('port',15082))+'/api/internal/ticket',data=raw,headers={'Content-Type':'application/json','X-OJ-Time':stamp,'X-OJ-Signature':signature})
    with urllib.request.urlopen(request,timeout=10) as r:ticket=json.load(r)['ticket']
    print(settings.get('publicUrl','http://127.0.0.1:'+str(settings.get('port',15082))).rstrip('/')+'/#/login?ticket='+ticket)

if __name__=='__main__':cli()
