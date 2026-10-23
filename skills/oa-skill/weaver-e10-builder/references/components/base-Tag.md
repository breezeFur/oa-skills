## 基础用法

```js
import React, { Component } from "react";
import { constants, Tag, Icon } from "@weapp/ui";

const prefixCls = `${constants.uiPcClsPrefix}-demo-tag`;

export default class TagDemo extends Component {
  // 删除标签时的事件
  handleClose = () => {
    console.log("标签已关闭");
  };

  // 点击关闭按钮后延迟 2s 关闭
  handleBeforeClose = () => {
    return new Promise((resolve, reject) => {
      setTimeout(function () {
        try {
          resolve(null);
        } catch (err) {
          reject(null);
        }
      }, 2000);
    });
  };

  render() {
    return (
      <div className={prefixCls}>
        <div>
          <div className="tag-demo-label">
            <h6>方形</h6>
          </div>
          <div className="tag-demo">
            <Tag title="标签1">方形标签</Tag>
          </div>
        </div>

        <div>
          <div className="tag-demo-label">
            <h6>圆角标签</h6>
          </div>
          <div className="tag-demo">
            <Tag radius>圆角标签</Tag>
          </div>
        </div>

        <div>
          <div className="tag-demo-label">
            <h6>悬浮状态展现删除按钮</h6>
          </div>
          <div className="tag-demo">
            <Tag closable onClose={this.handleClose}>
              删除
            </Tag>
            <Tag
              radius
              closable
              beforeClose={this.handleBeforeClose}
              onClose={this.handleClose}
              style={{ maxWidth: "80px" }}
            >
              点击关闭图标，延迟 2s 关闭
            </Tag>
          </div>
        </div>

        <div>
          <div className="tag-demo-label">
            <h6>中等标签</h6>
          </div>
          <div className="tag-demo">
            <Tag size="medium">中等的标签</Tag>
            <Tag disabled size="medium">禁用状态</Tag>
          </div>
        </div>

        <div>
          <div className="tag-demo-label">
             <h6>方形标签</h6>
          </div>
          <div className="tag-demo">
              <Tag type="default">默认标签</Tag>
              <Tag type="primary">主要标签</Tag>
              <Tag type="success">成功标签</Tag>
              <Tag type="warning">警告标签</Tag>
              <Tag type="danger">危险标签</Tag>
          </div>
        </div>
      </div>
    );
  }
}
```

## 参数说明

| 参数 | 说明 | 类型 | 必填 | 默认值 |
| --- | --- | --- | --- | --- |
| beforeClose | 标签关闭前的回调 | `(e: React.MouseEvent) => Promise` | 否 | — |
| checked | 是否选中 | `boolean` | 否 | `false` |
| closable | 是否可删除 | `boolean` | 否 | `false` |
| closeIcon | 自定义关闭按钮 | `ReactNode` | 否 | `x` |
| disabled | 是否禁用 | `boolean` | 否 | `false` |
| onCheck | 选中状态切换触发的函数 | `(checked: boolean, e: React.MouseEvent) => void` | 否 | — |
| onClose | 关闭后回调 | `(e: React.MouseEvent) => void` | 否 | — |
| radius | 是否是圆角标签 | `boolean` | 否 | `false` |
| size | 标签尺寸 | `'small'` \| `'medium'` \| `'large'` | 否 | `'large'` |
| solid | 是否是实心 | `boolean` | 否 | `false` |
| title | 提示文字 | `string` | 否 | — |
| type | 标签分类 | `'default'` \| `'primary'` \| `'success'` \| `'warning'` \| `'danger'` | 否 | `'default'` |
