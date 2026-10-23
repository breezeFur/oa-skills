'use strict';
/**
 * edc-report policy build — 会话搭建性能强制政策
 * 对应 references/cold-start-scan-guide.md · session-build-performance-guide.md
 */
const text = `
════════════════════════════════════════════════════════════
 edc-report 政策 · 会话搭建性能（强制）
════════════════════════════════════════════════════════════

0) 最小扫描面 + 冷启动（强制 · 防首包 502）
   开场只读：references/cold-start-scan-guide.md（一页）
   只允许：auth ready / e10-login status + edc-report + 点名 ≤2 篇 guide
   禁止：通读 SKILL 全文 / 全部 references / knowledge-base / help / 分析模板
   禁止：扫 .workbuddy/ 、通读 weaver-e10-login 、查找 e10-cli*
   本包不含 e10-cli* —— 禁止查找扫描

1) 登录（只走 e10-login · 兼容低版本）
   edc-report auth ready  → 已登录则直接搭建（与 CLI 大版本无关）
   未登录 + CLI <1.5 → action=login_required_legacy_set
   Agent 须 AskUserQuestion 二选一：
     A. 建议升级：npm i -g e10-login@1.5.0 → oidc
     B. 请用户提供必要信息后 set：
        · eteamsid（必填）= Cookie 中 Name=ETEAMSID 的 Value（单值，勿整段 Cookie）
        · baseUrl（必填）= 平台根地址，如 https://<your-e10-host>
        · agentType（可选，默认 WorkBuddy）
   禁止「必须升到 1.5」阻断搭表；细则：edc-report policy login

2) 找表（已给 app 时）
   只允许：edc-report find form <appId> <表单名>
   禁止：首轮 /ds/group、无关键字全库分页
   **规则 B（强制 · 2026-09-11）**：需求**未指明表** 或 检索**非完全精准匹配**
   （模糊/多命中/未命中）→ exit 3 + candidates，**提示用户自行选取指定表**；
   禁止按关键词猜表、禁止先建表再试。细则：spec-build-schema.md §1.1 · edc-report policy ask

3) SpreadJS
   禁止每次下载 gc.spread / 设计器 chunk 做黑盒逆向
   条件格式走 condition-format-guide + validate condition

4) 交付（模式 A · 搭完即停 · 最高）
   saveReportDevInfo 成功 → 立刻给设计器地址 → **本轮结束**
   禁止再跑：verify / 预聚合 / HTML / 需求分析 / 配置检测 / 再 save
   全局修复轮次 ≤1；禁止「报表好了 Agent 还在忙」
   已移除：测试用例 / 原型图（勿查找 generate_test_case、prototype）
   细则：report-delivery-contract.md

5) 条件格式
   突出显示 + 数据条 + 图标集；validate condition

6) 网格线（workbook 禁 gridline 键 · 存在即 500）
   只写 page gridLine=0|1；validate gridline

7) 禁止空壳 / 探测壳（强制 · 2026-09）
   先 fieldsBySource 预检字段（不精确命中 → exit 4，**不建表**）
   再目标名一次 baseInfo → 本表 addDataset（同源只挂一次）→ fieldsKey 复校 → save
   禁止 __build_* / __probe_*；禁止落库后再 rename；禁止跨报表复用 datasetId
   模糊表名：find form / build spec exit 3 确认后再搭；确认前不建表
   仅 save 失败时 deleteReport 未完成表

7.1) 字段精确绑定（强制 · 2026-09-11）
   仅精确匹配（fieldName/fieldMap → 列标题===text → field===text/name）
   禁止模糊自动绑定；禁止回退系统字段（name/id/create_time…）
   无命中 → exit 4，把 candidates/allFields 交用户指定字段
   单元格文案 ≠ 字段真实显示名 → 须用户确认（--field-confirmed / fieldConfirmed）
   verify bind 会列出 duplicate_dataset_mount / display_mismatch 待确认项
   细则：field-bind-exact-match-guide.md §2.0 · spec-build-schema.md §2.1

8) 同款样式复用（强制）
   多格相同样式 → validate format 只跑一次，其余深拷贝
   禁止逐格验写法 / 逐格翻 JSON 样例

9) 改已有报表
   仅改用户点名项（policy scope + targeted-fix）

细则：cold-start-scan-guide.md · failure-cleanup §〇 · spec-build-schema.md
════════════════════════════════════════════════════════════
`;

console.log(text.trim());
process.exit(0);
