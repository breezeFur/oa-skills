# 表单数据操作指南

Ebuilder 项目没有后端，但可以通过读写 Ebuilder 的表单来实现数据交互。所有 CRUD 接口已实现在 `/api/formApi.js` 中。

> 应用已注册的表单信息及字段用 `e10-cli form read <objId> --app-id <appId> --out fields.json` 导出（机器可读 JSON），为空说明还没注册。

---

## 〇、非对称设计（读写分离）

**这是整份指南最核心的概念，每次写表单页面之前必须理解。**

`getSimpleData` 对所有特殊类型（Select / RadioBox / CheckBox / Employee / Department / FileComponent）**统一返回 ID**（`fieldOptionId`）。好处是写入简单——直接拿 ID 原样写入，不用做任何转换。代价是展示麻烦——ID 是长数字，用户完全看不懂。

```
写入路径（简单）：getSimpleData → form 直接用 ID → saveFormData/updateFormData
展示路径（复杂）：getSimpleData → ID → 映射为名称 → 表格渲染
```

**不同字段类型，名称来源不同**：

| 字段类型 | getSimpleData 返回值 | 名称来源 |
|---------|---------------------|---------|
| 普通文本/数字/日期 | `"名称"` / `123` / `"2026-01-01"` | 直接展示 |
| Select / RadioBox / CheckBox | `"1283421826353889337"`（ID） | `getFieldOptions` 映射 `valueKey → name` |
| Employee / Department | `"5140559860850691459"`（用户ID） | `getAllData` 提取 `fieldOptionName` |
| FileComponent | `"fileid1,fileid2"`（文件ID串） | 上传组件的 `name` 字段 |

> **铁律：表格里永远不要直接渲染 `row[字段ID]`。** 用户看到一列长数字 = 你漏掉了名称转换。

---

## 一、四个 API 的职责

| API | 职责 |
|-----|------|
| `getAllData` | 做源（含 `fieldOptionName`，用于提取名称信息） |
| `getSimpleData` | 做读写（纯 ID，不含名称） |
| `withDisplayNames` | 做展示（ID → 名称转换） |
| `getFieldOptions` | 做下拉（拿 `valueKey` + `name`） |

---

## 二、核心规则：读取用 ID，展示用名称

**最容易出错的点，每次编码前务必理解：**

`getSimpleData` 对所有特殊类型（Select/RadioBox/CheckBox/Employee/Department/FileComponent）**统一返回 ID**（`fieldOptionId`），读写一致。

> 写完代码逐条自检，90% 的 bug 都是这几个：
> 1. `if (row[roomField] === '101')` — Select 字段值是 `fieldOptionId`（长数字如 `"1283421826353889337"`），永远不等于选项名称
> 2. `{row[empField]}` 直接渲染 — Employee/Department 返回的是长数字 ID，人名需从 `getAllData` 提取 `fieldOptionName`
> 3. 表格里直接显示 `row[fieldId]` — 用户看到一列长数字。展示用 `withDisplayNames()`

- **写入保存** → 直接用 `getSimpleData` 的返回值，所有字段都是 ID，无需转换
- **表格展示** → 用 `withDisplayNames()` 把 ID 转成名称，否则用户看到的是数字

---

## 三、读取表单数据

### 3.1 getSimpleData — 获取简单格式数据

```js
import { getSimpleData } from '../api/formApi.js';
const CONFIG = {
  objId: '12556432068......',
  userId: TEAMS.currentUser.id
};
const data = await getSimpleData(CONFIG.objId, CONFIG.userId);
```

返回格式：
```js
[
  {
    "4765111450482898127": "具体的数据内容",
    "4765111450482898155": "具体的数据内容",
    "id":"1259017552222814208"  // 表单数据固有的数据ID字段，fieldId固定为"id"
  },
  {.....}
]
```

`getSimpleData` 返回的是扁平对象，字段 ID 作为 key 直接挂载在行上，**没有 `_raw` 层**。直接用 `item[字段ID]` 访问。

> 注意：Table 组件的 `onRowClick` 回调参数中会带 `_raw`（引用原始数据行），仅在编辑回显等场景通过回调参数访问，不要主动去构造 `_raw`。

### 3.2 withDisplayNames — ID → 名称转换（表格展示用）

用于在表格中把 Select/Employee/Department 等字段的 ID 转成可读名称。

推荐写法：
```js
import { getSimpleData, withDisplayNames, getFieldOptions } from '../api/formApi.js';

function TemplatePage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(function () {
    Promise.all([
      getSimpleData(CONFIG.objId, CONFIG.userId),
      // 为每个需要展示名称的 Select 字段调用 getFieldOptions
      getFieldOptions(F.status, OBJ_ID),
    ]).then(function ([rows, statusOpts]) {
      setData(withDisplayNames(rows, { [F.status]: statusOpts }));
    }).catch(function () {})
      .finally(function () { setLoading(false); });
  }, []);
  // ......
```

### 3.3 getFieldOptions — 获取选项列表

动态获取 Select/RadioBox/CheckBox 字段的可选值：

```js
import { getFieldOptions } from './api/formApi.js';
```

返回结构：
```js
[
    {
        "valueKey": "1263421826353889337",
        "name": "已入职"
    },{
        "valueKey": "1263421826353889338",
        "name": "已离职"
    }
]
```

---

## 四、字段类型对应组件

`form read --out fields.json` 导出的字段列表会告诉你每个字段的类型和 ID，有一些特殊的类型你必须选用对应的组件进行输入：

| 字段类型 | 对应组件 |
|---------|---------|
| Employee | `Browser` — 人员选择框（`module="hrm" type="resource"`） |
| Department | `Browser` — 部门选择框（`module="hrm" type="department"`） |
| FileComponent | `Upload` — 文件上传（参考 `references/components/form-Upload.md`） |

---

## 五、数据写入

### 5.1 formData 格式

**一定是字段 ID 作为 key 的格式**，字段 ID 是纯数字组成的字符串，不包含任何其他符号。必须对照 `form read --out fields.json` 导出的字段来写，不要自己编造。

```
{
  "4765111450482898127": "数据内容1",
  "4765111450482898155": "数据内容2"
}
```

### 5.2 三个写接口

**新增：**
```js
export async function saveFormData(objId, formData, userId)
```

**更新（多一个 dataId 参数）：**
```js
export async function updateFormData(objId, formData, dataId, userId)
```

**删除：**
```js
export async function deleteFormData(objId, dataId, userId)
```

### 5.3 调用方式

```js
if (editingId) {
  promise = updateFormData(OBJ_ID, formToSave, editingId, USER_ID);
} else {
  promise = saveFormData(OBJ_ID, formToSave, USER_ID);
}
```

### 5.4 写入时直接使用 form 的值（已全部为 ID）

`getSimpleData` 对所有特殊类型（Select/Employee/Department/FileComponent）统一返回 ID。编辑保存时无需跳过任何字段，`form` 中的值可直接写入。

```js
var formToSave = {};

// 所有字段统一处理，getSimpleData 已返回 ID
Object.keys(form).forEach(function (key) {
  var val = form[key];
  if (val !== '' && val !== null && val !== undefined) {
    formToSave[key] = val;
  }
});

// 用户操作选择器时用新值覆盖
if (selectedPerson.length > 0) {
  formToSave[F.person] = selectedPerson[0].id;
}
if (selectedDept.length > 0) {
  formToSave[F.dept] = selectedDept[0].id;
}
if (uploadedFiles.length > 0) {
  formToSave[F.attachment] = uploadedFiles.map(function (f) { return f.fileid; }).join(',');
}
```

---

## 六、三个高频编码错误

编写 Ebuilder 页面时，以下三个错误非常高发，生成代码前务必检查：

### 错误 1：数据访问用错层级

`getSimpleData` 返回的每一行直接用 `item[字段ID]`，**没有 `_raw` 层**。

```js
// 错误
var title = item._raw[F.title];

// 正确
var title = item[F.title];
```

### 错误 2：Select 字段用名称做判断

`getSimpleData` 对 Select/RadioBox/CheckBox 字段返回的是**选项 ID**（`fieldOptionId`，即 `valueKey`），如 `"1283421826353889337"`，不是显示名称。

```js
// 错误
if (item[F.status] === '已完成') { ... }  // 显示名称永远不匹配

// 正确
if (item[F.status] === '1283421826353889337') { ... }  // 用选项 ID
```

**表格中显示名称**请使用 `withDisplayNames()`，不要在表格列渲染时逐行查 ID。

### 错误 3：React state 直接修改

直接修改对象属性再 `setForm` 不会触发 React 重新渲染。

```js
// 错误
form[F.name] = value;
setForm(form);

// 正确
var newForm = {};
Object.keys(form).forEach(function (k) { newForm[k] = form[k]; });
newForm[F.name] = value;
setForm(newForm);
```
