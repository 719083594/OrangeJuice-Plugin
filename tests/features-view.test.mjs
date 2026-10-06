import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const context=vm.createContext({});
vm.runInContext(fs.readFileSync(new URL('../web/features-view.js',import.meta.url),'utf8'),context);
const view=context.OrangeJuiceFeatures;
const report={items:[{id:'0',name:'欢迎新人',description:'新人入群欢迎',source:'example/welcome.js',origin:'framework',kind:'notice',event:'notice.group.increase',rules:[],priority:null,defaultState:'enabled'},
  {id:'1',name:'外部搜索',source:'WebSearch-Plugin/index.js',origin:'extension',kind:'command',rules:[{pattern:'<script>alert(1)</script>',handler:'search',permission:'all'}],defaultState:'unknown'}],files:[],duplicates:[],broadEntries:[]};
test('defaults to all functions and searches by event or source',()=>{
  assert.equal(view.filter(report).length,2);
  assert.equal(view.filter(report,{origin:'framework'}).length,1);
  assert.equal(view.filter(report,{origin:'all'}).length,2);
  assert.equal(view.filter(report,{query:'notice.group.increase'}).length,1);
  assert.equal(view.filter(report,{query:'WebSearch',origin:'all'}).length,1);
  assert.equal(view.filter(report,{overlapOnly:true}).length,0);
});
test('groups builtin sources together and shows configuration and per-rule explanations',()=>{
 const richer={...report,pluginGroups:[{id:'framework',title:'内置插件',origin:'framework',configs:[{id:'other.yaml',plugin:'framework',title:'访问控制',fields:[{path:'autoFriend',label:'自动同意好友'}]}]},{id:'WebSearch-Plugin',title:'联网搜索',origin:'extension',configs:[]}],items:report.items.map(x=>({...x,pluginId:x.origin==='framework'?'framework':'WebSearch-Plugin',operations:[{title:'实际用途',command:'#指令 参数',description:'内部权限检查'}]}))};
 const html=view.rows(richer);
 assert.ok(html.includes('内置插件')&&html.includes('我的插件'));
 assert.ok(!html.includes('<code>autoFriend</code>')&&html.includes('自动同意好友'));
 assert.ok(html.includes('实际用途')&&html.includes('#指令 参数'));
 assert.ok(html.includes('data-feature-plugin="framework"'));
 assert.ok(!view.rows(richer,{plugin:'framework'}).includes('外部搜索'));
});
test('escapes command metadata and shows notices even without command regex',()=>{
  const html=view.rows(report,{origin:'all'});
  assert.ok(html.includes('欢迎新人'));
  assert.ok(html.includes('notice.group.increase'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('状态未提供'));
});
test('overlap explanation includes evidence and human function names',()=>{
  const duplicated={...report,duplicates:[{label:'同名功能',evidence:'^#系统$',ids:['0','1']}]};
  assert.equal(view.filter(duplicated,{origin:'all',overlapOnly:true}).length,2);
  const html=view.duplicates(duplicated);
  assert.ok(html.includes('欢迎新人')&&html.includes('外部搜索')&&!html.includes('example/welcome.js'));
  assert.ok(html.includes('不代表一定重复回复'));
});
