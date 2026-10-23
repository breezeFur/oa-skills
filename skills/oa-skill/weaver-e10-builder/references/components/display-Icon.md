# Icon - 图标组件

> **重要：严禁自行编造图标名称！** 所有图标名必须通过 `e10-cli icon search {关键词}` 搜索获得，搜索结果中不存在的一律不准使用。不得凭记忆或猜测填写 name 属性。

## 组件说明

图标组件，支持内置图标、自定义SVG图标、iconfont图标等多种类型。

## Props 参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| name | `IconNames` | 否 | - | 图标名称 |
| component | `React.ReactNode` | 否 | - | 自定义图标组件 |
| size | `'xxs' \| 'xs' \| 's' \| 'sm' \| 'md' \| 'lg'` | 否 | `md` | 图标大小 |
| url | `string` | 否 | - | 图标图片地址 |
| moduleColor | `moduleType` | 否 | - | 模块颜色 |
| fromIconfontCN | `CustomIconOptions` | 否 | - | iconfont图标配置 |

## 用法示例

### 基础用法

```tsx
import { Icon } from '@weapp/ui';

const App = () => {
  return <Icon name="Icon-md02-mcolor" />;
};
```

### 自定义大小

```tsx
<Icon name="Icon-md02-mcolor" size="lg" />
```

### 自定义颜色

```tsx
<Icon name="Icon-md02-mcolor" style={{ color: '#1890ff' }} />
```

### 自定义图标组件

```tsx
<Icon component={<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>} />
```

### Iconfont 图标

```tsx
<Icon
  fromIconfontCN={{
    scriptUrl: '//at.alicdn.com/t/font_xxx.js',
  }}
  name="icon-name"
/>
```

## 注意事项

1. `name` 为内置图标名称，具体参考图标库文档
2. `size` 支持6种尺寸：xxs(12px)、xs(14px)、s(16px)、sm(18px)、md(20px)、lg(24px)
3. `component` 优先级最高，其次是 `url`，最后是 `name`
4. `fromIconfontCN` 用于加载 iconfont 图标