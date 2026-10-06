'use strict';
globalThis.OrangeJuiceFeatures = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const kinds = {command:'命令',notice:'通知事件',hook:'消息钩子',integration:'集成入口',task:'定时任务',module:'模块登记'};
  const origins = {framework:'内置插件',extension:'我的插件',unknown:'来源未提供'};
  const states = {enabled:'默认启用',disabled:'默认禁用','not-allowed':'不在默认白名单'};
  const permissions = {all:'所有用户',master:'仅主人',owner:'仅主人',admin:'管理员',groupAdmin:'群管理员',groupOwner:'群主'};
  function filter(report, {query='', origin='all', plugin='all', kind='all', overlapOnly=false} = {}) {
    const overlaps = new Set((report.duplicates || []).flatMap(group => group.ids));
    const q = query.trim().toLowerCase();
    return (report.items || []).filter(item => (origin === 'all' || item.origin === origin) && (plugin === 'all' || (item.pluginId || item.source?.split('/')[0]) === plugin) && (kind === 'all' || item.kind === kind) && (!overlapOnly || overlaps.has(item.id)) &&
      (!q || [item.name,item.displayName,item.description,item.explanation,item.pluginTitle,item.source,item.event,...(item.operations||[]).flatMap(x=>[x.title,x.command,x.description]),...(item.configRefs||[]).flatMap(x=>[x.id,...x.paths]),...(item.rules || []).flatMap(rule => [rule.pattern,rule.handler])].join(' ').toLowerCase().includes(q)));
  }
  function state(item) {
    if (item.kind === 'task') return item.scheduled ? '已排程' : '未排程';
    if (item.kind === 'module') return '模块登记';
    return states[item.defaultState] || '状态未提供';
  }
  function configButton(ref, title='打开配置') {
    if(ref.available===false)return `<span class="subtext">${esc(ref.id)}（当前未提供）</span>`;
    return `<button class="button" data-feature-config="${esc(ref.id)}" data-feature-plugin="${esc(ref.plugin)}">${esc(title)}</button>`;
  }
  function configuration(group) {
    return `<details class="feature-configs"><summary>配置项 · ${(group.configs||[]).length} 份配置</summary>${(group.configs||[]).map(c=>`<div class="feature-config-entry"><div class="card-head"><b>${esc(c.title)}</b>${configButton(c)}</div><small class="subtext">${esc(c.id)} · ${c.readonly?'只读':'可编辑'} · ${c.reload==='live'?'下次使用时读取':'保存后需重启相关服务'}</small>${c.fields?.length?`<div class="feature-fields">${c.fields.map(f=>`<div><code>${esc(f.path)}</code><span>${esc(f.label||f.path)}${f.readonly?' · 只读':''}</span>${f.description?`<small>${esc(f.description)}</small>`:''}</div>`).join('')}</div>`:'<p class="subtext">打开配置可查看全部实际字段和值；未声明的字段按原名称显示。</p>'}</div>`).join('')||'<p class="subtext">当前插件未提供可发现的配置文件。</p>'}</details>`;
  }
  function rows(report, options={}) {
    const selected=filter(report,options), overlaps=new Set((report.duplicates||[]).flatMap(g=>g.ids));
    let groups=report.pluginGroups;
    if(!groups)groups=[...new Set(selected.map(x=>x.pluginId||(x.origin==='framework'?'framework':x.source?.split('/')[0])))].map(id=>({id,title:id==='framework'?'内置插件':id,origin:id==='framework'?'framework':'extension',configs:[]}));
    groups=groups.filter(g=>(!options.origin||options.origin==='all'||g.origin===options.origin)&&(!options.plugin||options.plugin==='all'||g.id===options.plugin));
    return `<div class="feature-results">当前显示 ${selected.length} 项登记入口 · 按所属插件分组</div>`+['framework','extension','unknown'].map(origin=>{
      const included=groups.filter(g=>g.origin===origin).filter(g=>!options.query&&!options.overlapOnly&&(!options.kind||options.kind==='all')||selected.some(x=>(x.pluginId||(x.origin==='framework'?'framework':x.source?.split('/')[0]))===g.id));
      if(!included.length)return '';
      return `<section class="feature-category"><h2>${esc(origins[origin])}</h2>${included.map(g=>{
        const items=selected.filter(x=>(x.pluginId||(x.origin==='framework'?'framework':x.source?.split('/')[0]))===g.id);
        return `<section class="feature-plugin"><div class="card-head"><div><h3>${esc(g.title)}</h3><p class="subtext">${esc(g.description)}</p></div>${g.id==='framework'?configButton({plugin:'framework',id:g.configs?.some(c=>c.id==='group.yaml')?'group.yaml':g.configs?.[0]?.id||'',available:Boolean(g.configs?.length)},'内置插件配置'):`<button class="button" data-plugin="${esc(g.id)}">插件主页与配置</button>`}</div>${items.map(x=>`<article class="feature-item"><div class="card-head"><h3>${esc(x.displayName||x.name)} ${overlaps.has(x.id)?'<span class="pill gray">可能重叠</span>':''}</h3><span class="pill ${x.defaultState==='enabled'?'':'gray'}">${esc(state(x))}</span></div><p>${esc(x.explanation||x.description)}</p><div class="subtext">所属：${esc(g.title)} · ${esc(kinds[x.kind])} · ${esc(x.event||'事件未提供')}</div>${(x.operations||[]).map(op=>`<div class="feature-operation"><b>${esc(op.title)}</b><code>${esc(op.command)}</code><small>${esc(op.description)}</small></div>`).join('')}${!(x.rules||[]).length?`<p class="subtext">${x.kind==='module'?'没有聊天指令，由框架初始化。':'事件自动触发，不需要输入聊天指令。'}</p>`:''}${(x.configRefs||[]).length?`<div class="actions spaced">${x.configRefs.map(ref=>configButton(ref,ref.id)+' '+(ref.paths||[]).map(p=>`<code>${esc(p)}</code>`).join(' ')).join('')}</div>`:x.origin==='framework'?'<p class="subtext">本项没有专属配置字段；消息类入口还受群聊启用 / 禁用列表控制。</p>':''}<details class="feature-rules"><summary>查看原始规则与来源（${(x.rules||[]).length} 条）</summary><code class="feature-source">${esc(x.source)}</code>${(x.rules||[]).map(r=>`<div class="feature-rule"><code>/${esc(r.pattern)}/${esc(r.flags)}</code><small>${esc(r.handler)} · 注册权限：${esc(permissions[r.permission]||r.permission||'未提供')} · ${esc(r.event)}</small></div>`).join('')}${x.hooks?.length?`<small>内部钩子：${esc(x.hooks.join('、'))}（不作为聊天指令）</small>`:''}</details></article>`).join('')||'<p class="subtext">当前没有登记聊天或事件入口；下面列出插件声明及配置。</p>'}${(g.commands||[]).length?`<details class="spaced"><summary>插件声明的指令</summary><div class="actions spaced">${g.commands.map(c=>`<code>${esc(c)}</code>`).join('')}</div></details>`:''}${(g.capabilities||[]).length?`<details class="spaced"><summary>逐项功能说明（${g.capabilities.length} 项声明）</summary>${g.capabilities.map(c=>`<div class="feature-operation"><b>${esc(c.title||c.id)} <span class="pill ${c.status==='implemented'?'':'gray'}">${esc({implemented:'已实现',planned:'计划功能',unconfigured:'待配置'}[c.status]||'状态未提供')}</span></b><small>${esc(c.description)} ${esc(c.reason)}</small></div>`).join('')}</details>`:''}${configuration(g)}</section>`;
      }).join('')}</section>`;
    }).join('')+(selected.length||groups.some(g=>!options.query&&!options.overlapOnly)?'':'<div class="feature-empty">没有符合筛选条件的功能。</div>');
  }
  function duplicates(report) {
    return `<section class="card spaced"><div class="card-head"><h2>入口重叠检查</h2><span class="pill gray">${(report.duplicates || []).length} 组</span></div><p class="subtext">按同名功能或相同规则且事件范围交叉提示。结果不代表一定重复回复；优先级、返回值和插件内部判断仍会影响执行。</p>${report.duplicateTruncated?'<p class="subtext">重叠提示超过100组，当前显示前100组。</p>':''}${(report.duplicates || []).map(group => `<div class="feature-overlap"><b>${esc(group.label)}</b><code>${esc(group.evidence)}</code><p class="subtext">${group.ids.map(id => {const item=report.items.find(x => x.id === id);return item ? esc(item.name)+' · '+esc(item.source) : '';}).join('<br>')}</p></div>`).join('') || '<div class="feature-empty">当前没有发现同名或相同触发规则的交叉入口。不同规则仍可能处理相近功能，可用上方清单对照。</div>'}</section>`;
  }
  function files(report) {
    return `<section class="card spaced"><details><summary>查看模块文件登记（${(report.files || []).length} 个）</summary><div class="table-wrap"><table><thead><tr><th>文件</th><th>归属</th><th>功能入口</th><th>框架登记类数</th></tr></thead><tbody>${(report.files || []).map(file => `<tr><td><code>${esc(file.source)}</code></td><td>${esc(origins[file.origin])}</td><td>${esc(file.featureCount)}</td><td>${esc(file.importedClasses ?? '未提供')}</td></tr>`).join('')}</tbody></table></div><p class="subtext">仅初始化的适配器也会列在这里。没有消息处理器不等于模块未加载；类数来自框架注册表。</p></details></section>`;
  }
  return {filter,rows,duplicates,files,configuration};
})();
