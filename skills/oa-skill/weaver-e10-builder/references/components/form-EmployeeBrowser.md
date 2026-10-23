## 基础用法
```ts
import React, { PureComponent } from 'react';
import { Browser} from "@weapp/ui";


class HrmBrowserDemo extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      value: []
    };
  }

  onHandleChange = (value) => {
    this.setState({value});
  }
  
  render() {
    const { value } = this.state;
    
    return (
      <Browser
        module="hrm"
        type="resource"
        multiple={true}
        value={value}
        onChange={this.onHandleChange}
      />
    )
  }
}

export default HrmBrowserDemo
```

## 具体参数

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| - | - | - | - | - |
| module | 接口的模块标示 | string| 是 | 'hrm' |
| type | 浏览按钮类别 | string | 是 | 'resource' |
| value | 浏览按钮已选数据 受控值 | object[] | 否 | - |
| onChange | 浏览按钮数据改变回调 | (data: object[]) => void | 否 | - |
| multiple | 是否多选 | boolean | 否 | - |

> 注意事项：
1. module、type这两个类型需要固定写死，不能随意修改！
2. 根据用户需求再给人员浏览框组件开启多选功能！
3. 此 `multiple` 是**页面浏览框组件**的多选 prop。**表单里的"人员字段"多选**是字段级配置——fields.json 写 `"multiple":true` 或 `form add-field --multiple`（见 `references/form/guide-create-form.md` 多选小节）。两者用途不同，别混淆。

