## 基础用法
```js
import React, { ReactNode } from 'react';
import { Pagination, AnyObj } from '@weapp/ui';
import './index.less';

export default class CustomStyleDemo extends React.PureComponent<{}> {

  onChange = (value: number, pageSize: number) => {
    console.log('onChange', value, pageSize);
  }
  
  customRenderContent = (_: any, ele: ReactNode, customRenderMap: AnyObj) => {
    const { totalContent, pagerContent, sizeChangeContent, jumpContent } = customRenderMap
    return [
      totalContent,
      sizeChangeContent,
      pagerContent,
      jumpContent
    ].filter(i => !!i)
  }

  render() {
    return (
      <Pagination
        defaultValue={1}
        total={500} // 总数 会显示 `共500条`
        simple={false}
        showTotal={true}
        showJumper={true}
        showSizeChanger={true}
        onChange={this.onChange}
        onSizeChange={this.onChange}
        showFirstLastBtnInForce={true}
        customRenderContent={this.customRenderContent}
        className={'ui-demo-pagination-new'}
      />
    );
  }
}
```