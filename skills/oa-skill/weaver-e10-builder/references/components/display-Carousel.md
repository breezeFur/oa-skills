## 基础用法

```tsx
import React from "react";
import { Carousel, constants } from "@weapp/ui";

const s1 = "https://scpic.chinaz.net/files/pic/pic9/201801/zzpic9638.jpg";
const s2 =
  "https://scpic3.chinaz.net/Files/pic/pic9/201801/zzpic9478_s_w285.jpg";
const s3 =
  "https://scpic3.chinaz.net/Files/pic/pic9/201806/zzpic12518_s_w285.jpg";

const prefixCls = `${constants.uiPcClsPrefix}-demo-carousel`;

export default class CarouselDemo extends React.Component {
  onImagesReady = (swiper: any) => {};

  render() {
    return (
      <div className={prefixCls}>
        <h2>横向滚动</h2>
        <div style={{ background: "gray" }}>
          <Carousel
            fillWays="imgFill"
            navigation={true}
            speed={2000}
            effect="slide"
            pagination={{ type: "bullets" }}
            onSlideChange={this.onSlideChange}
            onSwiper={this.onSwiper}
          >
            <div style={{ height: "200px" }}>横向滚动 1</div>
            <div style={{ height: "200px" }}>横向滚动 2</div>
            <div style={{ height: "200px" }}>横向滚动 3</div>
            <div style={{ height: "200px" }}>横向滚动 4</div>
          </Carousel>
        </div>
        <h2>横向滚动</h2>
        <Carousel
          fillWays="backgroundFill"
          effect="fade"
          fadeEffect={{ crossFade: true }}
          navigation
          loop
          autoHeight
          effect="cube"
          onImagesReady={this.onImagesReady}
        >
          <img src={s1} alt="" />
          <img src={s2} alt="" />
          <img src={s3} alt="" />
        </Carousel>
        <h2>纵向滚动</h2>
        <Carousel
          style={{ height: "300px" }}
          fillWays="backgroundFill"
          fadeEffect={{ crossFade: true }}
          navigation
          loop
          autoHeight
          direction="vertical"
        >
          <img src={s1} alt="" />
          <img src={s2} alt="" />
          <img src={s3} alt="" />
        </Carousel>
      </div>
    );
  }
}
```

## 参数说明

### 组件参数说明如下

| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| autoplay | 自动切换 | boolean/Object | false | false |
| effect | 切换方式 | slide\| fade\| cube\| coverflow\| flip | false | slide |
| effects | 切换效果 | string | false | slide |
| fadeEffect | fade 效果参数。可选参数：crossFade。 默认：false。关闭淡出。过渡时，原 slide 透明度为 1（不淡出），过渡中的 slide 透明度从 0->1（淡入），其他 slide 透明度 0。可选值：true。开启淡出。过渡时，原 slide 透明度从 1->0（淡出），过渡中的 slide 透明度从 0->1（淡入），其他 slide 透明度 0。 | boolean | false | false |
| fillWays | 填充方式 | imgFill \| backgroundFill | false | backgroundFill |
| loop | 是否轮播 | boolean | boolean | false |
| navigation | 前进后退按钮 | boolean/Object | false | false |
| onSlideChanger | 切换图片时的回调函数 | (swiperInstance)=>void | false | |
| onSwiper | swiper加载完后执行 | (swiperInstance)=>void | false | |
| pagination | 分页器 | boolea/Object | false | false |
| slidesPerView | 设置 slider 容器能够同时显示的 slides 数量(carousel 模式) | number \| auto | false | 1 |
| speed | 切换动画速度，即 slider 自动滑动开始到结束的时间（单位 ms），也是触摸滑动时释放至贴合的时间。 | number | false | 300 |

### pagination配置说明
```tsx
pagination={{ type: 'bullets' }}
1、横向滚动分页器类型，可选 bullets 圆点 fraction 分式 progress 进度条 custom 自定义
2、纵向滚动分页器类型，可选fraction 分式 progress 进度条 custom 自定义
```
## 注意事项
1、使用effect=fade时防止图片重叠请添加以下代码
```tsx
fadeEffect={{ crossFade: true }}
```
2、swiper默认会监听浏览器窗口的变化,如果carousel组件需要监听父级容器的视口变化请添加resizeObserver属性
```tsx
<Carousel
    fillWays="backgroundFill"
    weId={`${this.props.weId || ''}_013hkd`}
    effect='fade'
    fadeEffect={{ crossFade: true }}
    navigation
    loop
    autoHeight
    resizeObserver
>
```
