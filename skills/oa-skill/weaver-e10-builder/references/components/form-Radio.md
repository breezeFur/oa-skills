## 基础用法
```tsx
import React from 'react';
import { constants, Radio, RadioValueType, RadioOptionType, RadioEvent, RadioDataType } from '@weapp/ui';

const prefixCls = `${constants.uiPcClsPrefix}-demo-radio`;

const optionsWithDisabled: RadioDataType = [
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

const defaultValue =
{
  id: 'Apple',
  value: 'Apple',
  content: 'Apple'
};

export default class RadioDemo extends React.Component {

  state = {
    checked: true,
    label: "已选择",
    value: 'Apple'
  }

  onClick = (v: RadioValueType, o: RadioOptionType, e: RadioEvent) => {
    console.log('onClick', v, o, e)
  }
  onBlur = (v: RadioValueType, o: RadioOptionType, e: React.FocusEvent<HTMLInputElement>) => {
    console.log('onBlur', v, o, e)
  }
  onFocus = (v: RadioValueType, o: RadioOptionType, e: React.FocusEvent<HTMLInputElement>) => {
    console.log('onFocus', v, o, e)
  }
  onKeyPress = (v: RadioValueType, o: RadioOptionType, e: React.KeyboardEvent<HTMLInputElement>) => {
    console.log('onKeyPress', v, o, e)
  }
  onKeyDown = (v: RadioValueType, o: RadioOptionType, e: React.KeyboardEvent<HTMLInputElement>) => {
    console.log('onKeyDown', v, o, e)
  }
  onKeyUp = (v: RadioValueType, o: RadioOptionType, e: React.KeyboardEvent<HTMLInputElement>) => {
    console.log('onKeyUp', v, o, e)
  }

  onChange1 = (v: RadioValueType, o: RadioOptionType, e: RadioEvent) => {
    console.log('onChange1', v, o, e)
  }

  onChange = (v: RadioValueType, o: RadioOptionType, e: RadioEvent) => {
    console.log('onChange', v, o, e)
    this.setState({ value: v })
  }
  btnClick = () => {
    this.setState({ value: !this.state.value })
  }

  render() {
    const { checked, value } = this.state;
    return (
      <div className={prefixCls}>
        <h4>基本用法</h4>
        <Radio defaultValue={false}
          onChange={this.onChange1}
          onClick={this.onClick}
          onFocus={this.onFocus}
          onBlur={this.onBlur}
        >Apple</Radio>
        <Radio value={checked} onChange={this.onChange1} onFocus={this.onFocus} onBlur={this.onBlur} onKeyPress={this.onKeyPress} onKeyDown={this.onKeyDown} onKeyUp={this.onKeyUp}>受控</Radio>
        <h4>只读状态</h4>
        <Radio readOnly>只读</Radio>
        <h4>禁用状态</h4>
        <Radio disabled>禁用</Radio>
        <Radio value={true} disabled>禁用</Radio>
        <h4>Radio datas -- value</h4>
        <Radio data={optionsWithDisabled} value={value} defaultValue={'Apple'} readOnly onChange={this.onChange} />
        <h4>Radio datas 垂直</h4>
        <Radio data={optionsWithDisabled} value={value} vertical onChange={this.onChange} />
        <h4>Radio datas 标签样式</h4>
        <Radio data={optionsWithDisabled} defaultValue={value} optionType='tag' onChange={this.onChange}/>
        <h4>Radio datas 标签样式(不带check框)</h4>
        <Radio data={optionsWithDisabled} value={value} optionType='tag' hideCheck onChange={this.onChange} />
        <h4>Checkbox (check框居右)</h4>
        <Radio data={optionsWithDisabled} defaultValue={value}  onChange={this.onChange} isHoldRight/>
        <Radio isHoldRight>不受控（defaultValue）</Radio>
        <h4>Radio (check框居右,竖向,左对齐)</h4>
        <Radio data={optionsWithDisabled} value={value} vertical alignType={'left'} isHoldRight  onChange={this.onChange} />
        <h4>Radio (check框居右,竖向,右对齐)</h4>
        <Radio data={optionsWithDisabled} value={value} vertical alignType={'right'} isHoldRight  onChange={this.onChange} />
        <h4>Radio (check框居右,竖向,两端对齐)</h4>
        <Radio data={optionsWithDisabled} value={value} vertical alignType={'justify'} isHoldRight onChange={this.onChange} />
      </div>
    );
  }
}
```

## 参数说明
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| canReversedChoose | 是否开启反选 | boolean | 否 | true |
| className | 自定义 className | string | 否 | |
| customOptionContenRender | 复写任一选项的 content 内容 | (props: RadioOptionProps, ele: ReactNode) => ReactNode | 否 | |
| customOptionRender | 自定义每一选项 | (props: RadioOptionProps, ele: ReactNode, eventProps?: any) => ReactNode | 否 | |
| customOverlayRender | 复写整体 radio | (_: any, ele: ReactNode) => ReactNode | 否 | |
| defaultValue | 默认值（单个使用时传递 Boolean) | RadioValueType | 否 | |
| disabled | 禁用 | boolean | 否 | false |
| domKey | 单个使用 radio 时，radio 的唯一标识（使用 data 时唯一标识为 data 的 id） | RadioValueType | 否 | |
| groupClassName | 设置外层 groupClassName（data 存在时生效） | string | 否 | |
| groupStyle | 设置外层 style（data 存在时生效） | CSSProperties | 否 | |
| hideCheck | 隐藏 check 框 | boolean | 否 | false |
| isHoldRight | checkbox 是否靠右显示 | boolean | | false |
| labelMaxWidth | label 最大宽度 (在表单中，默认生效，宽度 150，传递 0 则不生效,在选框居右模式下不生效) | number | 否 | |
| name | radio 的 name 属性 | string | 否 | |
| onBlur | blur 回调 | (value: RadioValueType, option: RadioOptionType , e: React.FocusEvent<HTMLInputElement>) => void | 否 | |
| onChange | 数据变化回调 | (value: RadioValueType, option: RadioOptionType , e: RadioEvent) => void | 否 | |
| onClick | 点击回调 | (value: RadioValueType, option: RadioOptionType , e: RadioEvent) => void | 否 | |
| onFocus | focus 回调 | (value: RadioValueType, option: RadioOptionType , e: React.FocusEvent<HTMLInputElement>) => void | 否 | |
| optionType | 选项类型 | 'default' \| 'tag' | 否 | 'default' |
| overlayClassName | 选项的样式名 | string | 否 | |
| readOnlyMode | 只读模式选择（区别普通的radio只读模式和表单中仅显示字段的只读模式） | boolean | 否 | false |
| showTitle | 控制 title 是否显示 api | boolean | 否 | true |
| style | 自定义样式 | CSSProperties | 否 | |
| tips | 提示信息（如果是传递了 data，直接在 data 中设置） | string | false | - |
| value | 受控（单个使用时传递 Boolean) | RadioValueType | 否 | |
| vertical | 是否竖直排列（data 存在时生效） | boolean | 否 | |