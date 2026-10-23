# 编辑回显指南

编辑已有数据时，需要将表单数据加载回表单控件中。`getSimpleData` 对特殊类型统一返回 ID，可直接用于表单回显，但选择器组件需要额外提取 name 信息。

---

## 核心流程

### 第一步：加载时同时获取两份数据

```js
// loadData 中用 Promise.all 同时获取两份数据
function loadData() {
  Promise.all([
    getSimpleData(OBJ_ID, USER_ID),
    getAllData(OBJ_ID, USER_ID),
  ]).then(function ([simpleRows, allRows]) {
    setData(withDisplayNames(simpleRows, statusMap));
    setRawData(allRows);  // 保存原始数据用于编辑回显
  });
}
```

### 第二步：编辑按钮点击时回填表单

```js
function handleEdit(rowData) {
  var dataId = rowData._raw.id;  // Table 回调的 rowData 有 _raw，不是 getSimpleData 返回的行

  // 1. 从 rawData(原始接口数据) 中查找对应记录
  var rawEntry = rawData.find(function (r) {
    return r.mainTable && r.mainTable.id && r.mainTable.id.fieldValue === dataId;
  });

  // 2. 用 getSimpleData 的值填充表单（所有特殊字段已是 ID，可直接用）
  var editForm = {};
  Object.keys(emptyForm).forEach(function (key) {
    editForm[key] = rowData._raw[key] || '';
  });

  // 3. 从 rawEntry.mainTable 中提取 name 信息（选择器组件需要 [{id, name}] 格式）
  var newSelectedPerson = [];
  var newSelectedDept = [];
  var newUploadedFiles = [];

  if (rawEntry && rawEntry.mainTable) {
    Object.keys(rawEntry.mainTable).forEach(function (key) {
      var val = rawEntry.mainTable[key];
      if (!val) return;

      if (Array.isArray(val) && val.length > 0) {
        var fieldId = val[0].fieldId;
        var fieldType = val[0].fieldType;

        if (fieldId === F.person) {
          newSelectedPerson = val.map(function (v) {
            return { id: v.fieldOptionId, name: v.fieldOptionName };
          });
        } else if (fieldId === F.dept) {
          newSelectedDept = val.map(function (v) {
            return { id: v.fieldOptionId, name: v.fieldOptionName };
          });
        } else if (fieldId === F.attachment) {
          newUploadedFiles = val.map(function (v) {
            return { fileid: v.fieldOptionId, name: v.fieldOptionName };
          });
        } else if (fieldType === 'Select' || fieldType === 'RadioBox' || fieldType === 'CheckBox') {
          // getSimpleData 已返回 ID，此处从 rawEntry 再次确认（多选时覆盖）
          editForm[fieldId] = val.map(function (v) { return v.fieldOptionId; }).join(',');
        }
      }
    });
  }

  // 4. 一次性设置所有状态
  setForm(editForm);
  setSelectedPerson(newSelectedPerson);
  setSelectedDept(newSelectedDept);
  setUploadedFiles(newUploadedFiles);
  setModalVisible(true);
}
```

---

## 关键点总结

| 要点 | 说明 |
|------|------|
| `getAllData` 返回结构中 `id` 在 `mainTable` 内部 | 查找原始记录必须是 `r.mainTable.id.fieldValue`，**不能**写成 `r.id.fieldValue` |
| `Browser`(人员/部门) 的 `value` | 需要 `[{id, name}]` 格式 |
| `Upload`(附件) 的 `data` | 需要 `[{fileid, name}]` 格式 |
| `Select` 下拉框的 `value` | 需要匹配 `fieldOptionId`（即 `opt.valueKey`），不能是显示名 |
| Table 的 `onRowClick` 回调 | `rowData._raw` 引用了原始数据行，`rowData._raw.id` 是 dataId |
| 表单字段值来源 | 从 `getSimpleData` 取值（已是 ID），选择器显示名从 `getAllData` 提取 |

---

## getSimpleData vs getAllData 结构对比

### getSimpleData 返回（扁平，纯 ID，用于写入）

```json
[
  {
    "1290462231772995585": "张三",                   // Text：直接就是值
    "1290462231772995586": "1290462231772995612",    // Select：选项 ID
    "1290462231772995589": "2765550234448235905",    // Employee：用户 ID
    "id": "1290469928435908609"
  }
]
```

所有特殊字段统一返回 `fieldOptionId`（纯 ID），直接用于 `formToSave`。

### getAllData 返回（含名称，用于展示/回显）

```json
{
  "mainTable": {
    "sjhfa391": {                                     // ← key 是随机哈希，不是 fieldId！
      "fieldId": "1290462231772995590",
      "fieldType": "Text",
      "fieldValue": "13800138000"
    },
    "zssj98f9d": [{                                   // ← Employee 是数组！
      "fieldId": "1290462231772995589",
      "fieldType": "Employee",
      "fieldOptionId": "2765550234448235905",
      "fieldOptionName": "张三"
    }],
    "bm1d630": [{                                     // ← Select 也是数组！
      "fieldId": "1290462231772995586",
      "fieldType": "Select",
      "fieldOptionId": "1290462231772995612",
      "fieldOptionName": "技术部"
    }],
    "id": {                                           // ← 只有 id 的 key 是 "id"
      "fieldId": "5",
      "fieldType": "Text",
      "fieldValue": "1290469928435908609"
    }
  }
}
```

### 三个关键规则

| 规则 | 说明 |
|------|------|
| **key 是随机哈希** | `mainTable` 的 key（如 `sjhfa391`）是随机字符串，**不能**用 `mainTable[fieldId]` 直接取值 |
| **只能用 fieldId 匹配** | 必须遍历 `Object.values(mainTable)`，通过 `val.fieldId` 或 `val[0].fieldId` 匹配目标字段 |
| **数组 vs 对象** | Employee / Select / FileComponent / RadioBox / CheckBox → **数组** `[{...}]`；Text / Number / DateComponent → **对象** `{...}` |
| **只有 id 是 deterministic** | 数据行 ID 的 key 固定为 `"id"`，可直接用 `mainTable.id.fieldValue` |

### 字段值 → 组件 props 映射表

> 这是整个编辑回显最容易出错的一步。getAllData 中的字段形状各不相同，映射到组件 props 的方式也不同。

| 字段类型 | getAllData 中的形状 | 目标组件 | 需要的 props 格式 | 映射方式 |
|---------|-------------------|---------|-----------------|---------|
| Employee | `[{fieldOptionId, fieldOptionName}]` | `Browser` | `value={[{id, name}]}` | `v.fieldOptionId → id`，`v.fieldOptionName → name` |
| Department | `[{fieldOptionId, fieldOptionName}]` | `Browser` | `value={[{id, name}]}` | 同上 |
| FileComponent | `[{fieldOptionId, fieldOptionName}]` | `Upload` | `data={[{fileid, name}]}` | `v.fieldOptionId → fileid`，`v.fieldOptionName → name` |
| Select（单选） | `[{fieldOptionId}]` | `<select>` | `value="fieldOptionId"` | 取 `val[0].fieldOptionId` |
| Select（多选） | `[{...}, {...}]` → 多个 | `<select multiple>` | 逗号分隔串 | `val.map(...).join(',')` |
| Text / Number | `{fieldValue}` | `<input>` | `value="fieldValue"` | 直接用 `getSimpleData` 的值 |

### 正确的字段提取方式

```js
// 查找 mainTable 中 fieldId 匹配的字段值
function findField(mainTable, targetFieldId) {
  var keys = Object.keys(mainTable);
  for (var i = 0; i < keys.length; i++) {
    var val = mainTable[keys[i]];
    if (!val) continue;
    // 数组类型（Employee/Select 等）取 val[0].fieldId
    if (Array.isArray(val) && val.length > 0 && val[0].fieldId === targetFieldId) {
      return val;
    }
    // 普通类型（Text/DateComponent 等）取 val.fieldId
    if (!Array.isArray(val) && val.fieldId === targetFieldId) {
      return val;
    }
  }
  return null;
}
```
