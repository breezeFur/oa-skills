## 代码演示
### 基础用法
```tsx
import React from "react";
import { Collapse, Switch, Icon } from "@weapp/ui";

export default class BasicDemo extends React.Component<{}> {
  state = {
    activeKey: "1",
    bg: true,
    accordion: false,
    iconPosition: "right",
  };

  handleChange = (activeKey: any) => {
    this.setState({
      activeKey,
    });
  };

  handleBgChange = (bg: boolean) => {
    this.setState({ bg });
  };

  handleAccordionChange = (accordion: boolean) => {
    this.setState({ accordion, activeKey: "1" });
  };

  handlePositionChange = (v: boolean) => {
    this.setState({ iconPosition: v ? "right" : "left" });
  };

  customIconRender = (props: ICollapsePanelProps) => {
    return (
      <Icon
        name={props.active ? "Icon-reduce03" : "Icon-add-to03"}
        style={{ marginRight: "15px" }}
      />
    );
  };

  render() {
    const { activeKey, bg, accordion } = this.state;
    const titleBg = bg ? "default" : "none";

    return (
      <div>
        <div style={{ margin: "20px 0" }}>
          <span>
            <Switch value={this.state.bg} onChange={this.handleBgChange} />
            <span>&nbsp;&nbsp;底色</span>
          </span>
          <span style={{ marginLeft: 20 }}>
            <Switch
              value={this.state.accordion}
              onChange={this.handleAccordionChange}
            />
            <span>&nbsp;&nbsp;手风琴</span>
          </span>
          <span style={{ marginLeft: 20 }}>
            <Switch
              value={this.state.iconPosition === "right"}
              onChange={this.handlePositionChange}
            />
            <span>&nbsp;&nbsp;图标位置</span>
          </span>
        </div>
        <Collapse
          accordion={accordion}
          panelTitleBackground={titleBg}
          activeKey={activeKey}
          onChange={this.handleChange}
          bordered={false}
          customIconRender={this.customIconRender}
        >
          <Collapse.Panel
            title="标题一"
            key="1"
            iconPosition={this.state.iconPosition as "left" | "right"}
          >
            标题一内容标题一内容标题一内容标题一内容标题一内容
          </Collapse.Panel>
          <Collapse.Panel
            title="标题二"
            key="2"
            iconPosition={this.state.iconPosition as "left" | "right"}
          >
            标题二内容标题二内容标题二内容标题二内容标题二内容标题二内容
          </Collapse.Panel>
          <Collapse.Panel
            title="标题三"
            key="3"
            disabled
            iconPosition={this.state.iconPosition as "left" | "right"}
          >
            标题三内容标题三内容标题三内容标题三内容标题三内容标题三内容
          </Collapse.Panel>
        </Collapse>
      </div>
    );
  }
}
```
### 编辑分组
```tsx
import React, { MouseEventHandler, ReactNode, ReactText } from 'react';
import { Collapse, Icon, utils, ICollapsePanelProps } from '@weapp/ui';

const { moveItem } = utils;

interface CustomIconProps {
  id?: string;
  onClick?: (id?: string) => void;
}

class CustomIcon extends React.Component<CustomIconProps> {
  onClick: MouseEventHandler = (e) => {
    const { id, onClick } = this.props;
    onClick?.(id);
    e && e.stopPropagation();
  }
  render() {
    return (<div>
      <Icon name="Icon-N-Deleted" onClick={this.onClick} />
    </div>)
  }
}

export default class BasicDemo extends React.Component<{}> {
  state = {
    activeKey: '1',
    bg: true,
    accordion: false,
    iconPosition: 'right',
    groups: [
      { id: '1', name: '标题1', defaultEditable: false },
      { id: '2', name: '标题2', defaultEditable: false },
      { id: '3', name: '标题3', defaultEditable: false },
    ]
  };

  handleChange = (activeKey: any) => {
    this.setState({
      activeKey,
    });
  };

  handleBgChange = (bg: boolean) => {
    this.setState({ bg });
  };

  handleAccordionChange = (accordion: boolean) => {
    this.setState({ accordion, activeKey: '1' });
  };

  handlePositionChange = (v: boolean) => {
    this.setState({ iconPosition: v ? 'right' : 'left' });
  };

  onSortEnd = (evt: any) => {
    const { oldIndex, newIndex, from, to } = evt;
    if (from.dataset.index === to.dataset.index) {
      // 分组内拖拽
      const result = [...this.state.groups];
      // 执行排序操作，更新result数据
      moveItem(result, oldIndex, newIndex)
      this.setState({ groups: result });
    }
  }

  onEdit = (key?: string, value?: ReactText) => {
    const result = [...this.state.groups]?.map((g) => {
      if (g.id === key) {
        return { ...g,name: value }
      }
      return g;
    });
    this.setState({ groups: result });
  }

  onAdd = () => {
    const maxIds = this.state.groups.map((g) => Number(g.id));
    const length = maxIds?.length > 0 ? Math.max(...maxIds) + 1 : 1;
    const groups = [
      ...this.state.groups,
      { id: `${length}`, name: `标题${length}`, defaultEditable: true },
    ]
    this.setState({ groups });
  }
  
  onDelete = (id?: string) => {
    const groups = this.state.groups?.filter((g) => g.id !== id);
    this.setState({ groups });
  }

  renderCustomIcon = (props: ICollapsePanelProps) => {
    return (<CustomIcon id={props?.panelKey} onClick={this.onDelete}/>)
  }
  
  customRenderTitle = (props: ICollapsePanelProps, com: ReactNode) => {
    return (<div>{com}{this.renderCustomIcon(props)}</div>)
  }

  render() {
    const { activeKey, bg, accordion } = this.state;
    const titleBg = bg ? 'default' : 'none';
    return (
      <div>
        <Collapse
          accordion={accordion}
          panelTitleBackground={titleBg}
          activeKey={activeKey}
          onChange={this.handleChange}
          bordered={false}
          editable
          sortable
          onSortEnd={this.onSortEnd}
          onEdit={this.onEdit}
          type="group"
        >
          {
            this.state.groups?.map((group) => (
              <Collapse.Panel
                title={group?.name}
                key={group.id}
                iconPosition={this.state.iconPosition as 'left' | 'right'}
                defaultEditable={group.defaultEditable}
                customRenderTitle={this.customRenderTitle}
              >
                {group?.name}内容
              </Collapse.Panel>
            ))
          }
        </Collapse>
        <div onClick={this.onAdd} >
          <Icon name="Icon-add-to02" />
          <span>添加数据</span>
        </div>
      </div>
    );
  }
}
```
## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| accordion | 手风琴模式，一次只能有一个 active 的面板 | boolean | 否 | - |
| activeKey | 当前打开的面板 id | string \| string[] | 否 | - |
| bordered | 是否有外边框 | boolean | 否 | - |
| className | 复写类名 | string | 否 | - |
| customIconRender | 自定义渲染箭头图标 | props: ICollapsePanelProps => React.ReactNode | 否 | - |
| direction | 折叠方向 | 'up'\|'down' | 否 | 'up' |
| editable | 启用可编辑状态(仅分组标题为string类型支持) | boolean | 否 | - |
| editableIcon | 自定义可编辑图标 | IconNames | 否 | - |
| isClickOnRow | 是否点击整行折叠收缩 | boolean | 否 | true |
| onChange | 切换面板的回调函数 | (value: string \| string[]) => any; | 否 | - |
| onEdit | 编辑分组名称回调事件 | (key?: string, title?: ReactText) => void | 否 | - |
| onSortEnd | 排序回调事件 | (evt: any) => void | 否 | - |
| panelTitleBackground | Panel 标题底色 | string | 否 | - |
| sortable | 启用排序 | boolean | 否 | - |
| sortableIcon | 自定义排序图标 | IconNames | 否 | - |
| sortableOptions | 自定义排序配置 | AnyObj | 否 | - |
| type | 展示模式 | 'normal' \| 'group' | 否 | 'normal' |
### 子组件 Collapse.Panel 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| bordered | 是否有边框 | boolean | 否 | - |
| className | 复写类名 | string | 否 | - |
| customIconRender | 自定义渲染箭头图标 | props: ICollapsePanelProps => React.ReactNode | 否 | - |
| customRenderTitle | 渲染自定义标题区域 | (props: ICollapsePanelProps, com: React.ReactNode) => React.ReactNode | 否 | - |
| defaultEditable | 默认可编辑 | boolean | 否 | - |
| direction | 折叠方向 | 'up'\|'down' | 否 | 'up' |
| disabled | 禁用 | boolean | 否 | - |
| editable | 启用可编辑状态(仅分组标题为string类型支持) | boolean | 否 | - |
| editableIcon | 自定义可编辑图标 | IconNames | 否 | - |
| iconPosition | 图标位置 | 'right' \| 'left' | 否 | 'right' |
| id | 面板 id | string | 否 | - |
| isMobile | 是否移动端 | boolean | 否 | - |
| onEdit | 编辑分组名称回调事件 | (key?: string, title?: ReactText) => void | 否 | - |
| onSortEnd | 排序回调事件 | (evt: any) => void | 否 | - |
| renderCustomIcon | 渲染自定义图标 | (props: ICollapsePanelProps) => React.ReactNode | 否 | - |
| showArrow | 是否显示箭头图标 | boolean | 否 | true |
| sortable | 启用排序 | boolean | 否 | - |
| sortableIcon | 自定义排序图标 | IconNames | 否 | - |
| style | 复写样式 | React.CSSProperties | 否 | - |
| title | 面板标题 | React.ReactNode | 是 | - |
### IAnimateHeightBaseProps类型如下
```tsx
export type IAnimateHeightOverflow = 'hidden' | 'scroll' | 'auto' | 'unset';
export interface IAnimateHeightBaseProps {
  appear?: boolean;
  duration?: number;
  easing?: string;
  className?: string;
  style?: CSSProperties;
  overflow?: IAnimateHeightOverflow;
}
```
