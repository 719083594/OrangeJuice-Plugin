import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import {webcrypto} from 'node:crypto'
import test from 'node:test'

const context=vm.createContext({structuredClone,crypto:webcrypto})
vm.runInContext(fs.readFileSync(new URL('../web/config-form.js',import.meta.url),'utf8'),context)
const form=context.OrangeJuiceConfigForm
const fields=[
  {path:'basic',label:'基础与命令',type:'object'},
  {path:'channels',label:'模型渠道',type:'array',itemDefaults:{id:'',name:'新渠道',apiKey:'',maxTokens:1024}},
  {path:'channels.*.id',label:'渠道标识',type:'string'},
  {path:'channels.*.name',label:'渠道名称',type:'string'},
  {path:'channels.*.apiKey',label:'接口密钥',type:'string',secret:true},
  {path:'channels.*.maxTokens',label:'最多输出 Token',type:'integer'},
  {path:'presets.*.prompt',label:'角色提示词',type:'string',multiline:true},
  {path:'chat.reasoningEffort',label:'思考强度',enum:['low','high'],enumLabels:{low:'较低',high:'较高'}}
]

test('common fields, nested sections and channel fields use Chinese labels',()=>{
  const html=form.renderTree({publicUrl:'http://127.0.0.1:15082',frameworkName:'通用应用',basic:{enabled:true},channels:[{id:'first',name:'默认',apiKey:'••••••••',maxTokens:1024}],presets:[{prompt:'<script>private fixture</script>'}],chat:{reasoningEffort:'low'}},[],false,fields)
  for(const label of ['管理面板访问地址','应用或框架名称','基础与命令','渠道名称','接口密钥','角色提示词','较低'])assert(html.includes(label))
  assert(html.includes('type="password"'))
  assert(!html.includes('channels.0.apiKey'));assert(html.includes(encodeURIComponent(JSON.stringify(['channels',0,'apiKey']))))
  assert(!html.includes('<script>private fixture</script>'))
  assert(html.includes('data-type="string" rows="4"'))
})

test('empty channel arrays expose a form entry and additions have stable independent IDs',()=>{
  const html=form.renderTree({channels:[]},[],false,fields)
  assert(html.includes('添加一项'))
  const first=form.arrayItem(['channels'],fields),second=form.arrayItem(['channels'],fields)
  assert.match(first.id,/^[a-f0-9-]{36}$/)
  assert.notEqual(first.id,second.id)
  first.name='changed'
  assert.equal(second.name,'新渠道')
  assert.equal(second.apiKey,'')
})

test('HTTP browser contexts can add channels without crypto.randomUUID',()=>{
  const fallback=vm.createContext({structuredClone,crypto:{getRandomValues:value=>webcrypto.getRandomValues(value)}})
  vm.runInContext(fs.readFileSync(new URL('../web/config-form.js',import.meta.url),'utf8'),fallback)
  const item=fallback.OrangeJuiceConfigForm.arrayItem(['channels'],fields)
  assert.match(item.id,/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/)
})

test('editing nested array leaves keeps unknown fields and masked secrets intact',()=>{
  const original={channels:[{id:'first',name:'before',apiKey:'••••••••',maxTokens:1024,unknown:{keep:true}}],enabled:true}
  const element=(path,type,value,checked=false)=>({dataset:{path:encodeURIComponent(JSON.stringify(path)),type},tagName:'INPUT',value,checked})
  const edited=form.readFields(original,[element(['channels',0,'name'],'string','after'),element(['channels',0,'maxTokens'],'number','2048'),element(['enabled'],'boolean','',false)])
  assert.equal(edited.channels[0].name,'after')
  assert.equal(edited.channels[0].maxTokens,2048)
  assert.equal(edited.channels[0].apiKey,'••••••••')
  assert.equal(edited.channels[0].unknown.keep,true)
  assert.equal(original.channels[0].name,'before')
  assert.equal(edited.enabled,false)
})

test('readonly arrays cannot add, remove or edit and invalid paths are rejected',()=>{
  const html=form.renderTree({channels:[{id:'first',apiKey:'••••••••'}]},[],true,fields)
  assert.match(html,/data-array-add="[^"]+" disabled/)
  assert.match(html,/data-array-remove="[^"]+" data-array-index="0" disabled/)
  assert(!html.includes('private-fixture'))
  assert.throws(()=>form.readFields({},[{dataset:{path:encodeURIComponent(JSON.stringify(['__proto__','key'])),type:'string'},value:'bad'}]),/路径无效/)
})

test('planned features display their status instead of a nonfunctional switch',()=>{
  const html=form.renderTree({memory:{autoExtract:false},extensions:{mcp:[]}},[],false,[{path:'memory.autoExtract',label:'自动提取记忆',status:'planned'},{path:'extensions.mcp',label:'MCP 工具',status:'planned'}])
  assert(html.includes('自动提取记忆'))
  assert(html.includes('当前版本未实现'))
  assert(!html.includes('type="checkbox"'))
  assert(!html.includes('data-array-add'))
  assert(!html.includes('config-field'))
})

test('extra configuration field declarations have Chinese labels and retain editable schema keys',()=>{
  const original={extraConfigs:[{id:'sample',path:'settings.json',fields:[{path:'wait',type:'integer',min:1,max:30,required:true,default:5}],ownerOnly:true}]}
  const html=form.renderTree(original)
  for(const label of ['额外配置文件','字段定义','数据类型','最小值','最大值','必填','默认值','仅主人可编辑'])assert(html.includes(label),label)
  for(const key of ['extraConfigs.0.fields.0.type','extraConfigs.0.fields.0.min','extraConfigs.0.fields.0.max'])assert(!html.includes(key),key)
  const edited=form.readFields(original,[{dataset:{path:encodeURIComponent(JSON.stringify(['extraConfigs',0,'fields',0,'min'])),type:'number'},value:'2'}])
  assert.equal(edited.extraConfigs[0].fields[0].min,2)
  assert.equal(edited.extraConfigs[0].fields[0].type,'integer')
  assert.equal(original.extraConfigs[0].fields[0].min,1)
})

test('all current public framework sample keys render Chinese headings while preserving original keys',()=>{
  // Key-only inventory from the framework's public default samples; no instance values.
  const sampleKeys={
    bot:['cache_group_member','chromium_path','file_to_url_time','file_to_url_times','file_watch','log_align','log_length','log_level','log_object','msg_type_count','online_msg_exp','plugin_load_timeout','proxyAddress','puppeteer_timeout','puppeteer_ws','restart_cron','restart_time','start_cron','stop_cron','update_cron','update_time'],
    db:['dialect','logging','storage'],
    group:['addAt','addLimit','addPrivate','addRecall','addReply','botAlias','default','disable','enable','groupCD','onlyReplyAt','singleCD'],
    milky:['access_token','connection','enable','heartbeat','host','http_timeout','path','port','prefix','reconnect_interval','webhook','ws'],
    other:['autoFriend','autoGroup','autoQuit','blackGroup','blackUser','disableAdopt','disableMsg','disablePrivate','master','masterQQ','stdin','whiteGroup','whiteUser'],
    redis:['db','host','password','path','port','username'],
    renderer:['name'],
    satori:['enable','heartbeat_interval','http_endpoint','platform','timeout','token','ws_endpoint'],
    server:['auth','https','port','redirect','url']
  }
  for(const [filename,keys] of Object.entries(sampleKeys)){
    const html=form.renderTree(Object.fromEntries(keys.map(key=>[key,'fixture'])))
    for(const key of keys){
      const label=form.labels[key]
      assert.match(label||'',/[\u3400-\u9fff]/,filename+':'+key)
      assert(html.includes('aria-label="'+label+'"'),filename+':'+key)
      assert(!html.includes('<small>'+key+'</small>'),filename+':'+key);assert(html.includes(encodeURIComponent(JSON.stringify([key]))))
    }
  }
  const nested=form.renderTree({webhook:{http_timeout:1}})
  assert(nested.includes('<h3>Webhook 事件接收</h3>'));assert(!nested.includes('<small class="subtext">webhook</small>'))
  assert.equal(form.labels.update_time,'自动更新时间')
  assert.equal(form.labels.online_msg_exp,'上线通知冷却时间')
  assert.equal(form.labels.groupCD,'群指令冷却时间（毫秒）')
})

test('framework filenames receive Chinese titles without overriding declared plugin titles',()=>{
  assert.equal(form.configTitle({id:'bot.yaml',title:'bot'},'framework'),'机器人与运行日志')
  assert.equal(form.configTitle({id:'db.json',title:'db'},'framework'),'数据库')
  assert.equal(form.configTitle({id:'group.yml',title:'group'},'framework'),'群聊与回复')
  assert.equal(form.configTitle({id:'bot.yaml',title:'自定义应用设置'},'framework'),'自定义应用设置')
  assert.equal(form.configTitle({id:'bot.yaml',title:'bot'},'custom-plugin'),'bot')
  assert.equal(form.configTitle({id:'custom.yaml',title:'custom'},'framework'),'custom')
})
