# eBuilder 接口索引（catalog）

本文件是 `weaver-e10-ebuilder-data` 的完整接口清单与路由索引。执行任务时依据本索引按需加载单个 reference，避免一次性加载全部资料。

## 前置依赖

- 必须先通过 `weaver-e10-login` 建立会话，取得完整请求地址、当前操作人及命名凭据 `key=ETEAMSID`。
- 运行时认证通过环境变量注入：`EBUILDER_ORIGIN`、`EBUILDER_COOKIE`（或 `ETEAMSID`），可选 `EBUILDER_API_PREFIX`。
- 请求头必须携带：① 完整原始 Cookie 串 ② `eteamsid` ③ `User-Agent: AgentType=<agentType>,IsAgent=true`（由 `scripts/ebuilder_http.py` 统一构造）。

## 接口分组

### 1. Tag 定位（跨环境重新定位表单）

| 接口 | 路径 | 文档 | 用途 |
|---|---|---|---|
| `getAppIds` | `/api/bs/ebuilder/app/tags/getAppIds` | [references/get-app-ids-by-tag.md](references/get-app-ids-by-tag.md) | 按应用 Tag 查询 appId |
| `getObjsByTag` | `/api/ebuilder/form/obj/getObjsByTag` | [references/get-objs-by-tag.md](references/get-objs-by-tag.md) | 按 appId + 表单 Tag 查询 objId |

### 2. 自定义接口（已发布，按 interfacePk 路由）

| 接口 | 路径 | 文档 | 用途 |
|---|---|---|---|
| `saveFormData`（新增） | `/api/ebuilder/form/formdata/v2/saveFormData/{interfacePk}` | [references/ebuilder-customapi-formdata-add.md](references/ebuilder-customapi-formdata-add.md) | 新增表单数据 |
| `updateFormData` | `/api/ebuilder/form/formdata/v2/updateFormData/{interfacePk}` | [references/ebuilder-customapi-formdata-update.md](references/ebuilder-customapi-formdata-update.md) | 修改表单数据 |
| `deleteFormData` | `/api/ebuilder/form/formdata/v2/deleteFormData/{interfacePk}` | [references/ebuilder-customapi-formdata-delete.md](references/ebuilder-customapi-formdata-delete.md) | 删除表单数据 |
| `getFormDataByPk` | `/api/ebuilder/form/formdata/v2/getFormDataByPk/{interfacePk}` | [references/ebuilder-customapi-formdata-querybypk.md](references/ebuilder-customapi-formdata-querybypk.md) | 按主键查询表单数据 |
| `getFormDataList` | `/api/ebuilder/form/formdata/v2/getFormDataList/{interfacePk}` | [references/ebuilder-customapi-formdata-querypagedata.md](references/ebuilder-customapi-formdata-querypagedata.md) | 分页查询表单数据 |
| `getFormDataCount` | `/api/ebuilder/form/formdata/v2/getFormDataCount/{interfacePk}` | [references/ebuilder-customapi-formdata-count.md](references/ebuilder-customapi-formdata-count.md) | 查询表单数据总数 |

### 3. OpenAPI（直接操作表单，按 objId 路由）

| 接口 | 路径 | 文档 | 用途 |
|---|---|---|---|
| `saveFormData` | `/api/ebuilder/form/dataset/v2/saveFormData` | [references/ebuilder-openapi-formdata-saveformdata.md](references/ebuilder-openapi-formdata-saveformdata.md) | 新建表单数据 |
| `updateFormData` | `/api/ebuilder/form/dataset/v2/updateFormData` | [references/ebuilder-openapi-formdata-updateformdata.md](references/ebuilder-openapi-formdata-updateformdata.md) | 修改表单数据 |
| `deleteData` | `/api/ebuilder/form/dataset/v2/deleteData` | [references/ebuilder-openapi-formdata-deletedata.md](references/ebuilder-openapi-formdata-deletedata.md) | 删除表单数据 |
| `getDataById` | `/api/ebuilder/form/dataset/v2/getDataById` | [references/ebuilder-openapi-formdata-getdatabyid.md](references/ebuilder-openapi-formdata-getdatabyid.md) | 获取数据详情 |
| `getAllData` | `/api/ebuilder/form/dataset/v2/getAllData` | [references/ebuilder-openapi-formdata-getalldata.md](references/ebuilder-openapi-formdata-getalldata.md) | 获取分页数据 |
| `getAllDataCount` | `/api/ebuilder/form/dataset/v2/getAllDataCount` | [references/ebuilder-openapi-formdata-getalldatacount.md](references/ebuilder-openapi-formdata-getalldatacount.md) | 获取数据总数 |

### 4. 元数据（字段、选项、映射）

| 接口 | 路径 | 文档 | 用途 |
|---|---|---|---|
| `getFields` | `/api/ebuilder/common/ds/fields` | [references/ebuilder-openapi-formdata-getfields.md](references/ebuilder-openapi-formdata-getfields.md) | 获取表单字段信息 |
| `getOptions` | `/api/ebuilder/common/ds/options` | [references/ebuilder-openapi-formdata-getoptions.md](references/ebuilder-openapi-formdata-getoptions.md) | 获取表单字段选项 |
| `getTableMapping` | `/api/ebuilder/form/dataset/v1/getTableMapping` | [references/ebuilder-openapi-formdata-gettablemapping.md](references/ebuilder-openapi-formdata-gettablemapping.md) | 获取主表/明细表标识映射 |
| OpenAPI 公共说明 | — | [references/ebuilder-openapi-common.md](references/ebuilder-openapi-common.md) | 认证、字段键、明细映射、响应校验 |

### 5. 浏览字段（按名称解析人员/部门/分部等）

| 能力 | 路径 | 文档 | 运行方式 |
|---|---|---|---|
| 按名称查询浏览字段 | `/api/{module}/common/browser/complete/{browserType}` | [references/browser-fields.md](references/browser-fields.md) | `scripts/query_browser_field.py` |

### 6. 按钮 Tag

| 接口 | 路径 | 文档 | 运行方式 |
|---|---|---|---|
| `queryByTags` | `/api/ebuilder/form/button/queryByTags` | [references/ebuilder-button-querybytags.md](references/ebuilder-button-querybytags.md) | `scripts/button_tag.py query` |

## 路由顺序

1. **准备会话**：加载 `weaver-e10-login`，确认环境与 `key=ETEAMSID`。
2. **定位**：缺少 `appId` → 应用 Tag 查询（分组 1）；缺少 `objId` → `appId + formTag` 查询（分组 1）。
3. **选接口族**：已发布自定义接口 → 分组 2（`interfacePk`）；直接操作表单/OpenAPI → 分组 3（`objId`）；两者均可能且意图不清时向用户确认。
4. **读取元数据**：数据任务先 `getFields`；需要选项名称/ID 转换时 `getOptions`；涉及明细时 `getTableMapping`。
5. **解析浏览字段**：仅名称 → 分组 5 脚本解析为 `optionId/content`。
6. **执行**：加载对应 reference，按文档组装请求并校验响应。

## 使用约束

- 只使用用户明确指定并已授权的 E10 环境；禁止猜测域名、禁止在对话中要求粘贴 Cookie。
- 写操作（新增/修改/删除）执行前必须取得用户明确确认。
- `401/403` 停止业务调用，交由登录技能刷新会话或确认权限。
