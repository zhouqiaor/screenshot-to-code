#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""E2E 验证报告生成器

把结构化数据（JSON）渲染成 **自包含单文件 HTML**：所有图片 base64 内嵌，
可在 WorkBuddy webview / 浏览器 file:// 下正常查看（外部相对路径图片会裂）。

用法:
    python build_report.py --data report_data.json --out final_report.html
    python build_report.py --data example_data.json --out /tmp/demo.html --base-dir .

参数:
    --data      数据 JSON 路径（schema 见 report_data.schema.json）
    --out       输出 HTML 路径
    --base-dir  数据中相对图片/产物路径的基准目录，默认取 --data 所在目录
    --strict    遇到缺图/缺产物直接报错退出（CI 用），默认仅告警

约定（对应 design-docs/e2e-verification-sop.md）:
    - 状态只允许 pass / fail / blocked / degraded / na，其它值直接报错
    - 产物清单会自动补算 SHA256 前 12 位与文件大小
"""

import argparse
import base64
import datetime
import hashlib
import html
import json
import mimetypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "report_template.html")

# SOP §1.1 定义的 5 种状态，禁止自造
VALID_STATUS = {
    "pass": "PASS",
    "fail": "FAIL",
    "blocked": "BLOCKED",
    "degraded": "DEGRADED",
    "na": "N/A",
}

WARNINGS = []


def warn(msg, strict=False):
    if strict:
        print("[ERROR] %s" % msg, file=sys.stderr)
        sys.exit(2)
    WARNINGS.append(msg)
    print("[WARN] %s" % msg)


def esc(s):
    return html.escape(str(s if s is not None else ""))


def badge(status, strict=False):
    """渲染状态徽章。status 必须是 VALID_STATUS 的 key。"""
    key = str(status or "").strip().lower().replace("/", "").replace("-", "")
    if key == "na":
        key = "na"
    if key not in VALID_STATUS:
        warn("非法状态值 %r（只允许 %s）" % (status, "/".join(VALID_STATUS)), strict)
        return '<span class="badge na">%s</span>' % esc(status)
    return '<span class="badge %s">%s</span>' % (key, VALID_STATUS[key])


def embed_image(path, base_dir, strict=False):
    """把图片读成 data URI。找不到则返回 None。"""
    if not path:
        return None
    full = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(full):
        warn("图片不存在，跳过内嵌: %s" % full, strict)
        return None
    mime = mimetypes.guess_type(full)[0] or "image/png"
    with open(full, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


def file_stat(path, base_dir, strict=False):
    """返回 (人类可读大小, sha256 前12位)。找不到返回 (None, None)。"""
    full = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(full):
        warn("产物不存在，无法取哈希: %s" % full, strict)
        return None, None
    size = os.path.getsize(full)
    h = hashlib.sha256()
    with open(full, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    if size >= 1024 ** 3:
        human = "%.2f GB" % (size / 1024 ** 3)
    elif size >= 1024 ** 2:
        human = "%.2f MB" % (size / 1024 ** 2)
    elif size >= 1024:
        human = "%.1f KB" % (size / 1024)
    else:
        human = "%d B" % size
    return human, h.hexdigest()[:12]


# --------------------------- 各章节渲染 ---------------------------

def render_metrics(data, strict=False):
    items = data.get("metrics") or []
    if not items:
        return ""
    cells = []
    for m in items:
        tone = str(m.get("tone", "")).lower()
        cls = " " + tone if tone in ("ok", "warn", "bad") else ""
        cells.append(
            '<div class="metric"><div class="m-val%s">%s</div>'
            '<div class="m-lbl">%s</div><div class="m-sub">%s</div></div>'
            % (cls, esc(m.get("value")), esc(m.get("label")), esc(m.get("sub", "")))
        )
    return '<section><h2>一、指标总览</h2>\n<div class="metrics">%s</div></section>\n' % "".join(cells)


def render_matrix(data, strict=False):
    """验证矩阵：层·项目·预期·操作·结果·状态 —— 六列缺一不可（SOP §5.2）"""
    rows = data.get("matrix") or []
    if not rows:
        return ""
    trs = []
    for r in rows:
        for k in ("expected", "action", "result"):
            if not r.get(k):
                warn("验证矩阵行缺少必填字段 %r: %s" % (k, r.get("item")), strict)
        trs.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td class=\"mono\">%s</td><td>%s</td><td>%s</td></tr>"
            % (esc(r.get("layer")), esc(r.get("item")), esc(r.get("expected")),
               esc(r.get("action")), esc(r.get("result")), badge(r.get("status"), strict))
        )
    note = data.get("matrix_note")
    note_html = '<div class="callout"><b>结论：</b>' + esc(note) + "</div>\n" if note else ""
    # 注意：表头含 CSS 的 `%`，一律用字符串拼接，禁用 %-格式化（会被当成格式符）
    return (
        '<section><h2>二、验证矩阵</h2>\n'
        '<table><thead><tr><th style="width:8%">层</th><th style="width:16%">验证项</th>'
        '<th style="width:20%">预期</th><th style="width:22%">操作</th>'
        '<th style="width:26%">结果</th><th style="width:8%">状态</th></tr></thead>\n'
        "<tbody>" + "".join(trs) + "</tbody></table>\n" + note_html + "</section>\n"
    )


def render_screenshots(data, base_dir, strict=False):
    groups = data.get("screenshot_groups") or []
    if not groups:
        return ""
    out = ['<section><h2>三、截图对比</h2>']
    for g in groups:
        if g.get("title"):
            out.append("<h3>%s</h3>" % esc(g["title"]))
        if g.get("note"):
            out.append('<div class="callout">%s</div>' % esc(g["note"]))
        shots = g.get("shots") or []
        grid = "grid2" if len(shots) == 2 else "grid3"
        cards = []
        for s in shots:
            uri = embed_image(s.get("path"), base_dir, strict)
            if not uri:
                continue
            meta = esc(s.get("meta", "")) if s.get("meta") else ""
            cards.append(
                '<div class="card"><div class="cap">%s</div><img src="%s">%s</div>'
                % (esc(s.get("caption")), uri,
                   '<div class="meta">%s</div>' % meta if meta else "")
            )
        if cards:
            out.append('<div class="%s">%s</div>' % (grid, "".join(cards)))
    out.append("</section>\n")
    return "\n".join(out)


def render_rootcause(data, strict=False):
    rows = data.get("root_causes") or []
    if not rows:
        return ""
    trs = []
    for r in rows:
        trs.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (esc(r.get("layer")), esc(r.get("symptom")), esc(r.get("cause")),
               badge(r.get("status"), strict), esc(r.get("fix")))
        )
    return (
        '<section><h2>四、根因分析</h2>\n'
        '<table><thead><tr><th style="width:10%">层级</th><th style="width:24%">症状</th>'
        '<th style="width:26%">根因</th><th style="width:10%">状态</th>'
        '<th style="width:30%">修复</th></tr></thead>\n'
        "<tbody>" + "".join(trs) + "</tbody></table></section>\n"
    )


def render_artifacts(data, base_dir, strict=False):
    """产物清单：自动补算大小与 SHA256（SOP §4.4 可追溯性硬要求）"""
    rows = data.get("artifacts") or []
    if not rows:
        return ""
    trs = []
    for a in rows:
        size, sha = file_stat(a.get("path"), base_dir, strict)
        size = a.get("size") or size or "—"
        sha = a.get("sha256") or sha or "—"
        trs.append(
            '<tr><td class="mono">%s</td><td>%s</td><td>%s</td>'
            '<td class="mono">%s</td><td class="mono">%s</td></tr>'
            % (esc(a.get("path")), esc(a.get("desc", "")), esc(size),
               esc(sha), esc(a.get("built_at", "—")))
        )
    env = data.get("environment") or {}
    env_html = ""
    if env:
        width = max((len(str(k)) for k in env), default=0) + 2
        body = "\n".join(str(k).ljust(width) + str(v) for k, v in env.items())
        env_html = "<h3>运行环境</h3>\n<pre>" + esc(body) + "</pre>\n"
    return (
        '<section><h2>五、产物清单</h2>\n'
        '<table><thead><tr><th style="width:34%">路径</th><th style="width:26%">说明</th>'
        '<th style="width:10%">大小</th><th style="width:14%">SHA256(12)</th>'
        '<th style="width:16%">构建时间</th></tr></thead>\n'
        "<tbody>" + "".join(trs) + "</tbody></table>\n" + env_html + "</section>\n"
    )


def render_references(data, strict=False):
    rows = data.get("references") or []
    if not rows:
        return ""
    trs = []
    for r in rows:
        trs.append("<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>"
                   % (esc(r.get("name")), esc(r.get("practice")), esc(r.get("applied"))))
    return (
        '<section><h2>六、业界参考</h2>\n'
        '<table><thead><tr><th style="width:20%">来源</th><th style="width:40%">做法</th>'
        '<th style="width:40%">本项目落地</th></tr></thead>\n'
        "<tbody>" + "".join(trs) + "</tbody></table></section>\n"
    )


def render_next(data, strict=False):
    items = data.get("next_steps") or []
    if not items:
        return ""
    lis = []
    for n in items:
        if isinstance(n, str):
            lis.append("<li>%s</li>" % esc(n))
        else:
            done = n.get("done")
            prio = esc(n.get("priority", ""))
            text = esc(n.get("text", ""))
            if done:
                lis.append('<li><b style="color:var(--pass)">&#10003; 已完成</b>：%s</li>' % text)
            else:
                lis.append("<li><b>%s</b>：%s</li>" % (prio, text))
    return '<section><h2>七、下一步</h2>\n<ul>%s</ul></section>\n' % "".join(lis)


# --------------------------- 主流程 ---------------------------

def build(data, base_dir, strict=False):
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    now = datetime.datetime.now().astimezone()
    subtitle = data.get("subtitle") or ""
    footer = data.get("footer") or (
        "生成时间 %s · 模板 e2e_runs/_templates/report · 规范 design-docs/e2e-verification-sop.md"
        % now.strftime("%Y-%m-%dT%H:%M:%S%z"))

    mapping = {
        "{{TITLE}}": esc(data.get("title") or "E2E 验证报告"),
        "{{SUBTITLE}}": esc(subtitle),
        "{{SECTION_METRICS}}": render_metrics(data, strict),
        "{{SECTION_MATRIX}}": render_matrix(data, strict),
        "{{SECTION_SCREENSHOTS}}": render_screenshots(data, base_dir, strict),
        "{{SECTION_ROOTCAUSE}}": render_rootcause(data, strict),
        "{{SECTION_ARTIFACTS}}": render_artifacts(data, base_dir, strict),
        "{{SECTION_REFERENCES}}": render_references(data, strict),
        "{{SECTION_NEXT}}": render_next(data, strict),
        "{{FOOTER}}": esc(footer),
    }
    for k, v in mapping.items():
        tpl = tpl.replace(k, v)
    return tpl


def main():
    ap = argparse.ArgumentParser(description="E2E 验证报告生成器")
    ap.add_argument("--data", required=True, help="数据 JSON 路径")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    ap.add_argument("--base-dir", default=None, help="相对路径基准目录，默认为 --data 所在目录")
    ap.add_argument("--strict", action="store_true", help="缺图/缺产物/非法状态时直接失败")
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    base_dir = args.base_dir or os.path.dirname(os.path.abspath(args.data))
    html_text = build(data, base_dir, args.strict)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_text)

    size_kb = os.path.getsize(args.out) / 1024
    print("[OK] %s (%.1f KB)" % (args.out, size_kb))
    if WARNINGS:
        print("[!] %d 条告警：" % len(WARNINGS))
        for w in WARNINGS:
            print("    -", w)


if __name__ == "__main__":
    main()
