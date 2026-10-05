# 锅巴接口研究与对应关系

研究版本：Guoba-Plugin 1.4.2，commit `eab9cb27c0a4af105307568a84fee33ba6413b95`。研究范围包含控制器、服务、配置模型、认证拦截器、框架加载与插件声明。源码研究资料保存在开发工作区，不进入发布包。

扫描发现 **56 条路由声明**。其中喵喵专属接口按插件安装情况加载，V2 迁移仅在 V2 条件成立时加载，不能把声明数当成当前实例可用接口数。

## 模块结论

- 登录：主人临时码三分钟、控制台验证码五分钟，JWT 存 Redis；账号密码登录接口实际提示使用主人命令。橙汁改为 scrypt 哈希账号体系、HttpOnly 会话和单次凭据。
- 权限：原 getLoginUser 返回固定超级管理员角色；橙汁独立实现主人、管理员、观察员与写请求 CSRF。
- 插件：原 supportGuoba 运行 JavaScript 回调，使用 schemas/getConfigData/setConfigData/actions。橙汁采用数据声明与固定操作，不运行旧回调。
- 配置：原配置服务适配 TRSS/Miao/V2 不同模型；橙汁对 JSON/YAML 独立文件完整读写，复杂配置应提供适配声明。
- 系统与账号：原系统接口有目录树、新建目录、锅巴重载，QQ 接口有好友群组查询；新平台提供实际系统采集和桥接账号列表。
- 扩展：随机角色图、天气、喵喵帮助主题、V2 迁移是生态专属能力，未假装为通用能力实现。
- 替换：橙汁不是锅巴 API 的兼容层。安装旧插件不自动执行其 guoba.support.js。自制插件已增加原生声明；第三方插件的复杂回调需要单独适配。

## 完整声明清单

| 方法 | 原路径（/api 前缀省略） | 处理函数 | 新平台对应 / 适配说明 |
| --- | --- | --- | --- |
| POST | `/bot/restart` | `this.doRestart` | /api/action；部署者登记的固定重启动作 |
| GET | `/config/tabs` | `this.tabs` | /api/configs?plugin=framework |
| GET | `/config/data` | `this.getData` | /api/config?plugin=framework&id=文件，GET/PUT |
| POST | `/config/data` | `this.setData` | /api/config?plugin=framework&id=文件，GET/PUT |
| DELETE | `/config/card-Form` | `this.removeCardForm` | JSON 表单或原始 JSON 编辑数组/对象并保存 |
| GET | `/oicq/pick/user` | `this.pickUser` | /api/runtime；框架同步好友、群组、数量与基本信息 |
| GET | `/oicq/pick/group` | `this.pickGroup` | /api/runtime；框架同步好友、群组、数量与基本信息 |
| GET | `/oicq/friend/list` | `this.queryFriendList` | /api/runtime；框架同步好友、群组、数量与基本信息 |
| GET | `/oicq/friend/count` | `(` | /api/runtime；框架同步好友、群组、数量与基本信息 |
| GET | `/oicq/group/list` | `this.queryGroupList` | /api/runtime；框架同步好友、群组、数量与基本信息 |
| GET | `/plugin/list` | `this.getPlugins` | /api/plugins；本地已安装插件清单 |
| GET | `/plugin/readme` | `this.getPluginReadme` | /api/plugin；读取本地 README，主页可跳转项目仓库 |
| PUT | `/plugin/install` | `this.installPlugin` | /api/plugins/install；GitHub/Gitee HTTPS 克隆 |
| PUT | `/plugin/uninstall` | `this.uninstallPlugin` | /api/plugins/remove；移动到后台卸载备份 |
| GET | `/plugin/s/:pluginName/icon` | `this.getPluginIcon` | /api/icon |
| GET | `/plugin/s/:pluginName/config` | `this.getPluginConfig` | /api/configs 与 /api/config；使用独立声明而非导入 supportGuoba |
| PUT | `/plugin/s/:pluginName/config` | `this.setPluginConfig` | /api/configs 与 /api/config；使用独立声明而非导入 supportGuoba |
| POST | `/plugin/do/:pluginName/action` | `this.doAction` | /api/action；由部署者登记固定动作，未执行旧回调 |
| ALL | `*splat` | `this.handle404` | 参见模块说明 |
| ALL | `/helper/transit` | `this.transitRequest` | 不提供通用任意 URL 中转；外部管理入口由 /api/external/open 注册 |
| GET | `/helper/city_weather` | `this.getCityWeather` | 天气不属于配置管理；可通过联网搜索插件查询 |
| DELETE | `/helper/release_port` | `this.tryReleasePort` | 通过服务管理器停止实例；不提供匿名停止接口 |
| GET | `/v2-transfer/status` | `this.getTransferStatus` | 仅云崽 V2 条件加载的迁移模块；当前 V3/TRSS 与通用核心不提供 |
| POST | `/v2-transfer/reset` | `this.resetTransfer` | 仅云崽 V2 条件加载的迁移模块；当前 V3/TRSS 与通用核心不提供 |
| POST | `/v2-transfer/start` | `this.startTransfer` | 仅云崽 V2 条件加载的迁移模块；当前 V3/TRSS 与通用核心不提供 |
| PUT | `/v2-transfer/stop` | `this.stopTransfer` | 仅云崽 V2 条件加载的迁移模块；当前 V3/TRSS 与通用核心不提供 |
| GET | `/v2-transfer/check-js` | `this.checkJsFile` | 仅云崽 V2 条件加载的迁移模块；当前 V3/TRSS 与通用核心不提供 |
| GET | `/plugin/miao/help` | `this.getMiaoHelpCfg` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help` | `this.saveMiaoHelpCfg` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/theme/bg` | `this.getHelpThemeBg` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/theme/main` | `this.getHelpThemeMain` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/theme/list` | `this.getHelpThemeList` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/theme/config` | `this.getHelpThemeConfig` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help/theme/config` | `this.saveHelpThemeConfig` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help/theme/action` | `this.addHelpTheme` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help/theme/action_put` | `this.putHelpTheme` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| DELETE | `/plugin/miao/help/theme/action` | `this.deleteHelpTheme` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/icon` | `this.getHelpIcon` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help/backup` | `this.addBackup` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/plugin/miao/help/backup/list` | `this.getBackupList` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| POST | `/plugin/miao/help/backup/restore` | `this.restoreBackup` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| DELETE | `/plugin/miao/help/backup/delete` | `this.deleteBackup` | 喵喵专属帮助主题编辑接口；需要该插件单独实现适配，当前不提供 |
| GET | `/home/data` | `this.getHomeData` | /api/system + /api/runtime |
| GET | `/home/random-image` | `this.randomImage` | 使用原创橙汁图标；原神角色随机图不纳入通用核心 |
| POST | `/login` | `this.login` | /api/auth/login：新增真正的账号密码校验 |
| POST | `/logout` | `this.logout` | /api/auth/logout |
| POST | `/login/quick` | `this.quickLogin` | /api/auth/ticket；主人 IPC/CLI 生成临时票据 |
| POST | `/login/code/request` | `this.codeLoginRequest` | /api/auth/request-code |
| POST | `/login/code/check` | `this.codeLoginCheck` | /api/auth/code |
| GET | `/getPermCode` | `this.getPermCode` | /api/me role；后端逐接口执行真实角色校验 |
| GET | `/getMenuList` | `this.getMenuList` | 网页导航与角色；配置来自插件独立声明 |
| POST | `/sys/restart-guoba` | `this.doRestartGuoba` | /api/action；新管理服务固定重启动作 |
| PUT | `/sys/fs/create-dir` | `this.putCreateDir` | 通用核心限定注册配置目录；未实现任意文件系统管理 |
| GET | `/sys/fs/tree/root` | `this.getFsTreeRoot` | 通用核心限定注册配置目录；未实现任意文件系统管理 |
| GET | `/sys/fs/tree/children` | `this.getFsTreeChildren` | 通用核心限定注册配置目录；未实现任意文件系统管理 |
| GET | `/user/getLoginUser` | `this.getLoginUser` | /api/me；另外提供 /api/users CRUD |

认证范围：原 TokenInterceptor 对 /api 认证，排除 login、helper/transit、helper/release_port、插件 icon；喵喵主题可使用弱令牌。橙汁只有健康、静态页与公开登录端点免会话，内部票据接口要求独立签名。

新管理核心的全部接口见 [API.md](API.md)。本调研是独立实现的功能分析，不附带原项目的程序、图标或打包前端。
