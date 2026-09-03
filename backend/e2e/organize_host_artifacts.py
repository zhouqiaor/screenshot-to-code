#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""e2e_hosts/<stack>/ 构建产物归档整理

配套 organize_runs.py（后者管 e2e_runs/），本脚本管 e2e_hosts/。
规范依据：design-docs/e2e-verification-sop.md §4.3 / §4.6

动作（默认 dry-run，加 --apply 才执行）:
    1. 散落的 _*.log / _*.txt          → logs/<mtime>_<name>
    2. 旧代 APK / *.old.* / *.bak.*    → <build_dir>/_stale_bak/（与构建缓存的回滚备份同目录）
    3. 报告可清理的大目录体积（deps_repo.old* 等），不自动删

沙箱注意：WorkBuddy 环境下 os.remove/shutil.rmtree 被安全 shim 拦截，
本脚本一律用 os.rename 归档，从不真删——真删由用户显式执行。

用法:
    python backend/e2e/organize_host_artifacts.py                     # dry-run 全部 stack
    python backend/e2e/organize_host_artifacts.py --apply
    python backend/e2e/organize_host_artifacts.py --stack android_compose --apply
    python backend/e2e/organize_host_artifacts.py --report-only       # 仅体积报告
"""

import argparse
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOSTS = os.path.join(REPO, "e2e_hosts")

# 判定「旧代产物」的文件名特征（SOP §4.3：演进信息属于日志，不属于文件名）
# 注意：不要把 .idsig 放进来——它是当前 APK 的 v4 签名配套文件，
# 应「跟随其 APK 的判定」（见 collect_stale 里的 companion 逻辑）
STALE_MARKERS = (".old.", ".bak.", ".stale.", ".old0")
# 已被新流程取代的历史 APK 名（仅当同目录存在更新的 *_signed.apk 时才归档）
LEGACY_APK_HINTS = ("_debug_signed.apk", "_md_signed.apk", "_debug.apk", "_md.apk")


def human(n):
    for unit, div in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= div:
            return "%.1f %s" % (n / div, unit)
    return "%d B" % n


def dir_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return total


def archive(src, dst, apply_it):
    """用 os.rename 归档（绕过沙箱删除 shim）。返回是否成功。"""
    if not apply_it:
        return True
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.rename(src, dst)
        return True
    except OSError as e:
        print("    [WARN] rename 失败: %s (%s)" % (src, e))
        return False


def is_log_file(fn):
    """判定是否为应收敛的日志文件。

    收：任意 *.log（如 build.log / build_vfs.log），以及下划线前缀的 _*.txt（诊断中间物）。
    不收：*.py / *.md / *.kts / *.json 等源码与文档。
    """
    if fn.endswith(".log"):
        return True
    if fn.startswith("_") and fn.endswith(".txt"):
        return True
    return False


def collect_logs(stack_dir, apply_it):
    """散落的日志 → logs/<YYYYMMDDTHHMMSS>_<name>"""
    moves = []
    logs_dir = os.path.join(stack_dir, "logs")
    for fn in sorted(os.listdir(stack_dir)):
        full = os.path.join(stack_dir, fn)
        if not os.path.isfile(full):
            continue
        if not is_log_file(fn):
            continue
        ts = time.strftime("%Y%m%dT%H%M%S", time.localtime(os.path.getmtime(full)))
        base = fn.lstrip("_")
        moves.append((full, os.path.join(logs_dir, "%s_%s" % (ts, base))))
    for src, dst in moves:
        print("    log  %s → logs/%s" % (os.path.basename(src), os.path.basename(dst)))
        archive(src, dst, apply_it)
    return len(moves)


def collect_stale(stack_dir, apply_it):
    """旧代产物 → <build_dir>/_stale_bak/（与构建缓存 buildcache.py 的 STALE_DIR 同目录，避免双份散落）"""
    moves = []

    # 扫描构建目录（新老路径都看）
    build_dirs = [d for d in ("build", "compose_cli_build", "xml_cli_build")
                  if os.path.isdir(os.path.join(stack_dir, d))]
    for bd in build_dirs:
        bdir = os.path.join(stack_dir, bd)
        # 回滚备份统一收进各构建目录自己的 _stale_bak/（与 buildcache.py 的 STALE_DIR 一致）
        stale_root = os.path.join(bdir, "_stale_bak")
        try:
            entries = sorted(os.listdir(bdir))
        except OSError:
            continue
        has_current = any(
            e.endswith("_signed.apk") and not any(h in e for h in LEGACY_APK_HINTS)
            for e in entries
        )

        def is_stale_name(name):
            if any(m in name for m in STALE_MARKERS):
                return True
            return has_current and any(h in name for h in LEGACY_APK_HINTS)

        stale_names = set()
        for e in entries:
            # 构建缓存的回滚备份目录本身、以及用户托管的废弃依赖副本，不要二次处理
            if e in ("_stale", "_stale_bak"):
                continue
            if e.startswith("deps_repo.old"):
                continue
            # .idsig 是 apksigner v4 签名的配套文件：只有当它对应的 APK 被判旧代时才一起归档，
            # 否则会把当前有效 APK 的签名误删（dry-run 时实际踩到过）
            if e.endswith(".idsig"):
                if is_stale_name(e[: -len(".idsig")]):
                    stale_names.add(e)
                continue
            if is_stale_name(e):
                stale_names.add(e)

        for e in sorted(stale_names):
            moves.append((os.path.join(bdir, e), os.path.join(stale_root, e)))

    for src, dst in moves:
        kind = "dir " if os.path.isdir(src) else "file"
        print("    %s %s → %s/" % (kind, os.path.relpath(src, stack_dir),
                                    os.path.relpath(os.path.dirname(dst), stack_dir)))
        archive(src, dst, apply_it)
    return len(moves)


def report_cleanable(stack_dir):
    """报告可清理的大目录，不自动删（用户决定）"""
    rows = []
    for name in sorted(os.listdir(stack_dir)):
        full = os.path.join(stack_dir, name)
        if not os.path.isdir(full):
            continue
        if name in ("deps_repo", "build", "compose_cli_build", "xml_cli_build",
                    "__pycache__", "gradle") or name.startswith("deps_repo.old"):
            rows.append((name, dir_size(full)))
    # 各构建目录内的「回滚备份堆积」单独列出：真正可复用的缓存在 <build>/.cache/，
    # 而 _stale_bak/ 只是 force_rmtree/rename_away 让位时留下的旧版/调试残骸，可清理。
    for bd in ("build", "compose_cli_build", "xml_cli_build"):
        sb = os.path.join(stack_dir, bd, "_stale_bak")
        if os.path.isdir(sb):
            rows.append((os.path.join(bd, "_stale_bak"), dir_size(sb)))
    return rows


def main():
    ap = argparse.ArgumentParser(description="e2e_hosts 构建产物归档整理")
    ap.add_argument("--stack", default=None, help="只处理指定 stack，默认全部")
    ap.add_argument("--apply", action="store_true", help="真正执行（默认 dry-run）")
    ap.add_argument("--report-only", action="store_true", help="仅输出体积报告")
    args = ap.parse_args()

    if not os.path.isdir(HOSTS):
        print("[ERROR] 找不到 %s" % HOSTS, file=sys.stderr)
        sys.exit(1)

    stacks = ([args.stack] if args.stack
              else sorted(d for d in os.listdir(HOSTS) if os.path.isdir(os.path.join(HOSTS, d))))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("=== e2e_hosts 归档整理 [%s] ===\n" % mode)

    total_logs = total_stale = 0
    for st in stacks:
        sdir = os.path.join(HOSTS, st)
        if not os.path.isdir(sdir):
            print("[skip] %s 不存在" % st)
            continue
        print("── %s" % st)

        rows = report_cleanable(sdir)
        if rows:
            print("  可清理目录体积：")
            for name, size in sorted(rows, key=lambda x: -x[1]):
                if ".old" in name:
                    tag = "  ← 废弃依赖副本，建议删除"
                elif name.endswith("_stale_bak"):
                    tag = "  ← 回滚备份堆积(可清理，真正缓存见 .cache/)"
                else:
                    tag = ""
                print("    %-24s %10s%s" % (name, human(size), tag))

        if not args.report_only:
            n1 = collect_logs(sdir, args.apply)
            n2 = collect_stale(sdir, args.apply)
            total_logs += n1
            total_stale += n2
            if n1 == 0 and n2 == 0:
                print("  已整洁，无需动作")
        print("")

    if not args.report_only:
        print("汇总：日志归位 %d，旧代产物归档 %d" % (total_logs, total_stale))
        if not args.apply:
            print("（dry-run，未实际移动。加 --apply 执行）")


if __name__ == "__main__":
    main()
