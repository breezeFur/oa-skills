## 基础用法
### 直接引入组件进行使用
```js
import { ECharts } from "echarts/core";
import React, { Component } from "react";
import { constants, EChart } from "@weapp/ui";

const prefixCls = `${constants.uiPcClsPrefix}-demo-echarts`;

interface EChartDemoState {
  barEchartOpt: any;
  newOption: any
}
export default class EChartDemo extends Component<{}, EChartDemoState> {
  echarts: any;
  constructor(props: any) {
    super(props);

    this.state = {
      barEchartOpt: {
        title: {
          show: true,
          text: "销量柱状图"
        },
        tooltip: {},
        legend: {
          data: ["销量"]
        },
        xAxis: {
          data: ["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"]
        },
        yAxis: {},
        series: [
          {
            name: "销量",
            type: "bar",
            data: [5, 20, 36, 10, 10, 20]
          }
        ]
      },
      newOption: {
        series: [{
          type: 'custom',
          coordinateSystem: 'none',
          renderItem: (params: any, api: any) => {
            // console.log(this.echarts)
            return {
              type: 'myCustomShape',
              shape: {
                x: api.value(0),
                y: api.value(1),
                width: api.value(2),
                height: api.value(3)
              },
              style: {
                fill: 'red'
              }
            };
          },
          data: [[10, 20, 30, 40]]
        }]
      }
    }
  }


  getInstance = (echart: ECharts) => {
    console.log(echart);
  }
  onReady = (echarts: any) => {
    this.echarts = echarts;
    const MyShape = echarts.graphic.extendShape({
      shape: {
        x: 0,
        y: 0,
        width: 0,
        height: 0
      },
      buildPath: function (ctx: any, shape: any) {
        ctx.moveTo(shape.x, shape.y);
        ctx.lineTo(shape.x + shape.width, shape.y);
        ctx.lineTo(shape.x, shape.y + shape.height);
        ctx.lineTo(shape.x + shape.width, shape.y + shape.height);
        ctx.closePath();
      }
    });
    echarts.graphic.registerShape('myCustomShape', MyShape);
  }
  render() {

    return (
      <div className={prefixCls}>
        <div className={`${prefixCls}-content`}>
          <EChart option={this.state.barEchartOpt} />
          {/* <EChart option={JSON.parse(JSON.stringify(this.state.barEchartOpt))} isEmpty={true} /> */}
          {/* <EChart option={this.state.newOption} onReady={this.onReady} /> */}
        </div>
      </div>
    )
  }
}
```