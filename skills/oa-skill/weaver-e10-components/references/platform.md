# 平台操作与证据边界

先检查 `e10-cli --help`、相关子命令帮助及相邻搭建技能的当前文档。历史环境顶层帮助没有专门的组件命令组，不能编造 `component create` 命令。如果新版本已有正式组件命令，优先采用正式命令。

没有对应 CLI 能力时，可复用 e10-cli 登录态，通过其已验证的客户端访问平台原生 API；先在当前版本核对参数和响应。下面记录的是 2026-10-22 至 2026-10-27 本项目真实使用过的接口，版本变化时重新核对，不能当成永久公开 API。

| 操作 | 历史接口 | 关键点 |
|---|---|---|
| 注册组件 | POST `/api/ebuilder/coms/component/create` | 历史参数含 type、name、terminalTypes、category、layoutScopes、module、moduleScope；以当前平台参数为准 |
| 读取代码树 | GET `/api/ecode/tree/list?parentId=<ecodeId>` | 从实际返回树取得文件 ID，不根据组件 ID 猜测 |
| 读取文件 | GET `/api/ecode/code/getById/<fileId>` | 历史 content 为 Base64 源码；保留 sourceId |
| 更新代码 | POST form `/api/ecode/code/update/<fileId>` | 历史表单字段 id、content、compileContent、sourceId；源码与编译产物均为 Base64 |
| 导出组件 | GET `/api/ebuilder/coms/packing/component/export?styleId=<id>` | styleId 从平台实际组件记录核实；历史返回原生下载路径 |

请求以 HTTP 和平台业务响应同时判断成功；历史成功结构含 code=200、status=true。保存响应成功后仍需读取源文件与编译产物核验。

## 代码文件职责

- `Config.js`：属性面板。历史实测返回 `Promise.resolve({items:{...},formatFormDatas:function(v){...}})`，每项使用中文 label 和已验证的 itemType。
- `StyleConfig.js`：平台样式面板。历史组件返回空 items，因此不能假定用户在此处能配置样式；当时外观字段放在 Config.js。新组件可按当前平台支持的方式分组。
- `Design.js` / `View.js`：设计态与运行态，消费一致的配置模型，区分预览副作用。
- `MDesign.js` / `MView.js`：移动端实现；按用户需求和实测能力交付。

历史可用的最小面板结构：

```javascript
export default function Config() {
  return Promise.resolve({
    items: { title: { label: '标题', itemType: 'TEXTAREA' } },
    formatFormDatas: function (value) { return value; }
  });
}
```

这是接口形状样例，不是包含默认值、分组或复杂编辑器的完整模板。默认值和校验由当前实现补齐，其他控件需要查当前 SDK/已有可用组件并验证。

## 编译、保存、实例验证

复用 E10 同款编译能力，遵循相邻技能的编译约束。历史操作使用 compileJsE10 编译，并以平台 `weappEcodesdk.jsonp.export/require` 包装后上传；不要上传只有源码的文件后宣布部署成功。包装中的应用/模块标识必须与当前代码树匹配，不照抄业务页面 ID。

写入前保存当前组件登记信息、源码、编译产物及要修改的页面布局。新增时立即记录返回 ID 和代码文件映射，重试前查询已创建结果，防止重复注册。修改时比对当前内容，遇到他人更新先合并，不覆盖未知变更。

组件注册/代码保存与页面布局保存是两步。组件出现于左侧目录不代表实例配置已保存；按设计器真实流程保存布局、释放本次取得的锁，再重新读取实例配置。必要时刷新组件加载缓存，并在运行页验证。

编译失败先修本地源码，不上传无效产物。写入结果不明先回读，最多进行两次有明确原因的修复重试；重复失败保留备份、停止该写入并说明实际错误。不要自动删除已有实例或清理历史版本。

## 原生导出

下载使用当前登录客户端与原生返回路径，核对状态、响应类型、文件名、非空大小并记录哈希。历史下载文件虽为 `.zip`，内容不是标准 `PK` ZIP 头；因此保留原始字节，不因为扩展名尝试解压、重新打包或改写。下载成功与目标环境成功导入必须分别报告；目标导入需要用户本次明确要求且实测回读。
