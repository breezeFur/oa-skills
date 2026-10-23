'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_SCRIPTS = path.join(__dirname, '..', 'scripts');

/**
 * Resolve scripts directory.
 * Priority: EDC_REPORT_SCRIPTS → in-skill ../scripts (唯一脚本源)
 */
function resolveScriptsDir() {
  if (process.env.EDC_REPORT_SCRIPTS) {
    const p = path.resolve(process.env.EDC_REPORT_SCRIPTS);
    if (fs.existsSync(p)) return p;
  }
  if (fs.existsSync(path.join(SKILL_SCRIPTS, 'verify_field_bind.js'))) {
    return SKILL_SCRIPTS;
  }
  throw new Error(
    'Cannot find report scripts. Run the CLI from the Skill tree ' +
      '(edc-report/ must sit beside scripts/) ' +
      'or set EDC_REPORT_SCRIPTS=/path/to/weaver-e10-edcreport/scripts'
  );
}

function printHelp() {
  console.log(`edc-report — e-Builder EDC 报表 CLI (v${require('./package.json').version})

用法:
  edc-report <command> [args...]

【最高优先级政策】仅改用户点名项 — 未点名禁止改删报表配置:
  edc-report policy scope
  细则: Skill references/user-request-scope-only-guide.md

环境体检（把历史踩过的工具链坑一次跑完）:
  edc-report doctor [env|scripts|install|trees|perf|all] [--json] [--fix] [--full]
    env      凭证 / host+port / host 变量名 / CLI 版本 + 连通性探针
    scripts  scripts 目录 / require 解析 / 漏 port 扫描 / python 依赖 [/ 语法 --full]
    install  全局 shim 是否悬空 / 入口行尾（--fix 可修）
    trees    当前树 vs 同级安装副本 一致性
    perf     渲染守卫与 5 万格上限策略
  → 有 FAIL 时 exit 1；--fix 自动修「入口 CRLF / shim 路径」等安全项

历史踩坑知识库（动手前先扫一遍）:
  edc-report pitfalls [关键词...] [--area auth|perf|env|build|layout|field|query|excel] [--json] [--list-areas]
    每条含 症状 / 根因 / 对策 / 对应 CLI

会话搭建性能（已登录跳过重登；找表禁全系统；禁 SpreadJS 黑盒）:
  edc-report policy build
  edc-report auth ready

渲染（默认被守卫拦截；搭表不需要渲染）:
  edc-report render <reportId> [appId] [pageRowCount]
    ↑ 默认直接拒绝：全量交叉表必然 code:555 且白烧 15~80s
    ↑ 确需诊断时：EB_ALLOW_RENDER=1（pageRowCount 自动封顶 574）
  edc-report verify limit <reportId> [appId] [--rows N] [--cols N] [--date-values N]
    ↑ 不渲染，只做算术：行 × 列 vs 50000，给出结论与收敛建议

定向修复（均为覆盖式写入；默认 dry-run，需 --apply）:
  edc-report fix table-name --report-id <id> [--app-id <id>] [--table-name "数据集名"] \
        [--restore-from <wb.json>] [--apply]
    ↑ 修「单元格不回显数据集名」：从 fields[] 反向重建 workbook，重写 cellType.tableName
    ↑ 内置重建保真自检；保真不足直接拒绝保存
  edc-report fix echo --report-id <id> --app-id <appId>
    ↑ 同 query fix-echo：长码/空值 queryType → 数组短码，恢复设计器勾选
  edc-report fix freeze --report-id <id> [--app-id <id>] [--anchor <x,y>] [--apply]
    ↑ 冻结单元格：在锚点格写 tag.fixed（唯一持久化标记）→ 冻结其上方行 + 左侧列
    ↑ 锚点 x,y 均 0 基；缺省 = 首个数据行 + 第 0 列（仅冻结表头）
    ↑ 检测到重复坐标（同格多条记录）会拒绝落库，避免丢格
  edc-report fix query-style --report-id <id> --app-id <appId> [--id <itemId>...] \
        [--delete-id <itemId>...] [--apply]
    ↑ 清除查询条件上**用户未点名**的展示样式字段（advancedSearchType='openCondition'）
    ↑ 该字段会把报表页查询区从「默认样式」改成「展开条件」——CLI 历史上曾静默注入
    ↑ 删除只认显式 --delete-id（修「不带 id 保存 → 变成新增」造成的重复条件）
  edc-report fix query-default --report-id <id> --app-id <appId> [--set "<文本|id>=<default|custom>:<JSON值>"]... \
        [--id <itemId>...] [--all] [--show-order <n>] [--apply]
    ↑ 补齐查询条件的「默认值三件套」：defaultValueType / defaultValue / handleDefaultValue
    ↑ 缺了它 → 设计器弹窗「默认值类型」= 请选择、默认值区把**所有**控件变体炸开、
      其后的「日期类型 / 显示位置 / 条件必填 / 查询条件」被顶出可视区（看着像被改坏了）
    ↑ --set '年月=custom:["{yearmonth:-0}",""]' 可对单条指定默认值
    ↑ --show-order 0 可把「排序」对齐为设计器模板值（人工配置的条件通常就是 0）
  edc-report verify query <reportId> <appId> [--json] [--fix]
    ↑ 查询条件合规体检（Q1~Q10）：缺三件套 / 残留 advancedSearchType / 长码 queryType /
      重复 asNameIndex / browser 富对象缺失 / 报表级 queryType 混杂 —— 有 FAIL 时 exit 1
  edc-report verify contract <reportId> [appId]
    ↑ fix table-name 的只读版：报告 tableName 缺失数与规范取值，不落库

必须让用户指定（字段找不到 / 表没指明或非精确匹配 → 停下问用户）:
  edc-report policy ask
    细则: Skill references/spec-build-schema.md §1.1/§2.1

登录 / 低版本兼容（建议升级或索要 ETEAMSID）:
  edc-report policy login
  edc-report auth ready

列表页操作（分组/移动/转移/矩阵/视图政策）:
  edc-report policy list-page
  edc-report group list|add|delete --app-id <appId> ...
  edc-report lifecycle move --app-id <appId> --report-id <id> --group-id <gid>
  edc-report lifecycle transfer --report-id <id> --app-id <目标> | --app-name "名"
  edc-report app search --name "关键字"
  edc-report scope matrix list|save|delete ...

设计器 · 数据集侧栏（自定义名/聚合/排序/替换/移除）:
  edc-report dataset rename --dataset-id <id> --name "显示名"
  edc-report dataset agg get|save|clear --dataset-id <id> [--file aggre.json]
  edc-report dataset sort get|save|clear --dataset-id <id> [--file sort.json]
  edc-report dataset replace --file replace.json
  edc-report dataset check-used|delete --report-id <rid> --dataset-id <did>
  edc-report dataset preview --dataset-id <id>

鉴权:
  edc-report auth status
  edc-report auth ready

找表 / 多表关联:
  edc-report find form <appId> <表单名>
  edc-report find form <appId> --list
  edc-report find form <appId> --suggest "资产,台账"
    ↑ 非完全精准匹配（模糊/多命中/未命中）→ exit 3 + candidates，**须用户指定**
  edc-report join suggest --app-id <appId> --parent-form "主表" --child-form "子表"

新建报表（列表页三模式 · 空白 / 模版 / 快速构建-列表式）:
  edc-report create models
  ★ 一次性声明式搭表（推荐 · 定源→预检字段→落库→回读·全程无空壳）:
  edc-report build spec --spec <spec.json> [--dry-run] [--form-confirmed] [--source-id <id>]
                        [--field-confirmed "标题1,标题2" | --field-confirmed]
    结构见 references/spec-build-schema.md
    规则 B（选表）：需求**未指明表** 或 应用内**非完全精准匹配** → exit 3 + candidates，
                    提示用户自行选取指定表（禁止按关键词猜表/建壳试探）
    规则 A（选字段）：需求字段在当前数据集表单中**找不到** → exit 4 + allFields/candidates，
                    提示用户自行指定字段（禁止模糊兜底/系统字段回退）
    exit 3 = 须确认表单（未建表）· exit 4 = 字段未精确命中（未建表/已删本表）
  edc-report create blank --app-id <appId> --name "报表名"
  edc-report create template --app-id <appId> --name "报表名" --model-id <模板ID>
  edc-report create quick --app-id <appId> --name "报表名" --quickly-file quickly.json

查询条件（multipart 单对象 · 防 500 · 条件级 queryType='["advance"]' 数组短码）:
  edc-report query list --report-id <id> --app-id <appId>
  edc-report query save --report-id <id> --app-id <appId> --item queryItem.json
  edc-report query save ... --show-where "高级搜索"   # 默认；用户要筛选时传「筛选」
  edc-report query type --report-id <id> --app-id <appId> [--show-where 高级搜索|筛选]
  edc-report query check-echo --report-id <id> --app-id <appId>
    ↑ 回读全部条件，报告「显示方式」能否正确回显（queryType 是否以 [ 开头）
  edc-report query fix-echo --report-id <id> --app-id <appId>
    ↑ 自动把长码/空值条件改写为 '["advance"]' / '["filter"]'，恢复设计器勾选
  edc-report query verify <reportId> <appId> [--json] [--fix]
    ↑ 查询条件**合规体检**（同 verify query）：Q1~Q10 一次跑完
    ↑ Q1 queryType 数组短码 / Q2 advancedSearchType 必须为空 / Q3~Q5 默认值三件套
      Q6 id+asNameIndex 唯一 / Q7 browser 富对象 / Q8 filterParam / Q9 showOrder / Q10 报表级是否混杂
    ↑ --fix 只做幂等安全项（清样式字段 / 补三件套 / 短码化），**绝不新增删条件**
  edc-report validate query --map-show-where "筛选"
  edc-report validate query --validate-show-where --file item.json

校验 / 落库自检:
  edc-report verify bind <reportId> [appId] [--strict]
    （name/fieldKey 门禁 + 文案 vs 字段显示名 + 重复数据集/回显名 待确认项）
  edc-report verify self <reportId> [appId] [--with-bind] [--with-condition]
  edc-report verify all <reportId> [appId]
  edc-report verify meta <reportId> [appId]
  edc-report verify condition <reportId> [appId]

基础字段规范（平台默认值 + name 禁 \\r\\n）:
  edc-report validate base --name "报表名" [--name-label-id -1] [--group-id 0]

条件格式（突出显示白名单；禁 between；冲突 warnings）:
  edc-report validate condition --file rule.json
  edc-report validate condition --inline "{...}"
  edc-report validate condition --map "介于 1 5"

单元格配置回显（数字格式目录 / 日期分组 / 字体）:
  edc-report validate format --map "货币"
  edc-report validate format --map "年份"
  edc-report validate format --file cell.json
  edc-report validate format --list
  edc-report validate transform --map "人员"
  edc-report validate transform --map "部门全路径"
  edc-report validate transform --map "二维码"
  edc-report validate transform --list
  edc-report validate transform --file cell.json
  edc-report validate href --map "弹出页"
  edc-report validate href --file cell.json
  edc-report validate href --list
  edc-report validate href --file cell.json --fix   # 全角？→ASCII ?
  edc-report verify format <reportId> [appId]

设计区空白防护（快照 sheetId 禁 Number / showLocation 禁 0 / 滑动分页完整性）:
  edc-report validate blank --inline "{...}"
  edc-report validate blank --file patch.json
  edc-report verify blank <reportId> [appId]

网格线（默认关闭；禁止畸形导致保存失败）:
  edc-report validate gridline --inline "{...}"
  edc-report validate gridline --file patch.json [--strict] [--fix]
  edc-report validate style --list
  edc-report validate style --inline "{}"
  edc-report verify gridline <reportId> [appId]

失败删空壳（仅用户要求或失败删壳流程）:
  edc-report cleanup shells --app-id <appId> --report-id <id>[,id2]
  edc-report cleanup shells --app-id <appId> --prefix __build_
  edc-report lifecycle delete --app-id <appId> --report-id <id> ...

生命周期 / 版本 / 权限:
  edc-report version save|list --report-id <id> ...
  edc-report snapshot set|list --report-id <id> [--cron "..."] [--snapshot-name "..."]
    （未指定名称默认 {报表名}-{date}-{time}；sheetId 强制字符串）
  edc-report scope set|list --report-id <id> --app-id <appId> ...
  edc-report lifecycle <copy-and-menu|add-menu|delete> ...
  edc-report restore --origin <reportId> --version <snapshotId> --app-id <appId> ...

Python:
  edc-report py validate <config.json>
  edc-report py preagg --fields <fields.json> [...]
  edc-report py left-filter [...]

历史会话沉淀 → CLI 映射见 references/edc-report-cli.md §历史映射

说明:
  - Skill 执行时：确定性 API 一律优先本 CLI；无 CLI 再回退 scripts
  - 不替代 Skill：需求分析 / 布局判断仍读 weaver-e10-edcreport
  - 脚本唯一来源：Skill 的 scripts/（本包与它同仓，相对解析 ../scripts）
  - 破坏性命令（delete/cleanup/restore）必须用户本轮明确要求才可执行

环境变量: EDC_REPORT_SCRIPTS | E10_HOST | E10_BASE_URL
`);
}

function runNodeScript(scriptName, args) {
  const dir = resolveScriptsDir();
  const file = path.join(dir, scriptName);
  if (!fs.existsSync(file)) {
    throw new Error(`Script not found: ${file}`);
  }
  const r = spawnSync(process.execPath, [file, ...args], {
    stdio: 'inherit',
    env: process.env,
    cwd: dir,
  });
  process.exit(r.status == null ? 1 : r.status);
}

function runPython(scriptName, args) {
  const dir = resolveScriptsDir();
  const file = path.join(dir, scriptName);
  if (!fs.existsSync(file)) {
    throw new Error(`Script not found: ${file}`);
  }
  const py = process.env.PYTHON || 'python';
  const r = spawnSync(py, [file, ...args], {
    stdio: 'inherit',
    env: process.env,
    cwd: dir,
  });
  process.exit(r.status == null ? 1 : r.status);
}

const ALLOWED_SHELL_CMDS = new Set(['e10-login']);
const ALLOWED_SHELL_ARGS = /^(--version|status|ready)$/;

function runShell(cmd, args) {
  if (!ALLOWED_SHELL_CMDS.has(cmd)) {
    throw new Error(`Disallowed shell command: ${cmd}`);
  }
  for (const a of args) {
    if (!ALLOWED_SHELL_ARGS.test(a)) throw new Error(`Disallowed argument for ${cmd}: ${a}`);
  }
  const r = spawnSync(cmd, args, { stdio: 'inherit', shell: false, env: process.env });
  process.exit(r.status == null ? 1 : r.status);
}

async function run(argv) {
  if (!argv.length || argv[0] === '-h' || argv[0] === '--help' || argv[0] === 'help') {
    printHelp();
    return;
  }
  if (argv[0] === '-V' || argv[0] === '--version') {
    console.log(require('./package.json').version);
    return;
  }

  const [cmd, sub, ...rest] = argv;

  switch (cmd) {
    case 'policy': {
      if (sub === 'scope' || !sub) {
        runNodeScript('print_scope_policy.js', rest);
      } else if (sub === 'build') {
        runNodeScript('print_build_policy.js', rest);
      } else if (sub === 'login') {
        runNodeScript('print_login_policy.js', rest);
      } else if (sub === 'list-page') {
        runNodeScript('print_list_page_policy.js', rest);
      } else if (sub === 'ask') {
        runNodeScript('print_ask_policy.js', rest);
      } else {
        throw new Error('Usage: edc-report policy scope|build|login|list-page|ask');
      }
      break;
    }
    case 'doctor': {
      runNodeScript('doctor.js', [sub, ...rest].filter(Boolean));
      break;
    }
    case 'pitfalls': {
      runNodeScript('pitfalls.js', [sub, ...rest].filter(Boolean));
      break;
    }
    case 'render': {
      // 渲染守卫（eb_render.js 自身默认拒绝，需 EB_ALLOW_RENDER=1）
      runNodeScript('eb_render.js', [sub, ...rest].filter(Boolean));
      break;
    }
    case 'fix': {
      if (sub === 'table-name' || sub === 'tablename' || sub === 'contract') {
        // 默认 dry-run；--apply 才落库
        const args = rest.includes('--report-id') ? rest : ['--report-id', ...rest];
        runNodeScript('fix_table_name_echo.js', args);
      } else if (sub === 'echo' || sub === 'query-echo') {
        runNodeScript('save_query_item.js', ['--fix-echo', ...rest]);
      } else if (sub === 'freeze' || sub === 'frozen') {
        // 冻结单元格：默认 dry-run；--apply 才落库
        const args = rest.includes('--report-id') ? rest : ['--report-id', ...rest];
        runNodeScript('set_freeze_cells.js', args);
      } else if (sub === 'query-style' || sub === 'querystyle' || sub === 'display-style') {
        // 清理查询条件上未点名的展示样式字段（advancedSearchType）：默认 dry-run；--apply 才落库
        const args = rest.includes('--report-id') ? rest : ['--report-id', ...rest];
        runNodeScript('fix_query_display_style.js', args);
      } else if (sub === 'query-default' || sub === 'querydefault' || sub === 'default-value') {
        // 补齐查询条件的「默认值三件套」(defaultValueType/defaultValue/handleDefaultValue)：
        // 缺了它 → 设计器弹窗「默认值类型」= 请选择、默认值区炸开、日期类型/显示位置/条件必填被顶出可视区
        const args = rest.includes('--report-id') ? rest : ['--report-id', ...rest];
        runNodeScript('fix_query_default_value.js', args);
      } else {
        throw new Error(
          'Usage: edc-report fix table-name --report-id <id> [--app-id <id>] [--table-name "数据集名"] [--restore-from <wb.json>] [--apply] | fix echo --report-id <id> --app-id <appId> | fix freeze --report-id <id> [--app-id <id>] --anchor <x,y> [--apply] | fix query-style --report-id <id> --app-id <appId> [--id <itemId>...] [--delete-id <itemId>...] [--apply] | fix query-default --report-id <id> --app-id <appId> [--set "<文本>=<default|custom>:<JSON值>"] [--all] [--show-order <n>] [--apply]'
        );
      }
      break;
    }
    case 'auth': {
      if (sub === 'ready') runNodeScript('auth_ready.js', rest);
      else if (sub === 'status' || !sub) runShell('e10-login', ['status']);
      else throw new Error(`Unknown auth subcommand: ${sub}. Use: edc-report auth ready|status`);
      break;
    }
    case 'find': {
      if (sub !== 'form') throw new Error('Usage: edc-report find form <appId> (<表单名>|--list|--suggest "关键词")');
      runNodeScript('find_form_in_app.js', rest);
      break;
    }
    case 'create': {
      if (!sub || !['models', 'blank', 'template', 'quick'].includes(sub)) {
        throw new Error(
          'Usage: edc-report create models|blank|template|quick ...（见 report-create-modes-guide.md）'
        );
      }
      runNodeScript('create_report.js', [sub, ...rest]);
      break;
    }
    case 'build': {
      if (sub !== 'spec') {
        throw new Error(
          'Usage: edc-report build spec --spec <spec.json> [--dry-run] [--form-confirmed] [--source-id <id>] [--field-confirmed "标题1,标题2"]'
        );
      }
      runNodeScript('build_from_spec.js', rest);
      break;
    }
    case 'group': {
      const map = {
        list: 'group-list',
        add: 'group-add',
        delete: 'group-delete',
      };
      if (!map[sub]) {
        throw new Error('Usage: edc-report group list|add|delete --app-id <appId> ...');
      }
      runNodeScript('report_list_ops.js', [map[sub], ...rest]);
      break;
    }
    case 'app': {
      if (sub !== 'search') throw new Error('Usage: edc-report app search --name "关键字"');
      runNodeScript('report_list_ops.js', ['app-search', ...rest]);
      break;
    }
    case 'dataset': {
      const map = {
        rename: 'rename',
        preview: 'preview',
        replace: 'replace',
        'check-used': 'check-used',
        delete: 'delete',
        remove: 'delete',
      };
      if (sub === 'agg') {
        const act = rest[0];
        const amap = { get: 'agg-get', save: 'agg-save', clear: 'agg-clear' };
        if (!amap[act]) throw new Error('Usage: edc-report dataset agg get|save|clear ...');
        runNodeScript('dataset_ops.js', [amap[act], ...rest.slice(1)]);
        break;
      }
      if (sub === 'sort') {
        const act = rest[0];
        const smap = { get: 'sort-get', save: 'sort-save', clear: 'sort-clear' };
        if (!smap[act]) throw new Error('Usage: edc-report dataset sort get|save|clear ...');
        runNodeScript('dataset_ops.js', [smap[act], ...rest.slice(1)]);
        break;
      }
      if (!map[sub]) {
        throw new Error(
          'Usage: edc-report dataset rename|agg|sort|replace|check-used|delete|preview ...（见 dataset-sidebar-ops-guide.md）'
        );
      }
      runNodeScript('dataset_ops.js', [map[sub], ...rest]);
      break;
    }
    case 'join': {
      if (sub !== 'suggest') {
        throw new Error(
          'Usage: edc-report join suggest --app-id <id> (--parent-source/--child-source | --parent-form/--child-form)'
        );
      }
      runNodeScript('suggest_join_fields.js', rest);
      break;
    }
    case 'query': {
      if (sub === 'list') {
        runNodeScript('save_query_item.js', ['--list', ...rest]);
      } else if (sub === 'save') {
        runNodeScript('save_query_item.js', rest);
      } else if (sub === 'type') {
        runNodeScript('save_query_item.js', ['--type', ...rest]);
      } else if (sub === 'check-echo') {
        runNodeScript('save_query_item.js', ['--check-echo', ...rest]);
      } else if (sub === 'fix-echo') {
        runNodeScript('save_query_item.js', ['--fix-echo', ...rest]);
      } else if (sub === 'verify' || sub === 'check') {
        // 同 verify query：查询条件合规体检（Q1~Q10）
        const pos = rest.filter((x) => !x.startsWith('--'));
        const flags = rest.filter((x) => x.startsWith('--'));
        const reportId = pos[0];
        const appId = pos[1];
        if (!reportId || !appId) {
          throw new Error('Usage: edc-report query verify <reportId> <appId> [--json] [--fix]');
        }
        runNodeScript('verify_query_items.js', ['--report-id', reportId, '--app-id', appId, ...flags]);
      } else {
        throw new Error(
          'Usage: edc-report query list|save|type|check-echo|fix-echo|verify --report-id <id> --app-id <appId> [--item file.json] [--show-where 高级搜索|筛选]'
        );
      }
      break;
    }
    case 'cleanup': {
      if (sub !== 'shells') {
        throw new Error(
          'Usage: edc-report cleanup shells --app-id <appId> (--report-id <id> | --prefix __build_) [--list|--dry-run 只读自查]'
        );
      }
      runNodeScript('cleanup_empty_shells.js', rest);
      break;
    }
    case 'verify': {
      if (sub === 'bind') {
        runNodeScript('verify_field_bind.js', rest);
      } else if (sub === 'self') {
        runNodeScript('verify_self_check.js', rest);
      } else if (sub === 'meta') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify meta <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('validate_report_base_meta.js', args);
      } else if (sub === 'condition') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify condition <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('validate_condition_format.js', args);
      } else if (sub === 'format') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify format <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('validate_cell_config_echo.js', args);
      } else if (sub === 'blank') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify blank <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('validate_designer_blank_guard.js', args);
      } else if (sub === 'gridline') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify gridline <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('validate_gridline.js', args);
      } else if (sub === 'limit') {
        // 渲染规模预检：位置参数 → flag；其余原样透传（--rows/--cols/--date-values/--json）
        const pos = rest.filter((x) => !x.startsWith('--'));
        const flags = rest.filter((x) => x.startsWith('--'));
        const reportId = pos[0];
        const appId = pos[1];
        if (!reportId) {
          throw new Error(
            'Usage: edc-report verify limit <reportId> [appId] [--rows N] [--cols N] [--date-values N] [--block-width 3] [--json]'
          );
        }
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('check_cell_limit.js', [...args, ...flags]);
      } else if (sub === 'contract') {
        // tableName 契约体检（只读：不带 --apply）
        const pos = rest.filter((x) => !x.startsWith('--'));
        const flags = rest.filter((x) => x.startsWith('--'));
        const reportId = pos[0];
        const appId = pos[1];
        if (!reportId) throw new Error('Usage: edc-report verify contract <reportId> [appId]');
        const args = ['--report-id', reportId];
        if (appId) args.push('--app-id', appId);
        runNodeScript('fix_table_name_echo.js', [...args, ...flags]);
      } else if (sub === 'query' || sub === 'queryItem' || sub === 'condition-items') {
        // 查询条件合规体检（Q1~Q10）：--fix 幂等修复；默认只读
        const pos = rest.filter((x) => !x.startsWith('--'));
        const flags = rest.filter((x) => x.startsWith('--'));
        const reportId = pos[0];
        const appId = pos[1];
        if (!reportId || !appId) {
          throw new Error('Usage: edc-report verify query <reportId> <appId> [--json] [--fix]');
        }
        runNodeScript('verify_query_items.js', ['--report-id', reportId, '--app-id', appId, ...flags]);
      } else if (sub === 'all') {
        const reportId = rest[0];
        const appId = rest[1];
        if (!reportId) throw new Error('Usage: edc-report verify all <reportId> [appId]');
        const args = appId
          ? [reportId, appId, '--with-bind', '--with-condition', '--with-meta', '--with-blank']
          : [reportId, '--with-bind', '--with-condition', '--with-meta', '--with-blank'];
        runNodeScript('verify_self_check.js', args);
      } else {
        throw new Error(
          'Usage: edc-report verify bind|self|meta|condition|format|blank|gridline|limit|contract|query|all <reportId> [appId] [--strict]'
        );
      }
      break;
    }
    case 'validate': {
      if (sub === 'base') {
        runNodeScript('validate_report_base_meta.js', rest);
      } else if (sub === 'condition') {
        runNodeScript('validate_condition_format.js', rest);
      } else if (sub === 'format') {
        runNodeScript('validate_cell_config_echo.js', rest);
      } else if (sub === 'transform') {
        runNodeScript('validate_cell_transform.js', rest);
      } else if (sub === 'href' || sub === 'event') {
        runNodeScript('validate_event_href.js', rest);
      } else if (sub === 'query' || sub === 'showwhere' || sub === 'show-where') {
        runNodeScript('save_query_item.js', rest);
      } else if (sub === 'blank') {
        runNodeScript('validate_designer_blank_guard.js', rest);
      } else if (sub === 'gridline') {
        runNodeScript('validate_gridline.js', rest);
      } else if (sub === 'style' || sub === 'header-style' || sub === 'default-header') {
        runNodeScript('default_header_style.js', rest);
      } else {
        throw new Error(
          'Usage: edc-report validate base|condition|format|transform|href|query|blank|gridline|style ...'
        );
      }
      break;
    }
    case 'version': {
      if (sub === 'list') {
        runNodeScript('save_as_version.js', ['--list-only', ...rest]);
      } else if (sub === 'save') {
        runNodeScript('save_as_version.js', rest);
      } else {
        throw new Error('Usage: edc-report version save|list --report-id <id> ...');
      }
      break;
    }
    case 'snapshot': {
      if (sub === 'list') {
        runNodeScript('set_snapshot_schedule.js', ['--list-only', ...rest]);
      } else if (sub === 'set') {
        runNodeScript('set_snapshot_schedule.js', rest);
      } else {
        throw new Error('Usage: edc-report snapshot set|list --report-id <id> ...');
      }
      break;
    }
    case 'scope': {
      if (sub === 'list') {
        runNodeScript('set_report_view_scope.js', ['--list', ...rest]);
      } else if (sub === 'set') {
        runNodeScript('set_report_view_scope.js', rest);
      } else if (sub === 'matrix') {
        const action = rest[0];
        const map = {
          list: 'matrix-list',
          save: 'matrix-save',
          delete: 'matrix-delete',
        };
        if (!map[action]) {
          throw new Error(
            'Usage: edc-report scope matrix list|save|delete --report-id <id> --app-id <appId> ...'
          );
        }
        runNodeScript('report_list_ops.js', [map[action], ...rest.slice(1)]);
      } else {
        throw new Error(
          'Usage: edc-report scope set|list|matrix ... --report-id <id> --app-id <appId>'
        );
      }
      break;
    }
    case 'lifecycle': {
      if (!sub) {
        throw new Error(
          'Usage: edc-report lifecycle <copy-and-menu|add-menu|delete|move|transfer> ...'
        );
      }
      if (sub === 'move' || sub === 'transfer') {
        runNodeScript('report_list_ops.js', [sub, ...rest]);
      } else {
        runNodeScript('report_lifecycle.js', [sub, ...rest]);
      }
      break;
    }
    case 'restore': {
      runNodeScript('restore_report_from_version.js', [sub, ...rest].filter(Boolean));
      break;
    }
    case 'py': {
      if (sub === 'validate') runPython('validate_report_config.py', rest);
      else if (sub === 'preagg') runPython('check_preaggregate_support.py', rest);
      else if (sub === 'left-filter') runPython('left_filter_builder.py', rest);
      else throw new Error('Usage: edc-report py validate|preagg|left-filter ...');
      break;
    }
    case 'scripts-path': {
      console.log(resolveScriptsDir());
      break;
    }
    default:
      throw new Error(`Unknown command: ${cmd}. Run: edc-report --help`);
  }
}

module.exports = { run, resolveScriptsDir };
