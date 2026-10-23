## 基础用法

```tsx
import React from 'react';
import { Spin } from '@weapp/ui';

class SpinDemo extends React.Component {
  render() {
    return (
      <div>
        <Spin />
        <Spin size="small" />
        <Spin size="large" />
        <Spin color='red'/>
        <Spin text="加载中。。。">
          Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
        </Spin>
      </div>
    )
  }
}
```

## 参数说明
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| color | 旋转图标颜色 | string | 否 | |
| customRender | 自定义渲染 | (_: any, ele: ReactNode) => ReactNode | 否 | |
| size | 尺寸大小 | small、large | 否 | |
| spinning | 是否显示 | boolean | 否 | false |
| style | 样式 | CSSProperties | 否 | |
| text | 加载文字 | string | 否 | |
| type | 加载模式 | circle、curve | 否 | |
| wrapperClassName | 最外层包裹样式 | string | 否 | |