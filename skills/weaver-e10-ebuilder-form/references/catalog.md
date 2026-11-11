# eBuilder 表单数据接口索引

只有 `/api/ebuilder/form/**` 路径使用共享上下文已经确定的 `{apiPrefix}`；独立部署时为 `/api/ebuilder{appId}`。`/api/ebuilder/common/**` 始终使用公共路径，不拼接 `appId`。

## 浏览字段

人员、部门、分部、审批、文档及其他关联浏览字段需要把业务名称解析成可选项 ID 时，读取[按名称查询人员、部门和关联数据](browser-fields.md)，运行 `../../scripts/query_browser_field.py`。这类字段不使用普通选项接口代替。

## OpenAPI

| 能力 | 方法 | 路径 | 文档 |
|---|---|---|---|
| 新建表单数据 | POST | `{apiPrefix}/form/dataset/v2/saveFormData` | [新建](ebuilder-openapi-formdata-saveformdata.md) |
| 修改表单数据 | POST | `{apiPrefix}/form/dataset/v2/updateFormData` | [修改](ebuilder-openapi-formdata-updateformdata.md) |
| 删除表单数据 | POST | `{apiPrefix}/form/dataset/v2/deleteData` | [删除](ebuilder-openapi-formdata-deletedata.md) |
| 获取数据详情 | POST | `{apiPrefix}/form/dataset/v2/getDataById` | [详情](ebuilder-openapi-formdata-getdatabyid.md) |
| 获取表单级分页 | POST | `{apiPrefix}/form/dataset/v2/getAllData` | [分页](ebuilder-openapi-formdata-getalldata.md) |
| 获取表单级总数 | POST | `{apiPrefix}/form/dataset/v2/getAllDataCount` | [总数](ebuilder-openapi-formdata-getalldatacount.md) |
| 获取表单字段 | POST multipart | `/api/ebuilder/common/ds/fields` | [字段](ebuilder-openapi-formdata-getfields.md) |
| 获取字段选项 | GET | `/api/ebuilder/common/ds/options` | [选项](ebuilder-openapi-formdata-getoptions.md) |
| 获取主明细映射 | GET | `{apiPrefix}/form/dataset/v1/getTableMapping` | [映射](ebuilder-openapi-formdata-gettablemapping.md) |

执行数据操作前优先读取 [OpenAPI 公共说明](ebuilder-openapi-common.md)。

## 自定义接口

| 能力 | 配置类型 | 方法 | 路径 | 文档 |
|---|---|---|---|---|
| 新增表单数据 | `addData` | POST | `{apiPrefix}/form/formdata/v2/saveFormData/{interfacePk}` | [新增](ebuilder-customapi-formdata-add.md) |
| 修改表单数据 | `editData` | POST | `{apiPrefix}/form/formdata/v2/updateFormData/{interfacePk}` | [修改](ebuilder-customapi-formdata-update.md) |
| 删除表单数据 | `delData` | POST | `{apiPrefix}/form/formdata/v2/deleteFormData/{interfacePk}` | [删除](ebuilder-customapi-formdata-delete.md) |
| 查询数据详情 | `getDataDetail` | POST | `{apiPrefix}/form/formdata/v2/getFormDataByPk/{interfacePk}` | [详情](ebuilder-customapi-formdata-querybypk.md) |
| 分页查询数据 | `getListData` | POST | `{apiPrefix}/form/formdata/v2/getFormDataList/{interfacePk}` | [分页](ebuilder-customapi-formdata-querypagedata.md) |
| 查询数据总数 | `getListCount` | POST | `{apiPrefix}/form/formdata/v2/getFormDataCount/{interfacePk}` | [总数](ebuilder-customapi-formdata-count.md) |

分页和总数必须使用相同的 `interfacePk`、配置条件、输入字段和操作人上下文。
