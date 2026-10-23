# 条件格式（突出显示 / 数据条 / 图标集）

> **源码**：`ReportUtil.generateConditionRule`（`weaver-edc-common-report-analysis`）  
> **UI**：设计器「开始 → 条件格式」  
> **落库唯一有效点**：`fields[].conditionRule` / workbook `style.cellType.conditionRule`  
> 结构：`{ highlightDatas, lineDatas, iconDatas }`（**不是** sheet 级 `conditionalFormats`，后者不持久化）  
> **禁黑盒**：禁止下载 SpreadJS / 设计器 chunk 循环试探；见 `session-build-performance-guide.md`

---

## 〇、性能与交付（强制）

1. 写入前用 CLI 映射/校验，**禁止**反复保存探结构  
2. 布局已落库 → **先交设计器地址**，条件格式校验可后置补丁  
3. 映射不到 → **提示用户确认**，不要开逆向循环

---

## 一、硬约束（突出显示）

1. **只写平台已识别的 `relation`**。未知值（如 `highlight:between`）会被引擎**静默跳过**。
2. **区间必须用一条 `highlight:interval`**；禁止拆成两条 `greater`+`less` 冒充 AND（多规则是 OR）。
3. **配置前先映射再写入**；映射不到或冲突 → **提示用户确认**。

---

## 二、突出显示 `relation` 白名单

| 中文 | `relation` | value |
|------|------------|-------|
| 大于 | `highlight:greater` | value1 |
| 大于等于 | `highlight:greaterAndEquals` | value1 |
| 小于 | `highlight:less` | value1 |
| 小于等于 | `highlight:lessAndEquals` | value1 |
| 等于 | `highlight:equals` | value1 |
| 不等于 | `highlight:noEquals` | value1 |
| **介于** | **`highlight:interval`** | value1=下界，value2=上界 |
| 文本包含 | `highlight:include` | value1 |
| 发生日期 | `highlight:happenDate` | value1 |
| 重复值 | `highlight:sameValue` | — |

**禁止**：`highlight:between` → 改 `interval`；缩写 `gt/lte` 等。

### 自然语言 → 突出显示

| 说法 | 映射 |
|------|------|
| 大于 N | `greater` |
| 介于 1 和 5 / 1–5 | **一条** `interval` |
| 文本包含 xx | `include` |

多档示例：「>0 红；>5 蓝」→ `interval(1,5)` 红 + `greater(5)` 蓝粗。

---

## 三、数据条（lineDatas）

落库：**`lineDatas`**（引擎 `ruleType=databar`）。

```json
{
  "lineDatas": [
    {
      "index": 0,
      "leftType": "min",
      "leftValue": "",
      "rightType": "max",
      "rightValue": "",
      "gradient": "gradient",
      "color": "#6495ED",
      "negativeFillColor": "#FF0000"
    }
  ]
}
```

| 字段 | 取值 |
|------|------|
| `leftType`/`rightType` | `min`/`max`/`custom` |
| `gradient` | `gradient`（渐变）\| `solid`（实心） |
| `color` / `negativeFillColor` | 正/负色 |

CLI：`edc-report validate condition --map "数据条"` / `--map "实心数据条"`

---

## 四、图标集（iconDatas）

落库：**`iconDatas`**（引擎 `ruleType=iconset`；UI 文案偶写 iconSets，JSON **必须** `iconDatas`）。

```json
{
  "iconDatas": [
    {
      "index": 0,
      "iconSetType": "0",
      "iconCriteria": [
        { "iconValue": "67", "isGreaterThanOrEqualTo": true, "iconValueType": 1 },
        { "iconValue": "33", "isGreaterThanOrEqualTo": true, "iconValueType": 1 }
      ]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `iconSetType` | **字符串**；常用 `"0"`/`"1"`/`"2"`/`"3"`（方向/形状/标记/等级类） |
| `iconCriteria` | 分档阈值 |

CLI：`edc-report validate condition --map "图标集"`

---

## 五、不支持 / 冲突

映射不到 → 明确告知并请用户确认；禁止静默、禁止黑盒下载。  
多条 greater 样式不同 → 提示重叠冲突，建议 interval + greater。

---

## 六、写入清单

1. `conditionRule = { highlightDatas?, lineDatas?, iconDatas? }` → fields + workbook cellType  
2. save 成功 → **先交设计器 URL**  
3. 可选 `verify condition` 后置

---

## 七、CLI

```bash
edc-report validate condition --file rule.json
edc-report validate condition --map "介于 1 5"
edc-report validate condition --map "数据条"
edc-report validate condition --map "图标集"
edc-report verify condition <reportId> [appId]
```

脚本：`scripts/validate_condition_format.js`。
