## 基础用法

```tsx
import { Component } from 'react'
import { Steps, StepBaseProps, Button } from '@weapp/ui';

const datas1: Array<StepBaseProps> = [
  { title: 'First', description: 'This is description.' },
  { title: 'Second', description: 'This is description.', subTitle: 'click me' },
  { title: 'Last', description: 'This is description.',subTitle:'click me' },
]

interface MStepsDemoProps {
  weId?: string
}

interface MStepsDemoState {
  current?: number
}

export default class StepDemo extends Component<MStepsDemoProps, MStepsDemoState> {

  state = {
    current: 0,
  }

  onChange = (current: number) => {
    this.setState({ current });
  };
  
  nextStep = () => {
    this.setState((state: any) => {
      return {
        current: state.current + 1
      }
    });
  };

  render() {
    const { current } = this.state;
    return (
      <div >
        <div style={{ lineHeight: '30px' }}>基本使用 </div>
        <Steps direction="horizontal" current={current} onChange={this.onChange} data={datas1} />
        <Steps
          current={current}
          onChange={this.onChange}
          data={datas1}
        />
        <Steps
          current={current}
          onChange={this.onChange}
          direction='vertical'
          data={datas1}
        />
      </div >
    )
  }

}
```

## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| current | 指定当前步骤，从 0 开始记数 | number | 否 | |
| customRender | 自定义渲染 | (_: Component, ele: ReactNode) => ReactNode | 否 | |
| customRenderContent | 自定义渲染 | (data:StepBaseProps, index: number) => ReactNode | 否 | |
| customRenderStep | 自定义渲染 | (data:StepBaseProps, index: number) => ReactNode | 否 | |
| data | 子组件的数据 | Array | 否 | |
| direction | 展示方式 horizontal 水平 vertical 垂直 | 'horizontal' \| 'vertical' | 否 | horizontal |
| labelPlacement | 标签放置位置相对于图标的位置 | 'horizontal' \| 'vertical' | 否 | vertical |
| labelSpace | 图标和文字的距离 | Number | 否 | 10 |
| onChange | 切换步骤时的回调 | (current: number) => void | 否 | |
| style | style 样式 | CSSProperties | 否 | |
| textAlign | 水平方向步骤条的·文字对齐方式 | 'left' \| 'center' | 否 | center |

### Steps.data 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| description | 步骤的详情描述，可选 | ReactNode | 否 | |
| disabled | 禁用点击 | boolean | 否 | false |
| icon | 步骤图标的类型，可选 | string ReactElement | 否 | |
| iconColor | 图标被选中时候的颜色 | string | 否 | |
| iconStyle | 图标的背景颜色，文字颜色，边框颜色等 | CSSProperties | 否 | |
| status | 指定状态。当不配置该属性时，会使用 Steps 的 current 来自动指定状态。可选：wait process finish error | string | 否 | wait |
| subTitle | 子标题 | ReactNode | 否 | |
| title | 标题 | ReactNode | 否 | |