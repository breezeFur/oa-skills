# 默认表头样式（强制分流）

> **适用**：新建 / `edc-report build spec` 搭表时的标题行、列表字段表头行外观。  
> **CLI**：`edc-report validate style --list` / `--inline '{...}'`  
> **实现**：`scripts/default_header_style.js` → `build_from_spec.js` 分层套用。

---

## 〇、何时用默认、何时听用户（强制）

| 用户输入 | 行为 |
|----------|------|
| **未提样式**、**未给效果图/截图配色** | 自动套 **默认表头样式**（本页 §一）；正文保持素色 |
| **明确样式**（颜色/字体/主题/「表头蓝色」等） | **完全按用户**；写入 `spec.style` / `titleStyle` / `headerStyle`；**不再**叠默认蓝灰头 |
| **有效果图 / 原型截图** | 从效果图提取配色写入 spec，并设 `styleFromMockup: true`；**禁止**再盖默认头 |
| `applyDefaultHeader: false` 或 `stylePreset: "plain"` | 强制素色，不要装饰表头 |

**禁止**：用户已指定样式或已给效果图时，仍强行刷默认 `#B6D6FF` / `#E6E6E6`。  
**禁止**：定点改已有报表时，未点名「改样式」却整表套默认头（见 `user-request-scope-only-guide.md`）。

---

## 一、默认值（与 assets 列表模板一致）

| 层级 | 用途 | backColor | foreColor | font | 对齐 |
|------|------|-----------|-----------|------|------|
| **title** | `layout.title` 合并标题行 | `#B6D6FF` | `#000000` | 微软雅黑 **14** 加粗 | 居中 |
| **header** | 列名 Const 表头行 | `#E6E6E6` | `#000000` | 微软雅黑 **12** 加粗 | 居中 |
| **body** | Field / 公式数据格 | `#FFFFFF` | `#333333` | 微软雅黑 **12** | 居左 |

边框默认 `#CCCCCC`（标题边略深 `#99B8D9`）。字号须落在设计器目录（无 10 号）。

---

## 二、spec 字段

```json
{
  "styleFromMockup": false,
  "applyDefaultHeader": true,
  "style": { },
  "titleStyle": { },
  "headerStyle": { },
  "bodyStyle": { }
}
```

| 字段 | 说明 |
|------|------|
| （均省略） | → `source=default-header`，套 §一 |
| `style` / 任一层 `*Style` | → `source=user`，用户优先 |
| `styleFromMockup: true` | → `source=user`，禁止默认头 |
| `applyDefaultHeader: false` | → `source=plain` |

`build_from_spec` 回读/日志含 `styleSource`。

---

## 三、Agent 话术

- 未指定时：落库后可一句带过「已套用默认表头（蓝标题 + 灰列头）；若要改配色请说明」。  
- 有指定/效果图：不要提默认头，只按用户视觉落地。

---

## 四、相关

- `spec-build-schema.md` §三  
- `cell-config-echo-guide.md`（同款样式复用、字号目录）  
- `assets/template-list-report.json`（同色脚手架）
