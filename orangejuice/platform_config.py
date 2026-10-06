"""Editable platform settings. Deployment commands are never editable via this form."""
FIELDS = [
    {'path':'host','label':'监听地址','type':'string','description':'服务启动时使用；默认仅监听本机。修改后需重启橙汁服务。'},
    {'path':'port','label':'监听端口','type':'integer','min':1024,'max':65535,'description':'修改后需同步管理隧道并重启橙汁服务。'},
    {'path':'publicUrl','label':'管理面板访问地址','type':'string','description':'从机器人或终端生成登录链接时使用的地址。'},
    {'path':'frameworkName','label':'应用或框架名称','type':'string'},
    {'path':'frameworkRoot','label':'应用根目录','type':'string'},
    {'path':'frameworkConfigsDirectory','label':'内置插件配置目录','type':'string','description':'必须位于应用根目录内；用于功能清单中的内置配置入口。'},
    {'path':'pluginsDirectory','label':'外置插件目录','type':'string'},
    {'path':'bridgeDirectory','label':'机器人通信目录','type':'string','description':'与机器人桥接端保持一致。'},
    {'path':'runtimeFile','label':'运行信息文件','type':'string'},
    {'path':'readonlyPlugins','label':'只读插件列表','type':'array'},
    {'path':'allowedOrigins','label':'允许的额外页面来源','type':'array','description':'填写完整的 http 或 https 来源；同源页面默认允许。'},
    {'path':'secureCookies','label':'仅通过 HTTPS 发送登录凭据','type':'boolean','description':'HTTP 本机管理入口应保持关闭；HTTPS 部署可开启。'},
]
KEYS = frozenset(field['path'] for field in FIELDS)
