import { appInfo } from '@weapp/utils';
const { publicUrl } = appInfo('@weapp/ecodesdk');
const API_BASE = `${publicUrl}/api/ebuilder/form/dataset`;

/**
 * Fetches data with a timeout and retry mechanism.
 * @param {string} url - The URL to fetch.
 * @param {RequestInit} options - Fetch options.
 * @param {number} [timeoutMs=5000] - Timeout in milliseconds.
 * @param {number} [retries=3] - Number of retries.
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, options, timeoutMs = 5000, retries = 3) {
  let lastError;

  for (let i = 0; i <= retries; i++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      lastError = error;
      
      // If it's the last attempt, throw the error
      if (i === retries) {
        throw new Error(`Request failed after ${retries + 1} attempts. Last error: ${lastError.message}`);
      }
      
      // Optional: Add exponential backoff or simple delay before retrying
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
  
  // This line should theoretically not be reached due to the throw above
  throw lastError;
}

/**
 * 获取字段定义
 * @param {string} objId 
 * @param {string} userId 
 * @returns {Promise<Array>}
 */
export async function getFields(objId, userId) {
  const response = await fetchWithRetry(`${API_BASE}/v1/getFields`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userid: userId,
      objId: objId,
      tenantKey: TENANTKEY,
    }),
  });

  const result = await response.json();
  
  if (result.message.code !== '0') {
    throw new Error(`获取字段失败: ${result.message.msg}`);
  }
  
  // 按 number 排序，保持表单原始顺序
  return result.data.mainFields.sort((a, b) => a.number - b.number);
}

/**
 * 获取所有数据
 * @param {string} objId 
 * @param {string} userId 
 * @returns {Promise<Array>}
 */
const TENANTKEY = TEAMS.currentTenant.tenantKey
export async function getAllData(objId, userId) {
  const response = await fetchWithRetry(`${API_BASE}/v2/getAllData?tenantkey=${TENANTKEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userid: userId,
      datajson: {
        header: { objId: objId },
      },
    }),
  });

  const result = await response.json();
  
  if (result.message.code !== '0') {
    throw new Error(`获取数据失败: ${result.message.msg}`);
  }
  
  return result.data.datajson.datas || [];
}

// ==================== 数据解析函数 ====================

/**
 * 解析单个字段的值
 * @param {any} value 
 * @param {Object} fieldDef 
 * @returns {Object} ParsedValue
 */
export function parseFieldValue(value, fieldDef) {
  // 处理 undefined 或 null 值
  if (!value) {
    return { displayValue: '', rawValue: value };
  }

  // 处理数组类型（Select, RadioBox, CheckBox 等多选/单选）
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return { displayValue: '', rawValue: [] };
    }
    
    // 提取选项名称列表
    const optionNames = value
      .map(v => v?.fieldOptionName || v?.fieldValue || '')
      .filter(v => v);
    
    const options = value.map(v => ({
      id: v?.fieldOptionId || '',
      name: v?.fieldOptionName || v?.fieldValue || '',
    }));
    
    return {
      displayValue: optionNames.join(', '),
      rawValue: value,
      options: options,
    };
  }
  
  // 处理普通对象
  const fieldType = fieldDef.fieldType;
  
  switch (fieldType) {
    case 'Employee':
      // 员工字段可能返回用户ID或姓名
      return {
        displayValue: value.fieldValue || '',
        rawValue: value,
      };
    case 'Date':
      // 日期格式化
      const dateValue = value.fieldValue;
      if (dateValue && dateValue.includes('-')) {
        return { displayValue: dateValue, rawValue: value };
      }
      return { displayValue: dateValue || '', rawValue: value };
    case 'Number':
      return {
        displayValue: value.fieldValue || '0',
        rawValue: value,
      };
    case 'Select':
    case 'RadioBox':
      return {
        displayValue: value.fieldOptionName || value.fieldValue || '',
        rawValue: value,
      };
    default:
      return {
        displayValue: value.fieldValue || '',
        rawValue: value,
      };
  }
}

// ==================== 数据格式转换函数 ====================

/**
 * 将API返回的复杂数据结构转换为简单的键值对格式
 * @param {Array} dataRows 
 * @param {Array} fields 
 * @returns {Array<SimpleDataItem>}
 */
export function transformToSimpleFormat(dataRows, fields) {
  if (!dataRows || !dataRows.length) return [];
  // Create a map for quick lookup: fieldId -> FieldDefinition
  const fieldMap = new Map();
  fields.forEach(field => {
    fieldMap.set(field.fieldId, field);
  });

  return dataRows.map(row => {
    const simpleItem = {};
    
    // Copy row-level id (data ID) to simple item
    if (row.id) {
      simpleItem.id = row.id;
    }

    // Process mainTable
    if (row.mainTable) {
      Object.entries(row.mainTable).forEach(([key, value]) => {
        // Handle the special 'id' field in mainTable
        if (key === 'id' && value && typeof value === 'object') {
          simpleItem.id = value.fieldValue || value.fieldOptionName || '';
          return;
        }

        let actualFieldId;
        let parsedValue;

        // Case 1: Value is an object/array containing fieldId (Standard dynamic form structure)
        if (value && typeof value === 'object') {
          if (Array.isArray(value)) {
            // For arrays (like RadioBox/Select), the fieldId is usually in the first item
            actualFieldId = value[0]?.fieldId;
          } else {
            // For objects (like TextArea, Number), the fieldId is directly on the object
            actualFieldId = value.fieldId;
          }
        } 
        // Case 2: Value is a primitive (fallback)
        else {
           actualFieldId = key;
        }

        // Find the field definition using the extracted actualFieldId
        const fieldDef = actualFieldId ? fieldMap.get(actualFieldId) : undefined;
        
        // Determine the key: Use fieldId if available, otherwise fallback to original key
        const resultKey = fieldDef ? fieldDef.fieldId : key;

        // Parse the value using the correct field definition
        // Fallback definition if fieldDef is missing
        const fallbackDef = {
          id: 0,
          fieldId: actualFieldId || key,
          fieldName: resultKey, 
          fieldType: 'String',
          fieldKey: 'Text',
          number: 0,
          multiSelect: false,
          objId: 0
        };

        parsedValue = parseFieldValue(value, fieldDef || fallbackDef);

        // Assign to result using the fieldId as the key
        let finalValue = parsedValue.displayValue;

        // 特殊类型统一返回 fieldOptionId（写入和组件回显需要的 ID）
        // Select/RadioBox/CheckBox → 选项ID, Employee → 人员ID, Department → 部门ID, FileComponent → 文件ID
        // 如需显示名称，配合 getFieldOptions 或从 uploadedFiles/selectedPerson 状态中获取
        const fieldType = fieldDef?.fieldType;
        const isIdType = fieldType === 'Select' || fieldType === 'RadioBox' || fieldType === 'CheckBox'
            || fieldType === 'Employee' || fieldType === 'Department' || fieldType === 'FileComponent';

        if (isIdType) {
            if (Array.isArray(value)) {
                const ids = value
                    .map((v) => v?.fieldOptionId)
                    .filter((id) => id !== undefined && id !== null && id !== '');

                finalValue = ids.length > 0 ? ids.join(',') : '';
            } else if (value && typeof value === 'object') {
                finalValue = value.fieldOptionId ? String(value.fieldOptionId) : '';
            }
        }
        
        simpleItem[actualFieldId] = finalValue;
      });
    }
    
    return simpleItem;
  });
}

/**
 * 获取转换后的简单格式数据
 * @param {string} objId 
 * @param {string} userId 
 * @returns {Promise<Array<SimpleDataItem>>}
 */
export async function getSimpleData(objId, userId) {
  const [fields, dataRows] = await Promise.all([
    getFields(objId, userId),
    getAllData(objId, userId)
  ]);
  const result = transformToSimpleFormat(dataRows, fields);
  return result;
}

// ==================== ID → 名称映射（用于表格展示） ====================

/**
 * 将 simpleData 中 Select/Employee/Department 等字段的 ID 替换为显示名称。
 * getSimpleData 返回的是 ID（用于写入），表格展示需要名称，用此函数转换。
 *
 * @param {Array<Object>} simpleData — getSimpleData 的返回值
 * @param {Object} optionsMap — { fieldId: [{valueKey, name}, ...] }，valueKey→name 的映射表
 * @returns {Array<Object>} 字段值为显示名称的新数组
 *
 * 用法：
 *   var [data, setData] = useState([]);
 *   useEffect(function () {
 *     Promise.all([
 *       getSimpleData(OBJ_ID, USER_ID),
 *       getFieldOptions(F.status, FORM_ID),
 *     ]).then(function ([rows, statusOpts]) {
 *       setData(withDisplayNames(rows, { [F.status]: statusOpts }));
 *     });
 *   }, []);
 */
export function withDisplayNames(simpleData, optionsMap) {
  return simpleData.map(function (row) {
    var displayRow = {};
    Object.keys(row).forEach(function (key) {
      var options = optionsMap[key];
      if (options && options.length) {
        var ids = (row[key] || '').split(',');
        displayRow[key] = ids.map(function (id) {
          var opt = options.find(function (o) { return o.valueKey === id; });
          return opt ? opt.name : id;
        }).join(', ');
      } else {
        displayRow[key] = row[key];
      }
    });
    return displayRow;
  });
}

// ==================== 保存表单数据 ====================

/**
 * 保存表单数据
 * @param {string} objId 
 * @param {Object} formData 
 * @param {string} userId 
 * @returns {Promise<Object>}
 */
export async function saveFormData(objId, formData, userId) {
  const requestData = {
    userid: userId,
    datajson: {
      datas: {
        mainTable: formData,
        operationinfo: {
          doAction: 'n', // 新增操作
          optionNoFindIgnore: 'false'
        }
      },
      header: {
        objId: objId,
        tenantKey: TENANTKEY
      }
    }
  };

  const response = await fetchWithRetry(`${API_BASE}/v1/saveFormData`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData),
  });

  const result = await response.json();
  if (result.data && result.data.isSuccess === false) {
    throw new Error('保存失败: ' + (result.data.msg || JSON.stringify(result.data)));
  }
  if (result.message && result.message.code !== '0') {
    throw new Error('保存失败: ' + (result.message.msg || JSON.stringify(result.message)));
  }
  return result;
}

// ==================== 更新表单数据 ====================

/**
 * 更新表单数据
 * @param {string} objId
 * @param {Object} formData
 * @param {string} dataId - 数据ID
 * @param {string} userId
 * @returns {Promise<Object>}
 */
export async function updateFormData(objId, formData, dataId, userId) {
  const requestData = {
    userid: userId,
    datajson: {
      datas: {
        mainTable: Object.assign({ id: dataId }, formData),
        operationinfo: {
          doAction: 'u',
          optionNoFindIgnore: 'false'
        }
      },
      header: {
        objId: objId,
        tenantKey: TENANTKEY
      }
    }
  };

  const response = await fetchWithRetry(`${API_BASE}/v1/saveFormData`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData),
  });

  const result = await response.json();
  if (result.data && result.data.isSuccess === false) {
    throw new Error('更新失败: ' + (result.data.msg || JSON.stringify(result.data)));
  }
  if (result.message && result.message.code !== '0') {
    throw new Error('更新失败: ' + (result.message.msg || JSON.stringify(result.message)));
  }
  return result;
}

// ==================== 删除表单数据 ====================

/**
 * 删除表单数据
 * @param {string} objId - 表单ID (objId)
 * @param {string|number} dataId - 数据ID
 * @param {string} userId - User ID
 * @returns {Promise<Object>}
 */
export async function deleteFormData(objId, dataId, userId) {
  const requestData = {
    userid: userId,
    datajson: {
      header: {
        objId: objId
      },
      mainTable: {
        id: dataId
      },
      operationinfo: {
        fieldNoFindIgnore: 'false'
      }
    }
  };

  const response = await fetchWithRetry(`${API_BASE}/v2/deleteData`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json' 
    },
    body: JSON.stringify(requestData),
  });

  const result = await response.json();
  
  if (result.message.code !== '0') {
    throw new Error(`删除数据失败: ${result.message.msg}`);
  }

  return result;
}

// ==================== 获取选项字段的具体选项值 ====================
export async function getFieldOptions(fieldId, objId) {
  // 注意：第二个参数是 objId（表单对象 ID），与 getSimpleData/saveFormData 用的是同一个值
  const infoUrl = `${publicUrl}/api/ebuilder/form/obj/getInfo/${objId}`;
  const infoResponse = await fetchWithRetry(infoUrl, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  const infoResult = await infoResponse.json();
  if (infoResult.code !== 200 || !infoResult.status) {
    throw new Error(`获取表单信息失败: ${infoResult.msg || 'Unknown error'}`);
  }
  const formIdNew = infoResult.data?.formId;
  
  if (!formIdNew) {
    throw new Error('未能从表单信息中获取有效的 formId');
  }

  const url = `${publicUrl}/api/ebuilder/form/form/field/manage/getFormField`;    
  const requestBody = {
    module: "ebuilderform",
    formTableField: {
      formField: {
        id: fieldId,
        form: {
          id: formIdNew // Use the dynamically fetched formId
        }
      }
    }
  };
  const response = await fetchWithRetry(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });

  const result = await response.json();
  if (result.code !== 200 || !result.status) {
    throw new Error(`获取字段选项失败: ${result.msg || 'Unknown error'}`);
  }
  
  const options = result.data?.options || [];
  return options.map(option => ({
    valueKey: option.valueKey,
    name: option.name
  }));
}