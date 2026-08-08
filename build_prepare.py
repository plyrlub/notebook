#!/usr/bin/env python3
"""MkDocs 构建准备脚本（GitHub Actions 调用）：
把 main 分支的中文文件名笔记复制为英文文件名到 docs/ 目录，
并生成 mkdocs.yml（nav 显示中文标题，URL 英文）。
效果：gh-pages 分支产物 URL 全英文安全字符，内容保持中文。
"""
import os
import re
import shutil

REPO = os.path.dirname(os.path.abspath(__file__))  # 仓库根目录
SRC = os.path.join(REPO, "Java")                   # 源：中文文件名
DST = os.path.join(REPO, "docs")                   # 目标：英文文件名

# 中文文件名 → 英文文件名（URL 用）
RENAME_MAP = {
    # Tomcat 系列
    "00-Tomcat 学习笔记（总览）.md": "tomcat-overview.md",
    "01-Tomcat 系统架构与原理剖析.md": "tomcat-architecture.md",
    "02-Tomcat 服务器核心配置详解.md": "tomcat-server-config.md",
    "03-Tomcat 源码构建.md": "tomcat-source-build.md",
    "04-Tomcat 核心流程剖析.md": "tomcat-core-process.md",
    "05-Tomcat 类加载机制剖析.md": "tomcat-classloader.md",
    "06-Tomcat 类加载机制详解.md": "tomcat-classloader-deepdive.md",
    "07-Tomcat 对 HTTPS 的支持.md": "tomcat-https.md",
    "08-Tomcat 性能优化策略.md": "tomcat-performance-tuning.md",
    # 独立笔记
    "Java SPI 机制详解.md": "java-spi.md",
    "Java volatile 详解.md": "java-volatile.md",
    "Java 反射详解.md": "java-reflection.md",
    "Java GC 详解.md": "java-gc.md",
}

# 英文文件名 → 导航显示名（中文）
NAV_TITLES = {
    "tomcat-overview.md": "Tomcat 学习笔记（总览）",
    "tomcat-architecture.md": "01 系统架构与原理剖析",
    "tomcat-server-config.md": "02 服务器核心配置详解",
    "tomcat-source-build.md": "03 源码构建",
    "tomcat-core-process.md": "04 核心流程剖析",
    "tomcat-classloader.md": "05 类加载机制剖析",
    "tomcat-classloader-deepdive.md": "06 类加载机制详解",
    "tomcat-https.md": "07 对 HTTPS 的支持",
    "tomcat-performance-tuning.md": "08 性能优化策略",
    "java-spi.md": "Java SPI 机制详解",
    "java-volatile.md": "Java volatile 详解",
    "java-reflection.md": "Java 反射详解",
    "java-gc.md": "Java GC 详解",
}


def convert_links(content):
    """把 markdown 链接里的中文文件名替换为英文文件名。
    链接: [显示名](中文名.md) → [显示名](英文名.md)
    图片: ![](assets/xxx.png) 路径不变（保持目录层级）
    外部链接（无 .md 后缀或 http）不动。
    """

    def repl(m):
        display = m.group(1)
        href = m.group(2)
        # 只处理指向本地 .md 的链接
        if href.endswith(".md") and not href.startswith("http"):
            name = href.rsplit("/", 1)[-1]
            # 去除 %20 编码还原中文名
            name_raw = name.replace("%20", " ")
            if name_raw in RENAME_MAP:
                return "[%s](%s)" % (display, RENAME_MAP[name_raw])
        return m.group(0)

    # [显示](链接)
    return re.sub(r"\[([^\]]+)\]\(([^)]+\.md[^)]*)\)", repl, content)


def generate_mkdocs_yml():
    """生成 mkdocs.yml（nav 显示中文标题，URL 英文）"""
    nav_lines = []
    nav_lines.append("nav:")
    nav_lines.append("  - 主页: index.md")
    nav_lines.append("  - Java:")
    for en, title in NAV_TITLES.items():
        if not en.startswith("tomcat-"):
            nav_lines.append("    - %s: Java/%s" % (title, en))
    nav_lines.append("  - Tomcat:")
    for en, title in NAV_TITLES.items():
        if en.startswith("tomcat-"):
            nav_lines.append("    - %s: Java/tomcat/%s" % (title, en))

    mkdocs = """site_name: 笔记分享库
site_description: 个人学习笔记整理
site_url: https://plyrlub.github.io/notebook/
repo_url: https://github.com/plyrlub/notebook

theme:
  name: material
  language: zh
  palette:
    scheme: default
    primary: indigo
    accent: indigo
  features:
    - navigation.sections
    - search.suggest

markdown_extensions:
  - admonition
  - codehilite
  - toc:
      permalink: true
  - tables

%s
""" % "\n".join(nav_lines)

    with open(os.path.join(REPO, "mkdocs.yml"), "w", encoding="utf-8") as f:
        f.write(mkdocs)
    print("mkdocs.yml generated")


def prepare():
    # 1. 清理旧 docs
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    # 1.5 复制主页 index.md（nav 引用它）
    src_index = os.path.join(REPO, "index.md")
    if os.path.exists(src_index):
        shutil.copy2(src_index, os.path.join(DST, "index.md"))
        print("index.md copied to docs/")
    else:
        print("WARNING: index.md not found in repo root")

    # 2. 遍历 Java/ 目录，复制 + 重命名（保留 Java/ 目录层级）
    #    md 文件同步转换内容里的内部链接（中文名 → 英文名）
    copied = 0
    for root, dirs, files in os.walk(SRC):
        rel = os.path.relpath(root, SRC)
        # 保留 "Java" 顶层目录：docs/Java/<相对路径>
        target_dir = os.path.join(DST, "Java", rel) if rel != "." else os.path.join(DST, "Java")
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            src_path = os.path.join(root, f)
            if f in RENAME_MAP:
                dst_name = RENAME_MAP[f]
            else:
                dst_name = f  # 非笔记文件（assets 图片等）原样复制
            dst_path = os.path.join(target_dir, dst_name)
            if f.endswith(".md"):
                # 复制并转换内容中的内部链接
                content = open(src_path, encoding="utf-8").read()
                content = convert_links(content)
                with open(dst_path, "w", encoding="utf-8") as out:
                    out.write(content)
            else:
                shutil.copy2(src_path, dst_path)
            copied += 1
    print("copied %d files to docs/" % copied)

    # 3. 生成 mkdocs.yml
    generate_mkdocs_yml()


if __name__ == "__main__":
    prepare()
