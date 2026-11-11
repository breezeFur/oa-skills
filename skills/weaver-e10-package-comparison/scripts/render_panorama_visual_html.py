#!/usr/bin/env python3
"""把 V12 业务全景对比 JSON 渲染为客户可直接打开的离线可视化报告。"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path


SUMMARY_LABELS = [
    "业务域", "功能卡片", "端到端链路", "页面", "表单", "动作流",
    "菜单", "审批流程", "权限对象", "业务数据对象", "查询数据集", "集成",
]
DIFF_LABELS = {
    "pages": "页面",
    "forms": "表单",
    "actionFlows": "动作流",
    "menus": "菜单",
    "workflows": "审批流程",
    "permissions": "权限",
    "entities": "业务数据",
    "datasets": "查询数据",
    "integrations": "集成",
    "dependencies": "关联功能",
    "userActions": "用户操作",
    "fields": "字段",
    "components": "组件",
    "entryPoints": "入口",
    "workflowBrowserDataScopes": "审批浏览数据范围",
    "workflowNodePostValidations": "审批节点后校验",
    "workflowSqlDatasources": "工作流 SQL 数据源",
}


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def public_model(result: dict) -> dict:
    domains_by_key = {}
    for domain in result.get("domainChanges", []):
        for key in (domain.get("oldLogicalKey"), domain.get("newLogicalKey")):
            if key:
                domains_by_key[key] = domain.get("newName") or domain.get("oldName") or "未命名业务域"

    features = []
    for index, item in enumerate(result.get("featureChanges", []), 1):
        old_domain = domains_by_key.get(item.get("oldDomain"))
        new_domain = domains_by_key.get(item.get("newDomain"))
        domain_name = new_domain or old_domain or "其他业务能力"
        changes = []
        for key, raw in (item.get("differences") or {}).items():
            if not isinstance(raw, dict):
                continue
            added = [str(x) for x in (raw.get("added") or []) if str(x).strip()]
            removed = [str(x) for x in (raw.get("removed") or []) if str(x).strip()]
            if not added and not removed and raw.get("oldCount") == raw.get("newCount"):
                continue
            changes.append({
                "label": DIFF_LABELS.get(key, "功能配置"),
                "added": added[:30], "removed": removed[:30],
                "oldCount": raw.get("oldCount", len(removed)),
                "newCount": raw.get("newCount", len(added)),
                "beforeAfter": key == "workflowSqlDatasources",
            })
        public_tests = []
        for test in item.get("testPoints", [])[:8]:
            public_tests.append({
                "priority": test.get("priority", "中"),
                "title": test.get("title") or "验证该功能变化后的业务路径",
                "scenario": test.get("scenario") or "按正常、异常和权限边界完成一次业务验证。",
            })
        display_name = item.get("displayName") or item.get("newName") or item.get("oldName") or "未命名功能"
        changed_objects = [
            {
                "type": obj.get("objectTypeLabel") or "业务对象",
                "name": obj.get("newName") or obj.get("oldName") or "未命名业务对象",
            }
            for obj in (item.get("changedObjects") or [])
        ]
        features.append({
            "id": digest({"index": index, "domain": domain_name, "name": display_name, "type": item.get("changeType")}),
            "changeType": item.get("changeType") or "更新",
            "name": display_name,
            "oldName": item.get("oldName"), "newName": item.get("newName"),
            "businessFunctionName": item.get("businessFunctionName") or item.get("newName") or item.get("oldName"),
            "subjectType": item.get("subjectType") or "业务功能",
            "changedObjects": changed_objects,
            "oldDomain": old_domain, "newDomain": new_domain,
            "domain": domain_name,
            "purpose": item.get("purpose") or "围绕该业务功能的配置发生变化。",
            "changes": changes,
            "tests": public_tests,
        })

    chains = []
    chain_changes = result.get("chainChanges") or {}
    for change_type, values in (("新增", chain_changes.get("added", [])), ("删除", chain_changes.get("removed", []))):
        for name in values:
            chains.append({"id": digest({"type": change_type, "name": name}), "changeType": change_type, "name": name, "oldNodes": [], "newNodes": []})
    for item in chain_changes.get("updated", []):
        chains.append({
            "id": digest({"type": "更新", "name": item.get("name")}), "changeType": "更新",
            "name": item.get("name") or "未命名业务链",
            "oldNodes": list(dict.fromkeys(item.get("oldNodes") or []))[:20],
            "newNodes": list(dict.fromkeys(item.get("newNodes") or []))[:20],
        })

    tests = []
    seen = set()
    for test in result.get("testPoints", []):
        public_test = {
            "priority": test.get("priority", "中"),
            "title": test.get("title") or "验证变化功能的业务路径",
            "scenario": test.get("scenario") or "按正常、异常和权限边界完成一次业务验证。",
        }
        key = (public_test["priority"], public_test["title"], public_test["scenario"])
        if key not in seen:
            tests.append(public_test)
            seen.add(key)

    action_roots = (result.get("rootObjectChanges") or {}).get("actionFlows") or {}
    return {
        "applicationName": result.get("applicationName") or "eBuilder 应用",
        "subtitle": "先还原两版应用全景，再按业务功能变化生成可执行验证建议",
        "summary": {
            "old": {key: int((result.get("oldSummary") or {}).get(key, 0) or 0) for key in SUMMARY_LABELS},
            "new": {key: int((result.get("newSummary") or {}).get(key, 0) or 0) for key in SUMMARY_LABELS},
        },
        "changeSummary": {key: int((result.get("changeSummary") or {}).get(key, 0) or 0) for key in ("新增", "删除", "归属调整", "更新")},
        "actionFlowChanges": {
            "oldCount": int(action_roots.get("oldCount", 0) or 0),
            "newCount": int(action_roots.get("newCount", 0) or 0),
            "added": [str(x) for x in action_roots.get("added", []) if str(x).strip()],
            "removed": [str(x) for x in action_roots.get("removed", []) if str(x).strip()],
            "renamed": [
                {"before": str(x.get("before") or ""), "after": str(x.get("after") or "")}
                for x in action_roots.get("renamed", []) if isinstance(x, dict)
            ],
        },
        "domains": [{
            "changeType": item.get("changeType") or "更新",
            "name": item.get("newName") or item.get("oldName") or "未命名业务域",
            "oldName": item.get("oldName"), "newName": item.get("newName"),
            "oldFunctionCount": len(item.get("oldFunctions") or []),
            "newFunctionCount": len(item.get("newFunctions") or []),
        } for item in result.get("domainChanges", [])],
        "features": features,
        "chains": chains,
        "tests": tests,
        "limitations": [str(x) for x in result.get("limitations", []) if str(x).strip()],
    }


def build_html(model: dict) -> str:
    data = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(f"{model['applicationName']}应用版本功能可视化报告")
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; --ink:#172033; --muted:#667085; --line:#dfe5ef; --surface:#fff; --canvas:#f4f7fb; --blue:#2759d7; --blue-soft:#edf3ff; --green:#168a5a; --green-soft:#e9f8f0; --red:#c63b43; --red-soft:#fff0f0; --orange:#ad6b00; --orange-soft:#fff7e8; --purple:#7657bb; --purple-soft:#f2edff; --shadow:0 10px 28px rgba(33,54,94,.08); }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.55; }}
button,input,select {{ font:inherit; }}
button {{ cursor:pointer; }}
.ebv-shell {{ max-width:1440px; margin:0 auto; padding:28px 32px 56px; }}
.ebv-hero {{ background:linear-gradient(135deg,#173b96,#2c67dd); color:#fff; border-radius:24px; padding:30px 34px; box-shadow:var(--shadow); }}
.ebv-hero h1 {{ margin:0 0 8px; font-size:clamp(25px,3vw,38px); letter-spacing:.01em; }}
.ebv-hero p {{ margin:0; opacity:.9; font-size:15px; }}
.ebv-direction {{ display:inline-flex; margin-top:18px; padding:6px 12px; border:1px solid rgba(255,255,255,.45); border-radius:99px; font-size:13px; }}
.ebv-tabs {{ display:flex; gap:8px; margin:22px 0 16px; flex-wrap:wrap; }}
.ebv-tab {{ border:1px solid var(--line); background:var(--surface); color:var(--muted); padding:10px 16px; border-radius:10px; font-weight:650; }}
.ebv-tab[aria-selected="true"] {{ background:var(--blue-soft); border-color:#9db7ff; color:var(--blue); }}
.ebv-panel[hidden] {{ display:none; }}
.ebv-kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:18px; }}
.ebv-kpi,.ebv-card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow); }}
.ebv-kpi {{ padding:18px 20px; }}
.ebv-kpi-label {{ color:var(--muted); font-size:13px; }}
.ebv-kpi-value {{ font-size:30px; font-weight:750; margin-top:4px; }}
.ebv-kpi-note {{ color:var(--muted); font-size:12px; margin-top:2px; }}
.ebv-grid {{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(300px,.9fr); gap:18px; }}
.ebv-card {{ padding:22px; }}
.ebv-card h2 {{ margin:0 0 14px; font-size:19px; }}
.ebv-card h3 {{ margin:18px 0 8px; font-size:15px; }}
.ebv-chart {{ width:100%; min-height:310px; }}
.ebv-chart svg {{ display:block; width:100%; height:auto; }}
.ebv-legend {{ display:flex; flex-wrap:wrap; gap:12px; color:var(--muted); font-size:12px; margin-top:8px; }}
.ebv-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; vertical-align:middle; }}
.ebv-change-strip {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
.ebv-change {{ padding:14px; border-radius:12px; border:1px solid var(--line); }}
.ebv-change strong {{ display:block; font-size:25px; }}
.ebv-change span {{ color:var(--muted); font-size:13px; }}
.ebv-change.add {{ background:var(--green-soft); color:var(--green); }} .ebv-change.del {{ background:var(--red-soft); color:var(--red); }} .ebv-change.move {{ background:var(--purple-soft); color:var(--purple); }} .ebv-change.update {{ background:var(--orange-soft); color:var(--orange); }}
.ebv-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.ebv-table th,.ebv-table td {{ padding:10px 8px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }}
.ebv-table th {{ color:var(--muted); font-weight:650; }}
.ebv-toolbar {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }}
.ebv-toolbar input,.ebv-toolbar select {{ min-height:42px; border:1px solid #cbd5e5; border-radius:10px; background:#fff; color:var(--ink); padding:8px 12px; }}
.ebv-toolbar input {{ flex:1 1 300px; }} .ebv-toolbar select {{ flex:0 1 180px; }}
.ebv-reset {{ border:0; border-radius:10px; background:var(--blue); color:#fff; padding:8px 16px; font-weight:650; }}
.ebv-result-count {{ color:var(--muted); font-size:13px; margin:5px 0 14px; }}
.ebv-feature-layout {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(320px,.8fr); gap:18px; align-items:start; }}
.ebv-feature-list {{ display:grid; gap:10px; }}
.ebv-feature {{ width:100%; text-align:left; border:1px solid var(--line); background:var(--surface); border-radius:14px; padding:15px 16px; color:var(--ink); }}
.ebv-feature:hover,.ebv-feature[aria-current="true"] {{ border-color:#8da9ff; box-shadow:0 6px 20px rgba(39,89,215,.12); }}
.ebv-feature-top {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px; }}
.ebv-feature-name {{ font-weight:730; font-size:15px; }} .ebv-feature-domain {{ color:var(--muted); font-size:12px; }}
.ebv-badge {{ display:inline-flex; align-items:center; border-radius:99px; padding:2px 8px; font-size:12px; font-weight:700; }}
.ebv-badge.add {{ color:var(--green); background:var(--green-soft); }} .ebv-badge.del {{ color:var(--red); background:var(--red-soft); }} .ebv-badge.move {{ color:var(--purple); background:var(--purple-soft); }} .ebv-badge.update {{ color:var(--orange); background:var(--orange-soft); }}
.ebv-feature-summary {{ color:var(--muted); font-size:13px; }}
.ebv-detail {{ position:sticky; top:18px; }}
.ebv-detail-empty {{ color:var(--muted); padding:28px 4px; }}
.ebv-detail p {{ margin:7px 0; font-size:13px; }} .ebv-detail ul {{ margin:6px 0 12px; padding-left:20px; font-size:13px; }}
.ebv-diff-row {{ border-top:1px solid var(--line); padding:11px 0; }} .ebv-diff-row strong {{ display:block; margin-bottom:4px; }}
.ebv-diff-add {{ color:var(--green); }} .ebv-diff-remove {{ color:var(--red); }}
.ebv-test {{ border-left:3px solid #9db7ff; background:#f8faff; padding:9px 11px; margin:8px 0; font-size:13px; }} .ebv-test b {{ color:var(--blue); }}
.ebv-chain-list {{ display:grid; gap:10px; }} .ebv-chain {{ border:1px solid var(--line); border-radius:12px; padding:13px; }}
.ebv-chain-name {{ font-weight:700; }} .ebv-chain small {{ color:var(--muted); }}
.ebv-note {{ margin-top:18px; color:var(--muted); font-size:12px; }}
@media (max-width:900px) {{ .ebv-shell {{ padding:18px 16px 40px; }} .ebv-kpis {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .ebv-grid,.ebv-feature-layout {{ grid-template-columns:1fr; }} .ebv-detail {{ position:static; }} }}
@media (max-width:520px) {{ .ebv-hero {{ padding:24px 20px; border-radius:18px; }} .ebv-kpis,.ebv-change-strip {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .ebv-card {{ padding:16px; }} .ebv-table {{ font-size:12px; }} }}
@media print {{ .ebv-shell {{ max-width:none; padding:0; }} .ebv-hero {{ box-shadow:none; }} .ebv-toolbar,.ebv-tabs,.ebv-reset {{ display:none; }} .ebv-card,.ebv-kpi {{ box-shadow:none; }} .ebv-detail {{ position:static; }} }}
</style>
</head>
<body>
<main class="ebv-shell" id="ebv-app">
<header class="ebv-hero"><h1>{title}</h1><p>{html.escape(model['subtitle'])}</p><span class="ebv-direction">旧版 → 新版 · 离线包保存态功能对比</span></header>
<nav class="ebv-tabs" role="tablist" aria-label="报告区域">
  <button class="ebv-tab" role="tab" aria-selected="true" aria-controls="overview-panel" data-tab="overview-panel">变化总览</button>
  <button class="ebv-tab" role="tab" aria-selected="false" aria-controls="features-panel" data-tab="features-panel">功能变化</button>
  <button class="ebv-tab" role="tab" aria-selected="false" aria-controls="tests-panel" data-tab="tests-panel">验证清单</button>
</nav>
<section class="ebv-panel" id="overview-panel" role="tabpanel">
  <div class="ebv-kpis" id="ebv-kpis"></div>
  <div class="ebv-grid">
    <section class="ebv-card"><h2>旧版与新版规模对比</h2><div class="ebv-chart" id="ebv-chart"></div><div class="ebv-legend"><span><i class="ebv-dot" style="background:#9db7ff"></i>旧版</span><span><i class="ebv-dot" style="background:#2759d7"></i>新版</span></div></section>
    <section class="ebv-card"><h2>功能变化汇总</h2><div class="ebv-change-strip" id="ebv-changes"></div><h3>业务域变化</h3><div class="ebv-table-responsive"><table class="ebv-table"><thead><tr><th>业务域</th><th>变化</th><th>功能数</th></tr></thead><tbody id="ebv-domain-table"></tbody></table></div></section>
  </div>
  <section class="ebv-card" style="margin-top:18px"><h2>动作流对象变化</h2><div id="ebv-action-root-changes"></div></section>
  <p class="ebv-note">本页面只展示可读的业务功能、业务链路和验证建议；不代表目标环境已迁入、启用或运行通过。</p>
</section>
<section class="ebv-panel" id="features-panel" role="tabpanel" hidden>
  <div class="ebv-card"><h2>功能变化明细</h2><div class="ebv-toolbar"><input id="ebv-search" type="search" placeholder="搜索业务域、功能名称或变化内容" aria-label="搜索业务功能"><select id="ebv-domain-filter" aria-label="按业务域筛选"><option value="">全部业务域</option></select><select id="ebv-change-filter" aria-label="按变化类型筛选"><option value="">全部变化类型</option><option>新增</option><option>删除</option><option>归属调整</option><option>更新</option></select><button class="ebv-reset" id="ebv-reset" type="button">恢复全局视图</button></div><div class="ebv-result-count" id="ebv-result-count"></div><div class="ebv-feature-layout"><div class="ebv-feature-list" id="ebv-feature-list"></div><aside class="ebv-card ebv-detail" id="ebv-detail" aria-live="polite"><div class="ebv-detail-empty">请选择左侧功能，查看变化内容和建议验证点。</div></aside></div></div>
</section>
<section class="ebv-panel" id="tests-panel" role="tabpanel" hidden>
  <div class="ebv-card"><h2>重点业务验证清单</h2><p class="ebv-result-count" id="ebv-test-count"></p><div id="ebv-tests"></div><h2 style="margin-top:26px">端到端业务链路变化</h2><div class="ebv-chain-list" id="ebv-chains"></div></div>
</section>
</main>
<script id="report-data" type="application/json">{data}</script>
<script>
(function () {{
  const model = JSON.parse(document.getElementById('report-data').textContent);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
  const cls = (type) => type === '新增' ? 'add' : type === '删除' ? 'del' : type === '归属调整' ? 'move' : 'update';
  const badge = (type) => `<span class="ebv-badge ${{cls(type)}}">${{esc(type)}}</span>`;
  const fmtItems = (items) => items && items.length ? items.map(esc).join('、') : '无';
  const summary = model.summary;
  const kpis = [
    ['功能卡片', summary.old['功能卡片'], summary.new['功能卡片']],
    ['业务域', summary.old['业务域'], summary.new['业务域']],
    ['端到端链路', summary.old['端到端链路'], summary.new['端到端链路']],
    ['重点验证点', model.tests.length, model.tests.length],
  ];
  document.getElementById('ebv-kpis').innerHTML = kpis.map(([label, oldValue, newValue]) => `<div class="ebv-kpi"><div class="ebv-kpi-label">${{esc(label)}}</div><div class="ebv-kpi-value">${{newValue}}</div><div class="ebv-kpi-note">旧版 ${{oldValue}} · 新版 ${{newValue}} · 变化 ${{newValue-oldValue >= 0 ? '+' : ''}}${{newValue-oldValue}}</div></div>`).join('');
  const changes = [['新增','add'],['删除','del'],['归属调整','move'],['更新','update']];
  document.getElementById('ebv-changes').innerHTML = changes.map(([label, style]) => `<div class="ebv-change ${{style}}"><strong>${{model.changeSummary[label] || 0}}</strong><span>${{label}}功能</span></div>`).join('');
  const af = model.actionFlowChanges || {{oldCount:0,newCount:0,added:[],removed:[],renamed:[]}};
  const renamed = af.renamed && af.renamed.length ? af.renamed.map((item) => `${{esc(item.before)}} → ${{esc(item.after)}}`).join('；') : '无';
  document.getElementById('ebv-action-root-changes').innerHTML = `<p><b>数量：</b>旧版 ${{af.oldCount}} 个 → 新版 ${{af.newCount}} 个</p><p><b>新增：</b>${{fmtItems(af.added)}}</p><p><b>删除：</b>${{fmtItems(af.removed)}}</p><p><b>同源名称调整：</b>${{renamed}}</p>`;
  document.getElementById('ebv-domain-table').innerHTML = model.domains.map((domain) => `<tr><td>${{esc(domain.name)}}</td><td>${{badge(domain.changeType)}}</td><td>${{domain.oldFunctionCount}} → ${{domain.newFunctionCount}}</td></tr>`).join('') || '<tr><td colspan="3">未识别到业务域变化</td></tr>';
  const chartLabels = ['业务域','功能卡片','端到端链路','页面','表单','动作流','菜单','审批流程'];
  const maxValue = Math.max(1, ...chartLabels.flatMap((key) => [summary.old[key] || 0, summary.new[key] || 0]));
  const width = 720, row = 34, height = chartLabels.length * row + 34, left = 150, right = 28, plot = width-left-right;
  let svg = `<svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="旧版与新版业务对象数量对比"><line x1="${{left}}" y1="10" x2="${{left}}" y2="${{height-8}}" stroke="#cbd5e5"/>`;
  chartLabels.forEach((key, i) => {{ const y = 22 + i*row; const ov=summary.old[key]||0, nv=summary.new[key]||0; const ow=Math.max(1, ov/maxValue*plot), nw=Math.max(1, nv/maxValue*plot); svg += `<text x="${{left-10}}" y="${{y+10}}" text-anchor="end" fill="#667085" font-size="12">${{esc(key)}}</text><rect x="${{left}}" y="${{y}}" width="${{ow}}" height="9" rx="4" fill="#9db7ff"><title>旧版 ${{ov}}</title></rect><rect x="${{left}}" y="${{y+12}}" width="${{nw}}" height="9" rx="4" fill="#2759d7"><title>新版 ${{nv}}</title></rect><text x="${{Math.min(width-6,left+nw+6)}}" y="${{y+21}}" fill="#2759d7" font-size="11">${{nv}}</text>`; }});
  svg += '</svg>'; document.getElementById('ebv-chart').innerHTML = svg;
  const domainFilter = document.getElementById('ebv-domain-filter');
  [...new Set(model.features.map((x) => x.domain).filter(Boolean))].sort((a,b) => a.localeCompare(b,'zh-CN')).forEach((domain) => {{ const option=document.createElement('option'); option.value=domain; option.textContent=domain; domainFilter.appendChild(option); }});
  const search = document.getElementById('ebv-search'), changeFilter = document.getElementById('ebv-change-filter'), list = document.getElementById('ebv-feature-list'), detail = document.getElementById('ebv-detail'), count = document.getElementById('ebv-result-count');
  let selectedId = null;
  function filtered() {{ const q=(search.value||'').trim().toLowerCase(), domain=domainFilter.value, type=changeFilter.value; return model.features.filter((x) => (!q || [x.name,x.businessFunctionName,x.domain,x.purpose,...x.changedObjects.map((o)=>o.name),...x.changes.flatMap((c)=>[c.label,...c.added,...c.removed])].join(' ').toLowerCase().includes(q)) && (!domain || x.domain===domain) && (!type || x.changeType===type)); }}
  function renderDetail(item) {{ if (!item) {{ detail.innerHTML='<div class="ebv-detail-empty">当前筛选条件下没有功能，请调整筛选后重试。</div>'; return; }} const diff = item.changes.length ? item.changes.map((x)=>`<div class="ebv-diff-row"><strong>${{esc(x.label)}} <small>(${{x.oldCount}} → ${{x.newCount}})</small></strong>${{x.added.length ? `<div class="ebv-diff-add">${{x.beforeAfter ? '新版' : '新增'}}：${{fmtItems(x.added)}}</div>` : ''}}${{x.removed.length ? `<div class="ebv-diff-remove">${{x.beforeAfter ? '前版' : '减少'}}：${{fmtItems(x.removed)}}</div>` : ''}}</div>`).join('') : '<p>配置结构发生调整，请结合业务场景验证。</p>'; const tests=item.tests.length ? item.tests.map((t)=>`<div class="ebv-test"><b>${{esc(t.priority)}} · ${{esc(t.title)}}</b><br>${{esc(t.scenario)}}</div>`).join('') : '<p>建议按主路径、异常路径和权限边界补充验证。</p>'; const ownership=item.businessFunctionName && item.businessFunctionName!==item.name ? `<p class="ebv-feature-domain">对象类型：${{esc(item.subjectType)}} · 所属业务功能：${{esc(item.businessFunctionName)}}</p>` : ''; const objects=item.changedObjects.length ? `<p><b>实际变化对象：</b>${{item.changedObjects.map((o)=>esc(o.name)).join('、')}}</p>` : ''; detail.innerHTML=`<h2>${{esc(item.name)}}</h2><div class="ebv-feature-top">${{badge(item.changeType)}}<span class="ebv-feature-domain">${{esc(item.domain)}}</span></div>${{ownership}}${{objects}}<p>${{esc(item.purpose)}}</p><h3>发生了什么变化</h3>${{diff}}<h3>建议验证</h3>${{tests}}`; }}
  function renderFeatures() {{ const items=filtered(); count.textContent=`筛选后 ${{items.length}} 项功能变化，共 ${{model.features.length}} 项`; list.innerHTML=items.map((x)=>`<button class="ebv-feature" type="button" data-id="${{x.id}}" aria-current="${{x.id===selectedId}}"><div class="ebv-feature-top">${{badge(x.changeType)}}<span class="ebv-feature-name">${{esc(x.name)}}</span></div><div class="ebv-feature-domain">${{esc(x.domain)}}</div><div class="ebv-feature-summary">${{esc(x.purpose)}}</div></button>`).join('') || '<div class="ebv-detail-empty">没有匹配的功能变化。</div>'; const current=items.find((x)=>x.id===selectedId)||items[0]; selectedId=current ? current.id : null; [...list.querySelectorAll('[data-id]')].forEach((button)=>button.addEventListener('click',()=>{{ selectedId=button.dataset.id; renderFeatures(); }})); renderDetail(current); }}
  search.addEventListener('input', renderFeatures); domainFilter.addEventListener('change', renderFeatures); changeFilter.addEventListener('change', renderFeatures); document.getElementById('ebv-reset').addEventListener('click',()=>{{ search.value=''; domainFilter.value=''; changeFilter.value=''; selectedId=null; renderFeatures(); }}); renderFeatures();
  document.getElementById('ebv-test-count').textContent=`共 ${{model.tests.length}} 项重点验证建议，按优先级从高到低排列。`;
  document.getElementById('ebv-tests').innerHTML=model.tests.map((t,i)=>`<div class="ebv-test"><b>${{i+1}}. ${{esc(t.priority)}} · ${{esc(t.title)}}</b><br>${{esc(t.scenario)}}</div>`).join('') || '<p class="ebv-detail-empty">暂无汇总验证点。</p>';
  document.getElementById('ebv-chains').innerHTML=model.chains.map((x)=>`<div class="ebv-chain"><div class="ebv-feature-top">${{badge(x.changeType)}}<span class="ebv-chain-name">${{esc(x.name)}}</span></div>${{x.changeType==='更新' ? `<small>旧版节点：${{esc(x.oldNodes.join(' → ') || '未提供')}}<br>新版节点：${{esc(x.newNodes.join(' → ') || '未提供')}}</small>` : '<small>建议验证该业务链路的入口、主路径、异常处理和权限边界。</small>'}}</div>`).join('') || '<div class="ebv-detail-empty">暂无端到端链路变化。</div>';
  document.querySelectorAll('[data-tab]').forEach((tab)=>tab.addEventListener('click',()=>{{ document.querySelectorAll('[data-tab]').forEach((x)=>x.setAttribute('aria-selected',String(x===tab))); document.querySelectorAll('.ebv-panel').forEach((panel)=>panel.hidden=panel.id!==tab.dataset.tab); }}));
}})();
</script>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison_json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.comparison_json.expanduser().resolve()
    output = args.output.expanduser().resolve()
    model = public_model(json.loads(source.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(model), encoding="utf-8")
    print(json.dumps({"output": str(output), "bytes": output.stat().st_size, "featureCount": len(model["features"]), "testCount": len(model["tests"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
