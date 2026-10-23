## 基础用法
```js
import { Component } from "react";
import { Empty, Icon, constants, Button } from "@weapp/ui";

const prefixCls = `${constants.uiPcClsPrefix}-demo-empty`;

export default class EmptyDemo extends Component {

  renderFooter = () => <Button type={'primary'}>新建流程</Button>

  render() {
    return (
      <div className={prefixCls}>
        <Empty
          title={'暂无待办流程'}
          description='您暂时还没有待办流程，可以主动发起一条试试哦~'
          image={
            <Icon
              style={{ width: 100, height: 100 }}
              name={'Icon-empty-file'
              } />
          }
        />

         <Empty
          description={
            <span>
              Customize  <a href="#API">Description</a>
            </span>
          }
          image={'https://img95.699pic.com/photo/50055/5642.jpg_wh300.jpg'}
          imageStyle={{ height: 100 }}
          renderFooter={this.renderFooter}
        />
      </div>
    )
  }
}

```

## 参数说明

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| customRender | 自定义渲染 | `(_: any, ele: React.ReactNode) => React.ReactNode` | 否 | |
| description | 次要文字描述 | `ReactNode` | 否 | |
| displayType | 展示类型 | `'404' \| 'ie'` | 否 | |
| image | 设置显示图片，为 string 时表示自定义图片地址。 | `ReactNode` | 否 | |
| imageStyle | 图片样式 | `CSSProperties` | 否 | |
| renderFooter | 自定义底部内容 | `() => ReactNode` | 否 | |
| style | style 样式 | `CSSProperties` | 否 | |
| title | 主要文字描述 | `ReactNode` | 否 | |

> 注意:
        1. 可修改 displayType 来展示 error 类型
        2. 可修改 displayType 来展示 IE浏览器支持提示