# -*- coding: utf-8 -*-
"""
build_guide_html.py
【报表搭建指导文档】唯一交付产物生成器 —— 独立静态 HTML（已废弃 docx 输出）。

设计约束（与 SKILL.md「能力一 · 交付产物规范」严格一致）：
  1. 单文件：CSS / JS / 数据全部内联，无任何外部资源依赖（不引 CDN、不引字体、不引图片）；
  2. 表格布局：以 Excel 单元格网格还原报表结构（列标行 + 分类横幅 + 表头行 + 配置行）；
     **不再输出独立的筛选行** —— 筛选/转换配置统一收进配置行单元格的点击弹窗；
  3. 点击配置行单元格弹出配置弹窗：一次性展示该列完整配置
     （基础配置 / 父格筛选 / 自定义筛选 / 结果筛选 / 转换设置）；
  4. **不再输出「全量配置明细」区** —— 避免同一份配置在页面上重复展示两遍；
     配置面板改为放在隐藏容器中，仅作为弹窗内容源；
  5. 无脚本降级：隐藏容器通过 <noscript> 内联样式自动显形，
     在禁用/隔离 JS 的预览环境（他人共享打开）中仍可完整查看 —— 这是实测踩过的坑。

用法：
    python build_guide_html.py --config <config.json> --output <out.html>

config.json 结构见模块底部 SAMPLE_CONFIG。
"""
import argparse
import html
import json
import re as _re


# 永久禁令：任何场景都禁止渲染此文本（见 SKILL.md「HTML报表搭建指导手册输出规范」）
_BANNED_TITLE_LINE = "严格依据需求生成，未添加需求未提及项（无行合计）"


def _clean(t) -> str:
    """清洗被永久禁用的文本行，避免在任何字段中渲染。"""
    if not t:
        return t
    s = str(t)
    s = s.replace(_BANNED_TITLE_LINE, "")
    s = s.replace("严格依据需求生成，未添加需求未提及项", "")
    return s.strip()


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def col_letter(i: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA"""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def kv(k, v) -> str:
    return f'<div class="kv"><div class="k">{e(k)}</div><div class="v">{e(v)}</div></div>'


# --------------------------------------------------------------------------
# 配置面板（单一来源：既供 <details> 降级展示，也供弹窗 innerHTML 复用）
# --------------------------------------------------------------------------
def build_panel(c: dict) -> str:
    """生成某一列的完整配置面板 HTML 片段。"""
    p = ['<div class="sec">一、基础配置</div>']
    p.append(kv("数据源字段", c.get("src") or "—"))
    p.append(kv("左父格", c.get("lparent") or "无"))
    p.append(kv("上父格", c.get("tparent") or "无"))
    p.append(kv("扩展方向", c.get("expand") or "不扩展"))
    disp = c.get("disp") or "—"
    if c.get("summ"):
        disp += f"（汇总方式：{c['summ']}）"
    p.append(kv("显示方式", disp))
    if c.get("formula"):
        p.append(kv("公式字段", c["formula"]))

    # 父格筛选：必须写清 左父格 / 左父格关联字段 / 子格关联字段 / 关联方式
    fp = c.get("fp") or {}
    p.append('<div class="sec">二、父格筛选</div>')
    if isinstance(fp, dict) and fp:
        p.append(kv("当前单元格左父格", fp.get("parent_cell") or c.get("lparent") or "—"))
        p.append(kv("左父格关联字段", fp.get("parent_field") or "—"))
        p.append(kv("子格关联字段", fp.get("child_field") or "—"))
        p.append(kv("关联方式", fp.get("match") or "等于"))
    elif isinstance(fp, str) and fp:
        p.append(f'<div class="kv"><div class="v">{e(fp)}</div></div>')
    else:
        p.append('<div class="kv"><div class="v">沿分组链自动过滤，无需额外配置</div></div>')

    # 自定义筛选：条件字段 / 过滤方式 / 条件值
    p.append('<div class="sec">三、自定义筛选</div>')
    cus = c.get("custom") or []
    if cus:
        p.append('<table class="mini"><thead><tr><th>条件字段</th>'
                 '<th>过滤方式</th><th>条件值</th></tr></thead><tbody>')
        for row in cus:
            f_, m_, v_ = (list(row) + ["", "", ""])[:3]
            p.append(f"<tr><td>{e(f_)}</td><td>{e(m_)}</td><td>{e(v_)}</td></tr>")
        p.append("</tbody></table>")
    else:
        p.append('<div class="kv"><div class="v">无</div></div>')

    p.append('<div class="sec">四、结果筛选 / 转换设置</div>')
    p.append(kv("结果筛选", c.get("result_filter") or "无"))
    p.append(kv("转换设置", c.get("transform") or "无"))
    return "".join(p)


# --------------------------------------------------------------------------
# 主体
# --------------------------------------------------------------------------
CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f5f7fa;color:#303133;
 font-family:"Microsoft YaHei","PingFang SC",sans-serif;font-size:13px;line-height:1.7}
.wrap{max-width:1600px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:16px;margin:28px 0 10px;padding-left:9px;border-left:4px solid #409eff}
.sub{color:#909399;margin:0 0 6px}
.meta{color:#606266;background:#f4f4f5;border:1px solid #e9e9eb;border-radius:4px;
 display:inline-block;padding:5px 10px;margin:0 0 12px;font-size:12px}
.tip{background:#ecf5ff;border:1px solid #b3d8ff;color:#409eff;
 padding:9px 12px;border-radius:4px;margin:12px 0 18px}
.gridwrap{overflow-x:auto;border:1px solid #e4e7ed;background:#fff;border-radius:4px}
table.grid{border-collapse:collapse;white-space:nowrap}
table.grid th,table.grid td{border:1px solid #dcdfe6;padding:5px 8px;
 font-size:12px;vertical-align:top}
.colhd{background:#f0f2f5;color:#909399;text-align:center;font-weight:400;font-size:11px}
.rowhd{background:#f0f2f5;color:#909399;text-align:center;font-size:11px;
 position:sticky;left:0;z-index:2;min-width:64px}
.banner{background:#eaf3ff;color:#1f5fa8;text-align:center;font-weight:600}
.hdr{background:#fafafa;font-weight:600;text-align:center}
td.cfg{cursor:pointer;max-width:230px;white-space:normal;position:relative}
td.cfg:hover{background:#ecf5ff;box-shadow:inset 0 0 0 1px #409eff}
.badges{position:absolute;top:2px;right:2px;display:flex;gap:2px}
.badges i{font-style:normal;font-size:9px;color:#fff;border-radius:2px;
 padding:0 3px;line-height:13px}
i.b-f{background:#e6a23c}
i.b-t{background:#67c23a}
i.b-p{background:#909399}
.tagline{color:#909399}
.tagline b{color:#303133;font-weight:600}
.panels{display:none}
.nsq{display:none}
.panels .pbox{background:#fff;border:1px solid #e4e7ed;border-radius:4px;margin:8px 0}
.panels .ptitle{padding:9px 12px;font-weight:600;background:#fafafa;
 border-bottom:1px solid #e4e7ed}
.pbody{padding:12px 14px}
.sec{font-weight:600;color:#409eff;margin:12px 0 6px}
.sec:first-child{margin-top:0}
.kv{display:flex;border-bottom:1px dashed #ebeef5;padding:4px 0}
.kv .k{width:150px;flex:none;color:#909399}
.kv .v{flex:1;word-break:break-all}
table.mini{border-collapse:collapse;width:100%;margin:4px 0}
table.mini th,table.mini td{border:1px solid #ebeef5;padding:4px 7px;font-size:12px;text-align:left}
table.mini th{background:#fafafa;color:#606266}
table.plain{border-collapse:collapse;width:100%;background:#fff}
table.plain th,table.plain td{border:1px solid #e4e7ed;padding:7px 9px;font-size:12px;text-align:left}
table.plain th{background:#fafafa}
.ds{border:1px solid #e4e7ed;border-radius:4px;margin:10px 0;padding:10px 12px;background:#fff}
.ds-h{font-size:13px;margin-bottom:4px}
.ds-use{color:#909399;font-size:12px}
.ds-logic{color:#606266;font-size:12px;margin:2px 0 6px}
.ds-logic b{color:#409eff}
table.ftbl{margin:2px 0 0}
tr.join td{border:none;padding:0;text-align:center}
tr.join .andor{display:inline-block;background:#ecf5ff;color:#409eff;border:1px solid #b3d8ff;
 border-radius:10px;padding:0 12px;font-size:11px;line-height:18px;margin:2px 0}
.ds-empty{color:#909399;font-size:12px;padding:4px 0}
#mask{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:50}
#modal{display:none;position:fixed;z-index:51;top:50%;left:50%;transform:translate(-50%,-50%);
 width:min(720px,92vw);max-height:82vh;overflow:auto;background:#fff;border-radius:6px;
 box-shadow:0 8px 26px rgba(0,0,0,.2)}
#mhd{padding:12px 16px;border-bottom:1px solid #e4e7ed;font-weight:600;
 display:flex;justify-content:space-between;align-items:center}
#mclose{cursor:pointer;color:#909399;font-size:19px;line-height:1}
#mbody{padding:14px 16px}
.foot{color:#c0c4cc;text-align:center;margin:28px 0 6px;font-size:11px}
"""

JS = """
(function(){
  var mask=document.getElementById('mask'),modal=document.getElementById('modal'),
      mt=document.getElementById('mtitle'),mb=document.getElementById('mbody');
  function open(col){
    var src=document.getElementById('p-'+col); if(!src) return;
    mt.textContent=src.getAttribute('data-title')||col;
    mb.innerHTML=src.innerHTML;
    mask.style.display='block'; modal.style.display='block';
  }
  function close(){ mask.style.display='none'; modal.style.display='none'; }
  document.querySelectorAll('[data-col]').forEach(function(td){
    td.addEventListener('click',function(){ open(td.getAttribute('data-col')); });
  });
  mask.addEventListener('click',close);
  document.getElementById('mclose').addEventListener('click',close);
  document.addEventListener('keydown',function(ev){ if(ev.key==='Escape') close(); });
})();
"""


def build_html(cfg: dict) -> str:
    cols = cfg.get("columns") or []
    n = len(cols)

    # ===== 表头动态生成规则（详见 SKILL.md「HTML报表搭建指导手册输出规范」）=====
    report_name = cfg.get("report_name")
    source_file = cfg.get("source_file")
    if report_name:
        title = f"{report_name} · 搭建配置指导"
    elif source_file:
        base = _re.sub(r"\.[^.]+$", "", str(source_file))
        title = f"{base} · 搭建配置指导"
    else:
        title = cfg.get("title") or "报表搭建配置指导"
    title = _clean(title)

    if source_file:
        subtitle = f"需求来源：{source_file}"
    else:
        subtitle = cfg.get("subtitle") or ""
    subtitle = _clean(subtitle)

    ds = cfg.get("datasets") or []
    ds_count = cfg.get("data_source_count") or len(ds)
    meta = f"｜共 {n} 列单元格字段配置、{ds_count} 个数据源"
    note = _clean(cfg.get("note"))
    tips = [_clean(t) for t in (cfg.get("tips") or []) if _clean(t)]

    # ---- 列标行 ----
    grid = ['<table class="grid"><tbody>']
    grid.append('<tr><td class="rowhd"></td>')
    for i in range(n):
        letter = cols[i].get("letter") or col_letter(i)
        grid.append(f'<td class="colhd">{e(letter)}</td>')
    grid.append("</tr>")

    # ---- 分类横幅行（可选）----
    rowno = 1
    banners = cfg.get("banners") or []
    if banners:
        grid.append(f'<tr><td class="rowhd">{rowno}</td>')
        for b in banners:
            grid.append(f'<td class="banner" colspan="{int(b.get("span",1))}">'
                        f'{e(b.get("text"))}</td>')
        grid.append("</tr>")
        rowno += 1

    # ---- 表头行（字段名）----
    grid.append(f'<tr><td class="rowhd">{rowno}</td>')
    for c in cols:
        grid.append(f'<td class="hdr">{e(c.get("field"))}</td>')
    grid.append("</tr>")
    rowno += 1

    # ---- 配置行：数据源/父格/扩展/显示(汇总)/公式 ----
    grid.append(f'<tr><td class="rowhd">{rowno}<br><span class="tagline">单元格配置</span></td>')
    for c in cols:
        letter = c.get("letter")
        disp = c.get("disp") or "—"
        if c.get("summ"):
            disp += "·" + c["summ"]
        bits = [f'<b>源</b> {e(c.get("src") or "—")}',
                f'<b>左父格</b> {e(c.get("lparent") or "无")}',
                f'<b>扩展</b> {e(c.get("expand") or "不扩展")}',
                f'<b>显示</b> {e(disp)}']
        if c.get("formula"):
            bits.append(f'<b>公式</b> {e(c["formula"])}')
        # 角标：仅标注「有区分度」的特殊配置，避免全表都亮而失去提示意义
        bg, hint = [], []
        if isinstance(c.get("fp"), dict) and c.get("fp"):
            bg.append('<i class="b-p" title="配有父格筛选">父</i>')
            hint.append("父格筛选")
        if c.get("custom") or c.get("result_filter"):
            bg.append('<i class="b-f" title="配有自定义/结果筛选">筛</i>')
            hint.append("自定义筛选")
        if c.get("transform"):
            bg.append('<i class="b-t" title="配有转换设置">转</i>')
            hint.append("转换设置")
        tip = "点击查看完整配置" + ("（含 %s）" % "、".join(hint) if hint else "")
        badge = f'<div class="badges">{"".join(bg)}</div>' if bg else ""
        grid.append(f'<td class="cfg" data-col="{e(letter)}" title="{tip}">{badge}'
                    f'<div class="tagline">' + "<br>".join(bits) + "</div></td>")
    grid.append("</tr></tbody></table>")

    # ---- 配置面板：隐藏容器，仅作弹窗内容源；禁用脚本时由 <noscript> 自动显形 ----
    det = []
    for c in cols:
        letter = c.get("letter")
        ptitle = f'{letter} · {c.get("field")}'
        det.append(f'<div class="pbox"><div class="ptitle">{e(ptitle)}</div>'
                   f'<div class="pbody" id="p-{e(letter)}" data-title="{e(ptitle)}">'
                   f'{build_panel(c)}</div></div>')

    # ---- 数据集 / 查询条件 / 其他表 ----
    extra = []
    ds = cfg.get("datasets") or []
    if ds:
        extra.append('<h2>数据集与筛选条件</h2>')
        for d in ds:
            name = d.get("name") or "—"
            logic = d.get("logic") or "AND"
            usage = d.get("usage")
            filters = d.get("filters")
            block = [f'<div class="ds"><div class="ds-h">数据集：<b>{e(name)}</b>']
            if usage:
                block.append(f'<span class="ds-use">｜ 用途：{e(usage)}</span>')
            block.append('</div>')
            if filters:
                block.append(f'<div class="ds-logic">组合逻辑：<b>{e(logic)}</b></div>')
                block.append('<table class="plain ftbl"><thead><tr>'
                             '<th>条件字段</th><th>过滤方式</th><th>条件值</th>'
                             '</tr></thead><tbody>')
                for i, f_ in enumerate(filters):
                    join = f_.get("join") or logic
                    if i > 0:
                        block.append(f'<tr class="join"><td colspan="3">'
                                     f'<span class="andor">{e(join)}</span></td></tr>')
                    block.append(f'<tr><td>{e(f_.get("field"))}</td>'
                                 f'<td>{e(f_.get("op"))}</td>'
                                 f'<td>{e(f_.get("value"))}</td></tr>')
                block.append('</tbody></table>')
            else:
                block.append('<div class="ds-empty">无数据集级筛选（按组织维度取数）</div>')
            block.append('</div>')
            extra.append("".join(block))

    qs = cfg.get("queries") or []
    if qs:
        extra.append('<h2>报表查询条件</h2><table class="plain"><thead><tr>'
                     "<th>查询条件</th><th>字段类型</th><th>是否配默认值</th>"
                     "<th>默认值类型</th><th>显示位置</th><th>关联字段 / SQL 过滤</th>"
                     "</tr></thead><tbody>")
        for q in qs:
            extra.append(
                f'<tr><td>{e(q.get("name"))}</td><td>{e(q.get("type"))}</td>'
                f'<td>{e(q.get("default"))}</td><td>{e(q.get("default_kind"))}</td>'
                f'<td>{e(q.get("position"))}</td><td>{e(q.get("relate") or q.get("sql"))}</td></tr>')
        extra.append("</tbody></table>")

    for tbl in (cfg.get("tables") or []):
        extra.append(f'<h2>{e(tbl.get("title"))}</h2><table class="plain"><thead><tr>'
                     + "".join(f"<th>{e(h)}</th>" for h in tbl.get("headers", []))
                     + "</tr></thead><tbody>")
        for r in tbl.get("rows", []):
            extra.append("<tr>" + "".join(f"<td>{e(v)}</td>" for v in r) + "</tr>")
        extra.append("</tbody></table>")

    if tips:
        extra.append("<h2>搭建注意事项</h2><ul>"
                     + "".join(f"<li>{e(t)}</li>" for t in tips) + "</ul>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><style>{CSS}</style>
<noscript><style>.panels{{display:block}} .nsq{{display:block}}</style></noscript></head>
<body><div class="wrap">
<h1>{e(title)}</h1>
<p class="sub">{e(subtitle)}</p>
<p class="meta">{e(meta)}</p>
<div class="tip">点击配置行中任一单元格，即可弹出该字段的完整配置说明
（基础配置 / 父格筛选 / 自定义筛选 / 结果筛选 / 转换设置）。
单元格右上角角标含义：<i class="b-p" style="padding:0 3px;border-radius:2px;color:#fff;
background:#909399;font-style:normal;font-size:11px">父</i> 配有父格筛选、
<i style="padding:0 3px;border-radius:2px;color:#fff;background:#e6a23c;
font-style:normal;font-size:11px">筛</i> 配有自定义/结果筛选、
<i style="padding:0 3px;border-radius:2px;color:#fff;background:#67c23a;
font-style:normal;font-size:11px">转</i> 配有转换设置。</div>
{e(note) if note else ""}
<h2>报表单元格布局与配置</h2>
<div class="gridwrap">{''.join(grid)}</div>
<h2 class="nsq">配置明细（当前环境未启用脚本，已自动展开）</h2>
<div class="panels">{''.join(det)}</div>
{''.join(extra)}
<div class="foot">本文档为单文件静态 HTML，全部样式与交互内联，无外部资源依赖。</div>
</div>
<div id="mask"></div>
<div id="modal"><div id="mhd"><span id="mtitle"></span><span id="mclose">&times;</span></div>
<div id="mbody"></div></div>
<script>{JS}</script>
</body></html>"""


SAMPLE_CONFIG = {
    # 表头动态生成：优先级1=report_name（需求文档内报表名），优先级2=source_file（文件名）
    "report_name": None,
    "source_file": "示例需求-费用统计.xlsx",
    "banners": [{"text": "组织体系", "span": 2}],
    "columns": [
        {"letter": "A", "field": "部门", "src": "组织表.部门", "lparent": "无",
         "tparent": "无", "expand": "纵向", "disp": "分组"},
        {"letter": "B", "field": "金额", "src": "费用表.金额", "lparent": "A4(部门)",
         "expand": "纵向", "disp": "汇总", "summ": "求和",
         "fp": {"parent_cell": "A4", "parent_field": "组织表.部门",
                "child_field": "费用表.所属部门", "match": "等于"},
         "custom": [["年份", "等于", "{year}"]], "transform": "万元"},
    ],
    "datasets": [{
        "name": "费用表",
        "logic": "AND",
        "usage": "金额汇总来源",
        "filters": [
            {"field": "核算机构", "op": "不包含", "value": "专项机构清单（亘岩/契约锁/e-office/eteams…）"},
            {"field": "年份", "op": "等于", "value": "{year}"},
        ],
    }],
    "queries": [{"name": "年份", "type": "日期", "default": "是", "default_kind": "常规",
                 "position": "平铺", "relate": "费用表.年份"}],
    "tips": ["合计行需手动放置，引擎不会自动生成"],
}


def main():
    ap = argparse.ArgumentParser(description="生成报表搭建指导 HTML（唯一交付格式）")
    ap.add_argument("--config", required=False, help="配置 JSON 路径")
    ap.add_argument("--output", required=True, help="输出 HTML 路径")
    ap.add_argument("--sample", action="store_true", help="使用内置示例配置")
    a = ap.parse_args()

    if a.sample or not a.config:
        cfg = SAMPLE_CONFIG
    else:
        with open(a.config, encoding="utf-8") as f:
            cfg = json.load(f)

    with open(a.output, "w", encoding="utf-8") as f:
        f.write(build_html(cfg))
    print("generated:", a.output, "columns =", len(cfg.get("columns") or []))


if __name__ == "__main__":
    main()
