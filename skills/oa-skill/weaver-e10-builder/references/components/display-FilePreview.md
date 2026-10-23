## 文件预览组件的使用

```js
import React from 'react';
import { CorsComponent } from '@weapp/ui';

export default class FilePreviewDemo extends React.Component {

    constructor(props) {
        super(props);
    }

    render() {
        return (
            <CorsComponent
                app={'@weapp/file'}
                compName={'FilePreview'}
                id={'3084136555520685109'}
                style={{ width: '100%', height: '200px' }}
            />
        );
    }
}
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `app` | 固定为 `'@weapp/file'` |
| `compName` | 固定为 `'FilePreview'` |
| `id` | 文件 ID（字符串），从附件字段的 `fileid` 获取 |
| `style` | 容器样式，建议设置 `width` 和 `height` |

### 获取文件 ID

附件字段（FileComponent）的 `fileid` 可通过以下方式获取：

**1. 从表单数据读取** — `getSimpleData` 对 FileComponent 字段返回 `fieldOptionId`（即 fileid）：
```js
var fileId = item[F.attachment];
// 多文件时为逗号分隔，取第一个
var firstFileId = (fileId || '').split(',')[0];
```

**2. 上传时** — 从 `uploadedFiles` 状态中获取：
```js
var fileId = uploadedFiles[0].fileid;
```
