## 代码演示
### 基础用法
```tsx
import React from "react";
import { List, Icon, ListData } from "@weapp/ui";

const style = { height: "300px" };
const sortableOptions = { handle: ".my-handle" };

const datas: any[] = [];
for (let i = 0; i < 20; i++) {
  datas.push({
    id: i,
    title: `开发${i + 1}部`,
  });
}
const datas1: any[] = [];
for (let i = 0; i < 200000; i++) {
  datas1.push({
    id: i,
    title: `开发${i + 1}部`,
  });
}

export default class ListDemo extends React.Component {
  state = {
    activeRows: [],
  };

  customRenderItem = (item: ListData) => (
    <div style={{ height: "40px", lineHeight: "40px" }}>
      <span style={{ marginLeft: "10px" }}>{item.title}</span>
    </div>
  );

    customRenderItem1 = (item: ListData) => <div style={{ height: '40px', lineHeight: '40px' }}>
    <span style={{ marginLeft: '10px' }}>
      {item.title}
    </span>
  </div>

  customRenderItem3 = (item: ListData) => (
    <div style={{ height: "40px", lineHeight: "40px" }}>
      <Icon name="Icon-move" className="my-handle" />
      <span style={{ marginLeft: "10px" }}>{item.title}</span>
    </div>
  );

  onRowClick = (data?: ListData, index?: number) => {
    this.setState({ activeRows: [data] });
  };

  onSortEnd = (data: ListData[]) => {};

  render() {
    return (
      <div>
        <h4>基础用法</h4>
        <List
          style={style}
          direction="column"
          data={datas}
          customRenderContent={this.customRenderItem}
          bordered={true}
          isStopMouseDown={true}
        />
        <h4>长按左边图标进行拖拽</h4>
        <List
          sortable={true}
          style={style}
          direction="column"
          sortableOptions={sortableOptions}
          data={datas}
          customRenderContent={this.customRenderItem3}
          onSortEnd={this.onSortEnd}
          onRowClick={this.onRowClick}
          activeRows={this.state.activeRows}
        />
        <h4>虚拟列表</h4>
        <List
          direction="column"
          data={datas1}
          virtualMode={true}
          virtualModeProps={{
            defaultRowHeight: 40,
            minContainerHeight: 360,
          }}
          customRenderContent={this.customRenderItem1}
        />
      </div>
    );
  }
}
```
### 分页模式
```tsx
import React from 'react';
import { List, ListData, ListGroupData, Radio, ListPaginationType, RadioDataType, RadioValueType } from '@weapp/ui';
const style2 = { height: '300px' }
const dataGroupTitle1 = [
  { id: 'A', content: 'A', draggable: false },
  { id: 'B', content: 'B', expandable: true },
  { id: 'C', content: 'C', expandable: true },
  { id: 'D', content: 'D' }
];
const dataGroupTitle = [
  { id: 'A', content: 'A', checkable: true, draggable: false },
  { id: 'B', content: 'B', checkable: true, icon: "Icon-integrate-o" },
  { id: 'C', content: 'C', checkable: true },
  { id: 'D', content: 'D', checkable: true }
];
const datas: any[] = [];
for (let i = 0; i < 20; i++) {
  datas.push({
    id: i,
    title: `开发${i + 1}部`,
  });
}
const datas2: any[] = [];
for (let i = 0; i < 20; i++) {
  datas2.push({
    id: i + 21,
    title: `开发${i + 21}部`,
  });
}
const data = datas;
const options: RadioDataType = [
  {
    id: 'scroll',
    title: '滚动分页',
    content: '滚动分页',
  },
  {
    id: 'more',
    title: '点击加载更多',
    content: '点击加载更多',
  },
  {
    id: 'part',
    title: 'Pagination分页',
    content: 'Pagination分页',
  },
];
export default class ListDemo extends React.Component {
  state = {
    selected1: [],
    data: datas,
    data1: datas,
    dataGroupTitle: dataGroupTitle,
    dataGroupTitle1: dataGroupTitle1,
    loading: false,
    hasMore: true,
    currentPage: 1,
    pageSize: 10,
    pageValue: 'scroll',
  }
  onRowSelect = (arr: Array<ListData> | Array<string>, data?: ListData[]) => {
    console.log(arr, data)
    this.setState({ selected1: arr })
  }
  customRenderItem5 = (rowData: ListData, rowID: number) => {
    const obj = rowData;
    return (
      <span key={rowID} style={{ marginLeft: '15px' }}>
        {obj.title}
      </span>
    );
  }
  onEndReached = () => {
    if (this.state.data.length > 60) {
      this.setState({ hasMore: false })
    } else {
      this.setState({ loading: true })
      setTimeout(() => {
        this.setState({ data: [...this.state.data, ...data], loading: false })
      }, 200)
    }
  }
  onPageChange = (value: number) => {
    const { data } = this.state;
    if (value * 10 > data.length) {
      this.setState({ loading: true })
      setTimeout(() => {
        const newData = data.concat(datas2)
        this.setState({ data: newData, loading: false })
        if (newData.length >= 40) {
          this.setState({ hasMore: false })
        }
      }, 20)
    }
    this.setState({ currentPage: value });
  }
  onScroll = (e: Event) => {
    console.log(e)
  }
  onQuickSearch = (obj: ListGroupData, i: number) => {
    this.setState({
      data1: datas,
      dataGroupTitle: [dataGroupTitle[i]],
    })
  }
  onSortEnd = (data: ListData[], dataGroupTitle?: ListGroupData[]) => {
    console.log(data);
  }
  onPageTypeChange = (value: RadioValueType) => {
    this.setState({ pageValue: value, data: datas, data1: datas, loading: false, hasMore: true, currentPage: 1 })
  }
  render() {
    const { hasMore, loading } = this.state;
    return (
      <div>
        <h4>分页模式</h4>
        <Radio data={options} value={this.state.pageValue} onChange={this.onPageTypeChange} />
        <br />
        <List
          data={this.state.data}
          customRenderContent={this.customRenderItem5}
          // onEndReached={this.onEndReached}
          onScroll={this.onScroll}
          paginationProps={{
            value: this.state.currentPage,
            pageSize: 10,
            paginationType: this.state.pageValue as ListPaginationType,
            onChange: (value, pageSize) => {
              this.onPageChange(value)
            },
            total: this?.state?.data?.length || 0
          }}
          style={["scroll", "more"]?.includes(this.state.pageValue) ? style2 : {}}
          loading={loading}
          hasMore={hasMore}
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
| activeRows | 点击选中的行 | Array | 否 | |
| boxSelection | 是否支持框选 | boolean | 否 | false |
| checkStyle | check 框样式 | CSSProperties | 否 | |
| checkTitle | check框鼠标浮动上去的提示文本 | string | 否 | |
| checkboxPosition | check 框位置 | 'left' \| 'right' | 否 | false |
| customRender | 自定义渲染 | (_: any, ele: ReactNode) => ReactNode | 否 | |
| customRenderContent | 自定义 html 模板渲染 Item 的内容布局,用组件内部的 Item 包裹,具有统一的默认样式和属性 | (rowData: ListData\|ListData[], rowIndex: number) => ReactNode | 否 | |
| customRenderItem | 自定义渲染 Item,不用组件内部的 Item 包裹,不具有统一的默认样式和属性 | (rowData: ListData, rowIndex: number) => ReactNode | 否 | |
| customRenderOrder | 自定义渲染序号 | (rowIndex: number \| string) => ReactNode | 否 | |
| customerSortableGroupOptions | 自定义分组的group配置项 | (groupData: object) => string \| object | 否 | false |
| data | 列表数据 | Array | 是 | |
| direction | 横向或纵向显示 | 'column' \| 'row' | 否 | 'row' |
| disabledHTMLDisplay | 是否禁用模板html渲染 | boolean | 否 | false |
| expandTemplate | 模板扩展,在模板渲染的基础上进行扩展 | (templateCom: ReactNode, data: ListData[]) => ReactNode | 否 | |
| getCheckedDisabledProps | 是否选择框禁止选中 | (rowData: ListData, rowIndex: number) => boolean | 否 | |
| getSortableInstance | 获取sortable实例 | (instance: object \| object[]) => void | 否 | |
| getTemplate | 重写模板的钩子函数 | (template: any) => void | 否 | |
| hasMore | 是否还有更多数据(为 false 时 onEndReached 不会触发) | boolean | 否 | true |
| hideEmptyGroup | 是否隐藏空分组 | boolean | 否 | false |
| horizontalScroll | 横向显示时,超出区域是滚动还是换行,默认换行 | boolean | 否 | true |
| indexedIdentities | 索引信息 | GroupData[] | 否 | |
| initialOrder | 初始序号 | number | 否 | |
| isClickable | 根据每行数据决定是否绑定点击事件 | (data: ListData, index: number, childData?: AnyObj[]) => boolean | 否 | |
| isStopMouseDown | 是否阻止 mousedown 事件冒泡（常用于搭配 Trigger 组件使用） | boolean | 否 | false |
| loading | 是否正在加载数据(为 true 时 onEndReached 不会触发) | boolean | 否 | false |
| multipleCheck | 多选或单选 | boolean | 否 | |
| noBorder | 是否显示边框 | boolean | 否 | false |
| onEndReached | 当所有的数据都已经渲染过，并且列表被滚动到距离最底部不足 onEndReachedThreshold 个像素的距离时调用 | () => void | 否 | |
| onEndReachedThreshold | 调用 onEndReached 之前的临界值，单位是像素 | number | 否 | 10 |
| onQuickSearch | 快捷导航切换时调用 | (sectionData: GroupData, sectionIndex: number) => void | 否 | |
| onQuickSearchTop | 快捷导航栏最顶部按钮点击调用 | (quickSearchBarTop?: GroupData) => void | 否 | |
| onRowClick | 行点击事件 | (data?: ListData, index?: number) => void | 否 | |
| onRowSelect | 行选中事件 | (selectedRowKeys: Array \| Array, selectedData?: ListData[]) => void | 否 | |
| onScroll | 滚动事件 | (e: Event) => void | 否 | |
| onSortEnd | 拖拽结束回调 | (data: ListData[]) => void | 否 | |
| paginationProps | 分页属性 | PaginationProps | 否 | |
| popoverProps | 气泡框属性 | PopoverProps | 否 | |
| pullToRefresh | 拉动刷新 | ReactNode | 否 | |
| quickSearchBarStyle | quickSearchBar 的 style | CSSProperties | 否 | |
| quickSearchBarTop | 快捷导航栏最顶部按钮、常用于回到顶部 | GroupData | 否 | |
| renderFooter | 列表尾部 | (() => ReactNode) \| string \| JSX.Element | 否 | |
| renderHeader | 列表头部 | (() => ReactNode) \| string \| JSX.Element | 否 | |
| renderPopup | 渲染气泡框内容 | (data?: ListData, index?: number) => void | 否 | |
| renderSectionHeader | 如果提供了此函数，会为每个小节(section)渲染一个标题 | (sectionData?: GroupData) => ReactNode | 否 | |
| rowSelect | 支持配置点击整行选中或是只点击 check 框选中 | boolean | 否 | false |
| scrollEventThrottle | 控制在滚动过程中，scroll 事件被调用的频率 | number | 否 | |
| selectedRowKeys | 选中行主键的集合 | Array \| Array | 否 | |
| showCheck | 显示可选 | boolean | 否 | false |
| showDataGroupByType | 跨分组拖拽 | boolean | 否 | false |
| showImg | 是否显示图标 | boolean | 否 | false |
| showOrder | 是否显示序号 | boolean | 否 | false |
| showPopover | 显示气泡框 | boolean | 否 | false |
| sortable | 是否可拖拽排序 | boolean | 否 | false |
| sortableOptions | 拖拽相关的方法,参考sortablejs 文档 | object | 否 | |
| stopCheckboxPropagation | 是否阻止check框点击事件的冒泡 | boolean | 否 | false |
| template | 模板 | any | 否 | |
| templateType | 模板类型 | string | 否 | |
| virtualMode | 是否开启虚拟列表模式 | boolean | 否 | false |
| virtualModeProps | 虚拟列表配置参数 | IVirtualModeProps | 否 | - |
### paginationProps分页配置 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| PaginationProps | 分页器配置，详情见 组件 Pagination API 说明 | boolean | | |
| paginationType | 分页模式 | 'scroll' \| 'part' | | 'scroll' |
### IndexedList索引列表配置 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| indexedIdentities | 索引信息 | GroupData[] | 是 | |
| initialOrder | 初始序号 | number | 否 | |
### IVirtualModeProps虚拟列表配置 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| defaultRowHeight | 默认行高 | number | | 40 |
| getItemSize | 动态计算列表每行高度 | (index?: number) => number | | |
| measuredRowHeight | 是否开启动态行高 | boolean | | false |
| minContainerHeight | 列表容器初始化默认最小高度 | number | | 300 |
## 注意事项
1、sortableOptions配置，可参考sortablejs文档(https://sortablejs.com/options.html)