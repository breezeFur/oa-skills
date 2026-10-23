## 基础用法
```js
import { Component } from 'react';
import { Upload, UploadData, Icon } from '@weapp/ui';
import { data } from '../mock';

class UploadDemo extends Component<any> {
  state = { data: data }
  onChange = (data?: UploadData[]) => {
    this.setState({ data })
  }
  renderListUploaded = (data: UploadData[], instance: any, com: any) => {
    return <div>{
      data.map((item) => {
        return <div key={item.fileid} style={{ display: 'flex', height: '20px', alignItems: 'center' }}>
          <Icon name="Icon-Knowledge-document-o" />
          <span style={{ display: 'inline-block', width: '200px', marginLeft: '10px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</span>
        </div>
      })
    }
    </div>
  }
  beforeUpload = (file: File): Promise<void | File> => {
    return new Promise((rs, rj) => {
      // xxxxx
      rj()
    })
    // or return false
    // or return this.encryFile(file)
  }
  encryFile = (file: File) => {
    // 可以在这里对文件进行校验,压缩,加密等操作
    // return xxx
  }
  render() {
    return (
      <div>
        <Upload
         
          data={this.state.data}
          onChange={this.onChange}
          uploadParams={{
            module: 'document'
          }}
          beforeUpload={this.beforeUpload}
        />
      </div>
    );
  }
}

export default UploadDemo;
```