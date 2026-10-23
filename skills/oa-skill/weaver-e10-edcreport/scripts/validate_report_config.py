#!/usr/bin/env python3
"""
E-Builder 报表配置验证脚本

用法:
    python validate_report_config.py <配置文件路径>

验证报表配置 JSON 的完整性和正确性，包括:
- 必填字段检查
- 枚举值合法性
- 父格坐标合法性
- 多数据集父格筛选 / 自定义筛选 fieldKey 与 type 枚举检查
- Formula 单元格格式（cellText 无前导 '='、countType/displayType）
- 循环引用检测
"""

import json
import sys
import os
import re
from typing import Dict, List, Any, Tuple, Optional


# === 枚举定义 ===

CELL_TYPES = {
    "Const", "Field", "Formula", "DateTime", "DateField",
    "SequenceNumber", "AllCheck", "SlashWord", "SystemField",
    "Control", "TreeField"
}

DISPLAY_TYPES = {"List", "Group", "Count", "Tree"}

EXPAND_TYPES = {"NoExpand", "Horizontal", "Vertical"}

GROUP_TYPES = {
    "year", "yearmonth", "month", "yearmonthday",
    "yearweekday", "monthweekday", "none"
}

COUNT_TYPES = {"sum", "max", "min", "avg", "count", "distinctcount", "none"}

ORDER_TYPES = {"no", "asc", "desc"}

PARENT_TYPES = {"empty", "default", "custom"}

FILTER_OPTIONS = {
    "Equals", "NotEquals", "Greater", "GreaterOrEquals",
    "Less", "LessOrEquals", "StartsWith", "NotStartsWith",
    "EndsWith", "NotEndsWith", "Contain", "NotContain",
    "Include", "NotInclude", "Null", "NotNull"
}

# 设计器不接受的简写 type（会导致筛选无效或回显异常）
LEGACY_FILTER_TYPES = {"eq", "uncontains", "empty", "nempty", "contains", "neq"}

# fieldKey: {dataSetId}.{sourceId}.{fieldName}
FIELD_KEY_PATTERN = re.compile(r"^\d+\.\d+\.field_\d+$")

# 主题编号范围
THEME_RANGE = set(range(1, 11))

# 对齐值
H_ALIGN_VALUES = {0, 1, 2}
V_ALIGN_VALUES = {0, 1, 2}


class ValidationReport:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warning(self, msg: str):
        self.warnings.append(msg)

    def info_msg(self, msg: str):
        self.info.append(msg)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def print_report(self):
        if self.info:
            print("\n=== 信息 ===")
            for msg in self.info:
                print(f"  [INFO] {msg}")

        if self.warnings:
            print("\n=== 警告 ===")
            for msg in self.warnings:
                print(f"  [WARN] {msg}")

        if self.errors:
            print("\n=== 错误 ===")
            for msg in self.errors:
                print(f"  [ERROR] {msg}")

        print(f"\n总计: {len(self.errors)} 错误, {len(self.warnings)} 警告, {len(self.info)} 信息")

        if not self.has_errors():
            print("✅ 配置验证通过!")
        else:
            print("❌ 配置验证失败，请修正上述错误!")


def _cell_type(field: Dict) -> Dict:
    """从 style.cellType 提取 cellType 对象"""
    ct = field.get("style", {}).get("cellType") if isinstance(field.get("style"), dict) else None
    return ct if isinstance(ct, dict) else {}


def _merged_filter_source(field: Dict) -> Dict:
    """合并顶层与 cellType 上的筛选配置（cellType 优先）"""
    ct = _cell_type(field)
    out = {}
    for key in ("leftFilterField", "topFilterField", "customFilterField", "subordination"):
        if key in ct and ct[key]:
            out[key] = ct[key]
        elif key in field and field[key]:
            out[key] = field[key]
    return out


def _check_field_key_ref(report: ValidationReport, prefix: str, label: str, value: Optional[str]):
    if not value:
        return
    if value.startswith("field_") and value.count(".") == 0:
        report.error(f"{prefix} {label} 使用了裸 field_xxx，应改为 fieldKey: {{dataSetId}}.{{sourceId}}.{value}")
        return
    if FIELD_KEY_PATTERN.match(value):
        return
    if value.count(".") < 2:
        report.warning(f"{prefix} {label} 可能不是 fieldKey 格式（应为 dataSetId.sourceId.fieldName）: {value}")
    elif not FIELD_KEY_PATTERN.match(value):
        report.warning(f"{prefix} {label} fieldKey 格式异常: {value}")


def _validate_filter_item(report: ValidationReport, prefix: str, filter_name: str, idx: int, item: Dict, *, require_parent: bool):
    loc = f"{filter_name}[{idx}]"
    ftype = item.get("type")
    if ftype in LEGACY_FILTER_TYPES:
        report.error(f"{prefix} {loc} type 使用了简写 '{ftype}'，应改为平台枚举（如 Equals/NotContain/Null/NotNull）")
    elif ftype and ftype not in FILTER_OPTIONS:
        report.error(f"{prefix} {loc} type 值无效: {ftype}，有效值: {FILTER_OPTIONS}")

    if require_parent:
        if "parentField" not in item or not item["parentField"]:
            report.warning(f"{prefix} {loc} 缺少 parentField")
        else:
            _check_field_key_ref(report, prefix, f"{loc}.parentField", item["parentField"])

    if "currentField" not in item or not item["currentField"]:
        report.warning(f"{prefix} {loc} 缺少 currentField")
    else:
        _check_field_key_ref(report, prefix, f"{loc}.currentField", item["currentField"])
        cid = item.get("id")
        if cid and cid != item["currentField"]:
            if len(str(cid)) <= 36 and "-" in str(cid) and str(cid).count(".") < 2:
                report.error(f"{prefix} {loc} id 使用了 UUID，应改为 currentField 完整 fieldKey（设计器会显示 undefined）")
            else:
                report.warning(f"{prefix} {loc} id 应等于 currentField（设计器回显）")


def _validate_filters(report: ValidationReport, prefix: str, filters: Dict):
    for filter_name in ("leftFilterField", "topFilterField"):
        items = filters.get(filter_name)
        if not items:
            continue
        if not isinstance(items, list):
            report.error(f"{prefix} {filter_name} 应为数组")
            continue
        for j, f in enumerate(items):
            if isinstance(f, dict):
                _validate_filter_item(report, prefix, filter_name, j, f, require_parent=True)

    custom = filters.get("customFilterField")
    if custom:
        if not isinstance(custom, list):
            report.error(f"{prefix} customFilterField 应为数组")
        else:
            for j, f in enumerate(custom):
                if isinstance(f, dict):
                    _validate_filter_item(report, prefix, "customFilterField", j, f, require_parent=False)

    sub = filters.get("subordination")
    if sub and sub not in (["", ""], ["", ""]):
        if not isinstance(sub, list) or len(sub) != 2:
            report.error(f"{prefix} subordination 应为长度为 2 的数组")
        else:
            _check_field_key_ref(report, prefix, "subordination[0]", sub[0] if sub[0] else None)
            _check_field_key_ref(report, prefix, "subordination[1]", sub[1] if sub[1] else None)
            lf = filters.get("leftFilterField")
            if lf and isinstance(lf, list) and len(lf) > 0 and isinstance(lf[0], dict):
                item = lf[0]
                if sub[0] and item.get("parentField") and sub[0] != item["parentField"]:
                    report.warning(f"{prefix} subordination[0] 与 leftFilterField[0].parentField 不一致")
                if sub[1] and item.get("currentField") and sub[1] != item["currentField"]:
                    report.warning(f"{prefix} subordination[1] 与 leftFilterField[0].currentField 不一致")


def _effective_cell_type(field: Dict) -> str:
    """顶层 cellType 或 style.cellType.cellType"""
    ct = field.get("cellType")
    if ct:
        return ct
    nested = _cell_type(field)
    return nested.get("cellType", "") if nested else ""


def _effective_formula_text(field: Dict) -> str:
    """公式文本：顶层 cellText / formula 或 style.cellType.cellText"""
    for key in ("cellText", "formula"):
        val = field.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = _cell_type(field)
    if nested:
        ct = nested.get("cellText")
        if isinstance(ct, str) and ct.strip():
            return ct.strip()
    return ""


def validate_formula_fields(fields: List[Dict], report: ValidationReport):
    """验证 Formula 单元格格式（对齐 formula-cell-api-guide.md）"""
    for i, field in enumerate(fields):
        if _effective_cell_type(field) != "Formula":
            continue
        prefix = f"公式字段 #{i} ({_effective_formula_text(field) or '未命名'})"
        text = _effective_formula_text(field)
        if not text:
            report.error(f"{prefix} 缺少公式内容（cellText / formula）")
            continue
        if text.startswith("="):
            report.error(
                f"{prefix} cellText/formula 不应以 '=' 开头（API 存储格式），"
                f"应去掉前导 '='，见 formula-cell-api-guide.md"
            )

        ct = _cell_type(field)
        count_type = field.get("countType") or (ct.get("countType") if ct else None)
        display_type = field.get("displayType") or (ct.get("displayType") if ct else None)
        group_type = field.get("groupType") if "groupType" in field else (ct.get("groupType") if ct else None)

        if count_type and count_type != "count":
            report.error(f"{prefix} countType 应为 'count'，当前: {count_type}")
        if display_type and display_type != "Group":
            report.error(f"{prefix} displayType 应为 'Group'，当前: {display_type}")
        if group_type == "none":
            report.warning(f"{prefix} groupType 应为 null 而非 'none'")

        style = field.get("style") if isinstance(field.get("style"), dict) else {}
        fmt = style.get("formatter")
        if fmt and fmt not in ("", "General"):
            report.warning(f"{prefix} style.formatter 建议留空（手动保存对齐），当前: {fmt!r}")

        top_formula = field.get("formula")
        nested_text = ct.get("cellText") if ct else None
        if top_formula and nested_text and top_formula.lstrip("=") != nested_text.lstrip("="):
            report.warning(f"{prefix} 顶层 formula 与 style.cellType.cellText 不一致")


def load_config(file_path: str) -> Dict:
    """加载 JSON 配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}")
        sys.exit(1)


def validate_basic_structure(config: Dict, report: ValidationReport):
    """验证基本结构"""
    if not isinstance(config, dict):
        report.error("配置根节点必须是对象")
        return

    if "name" not in config or not config["name"]:
        report.error("缺少报表名称 (name)")

    if "config" not in config:
        report.error("缺少 config 配置节点")
        return

    cfg = config["config"]

    if "ds" not in cfg or not cfg["ds"]:
        report.error("缺少数据集配置 (config.ds)，至少需要一个数据集")

    if "fields" not in cfg or not cfg["fields"]:
        report.error("缺少字段配置 (config.fields)，至少需要一个字段")


def validate_datasets(config: Dict, report: ValidationReport):
    """验证数据集配置"""
    ds_list = config.get("config", {}).get("ds", [])

    ds_ids = set()
    for i, ds in enumerate(ds_list):
        if "id" not in ds:
            report.error(f"数据集 #{i} 缺少 id 字段")
            continue

        if ds["id"] in ds_ids:
            report.error(f"数据集 id 重复: {ds['id']}")
        ds_ids.add(ds["id"])

        if "name" not in ds or not ds["name"]:
            report.warning(f"数据集 {ds.get('id', f'#{i}')} 缺少 name 字段")

        if "fields" not in ds:
            report.warning(f"数据集 {ds.get('id', f'#{i}')} 缺少 fields 列表")
        else:
            field_ids = set()
            for f in ds["fields"]:
                fid = f.get("id", "")
                if not fid:
                    report.warning(f"数据集 {ds.get('id', f'#{i}')} 中有字段缺少 id")
                elif fid in field_ids:
                    report.warning(f"数据集 {ds.get('id', f'#{i}')} 中字段 id 重复: {fid}")
                field_ids.add(fid)

    return ds_ids


def validate_fields(config: Dict, report: ValidationReport, ds_ids: set):
    """验证字段配置"""
    fields = config.get("config", {}).get("fields", [])

    field_positions = {}  # (x, y) -> field_index

    for i, field in enumerate(fields):
        prefix = f"字段 #{i} ({field.get('cellText', '未命名')})"

        # 必填字段检查
        required = [
            "cellType", "displayType", "expandType", "dataSet", "field",
            "leftParent", "topParent", "groupType", "countType",
            "orderType", "cellText", "x", "y", "rowCount", "colCount"
        ]

        for req in required:
            if req not in field:
                report.error(f"{prefix} 缺少必填字段: {req}")

        # 枚举值检查
        if "cellType" in field and field["cellType"] not in CELL_TYPES:
            report.error(f"{prefix} cellType 值无效: {field['cellType']}，有效值: {CELL_TYPES}")

        # Field 精确绑定：禁止裸雪花 ID（缺 field_ 前缀会导致取数匹配失败）
        eff_ct = _effective_cell_type(field)
        if eff_ct == "Field":
            fname = str(field.get("name") or field.get("field") or "")
            fkey = str(field.get("fieldKey") or "")
            last = fkey.split(".")[-1] if fkey else ""
            if re.match(r"^\d{15,}$", fname):
                report.error(
                    f"{prefix} name 为裸雪花 ID '{fname}'，必须使用 fieldsKey.name"
                    f"（通常为 field_{fname}）；见 field-bind-exact-match-guide.md"
                )
            if last and re.match(r"^\d{15,}$", last):
                report.error(
                    f"{prefix} fieldKey 末段为裸雪花 ID '{last}'，应为 fieldsKey.name"
                    f"（通常为 field_{last}）"
                )
            if fkey and fname and last and last != fname:
                report.warning(f"{prefix} fieldKey 末段 '{last}' 与 name '{fname}' 不一致")
            if fname and fname.count(".") == 0 and not fname.startswith("field_") and not re.match(
                r"^(create_time|update_time|name|creator|updater|id|data_status)$", fname
            ):
                # 非系统字段且无 field_ 前缀：提醒核对 fieldsKey
                if re.search(r"\d{10,}", fname):
                    report.warning(
                        f"{prefix} name='{fname}' 疑似非 fieldsKey.name，请与 fieldsAndOriginFields 核对"
                    )

        if "displayType" in field and field["displayType"] not in DISPLAY_TYPES:
            report.error(f"{prefix} displayType 值无效: {field['displayType']}，有效值: {DISPLAY_TYPES}")

        if "expandType" in field and field["expandType"] not in EXPAND_TYPES:
            report.error(f"{prefix} expandType 值无效: {field['expandType']}，有效值: {EXPAND_TYPES}")

        if "groupType" in field and field["groupType"] not in GROUP_TYPES:
            report.error(f"{prefix} groupType 值无效: {field['groupType']}，有效值: {GROUP_TYPES}")

        if "countType" in field and field["countType"] not in COUNT_TYPES:
            report.error(f"{prefix} countType 值无效: {field['countType']}，有效值: {COUNT_TYPES}")

        if "orderType" in field and field["orderType"] not in ORDER_TYPES:
            report.error(f"{prefix} orderType 值无效: {field['orderType']}，有效值: {ORDER_TYPES}")

        # 坐标检查
        for coord in ["x", "y"]:
            if coord in field:
                if not isinstance(field[coord], int) or field[coord] < 0:
                    report.error(f"{prefix} {coord} 坐标无效: {field[coord]}，必须为非负整数")

        for size in ["rowCount", "colCount"]:
            if size in field:
                if not isinstance(field[size], int) or field[size] < 1:
                    report.error(f"{prefix} {size} 值无效: {field[size]}，必须为 >= 1 的整数")

        # 数据集引用检查
        if "dataSet" in field and ds_ids and field["dataSet"] not in ds_ids:
            report.error(f"{prefix} 引用的数据集不存在: {field['dataSet']}，可用: {ds_ids}")

        # 父格检查
        for parent_name in ["leftParent", "topParent"]:
            if parent_name in field:
                parent = field[parent_name]
                if not isinstance(parent, list) or len(parent) != 3:
                    report.error(f"{prefix} {parent_name} 格式无效，应为 [type, x, y] 三元组")
                else:
                    ptype, px, py = parent
                    if ptype not in PARENT_TYPES:
                        report.error(f"{prefix} {parent_name} 类型无效: {ptype}，有效值: {PARENT_TYPES}")
                    if ptype == "custom":
                        if not isinstance(px, int) or px < 0:
                            report.error(f"{prefix} {parent_name} x 坐标无效: {px}")
                        if not isinstance(py, int) or py < 0:
                            report.error(f"{prefix} {parent_name} y 坐标无效: {py}")

        # 显示方式与字段类型一致性
        if "displayType" in field and "countType" in field:
            if field["displayType"] == "Count" and field["countType"] == "none":
                report.warning(f"{prefix} displayType=Count 但 countType=none，指标字段应指定聚合方式")
            if field["displayType"] != "Count" and field["countType"] != "none":
                report.warning(f"{prefix} displayType={field['displayType']} 但 countType={field['countType']}，非汇总字段不应指定聚合方式")

        if "displayType" in field and "groupType" in field:
            if field["displayType"] == "Group" and field["groupType"] == "none":
                # 日期字段分组时应该有 groupType，但普通分组字段 groupType=none 是正常的
                pass
            if field["displayType"] != "Group" and field["groupType"] != "none":
                report.warning(f"{prefix} displayType={field['displayType']} 但 groupType={field['groupType']}，非分组字段不应指定时间分组")

        # 记录位置
        if "x" in field and "y" in field:
            pos = (field["x"], field["y"])
            if pos in field_positions:
                report.warning(f"{prefix} 与字段 #{field_positions[pos]} 位置重叠: ({field['x']}, {field['y']})")
            field_positions[pos] = i

        # 样式检查
        if "style" in field and field["style"]:
            style = field["style"]
            if "hAlign" in style and style["hAlign"] not in H_ALIGN_VALUES:
                report.error(f"{prefix} style.hAlign 值无效: {style['hAlign']}，有效值: 0(左), 1(中), 2(右)")
            if "vAlign" in style and style["vAlign"] not in V_ALIGN_VALUES:
                report.error(f"{prefix} style.vAlign 值无效: {style['vAlign']}，有效值: 0(上), 1(中), 2(下)")

        # 过滤检查（支持 fields 顶层与 style.cellType）
        filter_src = _merged_filter_source(field)
        if filter_src:
            _validate_filters(report, prefix, filter_src)

    # 检测循环引用
    check_circular_refs(fields, report)


def check_circular_refs(fields: List[Dict], report: ValidationReport):
    """检测父格循环引用"""
    # 构建 依赖图: field_index -> [parent_field_indices]
    pos_map = {}
    for i, f in enumerate(fields):
        if "x" in f and "y" in f:
            pos_map[(f["x"], f["y"])] = i

    deps = {}  # field_index -> set of parent_indices
    for i, f in enumerate(fields):
        parents = set()
        for pname in ["leftParent", "topParent"]:
            p = f.get(pname, [])
            if isinstance(p, list) and len(p) == 3 and p[0] == "custom":
                target_pos = (p[1], p[2])
                if target_pos in pos_map:
                    parents.add(pos_map[target_pos])
        deps[i] = parents

    # DFS 检测环
    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in deps.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    for node in deps:
        if node not in visited:
            if dfs(node):
                field_info = fields[node].get("cellText", f"#{node}")
                report.error(f"检测到父格循环引用，涉及字段: {field_info}")
                return


def validate_sheet_props(config: Dict, report: ValidationReport):
    """验证工作表属性"""
    sheet_props = config.get("config", {}).get("sheetProps", {})
    if not sheet_props:
        return

    # 检查行高
    row_heights = sheet_props.get("rowHeights", {})
    for k, v in row_heights.items():
        if not isinstance(v, (int, float)) or v <= 0:
            report.warning(f"行高值无效: 行 {k} = {v}，应为正数")

    # 检查列宽
    col_widths = sheet_props.get("colWidths", {})
    for k, v in col_widths.items():
        if not isinstance(v, (int, float)) or v <= 0:
            report.warning(f"列宽值无效: 列 {k} = {v}，应为正数")

    # 检查主题
    style_config = sheet_props.get("styleConfig", {})
    if style_config:
        theme = style_config.get("theme")
        if theme is not None and theme not in THEME_RANGE:
            report.warning(f"主题编号无效: {theme}，有效范围: 1-10")

        # 检查颜色格式
        for color_field in ["titleBg", "alternateBg1", "alternateBg2"]:
            color = style_config.get(color_field)
            if color and not (color.startswith("#") or color.startswith("rgb")):
                report.warning(f"颜色值格式可能无效: {color_field} = {color}，建议使用 #RRGGBB 格式")


def validate_report_type(fields: List[Dict], report: ValidationReport):
    """验证报表类型与字段配置一致性"""
    group_count = sum(1 for f in fields if f.get("displayType") == "Group")
    count_fields = [f for f in fields if f.get("displayType") == "Count"]
    list_fields = [f for f in fields if f.get("displayType") == "List"]

    if group_count == 0 and not count_fields:
        report.info_msg(f"报表类型: 简单列表（{len(list_fields)} 个列表字段）")

    elif group_count < 2 or not count_fields:
        report.info_msg(f"报表类型: 分组表（{group_count} 个分组字段, {len(count_fields)} 个指标字段）")

    else:
        # 交叉表检查
        h_expand_group = [f for f in fields if f.get("displayType") == "Group" and f.get("expandType") == "Horizontal"]
        v_expand_group = [f for f in fields if f.get("displayType") == "Group" and f.get("expandType") == "Vertical"]

        if not h_expand_group:
            report.warning("交叉表应有至少一个横向扩展的分组字段（列维度）")
        if not v_expand_group:
            report.warning("交叉表应有至少一个纵向扩展的分组字段（行维度）")

        # 检查指标字段是否有自定义父格
        for cf in count_fields:
            left_p = cf.get("leftParent", [])
            top_p = cf.get("topParent", [])
            left_p_type = left_p[0] if isinstance(left_p, list) and len(left_p) > 0 else ""
            top_p_type = top_p[0] if isinstance(top_p, list) and len(top_p) > 0 else ""
            if left_p_type != "custom":
                report.warning(f"指标字段 '{cf.get('cellText', '')}' 左父格应设置为 custom（指向行维度单元格）")
            if top_p_type != "custom":
                report.warning(f"指标字段 '{cf.get('cellText', '')}' 上父格应设置为 custom（指向列维度单元格）")

        report.info_msg(f"报表类型: 交叉表（{group_count} 个分组字段, {len(count_fields)} 个指标字段）")


def main():
    if len(sys.argv) < 2:
        print("用法: python validate_report_config.py <配置文件路径>")
        print("示例: python validate_report_config.py report_config.json")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    print(f"正在验证报表配置: {file_path}\n")

    config = load_config(file_path)
    report = ValidationReport()

    # 1. 基本结构验证
    validate_basic_structure(config, report)

    if not report.has_errors():
        # 2. 数据集验证
        ds_ids = validate_datasets(config, report)

        # 3. 字段验证
        validate_fields(config, report, ds_ids)

        # 3.1 Formula 单元格格式验证
        fields = config.get("config", {}).get("fields", [])
        validate_formula_fields(fields, report)

        # 4. 工作表属性验证
        validate_sheet_props(config, report)

        # 5. 报表类型验证
        fields = config.get("config", {}).get("fields", [])
        validate_report_type(fields, report)

    report.print_report()

    sys.exit(1 if report.has_errors() else 0)


if __name__ == "__main__":
    main()
