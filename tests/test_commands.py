import json,tempfile,time,unittest
from pathlib import Path
from orangejuice.catalog import Catalog,MASK
from orangejuice.commands import options,run,function_control
from orangejuice.auth import Error

class CommandsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);p=self.root/'plugins/AI-Plugin';(p/'config').mkdir(parents=True)
  self.file=p/'config/settings.json';self.file.write_text(json.dumps({'enabled':True,'timeout':10,'apiKey':'private-command-fixture','nested':{'count':2,'planned':False},'presets':[{'id':'one','name':'星','prompt':'before'},{'id':'two','name':'流萤','prompt':'other'}]}))
  (p/'orangejuice.plugin.json').write_text(json.dumps({'title':'AI-Plugin','configs':[{'id':'settings','file':'config/settings.json','reload':'live','fields':[{'path':'timeout','label':'等待上限','type':'integer','min':1,'max':30},{'path':'nested.planned','status':'planned'},{'path':'presets.*.prompt','label':'角色提示词','type':'string'}]}]}))
  (self.root/'config/config').mkdir(parents=True);self.group=self.root/'config/config/group.yaml';self.group.write_text('default:\n  enable: []\n  disable: []\nfixture:\n  disable: [欢迎新人]\n123456:\n  groupCD: 500\n',encoding='utf-8')
  runtime=self.root/'runtime.json';runtime.write_text(json.dumps({'timestamp':time.time(),'featureInventory':{'schemaVersion':1,'features':[{'name':'欢迎新人','source':'example/进群退群通知.js','origin':'framework','kind':'notice','event':'notice.group.increase'},{'name':'连接','source':'adapter/demo.js','origin':'framework','kind':'module'}]}}))
  self.catalog=Catalog({'pluginsDirectory':str(self.root/'plugins'),'frameworkRoot':str(self.root),'runtimeFile':str(runtime)},self.root/'data')
 def tearDown(self):self.tmp.cleanup()
 def setting(self,path,value,revision=None):
  row=next(r for r in options(self.catalog,'AI-Plugin') if r['path']==path)
  return run(self.catalog,{'action':'config-set','plugin':'AI','option':row['id'],'revision':revision or row['revision'][:16],'value':value})
 def test_query_and_save_share_validation_mask_and_backups(self):
  text=run(self.catalog,{'action':'config-list','plugin':'AI','query':'等待上限'})['text'];self.assertIn('等待上限',text);self.assertNotIn('private-command-fixture',text)
  before=self.catalog.config('AI-Plugin','settings')['revision'];self.setting(['timeout'],'20')
  self.assertEqual(json.loads(self.file.read_text())['timeout'],20);self.assertEqual(json.loads(self.file.read_text())['apiKey'],'private-command-fixture');self.assertEqual(len(self.catalog.backup_list()),1)
  with self.assertRaises(Error):self.setting(['timeout'],'31')
  with self.assertRaises(Error):self.setting(['timeout'],'"text"')
  with self.assertRaises(Error):self.setting(['timeout'],'21',before[:16])
  self.setting(['enabled'],'关');self.assertIs(json.loads(self.file.read_text())['enabled'],False)
 def test_planned_and_parent_edits_are_blocked_and_array_versions_protect_roles(self):
  with self.assertRaises(Error):self.setting(['nested','planned'],'true')
  with self.assertRaises(Error):self.setting(['nested'],'{"count":3,"planned":true}')
  before=self.catalog.config('AI-Plugin','settings')['revision'];self.setting(['presets'],'[{"id":"two","name":"流萤","prompt":"other"},{"id":"one","name":"星","prompt":"before"}]')
  with self.assertRaises(Error):self.setting(['presets',0,'prompt'],'wrong',before[:16])
  self.assertEqual(json.loads(self.file.read_text())['presets'][0]['prompt'],'other')
 def test_virtual_builtin_and_function_controls_preserve_group_overrides(self):
  plugins=self.catalog.list();self.assertEqual(len([x for x in plugins if x['builtin']]),1)
  self.assertEqual(next(x for x in plugins if x['builtin'])['title'],'内置插件')
  function_control(self.catalog,{'name':'欢迎新人','enabled':False});self.assertEqual(self.catalog.features()['items'][0]['defaultState'],'disabled')
  function_control(self.catalog,{'name':'欢迎新人','enabled':True});value=self.catalog.config('framework','group.yaml')['value'];self.assertEqual(value['fixture']['disable'],['欢迎新人']);self.assertEqual(value['default']['disable'],[])
  self.assertEqual(value['123456']['groupCD'],500)
  self.assertTrue(any(row['path']==['123456','groupCD'] for row in options(self.catalog,'framework')))
  with self.assertRaises(Error):function_control(self.catalog,{'name':'连接','enabled':False})
 def test_private_service_declarations_are_projected_and_capability_mapping_survives(self):
  p=self.root/'plugins/OrangeJuice-Plugin';p.mkdir();(p/'orangejuice.plugin.json').write_text('{"configs":[]}')
  service=self.root/'platform.json';service.write_text(json.dumps({'port':15082,'extraConfigs':[{'fields':[{'path':'private'}]}],'actions':[]}))
  self.catalog.settings.update({'_settingsFile':str(service),'extraConfigs':[{'plugin':'OrangeJuice-Plugin','id':'service','path':str(service)}]})
  self.assertEqual([x['id'] for x in self.catalog.configs('OrangeJuice-Plugin')],['platform'])
  self.assertNotIn('extraConfigs',self.catalog.config('OrangeJuice-Plugin','platform')['value'])
  manifest=self.root/'plugins/AI-Plugin/orangejuice.plugin.json';m=json.loads(manifest.read_text());m['capabilities']=[{'title':'角色','status':'implemented','configPaths':['presets']}];manifest.write_text(json.dumps(m))
  self.assertEqual(next(x for x in self.catalog.list() if x['id']=='AI-Plugin')['capabilities'][0]['configPaths'],['presets'])
 def test_ambiguous_yaml_keys_are_rejected_without_data_loss(self):
  self.group.write_text('123456: {groupCD: 500}\n"123456": {groupCD: 1000}\n',encoding='utf-8')
  with self.assertRaises(Error):self.catalog.config('framework','group.yaml')

if __name__=='__main__':unittest.main()
