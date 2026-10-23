'use strict';
/**
 * edc-report policy list-page — 列表页分组/视图/移动/转移政策
 */
const text = `
════════════════════════════════════════════════════════════
 edc-report 政策 · 报表列表页操作（强制）
════════════════════════════════════════════════════════════

细则：references/report-list-page-ops-guide.md

1) 分组（新建/删除）
   GET  /api/bs/edc/report/group/list?appid=&groupType=0
   POST /api/bs/edc/report/group/save  form: appid + groupType + groups(JSON)
   删除=从 groups 去掉后全量 save；禁保存哨兵 -1/-2/-3
   CLI: edc-report group list|add|delete

2) 视图切换 / 快速排序（无服务端写）
   localStorage edc_report_view_type = grid|table
   快速排序=前端内存排序，不落库
   列表数据可读 GET tableView；禁止发明「保存视图」API

3) 权限矩阵添加/删除
   读: matrix/list type=1|-1
   使用矩阵写/删: savePermissions.viewMatrixRight（全量；空=清空）
   禁用矩阵写/删: matrix/save（删可 deleteType=1）
   CLI: edc-report scope matrix list|save|delete
   条件 DSL 必须抓包，禁止臆造

4) 移动到其他分组
   POST removeReport (reportId + groupId) —— 改 group_id，不是删表
   可选项=自建分组 only；无自建分组 → 不可移动，提示先添加分组
   CLI: edc-report lifecycle move

5) 转移到其他应用
   应用框: GET /api/bs/ebuilder/app/list?name=  （有权限且启用）
   重名 → AskUserQuestion / --confirm-app-id
   POST transferReport (reportIds + appId)；目标侧 group_id=-1
   CLI: edc-report app search · edc-report lifecycle transfer
════════════════════════════════════════════════════════════
`;
console.log(text.trim());
process.exit(0);
