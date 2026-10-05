import json,sys,tempfile,time,threading,unittest,urllib.request,urllib.error,http.cookies
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orangejuice.auth import Auth,Error
from orangejuice.catalog import Catalog,mask,MASK
from orangejuice.server import App,Handler
from http.server import ThreadingHTTPServer

class PlatformTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.plugins=self.root/'plugins';self.plugins.mkdir();p=self.plugins/'sample';(p/'config').mkdir(parents=True)
        (p/'config/settings.json').write_text(json.dumps({'enabled':True,'timeout':10,'apiKey':'private-fixture','nested':{'count':2},'items':['a']}))
        (p/'orangejuice.plugin.json').write_text(json.dumps({'title':'Sample','configs':[{'id':'settings','file':'config/settings.json','reload':'live','fields':[{'path':'timeout','type':'integer','min':1,'max':30}]}]}))
        (p/'README.md').write_text('<script>fixture</script>')
        self.settings={'pluginsDirectory':str(self.plugins),'frameworkRoot':str(self.root),'readonlyPlugins':['readonly'],'actions':[],'externalPanels':[]};self.app=App(self.settings,self.root/'data')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.app=self.app;self.server.daemon_threads=True;threading.Thread(target=self.server.serve_forever,daemon=True).start();self.url='http://127.0.0.1:'+str(self.server.server_port)
        sid,self.session=self.app.auth.session('owner');self.cookie='oj_session='+sid
    def tearDown(self):self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def call(self,path,method='GET',body=None,cookie=True,csrf=True,origin=None):
        headers={'Content-Type':'application/json'}
        if cookie:headers['Cookie']=self.cookie
        if csrf:headers['X-CSRF-Token']=self.session['csrf']
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r),dict(r.headers)
        except urllib.error.HTTPError as e:
            with e:return e.code,json.load(e),dict(e.headers)
    def test_authentication_and_csrf(self):
        self.assertEqual(self.call('/api/system',cookie=False)[0],401)
        self.assertEqual(self.call('/api/config?plugin=sample&id=settings','PUT',{'value':{},'revision':'x'},csrf=False)[0],403)
        self.assertEqual(self.call('/api/auth/login','POST',{'username':'owner','password':'x'},cookie=False,origin='https://other.example')[0],403)
        status,me,headers=self.call('/api/me');self.assertEqual(status,200);self.assertEqual(me['role'],'owner');self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
    def test_external_metadata_preserves_configuration_and_permissions(self):
        self.settings['pluginMetadata']={'sample':{'title':'External title','description':'External description','author':{'name':'Publisher'},'repository':'https://github.com/example/sample.git','configs':[{'file':'/private'}],'readonly':True}}
        item=next(x for x in self.app.catalog.list() if x['id']=='sample')
        self.assertEqual(item['title'],'External title');self.assertEqual(item['description'],'External description');self.assertEqual(item['author'],'Publisher');self.assertEqual(item['repository'],'https://github.com/example/sample');self.assertFalse(item['readonly']);self.assertEqual(item['configCount'],1)
        self.assertEqual(self.app.catalog.config('sample','settings')['value']['timeout'],10)
    def test_generic_framework_configuration_without_yunzai(self):
        directory=self.root/'settings';directory.mkdir()
        (directory/'application.json').write_text('{"enabled":true,"apiKey":"private-fixture"}')
        self.settings['frameworkConfigsDirectory']=str(directory)
        self.assertFalse((self.root/'lib/plugins/plugin.js').exists())
        entries=self.app.catalog.configs('framework')
        self.assertEqual([entry['id'] for entry in entries],['application.json'])
        config=self.app.catalog.config('framework','application.json')
        self.assertEqual(config['value']['apiKey'],MASK)
        config['value']['enabled']=False
        self.app.catalog.save('framework','application.json',config['value'],config['revision'])
        raw=json.loads((directory/'application.json').read_text())
        self.assertFalse(raw['enabled']);self.assertEqual(raw['apiKey'],'private-fixture')
        self.assertTrue(self.app.catalog.runtime()['stale'])
    def test_ticket_one_use_expiry_and_cookie(self):
        ticket=self.app.auth.ticket();status,result,headers=self.call('/api/auth/ticket','POST',{'ticket':ticket},cookie=False)
        self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie']);self.assertEqual(self.call('/api/auth/ticket','POST',{'ticket':ticket},cookie=False)[0],401)
        expired=self.app.auth.ticket();self.app.auth.tickets[expired]['expires']=0;self.assertEqual(self.call('/api/auth/ticket','POST',{'ticket':expired},cookie=False)[0],401)
    def test_password_rate_limit_and_roles(self):
        self.app.auth.user_update(self.session,{'username':'viewer','role':'viewer','password':'long-test-password'})
        sid,session=self.app.auth.login('viewer','long-test-password','test');self.cookie='oj_session='+sid;self.session=session
        self.assertEqual(self.call('/api/users')[0],403);self.assertEqual(self.call('/api/plugins/remove','POST',{'plugin':'sample'})[0],403);self.assertEqual(self.call('/api/plugins')[0],200)
        for i in range(8):
            with self.assertRaises(Error):self.app.auth.login('unknown','bad','limited')
        with self.assertRaises(Error) as e:self.app.auth.login('unknown','bad','limited')
        self.assertEqual(e.exception.status,429)
    def test_no_secret_exposure_mask_preservation(self):
        c=self.app.catalog.config('sample','settings');self.assertEqual(c['value']['apiKey'],MASK);c['value']['timeout']=11
        self.app.catalog.save('sample','settings',c['value'],c['revision']);raw=json.loads((self.plugins/'sample/config/settings.json').read_text(encoding='utf-8'));self.assertEqual(raw['apiKey'],'private-fixture');self.assertEqual(raw['nested']['count'],2)
        self.assertNotIn('private-fixture',json.dumps(self.app.activities()))
    def test_revision_conflict_range_validation_and_backups(self):
        c=self.app.catalog.config('sample','settings');c['value']['timeout']=31
        with self.assertRaises(Error):self.app.catalog.save('sample','settings',c['value'],c['revision'])
        c['value']['timeout']=15;self.app.catalog.save('sample','settings',c['value'],c['revision'])
        with self.assertRaises(Error) as e:self.app.catalog.save('sample','settings',c['value'],c['revision'])
        self.assertEqual(e.exception.status,409)
        backup=self.app.catalog.backup_list()[0];now=self.app.catalog.config('sample','settings');self.app.catalog.restore(backup['id'],now['revision']);self.assertEqual(self.app.catalog.config('sample','settings')['value']['timeout'],10)
    def test_readonly_plugin_and_path_boundaries(self):
        readonly=self.plugins/'readonly';readonly.mkdir();(readonly/'config.json').write_text('{"x":1}')
        c=self.app.catalog.config('readonly','file:config.json')
        with self.assertRaises(Error):self.app.catalog.save('readonly','file:config.json',{'x':2},c['revision'])
        self.assertEqual(self.call('/api/plugin?id=..')[0],404)
        self.assertEqual(self.call('/api/config?plugin=sample&id=../../accounts.json')[0],404)
        self.assertEqual(self.call('/api/plugins/install','POST',{'name':'evil','url':'https://github.com/a/b;touch /tmp/x'})[0],400)
        with self.assertRaises(Error):self.app.catalog.restore('../bad','x')
    def test_symlinks_and_reserved_fields(self):
        try:(self.plugins/'escape').symlink_to(self.root,target_is_directory=True)
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaises(Error):self.app.catalog.plugin('escape')
        c=self.app.catalog.config('sample','settings');c['value']['__proto__']={}
        with self.assertRaises(Error):self.app.catalog.save('sample','settings',c['value'],c['revision'])
    def test_yaml_types_and_discovery(self):
        p=self.plugins/'sample/config/new.yaml';p.write_text('enabled: true\ncount: 3\npassword: keepme\n',encoding='utf-8')
        c=self.app.catalog.config('sample','file:config/new.yaml');self.assertIs(c['value']['enabled'],True);self.assertEqual(c['value']['password'],MASK)
        c['value']['count']='wrong'
        with self.assertRaises(Error):self.app.catalog.save('sample','file:config/new.yaml',c['value'],c['revision'])
        self.assertEqual(self.app.catalog.list()[0]['title'],'Sample')
    def test_protected_actions_and_account_lifecycle(self):
        self.assertEqual(self.call('/api/action','POST',{'id':'not-enabled'})[0],403)
        self.assertEqual(self.call('/api/internal/ticket','POST',{},cookie=False)[0],403)
        with self.assertRaises(Error):self.app.auth.user_update(self.session,{'username':'owner','role':'viewer'})
        with self.assertRaises(Error):self.app.auth.user_delete(self.session,'owner')
        self.app.auth.user_update(self.session,{'username':'admin','role':'admin','password':'long-test-password'})
        sid,s=self.app.auth.session('admin');self.cookie='oj_session='+sid;self.session=s
        self.assertEqual(self.call('/api/plugins/remove','POST',{'plugin':'sample'})[0],403)
    def test_authenticated_system_and_readme_plain_text(self):
        status,s,_=self.call('/api/system');self.assertEqual(status,200);self.assertIn('memory',s);self.assertIn('disks',s)
        self.assertEqual(self.call('/api/plugin?id=sample')[1]['readme'],'<script>fixture</script>')
        self.assertEqual(self.call('/api/settings')[0],200)
    def test_http_password_change_logout_and_nonfinite(self):
        password=(self.root/'data/bootstrap.txt').read_text(encoding='utf-8').split('password: ')[1].strip()
        self.assertEqual(self.call('/api/auth/password','POST',{'old':password,'password':'new-long-test-password'})[0],200)
        self.assertEqual(self.call('/api/me')[0],401)
        sid,self.session=self.app.auth.login('owner','new-long-test-password','test');self.cookie='oj_session='+sid
        self.assertEqual(self.call('/api/auth/logout','POST',{})[0],200)
        self.assertEqual(self.call('/api/me')[0],401)
        sid,self.session=self.app.auth.session('owner');self.cookie='oj_session='+sid
        self.assertEqual(self.call('/api/config?plugin=sample&id=settings','PUT',{'value':{'timeout':float('nan')},'revision':'x'})[0],400)
    def test_owner_replacement_keeps_tickets_available(self):
        self.app.auth.user_update(self.session,{'username':'newowner','role':'owner','password':'long-test-password'})
        sid,s=self.app.auth.session('newowner');self.app.auth.user_delete(s,'owner')
        ticket=self.app.auth.ticket();self.assertEqual(self.app.auth.consume(ticket,'test')[1]['username'],'newowner')
        code=self.app.auth.code('console');self.assertEqual(self.app.auth.consume(code,'console','code')[1]['username'],'newowner')
    def create_ai_plugin(self):
        root=self.plugins/'AI-Plugin';(root/'config').mkdir(parents=True)
        value={'channels':[{'id':'first','name':'一','apiKey':'first-private-fixture','key':'alternate-private-fixture','maxTokens':1024},{'id':'second','name':'二','apiKey':'second-private-fixture','key':'second-alternate-fixture','maxTokens':2048}],'presets':[{'id':'default','prompt':'fixture prompt'}]}
        (root/'config/local.json').write_text(json.dumps(value),encoding='utf-8')
        manifest={'title':'AI-Plugin','managementPanel':'ai-plugin','capabilities':'capabilities.json','configs':[{'id':'settings','title':'AI 运行设置','file':'config/local.json','reload':'live','ownerOnly':True,'fields':[{'path':'channels.*.apiKey','label':'接口密钥','type':'string','secret':True},{'path':'channels.*.key','label':'备用密钥','type':'string','secret':True},{'path':'channels.*.maxTokens','label':'最多输出 Token','type':'integer','min':1,'max':8192}]}]}
        (root/'orangejuice.plugin.json').write_text(json.dumps(manifest),encoding='utf-8')
        (root/'capabilities.json').write_text(json.dumps({'capabilities':[{'id':'chat','title':'聊天','status':'implemented'},{'id':'workflow','title':'工作流','status':'planned'}]}),encoding='utf-8')
        return root,value
    def test_ai_native_registration_and_capabilities_are_not_editable_configs(self):
        root,_=self.create_ai_plugin()
        item=next(x for x in self.app.catalog.list() if x['id']=='AI-Plugin')
        self.assertTrue(item['native']);self.assertEqual(item['title'],'AI-Plugin');self.assertEqual(item['managementPanel'],'ai-plugin')
        self.assertEqual(item['configCount'],1);self.assertEqual(item['capabilities'][1]['status'],'planned')
        self.assertEqual(self.app.catalog.configs('AI-Plugin')[0]['id'],'settings')
    def test_ai_wildcard_secrets_survive_channel_deletion_and_reordering(self):
        root,original=self.create_ai_plugin()
        c=self.app.catalog.config('AI-Plugin','settings')
        for item in c['value']['channels']:
            self.assertEqual(item['apiKey'],MASK);self.assertEqual(item['key'],MASK)
        self.assertEqual(c['value']['channels'][0]['maxTokens'],1024)
        self.assertNotIn('private-fixture',json.dumps(c))
        c['value']['channels'].reverse();c['value']['channels'][0]['maxTokens']=4096
        self.app.catalog.save('AI-Plugin','settings',c['value'],c['revision'])
        raw=json.loads((root/'config/local.json').read_text(encoding='utf-8'))
        self.assertEqual(raw['channels'][0]['apiKey'],original['channels'][1]['apiKey'])
        self.assertEqual(raw['channels'][0]['key'],original['channels'][1]['key'])
        c=self.app.catalog.config('AI-Plugin','settings');c['value']['channels'].pop(0)
        self.app.catalog.save('AI-Plugin','settings',c['value'],c['revision'])
        raw=json.loads((root/'config/local.json').read_text(encoding='utf-8'))
        self.assertEqual(raw['channels'][0]['apiKey'],original['channels'][0]['apiKey'])
    def test_ai_wildcard_validation_and_duplicate_secret_ids_are_rejected(self):
        self.create_ai_plugin();c=self.app.catalog.config('AI-Plugin','settings')
        c['value']['channels'][1]['maxTokens']=9000
        with self.assertRaises(Error):self.app.catalog.save('AI-Plugin','settings',c['value'],c['revision'])
        c=self.app.catalog.config('AI-Plugin','settings');c['value']['channels'][0]['id']='new-channel'
        with self.assertRaises(Error):self.app.catalog.save('AI-Plugin','settings',c['value'],c['revision'])
        c=self.app.catalog.config('AI-Plugin','settings');c['value']['channels'][1]['id']='first'
        with self.assertRaises(Error):self.app.catalog.save('AI-Plugin','settings',c['value'],c['revision'])
    def test_ai_configuration_requires_owner_in_http_api(self):
        self.create_ai_plugin()
        self.app.auth.user_update(self.session,{'username':'admin','role':'admin','password':'long-test-password'})
        sid,self.session=self.app.auth.session('admin');self.cookie='oj_session='+sid
        status,c,_=self.call('/api/config?plugin=AI-Plugin&id=settings')
        self.assertEqual(status,200);self.assertTrue(c['readonly']);self.assertTrue(c['ownerOnly'])
        self.assertTrue(self.call('/api/configs?plugin=AI-Plugin')[1][0]['readonly'])
        self.assertTrue(self.call('/api/plugin?id=AI-Plugin')[1]['configs'][0]['readonly'])
        self.assertEqual(self.call('/api/config?plugin=AI-Plugin&id=settings','PUT',{'value':c['value'],'revision':c['revision']})[0],403)

if __name__=='__main__':unittest.main()
