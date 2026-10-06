# 部署与维护

## Linux 服务

在独立 Python 虚拟环境安装 requirements，使用该环境的 Python 执行 `scripts/install.py --systemd`。安装程序保留已有实例配置，已有 systemd 单元也不会覆盖。

```bash
sudo /opt/OrangeJuice-Plugin/.venv/bin/python scripts/install.py --framework-root /srv/yunzai --yunzai-bridge --systemd
systemctl status orangejuice
journalctl -u orangejuice -n 40
```

服务默认监听 `127.0.0.1:15082`。远程服务器可通过 SSH 转发保持本地地址：

```bash
ssh -N -L 127.0.0.1:16080:127.0.0.1:15082 user@your-server
```

此时设置 `publicUrl` 和桥接组件 `config/local.json` 的 `publicUrl` 为 `http://127.0.0.1:16080`。

浏览器使用 HTTPS 反向代理时将 `secureCookies` 设为 true，保持请求 Host 与 Origin 一致；允许的代理来源可放入 `allowedOrigins`。

## Docker 桥接

管理核心运行在宿主机。假设 `/srv/yunzai` 挂载为机器人容器 `/app`，实例配置使用：

```json
{
  "frameworkRoot": "/srv/yunzai",
  "pluginsDirectory": "/srv/yunzai/plugins",
  "bridgeDirectory": "/srv/yunzai/data/orangejuice",
  "runtimeFile": "/srv/yunzai/data/orangejuice/runtime.json"
}
```

桥接组件的 `ipcDirectory` 使用 `data/orangejuice`。第一次启动核心生成 `bridge.key`，确保机器人进程可读写共享目录；运行信息每5秒同步。它传递运行状态，以及通过主人权限检查的签名登录和配置请求。

## 服务动作与外部入口

`actions` 的每项包括 `id`、`label`、`description`、`command`。command 是固定参数数组，后台不执行 shell 字符串。例如 `['systemctl','restart','your-bot']`。仅主人可执行部署者明确配置的动作。重启本管理服务建议配置为 `systemctl --no-block restart orangejuice`。

`externalPanels` 可以配置固定 loopback `url` 或生成临时入口的 `command`，以及 `id`、`title`。面板只接收生成的 URL，不展示命令内容。外部入口当前限制 localhost/127.0.0.1。

`extraConfigs` 可把其他服务的 JSON/YAML 配置登记到某个插件：`plugin`、`id`、`title`、`path`、`fields`、`readonly`、`reload`。这些路径由部署管理员指定，保存会创建自动备份。

## 恢复

`data/accounts.json` 保存密码哈希，`data/bridge.key` 是桥接密钥，`data/backups` 是最近100次配置保存的备份。备份目录与实例配置属于私有数据。升级前保存这些目录和运行中的配置；对 YAML 保存会重新排版。

恢复旧管理器时先停止橙汁服务和桥接插件，再恢复旧插件及原端口转发。程序不会自动移除其他管理器。
