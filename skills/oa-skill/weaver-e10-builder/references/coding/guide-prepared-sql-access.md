# SQL 准备：运行端取数与使用权限

用于 E-Builder 页面、自定义组件调用 SQL 准备，以及排查“管理员正常、普通用户暂无权限”。下述协议已在实际合同看板验证；其他版本以当前环境原生组件/SDK 的实际请求为准。

## 接口选择与权限

- 数据准备管理端接口 `/api/dw/directConn/getModelDatasetData` 曾出现 HTTP 200、业务 code:401、msg:暂无权限！。增加“所有人”使用权限后，普通用户仍不能通过该管理接口取数。面向普通用户的 E-Builder 页面和组件不要使用它。
- 运行端优先复用平台原生 SQL SDK；直接请求时使用 POST `/api/ebuilder/coms/dataset/sql/getData`，携带当前登录会话，由平台校验权限。
- 使用权限、维护权限、页面/菜单权限及实际数据范围分别核查。按用户指定的对象与人群授权，只有明确要求开放给所有人时才配置“所有人”使用权限；不要因报错自动扩大授权或增加维护权限。

## 已验证的请求协议

请求体为 FormData：datasetId 是当前环境真实数据集 ID 字符串，params 是 SQL 参数对象的 JSON 字符串，无参数传 '{}'。不手动设置 multipart Content-Type，由浏览器生成 boundary。不沿用管理接口的 pageNo/pageSize 或假定两个接口采用相同分页规则。

~~~javascript
function queryPreparedSql(datasetId, params) {
  var form = new FormData();
  form.append('datasetId', datasetId);
  form.append('params', JSON.stringify(params || {}));
  return window.fetch('/api/ebuilder/coms/dataset/sql/getData', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
    body: form
  }).then(function(response) {
    if (!response.ok) throw Error('SQL准备查询失败 HTTP ' + response.status);
    if ((response.headers.get('content-type') || '').toLowerCase().indexOf('json') < 0)
      throw Error('SQL准备未返回JSON，请确认OA登录状态');
    return response.json();
  }).then(function(body) {
    if (!body || Number(body.code) !== 200 || body.status === false || body.fail === true)
      throw Error('SQL准备查询失败，请检查使用权限');
    if (!Array.isArray(body.data)) throw Error('SQL准备返回数据格式异常');
    return body.data;
  });
}
~~~

绑定 ID、参数和字段由实例配置及当前环境真实定义提供，不复制历史合同实例 ID。空数组是空数据；权限错误、登录失效、非 JSON 或异常结构显示失败并允许重试，不能显示为 0。迁移接口后核对完整结果、聚合口径与排序，避免漏行或重复累计。

## 排查与验收

1. 对比管理员和代表性普通用户在同一环境、页面与数据集上的实际请求，检查路径、HTTP 状态、业务码及响应体；HTTP 200 不等于业务成功。
2. 读取现有使用权限与页面/菜单权限。按授权范围修改并保留无关配置；保存后回读，确认 SQL、参数、字段及其他定义未被意外修改。
3. 组件误用管理接口时替换为原生 SDK/运行端协议，保留原组件 ID 与配置键，完成编译、保存和回读。
4. 用获授权的普通用户打开正式运行页，确认正确接口成功返回且图表/数值可见，覆盖实际受影响的绑定与分支。管理员成功或“所有人”权限回读不能替代普通用户访问验收。
5. 无法完成普通用户验收时，说明实际完成的检查及剩余验证，不声称已解决。凭据、Cookie 和认证缓存不写入技能、源码或交付记录。
