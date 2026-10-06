'use strict';
globalThis.OrangeJuiceFeatures = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const kinds = {command:'命令',notice:'通知事件',hook:'消息钩子',integration:'集成入口',task:'定时任务',module:'模块登记'};
  const origins = {framework:'框架内置',extension:'扩展插件',unknown:'来源未提供'};
  const states = {enabled:'默认启用',disabled:'默认禁用','not-allowed':'不在默认白名单'};
  const permissions = {all:'所有用户',master:'仅主人',owner:'仅主人',admin:'管理员',groupAdmin:'群管理员',groupOwner:'群主'};
  function filter(report, {query='', origin='framework', kind='all', overlapOnly=false} = {}) {
    const overlaps = new Set((report.duplicates || []).flatMap(group => group.ids));
    const q = query.trim().toLowerCase();
    return (report.items || []).filter(item => (origin === 'all' || item.origin === origin) && (kind === 'all' || item.kind === kind) && (!overlapOnly || overlaps.has(item.id)) &&
      (!q || [item.name,item.description,item.source,item.event,...(item.rules || []).flatMap(rule => [rule.pattern,rule.handler])].join(' ').toLowerCase().includes(q)));
  }
  function state(item) {
    if (item.kind === 'task') return item.scheduled ? '已排程' : '未排程';
    if (item.kind === 'module') return '模块登记';
    return states[item.defaultState] || '状态未提供';
  }
  function rows(report, options) {
    const selected = filter(report, options), overlaps = new Set((report.duplicates || []).flatMap(group => group.ids)), broad = new Set(report.broadEntries || []);
    return `<div class="feature-results">当前显示 ${selected.length} 项</div><div class="table-wrap"><table class="feature-table"><thead><tr><th>功能 / 来源</th><th>触发与权限</th><th>默认状态</th></tr></thead><tbody>${selected.map(item => `<tr><td><div class="feature-name">${esc(item.name)} ${overlaps.has(item.id)?'<span class="pill gray">可能重叠</span>':''}</div><div class="subtext">${esc(item.description)}</div><code class="feature-source">${esc(item.source || '适配器未提供文件')}</code><div><span class="chip">${esc(origins[item.origin])}</span><span class="chip">${esc(kinds[item.kind])}</span>${item.priority === null?'':`<span class="chip">优先级 ${esc(item.priority)}</span>`}</div></td><td><div class="feature-event">${esc(item.event || '事件未提供')}</div>${item.cron?`<div class="subtext">计划：${esc(item.cron)}</div>`:''}${broad.has(item.id)?'<div class="subtext">通用消息入口，是否响应由插件内部判断</div>':''}${(item.rules || []).length?`<details class="feature-rules"><summary>${item.rules.length} 条触发规则</summary>${item.rules.map(rule => `<div class="feature-rule"><code>/${esc(rule.pattern)}/${esc(rule.flags)}</code><small>${esc(rule.handler || '处理方法未提供')} · ${esc(permissions[rule.permission] || rule.permission || '权限未提供')} · ${esc(rule.event)}</small></div>`).join('')}</details>`:''}${item.hooks?.length?`<small class="subtext">钩子：${esc(item.hooks.join('、'))}</small>`:''}${item.handlers?.length?`<small class="subtext">处理器：${esc(item.handlers.join('、'))}</small>`:''}</td><td><span class="pill ${item.defaultState === 'enabled' || item.kind === 'task' && item.scheduled ? '' : 'gray'}">${esc(state(item))}</span></td></tr>`).join('') || '<tr><td colspan="3" class="feature-empty">没有符合筛选条件的功能。</td></tr>'}</tbody></table></div>`;
  }
  function duplicates(report) {
    return `<section class="card spaced"><div class="card-head"><h2>入口重叠检查</h2><span class="pill gray">${(report.duplicates || []).length} 组</span></div><p class="subtext">按同名功能或相同规则且事件范围交叉提示。结果不代表一定重复回复；优先级、返回值和插件内部判断仍会影响执行。</p>${report.duplicateTruncated?'<p class="subtext">重叠提示超过100组，当前显示前100组。</p>':''}${(report.duplicates || []).map(group => `<div class="feature-overlap"><b>${esc(group.label)}</b><code>${esc(group.evidence)}</code><p class="subtext">${group.ids.map(id => {const item=report.items.find(x => x.id === id);return item ? esc(item.name)+' · '+esc(item.source) : '';}).join('<br>')}</p></div>`).join('') || '<div class="feature-empty">当前没有发现同名或相同触发规则的交叉入口。不同规则仍可能处理相近功能，可用上方清单对照。</div>'}</section>`;
  }
  function files(report) {
    return `<section class="card spaced"><details><summary>查看模块文件登记（${(report.files || []).length} 个）</summary><div class="table-wrap"><table><thead><tr><th>文件</th><th>归属</th><th>功能入口</th><th>框架登记类数</th></tr></thead><tbody>${(report.files || []).map(file => `<tr><td><code>${esc(file.source)}</code></td><td>${esc(origins[file.origin])}</td><td>${esc(file.featureCount)}</td><td>${esc(file.importedClasses ?? '未提供')}</td></tr>`).join('')}</tbody></table></div><p class="subtext">仅初始化的适配器也会列在这里。没有消息处理器不等于模块未加载；类数来自框架注册表。</p></details></section>`;
  }
  return {filter,rows,duplicates,files};
})();
