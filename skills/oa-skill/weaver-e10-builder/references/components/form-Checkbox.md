## 基础用法

```tsx
import React from 'react';
import { Checkbox, CheckboxEvent, CheckboxDataType, CheckboxValueType, DataType, CheckboxOptionProps } from '@weapp/ui';

const prefixCls = `test-demo-checkbox`;

const optionsWithDisabled: CheckboxDataType = [
  {
    id: 'Apple',
    title: 'Apple',
    content: 'Apple',
    color: '#5D9CEC',
    tips: '我是一个提示信息'
  },
  {
    id: 'Pear',
    title: 'Pear',
    content: 'Pear',
    color: '#FF4D4F'
  },
  {
    id: 'Orange',
    title: 'Orange',
    content: 'Orange',
    disabled: true,
    color: '#52C41A'
  },
];

const defaultValue = [
  {
    id: 'Apple',
    value: 'Apple',
    content: 'Apple',
  },
];


export default class CheckboxDemo extends React.Component {
  state = {
    checked1: true,
    checked2: true,
    checked: true,
    label: "已选择",
    value: ['Apple'],
    value1: ['Apple'],
    value2: ['Apple'],
    value3: ['Apple'],
    value4: ['Apple'],
  }

  onChange1 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ checked1: value })
  }

  onChange2 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ checked2: value })
  }

  onChange3 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ value1: value })
  }
  onChange4 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ value2: value })
  }
  onChange5 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ value3: value })
  }
  onChange6 = (value: CheckboxValueType, option: CheckboxDataType, e: CheckboxEvent) => {
    this.setState({ value4: value })
  }

  onClick = (v: string | DataType, o: DataType, e: CheckboxEvent) => {}

  onBlur = (v: string | DataType, o: DataType, e: React.FocusEvent<HTMLInputElement>) => {}

  onFocus = (v: string | DataType, o: DataType, e: React.FocusEvent<HTMLInputElement>) => {}

  customOptionRender = (props: CheckboxOptionProps, ele: React.ReactNode) => {
    const option = props.option;
    return (
      <div>
        <span>自定义内容</span>
        <span>{ele}</span>
      </div>
    )
  }

  render() {
    const { checked, checked1, checked2, value, value1, value2, value3, value4 } = this.state;
    return (
      <div className={prefixCls}>
        <h4>基本用法</h4>
        <Checkbox>不受控（defaultValue）</Checkbox>
        <Checkbox value={checked2} onChange={this.onChange2}>受控（value）</Checkbox>
        <h4>只读状态</h4>
        <Checkbox readOnly>只读</Checkbox>
        <h4>禁用状态</h4>
        <Checkbox disabled>禁用</Checkbox>
        <h4>indeterminate 状态</h4>
        <Checkbox indeterminate >半选</Checkbox>
        <h4>Checkbox datas -- value</h4>
        <Checkbox data={optionsWithDisabled} value={value1} onChange={this.onChange3} />
        <h4>Checkbox datas -- defaultValue</h4>
        <Checkbox data={optionsWithDisabled} defaultValue={value} />
        <h4>Checkbox datas 垂直</h4>
        <Checkbox data={optionsWithDisabled} value={value2} vertical labelMaxWidth={'70%'} onChange={this.onChange4} />
        <h4>Checkbox datas(标签,不带check框)</h4>
        <Checkbox data={optionsWithDisabled} defaultValue={value4} optionType='tag' hideCheck onChange={this.onChange6} />
        <h4>Checkbox (check框居右)</h4>
        <Checkbox data={optionsWithDisabled} defaultValue={value4}  onChange={this.onChange6} isHoldRight/>
        <Checkbox isHoldRight>不受控（defaultValue</Checkbox>
        <h4>Checkbox (check框居右,竖向,左对齐)</h4>
        <Checkbox data={optionsWithDisabled} value={value2} vertical alignType={'left'} isHoldRight  onChange={this.onChange4} />
        <h4>Checkbox (check框居右,竖向,右对齐)</h4>
        <Checkbox data={optionsWithDisabled} value={value2} vertical alignType={'right'} isHoldRight  onChange={this.onChange4} />
        <h4>Checkbox (check框居右,竖向,两端对齐)</h4>
        <Checkbox data={optionsWithDisabled} value={value2} vertical alignType={'justify'} isHoldRight onChange={this.onChange4} />
        <h3>自定义渲染</h3>
        <Checkbox data={optionsWithDisabled} customOptionRender={this.customOptionRender}/>
      </div>
    );
  }
}
```

## 参数说明
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| alignType | 左右对齐方式（仅单个使用或者纵向排列时生效） | string | | left |
| className | 自定义 className | string | | |
| customOptionContenRender | 复写任一选项的 content 内容 | (props: RadioOptionProps, ele: ReactNode) => ReactNode | | |
| customOptionRender | 自定义每一选项 | (props: RadioOptionProps, ele: ReactNode, eventProps?: any) => ReactNode | | |
| customOverlayRender | 复写整体 radio | (_: any, ele: ReactNode) => ReactNode | | |
| data | 渲染一组 checkbox 时的数据 | CheckboxDataType | | |
| defaultValue | 默认值（单个使用时传递 Boolean) | CheckboxValueType | | |
| disabled | 禁用 | boolean | | false |
| domKey | 组件唯一标识（使用 data 时唯一标识为 data.id) | string | | |
| groupClassName | 设置外层 groupClassName（data 存在时生效） | string | | |
| groupStyle | 设置外层 style（data 存在时生效） | CSSProperties | | |
| hideCheck | 隐藏 check 框 | boolean | | false |
| indeterminate | 是否半选 | boolean | | |
| isHoldRight | checkbox 是否靠右显示 | boolean | | false |
| labelMaxWidth | label 最大宽度 (在表单中，默认生效，宽度 150，传递 0 则不生效，在竖直排列时可传递百分比,在选框居右模式下不生效) | number \| string | false | |
| minSelectMessageProps | 复写少于最少传递个数提示信息 props | DialogMessageProps | false | |
| minSelected | 设置最少选择个数 | number | false | |
| minSelectedMessage | 少于最少选择个数时提示信息 | string | false | |
| name | checkbox 的 name 属性 | string | | |
| onChange | 数据变化回调 | (value: ValueType, option: OptionData , e: RadioEvent) => void | | |
| onClick | 点击回调 | (value: ValueType, option: OptionData , e: RadioEvent) => void | | |
| optionType | 选项类型 | 'default' \| 'tag' | | 'default' |
| overlayClassName | 选项的样式名 | string | | |
| readOnlyMode | 只读模式选择（区别普通的radio只读模式和表单中仅显示字段的只读模式） | boolean | 否 | false |
| showTitle | 控制 title 是否显示 api | boolean | false | true |
| style | 自定义样式 | CSSProperties | | |
| tips | 提示信息（如果是传递了 data，直接在 data 中设置） | string | false | - |
| title | 提示文本(适用于担当适用check框情景) | string | 否 | |
| value | 受控（单个使用时传递 Boolean) | CheckboxValueType | | |
| vertical | 是否竖直排列（data 时生效） | boolean | | |