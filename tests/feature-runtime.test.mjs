import test from 'node:test';
import assert from 'node:assert/strict';
import {featureSnapshot} from '../integrations/yunzai/feature-runtime.mjs';

test('reads registered notices, commands, tasks and initialization modules without calling plugins', () => {
  const task={name:'自动任务',cron:'0 * * * *',job:{}};
  const command={name:'系统',event:'message',rule:[{reg:/^#系统$/,fnc:'status',permission:'master'}],apiKey:'private-secret',accept(){throw Error('must not execute')}};
  const loader={pluginCountMap:new Map([['example/进群退群通知.js',2],['ServerStatus-Plugin',1],['adapter/OneBotv11.js',1]]),priority:[
    {key:'example/进群退群通知.js',plugin:{name:'欢迎新人',dsc:'新人入群欢迎',event:'notice.group.increase'},priority:5000},
    {key:'example/进群退群通知.js',plugin:{name:'退群通知',event:'notice.group.decrease'}},
    {key:'ServerStatus-Plugin',plugin:command,class:class Forbidden {constructor(){throw Error('must not instantiate')}}}
  ],task:[task],taskMap:new Map([['ServerStatus-Plugin',new Set([task])]])};
  const result=featureSnapshot(loader);
  assert.equal(result.features.length,5);
  assert.equal(result.features[0].origin,'framework');
  assert.equal(result.features[0].kind,'notice');
  assert.equal(result.features[2].source,'ServerStatus-Plugin/index.js');
  assert.deepEqual(result.features[2].rules,[{pattern:'^#系统$',flags:'',handler:'status',permission:'master',event:'message'}]);
  assert.equal(result.features[3].scheduled,true);
  assert.equal(result.features[3].source,'ServerStatus-Plugin/index.js');
  assert.equal(result.features[4].kind,'module');
  assert.equal(result.files[0].featureCount,2);
  assert.ok(!JSON.stringify(result).includes('private-secret'));
});
test('bounds inventories and rejects absolute or traversing source paths', () => {
  const result=featureSnapshot({priority:Array.from({length:2100},(_,index)=>({key:index?'example/test.js':'/opt/private/config.js',plugin:{name:'Entry'+index,rule:[]}}))});
  assert.equal(result.truncated,true);
  assert.ok(result.features.length<=2000);
  assert.equal(result.features[0].source,'');
  assert.ok(!JSON.stringify(result).includes('/opt/private'));
  assert.equal(featureSnapshot({priority:[{key:'../secret',plugin:{rule:[null]}}]}).features[0].source,'');
  assert.deepEqual(featureSnapshot(),{schemaVersion:1,features:[],files:[],truncated:false});
});
