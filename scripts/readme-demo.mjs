/** Isolated README preview: real web assets, fictional read-only API fixtures. */
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import {fileURLToPath} from 'node:url'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const port=Number(process.env.README_DEMO_PORT||48883)
const GiB=1024**3
const plugins=[
  {id:'welcome-demo',title:'迎新助手 · 示例',author:'示例开发者',version:'1.0.0',description:'欢迎语、入群提醒与群聊小贴士。所有内容均为虚构演示数据。',native:true,configCount:1,loaded:true,icon:false},
  {id:'notes-demo',title:'灵感笔记 · 示例',author:'示例开发者',version:'1.2.0',description:'收集灵感与待办，用清晰的配置管理每一份记录。',native:true,configCount:1,loaded:true,icon:false},
  {id:'weather-demo',title:'天气便笺 · 示例',author:'示例开发者',version:'0.8.0',description:'展示通用 JSON 配置接入，不连接任何天气服务。',native:false,configCount:1,loaded:true,icon:false}
]
const config={id:'settings',title:'迎新设置',file:'config/settings.json',reload:'live',readonly:false,revision:'demo',value:{enabled:true,welcomeMessage:'欢迎来到橙汁小站，一起分享今天的新发现。',quietHours:{start:'23:00',end:'08:00'},dailyLimit:12},fields:[{path:'enabled',label:'开启迎新',description:'允许发送欢迎提示',type:'boolean'},{path:'welcomeMessage',label:'欢迎语',description:'新朋友加入时显示的文字',type:'string'},{path:'quietHours',label:'安静时段',type:'object'},{path:'quietHours.start',label:'开始时间',type:'string'},{path:'quietHours.end',label:'结束时间',type:'string'},{path:'dailyLimit',label:'每日提示上限',description:'限制每日自动提示次数',type:'integer',min:1,max:50}],controls:[]}
const api={
  '/api/me':{username:'演示空间',role:'owner',csrf:'demo-only',version:'1.6.1'},
  '/api/settings':{version:'1.6.1',framework:'通用文件适配器 · 示例',externalPanels:[]},
  '/api/config-labels':{},
  '/api/system':{cpuPercent:18.6,cores:8,memory:{total:16*GiB,used:5.2*GiB,percent:32.5},disks:[{used:108*GiB,total:512*GiB,percent:21.1}],platform:'演示环境',architecture:'x64',host:'orangejuice-demo',uptime:259200,network:{received:1.8*GiB,sent:0.6*GiB},swap:{used:0,total:4*GiB},timestamp:1791520200},
  '/api/runtime':{stale:true,bots:[]},
  '/api/plugins':plugins,
  '/api/actions':[],
  '/api/configs':[config],
  '/api/config':config
}
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'}
const server=http.createServer((req,res)=>{
  if(req.method!=='GET'){res.writeHead(405);res.end('Read-only demo');return}
  const url=new URL(req.url,'http://localhost')
  if(url.pathname==='/api/plugin'){
    const item=plugins.find(p=>p.id===url.searchParams.get('id'))||plugins[0]
    res.setHeader('Content-Type','application/json; charset=utf-8');res.end(JSON.stringify({...item,configs:[config],commands:[],capabilities:[],functions:[],readme:'虚构示例插件，仅用于 README 展示。'}));return
  }
  if(Object.hasOwn(api,url.pathname)){res.setHeader('Content-Type','application/json; charset=utf-8');res.end(JSON.stringify(api[url.pathname]));return}
  const name=url.pathname==='/'?'index.html':url.pathname.slice(1)
  const target=path.resolve(root,'web',name)
  if(!target.startsWith(path.join(root,'web')+path.sep)||!fs.existsSync(target)||!fs.statSync(target).isFile()){res.writeHead(404);res.end();return}
  res.setHeader('Content-Type',types[path.extname(target)]||'application/octet-stream');res.end(fs.readFileSync(target))
})
server.listen(port,'127.0.0.1',()=>console.log(`Read-only demo: http://127.0.0.1:${port}/#/home`))
