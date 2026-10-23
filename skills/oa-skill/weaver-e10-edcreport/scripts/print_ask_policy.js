'use strict';
/**
 * edc-report policy ask — 两条「必须让用户指定」规则（强制 · 2026-09-11）
 *
 * 规则 A：需求字段在当前数据集表单中**找不到** → 提示用户选取指定字段
 * 规则 B：需求**未指明表** 或 检索**非完全精准匹配** → 提示用户选取指定表
 *
 * 细则：references/spec-build-schema.md §1.1/§2.1
 *       references/field-bind-exact-match-guide.md §2.0
 */
const text = `
════════════════════════════════════════════════════════════
 edc-report 政策 · 必须让用户指定（强制 · 2 条）
════════════════════════════════════════════════════════════

核心原则：**不确定 → 停下来问用户；不允许替用户猜，也不允许先建表再回滚。**

────────────────────────────────────────────────────────────
 规则 A · 需求字段找不到 → 让用户指定字段
────────────────────────────────────────────────────────────
触发：需求列出的字段在当前数据集表单（fieldsKey/fieldsBySource）中**无精确命中**。
      「无精确命中」= 不满足任一条：
       1) 显式 fieldName/fieldMap 命中 fieldsKey.name
       2) 列标题 === fieldsKey.text/showName（归一化后精确相等）
       3) column.field === fieldsKey.text/showName
      另含：显式字段与列文案不一致（display_mismatch）而用户未确认。

禁止：模糊自动绑定；回退系统字段（name/id/create_time/creator…）；
      把「找不到」当成「换个相近字段顶上」。

行为：build spec **exit 4**，且**不创建报表**（落库后才发现的，删除本表）。
输出（原样交用户挑）：
  · unmatched[]：{ column, reason, message, prompt, candidates }
  · allFields[]：该表单全量字段 { name, text, system }
  · next.specFields.fieldMap：{ "<列标题>": "<字段显示名 | field_雪花 | 系统字段名>" }

reason 取值：
  no_exact_match      —— 无精确命中（字段在表单里不存在/名称不符）
  explicit_not_found  —— 显式指定的字段名不在该数据源
  display_mismatch    —— 能绑到，但字段真实显示名 ≠ 列文案，需 --field-confirmed

用户指定后复跑：
  edc-report build spec --spec <spec.json> --field-confirmed "党组织,姓名"
  （或 spec.fieldMap / spec.fieldConfirmed）

────────────────────────────────────────────────────────────
 规则 B · 表没指明 / 不是完全精准匹配 → 让用户指定表
────────────────────────────────────────────────────────────
触发（任一）：
  1) form_unspecified —— 需求**没指出具体表**（只给业务关键词，或 spec 无 form/sourceId）
  2) form_fuzzy_match —— 应用内命中但**非完全精准**（模糊包含、多条同名/近名）
  3) form_not_found   —— 应用内**未命中**

禁止：按关键词自行挑一张表；用「最像的」顶上；
      先建壳/试探表再判断对不对。

行为：build spec / find form **exit 3**，**不建表**。
输出：candidates[]（应用内候选，按相似度排序）+ confirmPrompt
      用户确认后复跑，二选一：
        edc-report build spec --spec <spec.json> --form-confirmed --source-id <id>
        spec: { "formConfirmed": true, "sourceId": "<id>", "form": "<准确表名>" }

浏览候选（不建表）：
  edc-report find form <appId> --list
  edc-report find form <appId> --suggest "关键词1,关键词2"

────────────────────────────────────────────────────────────
 两规则与退出码
────────────────────────────────────────────────────────────
  exit 3 = 须确认表单（规则 B）· 未建表
  exit 4 = 字段未精确命中（规则 A）· 未建表（或已删本轮未完成表）
  exit 0 = 精确命中/已确认，正常搭建

════════════════════════════════════════════════════════════
`;
console.log(text.trim());
process.exit(0);
