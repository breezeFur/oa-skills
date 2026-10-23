# 查询条件 API 写入规范

> **适用场景**：通过 `saveQueryItem` / `saveQueryConfig` API 或脚本添加、修复报表查询条件。
> **参考报表**：`1304979556231593985`（EBU 经营数据统计）
> **代码实现**：`本地工作目录` → `ensure_query_conditions()`；执行 `python 本地工作目录`
> **核心规则**：数据集合选取后，**选择类型未特别指定 SQL 时，一律默认为「条件字段」**。

## ⚡ TL;DR — 显示方式（2026-09-11 定案，务必先读 §2.1）

| 事实 | 结论 |
|---|---|
| 条件级 `queryType` 正确落库值 | **JSON 数组字符串** `'["advance"]'`（高级搜索）/ `'["filter"]'`（筛选） |
| 前端回显判据 | 只看首字符是否 `[`；`'["advance"]'` → 勾选 ✅，`"advancedSearch"` → 不勾 ❌ |
| **`updateQueryType` 是最大陷阱** | 它把入参 `queryType` **批量写进所有条件**；传长码 = 一键摧毁全表回显（§2.1.3） |
| 保存后必须自检 | `e10-cli report query check-echo --report-id <id> --app-id <appId>` |
| 一键修复 | `e10-cli report query fix-echo --report-id <id> --app-id <appId>` |

---

## 一、选择类型（设计器 UI ↔ API）

| 设计器「选择类型」 | 顶层 `filterType` | `conditions[]` 内 | 说明 |
|-------------------|-------------------|-------------------|------|
| **条件字段**（默认） | `"default"` | **仅** `dataSetId` + `fieldId` + `relation` | 绑定数据集字段，禁止 SQL |
| **SQL**（显式指定） | `"sql"` | `"filterType": "sql"` + `sql` | 私有化环境才可用 |

**Agent 硬约束**：除非需求明确写「SQL 条件」，否则不得使用 `filterType: "sql"`。

**常见错误**

| 错误写法 | 后果 |
|----------|------|
| `conditions[].filterType: "field"` | 设计器「选择类型」无法回显为「条件字段」 |
| 顶层 `dataSetId` / `name` 有值 | 与设计器 save 形态不一致，回显异常 |
| `sqlOptions: {selected: ...}` | 条件字段应为 `{}` |
| `defaultValue: "3"`（非 JSON 数组） | `getQueryItem` 解析失败，整表 500 |
| **`queryItems` 传数组 `[]`/`[{…}]`** | 服务端 `parseObject` 单对象失败 / NPE → **saveQueryItem 500** |
| **`queryItems` 为 `{}` 且无 `conditions`** | `getConditions().size()` NPE → **500** |
| **JSON body 而非 multipart** | 参数绑不上 / 权限校验异常 → 常 500 |
| 缺 `ebBusinessId` | `wrapEbRightCheck` 编辑权限失败 |

---

## 二、条件字段标准形态（saveQueryItem）

设计器 save 后回读的基准结构：

| 字段 | 条件字段正确值 |
|------|----------------|
| 顶层 `dataSetId` | **`null`** |
| 顶层 `name` | **`null`** |
| `nameIndex` | **`"0"`** |
| `filterType` | **`"default"`** |
| `sqlOptions` | **`{}`** |
| `conditions[]` | 仅 `dataSetId` + `fieldId` + `relation` |
| `fieldOptions` | 必传（含 `selected`、`dataSetField`、`relation`）；`getQueryItem` 不持久化，更新时须重带 |
| `asNameIndex` | **唯一且 > 0**；更新时**必须回传**，否则置 0。`showOrder`（弹窗「排序」）人工配置通常留 **`0`**（= 未设，平台回落按 `asNameIndex` 排）——API 建条件时若自行填 1,2,3… 会在弹窗上留下可见差异（2026-09-14 参照报表 5 条全为 0）。事件超链接传查询值用 `{searchfield` + 三位补零 + `}`（如 `asNameIndex=1` → `{searchfield001}`，区间另加 `_start`/`_end`），见 `event-hreflink-guide.md` |
| **默认值三件套** | **必填**：`defaultValueType`（`default`=常规 / `custom`=自定义）+ `defaultValue`（当前生效值）+ `type1DefaultValue`（常规那份）/ `type2DefaultValue`（自定义那份）；值均为 **JSON 字符串**。**漏写 → 设计器弹窗「默认值类型」= 请选择、默认值区炸开、后续整段行被顶出可视区**（见 §2.1.10） |
| `fieldId` / `dataSetField` | fieldKey：`{dataSetId}.{sourceId}.{fieldName}` |
| **`queryType`（显示方式）** | **必填 JSON 数组字符串**，见 §2.1；`'["advance"]'`（高级搜索，默认）或 `'["filter"]'`（筛选），可双选 `'["advance","filter"]'`。**服务端也接受长码字符串 `"advancedSearch"`，但那样设计器 UI 不会勾选** |
| `showWhere`（遗留） | 设计器一律写 `""`；**勿**用它表达显示方式 |
| `browserType` / `browserTypeStr` | `displayType=browser` 时必填；富对象优先，落库判据是 `browserTypeStr`（见 §2.1.2） |

```python
def build_conditions(ds_id, field_id, relation):
 return [{"dataSetId": ds_id, "fieldId": field_id, "relation": relation}]

def build_field_options(ds_id, field_id, relation, item_id=None):
 row = {"dataSetField": field_id, "relation": relation, "queryItemValue": "输入值"}
 if item_id:
 row["id"] = str(item_id)
 return {"selected": ds_id, ds_id: [row]}
```

API：`POST /api/bs/edc/report/saveQueryItem`

| 项 | 正确 | 错误 → 常 500 |
|----|------|----------------|
| Content-Type | **`multipart/form-data`** | `application/json` 整包 body |
| 表单字段 | `reportId` + **`queryItems`** | 缺参、或写成 `queryItem` / `items` |
| `queryItems` 值 | **单个** QueryField **对象**的 JSON 字符串 | **`[]` / `[{...}]` 数组**（源码 `parseObject` 单对象） |
| Header | `eteamsid` + `Cookie` + **`ebBusinessId`/`ebbusinessid`=appId** | 缺业务 app，权限包装失败 |
| Referer | `/sp/edc/report/designer/{reportId}` | 可无，但建议带 |

```http
POST /api/bs/edc/report/saveQueryItem
Content-Type: multipart/form-data; boundary=----x

------x
Content-Disposition: form-data; name="reportId"

{reportId}
------x
Content-Disposition: form-data; name="queryItems"

{"dataSetId":null,"name":null,...,"conditions":[{...}],"fieldOptions":{...}}
------x--
```

**硬约束（源码 `EdcReportDevDesignServiceImpl.saveQueryItem`）**

1. `JSONObject.parseObject(queryItems, QueryFieldDto.class)` → **禁止**传数组。
2. 非私有化环境会对 `queryField.getConditions()` 做 `jsonArray.size()`；**`conditions` 为 null**（如 `queryItems="{}"`）→ **NPE → 接口 500**。
3. 一次请求只保存**一条**条件；多条 → **循环多次** `saveQueryItem`（每条一个对象）。
4. 更新已有条件：对象内带 `id`（字符串雪花）；新建不带 `id`，服务端生成并自动递增 `asNameIndex`。
5. `saveQueryConfig` **不能代替** `saveQueryItem`；可先可后，但有高级搜索条件时建议条件级 `queryType: '["advance"]'`（见 §2.1）。

```javascript
// ✅
await saveQueryItem({ reportId, queryItems: JSON.stringify(oneItemObject) });
// ❌
await saveQueryItem({ reportId, queryItems: JSON.stringify([oneItemObject]) });
await saveQueryItem({ reportId, queryItems: '[]' });
await saveQueryItem({ reportId, queryItems: '{}' }); // conditions 缺失 → 500
```

---

### 2.1 显示方式（强制 · 不可不选）

> **✅ 终局定案（2026-09-11 · 以「设计器手工配置的真实条件」为基准反推）**
>
> 条件级「显示方式」的正确落库值是 **JSON 数组字符串**：
>
> | 显示方式 | 正确落库值 |
> |---|---|
> | 高级搜索 | `'["advance"]'` |
> | 筛选 | `'["filter"]'` |
> | 两者都选 | `'["advance","filter"]'` |
>
> **服务端对取值不敏感**：`'["advance"]'` / `'["filter"]'` / `'["advance","filter"]'` / `"advancedSearch"` / `"filter"` **全部返回 200 并原样落库**。
> **但只有 JSON 数组形态能在设计器 UI 正确回显勾选**；长码字符串 `"advancedSearch"` 会导致 **UI 两个都不勾**（旧版文档「写短码 500」的说法是错的，见下方推翻记录）。

#### 2.1.1 前端回显规则（源码级 · `_src/route_DatasetList.js`）

前端**只看首字符是否为 `[`**，据此决定是否 JSON 解析：

```js
// ① 读取（initCondition）—— 唯一判定逻辑
t.queryType = (t.queryType?.indexOf("[") > -1)
 ? JSON.parse(t.queryType || "[]") // 含 "[" → 解析成数组
 : t.queryType || []; // 不含 → 原样保留（普通字符串）
```

```js
// ② 复选项定义（initConditionFormStore）—— 选项 id 是「短码」
queryType:{ itemType:"CHECKBOX", required:!0,
 data:[{ id: ze.g.advance, content:"高级搜索" },
 { id: ze.g.filter, content:"筛选" }],
 otherParams:{ minSelected:1 } }
```

```js
// ③ 短码枚举（lib.js）
function(e){ e.filter="filter"; e.advance="advance" }(i||(i={}))
```

```js
// ④ 新建条件默认值（仅 fieldKey 为空时）
this.fieldKey || (i.queryType = ["advance"]) // ← 注意：默认就是「数组」
```

```js
// ⑤ 保存 —— 表单值原样写回，不做类型转换
var l = e.conditionFormStore.getFormDatas();
r.queryType = l.queryType;
s.append("queryItems", JSON.stringify(r));
```

**推论（四条必须记牢）**

1. `CheckboxGroup` 用**严格相等**匹配：表单 value 的每个元素 vs `data[].id`。
2. 落库 `'["advance"]'` → 解析为 `["advance"]` → 元素 `"advance"` === 选项 id `"advance"` → **勾选 ✅**
3. 落库 `"advancedSearch"` → 不含 `[` → 保留为字符串 `"advancedSearch"` → 与选项 id 严格不等 → **不勾选 ❌**
4. **设计器自己写出的就是数组**（见 ④ 默认值、⑥ 实际请求）；长码 `"advancedSearch"` 只可能由**脚本手写**产生 → 它是**错误值**。

#### 2.1.2 证据链（2026-09-11，报表 `1313798296523022337`，应用「进销存管理-共享表」）

**A. API 写入实验（`saveQueryItem`，同一条件往返改 4 种值）**

| 写入值 | 返回 | 回读落库 | UI「显示方式」 |
|---|---|---|---|
| `'["advance"]'` | **200** | `'["advance"]'` | **高级搜索 ☑ ✅** |
| `'["filter"]'` | **200** | `'["filter"]'` | 筛选 ☑ ✅ |
| `'["advance","filter"]'` | **200** | `'["advance","filter"]'` | 双选 ☑ ✅ |
| `"advancedSearch"`（长码） | **200** | `"advancedSearch"` | **两个都不勾 ❌** |

> ⚠️ 四者**全部 200**，不存在「写短码 → 500」。旧结论 500 的真实成因是**手写 multipart payload 的结构/字段不被服务端封装接受**，与 `queryType` 取值无关。

**B. 三条条件 UI 回显对照（CDP 真实鼠标点击 tag → 读弹窗 checkbox）**

| 条件 | 落库 `queryType` | UI「显示方式」 |
|---|---|---|
| 销售部门（**人工手工配置**） | `'["advance"]'` | **高级搜索 ☑** |
| 销售人员（脚本写长码） | `"advancedSearch"` | **两个都 ☐** |
| 销售日期（脚本写长码） | `"advancedSearch"` | **两个都 ☐** |

→ 脚本手工写的长码条件**全军覆没**，人工配置的数组条件**正确回显**。把两条长码条件改为 `'["advance"]'` 后，三条**全部回显 ☑ 高级搜索**，闭环验证通过。

**C. 设计器真实 `saveQueryItem` 实际请求（人工点击「确定」）**

```
Content-Disposition: form-data; name="queryItems"

{"id":"…","sheetId":"…","nameIndex":"0","text":"销售部门","displayType":"browser",
 "showWhere":"","advancedSearchType":"openCondition","queryType":["advance"], … }
 ^^^^^^^^^^^^^^^^^^
 数组（短码），非字符串长码
```

> 设计器上行 payload 里就是 `"queryType":["advance"]`（**数组 + 短码**）—— 这是平台的权威写法。

#### 2.1.3 🔴 真正根因：`updateQueryType` 会**批量覆盖所有条件**（最关键）

> **`POST /api/bs/edc/report/updateQueryType` 不是「只改报表级设置」** —— 它会把入参 `queryType` **全量写进该报表的每一条查询条件**，覆盖刚保存好的数组值。
> 这是「条件显示方式永远不勾选」的**真正单点根因**，也是历史定位一直抓不到的那个洞。

** 矩阵**（同一报表连续调用，观察条件级 `queryType`）

| 调用 `updateQueryType(queryType=…)` | 三条条件级 `queryType` 变为 | 设计器回显 |
|---|---|---|
| `"advancedSearch"`（长码） | `advancedSearch` ×3 | **全不勾 ❌** |
| `"advance"`（裸短码） | `advance` ×3 | 不勾 ❌ |
| `"filter"` | `filter` ×3 | 不勾 ❌ |
| **`'["advance"]'`（数组短码）** | `'["advance"]'` ×3 | **全勾 ✅** |

**为什么历史定位一直失败**

```text
旧 CLI 的 save 流程： saveQueryItem(写 '["advance"]' ✅) → updateQueryType("advancedSearch" ❌)
 ↓ 刚写好的数组 ↓ 立刻被批量打回长码
 设计器打开 → 不勾选
人工在页面直接配条件： 只走 saveQueryItem，不经过 updateQueryType → '["advance"]' 完好 → 正常勾选
```

于是「人工配的能勾、API 写的不能勾」，长期被误判为「平台前端缺陷，客户端不可修」。**实际是 CLI 自己把值写坏了。**

**硬约束**

1. **`updateQueryType` 的 `queryType` 必须传数组短码**：`'["advance"]'` / `'["filter"]'`，**与条件级同形态**。传长码 = 一键摧毁全表回显。
2. **保存条件的推荐调用顺序**：`saveQueryItem`（数组） → `updateQueryType`（**同一个数组值**）。
3. **不要**在保存后用长码 `updateQueryType`「对齐报表级显示形式」—— 它顺带把条件级也改坏。若只需报表级 `advancedSearchType`（如 `openCondition`），仍须把 `queryType` 传成数组形态。
4. 落库后**必须回读自检**：`e10-cli report query check-echo --report-id <id> --app-id <appId>`。

#### 2.1.4 落库门禁

| 检查 | 接口 | 通过标准 |
|------|------|----------|
| **条件级显示方式（落库）** | `POST /api/bs/edc/report/getQueryItemNew`（multipart `reportId` + `query:'{}'`） | 每条 `queryType` 是 **含 `[` 的 JSON 数组字符串**，元素 ∈ `advance` / `filter` |
| 报表级 + 条件级批量对齐 | `POST /api/bs/edc/report/updateQueryType` | `code=200`，且入参 `queryType` **为数组短码**（§2.1.3） |

**硬约束**

1. **写 `queryType` = JSON 数组字符串**：`'["advance"]'` / `'["filter"]'` / `'["advance","filter"]'`。**不要写长码 `"advancedSearch"`**（可落库但 UI 不回显）。
2. **写 `showWhere: ""`**（遗留字段，设计器一致行为）。
3. **回读判据**：`getQueryItemNew` 的 `queryType` **必须以 `[` 开头**。若是 `"advancedSearch"` → **回显必不勾**，需改写为 `'["advance"]'`。
4. **强制走 CLI**：Agent 禁止手写 multipart 调 `saveQueryItem`；统一 `e10-cli report query save|type|list|check-echo|fix-echo` / `validate query`。
5. 用户反馈「显示方式没勾选」时：**先 `check-echo` 回读 `queryType`**。若为长码 → **可修复的落库错误**，`fix-echo` 即恢复（**不要再解释为平台缺陷**）；同时定位是否被 `updateQueryType` 长码覆盖过。

#### 2.1.5 报表级 vs 条件级（勿混淆）

| 层面 | 字段 | 正确值 | 存储形态 |
|---|---|---|---|
| **条件级**「显示方式」（编辑查询条件弹窗内） | `queryType` | `'["advance"]'` / `'["filter"]'` | **JSON 数组字符串**（§2.1） |
| **报表级**「高级搜索显示形式」（查询设置弹窗） | `queryType`（入参） | **也须 `'["advance"]'` / `'["filter"]'`** | 会被批量写入所有条件（§2.1.3） |

> 「查询设置」弹窗只有 `高级搜索显示形式 + 默认样式/展开条件` 等报表级开关；条件级的「显示方式 ☑高级搜索 ☑筛选」在**「编辑查询条件」**弹窗里，两者入口不同，但**落库字段同名、同形态、且共享覆盖关系**。

#### 2.1.6 ⚠️ 旧结论推翻记录（避免回退）

| 旧结论（2026-09-10/11 早期） | 现结论（2026-09-11 定案） |
|---|---|
| 落库必须写长码 `"advancedSearch"` | ❌ 错。落库必须写数组 `'["advance"]'` |
| 写短码 `"advance"` → 服务端 500 | ❌ 错。写数组短码 **200 正常落库** |
| 「UI 不勾选 = 平台缺陷，客户端不可修」 | ❌ 错。**改数组即可修复**，是脚本落库值写错 |
| `advancedSearch` 前端 0 次出现 → 服务端产物 | ⚠️ 部分成立（前台确实无此串），但它**不是**服务端要求的取值，而是脚本臆造的 |
| 前端 `edit` 直取长码灌表单 → 死循环 | ❌ 错。`edit` 灌的就是落库值；落库是数组时**正常勾选** |
| 条件级与报表级是两个独立字段，互不影响 | ❌ 错。`updateQueryType` 用 `queryType` **批量覆盖所有条件**（§2.1.3 真正根因） |
| `updateQueryType` 只改报表级「高级搜索显示形式」 | ❌ 错。它会把入参写进每条条件 → 长码一键摧毁全表回显 |

**旧结论怎么来的 / 为什么错**：早期用 JS 合成事件点击条件 tag，实际点到了**左侧字段面板**的「显示方式」（那是字段属性，非条件显示方式），读取勾选态得到假信号；且未把「人工配置的条件」作为基准对照。**修复方式**：改用 **CDP `Input.dispatchMouseEvent` 真实鼠标事件**点条件 tag，读「编辑查询条件」弹窗，并以人工条件为参照。

**真正根因的发现路径**：给 `save` 加「落库后回读自检」时，发现**刚写入的数组被回读成长码** → 隔离实验证明只有 `saveQueryItem` 时数组完好，一旦再调 `updateQueryType` 即被批量覆盖 → 穷举入参证明 `updateQueryType` 是「全表条件 `queryType` 批量写」。**AI 自检回读是抓到它的关键手段**，务必保留。

#### 2.1.7 修复已有错误条件的操作

**首选（CLI 一键）：**

```bash
e10-cli report query check-echo --report-id <id> --app-id <appId> # 诊断
e10-cli report query fix-echo --report-id <id> --app-id <appId> # 修正为数组短码
```
**修复显示方式（CLI 原生，无需手写脚本）：**

```bash
e10-cli report query fix-echo <reportId> --app-id <appId>   # 长码/空值 → 数组短码，恢复设计器勾选
e10-cli report query verify <reportId> --app-id <appId> --fix # 体检 Q1~Q10 + 幂等修复
```

**设计器真实保存形态（基准，从 `saveQueryItem` 实际请求）**

```json
{
 "id": "…", "sheetId": "<reportId>", "nameIndex": "0",
 "text": "销售部门",
 "displayType": "browser",
 "browserType": [{ "id": "3332180495306215437", "name": "部门", "type": "department",
 "module": "hrm", "groupId": "3332180495271315421", "tenantKey": "thfnde9fvr",
 "dataId": "2005096031068185488", "labelId": "52148",
 "licenseModule": "hrm", "systemDefault": 1, "ebuliderDataBrowser": false, "disable": 0 }],
 "browserTypeStr": "[{\"id\":\"HrmDepartmentComInfo\"}]",
 "showWhere": "",
 "queryType": ["advance"],
 "dateType": "ymd",
 "filterParam": { "optionTile": {}, "isTile": false, "multiple": true, "dataOptions": [],
 "enableOption": false, "required": false, "dateSelectDefaultValue": "",
 "numberSelectDefaultValue": "", "eBuilderForm": "", "titleField": "" },
 "defaultValue": "[[],\"\"]", "handleDefaultValue": "[[],\"\"]",
 "filterType": "default", "fieldOptions": {},
 "conditions": [{ "dataSetId": "…", "fieldId": "…", "relation": "Equals" }],
 "asNameIndex": 1, "showOrder": 1
}
```

---

### 2.1.9 🔴 `advancedSearchType` —— **禁止静默注入**（会改掉报表页查询区的「样式」）

> **事故（2026-09-14）**：在报表 `1314970921403138199` 加 5 条查询条件后，用户质问
> 「怎么又把查询条件的样式改了，这个之前强调过不能动页面上原有展示格式」。
> 定位结论：**用户的 payload 里根本没有 `advancedSearchType`**，是 CLI `save_query_item.js`
> 在保存时**无条件注入** `advancedSearchType: 'openCondition'`（=「展开条件」）。

**字段语义（源码级）**

| 项 | 结论 |
|---|---|
| 实体字段 | `QueryFieldCommon.advancedSearchType`（`@ApiModelProperty("高级搜索类型")`） |
| 唯一功能读点 | `SheetServiceImpl`：取**第一条**高级搜索条件的 `advancedSearchType`，`=='openCondition'` → `isOpenCondition=true` |
| 页面效果 | `isOpenCondition=true` → 报表页查询区**展开铺开**（「展开条件」）；否则 → **默认样式**（右上角搜索图标，点击才展开） |
| 设计器入口 | 报表级「查询设置」弹窗的 **高级搜索显示形式：默认样式 / 展开条件** |
| 人工条件（基准） | **该键不存在**（`undefined`），平台不主动写 |

**硬规则**

1. **入参没有该键 → 就别写该键**（保持线上原值）。CLI 只在显式 `--advanced-search-type openCondition` 时才写。
2. `updateQueryType`（批量对齐 `queryType`）**不得夹带** `advancedSearchType`。
3. 该字段属于**展示样式**，与「显示方式」（`queryType`：高级搜索/筛选）**是两回事**，不得绑定在一起写。
4. 用户没说「展开条件」时，任何情况下都不要写它。

**判别与修复**

```bash
# 判别：条件里 advancedSearchType 非空 = 被注入过
e10-cli report query list --report-id <id> --app-id <appId>

# 修复（默认 dry-run；--apply 落库；只清该字段，保留 id/顺序/queryType）
e10-cli report fix query-style --report-id <id> --app-id <appId> [--id <itemId>...] [--apply]

# 附带修复「不带 id 保存 → 变成新增」造成的重复条件行（删除必须显式列 id）
e10-cli report fix query-style --report-id <id> --app-id <appId> --delete-id <itemId> --apply
```

> ⚠️ **另一个必须记住的坑**：`saveQueryItem` **必须带 `id` 才是原地更新**；
> 不带 `id` 会**INSERT 一条新条件**（`asNameIndex` 自增），报表上出现重复条件。
> 更新存量条件时，payload 一律从线上回读对象派生并**保留 `id`**。

---

### 2.1.10 🔴 「默认值三件套」漏写 → 设计器弹窗整段坏掉（2026-09-14 事故）

**用户看到的现象**（"查询条件的样式被改了"）：

| 现象 | 说明 |
|------|------|
| 「默认值类型」= **请选择** | 本该是「常规」或「自定义」 |
| 「默认值」区**同时铺开所有控件变体** | 请输入 / 开始日期-结束日期 / 选择日期时间 / 请选择 / 选择日期 / 选择月份 / 选择年份 … 一屏全来 |
| 「日期类型 / 显示位置 / 条件必填 / 查询条件」**看不见** | 被上面那一大片顶出可视区（弹窗高度固定），并非真被删除 |

**根因**：弹窗的默认值区由 `defaultValueType` 驱动渲染。不写它 → 前端取不到模式 → 每个变体都渲染一遍。

**数据模型（ 参照报表 `1314938962594906121`，人工配置的权威形态）**

| 键 | 含义 | 参照「年月」取值 | 参照「部门」取值 | 参照「人员/加班/聘用」取值 |
|----|------|------------------|------------------|----------------------------|
| `defaultValueType` | 模式：`default`=常规 / `custom`=自定义（前端 label：`55337`=常规、`53999`=自定义） | `custom` | `default` | `default` |
| `defaultValue` | **当前生效**的值 | `["{yearmonth:-0}",""]` | `[[],""]` | `["",""]` |
| `type1DefaultValue` | 「常规」模式下保存的值 | `""` | `[[],""]` | `["",""]` |
| `type2DefaultValue` | 「自定义」模式下保存的值 | `["{yearmonth:-0}",""]` | `""` | `""` |
| `handleDefaultValue` | 平台解析后的实际值（**服务端自己算并回写**） | `["2026-09",""]` | `[[],""]` | `["",""]` |

> ⚠️ **全部是 JSON 字符串**（`"[[],\""]"` 这种），不是对象/数组本身。
> ⚠️ 日期占位符（`{yearmonth:-0}` 等）**不用自己解析**：落库时平台会把 `handleDefaultValue` 回写成 `["2026-09",""]`。
> 设计器「新建条件」模板本身带 `defaultValueType:"default"` + `defaultValue:["",""]`，所以**人工配的条件永远不会缺** —— 只有用 API 建条件时才会漏。

**修复**

```bash
# 只补缺失项（默认模式、空默认值 —— 弹窗恢复正常渲染，不改取数范围）
e10-cli report fix query-default --report-id <id> --app-id <appId> --apply

# 点名某条用「自定义」默认值（如 年月默认当月，与参照报表一致）
e10-cli report fix query-default --report-id <id> --app-id <appId> \
 --set '年月=custom:["{yearmonth:-0}",""]' --set '部门=default:[[],""]' --apply

# 顺带把「排序」对齐为设计器模板值 0
e10-cli report fix query-default --report-id <id> --app-id <appId> --all --show-order 0 --apply
```

落库后脚本会自动回读校验（`stillMissingDefaultValueType` 必须为空）。

---

### 2.1.11 ★ 查询条件合规体检（Q1~Q10 判据总表 · `e10-cli report verify query`）

> 把本章所有坑的**判据**固化成一条只读命令。搭完条件、改完条件、用户投诉后，第一件事就是跑它。
> **命令**：`e10-cli report verify query <reportId> <appId> [--json] [--fix]`（等价别名 `e10-cli report query verify ...`）
> 有 FAIL → exit 1；`--fix` 只做幂等安全项（清样式字段 / 补三件套 / 短码化），**绝不新增或删除条件**。

| # | 判据 | 级别 | 不通过时页面上的表现 | 出处 |
|---|------|------|----------------------|------|
| Q1 | `queryType` 是 **JSON 数组短码**（以 `[` 开头且可 parse 成数组） | FAIL | 设计器「显示方式」复选框是空的 | §2.1.1 / QUERY-1 |
| Q2 | `advancedSearchType` **必须为空** | FAIL | 报表页查询区从「默认样式」变成「展开条件」铺开 | §2.1.9 / QUERY-5 |
| Q3 | `defaultValueType` 有值（`default`\|`custom`） | FAIL | 弹窗「默认值类型」=请选择，默认值区把**所有**控件变体炸开 | §2.1.10 / QUERY-7 |
| Q4 | `defaultValue` 有值（JSON 字符串） | WARN | 默认值区仍可能铺开 | QUERY-7 |
| Q5 | `type1DefaultValue`（常规）/ `type2DefaultValue`（自定义）随模式在位 | WARN | 切换模式时值丢失 | QUERY-7 |
| Q6 | `id` 存在且 `asNameIndex` **唯一且 >0** | FAIL | 重复条件 / 保存变新增 | QUERY-6 |
| Q7 | `displayType=browser` 时 `browserType` 富对象非空 + `browserTypeStr` 非空 | FAIL | 关联类型为空、条件点不开 | §2.1.2 / QUERY-3 |
| Q8 | `filterParam.required` / `showType` 在位 | WARN | 「显示位置 / 条件必填」等弹窗后段字段为空 | — |
| Q9 | `showOrder` 是否为设计器模板值 `0` | INFO | 弹窗「排序」与人工配置有可见差异 | QUERY-7 |
| Q10 | 报表级 `queryType` **是否混杂**（同时存在多种写法） | WARN | 曾被 `updateQueryType` 批量覆盖过 | §2.1.3 / QUERY-2 |

> **不要拿 `getQueryConfig` 当判据** —— 本环境它恒返回 `data:null`（QUERY-4）。判据一律走 `getQueryItemNew` 回读。

---

### 2.1.2 关联类型 `browserType`：必须写「富对象」，不是 `[{id}]` 简写（强制）

> **事故**：同报表查询条件「销售部门」绑定字段 `originFieldType=Department`，但设计器关联类型显示为空/默认**人员**。**定案根因：`browserType` 写成了简写 `[{"id":"HrmDepartmentComInfo"}]`，缺少 `name`/`type` 等字段 → 前端无法解析显示名 → 退回默认「人员」标签页。**

**设计器真实形态（基准）**：`browserType` 是 **全字段富对象数组**，关键字段 `name`（显示名）、`type`（`department`/`employee`）、`module`、`groupId`、`tenantKey`、`dataId`、`labelId`、`id`。**`browserTypeStr` 才是落库判据**（服务端存 `[{"id":"HrmDepartmentComInfo"}]` 形式的字符串）。

| 字段 `originFieldType` | `displayType` | `browserTypeStr`（落库） | 设计器关联类型 |
|------------------------|---------------|--------------------------|----------------|
| `Employee` | `browser` | `[{"id":"HrmEmployeeComInfo"}]` | **人员** |
| `Department` | `browser` | `[{"id":"HrmDepartmentComInfo"}]` | **部门** |
| `DepartmentAllPath` | `browser` | `[{"id":"HrmDepartmentAllPathComInfo"}]` | 部门全路径 |

**推荐获取富对象的正确姿势（最稳）**：**不要手拼** `browserType` 富对象；用 `saveQueryItem` 时：
1. `displayType: "browser"` + `browserTypeStr` 写 `[{"id":"HrmDepartmentComInfo"}]`；
2. 或在设计器里手动选一次「部门」让前端生成富对象后实际请求复用（本环境已验证：手动选后可正确回显「部门」）。

**硬约束**

1. `displayType: browser` **禁止** `browserTypeStr: "[]"`；必须按字段 `originFieldType` 写入对应 ComInfo id。
2. 仅写 `[{"id":...}]` 简写**服务端可接受**（`browserTypeStr` 落库正确），但**前端回显可能为空**；若要求 UI 正确显示，需富对象。
3. `save_query_item.js` 内置 `applyQueryDisplayType()` 自动补 `browserType`（未显式指定 `displayType` 时）；不匹配时输出 **WARN**。
4. 回读核对：`browserTypeStr` 不得为 `"[]"`（丢了 → 退回「人员」）。
5. 跳过自动推导用 `--skip-display-type`（仅在确实要手填时）。

---

```javascript
// 显示方式：条件级落库值 = JSON 数组字符串（前端唯一能回显勾选的形态）
function resolveQueryType(userHint) {
 const s = String(userHint || '').toLowerCase();
 if (/筛选|filter/.test(s) && !/高级搜索|advanced/.test(s)) return '["filter"]';
 return '["advance"]'; // 默认「高级搜索」· 不可不选
}
// 注意：showWhere 一律写 ''（遗留字段）
// 条件级选项 id 是短码 advance/filter；落库必须是含 "[" 的 JSON 数组字符串，
// 否则前端首字符判定落空 → 退化为普通字符串 → 严格相等失败 → UI 不勾选（见 §2.1）
// 报表级 updateQueryType 的 queryType 也须用数组形态（它会批量覆盖所有条件，见 §2.1.3）
```

### 2.1.8 「显示方式没勾选」诊断卡（对接用户质询时用）

| 用户说法 | 你的回答要点 |
|---|---|
| 「页面上显示方式没勾选」 | 先 `getQueryItemNew` 回读 `queryType`：**是否以 `[` 开头**？ |
| 「回读是 `'["advance"]'` 却仍不勾」 | 极罕见；先强刷设计器页面（CDN/缓存），再核对条件 `id` 是否为最新 |
| 「回读是 `"advancedSearch"` 长码」 | **这是落库值写错了**，属可修复问题 → 改写为 `'["advance"]'`，重开弹窗即勾选 |
| 「能修吗？」 | **能修**：把 `queryType` 改为 JSON 数组字符串（§2.1.7 脚本 / `e10-cli report query fix-echo`） |
| 交付口径 | 「已修正落库值，条件显示方式回显正常」——**不要再解释为平台缺陷** |

**判据一行流**

```text
queryType 以 "[" 开头 → 数组 → UI 勾选正常 ✅
queryType 是其它字符串 → 退化 → UI 不勾选 ❌（改写为 '["advance"]'）
```

> 来源：前端 bundle 经 CDP `Debugger.getScriptSource` 导出至 `本地工作目录`
> （`route_DatasetList.js` 179879B / `route_ReportDesigner.js` 702877B / `lib.js` 661658B）；
> UI 回显用 `_q_real2.py`（CDP `Input.dispatchMouseEvent` 真实鼠标点击条件 tag + 读「编辑查询条件」弹窗 checkbox）。

### 2.1.2.1 关联浏览分类元数据接口（⚠️ 富对象唯一正确来源）

> **勿手拼富对象！** 富对象的 13 个字段值全部来自服务端接口，手拼易错（`labelId`/`dataId` 无法猜）。
> 本接口 2026-09-11 定位、**2026-09-14 修正为 GET `browserBeanSearch`**，为「部门 / 人员 / 岗位 …」全部关联类型的权威数据源。

```http
GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文分类名>
Header: ebbusinessid: <appId>
→ data.data[] 每条 = 13 键富对象
```

> 🔴 **2026-09-14 修正**：旧文档写的 `POST /api/bcw/relevanceBrowser/getBrowserBean` 在**本环境恒返回 `{"code":500,"msg":"接口错误"}`**（前端其实把 `browserBeanSearch` 的响应**本地拦截**了 —— 见 `lib.js` 里 `relationList()` 分支，所以它在页面上看起来"能用"）。
> 可用的是 **GET `browserBeanSearch`**；`searchValue` 必须用**中文分类名**（拼音检索服务端不支持：`bm` / `ry` 返回 0 条），空串只返回档案/工作流等非 HRM 分类。
> CLI 已内置此回退：`themes/e10-cli report query save` 的 `fetchBrowserBeanSearch()`；`displayType=browser` 且 `browserType` 仅为 `[{id}]` 简写时**自动升级为富对象**。

** 取值（租户 `tmxislnm9p` / 应用 1178336857624084480）**

```http
GET …/browserBeanSearch?searchValue=部门 → 命中 3 条，取 name=部门
GET …/browserBeanSearch?searchValue=人员 → 命中 3 条，取 name=人员
```

**「部门」完整富对象（ 取值）**

```json
{"id":"2005096031068185488","tenantKey":"all_teams","deleteType":0,
 "dataId":"2005096031068185488","licenseModule":"hrm","labelId":"52148",
 "title":"人事： 部门","disable":0,"systemDefault":1,"ebuliderDataBrowser":false,
 "name":"部门","module":"hrm","type":"department","groupId":"8574699142778669114"}
```

**「人员」完整富对象（ 取值）**

```json
{"id":"2005096031068185492","tenantKey":"all_teams","deleteType":0,
 "dataId":"2005096031068185492","licenseModule":"hrm","labelId":"29511",
 "title":"人事： 人员","disable":0,"systemDefault":1,"ebuliderDataBrowser":false,
 "name":"人员","module":"hrm","type":"resource","groupId":"8574699142778669114"}
```

> ⚠️ 两条的 `id` 都是**业务 id**（= `dataId`，部门 …488 / 人员 …492），**不等于** ComInfo 短 id。
> 因此校验「关联类型对不对」**不能按 id 比**，要按 `name`（人员/部门）或 `type`（resource/department）判 —— 否则会误报"不匹配"（已修 `save_query_item.js`）。
> 同一环境里还有近名分类：`部门字段`(…498) / `人员字段`(…502)，按 `name` **精确**取，勿用 `indexOf`。

**落库判据对照**

| 关联类型 | `browserTypeStr`（落库判据） | 富对象 `name` / `type` |
|---|---|---|
| 部门 | `[{"id":"HrmDepartmentComInfo"}]` | 部门 / `department` |
| 人员 | `[{"id":"HrmEmployeeComInfo"}]` | 人员 / `resource` |
| 部门全路径 | `[{"id":"HrmDepartmentAllPathComInfo"}]` | 部门字段 / `departmentDesc` |

**修复存量条件（最小侵入，已 HTTP 200）**

```python
# 1) 读取
q = POST /api/bs/edc/report/getQueryItemNew (multipart: reportId + query:'{}')
items = q["data"]["list"] # ⚠️ 在 data.list，不是 data.queryItems
# 2) 取富对象
bean = GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=人员 → name=="人员" 那条
# 3) 替换 + 同步 browserTypeStr + 保存
item["browserType"] = [bean]
item["browserTypeStr"] = json.dumps([{"id":"HrmEmployeeComInfo"}], ensure_ascii=False)
POST /api/bs/edc/report/saveQueryItem (multipart: reportId + queryItems 单对象JSON)
```

**UI 验证要点**：打开「编辑查询条件」弹窗，查 `.ui-browser-type-search-input` 的 `value`：
- `""` + 控件容器带 `is-empty` 类 → 关联类型**丢失**
- `"人员"` / `"部门"` → **正确回显** ✅

> 修复前「销售人员」`value=""`（`is-empty`）；修复后 `value="人员"` ✅

---

## 二点五、saveQueryItem 始终 500 定位（强制）

> **事故**：议题类报表搭建时，改字段/单条/空数组/`queryConfig`/`sheetId` 均 500 → 根因是**调用形态**，不是业务字段内容。

| 检查顺序 | 项 | 通过标准 |
|----------|----|----------|
| 1 | Content-Type | `multipart/form-data`，字段名 `reportId`、`queryItems` |
| 2 | `queryItems` 形态 | **单个对象** JSON；禁止数组、禁止空 `{}` |
| 3 | `conditions` | **非 null 数组**，至少 1 个 `{dataSetId, fieldId, relation}` |
| 4 | Header | `ebBusinessId` = 报表所属 **appId**；`eteamsid` + Cookie |
| 5 | 多条条件 | **多次** POST，每次一条；不要一次塞数组 |
| 6 | 对照基准 | 先 `getQueryItem` 拉已有报表一条，改 `text`/`fieldId` 再 save |

**不要**：为排 500 去开浏览器扫页（浪费）；先按上表自检。仍 500 时看响应 `msg` 是否权限/报表不存在，再问用户。

**优先 CLI**（强制）：

```bash
# 保存条件（自动默认条件级 queryType='["advance"]'，并 updateQueryType）
e10-cli report query save --report-id <id> --app-id <appId> --item queryItem.json
e10-cli report query save ... --show-where "筛选" # 仅用户点名筛选时
e10-cli report query type --report-id <id> --app-id <appId> # 只对齐报表级显示方式勾选
e10-cli report query list --report-id <id> --app-id <appId>
e10-cli report validate query --map-show-where "高级搜索"
e10-cli report validate query --validate-show-where --file item.json
# queryItem.json = 单条对象（禁止数组）；须含非空 conditions；条件级 queryType='["advance"]'
```

**不卡死（强制）**：`saveQueryItem` / `e10-cli report query save` 按形态自检并重试 **至多 1 次** 仍失败 → **立即提示用户**（可在设计器手动配查询条件）→ **继续**权限/其它布局/交付主表 → 任务收尾再自动补试 1 次。**禁止**在查询条件步骤死循环。见 `failure-cleanup-and-nonblocking-guide.md` §二。

**与布局 500 区分**：`saveReportDevInfo` 的 border `style` 须为**数字**（如 `1`）与查询无关；查询 500 优先查本节。

---

| 需求 | displayType | relation | 备注 |
|------|-------------|----------|------|
| 文本（包含） | `text` | `Contain` | 勿写 `select` |
| 文本（等于） | `text` | `Equals` | |
| **日期区间**（日/时间） | `date` / `date.ymd` | `between` | 见 §3.1 自动匹配 |
| **年月/年** | `date.ym` / `date` | `between` | 见 §3.1 |
| 下拉 | `select` | `Equals` | **必须**自动拉选项写入 `selectOptions`（§3.2） |
| 数字范围 | `number` | 默认 | |
| 人员浏览按钮 | `browser` | `Equals` | 人员类字段 |

**日期 displayType 与字段 format**

| 数据集字段 format | 查询条件 displayType |
|-------------------|----------------------|
| `yyyy-MM-dd`（及带时分秒） | `date.ymd` |
| `yyyy-MM` | `date.ym` |
| `yyyy` / 仅「年」 | `date` |
| 其他日期 | `date` |

首条查询条件可设 `advancedSearchType: "openCondition"`（如集团军默认展开）。

---

### 3.1 查询条件类型自动匹配（强制）

> Agent 配置 / 修复查询条件时，**禁止**一律写成 `text`。必须按 **条件显示名 + 数据集字段类型/format** 自行判断。

**判定顺序**（命中即停）：

| 优先级 | 信号（名称或字段元数据） | displayType | relation | 设计器形态 |
|--------|--------------------------|-------------|----------|------------|
| 1 | 名称含「年月」；或 format=`yyyy-MM` | `date.ym` | `between` | 年月区间 |
| 2 | 名称含「年份」「年度」或纯「年」；format=`yyyy` | `date` | `between` | 日期（年） |
| 3 | 名称含「日期」「时间」「时段」「期间」；或 `fieldType`/`originFieldType` ∈ Date/DateTime/Time/datetime | `date.ymd`（format 非 yyyy-MM 时）或 `date` | **`between`** | **日期区间** |
| 4 | 人员 / Employee / 浏览按钮字段 | `browser` | `Equals` | 人员 |
| 5 | **Select / 下拉框 / Check**（`compType`/`type`/`originFieldType` 为 Select）或需求明确下拉 | `select` | `Equals` | 下拉（**§3.2 必拉选项**） |
| 6 | 其他 | `text` | `Contain`（模糊）或 `Equals` | 文本 |

**硬约束**

1. 日期/时间类 **必须** `relation: "between"`，**禁止** `Equals` + `displayType: text`（事故：签订日期被配成文本等于）。
2. 判定依据优先：`fieldsAndOriginFields` 的 `fieldType` / `originFieldType` / `config.format`；名称作辅助（如条件叫「签订日期」字段叫「合同签订日期」）。
3. 写成日期区间时同步带齐 §四：`filterParam.enableOption=true`、21 项 `dataOptions`、`selectOptions=[]`。
4. **`displayType: select` 时禁止 `selectOptions: []`** — 必须按 §3.2 按匹配字段自动获取选项（事故：供应商等级下拉无选项）。
5. 回读 `getQueryItem`：核对 `displayType` + `conditions[0].relation` +（下拉时）`selectOptions.length > 0` 且 `selectKey`/`selectValue` 方向正确。
6. **定点场景**：用户只点一条条件 → 只改该条，禁止重配全部查询（`targeted-fix-guide.md`）。

---

### 3.2 下拉查询条件：按匹配字段自动获取选项（强制）

> **事故**：报表「供应商-1」`1312703681350901760`，「供应商等级」已是 `displayType: select`，但 `selectOptions: []` → 预览/高级搜索无选项映射。

当判定为下拉（§3.1 优先级 5）或用户要求下拉时：

1. 从 `conditions[0].fieldId` 解析三段 fieldKey：`{dataSetId}.{sourceId}.{fieldName}`
 - `fieldName` 在报表内多为 `field_{雪花ID}`（绑定 fieldsKey）
 - **取选项时** `fieldName` 参数必须用 **裸雪花 ID**（去掉 `field_` 前缀）
2. 调用：

```
GET /api/ebuilder/form/ds/options
 ?sourceType=FORM
 &objId={sourceId}
 &fieldName={裸雪花ID} ← 禁止传 field_xxx（会返回空数组）
```

`FORM` 无数据时可再试 `sourceType=LOGIC`。也可用 `ds/fields` 里该字段 `config.options`（`name` + `valueKey`/`value`）作为兜底。

3. 映射写入 `selectOptions` / `selectOptionsStr`（**键值方向勿反**）：

| 字段 | 含义 | 示例 |
|------|------|------|
| `selectKey` | **选项值 / ID**（过滤用） | `"864407987151323141"` |
| `selectValue` | **显示名称** | `"准入供应商"` |
| `id` | 同 `selectKey` | `"864407987151323141"` |

```javascript
// ds/options → saveQueryItem（事故：曾把名称写进 selectKey、ID 写进 selectValue）
selectOptions = data
 .filter(o => String(o.archive ?? '0') !== '1')
 .map(o => ({
 selectKey: String(o.id), // 数值 / 选项 ID
 selectValue: o.name, // 名称
 id: String(o.id),
 }));
```

4. `relation` 用 `Equals`；`showWhere` 仍遵守 §2.1。
5. **禁止**：只设 `displayType: select` 却留下空 `selectOptions`；**禁止**用带 `field_` 前缀调 `/ds/options` 后误判「字段无选项」。

```javascript
async function fetchSelectOptionsForQuery(sourceId, fieldNameFromKey) {
 const bare = String(fieldNameFromKey).replace(/^field_/, '');
 const r = await get('/api/ebuilder/form/ds/options', {
 sourceType: 'FORM', objId: sourceId, fieldName: bare,
 });
 if (!r.data?.length) throw new Error(`select options empty for ${bare}`);
 return r.data.filter(o => String(o.archive ?? '0') !== '1')
 .map(o => ({ selectKey: String(o.id), selectValue: o.name, id: String(o.id) }));
}
```

```javascript
function inferQueryDisplay(text, fieldMeta) {
 const name = `${text||''} ${fieldMeta?.text||''}`;
 const ft = String(fieldMeta?.fieldType||'').toLowerCase();
 const oft = String(fieldMeta?.originFieldType||'').toLowerCase();
 const fmt = String(fieldMeta?.config?.format || fieldMeta?.format || '');
 if (/年月/.test(name) || fmt === 'yyyy-MM')
 return { displayType: 'date.ym', relation: 'between' };
 if (/年份|^年$|年度/.test(name) || fmt === 'yyyy')
 return { displayType: 'date', relation: 'between' };
 if (/日期|时间|时段|期间/.test(name) ||
 ['date','datetime','time','timestamp'].includes(ft) ||
 ['date','datetime','time'].includes(oft))
 return { displayType: fmt.startsWith('yyyy-MM-dd') || !fmt ? 'date.ymd' : 'date',
 relation: 'between' };
 return { displayType: 'text', relation: 'Contain' };
}
```

---

## 四、日期区间：快捷选项（21 项）

> 明细 catalog 见 `date-range-query-reference.md` · 快照 `outputs/join_date_filterparam.json`

设计器手动 save 后的**正确形态**（勿用旧版 15 项数字码 + 9 项 selectOptions）：

| 字段 | 正确值 |
|------|--------|
| `selectOptions` | **`[]`** |
| `filterParam.enableOption` | **`true`** |
| `filterParam.isTile` | **`true`** |
| `filterParam.dataOptions` | **21 行**，`id` = `selectValue`（camelCase，如 `day3`、`thisMonth`） |
| `filterParam.optionTile` | **`{}`** |
| `filterParam.dateSelectDefaultValue` | **`""`（空）** |

**错误做法**：写入 `filterParam.dateSelectDefaultValue: "thisMonth"` 或填满 `optionTile` — 设计器齿轮菜单往往**只剩「自定义」**。

```python
# 见 apply_ebu_from_xlsx.py → _default_date_filter_param()
```

---

## 五、日期区间：系统参数默认值（设计器「自定义」）

默认值**不是** `dateSelectDefaultValue`，而是顶层：

| 字段 | 说明 |
|------|------|
| `defaultValueType` | **`"custom"`** |
| `defaultValue` | JSON **字符串**，形如 `'["{thismonth}",""]'` |

运行时由 `SystemVariableUtil` + `DynamicParamsBuilder` 解析；`getQueryItem` 回读的 `handleDefaultValue` 为解析后结果。

### 5.1 已验证系统参数

| 场景 | defaultValue | handleDefaultValue 示例 |
|------|--------------|-------------------------|
| **本月** | `["{thismonth}",""]` | `["2026-08-01,2026-08-31",""]` |
| **今天** | `["{date}","{date}"]` | `["2026-08-19","2026-08-19"]` |
| **本周** | `["{thisweek}",""]` | `["2026-08-17,2026-08-23",""]` |
| **今年** | `["{thisyear}",""]` | `["2026-01-01,2026-12-31",""]` |
| **当前用户姓名** | `["{lastname}",""]` | `["张三",""]`（高级搜索文本等于） |
| **当前用户 ID** | 数据集筛选 **`eq`** + `{userid}` | 人员字段「创建者 = 当前登录人员」 |

**注意**

- `{today}` **无效**（不会被解析，占位符会被清空）；「今天」用 **`{date}`**。
- `{currmonth}` 无效；「本月」用 **`{thismonth}`**。
- 区间型参数（本月/本周）写在**数组首项**；今天需起止同一天则写 **`["{date}","{date}"]`**。
- `defaultValue` 必须是 **JSON 数组字符串**，禁止裸写 `"3"` 等（会导致 `getQueryItem` 500）。

### 5.2 设计器操作对应

1. 默认值类型 → **自定义**
2. 默认值 → 填 `{thismonth}`、`{date}` 等（设计器存为 JSON 数组）
3. 日期区间 + **启用选项** ON → 21 项快捷按钮（§四）

---

## 六、EBU 报表示例（三条高级搜索 + 数据集行级筛选）

报表 `1304979556231593985` · 数据集 EBU团队 `1304979556231593994`

| 显示名称 | fieldKey 末段 | displayType | relation | 默认值 | queryType |
|----------|---------------|-------------|----------|--------|-----------|
| 集团军 | `field_1299763447342276612` | `text` | `Contain` | 无 | `["advance"]` |
| 入职时间 | `field_1299763447342276619` | `date.ymd` | `between` | `["{thismonth}",""]` | `["advance"]` |
| EBU成立时间 | `field_1299763447342276620` | `date.ym` | `between` | `["{date}","{date}"]` | `["advance"]` |

> 三条均为「高级搜索」显示方式 → 条件级 `queryType` 一律 `'["advance"]'`（见 §2.1）。
> 「高级搜索显示形式」（报表级、`saveQueryConfig` → `{"advancedSearchType":"openCondition"}`）是**报表级**开关，与条件级显示方式共享 `queryType` 覆盖关系（§2.1.3）。

---

## 七、数据集筛选（设计器左侧 · 行级权限）

> **完整规范已独立成文**：`dataset-query-filter-guide.md`（func 对照、字段对比、日期 format、AND/OR、EBU 参考样本、验证清单）。
> 本节仅保留与高级搜索的边界说明。

**与高级搜索不同**：设计器左侧数据集右键「筛选条件」走 **`queryInfoSave` / `queryInfoGet`**（`conditionData` + `otherData`），**不是** `saveQueryItem`。

| API | 参数 |
|-----|------|
| 保存 | `POST /api/bs/edc/dataset/queryInfoSave` → `datasetId`, `filterData`, `otherData` |
| 读取 | `GET /api/bs/edc/dataset/queryInfoGet` → `datasetId` |

**快速对照**

| 需求入口 | 读哪份文档 |
|----------|-----------|
| 页面 → 查询设置（高级搜索） | 本文 §二–§六 |
| 左侧数据集 → 筛选条件 | **`dataset-query-filter-guide.md`** |
| 单元格自定义筛选 / datasetFilter | `cross-dataset-filter-guide.md` |

代码：`本地工作目录` → `ensure_team_dataset_filter()` / `ensure_contract_dataset_filter()`；执行 `python 本地工作目录`。

---

## 八、验证清单

写入后 `getQueryItem` 回读：

**形态**

- [ ] **调用**：multipart + `queryItems`=**单对象**（非数组）；`conditions` 非 null
- [ ] 顶层 `filterType: "default"`；`conditions[]` 无 `filterType`
- [ ] 顶层 `dataSetId` / `name` 为 `null`；`nameIndex: "0"`；`sqlOptions: {}`
- [ ] **`queryType` 为 JSON 数组字符串**：`'["advance"]'`（高级搜索）或 `'["filter"]'`（筛选），可双选 `'["advance","filter"]'`（§2.1）；**必须以 `[` 开头**
- [ ] **回显自检**：落库为长码 `"advancedSearch"` → 设计器「显示方式」**必不勾选**（落库错误，改数组即修复）；不要解释为平台缺陷
- [ ] `asNameIndex` 唯一且 > 0；与 `showOrder` 一致
- [ ] `fieldOptions` 与 `conditions` 字段一致

**浏览按钮（人员 / 部门）**

- [ ] `displayType: "browser"` 且 **`browserTypeStr` 非空**（§2.1.2）
- [ ] 字段 `originFieldType=Employee` → `HrmEmployeeComInfo`
- [ ] 字段 `originFieldType=Department` → `HrmDepartmentComInfo`
- [ ] `browserTypeStr` 不得为 `"[]"`（关联类型丢失 → 退回「人员」）
- [ ] 若要求 UI 正确回显显示名，`browserType` 用富对象（含 `name`/`type`），非 `[{"id"}]` 简写

**文本**

- [ ] `displayType: "text"`（非 `select`）

**下拉**

- [ ] `displayType: "select"` 且 `selectOptions.length > 0`
- [ ] 选项来自匹配字段的 `/ds/options`（`fieldName` 为裸 ID，见 §3.2）
- [ ] 每项：`selectKey`=选项 ID（数值）、`selectValue`=显示名称（勿写反）

**日期选项**

- [ ] `enableOption=true`、`isTile=true`、`dataOptions` 21 项、`selectOptions=[]`、`optionTile={}`

**日期默认值**

- [ ] `defaultValueType: "custom"`（有默认值时）
- [ ] `handleDefaultValue` 非空且符合预期（如本月区间、今天同一天）
- [ ] **未**依赖 `filterParam.dateSelectDefaultValue`

**工具**

- [ ] `本地工作目录` 导出快照对比
- [ ] 设计器刷新：齿轮菜单 21 项、默认值回显、删一条不影响其他条件

---

## 八、相关文档

| 文件 | 用途 |
|------|------|
| **`dataset-query-filter-guide.md`** | **左侧数据集筛选**（queryInfoSave 完整规范） |
| **`cell-transform-guide.md`** | **`browserType` 关联类型预设**（人员/部门 ComInfo id） |
| **`event-hreflink-guide.md`** | 事件链接传 `{searchfield00x}` / 单元格坐标 |
| `date-range-query-reference.md` | 21 项 dataOptions catalog |
| `cross-dataset-filter-guide.md` | datasetFilter / customFilterField |
| `report-building-guide.md` §6 | 设计器操作步骤 |
| `report-config-schema.md` §五 | Schema 摘要 |
| `SKILL.md` §6.3–§6.4 | Agent 步骤入口 |
| `outputs/join_date_filterparam.json` | filterParam 参考样本 |
| `本地工作目录` | 生成/修复实现 |
