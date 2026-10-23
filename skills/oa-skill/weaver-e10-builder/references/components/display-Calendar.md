## 基础用法

```tsx
import { Component } from 'react';
import { Calendar, Button, DateQuickFilter } from '@weapp/ui'

interface State {
  events?: any[];
  date?: string | number | Date;
  dateExtra: any;
  holidayEndDate: any;
}

export default class CalendarDemo extends Component<any, State> {
  constructor(props: any) {
    super(props);
    this.state = {
      date: '2021-3-26',
      holidayEndDate: '2021-06-01',
      events: [
        {
          id: '1',
          title: '非全天数据',
          start: '2021-03-01 08:00',
          end: '2021-03-01 18:00',
          borderColor: '#81AFE2',
        },
        {
          id: '1.5',
          title: 'All Day Event',
          start: '2021-03-02',
          end: '2021-03-05',
          backgroundColor: '#DCEDFF',
          borderColor: '#81AFE2',
          textColor: 'black',
          addTitle: '测试追加title'
        },
        {
          id: '2',
          title: '测试数据001',
          start: '2021-03-07',
          end: '2021-03-10',
          backgroundColor: '#E5E5E5',
          borderColor: '#A7A7A7'
        },
        {
          id: '3',
          groupId: 999,
          title: 'Repeating Event',
          start: '2021-03-09',
          end: '2021-03-09',
          backgroundColor: '#DCEDFF',
          borderColor: '#81AFE2',
        },
        {
          id: '4',
          title: 'Conference',
          start: '2021-03-11',
          end: '2021-03-13',
          backgroundColor: '#DCEDFF',
          borderColor: '#81AFE2',
        },
        {
          id: '5',
          title: '今日关注',
          start: '2021-03-12',
          end: '2021-03-12',
          backgroundColor: '#FFF1D6',
          borderColor: '#D7B167'
        },
      ],
      dateExtra: {
        '2021-03-15': { info: true, sign: { text: '班', textIcon: 'Icon-WeChat03-o', color: '#FAAD14', icon: 'Icon-WeChat03-o' } },
        '2021-03-16': { info: true, sign: { text: '休', color: '#52C41A', icon: 'Icon-robot' } },
        '2021-03-17': { info: true, sign: { icon: 'Icon-like', color: '#5d9cec' } },
        '2021-03-18': { info: true, sign: { text: '休', textIcon: 'Icon-robot', color: '#5d9cec' } },
        '2021-03-19': { info: true, sign: { text: '假' } },
        '2021-03-20': { info: true, sign: { icon: 'Icon-Speechless', } },
        '2021-03-22': { info: true, sign: { icon: ['Icon-WeChat03-o', 'Icon-Speechless'] } },
        '2021-03-23': {
          info: true,
          sign: {
            icon: [
              { name: 'Icon-WeChat03-o', color: '#FAAD14' },
              { name: 'Icon-robot', color: '#52C41A' },
              'Icon-like'
            ]
          }
        },
        '2021-03-25': { info: true, sign: { icon: 'Icon-WeChat03-o', text: "休", textIcon: "Icon-Rest-mcolor" } },
      }
    };
  }

  eventClick = (arg?: any) => {}
  eventDrop = (arg?: any) => {}
  onCellClick = (arg?: any) => {}
  onMultiSelect = (dates?: any[]) => {}
  select = (arg?: any) => {}

  // 当通知事项过多时，会展示
  moreLinkContent = (arg: any) => {
    return `<div>更多</div>`
  }

  changeHolidayEndDate = () => this.setState({ holidayEndDate: '2021-12-31' })
  onDatePickerChange = (value: any) => this.setState({ date: value as string })
  eventMouseEnter = (data: any) => console.info('eventMouseEnter', data)

  render() {
    const { events, date, dateExtra } = this.state;
    return (<div style={{ height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <DateQuickFilter type={'month'} value={date} onChange={this.onDatePickerChange} style={{ marginRight: '10px' }} />
        <Button onClick={this.changeHolidayEndDate} type={'primary'}>改变holidayEndDate</Button>
      </div>
      <Calendar date={date}/>
      <br />
      <Calendar date={date} mode={'week'}/>
      <br />
      <Calendar date={date} mode={'doubleWeek'} weekNames={["星期天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]} contentHeight={800} dateExtra={dateExtra} hideLunar={true} />
      <br />
      <Calendar
        events={events}
        date={date}
        eventClick={this.eventClick}
        contentHeight={800}
        isDrag={true}
        eventDrop={this.eventDrop}
        weekNames={["星期天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]}
        onMultiSelect={this.onMultiSelect}
        onCellClick={this.onCellClick}
        dateExtra={dateExtra}
        selectable={true}
        select={this.select}
        moreLinkContent={this.moreLinkContent}
        titlePopoverVisible={false}
        fullcalendarProps={{
          eventConstraint: {
            start: '10:00',
            end: '18:00',
          },
        }}
        holidayStartDate={'2021-1-1'}
        holidayEndDate={this.state.holidayEndDate}
      />
    </div>);
  }
}
```

## 参数说明
### 组件参数说明如下
| 参数 | 说明 | 类型 | 是否必填 | 默认值 |
| --- | --- | --- | --- | --- |
| allDayText | 自定义全天视图名称 | string | | |
| contentHeight | 视图高度 | number | | 600 |
| customHolidayDatas | 自定义节假日数据配置 | any[] | | |
| customHolidayUrlDatas | 自定义获取节假日接口数据配置 | any | | |
| date | 展示日期 | Date / string | | |
| dateExtra | 日期标识，如： 班，休 | any | | |
| endTime | 周,日模式下结束时间， 如： '18:00' | string | | |
| eventClick | 点击通知事项回调 | (arg?: any) => void; | | |
| eventDrop | 拖拽停止并且已经拖拽到其它位置了 | (arg?: any) => void; | | |
| eventResize | 大小调整完成并已经执行更新时触发 | (arg?: any) => void; | | |
| events | 通知事项数据源 | any[] | | |
| fixedWeekCount | 是否显示非本月数据 | boolean | | false |
| fullcalendarProps | fullcalendar 原有 props 都在此处配置 | any | | |
| getInstance | 获取 calendar 实例 | (calendar: any ) => void | | |
| hideLunar | 是否隐藏农历 | boolean | | false |
| holidayEndDate | 接口内配置：节假日查询的结束日期 | 可被 dayjs()解析的类型 | | |
| holidayStartDate | 接口内配置：节假日查询的开始日期 | 可被 dayjs()解析的类型 | | |
| isDrag | 通知事项是否可以拖动 | boolean | | false |
| lineHeight | 周，日模式下行高 | number | | |
| lunarFestival | 阴历节日 | string[] | | |
| mode | 初始模式 | month, doubleWeek, week, day | | |
| moreLinkContent | 自定义更多标签 | (arg?: any) => string; | | |
| navLinks | 日期 label 是否可以点击 | boolean | | false |
| needHoliday | 是否开启节假日模式 | boolean | | true |
| nowTimeline | 日模式下，当前时间线(红色) | boolean | | false |
| onCellClick | 点击格子空白区域回 | (arg?: any) => void; | | |
| onMultiSelect | 多选日期回调 | (dates?: any[]) => void; | | |
| renderEventContent | 自定义渲染每条数据 | (eventContent?: EventContentArg) => string; | | |
| renderWeekTopTitle | 周模式下，顶部周信息自定义渲染 | renderWeekTopTitle?:(arg?: Date) => string | | |
| scrollTime | 日,周模式下滚动区域偏移时间点 | string | | '10:00:00' |
| select | 点击空白区域/选择区域内容触发 | (arg?: any) => void/boolean | | 使用该属性时， selectable 需为 true,return true 清除选中样式 |
| selectable | 是否允许长按鼠标选择区域 | boolean | | false |
| showSolarTerm | 是否展示节气 | boolean | | |
| slotDuration | 一格时间槽代表多长时间，默认 00:30:00（30 分钟） | string | | |
| slotEventOverlap | 相同时间段的多个日程视觉上是否允许重叠 | boolean | | true |
| slotLabelFormat | 周模式下，自定义渲染左侧时间区域 | any[] | | |
| solarFestival | 阳历节日 | string[] | | |
| startTime | 周,日模式下起始时间， 如： '08:00' | string | | |
| titlePopoverVisible | 标题鼠标放上去是否隐藏 title | boolean | | false |
| useAttendanceHoliday | 是否接入考勤组接口数据 | boolean | | |
| useAttendanceSameViewHoliday | 是否使用面板内同视图的节假日数据 | boolean | | |
| weekNames | 月模式下日历周显示标签 | string[] | | |
| weekStart | 设置一周中显示的第一天是哪天，周日是 0，周一是 1，类推 | number | | 1 |

### 节假日模式说明
```tsx
calendar组件耦合了后端节假日接口 /api/attend/web/calendar/queryHolidayByUser,
请求方式如下
{
  url: `/api/attend/web/calendar/queryHolidayByUser`,
  method: 'post',
  data: {
    "userId": id, //此id为 window?.TEAMS?.currentUser?.id
    "beginDate": holidayStartDate, //当未传值或不合法时，会按照当前日期当月的开始日期传入
    "endDate": holidayEndDate //当未传值或不合法时，会按照当前日期当月的结束日期传入
  }
}
1.openHoliday默认为ture，会开启节假日模式
2.holidayDatas数据格式如下
{
  "id":"3573169252047636086",//必填
  "day":1633017600000, //必填
  "type":"HOLIDAY", //必填
  "status":"VALID",//必填 -> 当为 'VALID'时，才会添加类名
}
3.calendar组件会根据返回结果的status状态和day的日期类型，赋值给fc-daygrid-day的每个单元格以type的class类名，用户可以根据需求自定义复写样式
4.当传入customHolidayUrlDatas，内部会将customHolidayUrlDatas作为请求参数发起请求，并在内部处理返回数据给内部holidayDatas
5.当前端直接传入了customHolidayDatas时，会直接将值符给内部holidayDatas，不走接口
6.当走自定义url或customHolidayDatas时，需要注意返回的数据格式
```
### dataExtra说明
```tsx
按照以下下数据为例
const dateExtra = {
        '2021-03-15': { info: true, sign: { text: '班', textIcon: 'Icon-WeChat03-o', color: '#FAAD14', icon: 'Icon-WeChat03-o' } },
        '2021-03-16': { info: true, sign: { text: '休', color: '#52C41A', icon: 'Icon-robot' } },
        '2021-03-17': { info: true, sign: { icon: 'Icon-like', color: '#5d9cec' } },
        '2021-03-18': { info: true, sign: { text: '休', textIcon: 'Icon-robot', color: '#5d9cec' } },
        '2021-03-19': { info: true, sign: { text: '假' } },
        '2021-03-20': { info: true, sign: { icon: 'Icon-Speechless', } },
        '2021-03-22': { info: true, sign: { icon: ['Icon-WeChat03-o', 'Icon-Speechless'] } },
        '2021-03-23': {
          info: true,
          sign: {
            icon: [
              { name: 'Icon-WeChat03-o', color: '#FAAD14' },
              { name: 'Icon-robot', color: '#52C41A' },
              'Icon-like'
            ]
          }
        },
      }
1.sign表示开启额外数据展示
2.当sign中的text存在时，开启月模式单元格头部右上角展示（展示文字），当textIcon存在时，右上角展示图标，text内容在鼠标hover时出现
3.color表示右上角展示底色 
4.icon表示月模式单元格头部日期右侧的额外图标
```
### solarFestival与lunarFestival说明
```tsx
按照以下下数据为例
const solarFestival = ['0303 三月三号节日','0404 四月四号节日']
const lunarFestival = ['0303 三月初三','0404 四月初四']
分别代表农历节日与阳历节日
同时也可以用ecode来控制
const solarFestival = window?.weapp_ui_sFtv || window?.weapp_ui_solarFestival
const lunarFestival = window?.weapp_ui_lFtv || window?.weapp_ui_lunarFestival
const showSolarTerm = window?.weapp_ui_showSolarTerm
```
