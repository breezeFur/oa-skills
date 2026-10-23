# 编译规则参考

## 编译命令

```bash
ecodecmd build {project-dir} --target=e10
```

- 其中 `{project-dir}` 为代码项目的目录
- 打包会在项目产生一个 `.target` 文件夹，包含一个 `.zip` 文件
- **打包得 cd 到项目的前一级**，要不然传的目录里面没有名称

---

## 编译配置

ecodecmd 内部使用 `@babel/standalone` v7.5.5 编译代码，E10 模式下调用 `compileJsE10`。

```
presets: ['es2015', 'react', ['stage-2', {decoratorsLegacy: true, loose: true}]]
plugins: ['proposal-object-rest-spread', 'proposal-optional-chaining']
```

---

## 支持的语法

| 语法 | 示例 |
|------|------|
| JSX | `<div className="app">{content}</div>` |
| 箭头函数 | `(x) => x + 1` |
| async/await | `const data = await getSimpleData(...)` |
| 模板字符串 | `` `Hello ${name}` `` |
| 对象展开 `...` | `{ ...oldObj, newKey: val }` |
| 可选链 `?.` | `obj?.nested?.value` |
| Class 组件 | `class MyPage extends React.Component {}` |

---

## Babel 编译陷阱（语法合法但编译后行为异常）

| 陷阱 | 说明 | 解决方案 |
|------|------|---------|
| `forEach(fn, this)` 传 context | `this` 在 Babel 编译后丢失，回调内的 `this` 变成 `undefined` | 提前 `var self = this;`，回调内用 `self` |
| `map/filter/find` 同样受影响 | 所有数组方法只要传了第二个参数 `this`，编译后都失效 | 一律用 `var self = this;` 模式 |
| 漏写 `var` 直接赋值 | `x = {}` 未经声明直接赋值，Babel 编译后严格模式报 `ReferenceError: x is not defined` | **所有变量必须先 `var x = ...` 再使用** |

```js
// ❌ Babel 编译后 this 丢失，setState 报错
data.forEach(function (item) {
  this.setState({ ... });
}, this);

// ✅ 提前捕获 this
var self = this;

// ❌ 漏写 var，Babel 编译后报 ReferenceError
priorityColorCache = {};
priorityOpts.forEach(function(opt) { ... });

// ✅ 先声明再赋值
var priorityColorCache = {};
priorityOpts.forEach(function(opt) { ... });
data.forEach(function (item) {
  self.setState({ ... });
});
```

---

## 不支持的语法（会编译报错）

| 语法 | 解决方案 |
|------|---------|
| `catch { }` 无参数 catch | 必须写成 `catch(e) {}` |
| `??` 空值合并运算符 | 用 `||` 或三元表达式替代 |
| `import()` 动态导入 | 必须用 `asyncImport` |
| `private class fields #` | 不用 class fields，用普通方法 |
| `globalThis` | 用 `window` |
| `BigInt` | 不用 |

---

## 打包 & 上传流程

```bash
# 1. 编译检查
e10-cli check <项目目录>

# 2. 打包（cd 到项目前一级）
cd /path/to/parent && ecodecmd build project-dir --target=e10

# 3. 上传（先删旧应用）
e10-cli project tree <projectId>              # 找旧应用 folderId
e10-cli project delete-folder <folderId>
e10-cli project import <projectId> .target/xxx.zip --main-url /sp/custom/...
```

---

## E10 打包与平台加载规则（build.json / CSS / 资源）

> 首次 build 会自动生成 `build.json`。它决定每个文件是否**前置加载**，平台导入后按它加载代码。
> 违反本节规则不报编译错，只会让页面发布后白屏 / 无样式 / 资源 404。

### build.json：前置加载登记表

- 首次 `ecodecmd build` 在项目根自动生成 `build.json`：`entry.js`、`formApi.js`、`.css`、`.pre.js` → `state:"y"`（平台前置加载）；其余 `.js` → `"n"`（按需，经 `asyncImport` 加载）。
- **再次 build 以已存在的 `build.json` 为准，不会自动补登记之后新增的文件。** 新增 / 删除文件后若平台表现异常，先检查 `build.json`（必要时删掉让它重新生成，或手动补登记）。
- `entry.js` 是唯一前置业务 JS，必须在 codes 里 `state:y`；其他业务 JS 不要批量设成 `y`（会让首屏变慢）。

### CSS 规则

- **禁止在 JS 里 `import` CSS**：ecode 无 CSS 模块解析，写了必丢、发布后无样式。
- 少量页面样式用内联 style；确需独立 `.css` 文件时，确认它在 `build.json` 的 codes 里（首次自动生成时 `.css` 会登记为 `y`；文件是后加的要自行补登记），否则平台不合并加载。
- 业务 CSS 选择器挂在页面根容器下，避免裸 `.类名`、`body`、`:root` 或平台内部 class 污染全局。

### 资源规则

- 工程 `resources/` 目录内容打包进 zip 的 `${resources` 物理目录；**业务代码引用统一用模板变量 `${appRes}/相对路径`**（导入后平台自动替换成正式地址），如 `${appRes}/logo.png`。
- 禁止 `./resources/...`、`../resources/...`、`/resources/...` 相对写法，以及在线 `loadjs('http(s)://...')` / CDN。

---

## 关键注意事项

1. **所有变量用 var 声明**，非前置加载文件引用确保使用 `React.lazy(() => asyncImport...)`
2. `${appId}` 是占位符，运行时由 ecode SDK 替换
3. 写完代码后运行 `e10-cli check <项目目录>` 逐条自检，全部确认通过后再 build
4. 本地修改后一定要及时 `ecodecmd build` + `import` 上传，否则用户无法验证（用户看不到本地代码）
