import test from 'node:test'
import assert from 'node:assert/strict'
import {rewriteCommand,configurationPayload} from '../integrations/yunzai/command-aliases.mjs'
test('aliases rewrite exactly once, preserve parameters, and do not match ordinary text',()=>{
 const aliases=[{alias:'/查天气',target:'#搜索'},{alias:'#搜索',target:'#AI'}]
 assert.equal(rewriteCommand('/查天气 北京天气',aliases),'#搜索 北京天气')
 assert.equal(rewriteCommand('/查天气abc',aliases),'/查天气abc')
 assert.equal(rewriteCommand('你好',aliases),'你好')
 assert.equal(rewriteCommand('#搜索 北京',[]),'#搜索 北京')
})
test('configuration parser preserves spaces and JSON while requiring revisions',()=>{
 assert.deepEqual(configurationPayload('#橙汁配置 AI 角色提示词'),{action:'config-list',plugin:'AI',query:'角色提示词'})
 const p=configurationPayload('/橙汁设置 AI abcdef012345 @abcdef0123456789 "你是 开拓者"')
 assert.equal(p.value,'"你是 开拓者"');assert.equal(p.revision,'abcdef0123456789')
 assert.throws(()=>configurationPayload('#橙汁设置 AI abcdef012345 20'),/先发送/)
 assert.equal(configurationPayload('普通聊天'),null)
 assert.deepEqual(configurationPayload('#橙汁功能 欢迎新人 关'),{action:'function-control',name:'欢迎新人',enabled:false})
})
