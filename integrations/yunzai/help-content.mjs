// Fixed instructions only; no management URL, login ticket or runtime settings.
export const HELP_TEXT = 'OrangeJuice 管理面板\n#指令 /指令 #指令表 /指令表：按功能分类的全部指令；群聊隐藏主人指令，主人私聊显示完整表。\n#橙汁登录 /橙汁登录：主人临时登录链接，3分钟内一次有效。\n#橙汁功能 [功能名 开/关]：内置功能开关。\n#橙汁配置：插件列表。\n#橙汁配置 插件名 [搜索词或页码]：查询设置。\n#橙汁设置 插件名 选项编号 @版本 值：修改设置，支持 JSON 和开/关。\n配置命令仅主人私聊可用，保存会校验并备份。\n面板机器人桥接设置可配置自定义指令。\n网页登录支持账号密码和控制台验证码。\n#橙汁帮助 文字：查看文字版帮助。'

export const helpTopics = {
  'orangejuice-help': {
    title: '橙汁 · OrangeJuice',
    subtitle: '主人管理面板使用指南 · 仅机器人主人私聊查看',
    theme: 'dark',
    groups: [
      {title: '指令与入口', items: [
        {command: '#指令 / #指令表', description: '按功能分类查看实际加载指令；群内隐藏主人命令，主人私聊显示完整表。'},
        {command: '#橙汁登录 / /橙汁登录', description: '获取3分钟内一次有效的临时登录链接；请勿转发。', permission: '仅机器人主人私聊'},
        {command: '#橙汁帮助 / #橙汁帮助 文字', description: '查看本地固定帮助图，或切换文字版。', permission: '仅机器人主人私聊'}
      ]},
      {title: '配置与开关', items: [
        {command: '#橙汁功能 [功能名 开/关]', description: '查看内置功能状态；指定功能和开关可修改默认设置。', permission: '仅机器人主人私聊'},
        {command: '#橙汁配置', description: '查看可配置的插件列表。', permission: '仅机器人主人私聊'},
        {command: '#橙汁配置 插件名 [搜索词或页码]', description: '搜索配置选项，或翻页查看。', permission: '仅机器人主人私聊'},
        {command: '#橙汁设置 插件名 选项编号 @版本 值', description: '按查询返回的编号和版本修改设置；支持 JSON 与 开/关。保存前校验并备份。', permission: '仅机器人主人私聊'}
      ]},
      {title: '网页管理', items: [
        {command: '网页登录', description: '支持账号密码与控制台验证码；登录地址由当前实例配置提供。'},
        {command: '机器人桥接设置', description: '可配置自定义指令；目标命令仍执行原插件权限检查。'}
      ]}
    ],
    footer: '帮助只保存固定说明，不包含登录票据、服务地址或真实配置。动态指令表、配置查询与临时登录链接始终使用实时数据。'
  }
}
