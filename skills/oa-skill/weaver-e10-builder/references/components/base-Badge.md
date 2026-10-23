## 基础用法

```js
import { Component } from "react";
import { Badge, constants, Icon } from "@weapp/ui";

const prefixCls = `${constants.uiPcClsPrefix}-demo-badge`;

class BadgeDemo extends Component {
  render() {
    return (
      <div className={prefixCls}>
        <Badge className={`${prefixCls}-item`} count={5} showBorder>
          <div className={`${prefixCls}-item-children`} />
        </Badge>
        <Badge className={`${prefixCls}-item`} count={0} showBorder showZero>
          <div className={`${prefixCls}-item-children`} />
        </Badge>

        <h3>封顶数字</h3>
        <Badge className={`${prefixCls}-item`} count={99} showBorder>
          <div className={`${prefixCls}-item-children`} />
        </Badge>
        <Badge
          className={`${prefixCls}-item`}
          count={1000}
          showBorder
          overflowCount={999}
        >
          <div className={`${prefixCls}-item-children`} />
        </Badge>

        <h3>不同尺寸</h3>
        <Badge className={`${prefixCls}-item`} count={5} showBorder>
          <div className={`${prefixCls}-item-children`} />
        </Badge>
        <Badge
          className={`${prefixCls}-item`}
          count={5}
          showBorder
          size="small"
        >
          <div className={`${prefixCls}-item-children`} />
        </Badge>

        <h3>自定义</h3>
        <Badge
          className={`${prefixCls}-item`}
          count={<Icon name="Icon-Speechless" size="sm" />}
        >
          <div className={`${prefixCls}-item-children`} />
        </Badge>

        <h3>独立使用(不配children)</h3>
        <Badge className={`${prefixCls}-item`} count={5}></Badge>
        <Badge className={`${prefixCls}-item`} count={0} showZero></Badge>
        <Badge className={`${prefixCls}-item`} count={100} showBorder></Badge>
        <Badge
          className={`${prefixCls}-item`}
          count={1000}
          overflowCount={999}
        ></Badge>

        <h3>小红点</h3>
        <Badge className={`${prefixCls}-item`} dot>
          文本标记
        </Badge>

        <h3>自定义位置偏移量</h3>
        <Badge className={`${prefixCls}-item`} dot offset={[0, "100%"]}>
          <div className={`${prefixCls}-item-children`} />
        </Badge>
        <Badge className={`${prefixCls}-item`} count={5} offset={[10, -10]}>
          <div className={`${prefixCls}-item-children`} />
        </Badge>
      </div>
    );
  }
}

export default BadgeDemo;
```

## 具体参数

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
|------|------|------|----------|--------|
| children | 包裹在徽标内的组件 | React.ReactNode | 否 | - |
| color | 徽标颜色，dot 和 ribbon 效果使用 | `'blue' \| 'purple' \| 'cyan' \| 'green' \| 'magenta' \| 'pink' \| 'red' \| 'orange' \| 'yellow' \| 'volcano' \| 'geekblue' \| 'lime' \| 'gold' \| 自定义颜色` | 否 | - |
| count | 展示的数字 | React.ReactNode | 否 | - |
| dot | 是否为小红点效果 | boolean | 否 | false |
| offset | 徽标位置偏移量 [top, right]，dot 和 count 效果使用 | `[ number \| string, number \| string ]` | 否 | - |
| overflowCount | count 最大限制 | number | 否 | - |
| ribbon | 是否显示为缎带效果 | boolean | 否 | false |
| showBorder | 是否展示白色边框，dot 和 count 效果使用 | boolean | 否 | false |
| showZero | count 数量为 0 的 count | boolean | 否 | false |
| size | 徽标尺寸，仅 count 效果使用 | `'default' \| 'small'` | 否 | `'default'` |
| status | 徽标状态，dot 和 count 效果使用 | `'success' \| 'primary' \| 'error' \| 'warning' \| 'disabled'` | 否 | - |
| text | 徽标内文本，count 和 ribbon 效果使用 | React.ReactNode | 否 | - |
| title | 设置鼠标放在状态点上时显示的文字 | string | 否 | - |
