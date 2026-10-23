## 代码演示
### 基础用法
```tsx
import { Component } from 'react';
import { Dialog, Button, constants } from '@weapp/ui';

const { uiPcClsPrefix } = constants;

interface DialogDemoProps {
  history?: any;
}
interface DialogDemoState {
  visible?: boolean;
}

const prefixCls = `${uiPcClsPrefix}-demo-btn`;

class DialogBody extends Component<{}> {
  render() {
    return <div className={`${uiPcClsPrefix}-demo-dialog-dialogBody`}>
      <p>DialogBody</p>
      <p>show everything...</p>
      <p>show everything...</p>
    </div>
  }
}

class DialogDemo extends Component<DialogDemoProps, DialogDemoState> {
  constructor(props: DialogDemoProps) {
    super(props);
    this.state = {
      visible: false
    }
  }

  onClose = () => {
    this.setState({ visible: false });
  }

  showDialog = () => {
    this.setState({ visible: true });
  }

  handleOk = () => {
    this.setState({ visible: false });
  };

  handleCancel = () => {
    this.setState({ visible: false });
  };

  render() {
    const { visible } = this.state;
    return (
      <div className={prefixCls}>
        <Button type={'primary'} onClick={this.showDialog}>打开弹框</Button>
        <Dialog
          visible={visible}
          onClose={this.onClose}
          title="基础用法，支持自定义页头页脚"
          width={770}
          icon="Icon--Import-and-export"
          scale
          closable
          destroyOnClose
          buttons={[<Button key='a'>页头1</Button>, <Button key='b'>页头2</Button>]}
          footer={[<Button onClick={this.handleCancel} key='cancle'>自定义</Button>,<Button onClick={this.handleCancel} key='cancle'>取消</Button>, <Button onClick={this.handleOk} type={'primary'} key='ok'>确定</Button>]}
          maskClosable
        >
          <DialogBody />
        </Dialog>
      </div>
    );
  }
}
```
### 对话框和提示消息
```tsx
import { Component, ReactText } from 'react';
import { Dialog, Button, constants, Input, utils } from '@weapp/ui';

const { uiPcClsPrefix } = constants;
const { message, confirm } = Dialog;
const { getHd } = utils;
interface DialogDemoProps {
  history?: any;
}

const prefixCls = `${uiPcClsPrefix}-demo-btn`;

class MyInput extends Component<any, any> {
  constructor(props: any) {
    super(props)
    this.state = {
      value : ''
    }
  }

  handleChange = (value: ReactText) => {
    this.setState({
      value
    })
  }

  render() {
    return (
      <>
        test: <Input value={this.state.value} onChange={this.handleChange}></Input>
      </>
    )
  }
}
class DialogDemo extends Component<DialogDemoProps> {
  instance: any;
  confirm = () => {
    confirm({
      content: '确认删除xxx吗？',
      onOk: () => {
        console.log('OK');
      },
      onCancel: () => {
        console.log('Cancel');
      },
      destroy: () => {
        console.log('组件销毁了')
      },
    });
  }

  confirmDraggable = () => {
    confirm({
      content: '确认删除xxx吗？',
      onOk: () => {
        console.log('OK');
      },
      onCancel: () => {
        console.log('Cancel');
      },
      destroy: () => {
        console.log('组件销毁了')
      },
      draggable: true,
    });
  }

  getInstance = (el: any) => {
    this.instance = el;
  }
  close = () => {
    this.instance && this.instance.onClose()
    console.log('close')
  }
  handleOk = () => {
    this.instance && this.instance.onOk()
    console.log('ok')
  }

  confirmFooter = () => {
    confirm({
      content: '不设置left/top/right/bottom 默认水平垂直居中显示',
      height: 220 * (getHd?.() || 1),
      // enableKeyboardEvent: false,
      customKeyboardEvent:()=> {
        console.log('触发自定义的事件')
        this.close()
        // this.instance && this.instance.onOk()
      },
      getInstance: this.getInstance,
      footer: <div>
                <Button onClick={this.handleOk}>确认（支持键盘事件）</Button>
                <Button onClick={this.close}>取消</Button>
              </div>,
      destroy: () => {
        console.log('组件销毁了')
      },
      onOk: () => {
        console.log('OK');
      },
    });
  }
  confirmInput = () => {
    confirm({
      content:(
        <div>
          <MyInput></MyInput>
        </div>
      ),
      onOk: () => {
        console.log('OK');
      },
      onCancel: () => {
        console.log('Cancel');
      },
      destroy: () => {
        console.log('组件销毁了')
      }
    });
  }

    info  = () => {
    message({
      type: 'info', // type: 'info', 'error', 'success', 'custom'
      content: '这是一条普通提示',
    });
  }

  success = () => {
    message({
      type: 'success', // type: 'info', 'error', 'success', 'custom'
      content: '这是一条询问信息, 会主动消失',
    });
  }

  infoCustomClose = () => {
    message({
      type: 'error', // type: 'info', 'error', 'success', 'custom'
      content: '这是一条询问信息, 不会主动消失',
      delay: 0, // 相当于禁止主动消失
    });
  }

  maxMessageCount = () => {
    message({
      type: 'success', // type: 'info', 'error', 'success', 'custom'
      content: '这是一条询问信息, 会主动消失,最大是三条',
      maxMessageCount: 3
    });
  }

  render() {
    return (
      <div className={prefixCls}>
        <Button onClick={this.confirm}>确认框</Button>
        <Button onClick={this.confirmFooter}>确认框(自定义footer)</Button>
        <Button onClick={this.confirmInput}>确认框(插入input)</Button>
        <Button onClick={this.confirmDraggable}>确认框(可拖拽)</Button>
        <Button type={'primary'} onClick={this.info}>信息提示(info)</Button>
        <Button type={'success'} onClick={this.success}>信息提示(success)</Button>
        <Button type={'danger'} onClick={this.infoCustomClose}>信息提示(error)</Button>
        <Button type={'success'} onClick={this.maxMessageCount}>可控制最大展示消息数</Button>
      </div>
    );
  }
}
```

## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| bodyStyle | Dialog 内容部分样式 | CSSProperties | 否 | |
| bottom | 距离底部高度 | number \| string | 否 | |
| bottomExtraContent | 自定义底部内容 | ReactNode | 否 | |
| bottomExtraContentProps | 自定义弹层底部Layout区参数配置 | LayoutBoxProps | 否 | |
| buttons | 按钮组(顶部) | ReactNode | 否 | |
| closable | 是否显示右上角的关闭按钮 | boolean | 否 | |
| closeAnimation | 关闭动画 | boolean | 否 | false |
| closeIcon | 自定义关闭按钮 | ReactNode | 否 | |
| customRenderDialogBody | 自定义弹框内容(用于复写基于 Dialog 开发的组件弹层内容) | (_: any, ele: ReactNode) => ReactNode | 否 | |
| customRenderDialogTitle | 自定义标题内容(用于复写基于 Dialog 标题内容) | (_: any, ele: ReactNode) => ReactNode | 否 | |
| customRenderInDialogContainer | 在 container 层级下复写弹框内容 | ReactNode | 否 | |
| defaultInnerScale | 默认全屏 | boolean | 否 | |
| destroyOnClose | 关闭时销毁 Drawer 里的子元素 | boolean | 否 | |
| dialogConfig | 功能同Dialog.dialogConfig,优先级高于Dialog.dialogConfig | AnyObj | 否 | |
| dialogId | 弹框唯一标记 | string | 否 | |
| draggable | Dialog 是否开启拖拽 | boolean | 否 | true |
| enableEventEmitter | 启用事件监听方案 | boolean | 否 | true |
| footer | 按钮组(底部) | ReactNode | 否 | |
| forceRender | 预渲染弹框内部内容 | boolean | 否 | |
| getContainer | 弹层容器定位 | (element?: HTMLElement) => HTMLElement | 否 | |
| headerStyle | Dialog 标题区样式 | CSSProperties | 否 | |
| height | Dialog 高度（注意：1. left/right 模式不可改。 2. placement 为 middle 时，高度设置小于 200 不生效） | number \| string | 否 | |
| ignoreCalculationContainer | 忽略 dialog 内部宽高的最大最小值限定规则 | boolean | 否 | false |
| innerScale | 是否全屏，优先级高于defaultInnerScale | boolean | 否 | |
| isEnlargeFullScreen | 全屏模式下弹框宽高占可视区域比例 | boolean | 否 | false |
| isStopPropagation | 禁止阻止冒泡 | boolean | 否 | true |
| keepDialogAlive | 业签模式是否开启本地化存储(dialogId 必须唯一不变) | boolean | 否 | true |
| left | 距离左侧高度 | number \| string | 否 | |
| leftExtraContent | 自定义左侧内容 | ReactNode | 否 | |
| leftExtraContentProps | 自定义弹层左侧Layout区参数配置 | LayoutBoxProps | 否 | |
| mask | 是否展示遮罩 | boolean | 否 | |
| maskClosable | 点击蒙层是否允许关闭 | boolean | 否 | |
| maskStyle | Dialog 遮罩层部分样式 | CSSProperties | 否 | |
| maxResizeHeight | 可调整的最大高度 | string \| number | 否 | |
| maxResizeWidth | 可调整的最大宽度 | string \| number | 否 | |
| message | 消息层内容 | string \| ReactNode | 否 | |
| minResizeHeight | 可调整的最小高度 | string \| number | 否 | |
| minResizeWidth | 可调整的最小宽度 | string \| number | 否 | |
| noMaskClose | 无蒙层，Dialog 外部触发弹窗关闭，非 middle 模式支持 | boolean | 否 | |
| noTitle | 隐藏弹框顶部内容 | boolean | 否 | |
| onAfterClose | Dialog 关闭后回调(带动画效果) | ( () => void; | 否 | |
| onClose | 击遮罩层或右上角叉或取消按钮的回调 | () => void | 否 | |
| onDrag | Dialog 拖拽回调 | (e: HTMLDivElement, position:{x:number, y:number}) => void | 否 | |
| onDragStop | Dialog 拖拽停止回调 | (e: HTMLDivElement, position:{x:number, y:number}) => void | 否 | |
| onResize | 拖拽事件回调 | (style: CSSProperties, container?: HTMLDivElement \| null) => void | 否 | |
| onScale | 放大/缩小弹框回调 | () => void | 否 | |
| path | 通过路由打开 | string | 否 | |
| placement | middle \| top \| right \| bottom \| left | string | 否 | middle |
| ref | 组件实例 | any | 否 | |
| resetDragPosition | 监听弹窗容器宽高变化，变化后重置拖拽位置 | boolean | 否 | |
| resize | 是否支持拖拽调整宽度 | boolean | 否 | |
| right | 距离右侧高度 | number \| string | 否 | |
| rightExtraContent | 自定义右侧内容 | ReactNode | 否 | |
| rightExtraContentProps | 自定义弹层右侧Layout区参数配置 | LayoutBoxProps | 否 | |
| scale | 是否支持最大化 | boolean | 否 | |
| top | 距离顶部高度 | number \| string | 否 | |
| topExtraContent | 自定义顶部内容 | ReactNode | 否 | |
| topExtraContentProps | 自定义弹层顶部Layout区参数配置 | LayoutBoxProps | 否 | |
| visible | 显示受控 | boolean | 否 | |
| width | Dialog 宽度 （注意：placement 为 middle 时，宽度设置小于 380 不生效） | number \| string | 否 | |
| windowOpenUrl | 从新的窗口打开该 dialog 的地址 | string | 否 | |
| wrapClassName | 外层容器 class | string | 否 | |
| wrapStyle | 外层容器自定义样式 | CSSProperties | 否 | |
| zIndex | Dialog 层级 | number | 否 | |

### Dialog.message 参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| content | 消息内容 | ReactNode | 否 | |
| delay | 自定义消息消失时间, 以毫秒为单位（0: 代表不会自动消失） | number | 否 | |
| destroy | 销毁方法 | () => void; | 否 | |
| icon | type = 'custom' 时自定义icon | ReactNode | 否 | |
| maxMessageCount | 最大可同时展示的消息数 | number | 否 | 3 |
| type | 消息类型 | info \| error \| success \| custom | 否 | 'info' |

### Dialog.confirm 参数说明如下：
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| bottom | 距离底部高度 | number \| string | | |
| cancelText | 取消按钮文字 | string \|ReactNode | 否 | |
| cancelType | 取消按钮类型 | BtnType | 否 | |
| closeIcon | 自定义关闭按钮 | ReactNode | 否 | |
| confirmMaskClassName | 确认框蒙层样式名 | string | 否 | |
| confirmWrapId | 确认框蒙包裹层id(主要用于处理全局点击白名单) | string | 否 | |
| content | 内容 | ReactNode | 否 | |
| customKeyboardEvent | 自定义键盘事件触发的回调 | () => void | 否 | |
| draggable | 拖拽 | boolean | 否 | |
| enableHistoryListen | 启用路由监听关闭弹框方案 | boolean | 否 | |
| enableKeyboardEvent | 是否开启键盘事件（键盘事件默认触发onOK回调） | boolean | 否 | true |
| footer | 按钮组(底部) | ReactNode | 否 | |
| getInstance | 获取弹框实例 | (instance: any) => void | | |
| getTitle | 自定义标题 | () => ReactNode | 否 | |
| height | 设置弹窗高度 | number \| string | | |
| hideCancelBtn | 隐藏确定按钮 | boolean | 否 | |
| hideOkBtn | 隐藏确定按钮 | boolean | 否 | |
| icon | 标题图标 | string | 否 | |
| iconBgcolor | 标题图标颜色 | string | 否 | |
| left | 距离左边高度 | number \| string | | |
| okText | 确定按钮文字 | string \| ReactNode | 否 | |
| okType | 确定按钮类型 | BtnType | 否 | |
| onCancel | 取消回调方法 | () => void | 否 | |
| onOk | 确定回调方法 | () => void | 否 | |
| right | 距离右边高度 | number \| string | | |
| title | 标题信息 | string | 否 | |
| top | 距离顶部高度 | number \| string | | |
| width | 设置弹窗宽度 | number \| string | | |
| wrapStyle | 外层容器自定义样式 | CSSProperties | 否 | |
| zIndex | | number | 否 | |