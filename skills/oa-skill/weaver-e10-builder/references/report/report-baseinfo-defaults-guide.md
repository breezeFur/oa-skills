# 报表基础字段默认值与命名规范（强制）

> **权威来源**：`EdcReportDevBaseController.saveReportBaseInfo`（`@RequestParam defaultValue`） 
> + `EdcReportDevBaseServiceImpl.buildNewReportDto` / `buildEmptySheetProp` / `resetReportListI18nName` 
> **原则**：**对齐平台内置默认值**；禁止凭感觉改空、改哨兵值、或往 `name`/`nameLabelId` 塞特殊字符。

---

## 一、baseInfo 内置默认值（设计器新建 API）

`POST /api/bs/edc/report/baseInfo`（`weaver-edcreportd` · `EdcReportDevBaseController`）：

| 参数 | 源码 `defaultValue` / 行为 | Agent / CLI **必须** |
|------|---------------------------|----------------------|
| `groupId` | **`"0"`** | 未指定分组时传 **`0`**。会出现在页面「全部」（`list?groupid=-1` 哨兵=查全部） |
| `showOrder` | **`"1"`** | 未指定时传 **`1`**；勿传空 |
| `name` | **必填**（无 default） | 非空；见 §二 |
| `nameLabelId` | 可选（无 default） | **无多语言时显式传 `"-1"`**（与线上正常报表一致）；勿传空串、勿省略后写成脏值 |
| `id` | `"0"` = 新建 | 新建用 `0`；更新用真实 reportId |
| `appId` | `"0"`（须改为真实应用） | **必须**真实 appId |
| `reportModel` | `"0"` | 无模板时保持 `0`；**模版创建**时传模板报表 ID（见 `report-create-modes-guide.md`） |
| `quicklyParam` | 无（省略） | **快速构建-列表式**时传 QuicklyParam **JSON 字符串**；与 `reportModel>0` 互斥（模板优先） |
| `systemType`（新建分支） | 服务端置 **`1`** | 普通 EB 报表勿擅自改成空/其它 |

`buildNewReportDto` 其它落库默认：

| 字段 | 默认 |
|------|------|
| `version` | `"1"` |
| `enable` | `1` |
| `configurable` | `0` |
| `frontView` | `0` |
| `enableInsight` | `0` |
| `deleteType` | `0` |

空 Sheet（`buildEmptySheetProp`）：`gridLine=0`、`rowHeaderVisible=0`、`colHeaderVisible=0`（与「页面布局默认关闭」一致）。

### 1.1 哨兵值 ≠ 入库默认值（强制）

| 值 | 用途 | Agent 行为 |
|----|------|------------|
| **`groupid=-1`（list 查询参数）** | 「查全部报表」哨兵 | 仅查询用 |
| **`baseInfo.groupId=-1`** | 部分租户/应用下**默认分组展示值**（ 常见） | **原样保留**，禁止擅自改成其它 ID |
| **`groupId=0`（Controller 新建 defaultValue）** | 新建 API 未指定分组时的入参默认 | 新建可显式传 `0`；**不要**事后乱改已有报表分组 |

> **强制**：已有报表的 `groupId` **只认 `baseInfo` 回读**。保存 `saveReportDevInfo` 时把 `baseInfo.groupId` **原样写入 multipart**，禁止脚本硬编码 `0`/`-1`/臆造 ID。 
> 改分组只能用户明确要求后走 `removeReport` 等换组接口。

### 1.2 禁止随便改空 / 乱设分组

| 禁止 | 说明 |
|------|------|
| 把 `groupId` / `showOrder` / `nameLabelId` 改成 `""` / `null` 指望「用默认」 | multipart 空串可能覆盖或落脏；应**显式传**上表默认值或 baseInfo 原值 |
| **擅自改已有报表 `groupId`** | 以参考报表/`baseInfo` 为准；「默认分组」可能是 `0` 或展示为 `-1`，勿凭记忆改写 |
| 更新 baseInfo 时清空已有合法默认字段 | `updateReportBase` 本就不改 `group_id`；改分组用 `removeReport` |
| 为「好看」改 `frontView`/`configurable`/`gridLine` 等 | 未需求点名则保持平台默认 |

---

## 二、name / nameLabelId 规范（强制）

### 2.1 `name`（报表名称）

| 规则 | 说明 |
|------|------|
| 非空 | 去掉首尾空白后长度 ≥ 1 |
| **禁止**控制字符 | 不得含 `\r` `\n` `\t` 及其它 ISO 控制符（`\u0000-\u001F`、`\u007F`） |
| 禁止首尾异常空白 | 写入前 `trim()`；勿保留仅空白名 |
| 同名校验 | 服从平台 `checkReportName`（如 SAME_NAME） |

### 2.2 `nameLabelId`（多语言标识）

源码 `resetReportListI18nName`：

```java
if (StringUtils.isNotBlank(nameLabelId) && !"-1".equals(nameLabelId)) {
 Long.parseLong(nameLabelId); // 脏字符 → NumberFormatException →「报表内部错误」
}
```

| 规则 | 说明 |
|------|------|
| 无多语言 | **必须** `"-1"`（字符串） |
| 有多语言 | **纯数字**雪花 ID 字符串，无空白、无 `\r\n` |
| **禁止** | `"-1\r\n"`、空串、`"null"`、带空格数字、任意非数字（除精确 `"-1"`） |

### 2.3 事故对照

`BBB` + `nameLabelId="-1\r\n"` → 应用报表页 `list?groupid=-1` 整页 500「报表内部错误」。

---

## 三、CLI（优先）

```bash
# 落库前本地校验（不访问网络）
e10-cli report validate base --name "资产信息统计" --name-label-id -1 --group-id 0

# 线上报表元数据巡检
e10-cli report verify meta <reportId> [appId]
```

校验失败 exit ≠ 0；Agent **禁止**跳过继续 save。

内部错误根因与修复全流程：`report-internal-error-guide.md`。


---

## 四、与其它文档

| 文档 | 关系 |
|------|------|
| `api-report-build-fast-path.md` §2.1 | 建壳命名 + groupId/name 纪律 |
| `e10-cli report -cli.md` | CLI 映射 |
| `failure-cleanup-and-nonblocking-guide.md` | 失败空壳清理 |
| `report-self-check-guide.md` | 布局/父格自检（本篇只管 base 元数据） |
