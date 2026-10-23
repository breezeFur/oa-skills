# 数据源元数据获取指南（DataSetAction 接口）

> **冷启动禁止通读**：找表优先 `app-datasource-lookup-guide.md` + `e10-cli report find`。本文仅需全接口手册时再读。
> 对应 Java 文件：`DataSetAction.java`
> 统一前缀：`/api/{module}/{submodule}/ds` 或 `/api/{module}/ds`
> 认证方式：受 `@WeaPermission(publicPermission = true)` 保护，需携带 E10 标准登录态（`ebbusinessid`、`eteamsid`、`Cookie`）。

## 1. 用户指令到接口的路由规则

| 用户意图 / 指令 | 路由接口 | 前置依赖 |
| ---------------------------------------- | -------------------------------------------------- | ------------------------------------------ |
| "列出某个数据源下的所有数据集（不分页）" | `GET /ds/list` | 需已知 `sourceType` 与 `groupId` |
| "分页查询数据集列表" | `GET /ds/listByPage` | 需已知 `sourceType`、`groupId` |
| "获取数据源分组树" | `GET /ds/group` | 需已知 `sourceType` |
| "查看某数据集的字段列表" | `GET /ds/fields` | 需已知 `sourceId`、`sourceType` |
| "下拉选项/枚举值取数" | `GET /ds/options` | 需已知字段 `fieldName`、所属数据集 `objId` |
| "批量取多个字段的选项" | `GET /ds/optionsList` | 需字段集合 JSON |
| "校验 where 条件/函数公式是否可执行" | `POST /ds/conditionCheck`、`GET /ds/checkFunction` | 需完整 SQL/条件 JSON |
| "执行接口数据源的调用" | `GET /ds/callApi`、`GET /ds/getApiInfo` | 需 `queryDto`（含 queryType） |
| "根据 URL 解析数据源配置" | `GET /ds/pareDataSourceInfo` | 需目标页面/报表 URL |
| "获取 ESB 字段类型" | `GET /ds/queryForField`、`POST /ds/saveFieldsType` | 用于 ESB 动作流字段映射 |

## 2. 典型业务场景组合调用

### 场景 A：搭建 EB 报表时选择数据源 → 取字段 → 取选项

这是报表搭建（能力一）中最核心的数据源获取流程。

**分支（强制）**：

| 是否已指定 appId / appName | 流程 |
|----------------------------|------|
| **是** | 见 **`app-datasource-lookup-guide.md`** — 应用内 `form list` 或 scoped `listByPage`（1～2 次 API），**禁止**先调 `/ds/group` 全系统遍历 |
| **否** | 下列全系统步骤 1～2 |

全系统步骤（仅无 app 时）：

1. `GET /ds/group?sourceType=LOGIC` 获取表单类数据源分组
2. `GET /ds/listByPage?sourceType=LOGIC&groupId=weaver-ebuilder-form-service&name={关键字}&pageNo=1&pageSize=20` 分页选择数据集
3. `GET /ds/fields?sourceType=LOGIC&groupId=weaver-ebuilder-form-service&sourceId=xxx` 拉取字段结构
4. `GET /ds/options?sourceType=LOGIC&objId=xxx&fieldName=field_xx` 获取下拉选项
5. 如需批量：`GET /ds/optionsList?fieldList={...}`

应用内步骤（已指定 app，推荐）：

1. `e10-cli report find {appId} {表单名}` 或 `GET /api/datasource/ds/listByPage?sourceType=logic&appid={appId}&condition={name}` → `sourceId`
2. 报表内：`addDataset` → `fieldsAndOriginFields?isFront=true`（fieldKey 用 `data.fieldsKey`）
3. 字段核对走 fieldsKey / DataSetAction（本包不用 e10-cli）

### 场景 B：外部数据库数据源获取

1. `GET /ds/group?sourceType=EXTERNAL` 获取外部数据库分组树
2. `GET /ds/listByPage?sourceType=EXTERNAL&groupId={dbConnectionId}&pageNo=1&pageSize=20` 获取数据库下的表列表
3. `GET /ds/fields?sourceType=EXTERNAL&sourceId={tableId}` 获取表的字段结构

### 场景 C：内部接口数据源获取

1. `GET /ds/group?sourceType=INNERAPI` 获取内部接口分组
2. `GET /ds/listByPage?sourceType=INNERAPI&groupId={categoryId}&pageNo=1&pageSize=20` 获取分类下的接口列表
3. `GET /ds/fields?sourceType=INNERAPI&sourceId={apiId}` 获取接口返回字段

### 场景 D：报表搭建前预检数据源可用性

在执行 `saveReportConfig` 保存报表配置前，先通过数据源接口校验：
1. `GET /ds/fields` 确认所有 `sourceId` 对应的字段仍然存在
2. `GET /ds/checkFunction` 校验公式/条件是否可执行
3. `POST /ds/conditionCheck` 校验 where 条件语法

## 3. 接口间前后置依赖

```
GET /ds/group (获取分组树)
 │
 ▼
GET /ds/listByPage (选定数据集，拿到 sourceId)
 │
 ├──────────────────────────┐
 ▼ ▼
GET /ds/fields GET /ds/list (全量)
 │
 ├──────────────┐
 ▼ ▼
GET /ds/options GET /ds/optionsList (获取下拉选项)
```

- **所有查询接口** 必须先获取正确的 `sourceType`（枚举见下表）与 `groupId`。
- **`/ds/fields`** 依赖 `/ds/listByPage` 拿到的 `sourceId`。
- **`/ds/options`、`/ds/optionsList`** 依赖 `/ds/fields` 拿到的 `fieldName`。
- **`/ds/checkFunction`、`/ds/conditionCheck`** 必须在执行 SQL 类接口（`/ds/callApi`、`/ds/getFinalSql`）前优先调用，用于预检。
- **`/ds/permission`** 仅对数仓（ETEAMS）数据源有效，其他 `sourceType` 调用无意义。

## 4. sourceType 枚举速查

| sourceType | 含义 | 典型用途 |
| ---------------- | ------------------ | -------------------------------- |
| `ETEAMS` | E10 数仓 | 数仓报表，需 `permission` 校验 |
| `FORM` | EB 表单 | 表单数据集，最常用 |
| `BIZ` | 业务模块 | 业务数据集 |
| `LOGIC` | 逻辑数据源 | 跨表单组合视图 |
| `EXTERNAL` | 外部数据库 | MySQL/Oracle/PG/达梦等外部连接 |
| `INNERAPI` | 内部接口 | 平台内部 REST API 数据源 |
| `EXTERNALDATASET`| 外部数据集 | 外部系统自定义数据集 |
| `LOCALDS` | 本地数据源 | 本地文件/CSV |
| `BIDS` | 标书数据源 | 招投标场景 |
| `INTEGRATION` | 集成数据源 | 集成平台数据 |

## 5. 关键参数速查

| 参数 | 含义 | 典型值 |
| ---------------------- | --------------------------- | ------------------------------------------- |
| `sourceType` | 数据源类型枚举 | `FORM` / `LOGIC` / `ETEAMS` / `EXTERNAL` 等 |
| `groupId` | 数据源分组或连接 ID | 由 `/ds/group` 返回 |
| `sourceId` / `tableId` | 数据集 ID | 由 `/ds/listByPage` 返回 |
| `appId` | 所属应用 ID | eBuilder 应用 ID |
| `pageNo` | 当前页码（**注意**：不是 `current`） | 默认 1，≥1 |
| `pageSize` | 每页大小 | 默认 10，1~100 |
| `name` | 模糊搜索关键字 | 可为空 |
| `needPermission` | 是否开启权限校验 | 默认 false |
| `isPublic` | 是否支持外发 | 默认 false |
| `otherParams` | 扩展参数，JSON 字符串 | 含 `isPublic`、`dataUsage` 等 |
| `queryDto` | 查询结构体（JSON 字符串） | 含 `queryType`，用于 SQL 拼接 |
| `fieldInfo` | 字段映射入参（JSON 字符串） | 字段 ID + 选项集合 |

## 6. 核心接口详情

### 6.1 GET /ds/listByPage — 分页获取数据集列表

**业务用途**：搭建 EB 表单、报表、卡片时选择数据集的分页加载。

**请求参数**：

| 字段 | 类型 | 必填 | 传递位置 | 约束 | 说明 |
| -------------- | ------------ | ---- | -------- | ------------------------------------------------------------ | ----------------------------------- |
| sourceType | enum | 是 | query | `ETEAMS`/`FORM`/`BIZ`/`LOGIC`/`EXTERNAL`/`INNERAPI`/`EXTERNALDATASET`/`LOCALDS`/`BIDS`/`INTEGRATION` | 数据源类型 |
| groupId | string | 是 | query | 长度 ≤ 64 | 数据连接 ID 或分组 ID |
| name | string | 否 | query | 默认空串 | 按名称模糊搜索 |
| pageNo | int | 否 | query | 默认 1，≥1 | 当前页码 |
| pageSize | int | 否 | query | 默认 10，1~100 | 每页大小 |
| tableId | string | 否 | query | - | 指定表 ID |
| dataUsage | array | 否 | query | - | 数据用途过滤，如列表/图表 |
| needPermission | boolean | 否 | query | 默认 false | 是否开启权限校验 |
| appId | string | 否 | query | - | 应用 ID |
| comName | string | 否 | query | - | 组件名称 |
| isPublic | boolean | 否 | query | 默认 false | 是否支持外发 |
| otherParams | string(JSON) | 否 | query | 需 JSON 序列化 | 扩展参数，内部会自动追加 `isPublic` |
| dynamicParams | string(JSON) | 否 | query | 需 JSON 序列化 | 动态参数，解析为 `DynamicParamDto` |

**响应示例**：

```json
{
 "code": 200,
 "message": "success",
 "data": {
 "list": [
 {
 "id": "87123",
 "name": "demo_form",
 "label": "演示表单",
 "groupId": "1001",
 "sourceType": "FORM",
 "appId": "2001"
 }
 ],
 "total": 1,
 "pageNo": 1,
 "pageSize": 10
 },
 "success": true
}
```

**错误码**：

| code | 说明 |
| ---- | ------------------------------------ |
| 200 | 成功 |
| 500 | 服务器异常，`message` 含具体异常信息 |

**请求示例**：

```
GET /api/ebuilder/ds/listByPage?sourceType=FORM&groupId=1001&name=&pageNo=1&pageSize=10&needPermission=true
```

**调用参考**：
- 前置：先调 `GET /ds/group?sourceType=xxx` 拿到 `groupId`。
- 后置：拿到 `data.list[*].id` 后，调用 `GET /ds/fields?sourceType=xxx&sourceId=xxx` 获取字段。

**安全要求**：
- 必须校验用户登录态
- 当 `needPermission=true` 时，需过滤用户无权访问的数据集
- 风险等级：低（纯查询接口）

**注意事项**：
- `otherParams`/`dynamicParams` 为 JSON 字符串，务必进行 URL 编码
- `isPublic` 会被自动写入 `otherParams` 内部，建议只在外层传一次

### 6.2 GET /ds/group — 获取数据源分组树

**业务用途**：获取指定 `sourceType` 下的分组树结构，用于数据源选择面板的左侧导航。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
| ---------- | ---- | ---- | ------------ |
| sourceType | enum | 是 | 数据源类型 |
| appId | string | 否 | 应用 ID |

**响应示例**：

```json
{
 "code": 200,
 "data": [
 {
 "id": "weaver-ebuilder-form-service",
 "name": "EB表单服务",
 "children": [
 { "id": "form_001", "name": "人事表单组" }
 ]
 }
 ]
}
```

### 6.3 GET /ds/fields — 获取数据集字段列表

**业务用途**：获取指定数据集的全部字段结构，用于报表字段拖拽配置。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
| ---------- | ------ | ---- | -------------------------- |
| sourceType | enum | 是 | 数据源类型 |
| sourceId | string | 是 | 数据集 ID（来自 listByPage） |
| groupId | string | 否 | 分组 ID |

**响应示例**：

```json
{
 "code": 200,
 "data": [
 {
 "fieldId": "field_001",
 "fieldName": "f_emp_name",
 "label": "员工姓名",
 "type": "TEXT",
 "dbType": "VARCHAR"
 }
 ]
}
```

### 6.4 GET /ds/options — 获取字段下拉选项

**业务用途**：获取指定字段的下拉选项/枚举值，用于查询条件配置。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
| ---------- | ------ | ---- | ---------------- |
| sourceType | enum | 是 | 数据源类型 |
| objId | string | 是 | 数据集 ID |
| fieldName | string | 是 | 字段名 |

### 6.5 GET /ds/optionsList — 批量获取字段选项

**业务用途**：一次获取多个字段的下拉选项。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
| --------- | ------ | ---- | ---------------------- |
| fieldList | string | 是 | 字段集合 JSON 字符串 |

### 6.6 GET /ds/checkFunction — 校验函数公式

**业务用途**：校验报表公式/SQL 函数是否可执行，防止运行时报错。

### 6.7 POST /ds/conditionCheck — 校验 where 条件

**业务用途**：预检自定义筛选条件的 SQL 语法和合法性。

### 6.8 GET /ds/callApi — 执行接口数据源调用

**业务用途**：对内部接口类型数据源发起实际调用，获取返回数据。需 `queryDto` 中显式传入 `queryType`。

### 6.9 GET /ds/getApiInfo — 获取接口数据源信息

**业务用途**：获取内部接口数据源的元信息（URL、方法、参数定义）。

### 6.10 GET /ds/pareDataSourceInfo — 根据 URL 解析数据源配置

**业务用途**：从 e-builder 页面/报表 URL 中解析出数据源配置信息。`urlInfo` 为加密/编码字符串。

### 6.11 GET /ds/permission — 数据源权限校验

**业务用途**：校验用户对数仓（ETEAMS）数据源的访问权限。**仅对 ETEAMS 类型有效**。

### 6.12 GET /ds/getDataSourceName — 获取数据源名称

### 6.13 GET /ds/queryForField — 获取 ESB 字段类型

### 6.14 POST /ds/saveFieldsType — 保存 ESB 字段类型

### 6.15 POST /ds/fieldConvert — 字段类型转换

### 6.16 GET /ds/getFinalSql — 获取最终 SQL

> 必须在 `queryDto` 中显式传入 `queryType`，否则无法正确拼接 SQL。

### 6.17 GET /ds/getFinalSqlByType — 按类型获取最终 SQL

> 同样必须传入 `queryType`。

### 6.18 GET /ds/getGroupsForEteams — 获取 ETEAMS 分组

### 6.19 GET /ds/baseDataSourceInfo — 基础数据源信息

### 6.20 GET /ds/list — 全量数据集列表（不分页）

## 7. 应用内 vs 全系统查找（AI 必须遵守）

> 完整规则见 **`app-datasource-lookup-guide.md`**。

1. **用户已给 appId 或 appName** → 只在应用内找数据源（`form list` 或带 `appId`/`appid` 的 `listByPage`），**禁止**遍历全系统 `/ds/group`。
2. **用户未给 app** → 才走 §3 依赖图中的 `group → listByPage`；且 `listByPage` **必须带 name/condition 关键字**。
3. **探测预算**：应用内找表合计 ≤2、全系统合计 ≤3；超预算或难辨 → **打断询问用户**（`app-datasource-lookup-guide.md` §六）。
4. **少挂源 / 连续区域父格**：见 `datasource-selection-and-parent-filter-guide.md`。3. **用户已给 sourceId** → 跳过列表查找，直接 `fields` / `addDataset`。
4. **性能**：应用内路径目标 ≤3 次 API；全系统空扫常 10+ 次，导致任务响应慢。

## 8. 注意事项（AI 必须遵守）

1. **JSON 字符串参数需 URL 编码**：`otherParams`、`queryDto`、`fieldInfo`、`fieldList` 等均为 JSON 字符串，需 URL Encoded 后传递。
2. **queryType 必填**：`/ds/getFinalSql` 与 `/ds/getFinalSqlByType` **必须**在 `queryDto` 中显式传入 `queryType`，否则无法正确拼接 SQL。
3. **参数语义注意**：`/ds/checkFunction` 参数 `groupId` 与 `sourceId` 在代码中使用了同一个 `@Param("sourceId")`，调用时注意传参顺序与语义一致性。
4. **权限接口限定**：`/ds/permission` 仅对 `ETEAMS` 数仓类型生效。
5. **urlInfo 来源**：`/ds/pareDataSourceInfo` 的 `urlInfo` 是加密/编码字符串，来源于前端 E10 页面。
6. **错误结构**：通用错误返回结构为 `{ "code": 500, "message": "xxx", "data": ..., "success": false }`，需识别 `code` 与 `message`。
7. **分页参数命名差异**：本接口的分页参数是 `pageNo`/`pageSize`（DataSetAction 系列接口）。注意与数据源浏览器接口（`/api/datasource/common/browser/data/*`）的 `current`/`pageSize` 区分——两套接口的分页参数名不同！

## 9. 与数据源浏览器接口的区别

项目中存在两套数据源获取接口，用途不同：

| 对比项 | DataSetAction 接口 | 数据源浏览器接口 |
| ------ | ------------------ | ---------------- |
| URL 前缀 | `/api/{module}/ds/*` | `/api/datasource/common/browser/*` |
| 用途 | 报表搭建时的数据集选择器 | 设计器中数据源弹框选择 |
| 分页参数 | `pageNo` / `pageSize` | `current` / `pageSize` |
| 左面板数据 | `GET /ds/group` | `GET .../leftData/xxx` |
| 右面板数据 | `GET /ds/listByPage` | `GET .../data/xxx` |
| 认证 | E10 登录态 | 同左 |

**报表搭建时优先使用 DataSetAction 接口**（`/ds/*` 系列），因为它返回的数据结构更完整，且支持 `sourceId` → `fields` → `options` 的完整链路。

## 10. 变更记录

| 版本 | 日期 | 变更说明 |
| ---- | ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-03 | 基于 `DataSetAction.java` 初版生成，覆盖 list / listByPage / group / fields / options / optionsList / permission / getDataSourceName / queryForField / callApi / getApiInfo / fieldConvert / checkFunction / conditionCheck / getFinalSql / getFinalSqlByType / getGroupsForEteams / pareDataSourceInfo / baseDataSourceInfo / saveFieldsType 共 20 个接口 |
| v1.1 | 2026-08-03 | 整合到 report-builder-assistant 技能，补充场景 B/C/D、接口依赖图、sourceType 枚举速查、与浏览器接口对比表、分页参数差异说明 |
| v1.3 | 2026-09-04 | 场景 A 分支：已指定 app → 应用内查找；新增 §7 应用内 vs 全系统规则，链至 app-datasource-lookup-guide.md |
