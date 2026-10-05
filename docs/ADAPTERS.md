# 插件与框架适配

每个插件目录可放 `orangejuice.plugin.json`。核心读取声明，不导入或执行插件代码。

```json
{
  "title": "ExamplePlugin",
  "description": "示例插件的功能介绍",
  "homepage": "https://github.com/example/plugin",
  "commands": ["#示例帮助"],
  "configs": [{
    "id": "settings",
    "title": "基础设置",
    "file": "config/plugin.json",
    "example": "config/plugin.example.json",
    "reload": "restart",
    "fields": [{"path":"timeoutMs","label":"等待上限","description":"毫秒","type":"integer","min":1000,"max":30000}]
  }]
}
```

配置路径限定在插件目录内；支持 JSON/YAML。`defaults` 可代替 `example`。实例配置尚未存在时，后台先显示默认值，保存时创建实例文件。`readonly` 禁止保存。`reload` 为 `restart` 或 `live`；只有插件自身能即时读取文件时才标为 live。

字段支持 string、boolean、number、integer、array、object；可指定 required/min/max/enum。字段路径用点分隔，数组与对象在表单中以 JSON 编辑。未声明的已有字段仍完整显示。`password/token/secret/apiKey` 等敏感字段返回遮罩，保持遮罩会保留原值；填写新值会替换。

没有声明时，核心发现插件根目录、config 子目录的 JSON/YAML 和 data/config.json，排除包清单、锁文件及示例。自动发现不表示任意框架都能热更新，也不会解析 JavaScript 配置代码。复杂插件应把可配置数据和运行代码分离，或由部署者登记 extraConfigs。

## 运行信息

框架适配器原子写入 runtimeFile，格式如下：

```json
{
  "timestamp": 1780000000,
  "bots": [{"id":"example","nickname":"Demo","online":true,"platform":"Example","friendCount":1,"groupCount":1,"friends":[],"groups":[]}],
  "plugins": [{"directory":"ExamplePlugin","loaded":true}],
  "nodeVersion":"v22.0.0",
  "botRss":100000000,
  "botUptime":60,
  "loadedFunctions":12
}
```

30秒没有更新时标为过期；没有可靠加载证据时 loaded 应为 null，面板显示状态未提供。

## 主人登录 IPC

适配器在确认主人且属于私聊后，写入 bridgeDirectory/requests/随机UUID.json：payload 为 `{"action":"ticket"}`，time 为 Unix 秒数字符串，signature 为 HMAC-SHA256。签名原文是 `time + '\n' + SHA256(紧凑JSON(payload))`，密钥来自 bridgeDirectory/bridge.key。核心校验时间偏差30秒，生成3分钟一次有效 ticket，写入 responses/同名文件。适配器读取后删除响应并发给主人。

共享目录应限制为服务和机器人可访问。不要向群成员暴露 bridge.key、密码、实例配置或登录链接。新的框架可以独立实现这个协议，不需要采用云崽的目录或类结构。
