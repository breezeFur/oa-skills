## 基础用法

```tsx
import React, { Component } from "react";
import {
  constants,
  Select,
  SelectOptionData,
  SelectValueType,
  SingleType,
} from "@weapp/ui";

const prefixCls = `${constants.uiPcClsPrefix}-demo-input`;

type SelectDemoState = {
  value: string;
};

const options = [
  { id: "", content: "选项一", other: true, color: "#5D9CEC" },
  { id: "2", content: "选项二", custom: 3, color: "#FF4D4F" },
  {
    id: "3",
    content:
      "超长文本超长文本超长文本超长文本超长文本超长文本超长文本超长文本超长文本超长文本超长文本",
    color: "#52C41A",
  },
  { id: "4", content: "禁用项", disabled: true },
];

const groupOptions = [
  { id: "11", content: "选项一", type: "1" },
  { id: "12", content: "禁用项", type: "1", disabled: true },
  { id: "13", content: "选项三", type: "1" },
  { id: "21", content: "选项四", type: "2" },
  { id: "31", content: "选项五", type: "3" },
];

const groupTitle = [
  { id: "1", content: "分组1" },
  { id: "2", content: "分组2" },
  { id: "3", content: "分组3" },
];

class SelectDemo extends Component<any, SelectDemoState> {
  constructor(props: any) {
    super(props);
    this.state = {
      value: "",
      valueArr: ["1"],
      valueObj: groupOptions[0],
    };
  }

  handleChange = (v: SelectValueType, option: any, event: any) => {
    console.log("handleChange");
    console.log("v", v);
    console.log("option", option);
    console.log("event", event);
    this.setState({ value: v as string });
  };

  handleSelect = (
    value: SingleType<SelectValueType>,
    option: SelectOptionData,
  ) => {
    console.log("selected:", value, option);
  };

  handleArrChange = (v: SelectValueType) => this.setState({ valueArr: v as string[] });

  handleObjChange = (v: SelectValueType) => this.setState({ valueObj: v as SelectOptionData });

  handleDeselect = (
    value: SingleType<SelectValueType>,
    option: SelectOptionData,
  ) => {
    console.log("deselected:", value, option);
  };

  onSelectClick = () => console.info("onSelectClick");

  render() {
    const { value, valueArr, valueObj } = this.state;
    return (
      <div className={prefixCls}>
        <h4>单选</h4>
        <Select
          data={options}
          value={value}
          showSearch
          allowClear
          onSelect={this.handleSelect}
          onDeselect={this.handleDeselect}
          onChange={this.handleChange}
          onSelectClick={this.onSelectClick}
        />
        <h4>多选</h4>
        <Select
          style={{ width: 250 }}
          data={options}
          multiple
          showSearch
          allowClear
          allowSelectAll
          value={valueArr}
          onSelect={this.handleSelect}
          onChange={this.handleArrChange}
        />
        <h4>只读</h4>
        <Select data={options} value={"2"} readOnly />
        <h4>禁用</h4>
        <Select style={{ width: 200 }} data={options} value={"3"} disabled />
        <h4>分组</h4>
        <Select
          style={{ width: 200 }}
          data={groupOptions}
          showDataGroupByType
          dataGroupTitle={groupTitle}
          value={valueObj}
          onSelect={this.handleSelect}
          onChange={this.handleObjChange}
        />
      </div>
    );
  }
}
```

## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| allowCancel | 单选时是否允许取消选中项 | boolean | F | false |
| allowClear | 是否可以清除输入框 | boolean | F | false |
| allowSelectAll | 多选时是否允许全选 | boolean | F | false |
| alwaysTriggerSelect | 单选时允许选中已选数据并触发 onSelect 回调 | F | boolean | false |
| bindTriggerContainer | 是否绑定弹层容器，若为 true，则调用 getPopupContainer 函数；若为 false，使用 getPopupContainer 这个 props | boolean | F | - |
| customInputRender | 自定义输入框的渲染 | (selectComponent:any, selectedData: OptionsType) => ReactNode | F | - |
| customOptionRender | 自定义每一选项的渲染 | (option: OptionData) => ReactNode | F | - |
| customRenderEmpty | 自定义渲染无数据时暂时的空状态 | customRenderEmpty: () => ReactNode | F | - |
| data | 下拉选项数据 | SelectOptionsType | F | - |
| dataGroupTitle | 分组数据 | DataGroupType | F | false |
| defaultOpen | 是否默认打开下拉框 | boolean | F | false |
| defaultValue | 当前数(默认值) | string[],SelectOptionsType | F | - |
| disabled | 是否禁用 | boolean boolean | F | |
| dropdownClassName | 自定义下拉框的 class | string | F | - |
| dropdownMatchSelectWidth | 自定义下拉框宽度，若是 boolean 类型，则与 container 同宽；若是 number，则是自定义宽度 | boolean ｜ number | F | - |
| dropdownPlacement | 自定义下拉框的显示位置 | PopupPlacement | F | - |
| dropdownRender | 自定义下拉框 | (menu: React.ReactElement) => React.ReactElement | F | - |
| dropdownStyle | 自定义下拉框的样式 | CSSProperties | F | false |
| filterOption | 自定义筛选，会接收 inputValue option 两个参数，当 option 符合筛选条件时，应返回 true，反之则返回 false | (inputValue: string, option: SelectOptionData) => boolean | F | - |
| focusAutoExpand | select 内容区域溢出隐藏情况下,聚焦后自动放大效果功能开关 | boolean | F | - |
| focusAutoExpandProps | select 内容区域隐藏情况下,聚焦后自动放大效果其它参数 | focusAutoExpandProps | F | - |
| getPopupContainer | 弹层容器定位 | () => HTMLElement ｜ undefined | F | - |
| inputIcon | 自定义输入框右侧的图标 | RenderNode | F | - |
| multiple | 是否多选 | boolean | F | false |
| onBlur | 失去焦点时触发回调 | () => void | F | - |
| onChange | 数据修改时触发回调 | (value: string[],SelectOptionsType, option: SelectOptionData SelectOptionsType, event: SelectEvent) => void | F | |
| onClick | 鼠标点击时触发回调 | React.MouseEventHandler | F | - |
| onDeselect | 取消选择数据时触发回调 | SelectOptionData, option: SelectOptionData) => void | F | - |
| onFocus | 聚焦输入框时触发回调 | () => void | F | - |
| onKeyDown | 按下按键时触发回调 | React.KeyboardEventHandler | F | - |
| onSearch | 搜索数据时触发回调 | (value: string) => void | F | - |
| onSelect | 选择数据时触发回调 | (value: string) => void SelectOptionData, option: SelectOptionData) => void | F | |
| onSelectClick | 点击 select 框的回调 | () => void | F | - |
| onVisibleChange | 下拉框显示隐藏时触发回调 | (visible: boolean) => void | F | - |
| open | 是否打开下拉框 | boolean | F | false |
| optionType | 选项的类型，可以设置为'tag' | string | F | - |
| optionType | 是否显示为标签样式 | boolean | F | false |
| readOnly | 是否只读 | boolean | F | false |
| readOnlyShowPlaceholder | 只读情况下无数据，展示 placeholder | boolean | F | false |
| showArrow | 是否显示右侧箭头图标 | boolean | F | false |
| showDataGroupByType | 开启分组功能 | boolean | F | false |
| showSearch | 是否可以搜索 | boolean | F | false |
| tagRender | 自定义标签的渲染 | (props: CustomTagProps) => React.ReactNode | F | - |
| triggerProps | trigger 组件的 props | TriggerConfig | F | - |
| value | 当前数(受控值) | string[],SelectOptionsType | F | - |
| vertical | 是否竖向排列 | boolean | F | - |

### focusAutoExpandProps参数说明如下
autoExpandUseAbsolute 是否开启对应 select 组件展开后使用绝对定位，避免撑开布局。默认情况下不设置此属性时候会撑开布局。
autoExpandParentCls 对应 select 最大撑开的宽度大小参考系,参考父级 容器 class 类名， 无法直接设置参考容器 可以提供参考容器对应的 class 类名。
autoExpandContainer 对应 select 最大撑开的宽度大小参考系,参考父级注 如果不设置对应 select 撑开内容区的宽度参考下 默认效果为视口大小。
```tsx
export type focusAutoExpandProps = {
  autoExpandUseAbsolute?: boolean;
  autoExpandParentCls?: string;
  autoExpandContainer?: () => HTMLElement | undefined;
};
```