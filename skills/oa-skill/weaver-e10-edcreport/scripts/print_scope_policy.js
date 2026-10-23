'use strict';
/**
 * edc-report policy scope — 打印「仅改用户点名项」强制政策
 * 对应 references/user-request-scope-only-guide.md
 */
const text = `
════════════════════════════════════════════════════════════
 edc-report 政策 · 仅改用户点名项（强制 · 最高优先级）
════════════════════════════════════════════════════════════

一句话：用户没点名的 — 不执行、不删除、不重建、不顺手改。
已搭建好的配置视为成品；只允许调整用户本轮明确说明的点。

硬禁止：
  • 未点名禁止 deleteReport / lifecycle delete / cleanup shells
  • 未点名禁止改单元格/合并/样式/行高/父格/公式/查询/数据集/权限/快照/名称
  • 禁止为「方便/完整/对齐」扩大改动面或整表覆盖重建
  • 「改列宽/冻结/居左」≠ 可改样式或拆合并（须保留 spans）

允许：
  • 仅用户点名项的最小 patch
  • 整表回传 workbook 时其余配置原样写回
  • 不确定是否在范围内 → 先问用户

细则：Skill references/user-request-scope-only-guide.md
      + targeted-fix-guide.md
映射：references/edc-report-cli.md §一（§A0）

破坏性命令仅当用户明确要求时使用：
  edc-report lifecycle delete | cleanup shells | restore
════════════════════════════════════════════════════════════
`;

console.log(text.trim());
process.exit(0);
