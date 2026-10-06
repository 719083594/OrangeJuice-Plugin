# HTTP API 1.0

返回 JSON；错误使用 HTTP 400/401/403/404/409/413/429/500/502/504，正文为 `{"error":"说明"}`。Cookie `oj_session` 为 HttpOnly/SameSite=Strict。登录后 GET /api/me 得到 csrf，写请求携带 X-CSRF-Token。

| 方法 | 路径 | 内容 / 权限 |
| --- | --- | --- |
| GET | /healthz | 健康、版本；公开 |
| POST | /api/auth/login | username/password；公开，限流 |
| POST | /api/auth/ticket | ticket；公开，一次有效 |
| POST | /api/auth/request-code | 请求控制台验证码；公开，限流 |
| POST | /api/auth/code | code；公开，一次有效 |
| GET | /api/me | 账号、角色、csrf |
| POST | /api/auth/logout | 注销当前会话 |
| POST | /api/auth/password | old/password；修改后清除该账号会话 |
| GET | /api/system | 主机资源，3秒缓存 |
| GET | /api/services | 容器、进程，20秒缓存 |
| GET | /api/runtime | 框架运行信息 |
| GET | /api/features | 功能清单、模块来源、默认群聊状态、入口重叠证据；登录后只读 |
| GET | /api/plugins | 插件清单 |
| GET | /api/plugin?id=目录 | 插件主页数据、README、配置索引、能力状态、已登记独立入口ID |
| GET | /api/icon?plugin=目录 | 本地图标 |
| GET | /api/configs?plugin=目录 | 独立配置文件清单 |
| GET | /api/config?plugin=目录&id=配置ID | value/revision/fields/readonly/ownerOnly/reload/format；敏感字段遮罩 |
| PUT | /api/config?plugin=目录&id=配置ID | value/revision；主人、管理员；ownerOnly 配置和敏感后台仅主人 |
| GET | /api/backups | 最近100次备份元数据；主人、管理员 |
| POST | /api/backups/restore | id/revision；主人 |
| GET | /api/audit | 最近100条审计；主人、管理员 |
| GET/POST/DELETE | /api/users | 查询、保存 username/role/password、删除 username；主人 |
| GET | /api/actions | 已注册服务动作 |
| POST | /api/action | id；主人 |
| POST | /api/external/open | id；主人；生成外部管理链接 |
| POST | /api/plugins/install | name/url；主人 |
| POST | /api/plugins/update | plugin；主人；Git ff-only |
| POST | /api/plugins/remove | plugin；主人；移到后台备份 |
| GET | /api/settings | 面板名称、版本、入口、保护插件、致敬 |
| POST | /api/internal/ticket | 专供本机 CLI；X-OJ-Time/X-OJ-Signature HMAC，非浏览器认证 |

浏览器只消费临时票据，不保存票据到本地存储。服务重启使全部会话失效。内部 CLI 签名采用请求时间加换行加规范紧凑 JSON 的 SHA256；桥接使用文件 IPC。

`/api/features` 返回 `available/stale/timestamp/items/files/duplicates/broadEntries/truncated/groupControl`。`items` 包含 name、description、source（插件目录相对路径）、origin、kind、event、rules、hooks、handlers、priority、defaultState；定时任务另有 cron、scheduled。缺少快照或默认群聊配置时显示未知。重复检查仅比较同名入口、相同正则源码与 flags 且事件范围交叉，不运行正则表达式，也不自动禁用插件。账号、群号及实例密钥不进入功能清单。


1.4.0：`/api/features` 增加 `pluginGroups`（插件归属、配置索引、字段说明、插件指令及能力声明）。每项登记入口增加 `pluginId/pluginTitle/displayName/explanation/operations/configRefs`。这些说明是展示元数据，不改变框架执行或权限。

1.5.0：`/api/plugins` 将框架模块合并为虚拟的 `framework` 内置插件；`/api/plugin?id=framework` 提供统一的功能、指令和配置入口。插件详情的 `functions` 对应当前登记的功能，能力声明保留 `configPaths`。`/api/config-labels` 返回功能名称字典；`/api/config` 的 `controls` 提供同一设置的 QQ 配置指令编号和版本。

`POST /api/function-control`：主人或管理员可通过 `{name, enabled}` 修改内置功能默认开关，保留账号和群覆盖。需要登录会话与 CSRF。模块和定时任务使用其配置项管理。

签名文件通信新增 `config-list`、`config-set`、`function-control`；由框架桥接仅允许主人私聊调用。配置写入调用统一 Catalog 保存流程；版本不一致、类型无效、只读或计划字段均拒绝写入。选项编号是配置与字段路径的摘要，字段路径不作为面板操作文本展示。外部框架也可接入相同管理核心。

`plugin=framework` 用于内置插件共享配置；`plugin=orangejuice&id=platform` 专用于平台设置，仅主人可保存，采用 revision 冲突检查和自动备份。平台表单只接受监听地址、端口、公开地址、目录、只读插件、来源及 Cookie 设置等声明字段，保留未展示的部署定义。运行服务必须通过 `--config` 指定实例文件。
