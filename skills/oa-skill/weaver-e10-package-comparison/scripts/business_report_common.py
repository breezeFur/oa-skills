#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path


ASSIGNMENT_METHODS = {
    "EXPLICIT_DEPENDENCY",
    "EXPLICIT_BINDING",
    "FEATURE_GROUP",
    "MENU_TARGET",
    "PAGE_DATASET_BINDING",
    "FORM_ACTION_BINDING",
    "WORKFLOW_FORM_BINDING",
    "NAME_CLUSTER_INFERRED",
    "UNMAPPED",
}
EVIDENCE_LEVELS = {
    "CONFIG_OBSERVED",
    "CODE_CONFIRMED",
    "BUSINESS_INFERRED",
    "UNRESOLVED",
    "RUNTIME_VERIFIED",
}
CARD_STATUSES = {"CONFIRMED", "PARTIAL", "UNRESOLVED", "ADAPTER_REQUIRED"}

OBJECT_SECTIONS = (
    ("businessObject", ("businessObjects",)),
    ("serviceFragment", ("serviceFragments",)),
    ("entity", ("dataModel", "entities")),
    ("relation", ("dataModel", "relations")),
    ("dataset", ("dataModel", "datasets")),
    ("form", ("forms",)),
    ("page", ("pages",)),
    ("actionFlow", ("actionFlows",)),
    ("aiApplication", ("aiApplications",)),
    ("multiFillingTask", ("multiFillingTasks",)),
    ("workflow", ("workflows",)),
    ("report", ("reports",)),
    ("applicationShell", ("navigation", "applicationShells")),
    ("navigation", ("navigation", "navigations")),
    ("menuCombination", ("navigation", "combinations")),
    ("menu", ("navigation", "menus")),
    ("permission", ("permissions",)),
    ("integration", ("integrations",)),
    ("externalResource", ("externalResources",)),
    ("dependency", ("dependencies",)),
)

TYPE_LABELS = {
    "businessObject": "业务对象",
    "serviceFragment": "服务结构片段",
    "entity": "数据实体",
    "relation": "数据关系",
    "dataset": "数据集",
    "form": "表单",
    "page": "页面",
    "pageComponent": "页面组件",
    "actionFlow": "动作流",
    "aiApplication": "AI 应用",
    "multiFillingTask": "多级填报任务",
    "workflow": "审批流程",
    "report": "报表",
    "applicationShell": "应用壳",
    "navigation": "导航",
    "menuCombination": "菜单组合",
    "menu": "菜单",
    "permission": "权限对象",
    "integration": "集成对象",
    "externalResource": "外部资源",
    "dependency": "依赖",
}

TECHNICAL_RE = re.compile(
    r"(?:cache|缓存|同步|sync|初始化器|initializer|物理表|内部辅助|内部动作|"
    r"runtime|serverless|dml|mq|esb|adapter|组件适配|定时任务|job|debug)",
    re.I,
)
LONG_ID_RE = re.compile(r"(?<!\d)\d{16,}(?!\d)")
PHYSICAL_SUFFIX_RE = re.compile(r"(?:_[0-9]{8,}|-[0-9]{8,})$")
GENERIC_NAMES = {
    "", "未命名", "默认", "页面", "表单", "动作流", "菜单", "数据集", "对象",
    "配置", "管理", "应用", "系统", "业务", "详情", "列表", "新增", "编辑",
}
OPERATION_RULES = (
    ("初始化与同步", re.compile(r"初始化|预置|模板|导入|复制|同步|刷新|init|sync|import|copy", re.I)),
    ("审批与流程", re.compile(r"审批|审核|流程|提交|退回|驳回|会签|approve|workflow|process", re.I)),
    ("查询与分析", re.compile(r"查询|搜索|列表|看板|统计|分析|报表|图表|监控|详情|query|search|list|dashboard|report|chart", re.I)),
    ("维护与处理", re.compile(r"新增|创建|编辑|修改|更新|删除|维护|设置|配置|分派|调整|create|add|edit|update|delete|maintain|config", re.I)),
    ("协作与通知", re.compile(r"消息|通知|提醒|评论|协作|分享|沟通|message|notify|comment|share|collab", re.I)),
    ("文档与附件", re.compile(r"文档|文件|附件|目录|上传|下载|document|file|attachment|upload|download", re.I)),
    ("权限与组织", re.compile(r"权限|角色|组织|人员|部门|成员|permission|role|organization|user|department", re.I)),
)
STRIP_SUFFIX_RE = re.compile(
    r"(?:PC|H5|移动端|手机端|页面|表单|动作流|流程|审批|菜单|导航|组件|"
    r"数据集|数据源|列表|详情|看板|报表|图表|查询|搜索|新增|创建|编辑|"
    r"修改|更新|删除|维护|设置|配置|管理|处理|功能|中心|台账|记录|信息)+$",
    re.I,
)


def load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_slug(value, fallback="item"):
    text = str(value or "").strip().lower()
    normalized = "".join(ch if ch.isalnum() else "-" for ch in text)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if normalized:
        return normalized[:80]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{fallback}-{digest}"


def safe_file_name(value):
    text = re.sub(r"[\\/:*?\"<>|\r\n]+", "_", str(value or "未命名应用")).strip(" ._")
    return text or "未命名应用"


def safe_display(value, fallback="未命名对象"):
    text = str(value or "").strip()
    text = LONG_ID_RE.sub("[源标识已隐藏]", text)
    text = PHYSICAL_SUFFIX_RE.sub("", text)
    return text or fallback


def get_path(data, path):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key, [])
    return current if isinstance(current, list) else []


def object_name(item, object_type):
    for key in (
        "name", "title", "displayName", "showName", "label", "businessName",
        "featureGroupName", "service", "kind", "type",
    ):
        value = item.get(key)
        if value not in (None, "") and not isinstance(value, (dict, list)):
            return str(value)
    return TYPE_LABELS.get(object_type, object_type)


def collect_objects(ir):
    objects = []
    seen = set()

    def add(item, object_type, source_path, parent_key=None):
        if not isinstance(item, dict):
            return
        key = item.get("logicalKey")
        if not key or key in seen:
            return
        seen.add(key)
        objects.append({
            "logicalKey": key,
            "objectType": object_type,
            "name": object_name(item, object_type),
            "sourcePath": source_path,
            "parentKey": parent_key,
            "sourceRef": item.get("sourceRef", {}),
            "raw": item,
        })

    for object_type, path in OBJECT_SECTIONS:
        for index, item in enumerate(get_path(ir, path)):
            add(item, object_type, ".".join(path) + f"[{index}]")
            if object_type == "page":
                for component_index, component in enumerate(item.get("components", [])):
                    add(
                        component,
                        "pageComponent",
                        ".".join(path) + f"[{index}].components[{component_index}]",
                        item.get("logicalKey"),
                    )
    return objects


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def build_reference_graph(objects):
    by_key = {item["logicalKey"]: item for item in objects}
    known = set(by_key)
    adjacency = defaultdict(dict)

    def link(left, right, method):
        if left == right or left not in known or right not in known:
            return
        current = adjacency[left].get(right)
        priority = {
            "EXPLICIT_DEPENDENCY": 6,
            "MENU_TARGET": 5,
            "WORKFLOW_FORM_BINDING": 4,
            "FORM_ACTION_BINDING": 4,
            "PAGE_DATASET_BINDING": 4,
            "EXPLICIT_BINDING": 3,
        }
        if current is None or priority.get(method, 0) > priority.get(current, 0):
            adjacency[left][right] = method
            adjacency[right][left] = method

    for item in objects:
        key, raw = item["logicalKey"], item["raw"]
        if item.get("parentKey"):
            link(key, item["parentKey"], "EXPLICIT_BINDING")
        if item["objectType"] == "dependency":
            link(raw.get("from"), raw.get("to"), "EXPLICIT_DEPENDENCY")
            link(key, raw.get("from"), "EXPLICIT_DEPENDENCY")
            link(key, raw.get("to"), "EXPLICIT_DEPENDENCY")
        elif item["objectType"] == "relation":
            link(raw.get("from"), raw.get("to"), "EXPLICIT_BINDING")
            link(key, raw.get("from"), "EXPLICIT_BINDING")
            link(key, raw.get("to"), "EXPLICIT_BINDING")
        # A set is required for de-duplication, but its process-randomized
        # iteration order must not decide which equally short business path is
        # selected.  Keep graph insertion deterministic across processes and
        # across sequential/parallel reconstruction.
        for value in sorted(set(iter_strings(raw)) & known):
            method = "EXPLICIT_BINDING"
            if item["objectType"] == "menu":
                method = "MENU_TARGET"
            elif item["objectType"] == "page" and value.startswith("dataset:"):
                method = "PAGE_DATASET_BINDING"
            elif item["objectType"] == "form" and value.startswith("flow:"):
                method = "FORM_ACTION_BINDING"
            elif item["objectType"] == "workflow" and value.startswith("form:"):
                method = "WORKFLOW_FORM_BINDING"
            link(key, value, method)
    return adjacency


def application_prefixes(application_name):
    text = safe_display(application_name, "")
    values = {text}
    stripped = re.sub(r"(?:应用|系统|平台|管理|中心)+$", "", text)
    if len(stripped) >= 2:
        values.add(stripped)
    return sorted((x for x in values if len(x) >= 2), key=len, reverse=True)


def concept_from_name(name, application_name=""):
    text = safe_display(name, "")
    text = re.sub(r"[（(【\[].*?[）)】\]]", "", text)
    text = re.sub(r"\b(?:PC|H5|WEB|MOBILE)\b", "", text, flags=re.I)
    text = re.sub(r"^[~`'\"“”‘’\s]*(?:上|下|前|后|中)[~`'\"“”‘’\s_-]+", "", text)
    text = re.sub(r"[~`'\"“”‘’]+", "", text)
    text = re.sub(r"[/\\|_:：·]+", " ", text).strip(" -_")
    if not text or text.lower() in GENERIC_NAMES:
        return None
    prefixes = application_prefixes(application_name)
    if text in prefixes:
        return None
    for prefix in prefixes:
        if text.startswith(prefix) and len(text) - len(prefix) >= 2:
            text = text[len(prefix):].lstrip(" -_")
            break
    text = re.split(
        r"(?:新增|创建|编辑|修改|更新|删除|维护|设置|配置|查询|搜索|获取|带出|"
        r"联动|校验|标记|切换|生成|复制|迁移|导入|同步|刷新|统计|分析|审批|"
        r"通过后|保存后|变更后|完成后|后执行|触发|回写|推送|通知|提醒|"
        r"create|edit|update|delete|query|sync|import)",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    text = re.split(r"\s+-\s+|--+", text, maxsplit=1)[0]
    text = STRIP_SUFFIX_RE.sub("", text).strip(" -_")
    if " " in text:
        parts = [part for part in text.split() if part and part not in GENERIC_NAMES]
        text = parts[0] if parts else ""
    text = re.sub(r"^(?:我的|全部|待办|已办|新建|新增|编辑|查看)", "", text)
    text = re.sub(r"(?:相关|信息|数据|对象|单据)$", "", text)
    text = text[:24].strip()
    if len(text) < 2 or text.lower() in GENERIC_NAMES or LONG_ID_RE.search(text):
        return None
    return text


def operation_from_name(name, object_type):
    text = str(name or "")
    for operation, pattern in OPERATION_RULES:
        if pattern.search(text):
            return operation
    if object_type in {"integration", "actionFlow"} and TECHNICAL_RE.search(text):
        return "内部自动化"
    return "业务处理"


def domain_for_object(item, application_name=""):
    name = item["name"]
    if item["objectType"] == "page" and re.search(r"嵌入式表单列表视图|通用嵌入视图|未命名嵌入视图", name):
        return None, None, None
    if item["objectType"] == "serviceFragment" or TECHNICAL_RE.search(name):
        return "系统支撑能力", "FEATURE_GROUP", "CONFIG_OBSERVED"
    if item["objectType"] == "integration":
        return "外部协作与系统集成", "EXPLICIT_BINDING", "CONFIG_OBSERVED"
    concept = concept_from_name(name, application_name)
    if not concept:
        return None, None, None
    if item["objectType"] == "businessObject":
        return concept, "FEATURE_GROUP", "CONFIG_OBSERVED"
    if item["objectType"] == "menu" and any(item["raw"].get(key) for key in ("target", "targetRef", "pageRef", "formRef")):
        return concept, "MENU_TARGET", "CONFIG_OBSERVED"
    return concept, "NAME_CLUSTER_INFERRED", "BUSINESS_INFERRED"


def summarize_counts(objects):
    return dict(sorted(Counter(item["objectType"] for item in objects).items()))


def dependency_counts(ir):
    counter = Counter(item.get("status", "unknown") for item in ir.get("dependencies", []))
    return {
        "resolved": counter.get("resolved", 0),
        "external": counter.get("external", 0),
        "unresolved": counter.get("unresolved", 0),
        "unsupported": counter.get("unsupported", 0),
        "total": sum(counter.values()),
    }


def import_requirement_counts(ir, import_requirements=None):
    requirements = import_requirements or ir.get("importRequirements", {})
    return {
        "requiredInputs": len(requirements.get("requiredInputs", [])),
        "optionalInputs": len(requirements.get("optionalInputs", [])),
        "optionalMappings": len(requirements.get("optionalMappings", [])),
        "unresolvedRequiredInputs": sum(
            item.get("status") == "USER_INPUT_REQUIRED"
            for item in requirements.get("requiredInputs", [])
        ),
    }


def shortest_path(adjacency, start, goals, max_depth=10):
    goals = set(goals)
    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node in goals and node != start:
            return path
        if len(path) > max_depth:
            continue
        for neighbor in sorted(adjacency.get(node, {})):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return []


def evidence_level(item):
    level = item.get("sourceRef", {}).get("level")
    return level if level in EVIDENCE_LEVELS else "CONFIG_OBSERVED"


def public_object(item):
    return {
        "logicalKey": item["logicalKey"],
        "objectType": item["objectType"],
        "name": item["name"],
        "sourcePath": item["sourcePath"],
        "sourceRef": item.get("sourceRef", {}),
    }
