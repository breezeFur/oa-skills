# 报表踩坑清单

> 动手前扫一遍。每条都是「写进去不报错，但设计器上表现不对」的那一类。

---

## 一、请求层

### 1.1 `ebbusinessid` 只能发一次，且必须全小写

多发一个 `ebBusinessId`（驼峰）时，HTTP 头名大小写不敏感，运行时会把它和小写那个**归并成同一个头**，
值被拼成 `"<appId>, <appId>"`。

**症状**：`POST /api/bs/edc/report/addDataset` 与 `GET .../deleteReport` 恒返回
`HTTP 200` + `{"code":500,"msg":"报表内部错误"}`，响应头里 `responsetime` 只有十几毫秒
（服务端一进来就抛，没走到下游）。而同一时刻 `baseInfo` / `saveReportDevInfo` / `fieldsBySource` 全部正常。

**排查要点**：这类「HTTP 200 + 业务 500」优先怀疑**自己多发了什么**，而不是先怀疑服务。
二分时从「能通的那一份请求」逐项摘，比从「不通的那一份」逐项加收敛快得多。

### 1.2 建报表撞名时不报错，返回哨兵字符串

`baseInfo` 遇到同名报表**不回错误码**，而是把 `data` 写成字符串 `SAME_NAME`。

后果：不识别这个哨兵，就会拿着 `"SAME_NAME"` 当 reportId 一路往下跑，
最后错报在 `addDataset` 上，把人往完全错误的方向带。

CLI 已识别并给出明确提示。

### 1.3 `addDataset` 不返回 datasetId

它只回一个空的成功体，必须回查 `dataset/list` 才能拿到新数据集 id。
查询与 `addDataset` 之间**不要加 sleep** —— 命中即返回，轮询几次就够。

### 1.4 写接口不重试

建表、落库都不是幂等操作。网络层失败后重放会直接多出一张报表或一份重复配置，
所以 CLI 对报表接口固定 `retries=1`。

---

## 二、字段绑定

### 2.1 禁止系统字段兜底（历史事故）

列标题匹配不上时，**绝不能**回退到 `name` / `id` / `create_time` 等系统字段。
事故：需求写「姓名」，被静默绑到系统字段 `name`（真实显示名「标题」），报表能用但数据全错。

无精确命中 → 停下让用户指定（见 `field-bind-exact-match-guide.md`）。

### 2.2 `field_` 前缀不能加也不能去

平台业务字段的技术名形如 `field_1315401474786910245`。
写成裸雪花（去掉 `field_`）或凭空造一个 `field_xxx`，`fields` 记录都对不上。
`report verify bind` 会给出「应为 field_xxx」或「不要加前缀」的提示。

### 2.3 两个字段接口的信封不一样

| 接口 | `data` 形状 | `dataSetId` |
|---|---|---|
| `dataset/fieldsBySource` | **裸数组** | 恒为 `"0"`（还没落库） |
| `dataset/fieldsAndOriginFields` | `{fieldsKey, originFieldsKey}` | 真实值 |

字段元素本身同形，只有 `dataSetId` 不同。所以 `fieldsBySource` 的结果**必须**用本报表真实
datasetId 覆盖后再落库，否则单元格会绑到错误的数据集上。
详见 `dataset-table-field-contract-guide.md`。

### 2.4 `tableName` 缺失 → 数据源不显示模块类型

Field 单元格的 `tableName`（数据集显示名，含 `(业务模块)` / `(表单)` 后缀）与
`fieldId`/`fieldName`/`fieldText` 三件套缺一不可，否则属性面板回显不全。

补齐：`e10-cli report fix table-name <reportId> --apply`。

---

## 三、数据集

### 3.1 同源只挂一次

同一张表在一个报表里挂两次，左侧会出现**重复数据源分组**。
`resolveDataset` 会先查已有挂载再决定是否新建；发现存量重复会报 `duplicates` 提示用户清理。

清理前必须先摘掉画布上游离单元格对它的引用，否则删不掉。

### 3.2 报表自带一个系统数据集

每张报表都会带一个 `dataUpdateTime` 数据集（`sourceId` 是另一个雪花）。
它不在画布上，**不是重复挂载**，别当脏数据清掉。

### 3.3 `delDataset` 的参数名是历史包袱

它收的字段叫 `sourceIds`，但**值是 datasetId**，不是 sourceId。

### 3.4 数据集不能跨报表复用

拿 A 报表的 `datasetId` 去 B 报表用会被忽略（CLI 会警告并重新解析）。

---

## 四、布局与空白

### 4.1 `gridline` 键一出现就 500

workbook 的 sheet 上**禁止**出现 `gridline` / `gridLine` / `__gridline` 任何一个。
存在即 `saveReportDevInfo` 返回「报表内部错误」。

网格线只写在 `sheetProps` / 分页设置的 `gridLine`（`0|1`）上。
校验：`e10-cli report validate gridline --file wb.json`。

### 4.2 `showLocation` 不能是 0

只允许 `1`（居左）/ `2`（居中）。写 `0` 会被前端当成缺失，表现为设计区空白/布局异常。

### 4.3 `(0,0)` 的空 Const 是幽灵格

`Const` 的父格缺省时，服务端 Java `int` 会当 0，变成「伪自定义 A1」父格关系。
父格必须显式落到 `-1`。

### 4.4 合并只认 `spans`

`rows[].size = 0` **不会隐藏行**，合并单元格也只认 `spans` 数组。
详见 `hidden-row-and-header-merge-guide.md`。

### 4.5 链接格的父格规则

超链接格的上父格必须留 `-1,-1`（写了会把超链接文案冲掉）；
链接里含 `{坐标}` 占位符时，左父格必须指向依赖的数据格，且不能是 `(0,0)`。

---

## 五、查询条件

### 5.1 `queryType` 必须是数组短码

`'["advance"]'` / `'["filter"]'`。写成 `"advancedSearch"` 这种长码，服务端也收，
但设计器「显示方式」**不会勾选**。修复：`report query fix-echo`。

### 5.2 `updateQueryType` 是报表级批量覆盖

它会把入参的 `queryType` 写到**所有**条件上。所以只在用户明确点名要改显示方式时才调用，
绝不能顺手带一脚 —— 否则会把混合的筛选/高级搜索一键抹平。

### 5.3 绝不能静默注入 `advancedSearchType`

写 `'openCondition'` 等于把报表页查询区从「默认样式」改成「展开条件」，属于擅改用户的展示样式。
入参没有这个键就不写。存量清理：`report fix query-style --apply`。

### 5.4 默认值三件套必写

`defaultValueType` / `defaultValue`（+ `type1DefaultValue` / `type2DefaultValue`）。
漏写 → 设计器弹窗「默认值类型」= 请选择、默认值区把**所有**控件变体炸开，
其后的「日期类型 / 显示位置 / 条件必填」被顶出可视区，看着像被改坏了。

补齐：`report fix query-default --apply`。

### 5.5 不带 `id` 保存会变成「新增」

`saveQueryItem` 必须带 `id` 才是原地更新；不带就新增出重复条件。
`report query verify` 的 Q6 会拦这一条。

### 5.6 `queryItems` 只收单条对象

传数组会 500。且 `conditions[]` 不能为空，否则服务端 NPE。

### 5.7 条件格式的「介于」是 `interval`

引擎只认 `highlight:interval`，写 `between` 不会报错但**规则静默不生成**。
且多条规则是**或**不是**且** —— 「大于 5 且小于 10」要写成一条 `interval`，
写成 `greater` + `less` 两条会命中并集。

---

## 六、并发与权限

### 6.1 `designKey` 是乐观锁

已有报表保存前必须**回读最新的** `designKey`。用旧值会「数据不是最新」或偶发 500。
新建的空壳传空串即可。

### 6.2 权限接口是全量替换

`savePermissions` 的 `viewRight` 传空数组 = 谁都不给看。
只改共享范围时，必须先把 `disableRight` / `viewMatrixRight` 读回来原样带回，
否则会把「不可见」矩阵一起清掉。

### 6.3 复制出来的报表默认没人能看

`copySheet` 复制后权限是空的，必须单独授权，否则用户点菜单会看到无权限。
`report lifecycle copy-and-menu` 已把「复制 + 授权所有人 + 挂菜单」串起来了。

---

## 六补充、环境相关

### 6.4 `saveAsVersion` 在部分环境不可用

**现象**：保存版本返回 `HTTP 200` + `{"code":500,"msg":"报表内部错误"}`，
而同一张报表的 `getVersionWithPage`（读版本列表）完全正常，只是列表恒为空。

**已确认是环境问题，不是用法问题**：

- 同一个请求在**另一个环境**返回 `{"code":200,...,"data":{"id":...}}`，功能正常；
- 在报错的环境里，**用浏览器设计器自带的「保存版本」按钮操作，同样报「报表内部错误」**。

**排查时已经排除的**（不用重走）：权限（`appRight` 的 EDIT 为 true）、
请求格式（multipart 与 urlencoded 都试）、字段名（换 `id` 会返回 400，说明确实是 `sheetId`）、
`designKey`（带最新值照样 500）、版本名格式（带不带 `{date}-{time}` 占位符都一样）、
请求头（逐字节复刻浏览器请求仍 500）。

**请求格式备忘**：`saveAsVersion` 走 **multipart**（不是 urlencoded），两个字段
`sheetId`（报表 id）+ `versionName`；`versionName` 通常形如 `{报表名}-{date}-{time}`。

**处置**：如实告诉用户该环境的版本功能不可用；需要留档时可改用快照
（`e10-cli report snapshot set`）。**不要**为此在客户端反复试错。
`report version list` 仍可正常读取。

---

## 七、雪花 ID

19 位 id 一旦被 `Number()` 过就会截断，写回去指向不存在的记录，
表现为**设计区空白**，而且极难反推。

凡是 `reportId` / `sheetId` / `datasetId` / `snapshot.id` / `snapshot.jobId`，
一律保持字符串。详见 `snowflake-id-precision-guide.md`。
