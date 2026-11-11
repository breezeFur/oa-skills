# 根据 appId 和表单 Tag 查询表单对象

## 接口信息

| 项目 | 值 |
|---|---|
| 接口 URL | `/api/ebuilder/form/obj/getObjsByTag` |
| 请求方式 | `GET` |
| 风险等级 | L1，只读 |
| 幂等性 | 是 |

使用 `weaver-e10-login` 建立的已认证会话发送请求。不要在 URL 中添加域名占位符、`access_token`、`ETEAMSID` 或其他认证参数。

## 请求参数

| 参数 | 位置 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---|---|---|---|
| `appId` | Query | String(Long) | 是 | 目标应用 ID | 必须是大于 0 的明确 ID；通常来自应用 Tag 查询结果 |
| `tag` | Query | String | 是 | 表单标签 | 非空；按配置原值等值查询，不自动改写 |

## 请求示例

```http
GET /api/ebuilder/form/obj/getObjsByTag?appId=1279678440787804160&tag=budget-apply-main-form
```

所有 Query 参数必须进行 URL 编码。示例 ID 和 Tag 仅用于说明格式，实际调用必须使用已确认值。

## 响应结构

```json
{
  "code": 200,
  "msg": "接口返回成功",
  "status": true,
  "data": [
    {
      "id": "1290084837213270016",
      "appId": "1279678440787804160",
      "objName": "budget_apply",
      "showName": "预算申请",
      "description": "年度预算申请表",
      "formId": "1234567890123456789",
      "tableType": "physical",
      "tableName": "ebdf_budget_apply",
      "permissionId": "1003213899747811329",
      "status": 0,
      "tag": "budget-apply-main-form"
    }
  ],
  "fail": false
}
```

## 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，`200` 表示查询正常处理 |
| `status` | Boolean | 外层处理状态 |
| `data` | Array<Obj> | 匹配表单列表；无匹配时为空数组 |
| `data[].id` | String(Long) | 表单对象 ID，即后续接口常用的 `objId` |
| `data[].appId` | String(Long) | 所属应用 ID，应与请求值一致 |
| `data[].objName` | String | 表单内部名称 |
| `data[].showName` | String | 表单显示名称 |
| `data[].description` | String/null | 表单描述 |
| `data[].formId` | String | 表单引擎 ID，不能与 `objId` 混用 |
| `data[].tableType` | String | 表单存储类型，例如 `physical` |
| `data[].tableName` | String | 表单物理表标识 |
| `data[].permissionId` | String | 权限资源 ID |
| `data[].status` | Integer | 表单状态 |
| `data[].tag` | String | 表单标签，应与请求值一致 |
| `msg` | String | 提示或失败原因 |
| `fail` | Boolean | 是否失败；部分基线可能不返回 |

响应可能包含其他公开表单属性。只提取任务所需字段，不依赖未文档化字段，也不输出完整对象。

## 结果示例

无匹配：

```json
{
  "code": 200,
  "status": true,
  "msg": "接口返回成功",
  "data": [],
  "fail": false
}
```

多个匹配时 `data` 包含多个 `Obj`。查询结果按创建时间从新到旧排列，但该排序不构成业务唯一性，也不能作为自动选择第一条的依据。

## 成功判定

同时满足以下条件才进入结果数量处理：

1. HTTP 请求成功。
2. `code == 200`。
3. `status == true`。
4. `data` 是数组。
5. 每条结果的 `appId` 和 `tag` 与请求一致。

## 错误码与失败结果

| 错误码/结果 | 场景 | 可重试 | 处理方式 |
|---|---|---|---|
| `code=200, data=[]` | 无匹配，或 `appId` 无效 | 否 | 报告未找到，核对应用 ID、表单 Tag 和安装状态 |
| `code=80005` | 部分基线对缺失 `appId` 或 Tag 返回参数异常 | 否 | 补充真实参数后再调用 |
| `HTTP 401` | 会话无效或过期 | 否 | 使用 `weaver-e10-login` 重新建立会话 |
| `HTTP 403` | 当前用户无读取权限 | 否 | 确认当前账号与目标应用权限 |
| `status=false` | 业务处理失败 | 条件可重试 | 读取脱敏 `code` 和 `msg`，参数或权限错误不重试 |
| `HTTP 5xx` 或超时 | 服务或网络异常 | 是，有限重试 | 保持环境、`appId` 和 Tag 不变，最多有限重试 |

## AI 处理规则

1. 缺少 `appId` 时先按应用 Tag 查询；应用查询多结果时必须先解决应用歧义。
2. 返回 0 条时报告该应用下未找到表单，不猜测 `objId` 或 `formId`。
3. 返回 1 条时明确映射 `data[0].id -> objId`，并返回必要元数据。
4. 返回多条时展示候选的 `objId`、`showName`、`formId`、`tableType`、`status`，要求用户选择或确认全部处理。
5. 所有 Long ID 按字符串处理；禁止把 `objId`、`formId`、`permissionId` 或业务数据 ID 混用。
6. 不跨应用或跨租户扩大查询范围，不使用 SQL 兜底。

## 版本信息

| api_version | doc_version | baseline | 状态 |
|---|---|---|---|
| v1 | 20260817.1 | E10 | active |
