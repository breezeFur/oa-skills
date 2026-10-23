## 基础用法

```tsx
import { Component } from 'react';
import { Title, Button, constants } from '@weapp/ui';

const dataItem = {
  icon: null,
  disabled: false,
  closeable: false,
  closeIcon: null,
  data: [],
};

const data1 = [
  { ...dataItem, id: 'tab1', content: '可选标签2' },
  { ...dataItem, id: 'tab2', content: '可选标签3' },
  { ...dataItem, id: 'tab3', content: '可选标签4' },
  { ...dataItem, id: 'tab4', content: '可选标签5' },
]

interface TitleDemoProps {

}

interface TitleDemoState {
  menuValue: string;
}

class TitleDemo extends Component {
  constructor(props: TitleDemoProps) {
    super(props);
    this.state = {
      menuValue: 'tab1',
    }
  }

  onMenuChange = (key: any) => this.setState({ menuValue: key });

  render() {
    const { menuValue } = this.state;
    return (
      <>
        <Title title={'基本用法'} />
        <Title title={'无底部边线'} hideUnderLine />
        <Title title={'无图标'} noIcon />
        <Title icon='Icon-smiling-face' iconBgcolor='red' title={'自定义图标'}  />
        <Title title={'自定义右侧按钮'}
          buttons={[
            <Button key='a'>打开</Button>,
            <Button key='b'>跳转</Button>,
          ]}
        />
        <Title title={'自定义页签'}
          menuValue={menuValue}
          menus={data1}
          inDialog
          onMenuChange={this.onMenuChange}
          buttons={[<Button key='a'>打开</Button>, <Button key='b' >跳转</Button>]}
        />
      </>
    );
  }
}
```

## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| buttons | 按钮组 | ReactNode | 否 | - |
| customRenderLeft | 自定义渲染左侧内容，含 title 和 icon | (e?: JSX.Element) => ReactNode | 否 | - |
| customRenderRight | 自定义渲染右侧内容 | (e?: JSX.Element) => ReactNode | 否 | - |
| customStyleLeft | 自定义左侧行内样式 | CSSProperties | 否 | - |
| customStyleRight | 自定义左侧行内样式 | CSSProperties | 否 | - |
| enableAdaptiveLayout | 开启自适应布局 | boolean | 否 | - |
| getTitle | 自定义左侧区域,仅 title 部分 | () => ReactNode | 否 | - |
| getTitleLabel | 自定义标题 | () => ReactNode | 否 | - |
| hideUnderLine | 隐藏底部边线 | boolean | 否 | false |
| icon | 标题图标 | IconNames | 否 | - |
| iconBgcolor | 图标颜色 | string | 否 | - |
| iconBorderColor | 图标边框颜色 | string | 否 | - |
| iconStyle | 图标样式 | CSSProperties | 否 | - |
| inDialog | 兼容对话框中使用时的样式,且对话框默认开启 | boolean | 否 | - |
| leftCol | 左侧布局比例 | number | 否 | - |
| menuProps | 页签自定义参数配置，兼容 Menu 组件配置 | MenuBaseProps | 否 | - |
| menuValue | 页签选中值配置 | string | 否 | - |
| menus | 页签配置 | MenuItemData[] | 否 | - |
| needProgress | 需要进度条 | boolean | 否 | false |
| noIcon | 隐藏图标 | boolean | 否 | false |
| onMenuChange | 切换选中页签的事件 | (value: string) => void | 否 | - |
| progressProps | 进度条属性 | any | 否 | - |
| rightCol | 右侧布局比例 | number | 否 | - |
| title | 标题 | string | 否 | - |
| titleTipType | 标题提示效果 | 'title' \| 'popover' \| 'scroll' | 否 | - |
### MenuItemData 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| activeIcon | 菜单激活的时候左侧显示的激活图标 | string \| React.ReactNode | 否 | - |
| canBeSelected | 用于控制父级菜单是否可选, 默认为 false | boolean | 否 | - |
| children | 子数据 | MenuItemData[] | 否 | - |
| closeIcon | 自定义删除图标 | string \| React.ReactNode | 否 | - |
| closeTitle | 删除按钮鼠标浮动的的title | string | 否 | '删除' |
| closeable | 是否可删除 | boolean | 否 | - |
| content | 显示内容 | string \| React.ReactNode | 否 | - |
| customRenderItem | 自定义每一项的内容 | (this: any, itemNode: React.ReactNode, itemData: MenuItemData) => ReactElement | 否 | - |
| disabled | 是否是禁用项 | boolean | 否 | - |
| editIcon | 自定义编辑图标 | string \| React.ReactNode | 否 | |
| editTitle | 编辑按钮鼠标浮动的的title | string | 否 | '编辑' |
| editable | 是否可编辑 | boolean | 否 | |
| groupId | 分组的 id（分组带分割线） | string | 数据需要分组的情况下需要 | - |
| hide | 能否展示, 仅在type 为'tab'类型生效 (hide=true, 表示存在数据的情况,页签仍需隐藏) | boolean | 否 | - |
| icon | 左侧图标 | string \| React.ReactNode | 否 | - |
| id | 唯一标识 | string | 是 | - |
| parentId | 对应父级的 id | string | 如果是子菜单则需要,父级菜单不用 | - |
| rightIcon | 右侧图标 | string \| React.ReactNode | 否 | - |
| title | 浮动上去的提示文字 | stirng | 是 | - |
