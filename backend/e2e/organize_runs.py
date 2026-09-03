#!/usr/bin/env python3
"""
E2E 产物整理脚本 — 将散落的「生成代码 + 测试结果 + 渲染图」按 run 重组。

扫描源目录，识别三类产物并迁移到以 run 为中心的新结构：
  e2e_runs/<run_id>/
    ├── manifest.json
    ├── code/<stack>.<ext>  (+ variants/)
    ├── reports/NN_<type>.json  (+ 人类可读 *.html)
    ├── renders/<原始文件名>
    ├── inputs/<截图/ui_description>
    ├── subruns/<deep_verify|kotlin_pipeline>/   # 子流程产物整体保留，不拆平
    └── misc/<零散文件>

设计要点（避免数据丢失）：
  * deep_verify/ kotlin_pipeline/ 内含嵌套目录(aapt2_compile)与同名的 per-stack
    渲染图，若拆平会与顶层文件冲突。故这两个子目录整体搬入 subruns/，
    仅把少量「规范化文件」(deep 报告 / 变体代码) 提升到第 1 级目录。
  * 任何两个源文件解析到同一目标路径时，自动加消歧前缀，绝不静默覆盖。

默认 dry-run（只打印计划不改动）。加 --apply 才真正移动文件。
重复执行：若目标 run 目录已存在则中止，避免半截迁移。

用法:
  python organize_runs.py                 # dry-run
  python organize_runs.py --apply        # 执行
  python organize_runs.py --root /path   # 指定项目根（默认脚本上级的上级）
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ---- stack 识别：文件名/扩展名 → 规范 stack 名 ----
STACK_BY_EXT = {
    ".kt": "android_compose",
    ".xml": "android_xml",
    ".qml": "qt_qml",
    ".html": "windows_html",
    ".jsonl": "a2ui",
    ".xaml": "winui3",
}
LLM_PREFIX = "llm_"

# 测试报告 JSON：源文件名（不含扩展）→ (编号, 类型)。编号=验证深度，保证阅读顺序
REPORT_MAP = {
    "validation_report": ("01", "validation"),
    "validation_results": ("01", "validation"),
    "e2e_unified_report": ("02", "unified"),
    "quick_verify_report": ("02", "unified"),
    "final_report": ("02", "unified"),
    "e2e_deep_report": ("03", "deep"),
    "e2e_compile_report": ("04", "compile"),
    "generation_report": ("05", "generation"),
}

# 子流程目录中需要「提升」到第 1 级规范化位置的少数规范文件
SUBRUN_PROMOTE = {
    "deep_verify": ["e2e_deep_report.json", "e2e_deep_report.html", "settings_page.xaml"],
}


def stack_from_code_name(name: str) -> str | None:
    """从生成代码文件名推断 stack。"""
    stem = name.lower()
    if stem.startswith(LLM_PREFIX):
        rest = stem[len(LLM_PREFIX):]
        for key in ("android_compose", "android_xml", "qt_qml", "windows_html", "a2ui"):
            if rest.startswith(key):
                return key
    if stem.startswith("ws_") and stem.endswith(".kt"):
        return "android_compose"
    if stem in ("mainactivity.kt",) or stem.startswith("kotlin_pipeline"):
        return "android_compose"  # 变体（pipeline 生成），归入 variants/
    if "settings_page" in stem and stem.endswith(".xaml"):
        return "winui3"
    return None


def classify_file(path: Path):
    """返回 (category, meta)。category ∈ {code, report, render, input, other}。"""
    name = path.name
    stem = path.stem
    ext = path.suffix.lower()

    # 1) 生成代码
    stack = stack_from_code_name(name)
    if stack and ext in STACK_BY_EXT:
        # 只有 llm_<stack> 是主代码；其余（ws_/MainActivity/settings_page/kotlin_pipeline_*）都是变体
        is_variant = not name.startswith(LLM_PREFIX)
        return ("code", {"stack": stack, "variant": name if is_variant else None})

    # 2) 测试报告 JSON
    if ext == ".json" and stem in REPORT_MAP:
        num, rtype = REPORT_MAP[stem]
        return ("report", {"num": num, "rtype": rtype, "is_html": False})

    # 3) 人类可读 HTML 报告（*_report.html）→ reports/ 保留原名
    if ext == ".html" and stem.endswith("_report"):
        return ("report", {"num": "09", "rtype": stem, "is_html": True})

    # 4) 渲染截图 PNG / 预览 HTML（保留原始文件名，避免覆盖）
    if ext in (".png", ".html") and ("screenshot" in stem or "_render" in stem):
        return ("render", {"name": name})

    # 5) 输入：ui_description.json / ui_dump*.xml
    if ext == ".json" and stem == "ui_description":
        return ("input", {"name": name})
    if ext == ".xml" and stem.startswith("ui_dump"):
        return ("input", {"name": name})

    return ("other", {"name": name})


def discover_run_sources(root: Path):
    """发现所有待整理的 run 源目录（只含 e2e_demo/run_*）。"""
    return [d for d in (root / "e2e_demo").glob("run_*") if d.is_dir()]


def plan_run(run_dir: Path):
    """为一个 run 源目录生成迁移计划。"""
    plan = {
        "code": [], "code_variants": [], "reports": [],
        "renders": [], "inputs": [], "other": [], "subruns": [],
    }
    for f in sorted(run_dir.iterdir()):
        if f.is_dir():
            if f.name in ("deep_verify", "kotlin_pipeline"):
                # 提升少量规范文件，其余整体搬到 subruns/
                for cand in SUBRUN_PROMOTE.get(f.name, []):
                    cf = f / cand
                    if cf.is_file():
                        cat, meta = classify_file(cf)
                        if cat == "report":
                            plan["reports"].append((cf, meta))
                        elif cat == "code":
                            (plan["code_variants"] if meta.get("variant") else plan["code"]).append((cf, meta))
                        else:
                            plan["other"].append(cf)
                plan["subruns"].append(f)
                continue
            # 其它未知目录：整体归入 misc/<name>/
            plan["other"].append(f)
            continue
        cat, meta = classify_file(f)
        if cat == "code":
            (plan["code_variants"] if meta.get("variant") else plan["code"]).append((f, meta))
        elif cat == "report":
            plan["reports"].append((f, meta))
        elif cat == "render":
            plan["renders"].append((f, meta))
        elif cat == "input":
            plan["inputs"].append((f, meta))
        else:
            plan["other"].append(f)
    # 输入截图：screenshots/run_*/source_screenshot_*.png
    shot = run_dir.parent / "screenshots" / run_dir.name / "source_screenshot_1024.png"
    if shot.exists():
        plan["inputs"].append((shot, {"name": shot.name}))
    return plan


def run_id_for(run_dir: Path) -> str:
    """从源目录名 + generation_report.json 中的 model 推导稳定 run_id。"""
    m = re.search(r"(\d{8})", run_dir.name)
    date = m.group(1) if m else datetime.now().strftime("%Y%m%d")
    model = "doubao-seed-2-1-turbo"
    gr = run_dir / "generation_report.json"
    if gr.exists():
        try:
            data = json.loads(gr.read_text(encoding="utf-8"))
            if data.get("model"):
                model = data["model"]
        except Exception:
            pass
    slug = model.replace(".", "-").lower()
    return f"{date}_{slug}"


def build_moves(plan, run_dir, dest):
    """把 plan 展开成 (src, dst) 列表，并对冲突目标做消歧。"""
    used = {}  # dst(相对dest) -> src
    moves = []

    def place(src: Path, dst: Path):
        rel = dst.relative_to(dest)
        if rel in used and used[rel] != src:
            # 冲突：优先用源文件所在的子目录名做命名空间，否则加数字后缀
            rel_src = src.relative_to(run_dir)
            if len(rel_src.parts) > 1:
                ns = rel_src.parts[-2]
                cand = dst.parent / ns / dst.name
            else:
                cand = dst
            base = cand
            i = 1
            while True:
                crel = cand.relative_to(dest)
                if crel not in used or used[crel] == src:
                    break
                cand = base.parent / f"{base.stem}__{i}{base.suffix}"
                i += 1
            dst = cand
        used[dst.relative_to(dest)] = src
        moves.append((src, dst))

    for (src, meta) in plan["code"]:
        place(src, dest / "code" / f"{meta['stack']}{src.suffix}")
    for (src, meta) in plan["code_variants"]:
        place(src, dest / "code" / "variants" / f"{src.stem}_{meta['stack']}{src.suffix}")
    for (src, meta) in plan["reports"]:
        if meta["is_html"]:
            place(src, dest / "reports" / src.name)
        else:
            place(src, dest / "reports" / f"{meta['num']}_{meta['rtype']}.json")
    for (src, meta) in plan["renders"]:
        place(src, dest / "renders" / meta["name"])
    for (src, meta) in plan["inputs"]:
        place(src, dest / "inputs" / meta["name"])
    for other in plan["other"]:
        place(other, dest / "misc" / other.name)
    return moves


def apply_plan(root: Path, run_dir: Path, run_id: str, plan, do_apply: bool):
    dest = root / "e2e_runs" / run_id
    moves = build_moves(plan, run_dir, dest)
    subruns = plan["subruns"]

    print(f"\n=== run: {run_dir.name} → {run_id} ===")
    print(f"  dest: {dest}")
    for src, dst in moves:
        rel = dst.relative_to(dest)
        print(f"  {'MOVE' if do_apply else 'WOULD':>7}  {src.name:35s} → {rel}")

    if do_apply:
        # 1) 先把第 1 级规范化文件搬走（含从子流程「提升」出来的 deep 报告 / 变体代码）。
        #    必须在整体搬子目录之前，否则提升文件已被移进 subruns/ 导致二次 move 找不到源。
        for sub in ("code", "code/variants", "reports", "renders", "inputs", "subruns", "misc"):
            (dest / sub).mkdir(parents=True, exist_ok=True)
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

        # 2) 子流程目录：整体搬入 subruns/<name>/（提升过的文件已被移走，不会重复）
        for sub in subruns:
            target = dest / "subruns" / sub.name
            target.mkdir(parents=True, exist_ok=True)
            for child in sorted(sub.iterdir()):
                if child.exists():
                    shutil.move(str(child), str(target / child.name))
            # 子目录已空则移除
            try:
                sub.rmdir()
            except OSError:
                pass

        (dest / "manifest.json").write_text(
            json.dumps(build_manifest(run_id, run_dir, plan), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  WROTE manifest.json ({len(moves)} + {len(subruns)} subruns)")
    return moves


def build_manifest(run_id, run_dir, plan):
    code, variants, reports, renders, subruns = {}, {}, [], {}, []
    for (src, meta) in plan["code"]:
        code[meta["stack"]] = f"code/{meta['stack']}{src.suffix}"
    for (src, meta) in plan["code_variants"]:
        variants[src.stem] = f"code/variants/{src.stem}_{meta['stack']}{src.suffix}"
    for (src, meta) in plan["reports"]:
        reports.append(src.name if meta["is_html"] else f"reports/{meta['num']}_{meta['rtype']}.json")
    for (src, meta) in plan["renders"]:
        renders[meta["name"]] = f"renders/{meta['name']}"
    for sub in plan["subruns"]:
        subruns.append(sub.name)
    return {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": f"e2e_demo/{run_dir.name} (migrated)",
        "code": code,
        "variants": variants,
        "reports": reports,
        "renders": renders,
        "subruns": subruns,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正移动文件（默认 dry-run）")
    ap.add_argument("--root", type=str, default=None, help="项目根目录")
    args = ap.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    if not (root / "e2e_demo").exists():
        print(f"ERROR: 找不到 {root/'e2e_demo'}，请检查 --root", file=sys.stderr)
        return 1

    sources = discover_run_sources(root)
    if not sources:
        print("没有发现可整理的 run 源目录。")
        return 0

    print(f"[dry-run] 根目录: {root}")
    print(f"[dry-run] 将整理 {len(sources)} 个 run 源")
    for run_dir in sources:
        run_id = run_id_for(run_dir)
        dest = root / "e2e_runs" / run_id
        if dest.exists():
            print(f"\n⚠️  目标目录已存在：{dest}\n    请先处理或删除该目录，避免半截迁移。已跳过。")
            continue
        plan = plan_run(run_dir)
        apply_plan(root, run_dir, run_id, plan, do_apply=args.apply)

    if not args.apply:
        print("\n⚠️  dry-run 模式，未改动任何文件。加 --apply 执行迁移。")
    else:
        print("\n✅ 迁移完成。请检查 e2e_runs/ 并确认后删除旧目录 e2e_demo/run_20260901。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
