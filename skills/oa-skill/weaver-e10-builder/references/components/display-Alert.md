## 基础用法
```tsx
import { Component } from 'react'
import { constants, Alert, Icon } from '@weapp/ui'

const prefixCls = `${constants.uiPcClsPrefix}-demo-alert`

export default class AlertDemo extends Component<{}> {
  render() {
    return (
      <div className={prefixCls}>
        <Alert
          message="Success Text"
          type="success"
        />
        <br />
        <Alert
          message="Info Text"
          description="common LunarKK common LunarKK common LunarKK common LunarKK"
          type="info"
          showIcon
        />
        <br />
        <Alert
          message="Warning Text"
          description="Warning Description Warning Description Warning Description Warning Description"
          type="warning"
          showIcon
          closable
        />
        <br />
        <Alert
          message="Error Text"
          description="Error Description Error Description Error Description Error Description"
          icon={<Icon name="Icon-smiling-face" size={'s'} />}
          type="error"
          showIcon
          closable
        />
      </div>
    )
  }
}
```

## 参数说明
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| action | 自定义操作按钮 | ReactNode | false | |
| afterClose | 关闭动画结束后触发的回调函数 | () => void | false | |
| banner | 是否用作顶部公告 | boolean | false | |
| closable | 是否可关闭 | boolean | false | |
| closeIcon | 自定义关闭图标 | 参考 Icon 组件的 IconNames | false | |
| closeText | 自定义关闭按钮 | ReactNode | false | |
| description | 警告提示的辅助性文字介绍 | ReactNode | false | |
| icon | 自定义图标，showIcon 为 true 时有效 | ReactNode | false | |
| iconName | 自定义图标名称 | 参考 Icon 组件的 IconNames | false | |
| message | 警告提示内容 | ReactNode | false | |
| onClick | 鼠标点击的回调函数 | (e: MouseEvent) => void | false | |
| onClose | 关闭时触发的回调函数 | (e: MouseEvent) => void | false | |
| onMouseEnter | 鼠标移入的回调函数 | (e: MouseEvent) => void | false | |
| onMouseLeave | 鼠标移出的回调函数 | (e: MouseEvent) => void | false | |
| showIcon | 是否显示辅助图标 | boolean | false | banner 模式下默认值为 true |
| type | 指定警告提示的样式 | success｜info｜warning｜error | false | info，banner模式下默认值为warning |