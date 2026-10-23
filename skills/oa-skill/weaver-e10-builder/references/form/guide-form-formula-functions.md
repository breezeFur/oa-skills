# 字段函数公式大全（平台 funcList）

> 来源：平台公式函数目录，共 **219 个函数**，11 类。写 `fields.json` 的 `formula` 或 `form formula set --expression` 时查这里。
> 引用字段语法：`{主表.字段名}` / `{明细表名.字段名}`；**日期差用 `DAYS(开始,结束)`**（相减不生效）。
>
> **两种写法都收**：设计器的公式编辑器里显示和输入的是方括号 `[字段名]`，平台存储的是花括号
> `{主表.字段名}`。CLI 两者都认，**从编辑器里复制原文直接传即可**，会先归一化成花括号再下发。
> 不必自己把 `[通知]` 改写成 `{主表.通知}`。
>
> ⚠️ 注意区分：**函数签名里的 `[...]` 表示「可选参数」**（如 `CONCAT(文本1, 文本2, [文本3, …])`），
> 而表达式里写在字段位置上的 `[字段名]` 才是字段引用。别把签名里的方括号当成引用照抄。
>
> 返回类型不填时按目标字段类型推断（数字/金额→Number，日期/时间→Date，其余→String）。
> **纯常量公式**（不含任何字段引用）平台允许，会带一条提示正常保存。
> 完整原始数据含参数说明/示例结果：`senba6/公式表.json`。

## ⚠️ 写公式前先记住这几条

这四条是**平台侧的语言规则**，写错**不报错**，只是算不对或整段失效 —— 出问题很难往回找。

**1. 函数名称必须大写。** `CONCAT(...)` / `VALUE(...)` / `IF(...)` / `SUM(...)`，小写平台不认。
> **例外：自定义 JS 脚本函数保持原样大小写** —— `default()`、`replaceAll()`、`countRelate()`、`getAddHrmIds()` 这些（见「自定义JS脚本函数」一类）是用户脚本注册的，名字怎么写就怎么用，**别跟着一起改成大写**。

**2. 逻辑比较用 `==`（两个等号），不是 `=`（一个等号）。**

```
✅ IF({主表.状态}=="已完成", 1, 0)
❌ IF({主表.状态}="已完成", 1, 0)      ← 单个等号是赋值语义，不是比较
```

**3. 给字段赋值用 `=`（一个等号），它只出现在整条公式的最左边。**

```
{主表.销售金额}=VALUE({主表.数量})*VALUE({主表.单价})
└──── 赋值，一个等号 ────┘└──── 函数体内部，比较用两个等号 ────┘
```

顶层那个 `=` 与函数体里的 `==` 是**两个层次**的东西，别因为看见 `=` 就写成 `==`，也别在函数体里把比较写成 `=`。函数联动的赋值式与 CLI 的关系见 `guide-formula-linkage.md`。

**4. 跨表复制粘贴公式，必须把非本表的字段变量换掉。** 从别的表单复制来的公式里，`{主表.X}` / `{明细表.X}` 指的是**原来那张表**的字段。粘到当前表必须逐个替换成本表字段 —— 平台按名字找字段，找不到、或者找到同名但语义不同的字段，**都不会拦住你**，只会静默算出不对的结果。

**5. 选项型控件（Select / RadioBox / CheckBox）要比的值，得引用「选项本身」，不能拿字符串比。**

```
✅ IF({主表.性别}=={主表.性别.男}, 65, 60)     ← 三段式：表.字段.选项
❌ IF({主表.性别}=='男', 65, 60)               ← 恒不成立
```

选项在库里存的是 **valueKey**（一串 id），不是选项名，所以拿 `'男'` 去比**永远不相等**；而平台**照收、不报错、回 200** —— 写完看着全绿，结果永远不对，是最难查的一类错。`e10-cli` 解析到「选项型字段 与字符串字面量 做 `==`/`!=`」会**出声警告**并给出正确写法，但**不会替你改**（表达式合不合法最终由平台定）。

⚠ 选项引用必须写**完整三段**。`[性别.男]` 只有两段，会被当成「明细表 `性别` 里的字段 `男`」—— 两段的方括号写法是既有的「明细表.字段名」，两者撞车，不给它开后门。

## 函数速查矩阵

| 分类 | 函数（中文名） |
|------|--------------|
| 字符函数 | CONCAT(链接多个文本), TEXT(将变量转为文本), VALUE(将文本转为数字), LEN(返回文本长度), SEARCH(在文本中查找关键字), REPLACE(替换文本中的字), REPT(将文本重复指定次数), PAD(将文本填充至指定长度), TRIM(清除前后空格), LEFT(返回文本左侧开始的文字), RIGHT(返回文本右侧开始的文字), MID(返回文本指定位置开始的文字), SCORE(获取选项型控件分数), IDCARD(身份证函数), ISSTRING(是否是字符串), ISJSON(JSON字符格式化), GETJSONVALUE(JSON字符取值), ISINT(字符内容是否是整数), ISNUMBER(字符内容是否是数字), ISFLOAT(字符内容是否是浮点型), SPLIT(字符分割), LOWER(字符转小写), UPPER(字符转大写), TEXTBEFORE(截取N个分割符之前的字符), TEXTAFTER(截取N个分隔符之后的字符), ENDWITH(判断字符串str1是否以str2结束), NVL(在所有参数中返回第一个不是null的值), CODE(计算文本串中第一个字符的数字代码), RMB(数字转换成金额写法), BAHTTEXT(数字金额转成泰铢文本表示), DOLLAR(数字金额转换成美元文本表示), PROPER(将首字母大写其余小写), TEXTJOIN(分隔符文本化，支持排除空值), LTRIM(清除左边空格), RTRIM(清除右边空格), SUBSTR(将指定字符串按指定位数进行截取), ASC(返回半角（单字节）字符), CONCATENATE(函数用于将多个变量合并成一个单独的字符串), ENCODEURL(将文本字符串中的特殊字符编码为 URL 编码格式), NUMBERSTRING(数字转汉字), DOLLARDE(将数字转换为以小数部分表示的价格), DOLLARFR(转换成分数表示的金额数字), EXACT(判断两个字符是否完全相等（区分大小写）), REPLACEALL(依据关键字替换所有字符) |
| 聚合函数 | COUNT(计数), SUM(求和), AVG(平均值), MIN(最小值), MAX(最大值), COUNTDATA(跨表计数), SUMDATA(跨表求和), AVGDATA(跨表求平均值), MINDATA(跨表求最小值), MAXDATA(跨表求最大值), COUNTIF(计数), SUMIF(合计), MAXIF(最大值), MINIF(最小值), AVGIF(平均数), AVGIFS(条件过滤求平均数), SUMIFS(条件过滤求合计), COUNTIFS(条件过滤求总数), MAXIFS(条件过滤求最大值), MINIFS(条件过滤求最小值) |
| 日期函数 | TODAY(当前日期), NOW(当前日期时间), DATEADD(对日期加减年、月、日), DATEDIFF(返回两个日期的差值), DATEFORMAT(返回指定格式的日期), YEAR(返回日期中的年), MONTH(返回日期中的月), DAY(返回日期中的日), HOUR(返回日期中的小时), MINUTE(返回日期中的分钟), SECOND(返回日期中的秒), WEEKNUM(返回日期为第几周), WEEKDAY(返回日期为星期几), NETWORKDAYSPI(返回所选时间段内包含的工作日天数), EOMONTH(返回某月最后一天日期), CURRYEAR(返回当前年份), CURRMONTH(返回当前月份), CURRDAY(返回当前第几日（当月）), CURRWEEK(返回当前日期是本周第几天), CURRHOUR(返回当前小时), CURRMINUTE(返回当前分), CURRSECOND(返回当前秒), MAXDATE(返回一组日期中的最大值), MINDATE(返回一组日期中的最小值), COMPAREDATE(返回两个日期指定时间的差值), TIMESTAMPTODATE(返回时间戳转换后的日期), DATETOTIMESTAMP(返回日期转换后的时间戳), DATE(拼接日期字符串), DAYS(计算两个日期之间的间隔天数), LUNAR(返回当前日期对应的农历时间), QUARTER(返回日期中的季度), YEARDELTA(返回指定日期后一年的日期), TIME(返回12小时制的时间), CURRDATETIME(获取当前日期时间), GETDATEVALUE(返回指定类型的日期), COMPAREWORKDATE(返回所选时间段内包含的工作日天数), CURRDATE(当前日期), TIMEVALUE(时间值), YEARFRAC(年份差), DAYS360(360天计算) |
| 逻辑函数 | IF(如果条件为真，则...否则...), AND(且), OR(或), NOT(反转真假结果), IN(变量是否包含在一组结果中), LIKE(文本是否包含任意一个关键字), ISEMPTY(是否为空), TRUE(返回真), FALSE(返回假), IFS(多条件), SWITCH(条件选择), SORT(条件排序), IFERROR(异常处理), NOTEMPTY(是否不为空) |
| 数学函数 | ROUNDUP(向上舍入), ROUND(四舍五入), ROUNDDOWN(向下舍入), AGGREGATION(聚合运算), MOD(求余), TRUNC(数字格式化), CALDTROW(明细逐行计算函数), ABS(绝对值), RANDOM(随机数生成), POWER(N次方), SQRT(根号), ACOS(返回指定数值的反余弦值), ASIN(返回指定数值的反正弦值), ATAN(计算指定数值的反正切值), CEILING(将参数number沿绝对值增大的方向), COS(返回一个角度的余弦值), DEGREES(将弧度转化为度), EXP(返回e的n次幂), FACT(返回数的阶乘), LN(返回一个数的自然对数), PI(是一个数学常量函数), PROMOTION(返回参数2在参数1上提升的比例), RADIANS(将角度转换成弧度), RANDBETWEEN(在两个数之间生成一个随机整数), SIGN(返回数值的正负性), SIN(计算给定角度的正弦值), TAN(返回指定角度的正切值), DEF(满足过滤条件的明细数据按照【维度】对指标进行聚合运算), EARLIER(满足过滤条件的明细数据按照【维度】对指标进行聚合运算), FLOOR(将参数 Number 沿绝对值减小的方向向下舍入，使其等于最接近Significance的倍数), INT(向下舍入到最接近的整数), RAND(随机返回一个值) |
| 财务函数 | GETMONEY(获取所给定数字的金额大写) |
| 自定义拓展函数 | default() |
| 查找函数 | CHOOSE(返回索引范围内指定的值), VLOOKUPS(按列查找，返回所需值), MATCH(返回指定数值在指定数组区域中的位置), FIND(查找), INDEX(数据索引), UNIQUE(唯一值过滤), FILTER(条件过滤) |
| 数据库函数 | GETHRMLOGINID(返回指定人员系统账号), GETHRMWORKCODE(返回指定人员编号), GETHRMMANAGER(返回指定人员直接上级), GETHRMEMAIL(获取指定人员邮箱), GETHRMSECLEVEL(获取指定人员安全级别), GETHRMALLMANAGER(返回指定人员所有上级), GETHRMDEPARTMENT(返回指定人员部门), GETHRMSUBCOMPANY(返回指定人员分部), GETDEPARTMENTNAME(返回指定部门名称), GETDEPARTMENTCODE(返回指定部门编号), GETSUPERDEPARTMENT(返回指定部门直接上级部门), GETALLSUPERDEPARTMENT(返回指定部门所有上级部门), GETSUBCOMPANYNAME(返回指定分部名称), GETSUBCOMPANYCODE(返回指定分部编号), GETSUPERSUBCOMPANY(返回指定分部直接上级分部), GETALLSUPERSUBCOMPANY(返回指定分部所有上级分部), GETHRMNAME(获取人员名称), GETHRMMOBILE(获取人员手机号码), GETREQUESTMARK(获取指定流程编号), GETDOCCODE(获取指定文档编号), GETPRJCODE(获取指定项目编号), GETCRMCODE(获取指定客户编号), LANGUAGE(当前语言), LANGUAGEID(当前语言ID), GETREQUESTSTATUS(流程状态), GETEMPIDBYNUMBER(人员编号获取人员ID), GETEMPIDBYACCOUNTNAME(登录名获取人员ID), GETDEPTIDBYNUMBER(部门编号获取部门), GETEMPIDBYMOBILE(人员手机获取人员ID), GETALLPARTNER(获取同部门所有同事), GETSUBDEPARTMENTS(获取所有下级部门), GETALLSUBEMPS(获取所有下级), GETSUBBRANCHSBYPID(获取所有下级分部), GTLDEP(获取一级部门), GTLSDEP(获取一级分部), GETHRMGRADE(获取指定人员职级), GETHRMPOSITION(获取指定人员岗位), GETEMPSTATUS(获取指定人员的状态) |
| 特殊函数 | DISTANCE(返回两个位置间的直线距离), GETUSER(返回用户的个人资料), FIELDS(根据条件和排序获取指定表格中的全部数据（最多50条）或指定条数的数据的指定字段值的集合。), CONCATOPT(选项合并) |
| 自定义JS脚本函数 | 1(1), 10(10), 2(2), 3(3), 4(4), 5(5), 6(6), 15(15), 16(16), 8(8), 9(9), replaceAll(replaceAll), commonHrmIds(变更前后未改变的参会人), isMainInfoEqual(变更前后主要信息是否修改（时间地点）), getRemoveHrmIds(获取移除人员), getAddHrmIds(获取新增人员), uniqueNumberString(提醒人员汇总), countRelate(计算浏览按钮选择数量) |

## 各函数格式与示例

### 字符函数（44 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| CONCAT(链接多个文本) | `CONCAT(文本1, 文本2, [文本3, …],[#分隔符#])` | CONCAT({总价}/10000, '万元') | string |
| TEXT(将变量转为文本) | `TEXT(变量)` | TEXT({当前数据.性别}) | string |
| VALUE(将文本转为数字) | `VALUE([文本、数字、选项])` | VALUE('23') | number |
| LEN(返回文本长度) | `LEN(文本)` | LEN('大家好dajiahao') | number |
| SEARCH(在文本中查找关键字) | `SEARCH(关键字, 文本, [搜索开始位置])` | SEARCH('大家', '大家好大家好', 3) | number |
| REPLACE(替换文本中的字) | `REPLACE(原文本, 替换开始位置, 替换字符数, 新文本)` | REPLACE('大家好大家好', 2, 3, 'dajia') | string |
| REPT(将文本重复指定次数) | `REPT(文本, 重复次数)` | REPT('大家', 2) | string |
| PAD(将文本填充至指定长度) | `PAD(原文本, 长度, 填充用的文本, [填充位置])` | PAD('你好', 4, '你', 'LEFT') | string |
| TRIM(清除前后空格) | `TRIM(文本)` | TRIM(' 大家好 ') | string |
| LEFT(返回文本左侧开始的文字) | `LEFT(文本, 截取字符数)` | LEFT('大家好', 2) | string |
| RIGHT(返回文本右侧开始的文字) | `RIGHT(文本, 截取字符数)` | RIGHT('大家好', 2) | string |
| MID(返回文本指定位置开始的文字) | `MID(文本, 指定位置, 截取字符数)` | MID('大家好', 2, 1) | string |
| SCORE(获取选项型控件分数) | `SCORE({选项})` | SCORE({当前数据.单选框}) | number |
| IDCARD(身份证函数) | `IDCARD({身份证号码}, {查找类型})` | IDCARD( ‘43070319980706334X’ , ‘BD’ ) | string |
| ISSTRING(是否是字符串) | `ISSTRING({任意控件})` | ISSTRING('泛微123456') | boolean |
| ISJSON(JSON字符格式化) | `ISJSON({变量})` | 假设文本控件={a:123},ISJSON({文本控件}) | boolean |
| GETJSONVALUE(JSON字符取值) | `GETJSONVALUE({变量1},变量2)` | 假设文本控件={a:123}，GETJSONVALUE('{文本控件}','a') | string |
| ISINT(字符内容是否是整数) | `ISINT({字符})` | ISINT( 2.123  ) | boolean |
| ISNUMBER(字符内容是否是数字) | `ISNUMBER({字符})` | ISNUMBER('2.123') | boolean |
| ISFLOAT(字符内容是否是浮点型) | `ISFLOAT({变量})` | ISFLOAT('2.123') | boolean |
| SPLIT(字符分割) | `SPLIT({字符},{字符})` | 假设文本控件=ABC#DEF，SPLIT('{文本控件}','#') | string |
| LOWER(字符转小写) | `LOWER({字符})` | LOWER('ABC') | String |
| UPPER(字符转大写) | `UPPER({字符})` | UPPER('abc') | String |
| TEXTBEFORE(截取N个分割符之前的字符) | `TEXTBEFORE({目标文本},{分隔符},{索引下标})` | TEXTBEFORE('abc-12','-',1) | String |
| TEXTAFTER(截取N个分隔符之后的字符) | `TEXTAFTER({目标文本},{分隔符},{索引下标})` | TEXTAFTER('abc-12','-',1) | String |
| ENDWITH(判断字符串str1是否以str2结束) | `ENDWITH({字符},{字符})` | ENDWITH('abc','c') | all |
| NVL(在所有参数中返回第一个不是null的值) | `NVL({字符})` | NVL('abc','','') | all |
| CODE(计算文本串中第一个字符的数字代码) | `CODE({字符})` | CODE('abc') | all |
| RMB(数字转换成金额写法) | `RMB({字符})` | RMB('1000.23') | all |
| BAHTTEXT(数字金额转成泰铢文本表示) | `BAHTTEXT({字符})` | BAHTTEXT('1000.23') | all |
| DOLLAR(数字金额转换成美元文本表示) | `DOLLAR({字符})` | DOLLAR('1000.23') | all |
| PROPER(将首字母大写其余小写) | `PROPER({字符})` | PROPER('abc') | all |
| TEXTJOIN(分隔符文本化，支持排除空值) | `TEXTJOIN({字符},{真假值},{字符})` | TEXTJOIN('-',TRUE(),'abc','cde') | all |
| LTRIM(清除左边空格) | `LTRIM({字符})` | LTRIM(' abc ') | all |
| RTRIM(清除右边空格) | `RTRIM({字符})` | RTRIM(' abc ') | all |
| SUBSTR(将指定字符串按指定位数进行截取) | `SUBSTR({字符},{数字},{数字})` | SUBSTR('abcdcf',1,3) | all |
| ASC(返回半角（单字节）字符) | `ASC({字符})` | ASC('abcＡＢＣ')  | all |
| CONCATENATE(函数用于将多个变量合并成一个单独的字符串) | `CONCATENATE({字符},{字符})` | CONCATENATE('AA','BB') | all |
| ENCODEURL(将文本字符串中的特殊字符编码为 URL 编码格式) | `ENCODEURL({字符})` | ENCODEURL('A B C') | all |
| NUMBERSTRING(数字转汉字) | `NUMBERSTRING({数字},{数字})` | NUMBERSTRING(123456,3) | all |
| DOLLARDE(将数字转换为以小数部分表示的价格) | `DOLLARDE({数字},{数字})` | DOLLARDE(1.02,16) | all |
| DOLLARFR(转换成分数表示的金额数字) | `DOLLARFR({数字},{数字})` | DOLLARFR(1.125,16) | all |
| EXACT(判断两个字符是否完全相等（区分大小写）) | `EXACT({字符},{字符})` | EXACT('ABC','Abc') | boolean |
| REPLACEALL(依据关键字替换所有字符) | `REPLACEALL({原字符},{目标字符},{替换字符},[指定替换位置])` | REPLACEALL('ABCA','A','a') | all |

### 聚合函数（20 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| COUNT(计数) | `COUNT(变量,{变量...{变量N}})` | COUNT(1,2,3,4,5) | Number |
| SUM(求和) | `SUM(变量,{变量...{变量N}})` | SUM(1,2,3,4,5) | Number |
| AVG(平均值) | `AVG(变量,{变量...{变量N}})` | AVG(2,2,2) | Number |
| MIN(最小值) | `MIN(变量,{变量...{变量N}})` | MIN(1,2,3,4,5) | Number |
| MAX(最大值) | `MAX(变量,{变量...{变量N}})` | MAX(1,2,3,4,5) | Number |
| COUNTDATA(跨表计数) | `COUNTDATA(表,{条件})` | COUNTDATA({表B},{表B.金额}=={当前表格.金额}) | Number |
| SUMDATA(跨表求和) | `SUMDATA(数字,{条件})` | SUMDATA({表B.金额},{表B.年度}=={当前表格.年度}) | Number |
| AVGDATA(跨表求平均值) | `AVGDATA(数字,{条件})` | AVGDATA({表B.金额},{表B.年度}=={当前表格.年度}) | Number |
| MINDATA(跨表求最小值) | `MINDATA(数字,{条件})` | MINDATA({表B.金额},{表B.年度}=={当前表格.年度}) | Number |
| MAXDATA(跨表求最大值) | `MAXDATA(数字,{条件})` | MAXDATA({表B.金额},{表B.年度}=={当前表格.年度}) | Number |
| COUNTIF(计数) | `COUNTIF({数字}...)` | COUNTIF(1,2,3) | number |
| SUMIF(合计) | `SUMIF({数字}...)` | SUMIF(1,2,3) | number |
| MAXIF(最大值) | `MAXIF({数字}...)` | MAXIF(1,2,3) | number |
| MINIF(最小值) | `MINIF({数字}...)` | MINIF(1,2,3) | number |
| AVGIF(平均数) | `AVGIF({数字}...)` | AVGIF(1,2,3) | number |
| AVGIFS(条件过滤求平均数) | `AVGIFS({数字}.{变量},{条件})` | AVGIFS({表A.入账},{表A.月份},{表A.月份}=10) | number |
| SUMIFS(条件过滤求合计) | `SUMIFS({数字},{变量},{条件})` | SUMIFS({表A.入账},{表A.月份},{表A.月份}=10) | number |
| COUNTIFS(条件过滤求总数) | `COUNTIFS({数字},{变量},{条件},{是否合计选项条数},{是否去重})` | COUNTIFS({表A.入账},{表A.月份},{表A.月份}=10) COUNTIFS({表A.入账},{表A.月份},{表A.月份}=10,TRUE(),TRUE()) | number |
| MAXIFS(条件过滤求最大值) | `MAXIFS({数字}.{变量},{条件})` | MAXIFS({表A.入账},{表A.月份},{表A.月份}=10) | number |
| MINIFS(条件过滤求最小值) | `MINIFS({数字}.{变量},{条件})` | MINIFS({表A.入账},{表A.月份},{表A.月份}=10) | number |

### 日期函数（40 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| TODAY(当前日期) | `TODAY()` | TODAY() | date |
| NOW(当前日期时间) | `NOW()` | NOW() | date |
| DATEADD(对日期加减年、月、日) | `DATEADD(日期,数值 , [单位],[日期累加类型])` | DATEADD('2016-12-21', 3) <br/> DATEADD('2016-12-24 20:00:00', 3, 'H') | date |
| DATEDIFF(返回两个日期的差值) | `DATEDIFF(日期1, 日期2, [单位])` | DATEDIFF('2016-12-21', '2016-12-24') <br/> DATEDIFF('2016-12-24 20:00:00', '2016-12-25 20:00:00', 'H') | number |
| DATEFORMAT(返回指定格式的日期) | `DATEFORMAT(日期, 可选格式)` | DATEFORMAT('2016-12-24', 'yyyy-MM-dd') | date |
| YEAR(返回日期中的年) | `YEAR(日期)` | YEAR('2016-12-24') | number |
| MONTH(返回日期中的月) | `MONTH(日期)` | MONTH('2016-12-24') | number |
| DAY(返回日期中的日) | `DAY(日期)` | DAY('2016-12-24') | number |
| HOUR(返回日期中的小时) | `HOUR(日期)` | HOUR('2016-12-24 20:30:56') | number |
| MINUTE(返回日期中的分钟) | `MINUTE(日期)` | MINUTE('2016-12-24 20:30:56') | number |
| SECOND(返回日期中的秒) | `SECOND(日期)` | SECOND('2016-12-24 20:30:56') | number |
| WEEKNUM(返回日期为第几周) | `WEEKNUM(日期)` | WEEKNUM('2016-12-25')<br/>WEEKNUM('2016-12-25',2) | number |
| WEEKDAY(返回日期为星期几) | `WEEKDAY(日期)` | WEEKDAY('2016-12-24') | number |
| NETWORKDAYSPI(返回所选时间段内包含的工作日天数) | `NETWORKDAYSPI(日期1, 日期2, 成员, [类型], [单位])` | 想知道李四在2021-11-07和2021-11-12之间的工作日天数<br/>NETWORKDAYSPI（＇2021-11-07＇, ＇2021-11-12＇,{U:李四}, ＇A＇,＇D＇)<br/>NETWORKDAYSPI（＇2021-11-07＇, ＇2021-11-12＇,{U:李四}, ＇A＇,＇ASS＇) | number |
| EOMONTH(返回某月最后一天日期) | `EOMONTH(日期,指定日期之前或之后的月数)` | EOMONTH('2021-11-07', -2) | string |
| CURRYEAR(返回当前年份) | `CURRYEAR()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRYEAR() | number |
| CURRMONTH(返回当前月份) | `CURRMONTH()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRMONTH() | number |
| CURRDAY(返回当前第几日（当月）) | `CURRDAY()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRDAY() | number |
| CURRWEEK(返回当前日期是本周第几天) | `CURRWEEK()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRWEEK() | number |
| CURRHOUR(返回当前小时) | `CURRHOUR()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRHOUR() | number |
| CURRMINUTE(返回当前分) | `CURRMINUTE()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRMINUTE() | number |
| CURRSECOND(返回当前秒) | `CURRSECOND()` | 假设当前时间为：2022年2月17日 11:20:30 ，CURRSECOND() | number |
| MAXDATE(返回一组日期中的最大值) | `MAXDATE(日期1,日期2,……)` | MAXDATE('2016-12-24', '2022-12-24') | date |
| MINDATE(返回一组日期中的最小值) | `MINDATE(日期1,日期2,……)` | MINDATE('2016-12-24', '2022-12-24') | date |
| COMPAREDATE(返回两个日期指定时间的差值) | `COMPAREDATE(日期1，日期2，[比较类型])` | 假设 日期1=2022-04-03、日期2=2022-04-04，COMPAREDATE({日期1},{日期2},'D') | date |
| TIMESTAMPTODATE(返回时间戳转换后的日期) | `TIMESTAMPTODATE(时间戳,日期格式)` | TIMESTAMPTODATE('1671172579', 'yyyy-MM-dd HH:mm:ss') | string |
| DATETOTIMESTAMP(返回日期转换后的时间戳) | `DATETOTIMESTAMP(日期)` | DATETOTIMESTAMP('2022-12-16 14:36:19') | string |
| DATE(拼接日期字符串) | `DATE({年},{月},{日})` | DATE('2022','12','16') | string |
| DAYS(计算两个日期之间的间隔天数) | `DAYS({日期},{日期})` | DAYS('2022-12-16','2022-12-18') | number |
| LUNAR(返回当前日期对应的农历时间) | `LUNAR({字符})` | LUNAR('2023','09','08') | all |
| QUARTER(返回日期中的季度) | `QUARTER({字符})` | QUARTER('2023-02-08') | all |
| YEARDELTA(返回指定日期后一年的日期) | `YEARDELTA({字符})` | YEARDELTA('2023-02-08') | all |
| TIME(返回12小时制的时间) | `TIME({字符})` | TIME(16,23,50) | all |
| CURRDATETIME(获取当前日期时间) | `CURRDATETIME({字符})` | CURRDATETIME('yyyy-MM-dd HH:mm:ss') | all |
| GETDATEVALUE(返回指定类型的日期) | `GETDATEVALUE({日期},{字符})` | GETDATEVALUE('2023-09-09 12:23:23','Y') | all |
| COMPAREWORKDATE(返回所选时间段内包含的工作日天数) | `COMPAREWORKDATE(日期1, 日期2, 成员, [类型], [单位])` | 想知道李四在2021-11-07和2021-11-12之间的工作日天数<br/>COMPAREWORKDATE('2021-11-07', '2021-11-12',{U:李四}, 'A','D') | number |
| CURRDATE(当前日期) | `CURRDATE()` | CURRDATE() | date |
| TIMEVALUE(时间值) | `TIMEVALUE({时间})` | TIMEVALUE('08:00') | date |
| YEARFRAC(年份差) | `YEARFRAC({日期},{日期})` | YEARFRAC('2022-09-09','2023-09-09') | date |
| DAYS360(360天计算) | `DAYS360({日期},{日期})` | DAYS360('2022-09-09','2023-10-09') | date |

### 逻辑函数（14 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| IF(如果条件为真，则...否则...) | `IF(条件, 表达式1, 表达式2)` | IF（{员工表.年龄} > 60, ＇退休＇, ＇在职＇) <Br/> IF（{员工表.年龄} > 60, IF（{员工表.性别} = {员工表.性别.女}, ＇退休＇, ＇在职＇), ＇在职＇) | all |
| AND(且) | `AND(条件1, 条件2, [条件3, …])` | AND(2 = 2, 2 < 2) | boolean |
| OR(或) | `OR(条件1, 条件2, [条件3, …])` | OR(2 = 2, 2 > 3) | boolean |
| NOT(反转真假结果) | `NOT(逻辑结果)` | NOT(2 > 3) | boolean |
| IN(变量是否包含在一组结果中) | `IN(变量, [变量1, 变量2, …])` | IN(2, [2, 3, 4]) | boolean |
| LIKE(文本是否包含任意一个关键字) | `LIKE(文本, [文本1, 文本2, …])` | LIKE('大家好', ['大家', '好']) | boolean |
| ISEMPTY(是否为空) | `ISEMPTY(变量)` | ISEMPTY({员工表.电话}) | boolean |
| TRUE(返回真) | `TRUE()` | TRUE() | boolean |
| FALSE(返回假) | `FALSE()` | FALSE() | boolean |
| IFS(多条件) | `IFS({条件1},{结果1},{条件2},{结果2}...{默认结果})` | IFS(1>1,1,1=1,2,0) | all |
| SWITCH(条件选择) | `SWITCH({变量},{条件1},{结果1},{条件2},{结果2}...{默认结果})` | SWITCH({字段1},1,'A',2,'B','C') | all |
| SORT(条件排序) | `SORT({变量1},{变量2},{变量3}...{排序方式})` | SORT(1,2,5,4,3,'UP') | all |
| IFERROR(异常处理) | `IFERROR({变量},{变量})` | IFERROR(10/0,'0') | all |
| NOTEMPTY(是否不为空) | `NOTEMPTY(变量)` | NOTEMPTY({员工表.电话}) | boolean |

### 数学函数（32 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| ROUNDUP(向上舍入) | `ROUNDUP(数字, [小数位精确度])` | ROUNDUP(76.9,0) | number |
| ROUND(四舍五入) | `ROUND(数字, [小数位精确度])` | ROUND(123.456,2),ROUND(123.456,0) | number |
| ROUNDDOWN(向下舍入) | `ROUNDDOWN(数字, [小数位精确度])` | ROUNDDOWN(76.9,0) | number |
| AGGREGATION(聚合运算) | `AGGREGATION({数字}...,{聚合运算类型})` | AGGREGATION(1 , 2,3,'AVG') | number |
| MOD(求余) | `MOD({数字},{数字})` | MOD( 7 , 3 ) | number |
| TRUNC(数字格式化) | `TRUNC({数字},{精度})` | TRUNC( 2.123 , 2 ) | number |
| CALDTROW(明细逐行计算函数) | `CALDTROW({字段},{公式或字段})` | 假设：明细有金额1、金额2、金额3等三个控件，明细行数为2，第一行值分别为：5、6、10，第二行的值分别为：1、1、9。CALDTROW({金额3}==10,{金额1}+{金额2}) | all |
| ABS(绝对值) | `ABS({字段})` | ABS(-9) | all |
| RANDOM(随机数生成) | `RANDOM({随机数长度},{随机类型})` | RANDOM(5,'NUM') | all |
| POWER(N次方) | `POWER({数字}, {数字}, {数字})` | POWER(2, 2) <br/> POWER(4, 1/2) <br/> POWER(0.33, 2, 3) | all |
| SQRT(根号) | `SQRT({数字})` | SQRT(4) | all |
| ACOS(返回指定数值的反余弦值) | `ACOS({数字})` | ACOS(0.1) | all |
| ASIN(返回指定数值的反正弦值) | `ASIN({数字})` | ASIN(0.1) | all |
| ATAN(计算指定数值的反正切值) | `ATAN({数字})` | ATAN(0.1) | all |
| CEILING(将参数number沿绝对值增大的方向) | `CEILING({数字})` | CEILING(0.5) | all |
| COS(返回一个角度的余弦值) | `COS({数字})` | COS(60*PI()/180) | all |
| DEGREES(将弧度转化为度) | `DEGREES({数字})` | DEGREES(1) | all |
| EXP(返回e的n次幂) | `EXP({数字})` | EXP(1) | all |
| FACT(返回数的阶乘) | `FACT({数字})` | FACT(4.8) | all |
| LN(返回一个数的自然对数) | `LN({数字})` | LN(0.5) | all |
| PI(是一个数学常量函数) | `PI({数字})` | PI() | all |
| PROMOTION(返回参数2在参数1上提升的比例) | `PROMOTION({数字},{数字})` | PROMOTION(12,14) | all |
| RADIANS(将角度转换成弧度) | `RADIANS({数字})` | RADIANS(30) | all |
| RANDBETWEEN(在两个数之间生成一个随机整数) | `RANDBETWEEN({数字},{数字})` | RANDBETWEEN(1,10) | all |
| SIGN(返回数值的正负性) | `SIGN({数字})` | SIGN(10) | all |
| SIN(计算给定角度的正弦值) | `SIN({数字})` | SIN(10) | all |
| TAN(返回指定角度的正切值) | `TAN({数字})` | TAN(0.785) | all |
| DEF(满足过滤条件的明细数据按照【维度】对指标进行聚合运算) | `DEF(聚合字段, 分组字段,聚合类型[SUM、AVG、COUNT],过滤条件)` | DEF({销售额},{省份},'SUM',{年份}=2013) | all |
| EARLIER(满足过滤条件的明细数据按照【维度】对指标进行聚合运算) | `EARLIER(排序列,排序类型：[UP、DOWN],聚合目标,聚合类型[SUM、COUNT])` | EARLIER({月份},'UP',{金额},'SUM') | all |
| FLOOR(将参数 Number 沿绝对值减小的方向向下舍入，使其等于最接近Significance的倍数) | `FLOOR({数字},{数字})` | FLOOR(23.445,1) | all |
| INT(向下舍入到最接近的整数) | `INT({数字})` | INT(234.32) | all |
| RAND(随机返回一个值) | `RAND({变量},{变量}...)` | RAND(5,9,10,23,44) | all |

### 财务函数（1 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| GETMONEY(获取所给定数字的金额大写) | `GETMONEY({数字})` | GETMONEY(1234) |  |

### 自定义拓展函数（1 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| default | `` |  | text |

### 查找函数（7 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| CHOOSE(返回索引范围内指定的值) | `CHOOSE(索引位置，索引目标1...索引目标N)` | 假设：数字输入框1为0，数字输入框2为2，数字输入框3为3，数字输入框4为4。数字输入框1为检索位置的变量，后面3个为检索目标。 示例：CHOOSE({表A.数字输入框1}, {表A.数字输入框2}, {表A.数字输入框3}, {表A.数字输入框4}) | Array |
| VLOOKUPS(按列查找，返回所需值) | `VLOOKUPS（表,[条件],[返回参数]）` | VLOOKUPS({税表}，{税表.收入}，AND（{税表.收入}>{税表.应纳税所得额下限}，{税表.收入}<{税表.应纳税所得额上限}），[{税表.税率},{税表.速算扣除数}]) | Array |
| MATCH(返回指定数值在指定数组区域中的位置) | `MATCH（值,[数组])` | MATCH(15000,  [1000, 15000,  2000]) | Number |
| FIND(查找) | `FIND([{查找值1},{查找值2}...{查找值N}],[{查找目标1},{查找目标2}...{查找目标N}])` | FIND([1,2,3],[1,2,3,4],1) | boolean |
| INDEX(数据索引) | `INDEX({查找值},[{查找目标1},{查找目标2}...{查找目标N}])` | 假设：数字控件1=2，金额控件1=3，金额控件3=5，INDEX(1，[{数字控件1},{金额控件1},{金额控件2}] | all |
| UNIQUE(唯一值过滤) | `UNIQUE({过滤目标1},{过滤目标2}...{过滤目标N})` | 假设：文本控件1='A'，文本控件2='B'，文本控件3='B'，UNIQUE({文本控件1},{文本控件2},{文本控件3}) | all |
| FILTER(条件过滤) | `FILTER([{过滤目标1},{过滤目标2}...{过滤目标N}],{过滤字段}={过滤依据})` | 假设：文本控件1='A'，文本控件2='B'，文本控件3='B'，FILTER([{文本控件1},{文本控件2},{文本控件3}],'B') | all |

### 数据库函数（38 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| GETHRMLOGINID(返回指定人员系统账号) | `GETHRMLOGINID({人员})` | GETHRMLOGINID({表单.张三}) |  |
| GETHRMWORKCODE(返回指定人员编号) | `GETHRMWORKCODE({人员})` | GETHRMWORKCODE({表单.张三}) |  |
| GETHRMMANAGER(返回指定人员直接上级) | `GETHRMMANAGER({人员}})` | GETHRMMANAGER({表单.张三}) |  |
| GETHRMEMAIL(获取指定人员邮箱) | `GETHRMEMAIL({人员})` | GETHRMEMAIL({表单.张三}) |  |
| GETHRMSECLEVEL(获取指定人员安全级别) | `GETHRMSECLEVEL({人员})` | 张三安全级别为1；GETHRMSECLEVEL({表单.张三}) |  |
| GETHRMALLMANAGER(返回指定人员所有上级) | `GETHRMALLMANAGER({人员})` | GETHRMALLMANAGER({表单.张三}) |  |
| GETHRMDEPARTMENT(返回指定人员部门) | `GETHRMDEPARTMENT({人员})` | GETHRMDEPARTMENT({表单.张三}) |  |
| GETHRMSUBCOMPANY(返回指定人员分部) | `GETHRMSUBCOMPANY({人员})` | GETHRMSUBCOMPANY({表单.张三}) |  |
| GETDEPARTMENTNAME(返回指定部门名称) | `GETDEPARTMENTNAME({部门})` | GETDEPARTMENTNAME({表单.A部门}) |  |
| GETDEPARTMENTCODE(返回指定部门编号) | `GETDEPARTMENTCODE({部门})` | GETDEPARTMENTCODE({表单.A部门}) |  |
| GETSUPERDEPARTMENT(返回指定部门直接上级部门) | `GETSUPERDEPARTMENT({部门})` | GETSUPERDEPARTMENT({表单.A部门}) |  |
| GETALLSUPERDEPARTMENT(返回指定部门所有上级部门) | `GETALLSUPERDEPARTMENT({部门})` | GETALLSUPERDEPARTMENT({表单.A部门}) |  |
| GETSUBCOMPANYNAME(返回指定分部名称) | `GETSUBCOMPANYNAME({分部})` | GETSUBCOMPANYNAME({表单.A分部}) |  |
| GETSUBCOMPANYCODE(返回指定分部编号) | `GETSUBCOMPANYCODE({分部})` | GETSUBCOMPANYCODE({表单.A分部}) |  |
| GETSUPERSUBCOMPANY(返回指定分部直接上级分部) | `GETSUPERSUBCOMPANY({分部})` | GETSUPERSUBCOMPANY({表单.A分部}) |  |
| GETALLSUPERSUBCOMPANY(返回指定分部所有上级分部) | `GETALLSUPERSUBCOMPANY({分部})` | GETALLSUPERSUBCOMPANY({表单.A分部}) |  |
| GETHRMNAME(获取人员名称) | `GETHRMNAME({人员})` | GETHRMNAME({U:张三}) |  |
| GETHRMMOBILE(获取人员手机号码) | `GETHRMMOBILE({人员})` | GETHRMMOBILE({U:张三}) |  |
| GETREQUESTMARK(获取指定流程编号) | `GETREQUESTMARK({关联流程})` | 假设关联流程=流程数据A，编号为：2332323，GETREQUESTMARK({关联流程}) |  |
| GETDOCCODE(获取指定文档编号) | `GETDOCCODE({关联文档})` | 假设关联文档=文档A，文档A编号为：234567，GETDOCCODE({关联文档}) |  |
| GETPRJCODE(获取指定项目编号) | `GETPRJCODE({关联项目})` | 假设关联项目=项目A，项目A编号为：2838383，GETPRJCODE({关联项目}) |  |
| GETCRMCODE(获取指定客户编号) | `GETCRMCODE({关联客户})` | 假设关联客户=客户A，客户A编号为：2838383，GETCRMCODE({关联客户}) |  |
| LANGUAGE(当前语言) | `LANGUAGE({人员})` | LANGUAGE({U:张三}) |  |
| LANGUAGEID(当前语言ID) | `LANGUAGEID({人员})` | LANGUAGEID（{U:张三}) | number |
| GETREQUESTSTATUS(流程状态) | `GETREQUESTSTATUS({关联流程})` | 假设关联流程所选中的数据正在审批中；GETREQUESTSTATUS({表单.关联流程}) |  |
| GETEMPIDBYNUMBER(人员编号获取人员ID) | `GETEMPIDBYNUMBER({人员编号})` | GETEMPIDBYNUMBER({人员编号}) | string |
| GETEMPIDBYACCOUNTNAME(登录名获取人员ID) | `GETEMPIDBYACCOUNTNAME({登录名})` | 登录名获取人员ID；GETEMPIDBYACCOUNTNAME({登录名}) | string |
| GETDEPTIDBYNUMBER(部门编号获取部门) | `GETDEPTIDBYNUMBER({部门编号})` | 部门编号获取部门ID：GETDEPTIDBYNUMBER({部门编号},'id') | string |
| GETEMPIDBYMOBILE(人员手机获取人员ID) | `GETEMPIDBYMOBILE({手机号})` | 人员手机号码获取人员ID；GETEMPIDBYMOBILE({手机号}) | string |
| GETALLPARTNER(获取同部门所有同事) | `GETALLPARTNER({人员})` | GETALLPARTNER({U:张三}) |  |
| GETSUBDEPARTMENTS(获取所有下级部门) | `GETSUBDEPARTMENTS({部门})` | GETSUBDEPARTMENTS({D:部门A}) |  |
| GETALLSUBEMPS(获取所有下级) | `GETALLSUBEMPS({人员})` | GETALLPARTNER({U:张三}) |  |
| GETSUBBRANCHSBYPID(获取所有下级分部) | `GETSUBBRANCHSBYPID({分部})` | GETSUBBRANCHSBYPID({D:分部A}) |  |
| GTLDEP(获取一级部门) | `GTLDEP({部门})` | GTLDEP({D:部门B}) |  |
| GTLSDEP(获取一级分部) | `GTLSDEP({分部})` | GTLSDEP({分部C}) |  |
| GETHRMGRADE(获取指定人员职级) | `GTLSDEP({人员})` | GETHRMGRADE({U:张三}) |  |
| GETHRMPOSITION(获取指定人员岗位) | `GETHRMPOSITION({人员})` | GETHRMPOSITION({U:张三}) |  |
| GETEMPSTATUS(获取指定人员的状态) | `GETEMPSTATUS({人员})` | GETEMPSTATUS({U:张三}) |  |

### 特殊函数（4 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| DISTANCE(返回两个位置间的直线距离) | `DISTANCE({地理位置1}, {地理位置2})` | DISTANCE({表A.地理位置1}, {表A.地理位置2}) | number |
| GETUSER(返回用户的个人资料) | `GETUSER({人员选择}, 文本)` | GETUSER({表A.人员选择}, 'M') | string |
| FIELDS(根据条件和排序获取指定表格中的全部数据（最多50条）或指定条数的数据的指定字段值的集合。) | `FIELDS({字段}, [条件], [排序字段], [排序类型], [返回条数])` | FIELDS({表A.负责人}, {表A.销售状态} = {C:已签约}, {表A.创建时间-倒序}, 'desc', 50}) | Array |
| CONCATOPT(选项合并) | `CONCATOPT({明细选项}...[是否去重])` | 公式1: CONCATOPT({表A.明细复选框},TRUE())<br/>公式2: CONCATOPT({表A.明细复选框},FALSE()) | string |

### 自定义JS脚本函数（18 个）

| 函数 | 格式 | 示例 | 返回 |
|------|------|------|------|
| 1 | `1(函数参数...)` |  | number |
| 10 | `10(函数参数...)` |  | number |
| 2 | `2(函数参数...)` |  | number |
| 3 | `3(函数参数...)` |  | number |
| 4 | `4(函数参数...)` |  | number |
| 5 | `5(函数参数...)` |  | number |
| 6 | `6(函数参数...)` |  | number |
| 15 | `15(函数参数...)` |  | number |
| 16 | `16(函数参数...)` |  | number |
| 8 | `8(函数参数...)` |  | number |
| 9 | `9(函数参数...)` |  | number |
| replaceAll | `replaceAll(str,searchValue,replaceValue)` |  | char |
| commonHrmIds(变更前后未改变的参会人) | `commonHrmIds(oldHrms,newHrms)` |  | char |
| isMainInfoEqual(变更前后主要信息是否修改（时间地点）) | `isMainInfoEqual(oldInfo,newInfo)` |  | number |
| getRemoveHrmIds(获取移除人员) | `getRemoveHrmIds(oldHrms,newHrms)` |  | char |
| getAddHrmIds(获取新增人员) | `getAddHrmIds(oldHrms,newHrms)` |  | char |
| uniqueNumberString(提醒人员汇总) | `uniqueNumberString(params)` |  | char |
| countRelate(计算浏览按钮选择数量) | `countRelate(var1)` |  | number |
