# 修改已有报表（只改用户点名项）

> **最高优先级规则**：用户没点名的东西，一个都不动。
> 完整版见 `user-request-scope-only-guide.md`。

---

## 一、铁律

改已有报表时，**默认什么都不改**。用户说了什么就改什么，其余部分原样写回。

**禁止**：

- ❌ 「顺便」改单元格内容、合并、样式、行高、父格、公式、查询条件、数据集、权限、快照、报表名
- ❌ 为了「好维护」把整张表重新识别、重扫字段、重建布局
- ❌ 用「全表重写更干净」当借口覆盖用户的手工调整
- ❌ 改列宽/冻结/居左时顺手改样式或拆掉合并 —— 这些是**独立**的改动

**允许**：只 patch 点名项；其余从回读结果原样写回。

拿不准就**问用户**，不要替用户决定。

---

## 二、典型改法

### 改字段（列）

```bash
e10-cli report read <reportId> --fields          # 先看清楚现状
```

改列 = 重建布局再整体保存。走 `report build` 的重跑不适用（会新建一张），
定点改要用 `report fix` 系列或重新组表后 `saveReportDevInfo`。

**关键**：保存前必须回读最新的 `designKey`（乐观锁），并且**从回读的 `fields[]` 重建工作簿**，
不能把读到的空 `sheets` 原样写回 —— 那会把整张表的布局清掉。详见 `safe-partial-save-guide.md`。

### 改显示名 / 改名

报表名走 `baseInfo`，字段显示名走字段接口，两者不是一回事。

### 改共享范围

```bash
e10-cli report scope list <reportId> --app-id <appId>     # 先读
e10-cli report scope set  <reportId> --app-id <appId> --scope "部门:销售部"
```

⚠️ `savePermissions` 是**全量替换**：只改 `viewRight` 时，`disableRight` 与 `viewMatrixRight`
必须原样带回，否则会把「不可见」矩阵一起清掉。

### 冻结 / 居左

```bash
e10-cli report fix freeze <reportId> --anchor <x,y>        # 预演
e10-cli report fix freeze <reportId> --anchor <x,y> --apply
```

唯一持久化标记是 `cell.tag.fixed`；`frozenRowCount` / `tag.fixedCell` 只影响设计器显示。

### 改查询条件

见 `guide-report-query.md`。**改条件不改显示方式**，除非用户点名。

---

## 三、改完必做

```bash
e10-cli report verify all <reportId> --app-id <appId>   # 绑定 + 结构 + tableName
```

改坏了**立刻回滚**：

```bash
e10-cli report version list <reportId>                  # 找版本
e10-cli report restore <reportId> --version <versionId> # 回滚
```

布局被冲掉（字段数骤降）时的首选是回滚，不是「再存一次试试」。

---

## 四、保存前的三道防线

CLI 已内置，改动时不要绕过：

1. **布局守卫** —— 字段与工作簿内容不能同时为空；保存后字段数不能掉。
2. **空白守卫** —— `showLocation=0` 会被纠正为 2；`scrollPage=1` 却没内容字段会拦下。
3. **雪花守卫** —— `snapshot.sheetId/id/jobId` 是 number 直接拒绝保存（`Number()` 截断会让设计区空白）。

---

## 相关文档

- `targeted-fix-guide.md` —— 定点改的细则
- `safe-partial-save-guide.md` —— 安全局部保存
- `designer-blank-prevention-guide.md` —— 设计区空白的成因与预防
- `report-delivery-contract.md` —— 改完交付什么
