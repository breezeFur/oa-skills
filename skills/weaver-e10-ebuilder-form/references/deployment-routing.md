# 独立部署检查与运行时路径路由

在唯一菜单或直接列表 URL 已确定，并取得或通过对应运行时接口发现 `appId` 后，调用后续列表或表单数据接口前读取本文件。

## 检查接口

接口来自 `RuntimeAppDeployController#isIndependentDeploy`：

```text
GET {origin}/api/ebuilder/form/app/isIndependentDeploy?appId={appId}
Cookie: <当前已认证会话>
```

- `{appId}` 取唯一菜单返回对象的 `appId`，或从受支持的直接链接结构中拆出；无损转换后按字符串保存，调用前校验为非空十进制 ID。
- 该检查固定使用公共 `/api/ebuilder` 路径，避免在部署模式尚未确定时形成循环路由。
- 控制器返回 `WeaResult<Boolean>`。只有 HTTP 和外层结果成功且业务 `data` 是 JSON 布尔值时才能确定部署模式。

## 确定前缀

| 检查结果 | 后续 `apiPrefix` | 示例 |
|---|---|---|
| 明确返回布尔 `true` | `/api/ebuilder{appId}` | `appId=123` 时为 `/api/ebuilder123/form/list/listInit` |
| 明确返回布尔 `false` | `/api/ebuilder` | `/api/ebuilder/form/list/listInit` |

`ebuilder` 与真实 `appId` 之间没有斜杠。只替换路径开头完整的 `/api/ebuilder`，不要重复拼接应用 ID。

## 应用范围

部署判断只影响公共路径以 `/api/ebuilder/form/**` 开头的接口。独立部署时，把这类路径开头的 `/api/ebuilder` 替换为 `/api/ebuilder{appId}`，包括：

- 菜单解析完成后的列表信息与 List/NList 配置请求。
- List/NList 分页数据、搜索、排序和总数请求。
- 主明细映射等位于 `/form/**` 的 CRUD 前置请求。
- 详情、新增、修改、删除、表单级分页和表单级总数请求。

以下接口不拼接 `appId`，始终使用各自的公共路径：

- 菜单搜索和作为部署判断入口的 `isIndependentDeploy`。
- `/api/ebuilder/common/**`，包括字段定义和字段选项。
- `/api/{module}/common/browser/**` 等字段配置指定的业务模块浏览接口。

禁止调用任何 `/api/bs/` 接口。

## 默认与一致性

- HTTP 失败、外层结果失败、401/403、`data` 缺失或不是布尔值时，部署模式仍未知。停止后续请求并修复会话或接口问题；不能把检查失败当作 `false`，也不能同时尝试两套前缀。
- 后续列表信息返回的 `appId`/`pageAppId` 与菜单或直链已确认的 `appId` 不一致：停止并报告上下文冲突。
- 只在当前 origin、租户、登录会话和 `appId` 的任务上下文中复用检查结果；切换任一项后重新检查。
- 本 skill 的脚本通过 `--api-prefix` 或 `EBUILDER_API_PREFIX` 接受 `/form/**` 的动态前缀；公共 `/common/**` 和业务模块浏览接口不受该参数影响。使用其他不支持动态前缀的客户端调用独立部署 `/form/**` 接口时，禁止回退到公共路径；改用同源浏览器按相同请求契约调用，或报告能力限制。
