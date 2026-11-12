# App切换组织

## 接口信息

- **接口名称**: appChangeTenant
- **请求方法**: `GET`
- **接口路径**: `/papi/passport/login/appChangeTenant`
- **所属控制器**: AppLoginController
- **调用方**: 客户端/App/H5调用

## 功能描述

客户端/App/H5切换组织接口，直接返回最终的ETEAMSID信息，无需重定向跳转。ETEAMSID从Cookie中获取，切换成功后接口会回写新的ETEAMSID到Cookie。

## 调用流程

```
1. 客户端调用 /papi/passport/login/appChangeTenant
2. 接口从Cookie中获取ETEAMSID
3. 切换组织成功后，接口回写新的ETEAMSID到Cookie
4. 接口直接返回包含新ETEAMSID的JSON数据
5. 客户端使用返回的ETEAMSID进行后续请求
```

## 请求参数

### 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| employeeId | Long | 是 | 人员ID（employeeId） |
| language | String | 否 | 语言设置，默认 zh_CN |

## 响应参数

| 参数名 | 类型 | 说明 |
|---|---|---|
| status | Boolean | 操作状态，true=成功 |
| eteamsid | String | 新的ETEAMSID |
| tenantkey | String | 租户Key |
| userid | Long | 用户ID |
| employeeid | Long | 人员ID |
| logintype | String | 登录类型 |

### 响应示例

```json
{
  "status": true,
  "eteamsid": "xxx",
  "tenantkey": "tenant_key_001",
  "userid": 1234567890,
  "employeeid": 9876543210,
  "logintype": "PC_ACCOUNT"
}
```

## 调用示例

```http
GET /papi/passport/login/appChangeTenant?employeeId=1234567890&language=zh_CN HTTP/1.1
Host: passport.example.com
Cookie: ETEAMSID=xxx
```

```javascript
// 客户端调用示例
const employeeId = 1234567890;

const url = `/papi/passport/login/appChangeTenant?employeeId=${employeeId}`;
fetch(url, {
  credentials: 'include' // 携带Cookie
})
  .then(response => response.json())
  .then(data => {
    if (data.status) {
      const newEteamsid = data.eteamsid;
      const tenantKey = data.tenantkey;
      // 使用新的ETEAMSID进行后续请求
    }
  });
```

## 使用场景

- 客户端/App切换租户/团队
- H5页面切换组织
- 移动端多组织账号管理
- 第三方系统对接（如workbuddy）切换组织，直接获取ETEAMSID

## 注意事项

- employeeId 为必填项
- ETEAMSID 从Cookie中自动获取，无需作为参数传递
- 接口直接返回JSON数据，包含新的ETEAMSID
- 切换成功后，接口会回写新的ETEAMSID到Cookie
- 与PC端切换组织接口不同，此接口无需重定向跳转
- 此操作为敏感操作，建议先确认用户身份和目标组织
