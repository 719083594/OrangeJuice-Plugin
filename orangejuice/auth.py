import hashlib,hmac,json,os,secrets,time,threading
from pathlib import Path

class Error(Exception):
    def __init__(self,message,status=400): super().__init__(message);self.status=status

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        os.chmod(tmp,0o600);json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def password_hash(password,salt):
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

class Auth:
    def __init__(self,directory,clock=time.time):
        self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True);self.path=self.root/'accounts.json';self.clock=clock
        self.lock=threading.RLock();self.sessions={};self.tickets={};self.attempts={};self.codes={}
        if not self.path.exists():
            password=secrets.token_urlsafe(20);salt=secrets.token_hex(16)
            atomic(self.path,{'owner':{'role':'owner','salt':salt,'hash':password_hash(password,salt),'created':clock()}})
            bootstrap=self.root/'bootstrap.txt';bootstrap.write_text('username: owner\npassword: '+password+'\n',encoding='utf-8');os.chmod(bootstrap,0o600)
        key=self.root/'bridge.key'
        if not key.exists():key.write_text(secrets.token_urlsafe(32),encoding='ascii');os.chmod(key,0o600)
        self.bridge_key=key.read_text(encoding='utf-8').strip()
    def accounts(self):return json.loads(self.path.read_text(encoding='utf-8'))
    def public_users(self):return [{'username':k,'role':v['role'],'created':v.get('created')} for k,v in self.accounts().items()]
    def clean(self):
        now=self.clock()
        for store in (self.sessions,self.tickets,self.codes):
            for key in list(store):
                if store[key]['expires']<now:store.pop(key,None)
        for key in list(self.attempts):
            if now-self.attempts[key]['at']>900:self.attempts.pop(key,None)
    def rate(self,peer):
        self.clean();item=self.attempts.get(peer)
        if item and item['count']>=8:raise Error('登录尝试过多，请稍后重试',429)
    def fail(self,peer):
        item=self.attempts.setdefault(peer,{'at':self.clock(),'count':0});item['count']+=1
    def session(self,username):
        self.clean();user=self.accounts().get(username)
        if not user:raise Error('账号不可用',401)
        sid=secrets.token_urlsafe(32);value={'username':username,'role':user['role'],'csrf':secrets.token_urlsafe(24),'expires':self.clock()+43200}
        self.sessions[sid]=value
        return sid,value
    def login(self,username,password,peer):
        with self.lock:
            self.rate(peer);user=self.accounts().get(username);salt=user['salt'] if user else '00'*16
            digest=password_hash(str(password)[:1024],salt)
            if not user or not hmac.compare_digest(digest,user['hash']):self.fail(peer);raise Error('账号或密码错误',401)
            self.attempts.pop(peer,None);(self.root/'bootstrap.txt').unlink(missing_ok=True)
            return self.session(username)
    def ticket(self,username=None,ttl=180):
        with self.lock:
            self.clean()
            if username is None:username=next((k for k,v in self.accounts().items() if v['role']=='owner'),None)
            if username not in self.accounts():raise Error('账号不存在')
            ticket=secrets.token_urlsafe(32);self.tickets[ticket]={'username':username,'expires':self.clock()+min(300,ttl)};return ticket
    def consume(self,ticket,peer,kind='ticket'):
        with self.lock:
            self.rate(peer);store=self.codes if kind=='code' else self.tickets;item=store.pop(str(ticket),None)
            if not item or item['expires']<self.clock():self.fail(peer);raise Error('登录凭据错误或已失效',401)
            self.attempts.pop(peer,None);return self.session(item['username'])
    def code(self,peer):
        with self.lock:
            self.rate(peer)
            if self.codes:raise Error('已有有效验证码，请查看服务控制台',429)
            owner=next((k for k,v in self.accounts().items() if v['role']=='owner'),None)
            if owner is None:raise Error('主人账号不可用',503)
            code=f'{secrets.randbelow(100000000):08d}';self.codes[code]={'username':owner,'expires':self.clock()+300};return code
    def get(self,sid):
        with self.lock:
            self.clean();session=self.sessions.get(sid)
            if not session:raise Error('请先登录',401)
            user=self.accounts().get(session['username'])
            if not user:raise Error('账号不可用',401)
            session['role']=user['role'];return dict(session)
    def require(self,session,roles=('owner','admin')):
        if session['role'] not in roles:raise Error('当前账号没有操作权限',403)
    def user_update(self,session,payload):
        self.require(session,('owner',));name=payload.get('username','')
        if not isinstance(name,str) or not name or len(name)>40 or not all(c.isalnum() or c in '_-' for c in name):raise Error('账号名称格式不正确')
        role=payload.get('role','viewer')
        if role not in ('owner','admin','viewer'):raise Error('无效角色')
        with self.lock:
            users=self.accounts();old=users.get(name)
            if old and old['role']=='owner' and role!='owner' and sum(v['role']=='owner' for v in users.values())<=1:raise Error('必须保留至少一个主人账号')
            password=payload.get('password')
            if not old or password:
                if not isinstance(password,str) or not 12<=len(password)<=256:raise Error('密码长度应为12至256个字符')
                salt=secrets.token_hex(16);old={'salt':salt,'hash':password_hash(password,salt),'created':self.clock()}
            users[name]={**old,'role':role};atomic(self.path,users)
            self.sessions={k:v for k,v in self.sessions.items() if v['username']!=name}
    def user_delete(self,session,name):
        self.require(session,('owner',))
        with self.lock:
            users=self.accounts()
            if name==session['username']:raise Error('不能删除当前账号')
            if name not in users:raise Error('账号不存在',404)
            if users[name]['role']=='owner' and sum(v['role']=='owner' for v in users.values())<=1:raise Error('不能删除最后一个主人')
            del users[name];atomic(self.path,users);self.sessions={k:v for k,v in self.sessions.items() if v['username']!=name}
    def change_password(self,session,old,new):
        with self.lock:
            user=self.accounts()[session['username']]
            if not hmac.compare_digest(password_hash(str(old),user['salt']),user['hash']):raise Error('原密码错误',403)
            if not isinstance(new,str) or not 12<=len(new)<=256:raise Error('新密码至少12个字符')
            users=self.accounts();salt=secrets.token_hex(16);users[session['username']].update(salt=salt,hash=password_hash(new,salt));atomic(self.path,users)
            self.sessions={k:v for k,v in self.sessions.items() if v['username']!=session['username']}
