# 插件与框架适配

独立管理服务不要求 `lib/plugins/plugin.js` 等云崽文件存在，也不导入机器人代码。`frameworkRoot` 表示通用应用根目录，`pluginsDirectory` 可为任意扩展目录；`frameworkConfigsDirectory` 可指定应用根目录内的 JSON/YAML 配置目录，不指定则保持兼容路径 `config/config`。其他框架无须伪造云崽目录。云崽适配器只是包内一个可选实现，未实现的框架专属功能不会自动可用。

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

字段支持 string、boolean、number、integer、array、object；可指定 required/min/max/enum。字段路径用点分隔，未声明的已有字段仍完整显示。`password/token/secret/apiKey` 等敏感字段返回遮罩，保持遮罩会保留原值；填写新值会替换。

对象与数组项可按中文字段表单编辑。嵌套对象标题使用对应字段的 `label`，数组子字段使用 `*` 通配符，例如 `channels.*.apiKey`。对象数组提供添加、删除入口；简单值数组保留 JSON 编辑。每个含密钥的数组项应有唯一、持久的 `id`，删除或重排后按标识保留原密钥，无法确定原项时拒绝保存，避免串用其他渠道密钥。

`secret:true` 可声明名称不含 key/token 的敏感字段；`maxTokens` 等数量参数仍正常显示。`multiline:true` 用于角色提示词等长文本，`enumLabels` 用于中文选项。数组字段的 `itemDefaults` 提供新增项默认结构，包含 `id` 时会生成新的 UUID。配置条目的 `ownerOnly:true` 使管理员和观察员仅能读取遮罩后的配置，修改仅允许主人。

```json
{
  "title": "AI-Plugin",
  "managementPanel": "ai-plugin",
  "capabilities": "capabilities.json",
  "configs": [{
    "id": "settings", "title": "AI 运行设置",
    "file": "config/local.json", "example": "config/example.json",
    "ownerOnly": true, "reload": "restart",
    "fields": [
      {"path":"channels","label":"模型渠道","type":"array","itemDefaults":{"id":"","name":"新渠道","apiKey":"","model":""}},
      {"path":"channels.*.id","label":"渠道标识","type":"string","required":true},
      {"path":"channels.*.name","label":"渠道名称","type":"string"},
      {"path":"channels.*.apiKey","label":"接口密钥","type":"string","secret":true},
      {"path":"channels.*.model","label":"模型名称","type":"string"},
      {"path":"presets.*.systemPrompt","label":"角色提示词","type":"string","multiline":true},
      {"path":"chat.reasoningEffort","label":"思考强度","enum":["low","high"],"enumLabels":{"low":"较低","high":"较高"}}
    ]
  }]
}
```

`managementPanel` 引用部署者登记的 `externalPanels[].id`，没有登记时不显示链接。打开入口需主人权限，服务端继续限制为本机 HTTP/HTTPS 地址。此声明不会执行插件代码或创建登录凭据。

`capabilities` 可提供内联数组或插件内 JSON 文件路径，文件接受数组或 `{"capabilities":[...]}`。每项包含 `id/title/description/status/reason`，状态为 `implemented`（已实现）、`unconfigured`（待配置）或 `planned`（计划功能）。面板只展示这些说明，不把计划功能做成可启用开关，也不会把该文件当成可编辑配置。

没有声明时，核心发现插件根目录、config 子目录的 JSON/YAML 和 data/config.json，排除包清单、锁文件及示例。自动发现不表示任意框架都能热更新，也不会解析 JavaScript 配置代码。复杂插件应把可配置数据和运行代码分离，或由部署者登记 extraConfigs。

## 运行信息

不修改第三方插件时，可在面板实例配置中登记 `pluginMetadata`，键为插件目录名。支持 title、description、author、version、repository、homepage 和 commands。它只补充展示信息，不改变配置文件路径、原生适配标记或只读权限。

```json
{"pluginMetadata":{"ExamplePlugin":{"title":"ExamplePlugin","description":"插件功能介绍","homepage":"https://github.com/example/plugin"}}}
```

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
