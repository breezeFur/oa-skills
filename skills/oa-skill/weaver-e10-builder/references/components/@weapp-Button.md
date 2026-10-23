## 基础用法

```
import React, { Component } from 'react';
import { Button, Icon, constants } from '@weapp/ui';
import { getLabel } from '@weapp/utils';

const prefixCls = `${constants.uiPcClsPrefix}-demo-btn`;

class ButtonDemo extends Component {
  handleBeforeClick = () => {
    console.log('before click called');
    return new Promise((resolve, reject) => {
      console.log('interrupt click');
      reject();
    });
  }
  handleClick = () => {
    console.log('click callback');
  }
  render() {
    return (
      <div className={prefixCls}>
        <h3>不同类型</h3>
        <Button title="次要按钮" type="default">次要按钮</Button>
        <Button type="primary">主要按钮</Button>
        <Button type="success">成功按钮</Button>
        <Button type="warning">警告按钮</Button>
        <Button type="danger">危险按钮</Button>
        <h3>内容很长时候隐藏</h3>
        <Button style={{ width: 100 }} type="danger">内容很长内容很长内容很长</Button>
        <h3>设置圆角</h3>
        <Button radius type="default">次要按钮</Button>
        <Button radius type="primary">主要按钮</Button>
        <Button radius type="success">成功按钮</Button>
        <Button radius type="warning">警告按钮</Button>
        <Button radius type="danger">危险按钮</Button>
        <h3>禁用按钮</h3>
        <Button disabled >禁用按钮</Button>
        <Button disabled radius >禁用按钮</Button>
        <Button type="danger" disabled radius >禁用按钮</Button>
        <h3>调整尺寸</h3>
        <Button size="large">large</Button>
        <Button size="middle">middle</Button>
        <Button size="small">small</Button>
        <h3>自定义按钮</h3>
        <Button type="primary">
          <Icon style={{ width: 15, height: 15 }} name="Icon-search" />
        </Button>
        <Button disabled>
          <Icon style={{ width: 15, height: 15 }} name="Icon-search" />
        </Button>
        <h3>文字按钮</h3>
        <Button type="link">文字按钮</Button>
        <Button type="link" disabled>禁用</Button>
      </div>
    );
  }
}

export default ButtonDemo;
```

## hook 的使用
```
import React, { Component } from 'react';
import { Button, constants, utils } from '@weapp/ui';

const prefixCls = `${constants.uiPcClsPrefix}-demo-btn`;

class ButtonDemo extends Component {
  handleBeforeClick = () => {
    console.log('before click called');
    return new Promise((resolve, reject) => {
      console.log('interrupt click');
      reject();
    });
  }
  handleClick = () => {
    console.log('click callback');
  }
  onClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const { pauseEvent } = utils;
    pauseEvent(e)
  }
  render() {
    return (
      <div className={prefixCls}>
        <h2>onBeforeClick</h2>
        <Button onBeforeClick={this.handleBeforeClick} onClick={this.handleClick}>中断click</Button>
        <Button onClick={this.onClick}>click</Button>
      </div>
    );
  }
}

export default ButtonDemo;
```

参数	说明	类型	是否必填	默认值
disabled	禁用	boolean	否	false
inline	是否设置为整行按钮（是否默认宽度 100%）	boolean	否	false
onAfterClick	点击事件方法执行后钩子	(this) => void;	否	
onBeforeClick	点击事件方法执行前钩子	(this) => void;	否