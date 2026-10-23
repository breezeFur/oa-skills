# 报表命令速查

> 全部挂在 `e10-cli report` 下。全局加 `--profile <名>` 切环境、`--json` 出结构化结果。
> 破坏性命令（`delete` / `lifecycle recycle purge` / `cleanup --apply`）必须用户本轮明确要求才执行。

---

## 建表

| 命令 | 用途 |
|---|---|
| `report build --spec <file>` | 声明式一步建表（**首选**）；spec 写 `sources[]` 即**多数据源**，见 `guide-report-multisource.md` |
| `report render <reportId> --app-id <id> [--page-row-count <n>] [--condition <json>] [--dump <file>]` | **渲染回读**：真跑一遍拿展开后的行列数，是「关联/公式/条件格式真的生效」的唯一证据 |
| `report build --spec <file> --dry-run` | 只做定源与字段预检 |
| `report build ... --form-confirmed --source-id <id>` | 用户已确认表 |
| `report build ... --field-confirmed "列A,列B"` | 确认文案与显示名不同 |
| `report find <appId> [表名]` / `--list` / `--suggest <kw>` | 应用内定源 |
| `report create blank --app-id --name` | 空白报表 |
| `report create template --app-id --name --model-id` | 按模板建 |
| `report create quick --app-id --name --quickly-file <f>` | 快速构建（列表式） |
| `report create models` | 列出可用模板 |

## 读取

| 命令 | 用途 |
|---|---|
| `report read <reportId> [--fields]` | 基础信息 + 数据集 + 字段记录 |
| `report list --app-id <id>` | 应用内报表列表 |
| `report app-search --name <kw>` | 搜应用 |

## 数据集侧栏

| 命令 | 用途 |
|---|---|
| `report dataset add <reportId> --app-id (--form <名>\|--source-id <id>)` | 给已有报表**再挂一个数据源**（同源只挂一次） |
| `report dataset list <reportId> --app-id` | 已挂载数据集 |
| `report dataset rename --dataset-id --name` | 改显示名 |
| `report dataset preview --dataset-id` | 预览数据 |
| `report dataset check-used --report-id --dataset-id` | 是否仍被引用 |
| `report dataset delete --report-id --dataset-id [--force]` | 移除数据集 |
| `report dataset agg get\|save\|clear --dataset-id [--file]` | 预聚合 |
| `report dataset sort get\|save\|clear --dataset-id [--file]` | 排序 |
| `report dataset replace --file <f>` | 整表换源（含 fieldMap） |

## 查询条件

| 命令 | 用途 |
|---|---|
| `report query list <reportId> --app-id` | 列出条件 |
| `report query save <reportId> --app-id --item <f> [--show-where 高级搜索\|筛选]` | 保存一条 |
| `report query type <reportId> --app-id [--show-where]` | 设显示方式（**报表级批量覆盖**） |
| `report query check-echo <reportId> --app-id` | 回显体检 |
| `report query fix-echo <reportId> --app-id` | 短码化修复 |
| `report query verify <reportId> --app-id [--fix]` | Q1~Q10 合规体检 |
| `report fix query-default <reportId> --app-id [--set ...] [--all] [--apply]` | 补默认值三件套 |
| `report fix query-style <reportId> --app-id [--id ...] [--delete-id ...] [--apply]` | 清未点名的展示样式 |
| `report validate query --map-show-where "顶部筛选"` | 显示方式说法映射 |

## 权限

| 命令 | 用途 |
|---|---|
| `report scope list <reportId> --app-id` | 读共享范围 |
| `report scope set <reportId> --app-id --scope "all"` / `"部门:销售部,人员:张三"` | 设共享范围（全量替换 viewRight） |
| `report scope matrix list\|save\|delete <reportId> --app-id [--type 1\|-1]` | 权责矩阵 |

## 分组 / 生命周期 / 版本

| 命令 | 用途 |
|---|---|
| `report group list\|add\|delete --app-id [--name] [--group-id]` | 报表分组 |
| `report lifecycle copy-and-menu --app-id --source-name` | 复制 + 授权 + 挂菜单 |
| `report lifecycle add-menu --app-id --report-id --menu-name` | 挂菜单 |
| `report lifecycle move --app-id --report-id --group-id` | 移到分组 |
| `report lifecycle transfer --report-id <ids> (--app-id \| --app-name)` | 转移到别的应用 |
| `report lifecycle recycle list\|restore\|purge --app-id / --report-id` | 回收站 |
| `report version save\|list <reportId>` | 版本 |
| `report snapshot set\|list <reportId> [--cron] [--snapshot-name]` | 定时快照 |
| `report restore <reportId> --version <versionId>` | 从版本回滚 |
| `report cleanup --app-id [--prefix] [--apply]` | 空壳报表清理 |

## 校验 / 体检 / 修复

| 命令 | 用途 |
|---|---|
| `report validate base --name ...` | 报表名等基础字段规范 |
| `report validate condition (--file\|--inline\|--map\|--report-id)` | 条件格式白名单 |
| `report validate format (--map\|--file\|--list)` | 数字格式 / 日期分组 / 字号 |
| `report validate transform (--map\|--file\|--list)` | 转换面板 |
| `report validate href (--map\|--file\|--list) [--fix]` | 事件超链接 |
| `report validate gridline\|blank (--file\|--inline)` | 网格线 / 空白风险 |
| `report validate style [--list\|--inline]` | 默认分层样式 |
| `report verify bind\|all\|meta\|condition\|format\|blank\|gridline\|contract\|limit <reportId>` | 线上体检 |
| `report verify parents <reportId> --app-id <id>` | 跨数据源父格体检（入口格唯一 / fieldKey 三段式 / id=currentField / 算子白名单 / 锚点） |
| `report fix table-name <reportId> [--apply]` | 补 tableName |
| `report fix freeze <reportId> [--anchor x,y] [--apply]` | 冻结单元格 |
| `report fix echo <reportId> --app-id` | 同 `query fix-echo` |

## 分析

| 命令 | 用途 |
|---|---|
| `report join-suggest --app-id (--parent-source\|--parent-form) (--child-source\|--child-form)` | 推断两表关联字段（须用户确认） |
| `report py preagg (--fields <f> \| --report-id <id>) [--layout <f>]` | 预聚合可用性判定 |
| `report py left-filter --parent-ds/--parent-src/--parent-field --child-ds/--child-src/--child-field [--type]` | 算跨数据集父格筛选（输出 `subordination` + `leftFilterField`），定点修复时手工拼配置用 |

---

## 退出码约定

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 失败（校验不通过 / 接口报错） |
| 2 | 成功但有警告；或 `--strict` 下有「待用户确认」项；预聚合建议关闭 |
| 3 | `report build` / `join-suggest`：需要用户指定表，未建表 |
| 4 | `report build`：需要用户指定字段，未建表或已删未完成报表 |

## 默认只读、要 `--apply` 才写的命令

`fix table-name`、`fix freeze`、`fix query-default`、`fix query-style`、`cleanup`。
不带 `--apply` 时只预演并打印将要做的改动。
