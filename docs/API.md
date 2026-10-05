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
