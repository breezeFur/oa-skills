# 报表搭建完成交付规范（强制）

> **冷启动**：开场只读 `cold-start-scan-guide.md`；交链后禁止续跑（含 verify/HTML）。
> **适用范围**：凡通过本 Skill 完成「线上建表 / 布局落库」或「需求分析」的任务。
> **优先级**：高于 Agent 默认收尾习惯。

---

## 搭完即停（最高 · 防「报表好了 Agent 还在忙」）

`saveReportDevInfo`（或等价落库）成功，且对话中已给出 **设计器地址** 后：

1. **本轮任务立即结束** —— 停止调用工具、停止读文档、停止写脚本。
2. **禁止**再跑：`verify_*`、预聚合、HTML 手册、需求分析模板、配置 JSON 检测、再 save、回读全表、截图比对、通读 knowledge-base。
3. **禁止**在交链后再开「后台继续」长链（旧文「可后置校验」已废止为默认行为）。
4. 硬失败才允许修；软告警 **最多补丁 1 次** 后仍须结束并告知用户。
5. 单步 API 最多重试 1 次，**不得**叠成无限交付轮。

---

## 模式分流

| 用户意图 | 判定 | Agent 做什么 | **禁止** |
|----------|------|--------------|----------|
| **A. 直接搭建**（默认） | 「搭建」「创建报表」「生成报表」 | 定源 → 落库 → **交设计器地址 → 停** | 分析模板、配置检测、HTML、verify 环 |
| **B. 需求分析** | 「需求分析」「搭建指导」「图示」 | 按 `report-requirement-analysis-template.md` | 未点名却搭表；未点名却 HTML |
| **C. 分析 + 搭表** | 同时含 B 与 A | 短分析（若需要）→ A → **停** | 把 HTML/verify 当完成条件 |

**HTML 手册**：非强制；仅用户明确要「HTML/指导文档」时生成，且不得拖延首链、不得在交链后自动生成。

**已移除能力**：测试用例生成、功能原型图 —— 包内无对应脚本/指南，禁止查找 `generate_test_case` / `prototype-design` / 测试用例模板。

---

## 〇、先交地址（强制）

布局落库成功并拿到稳定 `reportId` 后，**立即**输出 §一 模板，然后 **结束**。

**禁止**为下列事项拖延或续跑：视觉比对、多轮 `getReportDevInfo`、SpreadJS 黑盒、HTML、verify、预聚合、需求分析、配置检测、「再确认一下」。

### 与门禁

- **硬失败** → 不交假链；删空壳（`failure-cleanup-and-nonblocking-guide.md`）。
- **会话终止未交付** → `cleanup shells`。
- **附属失败**（如查询条件）→ 提示后 **仍交主表链接并结束**；最多补试 1 次。

---

## 一、对话收尾（模式 A）

```markdown
## 应用信息
- **应用名称**：…
- **应用 ID**：…
- **应用地址**：…

## 报表信息
- **报表名称**：…
- **报表 ID**：…
- **设计器地址**：…
```

**禁止**附加：搭建指导手册段、changed files、verify 报告（除非用户本轮点名）。

---

## 二、HTML（按需 · 非强制）

仅用户明确要求时：

```bash
python （未移植，需要时另议） --config <guide_config.json> --output <输出路径>.html
```

建议：`outputs/<reportId>/《报表名称》·搭建配置指导.html`

---

## 三、直接搭建跳过

模式 A **禁止**：分析模板 8 章节、ReportProps 整包检测、`build_guide_html`、交链后 verify/预聚合环。

最小路径：`auth ready` → 定源 → 建壳 → addDataset → 布局 → save → **交链停**。

---

## 四、自检清单

- [ ] 含应用三要素 + 报表三要素（含设计器地址）
- [ ] 交链后已停止（无续跑工具）
- [ ] 未主动生成 HTML / 测例 / 原型
- [ ] 未展示 changed files

---

## 五、相关文档

- `api-report-build-fast-path.md`
- `session-build-performance-guide.md`
- `report-requirement-analysis-template.md`（仅分析意图）
- `failure-cleanup-and-nonblocking-guide.md`
