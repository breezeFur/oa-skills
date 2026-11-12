# 按 Tag 查询按钮

> 通过登录态 PC 前台接口按一个或多个 Tag 查询当前表单数据上可用的按钮，并按显示/编辑布局返回当前用户有权限的按钮及其动作。调用方需同时处理 HTTP 异常、WeaResult 业务失败，以及 data 内单个按钮的 `success=false`。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/button/queryByTags` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | 当前登录用户会话（`Cookie: ETEAMSID={{ETEAMSID}}`） |
| **风险等级** | L1，只读 |
| **幂等性** | 是 |

使用 `weaver-e10-login` 建立的已认证会话发送请求。不要在 URL 中添加域名占位符、`access_token` 或其他认证参数。

## 请求参数

### Body 参数（JSON）

| 字段 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---|---|---|
| `objId` | Long | 是 | 表单对象 ID | 必须是有效的表单对象 ID |
| `dataId` | Long | 是 | 当前表单数据 ID | 必须属于 `objId` |
| `tags` | String | 是 | 一个或多个 Tag | 使用英文逗号分隔；服务端自动去除首尾空格并去重 |
| `viewType` | String | 是 | 布局类型 | 仅支持 `"0"`（显示布局，按查看权限判断）与 `"2"`（编辑布局，按编辑权限判断）；不支持其他值 |

## 请求示例

```http
POST /api/ebuilder/form/button/queryByTags
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "objId": 200001,
  "dataId": 300001,
  "tags": "approve,reject",
  "viewType": "0"
}
```

## 响应结构

接口返回 `WeaResult`，成功数据位于 `data`，为按钮数组：

```json
{
  "success": true,
  "errorMessage": null,
  "data": [
    {
      "buttonId": "100001",
      "buttonName": "同意",
      "tag": "approve",
      "success": true,
      "errorMessage": null,
      "actions": [
        {
          "actionId": "900001",
          "actionName": "提交审批",
          "actionType": "submit"
        }
      ]
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data[].buttonId` | String | 按钮 ID（Long 型，按字符串返回） |
| `data[].buttonName` | String | 按钮名称 |
| `data[].tag` | String | 按钮 Tag |
| `data[].success` | Boolean | 该按钮在当前布局/权限下是否可访问 |
| `data[].errorMessage` | String | 单按钮失败原因；无则 `null` |
| `data[].actions` | Array | 按钮动作列表；没有动作时返回空数组 |
| `data[].actions[].actionId` | String | 动作 ID |
| `data[].actions[].actionName` | String | 动作名称 |
| `data[].actions[].actionType` | String | 动作类型，例如 `submit` |

## 处理规则

- 没有动作的按钮仍需返回，`actions` 返回空数组。
- 传入多个 Tag 时，部分 Tag 未匹配：保留已匹配按钮，并在结果中返回对应失败信息。
- 所有 Tag 均未匹配：接口返回业务异常。
- 按钮匹配但当前用户无显示权限：仍返回该按钮和 `actions`，但 `success=false`，`errorMessage` 为「该按钮无权限显示」。
- 调用方应同时处理三层结果：HTTP 异常、WeaResult 业务失败、`data` 内单个按钮的 `success=false`。

## 错误处理

| 场景 | 表现 | 处理方式 |
|---|---|---|
| 所有 Tag 均未匹配 | 接口返回业务异常 | 透传 `code`/`msg`/`errorMessage`，报告未匹配并核对 Tag |
| 部分 Tag 未匹配 | 保留已匹配按钮并返回失败信息 | 展示匹配结果与失败信息，不丢弃已匹配按钮 |
| 按钮无显示权限 | 按钮 `success=false`，`errorMessage=「该按钮无权限显示」` | 原样透传，不模拟权限判断，不替代用户决策 |
| `HTTP 401` | 会话无效或过期 | 使用 `weaver-e10-login` 重新建立会话 |
| `HTTP 403` | 当前用户无权限 | 确认当前账号与租户权限 |
| `HTTP 5xx` 或超时 | 服务或网络异常 | 有限重试（只读请求） |

## AI 处理规则

1. `objId`、`dataId` 均为 Long 型 ID，始终按字符串保存、比较和展示，不使用 JavaScript Number 保存大整数。
2. `tags` 支持多个，使用英文逗号分隔；服务端自动去除首尾空格并去重，客户端可原样透传或先做同样的规范化。
3. `viewType` 只接受 `"0"` 或 `"2"`；其他值直接报参数错误，不猜测布局。
4. 判断按钮可用性以 `data[].success` 为准，不以 HTTP 状态或外层 `WeaResult.success` 代替。
5. 不在客户端绕过或模拟权限判断；单按钮 `success=false` 及其 `errorMessage` 原样透传给用户。
6. 不将按钮 Tag 视为唯一值；同一 Tag 可能匹配多个按钮。

## 版本信息

| api_version | doc_version | baseline | 状态 |
|---|---|---|---|
| v1 | 20260826.1 | E10 | active |
