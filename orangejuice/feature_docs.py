"""Human descriptions for the optional TRSS adapter; never execute plugin code."""

# source -> title, explanation, configuration file, relevant paths
BUILTINS = {
    'system/botOperate.js': ('机器人连接操作', '向适配器提交登录验证或上线、下线请求；是否支持取决于连接适配器。', '', []),
    'system/recallReply.js': ('撤回消息', '主人引用一条消息后发送撤回指令；能否撤回取决于平台权限。', '', []),
    'system/master.js': ('设置主人', '发起主人绑定后输入验证码；现有主人可查看待验证的验证码。', 'other.yaml', ['masterQQ','master']),
    'other/sendLog.js': ('查看运行日志', '发送最近的运行或错误日志，可指定行数或关键词。', 'bot.yaml', ['log_level','log_length']),
    'system/disablePrivate.js': ('私聊访问控制', '限制非主人的私聊消息和戳一戳；允许指定通行内容，主人不受限制。', 'other.yaml', ['disablePrivate','disableMsg','disableAdopt']),
    'other/restart.js': ('进程管理', '重启机器人、停止进程或退出运行；这些是机器人进程操作。', 'bot.yaml', ['restart_time','restart_cron','stop_cron','start_cron']),
    'other/update.js': ('源码更新', '查看更新日志，更新框架或指定插件；具体权限还由处理方法检查。', 'bot.yaml', ['update_time','update_cron']),
    'other/install.js': ('安装插件', '交互选择或安装框架支持的插件，需要主人权限。', '', []),
    'example/主动复读.js': ('复读消息', '主人发送指令后再发送内容，机器人复读并在约5秒后撤回。', '', []),
    'example/进群退群通知.js': ('群成员通知', '监听成员加入、退出事件；欢迎新人和退群通知可分别控制。', 'group.yaml', ['default.enable','default.disable']),
    'system/friend.js': ('自动同意好友', '收到添加好友请求时按开关处理。', 'other.yaml', ['autoFriend']),
    'system/invite.js': ('邀请进群', '同意主人的群邀请；autoGroup=1 时也同意其他人的邀请。', 'other.yaml', ['autoGroup']),
    'system/quit.js': ('小群自动退出', '机器人入群时检查人数，低于阈值且无主人在群内时退出；0关闭。', 'other.yaml', ['autoQuit','masterQQ']),
    'system/status.js': ('状态统计', '发送机器人运行时长、框架及插件统计等文本信息。', '', []),
    'system/add.js': ('关键词消息', '添加、删除和列出关键词回复；全局操作仅主人，群内权限按配置判断。', 'group.yaml', ['default.addLimit','default.addPrivate','default.addReply','default.addAt','default.addRecall','default.botAlias']),
}

# Each registered rule has its own purpose. Examples are not replacements for regexes.
RULES = {
    ('system/botOperate.js','Verify'): ('提交连接验证', '#机器人验证 账号:验证内容', '仅主人；由连接适配器处理验证。'),
    ('system/botOperate.js','Operate'): ('上线或下线', '#机器人上线 账号 / #机器人下线 账号', '仅主人；适配器必须实现相应方法。'),
    ('system/recallReply.js','recall'): ('撤回引用消息', '#撤回 / 撤回', '处理方法额外检查主人权限。'),
    ('system/master.js','code'): ('查看待验证验证码', '#设置主人验证码', '仅已有主人查看，不会直接绑定新主人。'),
    ('system/master.js','master'): ('发起主人绑定', '#设置主人', '需要通过验证码验证才能完成绑定。'),
    ('other/sendLog.js','sendLog'): ('发送日志', '#运行日志 / #错误日志 / #日志200 / #日志关键词', '默认100行，最多1000行；仅主人。'),
    ('other/restart.js','restart'): ('重启机器人进程', '#重启', '仅主人；机器人会暂时断开并重新启动。'),
    ('other/restart.js','stop'): ('关机操作', '#关机', '仅主人；按框架启动方式执行停止操作。'),
    ('other/restart.js','exit'): ('停止进程', '#停止 / #停机', '仅主人；退出机器人进程。'),
    ('other/update.js','updateLog'): ('查看更新日志', '#更新日志 / #更新日志 插件名', '查看源码更新记录。'),
    ('other/update.js','update'): ('更新源码', '#更新 / #更新 插件名 / #强制更新 插件名', '处理方法会检查主人；强制更新可能覆盖本地源码修改。'),
    ('other/update.js','updateAll'): ('更新全部插件', '#全部更新 / #全部静默更新', '仅主人；遍历可更新的插件。'),
    ('other/install.js','install'): ('安装指定插件', '#安装插件 / #安装TRSS-Plugin', '仅主人；按交互提示继续。'),
    ('example/主动复读.js','repeat'): ('复读下一条内容', '#复读', '仅主人；之后发送要复读的内容。'),
    ('system/status.js','status'): ('查看框架统计', '#状态 / #统计', '注册规则还允许后续参数，实际统计由框架处理。'),
    ('system/add.js','add'): ('添加关键词回复', '#添加 关键词 / #全局添加 关键词', '发送内容后用 #结束添加 完成；权限由 addLimit 等配置决定。'),
    ('system/add.js','del'): ('删除关键词回复', '#删除 关键词 / #全局删除 关键词', '群内权限按配置检查，全局操作仅主人。'),
    ('system/add.js','getMessage'): ('触发关键词回复', '直接发送已保存的关键词', '这条宽泛匹配用于查找词条，不是空白指令。'),
    ('system/add.js','list'): ('列出关键词', '#消息 / #词条 / #全局消息', '查看当前群或全局词条。'),
}

EXTENSIONS = {
    'WebSearch-Plugin': [
        ('联网搜索', '#搜索 关键词 / /搜索 关键词', '搜索当前网页信息并按配置发送结果。'),
        ('文字搜索结果', '#搜文 关键词', '以文字发送摘要、来源链接及搜索时间。'),
        ('图片形式搜索结果', '#搜图 关键词', '把网页搜索结果渲染成结果图片；不等于搜索原始图片。'),
        ('搜索帮助', '#搜索帮助', '显示命令用法。'),
        ('搜索诊断', '#搜索诊断', '仅主人，检查 Python、图片组件和字体；本诊断不联网。'),
    ],
    'ServerStatus-Plugin': [
        ('系统总览', '#系统 / /系统 / #服务器', '发送宿主机系统总览图；仅主人。'),
        ('资源占用', '#资源', 'CPU、内存及资源占用图；仅主人。'),
        ('存储状态', '#存储', '磁盘和配置目录的容量统计；仅主人。'),
        ('插件状态', '#插件', '应用插件和程序状态图；仅主人。'),
        ('运行服务', '#服务', '服务和容器状态图；仅主人。'),
        ('系统帮助', '#系统帮助', '显示状态命令用法；仅主人。'),
    ],
    'OrangeJuice-Plugin': [
        ('打开橙汁面板', '#橙汁登录 / /橙汁登录', '主人获取一次性管理面板登录入口。'),
        ('橙汁帮助', '#橙汁帮助', '显示面板登录与使用方式。'),
    ],
}


def describe(item):
    path = item['source']
    known = BUILTINS.get(path) if item['origin'] == 'framework' else None
    item['pluginId'] = 'framework' if item['origin'] == 'framework' else item['directory'] or 'unknown'
    item['pluginTitle'] = '内置插件' if item['origin'] == 'framework' else item['directory'] or '来源未提供'
    item['displayName'] = known[0] if known else item['name']
    if path == 'example/进群退群通知.js': item['displayName'] = item['name']
    if path == 'system/disablePrivate.js': item['displayName'] += '（戳一戳）' if item['event'].startswith('notice') else '（消息）'
    item['explanation'] = known[1] if known else item['description']
    item['configRefs'] = [{'plugin':'framework','id':known[2],'paths':known[3]}] if known and known[2] else []
    item['operations'] = []
    for rule in item['rules']:
        note = RULES.get((path,rule['handler'])) if item['origin'] == 'framework' else None
        if note:
            item['operations'].append({'title':note[0],'command':note[1],'description':note[2]})
    if item['origin'] == 'extension' and item['directory'] in EXTENSIONS:
        item['operations'] = [dict(title=t,command=c,description=d) for t,c,d in EXTENSIONS[item['directory']]]
    if item['kind'] == 'module':
        item['explanation'] = '框架加载的连接适配或初始化模块；未登记聊天指令，不表示已有对应平台账号在线。'
    return item
