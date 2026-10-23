## 基础用法

```js
import { Component } from 'react';
import { Avatar, constants } from '@weapp/ui';

const AvatarImage1 = 'https://cdn-static-test1.eteams.cn/build/ui/static/media/avatar_demo_1.jpeg?v=c46ea46f';
const AvatarImage2 = 'https://cdn-static-test1.eteams.cn/build/ui/static/media/avatar_demo_2.jpg?v=0456c2c7';

const prefixCls = `${constants.uiPcClsPrefix}-demo-avatar`;

// avatarConfigList 配置：展示不同的头像效果
const avatarConfigList = [
  // 1. 图片显示
  {
    description: '图片显示',
    url: AvatarImage1,
  },
  // 2. 默认性别展示 - 男
  {
    description: '默认性别 - 男',
    gender: 'male',
  },
  // 3. 默认性别展示 - 女
  {
    description: '默认性别 - 女',
    gender: 'female',
  },
  // 4. 默认姓名首字母
  {
    description: '默认姓名首字母(女)',
    name: '王晓晓 (南京)',
    gender: 'female',
    defaultAvatarConfig: {
      avatarType: 'surName',
      avatarFemaleFontColor: '#FFF',
      avatarFemaleBgColor: '#EF8BBA',
    }
  },
  // 5. 默认姓名后两字
  {
    description: '默认姓名后两字(女)',
    name: '王晓晓（上海）',
    gender: 'female',
    defaultAvatarConfig: {
      avatarType: 'shortName',
      avatarFemaleFontColor: '#FFF',
      avatarFemaleBgColor: '#EF8BBA',
    }
  },
  // 6. 默认固定图片 - 裁剪模式
  {
    description: '默认固定图片 - 裁剪模式',
    gender: 'female',
    defaultAvatarConfig: {
      avatarType: 'image',
      avatarFemaleImage: AvatarImage2,
      avatarImageEffect: 'crop',
    }
  },
  // 7. 默认固定图片 - 原比例底色填充模式
  {
    description: '默认固定图片 - 原比例填充模式',
    gender: 'female',
    defaultAvatarConfig: {
      avatarType: 'image',
      avatarFemaleImage: AvatarImage2,
      avatarImageEffect: 'fill',
      avatarImageBorderColor: '#D7D7D7',
      avatarImageBgColor: '#FFFFFF',
    }
  },
];

class AvatarDemo extends Component {
  render() {
    return (
      <div className={prefixCls}>
        <div className={`${prefixCls}-grid`}>
          <h4>个人头像</h4>
          {avatarConfigList.map((config, index) => (
            <div key={index} className={`${prefixCls}-item`}>
              <div className={`${prefixCls}-item-label`}>{config.description}</div>
              <div className={`${prefixCls}-item-content`}>
                <Avatar
                  size="lg"
                  shape="circle"
                  {...config}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }
}

export default AvatarDemo;
```
## 具体参数

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
|------|------|------|----------|--------|
| anonymous | 是否匿名 | boolean | 否 | false |
| avatarIconProps | 图标属性 | IconProps | 否 | - |
| className | class 名 | string | 否 | - |
| customRender | 自定义组件渲染 | `(props: any, ele: ReactElement) => ReactElement` | 否 | - |
| defaultAvatarConfig | 自定义头像的默认配置（不从统一的配置中读取，但是属性需要按照统一的属性） | object | 否 | - |
| gender | 性别 | `'male' \| 'female'` | 否 | `'male'` |
| imgFormat | 请求头像图片尺寸，small 表示压缩后的图片，请求速度会更快，image 表示原图 | `'small' \| 'big' \| 'image'` | 否 | `'small'` |
| inHrmCard | 是否在人力卡片中使用（处理 ie 浏览器图片自适应问题） | boolean | 否 | false |
| isGroup | 是否为群组头像 | boolean | 否 | false |
| loginFree | 是否为免登场景 | boolean | 否 | false |
| name | 姓名 | string | 人员头像必填 | - |
| onClick | 自定义头像点击事件 | `(userId?: string) => void` | 否 | - |
| prefixCls | 默认组件 class 名 | string | 否 | - |
| shape | 形状 | `'circle' \| 'square'` | 否 | `'circle'` |
| size | 尺寸 | `'lg' \| 'md' \| 'sm' \| 'xs'` | 否 | `'lg'` |
| status | 状态 | `'online' \| 'offline'` | 否 | - |
| statusIcon | 在线状态图标 | `IconName \| ReactNode` | 否 | - |
| style | 样式 | CSSProperties | 否 | - |
| url | 图片地址 | string | 人员 \| 群组头像必填 | - |
| useAnonymous | 强制使用匿名展示 | boolean | 否 | false |

### defaultAvatarConfig 参数配置说明：

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
|------|------|------|----------|--------|
| avatarFemaleBgColor | 女性头像背景颜色（avatarType 为姓名相关时生效） | string | 否 | `'#EF8BBA'` |
| avatarFemaleFontColor | 女性头像文字颜色（avatarType 为姓名相关时生效） | string | 否 | `'#FFF'` |
| avatarFemaleImage | 女性头像默认图片 | string | 否 | - |
| avatarImageBgColor | 背景色（仅在 avatarImageEffect='fill' 时生效） | string | 否 | `'#FFF'` |
| avatarImageBorderColor | 边框色（仅在 avatarImageEffect='fill' 时生效） | string | 否 | `'#D7D7D7'` |
| avatarImageEffect | 图片头像效果 | `'crop' \| 'stretch' \| 'fill'` | 否 | `'crop'` |
| avatarMaleBgColor | 男性头像背景颜色（avatarType 为姓名相关时生效） | string | 否 | `'#5D9CEC'` |
| avatarMaleFontColor | 男性头像文字颜色（avatarType 为姓名相关时生效） | string | 否 | `'#FFF'` |
| avatarMaleImage | 男性头像默认图片 | string | 否 | - |
| avatarType | 默认头像格式 | `'surName' \| 'shortName' \| 'image'` | 否 | `'surName'` |

> 注意事项：
1. IconProps、IconName 参数说明： 都是 Icon 图标组件的参数配置，如果未收录相关能力不要随意设置
2. avatarType 参数说明：
  - surName: 姓名首字
  - shortName: 姓名后两字（会自动过滤括号中的备注内容，如"王晓晓 (南京)"会显示为"晓晓"）
  - image: 固定图片
3. avatarImageEffect 参数说明：
  - crop: 裁剪模式，1:1比例，填充整个容器（object-fit: cover）
  - stretch: 拉伸模式，不管原始图片宽高，统一宽高100%显示（object-fit: fill）
  - fill: 原比例填充模式，保持原始比例，完整显示，支持设置边框色和背景色（object-fit: contain）
