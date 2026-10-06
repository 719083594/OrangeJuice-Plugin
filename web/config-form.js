'use strict';

// This module renders data only. Plugins supply labels and rules in their manifest.
globalThis.OrangeJuiceConfigForm = (() => {
  const labels = {
    commandAliases: '自定义指令', alias: '自定义指令', target: '原始指令',
    publicUrl: '管理面板访问地址', frameworkName: '应用或框架名称', frameworkRoot: '应用根目录',
    frameworkConfigsDirectory: '应用配置目录', pluginsDirectory: '插件安装目录', bridgeDirectory: '机器人通信目录',
    runtimeFile: '机器人运行信息文件', readonlyPlugins: '只读插件列表', extraConfigs: '额外配置文件',
    actions: '服务管理操作', externalPanels: '独立管理入口', allowedOrigins: '允许访问的来源', secureCookies: '仅通过 HTTPS 发送登录凭据',
    pluginMetadata: '插件展示信息', ipcDirectory: '状态图片通信目录', pythonPath: 'Python 程序路径', fontPath: '中文字体路径',
    host: '监听地址', port: '监听端口', url: '服务地址', baseUrl: '接口基础地址', endpoint: '接口地址',
    timeoutMs: '等待上限（毫秒）', timeout: '等待上限', maxResults: '最多搜索结果', masterOnly: '仅主人可使用',
    cooldownMs: '用户冷却时间（毫秒）', timeZone: '显示时区', basic: '基础设置', provider: '默认模型服务',
    channels: '模型渠道', presets: '角色预设', chat: '聊天设置', group: '群聊设置', llm: '模型与对话',
    bym: '伪人模式', vision: '视觉配置', memory: '记忆设置', tools: '工具设置', media: '图片与媒体',
    automation: '自动任务', security: '安全设置', management: '管理面板', retention: '数据保留与清理', extensions: '扩展功能',
    chaite: 'Chaite 配置', masterQQ: '主人账号', masterQQs: '主人账号', ownerIds: '主人账号列表',
    botAlias: '机器人别名', whiteGroup: '群白名单', blackGroup: '群黑名单', blackQQ: '用户黑名单',
    blackUser: '用户黑名单', whiteUser: '用户白名单', allowedUsers: '允许的用户', blockedUsers: '禁止的用户',
    allowedGroups: '允许的群', blockedGroups: '禁止的群', enable: '启用', enabled: '启用', disable: '禁用',
    name: '名称', title: '显示名称', description: '说明', id: '标识', plugin: '所属插件', path: '文件路径',
    command: '操作命令', label: '显示名称', author: '作者', version: '版本', repository: '代码仓库', homepage: '项目主页', commands: '使用命令',
    apiKey: '接口密钥', key: '密钥', token: '访问令牌', password: '密码', secret: '密钥', auth: '服务认证', permission: '使用权限',
    model: '模型名称', defaultModel: '默认模型', embeddingModel: '向量模型', temperature: '回答随机度',
    maxTokens: '最多输出 Token', reasoning: '深度思考', reasoningEffort: '思考强度', stream: '流式请求',
    priority: '优先级', weight: '选择权重', systemPrompt: '角色提示词', prompt: '提示词', prefix: '调用前缀',
    readonly: '只读', ownerOnly: '仅主人可编辑', reload: '生效方式', format: '文件格式',
    fields: '字段定义', type: '数据类型', min: '最小值', max: '最大值', required: '必填',
    enum: '可选值', enumLabels: '选项显示名称', default: '默认值', defaults: '默认配置',
    example: '示例配置文件', file: '配置文件', itemDefaults: '新增项默认结构',
    multiline: '使用多行输入', rows: '输入框行数', schemaVersion: '声明格式版本',
    managementPanel: '独立管理入口标识', capabilities: '功能能力声明', status: '功能状态',
    cwd: '命令工作目录', timeoutSeconds: '等待上限（秒）', ticketSeconds: '登录链接有效期（秒）',
    sessionSeconds: '登录会话有效期（秒）', backupCount: '最多保留的备份数量',
    log_level: '日志等级', log_length: '单条日志长度', log_object: '对象日志格式', log_align: '日志标识对齐',
    plugin_load_timeout: '插件加载等待上限', file_watch: '监听文件变化',
    update_time: '自动更新时间', restart_time: '自动重启时间',
    update_cron: '自动更新计划（Cron）', restart_cron: '自动重启计划（Cron）',
    start_cron: '自动启动计划（Cron）', stop_cron: '自动停止计划（Cron）',
    cache_group_member: '缓存群成员信息', online_msg_exp: '上线通知冷却时间',
    file_to_url_time: '文件链接有效时间', file_to_url_times: '文件链接可访问次数',
    msg_type_count: '统计消息类型', chromium_path: 'Chromium 浏览器程序路径',
    puppeteer_ws: '浏览器 WebSocket 连接地址', puppeteer_timeout: '截图等待上限', proxyAddress: '代理服务器地址',
    dialect: '数据库类型', logging: '记录数据库操作日志', storage: '数据库文件位置', db: '数据库编号', username: '用户名',
    groupCD: '群指令冷却时间（毫秒）', singleCD: '个人指令冷却时间（毫秒）', onlyReplyAt: '仅响应提及机器人',
    addLimit: '添加自定义回复的权限', addPrivate: '允许私聊添加自定义回复', addReply: '回复自定义消息触发结果',
    addAt: '自定义回复提及触发者', addRecall: '撤回自定义回复',
    autoFriend: '自动同意好友申请', autoGroup: '自动同意群邀请', autoQuit: '自动退出群聊',
    disablePrivate: '限制私聊使用', disableMsg: '私聊禁用提示', disableAdopt: '私聊通行口令',
    master: '机器人与主人账号对应表', stdin: '接收控制台输入',
    connection: '事件接收方式', access_token: '访问令牌', heartbeat: '心跳间隔（秒）',
    reconnect_interval: '断线重连间隔（秒）', http_timeout: 'HTTP 请求等待上限（秒）',
    webhook: 'Webhook 事件接收', ws: 'WebSocket 事件接收', heartbeat_interval: '心跳间隔',
    http_endpoint: 'HTTP 接口地址', ws_endpoint: 'WebSocket 接口地址', platform: '平台类型',
    https: 'HTTPS 设置', redirect: '默认跳转地址',
    days: '保留天数', hours: '保留小时数', historyRetentionDays: '历史记录保留天数', imageRetentionPreset: '图片缓存保留方式',
    imageRetentionCustomHours: '图片缓存保留小时数', operationLogLimit: '最多保留的操作记录', autoVacuum: '自动回收数据库空间'
  };
  const configFileTitles = {
    bot: '机器人与运行日志', db: '数据库', group: '群聊与回复', milky: 'Milky 协议连接',
    other: '好友与访问权限', redis: 'Redis 连接', renderer: '截图渲染器',
    satori: 'Satori 协议连接', server: 'HTTP 服务'
  };
  Object.assign(labels, globalThis.OrangeJuiceLabels || {});
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const plainObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function metadata(path, fields = []) {
    const exact = fields.find(field => field.path === path.join('.'));
    return exact || fields.find(field => {
      const parts = String(field.path || '').split('.');
      return parts.length === path.length && parts.every((part, i) => part === '*' || part === String(path[i]));
    }) || {};
  }
  function label(path, fields) {
    const key = path.at(-1) ?? '配置';
    return metadata(path, fields).label || labels[key] || key;
  }
  function configTitle(entry, plugin) {
    const title = entry.title || entry.id || '配置';
    if (plugin !== 'framework') return title;
    const stem = String(entry.id || title).replace(/\.(?:json|ya?ml)$/i, '');
    // Explicit application titles take precedence over the filename fallback.
    return title !== stem && title !== entry.id ? title : configFileTitles[stem] || title;
  }
  function field(value, path, readonly, fields) {
    const meta = metadata(path, fields), title = label(path, fields);
    readonly = readonly || meta.readonly === true;
    const pointer = encodeURIComponent(JSON.stringify(path));
    const attr = `class="field-input config-field" data-path="${pointer}" ${readonly ? 'disabled' : ''} aria-label="${esc(title)}"`;
    let input;
    if (meta.status === 'planned') input = '<span class="pill gray">计划功能 · 当前版本未实现</span>';
    else if (Array.isArray(meta.enum)) input = `<select ${attr} data-type="${typeof value}">${meta.enum.map(v => `<option value="${esc(v)}" ${value === v ? 'selected' : ''}>${esc(meta.enumLabels?.[v] ?? v)}</option>`).join('')}</select>`;
    else if (typeof value === 'boolean') input = `<input ${attr} type="checkbox" data-type="boolean" ${value ? 'checked' : ''}>`;
    else if (Array.isArray(value) || value === null) input = `<textarea ${attr} data-type="json">${esc(JSON.stringify(value, null, 2))}</textarea>`;
    else if (meta.multiline && typeof value === 'string' && !meta.secret) input = `<textarea ${attr} data-type="string" rows="${Math.max(2, Number(meta.rows) || 4)}">${esc(value)}</textarea>`;
    else input = `<input ${attr} type="${meta.secret || value === '••••••••' ? 'password' : typeof value === 'number' ? 'number' : 'text'}" data-type="${typeof value}" value="${esc(value)}" ${meta.min !== undefined ? `min="${esc(meta.min)}"` : ''} ${meta.max !== undefined ? `max="${esc(meta.max)}"` : ''} step="any">`;
    return `<div class="form-field"><div class="form-label">${esc(title)}${meta.description ? '<small>' + esc(meta.description) + '</small>' : ''}</div><div>${input}</div></div>`;
  }
  function arraySchema(path, fields) {
    return fields.some(field => {
      const parts = String(field.path || '').split('.');
      return parts.length > path.length + 1 && parts[path.length] === '*' && path.every((key, i) => parts[i] === '*' || parts[i] === String(key));
    });
  }
  function renderTree(value, path = [], readonly = false, fields = []) {
    if (plainObject(value)) return Object.entries(value).map(([key, item]) => {
      const child = [...path, key], meta = metadata(child, fields);
      const locked = readonly || meta.readonly === true;
      if (meta.status === 'planned') return field(item, child, locked, fields);
      if (plainObject(item)) return `<section class="form-section"><h3>${esc(label(child, fields))}</h3>${meta.description ? `<p class="subtext">${esc(meta.description)}</p>` : ''}${renderTree(item, child, locked, fields)}</section>`;
      if (Array.isArray(item) && (arraySchema(child, fields) || item.length > 0 && item.every(plainObject))) {
        const pointer = encodeURIComponent(JSON.stringify(child));
        return `<section class="form-section"><div class="card-head"><div><h3>${esc(label(child, fields))}</h3>${meta.description ? '<small class="subtext">' + esc(meta.description) + '</small>' : ''}</div><button class="button" type="button" data-array-add="${pointer}" ${locked ? 'disabled' : ''}>添加一项</button></div>${item.length ? item.map((entry, index) => `<section class="card spaced"><div class="card-head"><h3>第 ${index + 1} 项${entry.name || entry.title ? ' · ' + esc(entry.name || entry.title) : ''}</h3><button class="button danger" type="button" data-array-remove="${pointer}" data-array-index="${index}" ${locked ? 'disabled' : ''}>删除此项</button></div>${renderTree(entry, [...child, index], locked, fields)}</section>`).join('') : '<p class="subtext">暂无配置项，添加后可以逐字段填写。</p>'}</section>`;
      }
      return field(item, child, readonly, fields);
    }).join('');
    return field(value, path, readonly, fields);
  }
  function readFields(original, elements) {
    const value = structuredClone(original); let result = value;
    for (const element of elements) {
      const path = JSON.parse(decodeURIComponent(element.dataset.path));
      if (!Array.isArray(path) || path.some(key => ['__proto__', 'constructor', 'prototype'].includes(String(key)))) throw new Error('配置字段路径无效');
      const next = element.dataset.type === 'boolean' ? (element.tagName === 'SELECT' ? element.value === 'true' : element.checked) : element.dataset.type === 'number' ? Number(element.value) : element.dataset.type === 'json' ? JSON.parse(element.value) : element.value;
      if (typeof next === 'number' && !Number.isFinite(next)) throw new Error('数值不是有效数字');
      if (!path.length) { result = next; continue; }
      let parent = value; for (const key of path.slice(0, -1)) parent = parent[key];
      parent[path.at(-1)] = next;
    }
    return result;
  }
  function newId() {
    if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = bytes[6] & 15 | 64; bytes[8] = bytes[8] & 63 | 128;
    const hex = [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  function arrayItem(path, fields = []) {
    const declared = metadata(path, fields).itemDefaults;
    if (plainObject(declared)) {
      const result = structuredClone(declared);
      if (Object.hasOwn(result, 'id')) result.id = newId();
      return result;
    }
    const result = {};
    for (const field of fields) {
      const declaredParts = String(field.path || '').split('.');
      if (declaredParts.length <= path.length + 1 || declaredParts[path.length] !== '*' || !path.every((key, i) => declaredParts[i] === '*' || declaredParts[i] === String(key))) continue;
      const parts = declaredParts.slice(path.length + 1);
      if (parts.includes('*') || parts.some(part => ['__proto__', 'constructor', 'prototype'].includes(part))) continue;
      let parent = result;
      for (const part of parts.slice(0, -1)) parent = parent[part] ||= {};
      parent[parts.at(-1)] = field.default ?? field.enum?.[0] ?? ({boolean: false, number: 0, integer: 0, array: [], object: {}}[field.type] ?? '');
    }
    if (Object.hasOwn(result, 'id')) result.id = newId();
    return result;
  }
  return Object.freeze({labels, metadata, configTitle, renderTree, readFields, arrayItem});
})();
