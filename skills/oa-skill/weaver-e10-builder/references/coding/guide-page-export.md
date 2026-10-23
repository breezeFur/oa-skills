# 页面导出与路由注册指南

## 引用规范

### 前置加载文件（entry.js）

只有前置加载的文件才可以直接 import：

```js
import { getSimpleData } from './api/formApi.js';  // entry.js 中可以直接引用
```

- entry.js 中只能使用 `React`、`ReactDOM`、`@weapp/utils`、`@weapp/ecodesdk`、`axios`
- **不能使用 `@weapp/ui` 组件**
- entry 只完成入口的注册，不要写入业务逻辑

### 非前置加载文件（pages/ 目录）

**非常关键！！！** 非前置加载的文件（新增的所有文件），只能通过以下方式引用：

```js
import { asyncImport } from '@weapp/ecodesdk';
const AgentSxxx = React.lazy(() => asyncImport('${appId}', 'pages/AgentSxxx'));
// '${appId}' 是固定写法，是内置的ecode应用ID，不用管
```

引用路径要根据文件相对位置判断：
- entry.js 中引用 `api/formApi.js`：`'./api/formApi.js'`
- pages/ 目录下引用 `api/formApi.js`：`'../api/formApi.js'`

---

## 页面导出（路由注册）

在 `entry.js` 中通过 `regOvProps` + `regReactChildren` 注册路由：

```js
import { regOvProps, appInfo, regReactChildren } from '@weapp/utils';
const { publicUrl } = appInfo('@weapp/ecodesdk');
const extract = (
  <Route path={`${publicUrl}/sp/custom/abc123123/abc123`}> // 导出页面的具体路径
    <React.Suspense fallback={<div>Loading...</div>}>
      <Test />  // 导出页面的组件
    </React.Suspense>
  </Route>
);
regOvProps('weappEcodesdk', 'Switch', (props) => {
  regReactChildren(props, extract);
  return props;
}, 0);
```

---

## 路由规范

> **核心规则：entry.js 中的路由 path 不要拼接变量，直接写死字符串。**

| 端 | 路由前缀 |
|----|---------|
| PC 端 | `/sp/custom/...` |
| 移动端 | `/mobile/custom/...` |

- path 写固定字符串，如 `/sp/custom/ecode/onboarding`，不拼接 `${appId}`
- 使用 `appInfo('@weapp/ecodesdk').publicUrl` 处理二级路径兼容（`publicUrl` 本身已包含二级路径前缀）
- 页面跳转使用 `Link` 或 `withRouter` 的 `history.push`，需拼接 `publicUrl`

---

## ecodInfo.json

项目根目录下的 `ecodInfo.json` 记录项目元信息：

```json
{
  "ecodeProjId": "",
  "ecodeAppId": "",
  "ebuilderAppId": "",
  "mainUrl": ""
}
```

- 如果文件不存在或内容为空，说明项目还未上传到 Ecode 平台
- **导入 Ecode 成功后，必须将主页面路径写入 `mainUrl` 字段**，格式如 `/sp/custom/......`，和 entry.js 里必须完全相同
- **如果当前 Ecode 项目关联了 Ebuilder 应用，必须将 Ebuilder 应用 ID 写入 `ebuilderAppId`**。注意：`ebuilderAppId` 是 Ebuilder 应用的 ID，与 `ecodeAppId`（Ecode 应用文件夹 ID）不同

---

## entry.js 完整模板

```js
import React from 'react';
import { regOvProps, appInfo, regReactChildren } from '@weapp/utils';
import { asyncImport } from '@weapp/ecodesdk';

const { publicUrl } = appInfo('@weapp/ecodesdk');
const appId = '${appId}';

// 异步引入页面组件
const MyPage = React.lazy(() => asyncImport('${appId}', 'pages/MyPage'));

// 注册路由 — path 写死固定字符串，和
var ROUTE_PATH = '/sp/custom/ecode/my-page';
const myRoute = (
  <Route path={`${publicUrl}${ROUTE_PATH}`}>
    <React.Suspense fallback={<div>Loading...</div>}>
      <MyPage />
    </React.Suspense>
  </Route>
);

regOvProps('weappEcodesdk', 'Switch', (props) => {
  regReactChildren(props, myRoute);
  return props;
}, 0);
```
> `ROUTE_PATH` 不要在这里拼接 `appId` 变量，`publicUrl` 已包含二级路径前缀。

> 完成后记得告诉用户哪些页面对应哪些 URL。
