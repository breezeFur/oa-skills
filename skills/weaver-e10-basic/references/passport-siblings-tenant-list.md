# 查询用户所属组织列表

## 接口信息

- **接口名称**: siblingsTenantList
- **请求方法**: `GET`
- **接口路径**: `/papi/app/basicserver/siblingstenant/list`
- **所属控制器**: SiblingsTenantAppController
- **调用方**: App/H5/PC端调用

## 功能描述

查询当前登录用户所属的所有租户/组织列表。返回结果包含每个组织的基本信息（组织名称、认证状态、环境信息）、当前选中标识、外部团队标识，以及内部团队的次身份信息。

结果按认证状态排序：已认证（`verified`）的组织排在前面，未认证或其他状态排在后面。

## 调用流程

```
1. 客户端调用 /papi/app/basicserver/siblingstenant/list
2. 接口从登录态获取当前用户ID
3. 查询当前用户的所有主次身份人员信息
4. 遍历每个人员，加载其所属租户信息
5. 组装返回列表，按认证状态排序
6. 对组织名称进行国际化处理
7. 返回组织列表JSON数据
```

## 请求参数

### 凭证要求

调用前须已建立有效 `ETEAMSID` 会话（通过 `weaver-e10-login` skill），请求时携带 Cookie 或等效认证头。接口从当前登录态自动获取用户ID，无需手动传入。

### 查询参数

无。该接口无需传入任何业务参数，自动从当前登录态获取用户信息。

## 响应参数

### 响应结构

| 参数名 | 类型 | 说明 |
|---|---|---|
| code | Integer | 状态码，200=成功 |
| msg | String | 状态信息 |
| data | Array&lt;TenantEmployeeVo&gt; | 组织列表 |

### TenantEmployeeVo 结构

| 参数名 | 类型 | 说明 |
|---|---|---|
| employeeId | String | 人员ID（大整数字符串） |
| tenantKey | String | 租户Key |
| tenantName | String | 组织名称（已做国际化处理） |
| isCurrent | Boolean | 是否为当前选中的组织 |
| isAuthStatus | String | 组织认证状态，`verified`=已认证，其他为未认证或未知 |
| cid | String | IM会话ID（大整数字符串） |
| uuid | String | IM会话ID，与cid相同（大整数字符串） |
| envType | String | 环境类型 |
| envDomain | String | 环境域名 |
| externalTenant | Boolean | 是否为外部团队 |
| identityEmployee | Array&lt;BelongtoEmpInfoEx&gt; | 次身份列表（仅内部团队有此字段） |
| jobNum | String | 工号 |
| departmentOutKey | String | 部门表outKey |
| employeeLoginName | String | 登录名 |

### BelongtoEmpInfoEx 结构（次身份信息）

| 参数名 | 类型 | 说明 |
|---|---|---|
| id | Long | 次身份人员ID |
| tenantKey | String | 租户Key |
| name | String | 人员姓名 |
| accounttype | Integer | 账号类型，0=主身份，非0=次身份 |
| current | Boolean | 是否为当前选中的次身份 |
| departmentId | Long | 部门ID |
| departmentName | String | 部门名称 |
| employeeLoginName | String | 登录名 |
| jobNum | String | 工号 |
| departmentOutKey | String | 部门表outKey |

### 响应示例

```json
{
  "code": 200,
  "msg": "ok",
  "data": [
    {
      "employeeId": "1234567890123456789",
      "tenantKey": "tenant_key_001",
      "tenantName": "示例科技有限公司",
      "isCurrent": true,
      "isAuthStatus": "verified",
      "cid": "9876543210987654321",
      "uuid": "9876543210987654321",
      "envType": "0",
      "envDomain": "",
      "externalTenant": false,
      "identityEmployee": [
        {
          "id": 1234567890123456789,
          "tenantKey": "tenant_key_001",
          "name": "张三",
          "accounttype": 0,
          "current": true,
          "departmentId": 1111111111111111111,
          "departmentName": "技术部",
          "employeeLoginName": "zhangsan",
          "jobNum": "EMP001",
          "departmentOutKey": "DEPT001"
        }
      ],
      "jobNum": "EMP001",
      "departmentOutKey": "DEPT001",
      "employeeLoginName": "zhangsan"
    },
    {
      "employeeId": "2222222222222222222",
      "tenantKey": "tenant_key_002",
      "tenantName": "外部合作公司",
      "isCurrent": false,
      "isAuthStatus": null,
      "cid": "3333333333333333333",
      "uuid": "3333333333333333333",
      "envType": "0",
      "envDomain": "",
      "externalTenant": true,
      "identityEmployee": null,
      "jobNum": null,
      "departmentOutKey": null,
      "employeeLoginName": "zhangsan_ext"
    }
  ]
}
```

## 调用示例

```http
GET /papi/app/basicserver/siblingstenant/list HTTP/1.1
Host: basic-web.example.com
Cookie: ETEAMSID=xxx
```

```javascript
// 前端调用示例
fetch('/papi/app/basicserver/siblingstenant/list', {
  credentials: 'include'
})
  .then(response => response.json())
  .then(data => {
    if (data.code === 200) {
      const tenants = data.data;
      tenants.forEach(tenant => {
        console.log(`${tenant.tenantName} ${tenant.isCurrent ? '(当前)' : ''}`);
      });
    }
  });
```

## 业务逻辑说明

1. **主次身份解析**：接口通过 `getBelongtoEmployeesByUserId` 获取当前用户的所有主次身份人员，以主身份 employeeId 为 key，次身份列表为 value。
2. **外部团队过滤**：外部团队（`EmployeeType.external`）会被标记 `externalTenant=true`，且其次身份信息不会返回（`identityEmployee` 为 null）。
3. **外部团队限制**：系统可配置外部团队限制（`externalLimitTenantKeys`），被限制的外部团队不会出现在返回列表中。
4. **组织名称过滤**：名称以「初始团队-年会」开头的组织会被自动过滤，不出现在返回列表中。
5. **排序规则**：当组织数量 > 1 时，已认证（`verified`）的组织排在前面，未认证或其他状态排在后面。
6. **国际化**：组织名称会根据当前语言设置进行国际化处理。
7. **当前组织标识**：`isCurrent=true` 标识当前选中的组织。对于内部团队，匹配当前 employeeId；对于外部团队，匹配当前 tenantKey。

## 使用场景

- 查询当前用户所属的所有组织/团队列表
- 展示组织切换面板的可选组织
- 判断当前用户是否为外部团队成员
- 获取当前用户的主次身份信息
- 多组织账号管理

## 注意事项

- 该接口无需传入参数，自动从登录态获取用户信息
- 所有大整数 ID（employeeId、cid、uuid）以字符串形式返回
- 外部团队没有 `identityEmployee`（次身份）字段
- 组织名称已做国际化处理，无需前端再次转换
- 该接口为只读查询接口，无副作用
