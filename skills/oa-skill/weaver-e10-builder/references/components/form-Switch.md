## 基础用法
```js
import React from 'react';
import { Switch, SwitchChangeEventHandler, SwitchClickEventHandler } from '@weapp/ui';

class SwitchDemo extends React.Component {

  state = {
    checked: false,
    isLoading: true
  }

  handleClick: SwitchClickEventHandler = (checked, e) => {
    this.setState({ checked: !this.state.checked, isLoading: !this.state.isLoading })
  }

  render() {
    const { checked, isLoading } = this.state;
    return (
      <div>
        <h3>基础用法</h3>
        <div style={{width: '140px', display: 'flex',justifyContent: 'space-between'}}>
        <Switch size="sm" />
        <Switch size="md" loading={isLoading} />
        <Switch size="lg" value={checked} onClick={this.handleClick}/>
        </div>
      </div>
    );
  }
}
```

## 参数配置

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| checkedChildren | 选中时的内容 | `React.ReactNode` | 否 | |
| defaultValue | 默认是否选中 | `boolean` | 否 | |
| loading | 加载中的开关 | `boolean` | 否 | |
| loadingIcon | switch 加载中图标 | `React.ReactNode` | 否 | |
| onBeforeChange | 变化前回调 | `(checked: boolean, e: React.MouseEvent \| React.KeyboardEvent) => Promise` | 否 | |
| onChange | 变化回调 | `(checked: boolean, event: React.MouseEvent \| React.KeyboardEvent) => void` | 否 | |
| onClick | 点击事件回调 | `SwitchClickEventHandler` | 否 | |
| size | switch 大小 | `'sm' \| 'md' \| 'lg'` | 否 | |
| unCheckedChildren | 非选中时的内容 | `React.ReactNode` | 否 | |
| value | 是否选中（受控） | `boolean` | 否 | |
