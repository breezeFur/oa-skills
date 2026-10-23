# Skill Ebcoder 目录索引

> 此文件列出所有子文档的加载条件，供 Agent 按需加载。不要一次性加载全部。
>
> 以下所有路径统一写作 `references/...`：相对工作区根目录（`skill copy` 拷出的位置），或本机 skill 根目录（完整安装自带）。

## Guides（编码指南）

| 用户意图关键词 | 加载文档 |
|---------------|---------|
| 表单CRUD、增删改查、getSimpleData、withDisplayNames、getFieldOptions、saveFormData、updateFormData、deleteFormData、字段类型 | `references/coding/guide-form-crud.md`（前端代码） |
| 编辑、修改、回显、handleEdit、getAllData、rawData、selectedPerson、editForm、数据回填 | `references/coding/guide-edit-backfill.md`（前端代码） |
| 显隐联动、条件显示、form linkage、为空/不为空条件、NULL 算子 | `references/form/guide-form-linkage.md` |
| 函数联动、本表字段公式赋值、赋值式公式、EXCEL 公式联动、字段自动计算、form formula-linkage、wf-form formula-linkage、流程表单函数联动、值改变时、载入时触发、当前工作流生效 | `references/form/guide-formula-linkage.md` |
| 字段联动、跨表带出、field-linkage、多跳带出、带出字段赋值、Text 字段取名称 | `references/form/guide-field-linkage.md` |
| 新建表单、form create、EB 表单标准创建流程 | `references/form/guide-create-form.md` |
| 二级明细、子明细、父级行标识、子级行标识、多级明细 | `references/form/guide-form-sub-detail.md` |
| 物理表、多物理表、附属物理表、saveFormTable、getFormAGroupList、字段管理其他页签、字段超过100、add-physical-table、add-physical-field | `references/form/guide-form-physical-table.md` |
| 虚拟表、虚拟表单、数据源表单、业务表展示、数据加工结果 | `references/form/guide-virtual-form.md` |
| 字段定义、字段类型、关联字段码表、DateRange、multiple | `references/form/ref-form-fields.md` |
| FLOW/EXCEL、布局样表、布局蓝图、字段分组、singleRow | `references/form/guide-form-layout-planning.md` |
| 布局样式模板、换配色、form layout init | `references/form/style-templates.md`（流式/表格式两套，同名不同 id） |
| 已有表单加字段、改必填/只读、布局被重建、add-field --reinit、别动别人的表、布局组件、associatedId、字段标题取不到 | `references/form/guide-form-layout-incremental.md` |
| 表单复杂编号、serial-mark、流水号、代字 | `references/form/guide-form-serial-mark.md` |
| 表单数据读写、form data、写入数据、查询数据、删除数据 | `references/form/guide-form-data.md` |
| 列表自定义文本列、富文本列、列里插入字段、form nlist、列表式视图 | `references/form/guide-list-custom-text.md` |
| 流程、审批、workflow、提交流程、flowpage、预填、URL传参、节点、操作者、审批人、连线 | `references/workflow/guide-workflow.md` |
| 流程绑的表、流程关联表单、workflow info、workflowId 查表单、formId 不是 objId | `references/common/ref-cli-commands.md`（`workflow info` 一行） |
| 权责表、权责矩阵、权责表方式流程、分支场景、变量映射 | `references/workflow/guide-workflow-auth-resp.md` + `references/workflow/guide-workflow-condition.md` |
| 公文流程、公文审批、收文、发文、公文设置、正文设置 | `references/workflow/guide-workflow-odoc.md` + `references/workflow/guide-workflow.md` |
| 分支条件、出口条件、条件JSON、save-condition、连线条件、condition add | `references/workflow/guide-workflow-condition.md` |
| 条件操作符编码、字段类型矩阵、关系符 | `references/workflow/operator-matrix.md` |
| 动作流、跨表单、写入台账、ActionEbAdd/ActionEbUpdate/ActionEbDelete、提交事件、自定义事件触发、内置MQ监听/发送、HTTP/HTTPS、DML/数仓 | `references/workflow/guide-workflow-action.md`；复杂动作流组件契约按需读取 `actionflows/SKILL.md` 及其 `references/components/` |
| 鉴权、登录、auth、ETEAMSID、多环境、profile、切换环境 | `references/auth/guide-auth.md` |
| HRM矩阵、条件矩阵、部门矩阵、分部矩阵、matrix、映射表、行 id、rowId、syncType | `references/hrm/guide-matrix.md` |
| 报表、设计器报表、EDC报表、新建报表、report build、数据集、报表列、父格、合并、冻结、tableName | `references/report/guide-report-build.md`（建表主干）· `guide-report-modify.md`（改已有）· `ref-report-pitfalls.md`（先扫坑） |
| 报表查询条件、高级搜索、筛选、queryType、默认值三件套 | `references/report/guide-report-query.md`；细则 `query-condition-api-guide.md` |
| 报表命令、report 子命令、report build/verify/fix/scope/snapshot | `references/report/ref-report-commands.md` |
| 报表接口、saveReportDevInfo、addDataset、getReportDevInfo、报表落库流程 | `references/report/api-report-build-fast-path.md` · `report-config-schema.md`（配置结构） · `report-data-model.md`（枚举） |
| 报表单元格模型、cellType、displayType、expandType、groupType、countType | `references/report/report-data-model.md` · `report-config-schema.md` |
| 报表权限、共享范围、viewRight、权责矩阵 | `references/report/report-permission-guide.md` |
| 报表版本、快照、生命周期、回收站、复制挂菜单 | `references/report/report-lifecycle-api-guide.md` |
| 报表条件格式、数据条、图标集 | `references/report/condition-format-guide.md` |
| 新页面、导出、路由、entry.js、regOvProps、regReactChildren、asyncImport、publicUrl、Suspense | `references/coding/guide-page-export.md`（前端代码） |
| 写页面、页面代码、React编码、组件、entry.js模板 | `references/coding/guide-page-code.md`（前端代码） |
| 页面设计器、配置式页面、仪表盘、看板页、designer、page create、comp-add、工厂模板、factory、组件模板、页面布局、designer layout/save、页面版本、version revert、发布页面菜单、publish-menu、自定义CSS、组件样式、选择器、DOM结构、样式不生效 | `references/ebuilder-designer/guide-designer.md`（布局层主干）· `guide-designer-components.md`（组件 config）· `guide-designer-factory.md`（工厂模板）· `guide-designer-version.md`（版本）· `guide-designer-css.md`（自定义 CSS 与 DOM 结构索引） |

## Reference（参考手册）

| 用户意图关键词 | 加载文档 |
|---------------|---------|
| CLI、命令、打包、build、import、创建应用、创建表单、菜单、project、form create、app create、matrix | `references/common/ref-cli-commands.md` |
| 接口文档导入、Postman、系统接口、连接器接口、createSystemInterfaceByAi、接口批量创建 | `references/esb-interface/guide-import.md` |
| 系统菜单、内置菜单、挂系统页面到菜单、menuUrl、pageType、工作流菜单、独立页面菜单、菜单改名、menu rename、重命名菜单、找不到菜单 | `references/menu/system-menus.md` |
| 编译、语法、报错、不支持、babel、打包、var、const、let、es2015、stage-2 | `references/coding/ref-compile-rules.md`（前端代码） |

## Components（组件文档）

| 用户意图关键词 | 加载文档 |
|---------------|---------|
| Button、按钮 | `references/components/@weapp-Button.md` |
| Table、表格 | `references/components/display-Table.md` |
| List、列表 | `references/components/display-List.md` |
| Pagination、分页 | `references/components/display-Pagination.md` |
| Icon、图标 | `references/components/display-Icon.md` |
| Avatar、头像 | `references/components/display-Avatar.md` |
| EChart、图表、Echarts | `references/components/generic-Echarts.md` |
| 文件预览、CorsComponent | `references/components/display-FilePreview.md` |
| Input、输入框、文本框 | `references/components/form-Input.md` |
| 人员选择、Browser Employee、resource | `references/components/form-EmployeeBrowser-api.md` |
| 部门选择、Browser Department、department | `references/components/form-DepartmentBrowser-api.md` |
| Upload、文件上传、附件、FileComponent | `references/components/form-Upload.md` |
| Badge、徽标 | `references/components/base-Badge.md` |
| Tag、标签 | `references/components/base-Tag.md` |

## 组合场景

| 场景 | 需加载的文档 |
|------|-------------|
| CRUD 列表页 | `references/coding/guide-form-crud.md`（前端代码） + `references/components/display-Table.md` + `references/components/display-Pagination.md` |
| 表单新增/编辑弹窗 | `references/coding/guide-form-crud.md`（前端代码） + `references/coding/guide-edit-backfill.md` + 对应表单组件文档 |
| 新建完整应用 | `references/common/ref-cli-commands.md` + `references/form/guide-create-form.md` + `references/coding/guide-page-export.md`（前端代码） |
| 流程触发页面 | `references/workflow/guide-workflow.md` + `references/coding/guide-form-crud.md`（前端代码） |
| 流程分支条件 | `references/workflow/guide-workflow.md` + `references/workflow/guide-workflow-condition.md` |
| 跨表单动作流 | `references/workflow/guide-workflow.md` + `references/workflow/guide-workflow-action.md` |
| 编译报错排查 | `references/coding/ref-compile-rules.md`（前端代码） |
