#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 Flask 博客整站导出成静态站点，输出到 dist/。

用法（在项目根目录执行）：

    python tools/export_static.py

为什么要它：线上托管的是静态站，而页面本身是 Flask 在请求时渲染的。
改了 posts/ 里的文章或 templates/ 里的模板后，必须重新跑一次本脚本，
dist/ 才会与源码同步。
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist"
STATIC_DIR = BASE_DIR / "static"


def load_app():
    """按文件路径加载 app.py，避免依赖当前工作目录。"""
    spec = importlib.util.spec_from_file_location("blog_app_export", str(BASE_DIR / "app.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["blog_app_export"] = module
    spec.loader.exec_module(module)
    return module


def export() -> int:
    mod = load_app()
    client = mod.app.test_client()
    posts = mod.load_posts()

    # 有文章被跳过时不要静默导出：少一篇文章 = 少一个详情页 = 少若干标签页，
    # 线上页面数和 README 里的数字都会对不上。
    skipped = getattr(mod, "SKIPPED_POSTS", [])
    if skipped:
        print("导出中止：以下文章被跳过，请先修复再导出")
        for name, reason in skipped:
            print(f"  - {name}: {reason}")
        return 2

    tags = sorted({t for p in posts for t in p["tags"]})

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    written = []

    def dump(url: str, target: str, expect: int = 200) -> None:
        r = client.get(url)
        if r.status_code != expect:
            raise SystemExit(f"导出失败：GET {url} 返回 {r.status_code}，预期 {expect}")
        path = DIST_DIR / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.data)
        written.append(target)

    dump("/", "index.html")
    dump("/archive/", "archive/index.html")
    dump("/about/", "about/index.html")
    for post in posts:
        dump(f"/post/{post['slug']}/", f"post/{post['slug']}/index.html")
    for tag in tags:
        dump(f"/tag/{tag}/", f"tag/{tag}/index.html")
    dump("/__404__/", "404.html", expect=404)

    shutil.copytree(STATIC_DIR, DIST_DIR / "static")

    # ---- 自检：页面里引用的本地绝对路径必须都能落到真实文件 ----
    refs = set()
    for f in DIST_DIR.rglob("*.html"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        refs |= set(re.findall(r'(?:href|src)="(/[^"#?]*)"', text))

    missing = []
    for ref in sorted(refs):
        rel = urllib.parse.unquote(ref).lstrip("/")
        target = DIST_DIR / rel / "index.html" if ref.endswith("/") else DIST_DIR / rel
        if not target.exists():
            missing.append(ref)

    total = sum(1 for p in DIST_DIR.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in DIST_DIR.rglob("*") if p.is_file())

    print(f"已导出 {len(written)} 个页面 + static/，共 {total} 个文件，{size / 1024:.0f} KB")
    print(f"页面内本地引用 {len(refs)} 个，缺失 {len(missing)} 个")
    if missing:
        for m in missing:
            print("  缺失:", m)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(export())
