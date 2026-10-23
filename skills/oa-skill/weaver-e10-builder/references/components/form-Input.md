## 基础用法

```js
import React, { Component, CSSProperties, ReactText } from 'react';
import { Input, constants, Icon } from '@weapp/ui';

const { Password, InputNumber, Textarea } = Input;

const prefixCls = `${constants.uiPcClsPrefix}-demo-input`;

type InputDemoState = {
  value: ReactText;
  visible: boolean;
  style?: CSSProperties;
}

class InputDemo extends Component<any, InputDemoState> {
  constructor(props: any) {
    super(props);
    this.state = {
      value: '默认内容',
      numValue: 1,
      textareaValue:'基本Textarea',
      visible: false,
      style: {
        width: 200
      }
    };
  }

  handleChange = (v: ReactText) => this.setState({ value: v })

  handleNumChange = (v: ReactText) => this.setState({numValue: v})

  handleTextareaChange = (v: ReactText) => this.setState({ textareaValue: v })

  render() {
    const { value, style, numValue, textareaValue } = this.state;
    return (
      <div className={prefixCls}>
        <Input
          style={{ width: 200 }}
          value={value}
          onChange={this.handleChange}
          placeholder="请输入内容"
          suffix={''}
        />
        <h4>受控(未注册onChange事件,数据输入无变化)</h4>
        <Input style={style} value={value} placeholder="请输入内容"/>
        <h4>只读状态(内容渲染span标签)</h4>
        <Input style={style} value={'只读状态'} readOnly/>
        <h4>只读状态(显示input)</h4>
        <Input style={style} value={'只读状态'} inputReadOnly/>
        <h4>禁用状态</h4>
        <Input style={style} placeholder="Disabled Input" disabled defaultValue={'文字超长'}/>
        <h4>可清空</h4>
        <Input defaultValue="基本Input" style={style} allowClear
               placeholder="请输入内容"/>
        <h4>密码框</h4>
        <Password
          style={style}
          defaultValue="password"
          placeholder="请输入内容"
        />
        <h4>密码框 只读</h4>
        <Password
          style={style}
          readOnly
          defaultValue="password"
          placeholder="请输入内容"
        />
        <h4>密码框 禁用</h4>
        <Password
          style={style}
          disabled
          allowClear
          defaultValue="password"
          placeholder="请输入内容"
        />

        <h4>文本框限制长度5位</h4>
        <Input style={style} value={value} onChange={this.handleChange} placeholder="请输入内容" maxLength={5}/>

        <h4>带icon的输入框</h4>
        <Input readOnly 
          style={style} 
          prefix="Date:" 
          suffix={<Icon 
          size={'s'} name={'Icon-date-o'} />} 
          placeholder="请选择日期"
          inputStyle={{ color: 'red' }}
          value={this.state.value}
         />

        <Input style={style} prefix="Search:" suffix={<Icon size={'s'} name="Icon-search" />} placeholder="请输入内容" />

        <h4>带前缀后缀的输入框</h4>
        <Input style={style} prepend="https://" append=".com.cn" defaultValue="e-cology" allowClear />

        <h4>InputNumber 数字框</h4>
        <InputNumber style={style} precision={0} placeholder={'请输入'} />
        <h4>InputNumber 数字框 数据受控</h4>
        <InputNumber style={style} min={0} max={10} value={value} onChange={this.handleNumChange} />
        <h4>InputNumber 数字框 千分位分隔符和精度</h4>
        <InputNumber defaultValue={100000} hasSeparator precision={3} style={style} />
        <h4>InputNumber 数字框 按钮位置两端显示</h4>
        <InputNumber style={style} hideOps={false} min={-3} max={10} />
        <h4>使用箭头按钮</h4>
        <InputNumber showArrow style={style} hideOps={false} align="right" />

        <h4>Textarea 多行文本框</h4>
        <Textarea style={style} onChange={this.handleTextareaChange} value={textareaValue} placeholder="请输入内容" />

        <h4>Textarea 多行文本框 高度自适应(autoHeight)</h4>
        <Textarea style={style} onChange={this.handleTextareaChange} defaultValue={textareaValue} autoHeight />

        <h4>Textarea 多行文本框 显示上限计数功能(showCount)</h4>
        <Textarea style={style} rows={3} showCount maxLength={30} allowClear value={textareaValue} onChange={this.handleTextareaChange} placeholder="请输入内容" />
      </div>
    );
  }
}
```
