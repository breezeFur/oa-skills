## 表格组件的使用案例
```js
import React from 'react';
import { Table, Avatar, Dialog, ITableColumn, Switch } from '@weapp/ui';
import imgSrc from "../../../../assets/images/ODTLcjxAfvqbxHnVXCYX.png"
const { message } = Dialog;

const columns: ITableColumn[] = [
  {
    title: '姓名',
    dataIndex: 'name',
    isPrimaryKey: true,
    bodyRender: getName,
  }, {
    title: '联系方式',
    dataIndex: 'tel'
  }, {
    title: '部门',
    dataIndex: 'depart',
  },{
    title: '多行文本',
    dataIndex: 'textarea',
  },{
    title: '上级',
    dataIndex: 'leader',
    bodyRender: getLeader
  },{
    title: '入职时间',
    dataIndex: 'join_time',
  }
];

function getName(data: any, pos: any, name: any) {
  const url = imgSrc;
  return (
    <span className={'ui-table-demo-name'}>
      <Avatar size='small' url={url} ></Avatar>
      <a style={{ marginLeft: '10px', color: '#5D9CEC' }}>{data[name]}</a>
    </span>
  )
}

function getLeader(data: any, pos: any, name: any) {
  return <a>{data[name]}</a>
}

const data = [{
  name: '张天逸',
  tel: '15199398787',
  depart: '泛微-北方大区',
  textarea: '设计师',
  leader: '王紫博',
  join_time: '2021-06-23'
}];

export default class BasicDemo extends React.Component<{}, any> {
  state = {
    current: 1,
    pageSize: 5,
    data: data,
    isShowHead: true,
    loading: false,
    isShowIndex: true,
    bordered: false
  };

  onRowClick = (data: any, index: any, event: any) => {
    console.log('onRowClick', data, index, event.target)
  }

  onRowMouseEnter = (a: number, b: object) => {
    console.log('onRowMouseEnter', a, b)
  }

  handleChange = (v: boolean) => {
    this.setState({
      isShowHead: v
    })
  }

  handleLoadingChange = (v: boolean) => {
    this.setState({
      loading: v
    })
  }

  handleIndexChange = (v: boolean) => {
    this.setState({
      isShowIndex: v
    })
  }

  onChange = (value: number, pageSize: number) => {
    this.setState({ current: value, pageSize });
    message({
      type: 'success', // type: 'info', 'error', 'success'
      content: `value: ${value}, pageSize: ${pageSize}`,
    });
  }

  onSizeChange = (value: number, pageSize: number) => {
    this.setState({ current: value, pageSize })
    message({
      type: 'success', // type: 'info', 'error', 'success'
      content: `value: ${value}, pageSize: ${pageSize}`,
    });
  }

  getPageInfo = () => {
    const { current, pageSize, data } = this.state

    return {
      value: current,
      pageSize: pageSize,
      total: data.length,
      showSizeChanger: true,
      showTotal: false,
      showJumper: false,
      pageSizeOptions: [5, 10],
      onChange: this.onChange,
      onSizeChange: this.onSizeChange
    }
  }

  handleBorderedChange = (v: boolean) => {
    this.setState({ bordered: v })
  }

  render() {
    const { data, isShowHead, loading, isShowIndex, bordered } = this.state
    return (
      <div>
        <span style={{ margin: '15px 10px', display: 'inline-block', alignItems: 'center' }}>
          <Switch value={isShowHead} onChange={this.handleChange} />是否显示表头
        </span>
        <span>
          <Switch value={loading} onChange={this.handleLoadingChange} />是否loading
        </span>
        <span style={{ margin: '15px 10px', display: 'inline-block', alignItems: 'center' }}>
          <Switch value={isShowIndex} onChange={this.handleIndexChange} />是否显示序号
        </span>
        <span style={{ margin: '15px 10px', display: 'inline-block', alignItems: 'center' }}>
          <Switch value={bordered} onChange={this.handleBorderedChange} />是否显示边框
        </span>
        <Table
         
          columns={columns}
          data={data}
          pageInfo={this.getPageInfo()}
          onRowClick={this.onRowClick}
          isShowHead={isShowHead}
          loading={loading}
          isShowIndex={isShowIndex}
          bordered={bordered}
        />
      </div>
    )
  }
}
```