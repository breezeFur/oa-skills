#!/usr/bin/env python3
"""把 visual-diff-model 渲染为完全离线、可直接打开的单文件 HTML。"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from typing import Any


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>应用版本差异可视化</title>
<style>
:root{--ink:#172033;--muted:#687389;--line:#dbe2ec;--panel:#fff;--bg:#f4f7fb;--brand:#2855d9;--add:#15803d;--remove:#c62828;--update:#c26100;--rename:#7357b6;--unknown:#8a6d1d;--high:#9f1d20;--medium:#c26100;--low:#087f75;--shadow:0 12px 34px rgba(29,43,76,.09)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;overflow-x:hidden}button,select,input{font:inherit}.hero{padding:32px clamp(18px,4vw,56px);color:white;background:linear-gradient(120deg,#162a60,#2855d9 58%,#397fcf)}.hero h1{margin:0 0 8px;font-size:clamp(25px,4vw,40px)}.hero p{margin:4px 0;opacity:.9}.wrap{max-width:1380px;margin:auto;padding:18px 24px}.toolbar{position:sticky;top:0;z-index:10;display:grid;grid-template-columns:repeat(4,minmax(150px,1fr)) minmax(220px,1.35fr) auto;gap:10px;padding:12px;background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}select,input,button{min-height:40px;border:1px solid #cbd5e1;border-radius:9px;background:#fff;padding:7px 10px;color:var(--ink)}button{cursor:pointer}button.primary{background:var(--brand);border-color:var(--brand);color:white}.tabs{display:flex;gap:8px;margin:18px 0;overflow:auto}.tab{white-space:nowrap;border-color:transparent;background:transparent}.tab.active{background:#e7edff;color:#173eaf;border-color:#c6d4ff;font-weight:700}.view{display:none}.view.active{display:block}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:16px;box-shadow:0 4px 18px rgba(29,43,76,.04)}.panel h2,.panel h3{margin-top:0}.panel h2{font-size:21px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}.metric{padding:15px;border:1px solid var(--line);border-radius:12px;background:linear-gradient(180deg,#fff,#f8faff)}.metric strong{display:block;font-size:28px}.muted{color:var(--muted)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:760px}th,td{text-align:left;padding:11px;border-bottom:1px solid #e6ebf2;vertical-align:top}th{position:sticky;top:0;background:#f8fafc;color:#3f4b5f}.badge{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:2px 8px;font-size:12px;font-weight:700;border:1px solid currentColor}.ADDED{color:var(--add)}.REMOVED{color:var(--remove)}.UPDATED{color:var(--update)}.POSSIBLE_RENAME{color:var(--rename)}.UNMATCHED,.UNKNOWN{color:var(--unknown)}.HIGH{color:var(--high)}.MEDIUM{color:var(--medium)}.LOW{color:var(--low)}.split{display:grid;grid-template-columns:minmax(300px,330px) minmax(0,1fr);gap:16px}.item-list{max-height:720px;overflow:auto}.item{display:block;width:100%;text-align:left;margin:0 0 8px;padding:13px;border:1px solid var(--line);border-radius:10px;background:white;line-height:1.5}.item:hover,.item.selected{border-color:#7797ef;background:#f1f5ff}.item b{display:block;margin-bottom:4px}.swimlane{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;padding:8px 0}.lane{position:relative;min-height:150px;padding:15px;border:1px solid var(--line);border-top:5px solid var(--brand);border-radius:12px;background:white;overflow-wrap:anywhere}.lane:not(:last-child):after{content:"→";position:absolute;right:-14px;top:52px;font-size:22px;color:#8090ac}.lane h4{margin:0 0 10px;color:#36506f}.lane.UNKNOWN{border-style:dashed;background:#fffaf0}.detail-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.detail-card{padding:13px;border-radius:10px;background:#f8fafc;border:1px solid var(--line);overflow-wrap:anywhere}.before-after{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}.value{white-space:pre-wrap;word-break:break-word;max-height:190px;overflow:auto;padding:12px;border-radius:9px;background:#f7f8fa;border:1px solid #e1e5eb}.value.before{border-left:4px solid var(--remove)}.value.after{border-left:4px solid var(--add)}.impact-flow{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;padding:12px 0}.impact-step{position:relative;min-width:0;max-width:none;padding:15px;border:1px solid var(--line);border-radius:12px;background:white;overflow-wrap:anywhere}.impact-step:not(:last-child):after{content:"→";position:absolute;right:-13px;top:42%;font-size:22px;color:#8090ac}.empty{padding:42px;text-align:center;color:var(--muted);border:1px dashed #b9c4d5;border-radius:12px;background:#fafcff}.count-note{margin:8px 0;color:var(--muted)}.drawer{position:fixed;z-index:30;right:0;top:0;width:min(560px,94vw);height:100vh;overflow:auto;background:white;box-shadow:-10px 0 35px rgba(20,30,55,.22);padding:24px;transform:translateX(105%);transition:.22s}.drawer.open{transform:none}.drawer-close{float:right}.legend{display:flex;flex-wrap:wrap;gap:10px}.legend .badge:before{content:"●"}.footer{text-align:center;padding:24px;color:var(--muted)}
@media(max-width:1100px){.toolbar{grid-template-columns:1fr 1fr}.split{grid-template-columns:1fr}.detail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.swimlane{grid-template-columns:repeat(3,minmax(0,1fr))}.impact-flow{grid-template-columns:repeat(3,minmax(0,1fr))}.lane:not(:last-child):after,.impact-step:not(:last-child):after{content:none}}
@media(max-width:680px){.wrap{padding:12px}.toolbar{grid-template-columns:1fr}.split{grid-template-columns:1fr}.detail-grid,.swimlane,.impact-flow{grid-template-columns:1fr}.lane:not(:last-child):after,.impact-step:not(:last-child):after{content:"↓";right:auto;left:50%;top:auto;bottom:-25px}.before-after{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="hero"><h1 id="appTitle">应用版本差异可视化</h1><p id="directionText"></p><p id="timeText"></p></header>
<main class="wrap">
<section class="toolbar" aria-label="全局筛选">
  <select id="packageFilter" aria-label="按子应用筛选"><option value="">全部子应用</option></select>
  <select id="typeFilter" aria-label="按对象类型筛选"><option value="">全部对象类型</option></select>
  <select id="changeFilter" aria-label="按变化类型筛选"><option value="">全部变化类型</option></select>
  <select id="riskFilter" aria-label="按风险等级筛选"><option value="">全部风险等级</option></select>
  <input id="searchInput" type="search" placeholder="搜索业务名称、功能或字段" aria-label="按业务名称搜索">
  <button id="resetButton" class="primary">恢复全局视图</button>
</section>
<nav class="tabs" aria-label="可视化视图">
  <button class="tab active" data-view="overview">版本变化总览</button>
  <button class="tab" data-view="chains">业务功能链路差异图</button>
  <button class="tab" data-view="fields">字段级数据勾稽与变化图</button>
  <button class="tab" data-view="impacts">影响范围与验证图</button>
</nav>
<section id="overview" class="view active"></section>
<section id="chains" class="view"></section>
<section id="fields" class="view"></section>
<section id="impacts" class="view"></section>
</main>
<aside id="drawer" class="drawer" aria-label="节点详情"><button class="drawer-close" onclick="closeDrawer()">关闭</button><div id="drawerBody"></div></aside>
<footer class="footer">完全离线 · 仅展示业务功能、变化结论和验证建议 · 待确认表示静态包缺少足够业务归属证据</footer>
<script id="visual-diff-data" type="application/json">__VISUAL_DATA__</script>
<script>
const model=JSON.parse(document.getElementById('visual-diff-data').textContent);
const state={packageUnit:'',objectType:'',changeType:'',riskLevel:'',search:'',selectedChain:null,selectedField:null,selectedImpact:null};
const packageFilter=document.getElementById('packageFilter'),typeFilter=document.getElementById('typeFilter'),changeFilter=document.getElementById('changeFilter'),riskFilter=document.getElementById('riskFilter'),searchInput=document.getElementById('searchInput'),resetButton=document.getElementById('resetButton');
const overview=document.getElementById('overview'),chains=document.getElementById('chains'),fields=document.getElementById('fields'),impacts=document.getElementById('impacts'),drawer=document.getElementById('drawer'),drawerBody=document.getElementById('drawerBody');
const labels={ADDED:'新增',REMOVED:'删除',UPDATED:'更新',POSSIBLE_RENAME:'疑似替代',UNMATCHED:'待确认',UNCHANGED:'未变化',HIGH:'高风险',MEDIUM:'中风险',LOW:'低风险',UNKNOWN:'待确认风险',NONE:'无关联风险',OBSERVED:'已观察',INFERRED:'关系推断',FORM:'表单',PAGE:'页面',EMBEDDED_VIEW:'嵌入式视图',ESB_ACTION_FLOW:'动作流',WORKFLOW:'工作流/审批流程',MENU:'菜单',NAVIGATION:'导航',REPORT:'报表',MULTI_FILLING:'多级填报',DATASET:'独立数据集',EXTERNAL_INTEGRATION:'业务资源绑定',PERMISSION:'权限',APPLICATION_SHELL:'应用基础配置',OTHER:'其他功能'};
const esc=v=>String(v??'未确认').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>esc(clientValue(v));
const badge=(v)=>`<span class="badge ${esc(v)}">${esc(labels[v]||v)}</span>`;
const uniq=a=>[...new Set(a.filter(Boolean))].sort((a,b)=>String(a).localeCompare(String(b),'zh-CN'));
const clientValue=v=>{if(v===null||v===undefined||v==='')return '未设置';if(typeof v==='string'||typeof v==='number'||typeof v==='boolean')return String(v);if(Array.isArray(v))return v.length?`包含 ${v.length} 项业务配置`:'未设置';if(typeof v==='object'){if(v.summary)return '业务配置内容已调整（完整内容不在客户视图展示）';const keys=Object.keys(v);if(keys.some(k=>['name','title','label','value','before','after'].includes(k))){const vals=keys.filter(k=>['name','title','label','value','before','after'].includes(k)).map(k=>String(v[k])).filter(Boolean);if(vals.length)return vals.slice(0,3).join('、');}return '业务配置已调整';}return String(v);};
const clientRiskTitle=r=>{const t=String(r?.title||'');if(t.includes('跨模块')||t.includes('包外'))return '跨模块或包外业务引用需要确认';if(t.includes('关联')||t.includes('映射')||t.includes('替换'))return '跨环境业务关联需要重新核对';return '业务配置关联需要核对';};
const clientText=t=>String(t??'').replace(/weaver-[a-z0-9-]+-service/gi,'相关业务模块').replace(/\b(?:ebdf|ebdd|ebdp|esb|wfp|wfc|bpm|form|ai_app|t_cus_app|edc_[a-z0-9_]+|custom_[a-z0-9_]+|browser_[a-z0-9_]+|fd_[a-z0-9_]+|i18n_[a-z0-9_]+|dw_[a-z0-9_]+|wf_[a-z0-9_]+|wfr_[a-z0-9_]+)_[a-z0-9_]*\b/gi,'业务配置项').replace(/\b(?:CONFIG_FOREIGN_KEY|JSON_REFERENCE)\b/g,'跨环境关联配置').replace(/\bidMap\[[^\]]+\]/g,'迁入映射中的对应关系').replace(/\bCHG-[A-Z0-9]+\b/g,'').replace(/\s{2,}/g,' ').trim();
const nodeMap=new Map(model.nodes.map(n=>[n.nodeId,n]));
const riskMap=new Map(model.risks.map(n=>[n.riskId,n]));
const validationMap=new Map(model.validations.map(n=>[n.validationId,n]));
const chainMap=new Map(model.businessChains.map(n=>[n.chainId,n]));
const fieldMap=new Map(model.fieldLineage.map(n=>[n.fieldId,n]));
function activeNodes(){const q=state.search.trim().toLowerCase();return model.nodes.filter(n=>(!state.packageUnit||n.packageUnit===state.packageUnit)&&(!state.objectType||n.objectType===state.objectType)&&(!state.changeType||n.changeType===state.changeType)&&(!state.riskLevel||n.riskLevel===state.riskLevel)&&(!q||n.searchableText.includes(q)));}
function option(select,values,placeholder){select.innerHTML=`<option value="">${placeholder}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(labels[v]||v)}</option>`).join('');}
function init(){document.getElementById('appTitle').textContent=`${model.application.name} · 应用版本差异可视化`;const old=model.packages.old||{},nw=model.packages.new||{};document.getElementById('directionText').textContent=`旧包：${old.name||'未确认'} → 新包：${nw.name||'未确认'}（${model.directionResolution.directionSource==='PROFILE_EXPORT_TIME'?'按最外层 profile.json.exportTime 自动识别':'按用户指定方向'}）`;document.getElementById('timeText').textContent=`旧包 exportTime：${old.profile?.exportTime||'未确认'} ｜ 新包 exportTime：${nw.profile?.exportTime||'未确认'}`;option(packageFilter,uniq(model.nodes.map(n=>n.packageUnit)),'全部子应用');option(typeFilter,uniq(model.nodes.map(n=>n.objectType)),'全部对象类型');option(changeFilter,['ADDED','REMOVED','UPDATED','POSSIBLE_RENAME','UNMATCHED'],'全部变化类型');option(riskFilter,['HIGH','MEDIUM','LOW','UNKNOWN','NONE'],'全部风险等级');renderAll();}
function renderAll(){renderOverview();renderChains();renderFields();renderImpacts();}
function renderOverview(){const s=model.summary,old=model.packages.old||{},nw=model.packages.new||{};const risk=s.riskLevels||{};const changes=s.changeTypes||{};overview.innerHTML=`<div class="panel"><h2>版本变化规模</h2><div class="cards"><div class="metric"><span>新增业务对象</span><strong class="ADDED">${changes.ADDED||0}</strong></div><div class="metric"><span>删除业务对象</span><strong class="REMOVED">${changes.REMOVED||0}</strong></div><div class="metric"><span>更新业务对象</span><strong class="UPDATED">${changes.UPDATED||0}</strong></div><div class="metric"><span>疑似替代</span><strong class="POSSIBLE_RENAME">${changes.POSSIBLE_RENAME||0}</strong></div><div class="metric"><span>高风险</span><strong class="HIGH">${risk.HIGH||0}</strong></div><div class="metric"><span>待确认风险</span><strong class="UNKNOWN">${risk.UNKNOWN||0}</strong></div><div class="metric"><span>重点验证场景</span><strong>${s.validationScenarios||0}</strong></div></div></div><div class="panel"><h2>业务对象数量</h2><p class="muted">以下数量来自同一份业务功能差异模型；页面不会重新计算或展开底层配置记录。</p><div class="table-wrap"><table><thead><tr><th>功能对象</th><th>旧版</th><th>新版</th><th>新增</th><th>删除</th><th>更新</th><th>净变化</th></tr></thead><tbody>${s.businessObjects.map(r=>`<tr><td>${esc(r.label)}</td><td>${r.oldCount}</td><td>${r.newCount}</td><td class="ADDED">${r.added}</td><td class="REMOVED">${r.removed}</td><td class="UPDATED">${r.updated}</td><td>${r.netChange>=0?'+':''}${r.netChange}</td></tr>`).join('')}</tbody></table></div></div><div class="panel"><h2>批量包子应用</h2>${model.packageUnitSummary.length?`<div class="table-wrap"><table><thead><tr><th>子应用</th><th>新增</th><th>删除</th><th>更新</th><th>疑似替代</th><th>涉及对象类型</th></tr></thead><tbody>${model.packageUnitSummary.map(r=>`<tr><td>${esc(r.name)}</td><td>${r.added}</td><td>${r.removed}</td><td>${r.updated}</td><td>${r.possibleRename}</td><td>${esc(Object.keys(r.activeByObjectType||{}).map(x=>labels[x]||x).join('、'))}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">当前离线包按单一应用展示。</div>'}</div><div class="panel"><h2>状态图例</h2><div class="legend">${['ADDED','REMOVED','UPDATED','POSSIBLE_RENAME','UNMATCHED','HIGH','MEDIUM','LOW','UNKNOWN'].map(badge).join('')}</div></div>`;}
function renderChains(){const allowed=new Set(activeNodes().map(n=>n.nodeId));const values=model.businessChains.filter(c=>allowed.has(c.sourceNodeId));if(!values.length){chains.innerHTML='<div class="panel empty">当前筛选条件下没有可展示的业务链路。若包内关系证据不足，相关对象会标记为“关系待确认”。</div>';return;}if(!state.selectedChain||!values.some(x=>x.chainId===state.selectedChain))state.selectedChain=values[0].chainId;const selected=chainMap.get(state.selectedChain);chains.innerHTML=`<div class="split"><div class="panel item-list"><h2>业务功能链路</h2><p class="count-note">筛选后 ${values.length} 条，首屏展示前 ${Math.min(80,values.length)} 条；请使用筛选或搜索展开局部链路。</p>${values.slice(0,80).map(c=>`<button class="item ${c.chainId===state.selectedChain?'selected':''}" onclick="selectChain('${c.chainId}')"><b>${esc(c.businessName)}</b>${badge(c.changeType)} ${badge(c.evidenceLevel)}<span class="muted">${esc(labels[c.objectType]||c.objectType)} · ${esc(c.packageUnit)}</span></button>`).join('')}</div><div><div class="panel"><h2>${esc(selected.businessName)}</h2><p>${badge(selected.changeType)} ${badge(selected.evidenceLevel)} ${selected.relationPending?'<span class="badge UNKNOWN">关系待确认</span>':''}</p><div class="swimlane">${selected.lanes.map(l=>`<article class="lane ${l.evidenceLevel}"><h4>${esc(l.lane)} ${badge(l.evidenceLevel)}</h4><div>${esc(l.text)}</div></article>`).join('')}</div></div><div class="panel"><h3>关联风险与重点场景</h3>${renderRiskValidation(selected.riskIds,selected.validationIds)}</div></div></div>`;}
function selectChain(id){state.selectedChain=id;renderChains();}
function renderFields(){const allowed=new Set(activeNodes().map(n=>n.nodeId));const q=state.search.trim().toLowerCase();const values=model.fieldLineage.filter(f=>allowed.has(f.ownerNodeId)&&(!q||f.searchableText.includes(q)));if(!values.length){fields.innerHTML='<div class="panel empty">当前筛选条件下没有字段级变化。对象可能只有新增、删除或关系待确认，未编造字段连接。</div>';return;}if(!state.selectedField||!values.some(x=>x.fieldId===state.selectedField))state.selectedField=values[0].fieldId;const f=fieldMap.get(state.selectedField),owner=nodeMap.get(f.ownerNodeId);fields.innerHTML=`<div class="split"><div class="panel item-list"><h2>变化字段与业务配置</h2><p class="count-note">筛选后 ${values.length} 项，首屏展示前 ${Math.min(100,values.length)} 项。</p>${values.slice(0,100).map(x=>`<button class="item ${x.fieldId===state.selectedField?'selected':''}" onclick="selectField('${x.fieldId}')"><b>${esc(x.businessName)} · ${esc(x.fieldName)}</b><span class="muted">${esc(labels[x.objectType]||x.objectType)} · ${esc(labels[x.operation]||clientText(x.operation))}</span></button>`).join('')}</div><div><div class="panel"><h2>${esc(f.businessName)} · ${esc(f.fieldName)}</h2><p>${badge(owner.changeType)} ${badge(f.evidenceLevel)}</p><div class="before-after"><div><h3>修改前</h3><div class="value before">${fmt(f.before)}</div></div><div><h3>修改后</h3><div class="value after">${fmt(f.after)}</div></div></div></div><div class="panel"><div class="detail-grid"><div class="detail-card"><b>业务字段/配置项</b><br>${esc(f.fieldName)}</div><div class="detail-card"><b>所属功能</b><br>${esc(labels[f.objectType]||f.objectType)} · ${esc(f.businessName)}</div><div class="detail-card"><b>直接影响</b><br>${esc(f.directImpacts.join('、')||'待确认')}</div><div class="detail-card"><b>最多三层间接影响</b><br>${esc(f.indirectImpacts.join('、')||'未观察到可稳定归属的间接影响')}</div></div></div></div></div>`;}
function selectField(id){state.selectedField=id;renderFields();}
function renderImpacts(){const values=activeNodes().filter(n=>n.changeType!=='UNCHANGED');if(!values.length){impacts.innerHTML='<div class="panel empty">当前筛选条件下没有变化对象，因此没有可展示的影响与验证链路。</div>';return;}if(!state.selectedImpact||!values.some(x=>x.nodeId===state.selectedImpact))state.selectedImpact=values[0].nodeId;const n=nodeMap.get(state.selectedImpact);const risks=n.riskIds.map(id=>riskMap.get(id)).filter(Boolean),vals=n.validationIds.map(id=>validationMap.get(id)).filter(Boolean);impacts.innerHTML=`<div class="split"><div class="panel item-list"><h2>变化对象</h2><p class="count-note">筛选后 ${values.length} 项，首屏展示前 ${Math.min(80,values.length)} 项。</p>${values.slice(0,80).map(x=>`<button class="item ${x.nodeId===state.selectedImpact?'selected':''}" onclick="selectImpact('${x.nodeId}')"><b>${esc(x.businessName)}</b>${badge(x.changeType)} ${badge(x.riskLevel)}<span class="muted">${esc(labels[x.objectType]||x.objectType)} · ${esc(x.packageUnit)}</span></button>`).join('')}</div><div><div class="panel"><h2>${esc(n.businessName)}</h2><div class="impact-flow"><div class="impact-step"><b>变化对象</b><br>${badge(n.changeType)}<br>${esc(n.businessName)}</div><div class="impact-step"><b>直接影响功能</b><br>${esc(n.affectedFunctions.join('、')||'关系待确认')}</div><div class="impact-step"><b>间接影响功能</b><br>${esc(indirectFor(n.nodeId).join('、')||'未观察到可稳定归属的间接影响')}</div><div class="impact-step"><b>风险根因</b><br>${risks.length?risks.map(r=>`${labels[r.severity]||r.severity}：${clientRiskTitle(r)}`).map(esc).join('<br>'):'未关联确定风险'}</div><div class="impact-step"><b>配置检查与业务测试</b><br>${vals.length?vals.slice(0,8).map(v=>esc(clientText(v.title))).join('<br>'):'按对象重点场景验证'}</div></div></div><div class="panel"><h3>风险与业务验证建议</h3>${renderRiskValidation(n.riskIds,n.validationIds)}</div><button class="primary" onclick="openDrawer('${n.nodeId}')">查看功能详情</button></div></div>`;}
function indirectFor(nodeId){return uniq(model.impacts.filter(i=>i.sourceNodeId===nodeId&&i.directOrIndirect==='INDIRECT').map(i=>i.label));}
function selectImpact(id){state.selectedImpact=id;renderImpacts();}
function renderRiskValidation(riskIds,validationIds){const rs=riskIds.map(id=>riskMap.get(id)).filter(Boolean),vs=validationIds.map(id=>validationMap.get(id)).filter(Boolean);if(!rs.length&&!vs.length)return '<div class="empty">没有与该业务对象稳定关联的风险根因；仍应执行报告中的对象级重点场景。</div>';return `<div class="detail-grid">${rs.map(r=>`<div class="detail-card"><b>${badge(r.severity)} ${esc(clientRiskTitle(r))}</b><p>${badge(r.evidenceLevel)} ${esc(r.uncertaintyStatement||'风险基于已观察到的业务变化触发')}</p><p>${esc(clientText((r.verificationGuidance||[]).join('；')))}</p></div>`).join('')}${vs.slice(0,20).map(v=>`<div class="detail-card"><b>${esc(clientText(v.title))}</b><ol>${v.steps.map(s=>`<li>${esc(clientText(s))}</li>`).join('')}</ol><p><b>预期：</b>${esc(clientText(v.expectedResult||'完成后业务结果符合预期'))}</p><p><b>建议保留：</b>页面截图、操作结果、数据前后值或必要的运行记录</p></div>`).join('')}</div>`;}
function openDrawer(nodeId){const n=nodeMap.get(nodeId);drawerBody.innerHTML=`<h2>${esc(n.businessName)}</h2><p>${badge(n.changeType)} ${badge(n.riskLevel)} ${badge(n.evidenceLevel)}</p><div class="detail-card"><b>子应用</b><br>${esc(n.packageUnit)}</div><div class="detail-card"><b>对象类型</b><br>${esc(labels[n.objectType]||n.objectType)}</div><div class="detail-card"><b>业务作用</b><br>${esc(n.businessPurpose)}</div><div class="detail-card"><b>用户入口</b><br>${esc(n.userEntry)}</div><h3>修改前</h3><div class="value before">${fmt(n.oldSummary)}</div><h3>修改后</h3><div class="value after">${fmt(n.newSummary)}</div>`;drawer.classList.add('open');}
function closeDrawer(){drawer.classList.remove('open');}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.view).classList.add('active');}));
[[packageFilter,'packageUnit'],[typeFilter,'objectType'],[changeFilter,'changeType'],[riskFilter,'riskLevel']].forEach(([el,key])=>el.addEventListener('change',()=>{state[key]=el.value;renderAll();}));searchInput.addEventListener('input',()=>{state.search=searchInput.value.toLowerCase();renderAll();});resetButton.addEventListener('click',()=>{Object.assign(state,{packageUnit:'',objectType:'',changeType:'',riskLevel:'',search:'',selectedChain:null,selectedField:null,selectedImpact:null});[packageFilter,typeFilter,changeFilter,riskFilter].forEach(x=>x.value='');searchInput.value='';renderAll();});
window.__VISUAL_DIFF_READY__=true;init();
</script>
</body>
</html>'''


def client_model_projection(model: dict[str, Any]) -> dict[str, Any]:
    """生成嵌入 HTML 的客户视图模型，隔离完整机器证据。"""

    def client_text(value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"weaver-[a-z0-9-]+-service", "相关业务模块", text, flags=re.I)
        text = re.sub(
            r"\b(?:ebdf|ebdd|ebdp|esb|wfp|wfc|bpm|form|ai_app|t_cus_app|edc_[a-z0-9_]+|custom_[a-z0-9_]+|browser_[a-z0-9_]+|fd_[a-z0-9_]+|i18n_[a-z0-9_]+|dw_[a-z0-9_]+|wf_[a-z0-9_]+|wfr_[a-z0-9_]+)_[a-z0-9_]*\b",
            "业务配置项",
            text,
            flags=re.I,
        )
        text = re.sub(r"\b(?:CONFIG_FOREIGN_KEY|JSON_REFERENCE)\b", "跨环境关联配置", text)
        text = re.sub(r"\bidMap\[[^\]]+\]", "迁入映射中的对应关系", text)
        text = re.sub(r"\bCHG-[A-Z0-9]+\b", "", text)
        text = re.sub(r"\b(?:source_id|import_id|oldExportId|eid)\b", "关联标识", text, flags=re.I)
        text = re.sub(r"\b[\w]*(?:source_id|import_id)\b", "关联标识", text, flags=re.I)
        text = re.sub(r"\b(?:migration-source|content|parent)=[^:\s,\"]+", "对象关联", text, flags=re.I)
        text = re.sub(r"\b[a-zA-Z][\w.-]*\.\$ref\b", "对象绑定", text)
        text = re.sub(r"\b(?:risk|idr|unk|val)[-_][a-z0-9-]{6,}\b", "", text, flags=re.I)
        text = re.sub(r"\ballServerIdMap\[[^\]]+\]", "迁入映射结果", text, flags=re.I)
        text = re.sub(r"\bnoReplaceFkDetail\b", "未替换引用清单", text, flags=re.I)
        text = re.sub(r"按模块与逻辑键定位以下配置表[^。]*", "按业务功能确认相关配置", text)
        text = re.sub(r"逐项核对字段级前后值：[^。]*", "核对业务配置前后变化", text)
        text = text.replace("将核对结果与变化编号逐项回填，并保留查询截图或导出片段", "记录核对结果并保留页面截图或操作结果")
        text = text.replace("变化编号", "业务变化")
        return re.sub(r"\s{2,}", " ", text).strip()

    def client_value(value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return client_text(value)[:500]
        if isinstance(value, list):
            return f"包含 {len(value)} 项业务配置" if value else "未设置"
        return "业务配置已调整"

    node_fields = (
        "nodeId", "nodeType", "objectType", "packageUnit", "packageUnitKey",
        "businessName", "changeType", "oldExists", "newExists", "oldSummary",
        "newSummary", "businessPurpose", "userEntry", "confidence", "evidenceLevel",
        "riskLevel", "riskIds", "validationIds", "affectedFunctions", "searchableText",
    )
    chain_fields = (
        "chainId", "sourceNodeId", "packageUnit", "businessName", "objectType",
        "changeType", "evidenceLevel", "relationPending", "changedStage", "lanes",
        "fieldIds", "impactIds", "riskIds", "validationIds",
    )
    field_fields = (
        "fieldId", "ownerNodeId", "packageUnit", "objectType", "businessName",
        "fieldName", "operation", "category", "before", "after", "directImpacts",
        "indirectImpacts", "evidenceLevel", "searchableText",
    )
    risk_fields = (
        "riskId", "severity", "title", "evidenceLevel", "uncertaintyStatement",
        "validationIds", "verificationGuidance", "searchableText",
    )
    validation_fields = (
        "validationId", "title", "type", "evidenceLevel", "relatedRiskIds", "steps",
        "expectedResult", "applicability", "searchableText",
    )

    def pick(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
        return [{key: item.get(key) for key in fields if key in item} for item in items]

    def safe_node(item: dict[str, Any]) -> dict[str, Any]:
        result = {key: item.get(key) for key in node_fields if key in item}
        for key in ("businessName", "businessPurpose", "userEntry"):
            if key in result:
                result[key] = client_text(result[key])
        for key in ("oldSummary", "newSummary"):
            if key in result:
                result[key] = client_value(result[key])
        result["affectedFunctions"] = [client_text(v) for v in item.get("affectedFunctions") or []]
        result["searchableText"] = " ".join(
            client_text(v) for v in (
                item.get("packageUnit"), item.get("objectType"), item.get("businessName"),
                item.get("businessPurpose"), item.get("userEntry"),
                *(item.get("affectedFunctions") or []),
            ) if v
        ).lower()
        result.pop("packageUnitKey", None)
        return result

    def safe_field(item: dict[str, Any]) -> dict[str, Any]:
        result = {key: item.get(key) for key in field_fields if key in item}
        for key in ("businessName", "fieldName", "operation", "category"):
            if key in result:
                result[key] = client_text(result[key])
        result["before"] = client_value(item.get("before"))
        result["after"] = client_value(item.get("after"))
        result["directImpacts"] = [client_text(v) for v in item.get("directImpacts") or []]
        result["indirectImpacts"] = [client_text(v) for v in item.get("indirectImpacts") or []]
        result.pop("category", None)
        result["searchableText"] = " ".join(
            client_text(v) for v in (
                item.get("businessName"), item.get("fieldName"),
                *(item.get("directImpacts") or []), *(item.get("indirectImpacts") or []),
            ) if v
        ).lower()
        return result

    def safe_chain(item: dict[str, Any]) -> dict[str, Any]:
        result = {key: item.get(key) for key in chain_fields if key in item}
        result["businessName"] = client_text(item.get("businessName"))
        result["lanes"] = [
            {
                "lane": client_text(lane.get("lane")),
                "text": client_text(lane.get("text")),
                "evidenceLevel": lane.get("evidenceLevel"),
            }
            for lane in item.get("lanes") or []
        ]
        return result

    def safe_risk(item: dict[str, Any]) -> dict[str, Any]:
        result = {key: item.get(key) for key in risk_fields if key in item}
        result["title"] = client_text(item.get("title"))
        result["uncertaintyStatement"] = client_text(item.get("uncertaintyStatement"))
        result["verificationGuidance"] = ["核对迁入后的业务关联和功能结果"]
        result["searchableText"] = result["title"].lower()
        return result

    def safe_validation(item: dict[str, Any]) -> dict[str, Any]:
        result = {key: item.get(key) for key in validation_fields if key in item}
        result["title"] = client_text(item.get("title"))
        result["steps"] = [client_text(v) for v in item.get("steps") or []]
        result["expectedResult"] = client_text(item.get("expectedResult"))
        result["searchableText"] = " ".join(
            [result["title"], result["expectedResult"]]
            + result["steps"]
        ).lower()
        return result

    packages = {}
    for role in ("old", "new"):
        package = dict((model.get("packages") or {}).get(role) or {})
        profile = package.get("profile") or {}
        packages[role] = {
            "name": package.get("name"),
            "profile": {"exportTime": profile.get("exportTime")},
        }
    return {
        "schemaVersion": "ebuilder-client-view/v1.0",
        "application": {"name": (model.get("application") or {}).get("name")},
        "packages": packages,
        "directionResolution": {
            "directionSource": (model.get("directionResolution") or {}).get("directionSource"),
        },
        "summary": model.get("summary") or {},
        "packageUnitSummary": [
            {key: item.get(key) for key in ("name", "added", "removed", "updated", "possibleRename")}
            for item in model.get("packageUnitSummary") or []
        ],
        "nodes": [safe_node(item) for item in model.get("nodes") or []],
        "businessChains": [safe_chain(item) for item in model.get("businessChains") or []],
        "fieldLineage": [safe_field(item) for item in model.get("fieldLineage") or []],
        "impacts": [
            {key: item.get(key) for key in ("impactId", "sourceNodeId", "label", "directOrIndirect", "depth")}
            for item in model.get("impacts") or []
        ],
        "risks": [safe_risk(item) for item in model.get("risks") or []],
        "validations": [safe_validation(item) for item in model.get("validations") or []],
    }


def render_visual_diff_html(model: dict[str, Any]) -> str:
    payload = json.dumps(client_model_projection(model), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return HTML_TEMPLATE.replace("__VISUAL_DATA__", payload)


def _read_json(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(render_visual_diff_html(_read_json(args.model)), encoding="utf-8")


if __name__ == "__main__":
    main()
