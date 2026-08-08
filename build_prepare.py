#!/usr/bin/env python3
"""MkDocs 构建准备脚本（GitHub Actions 调用）：
把 main 分支的中文文件名笔记复制为英文文件名到 docs/ 目录，
并生成 mkdocs.yml（nav 显示中文标题，URL 英文）。
支持 Java/ 与 Nginx/ 两个源目录。
效果：gh-pages 分支产物 URL 全英文安全字符，内容保持中文。
"""
import os
import re
import shutil

REPO = os.path.dirname(os.path.abspath(__file__))  # 仓库根目录
DST = os.path.join(REPO, "docs")                    # 目标：英文文件名

# ============ Java：精确映射 ============
JAVA_SRC = os.path.join(REPO, "Java")

# 中文文件名 → 英文文件名（URL 用）
JAVA_RENAME_MAP = {
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
JAVA_NAV_TITLES = {
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

# ============ Nginx：通用 slug 规则 ============
NGINX_SRC = os.path.join(REPO, "Nginx")

# ============ 构建工具：Java 下二级分组（Maven/Gradle 子目录 + 00 总览）============
BUILDTOOL_SRC = os.path.join(REPO, "Java", "构建工具")
# basename → 英文 slug（构建工具 3 篇 basename 唯一）
BUILDTOOL_RENAME_MAP = {
    "00-构建工具总览（Maven vs Gradle 选型对比）.md": "buildtool-overview.md",
    "Gradle 学习笔记（总览）.md": "gradle-overview.md",
    "Maven 学习笔记（总览）.md": "maven-overview.md",
}

# ============ 其他语言：Lua 主题 ============
LUA_SRC = os.path.join(REPO, "其他语言")
LUA_RENAME_MAP = {
    "Lua 语言详解.md": "lua-guide.md",
}
LUA_NAV_TITLES = {
    "lua-guide.md": "Lua 语言详解",
}

# Nginx 子目录分类（中文目录名 → 导航分组显示名）
NGINX_DIRS = {
    "01-基础认知": "01 基础认知",
    "02-配置基础": "02 配置基础",
    "03-核心机制": "03 核心机制",
    "04-反向代理与负载均衡": "04 反向代理与负载均衡",
    "05-安全与传输": "05 安全与传输",
    "06-高级与优化": "06 高级与优化",
    "07-OpenResty与Lua插件": "07 OpenResty 与 Lua",
    "08-专题补充": "08 专题补充",
}


def nginx_slug(filename):
    """Nginx 中文文件名 → 英文 slug（nginx-NN.md）
    '01-Nginx概述与架构原理.md' → 'nginx-01.md'
    'A01-Python应用对接Nginx实战.md' → 'nginx-A01.md'
    '00-Nginx 学习笔记（总览）.md' → 'nginx-00.md'
    顶层编号文件（28-99）同规则。
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+|A\d+)-", base)
    if m:
        return "nginx-%s.md" % m.group(1)
    # 兜底：去掉中文，用 nginx- 前缀 + 原编号
    return filename


def nginx_nav_title(filename):
    """Nginx 英文 slug → 中文导航标题（用原中文文件名去编号前缀）"""
    return os.path.splitext(filename)[0]


def convert_links(content, rename_map, base_dir=""):
    """把 markdown 链接里的中文文件名替换为英文文件名。
    链接: [显示名](中文名.md) → [显示名](英文名.md)
    支持带路径前缀: [显示名](Java/中文名.md) → [显示名](Java/英文名.md)
    图片: ![](assets/xxx.png) 路径不变（保持目录层级）
    外部链接（无 .md 后缀或 http）不动。
    """

    def repl(m):
        display = m.group(1)
        href = m.group(2)
        # 只处理指向本地 .md 的链接
        if href.endswith(".md") or (".md#" in href):
            path, _, name = href.rpartition("/")
            # 去除 %20 编码还原中文名
            name_raw = name.split("#")[0].replace("%20", " ")
            if name_raw in rename_map:
                en = rename_map[name_raw]
                # 保持原路径前缀（如果链接带 Java/ 等前缀）
                if path:
                    return "[%s](%s/%s)" % (display, path, en)
                return "[%s](%s)" % (display, en)
        return m.group(0)

    # [显示](链接)
    return re.sub(r"\[([^\]]+)\]\(([^)]+\.md[^)]*)\)", repl, content)


def generate_mkdocs_yml(java_renamed, nginx_renamed, lua_renamed):
    """生成 mkdocs.yml（nav 两级折叠：主题 → 子域分组 → 笔记，默认收起）"""
    nav_lines = []
    nav_lines.append("nav:")
    nav_lines.append("  - 主页: index.md")

    # ===== 其他语言主题：Lua =====
    nav_lines.append("  - 其他语言:")
    nav_lines.append("    - Lua:")
    if lua_renamed:
        for en, cn in sorted(lua_renamed.get(".", {}).items()):
            title = LUA_NAV_TITLES.get(en, cn)
            nav_lines.append("      - %s: 其他语言/%s" % (title, en))

    # ===== Java 主题：两级折叠（核心机制 / JVM / 框架含 Tomcat）=====
    nav_lines.append("  - Java:")

    # Java 核心机制（SPI / volatile / 反射）
    nav_lines.append("    - Java 核心机制:")
    for en in ["java-spi.md", "java-volatile.md", "java-reflection.md"]:
        if en in JAVA_NAV_TITLES:
            nav_lines.append("      - %s: Java/%s" % (JAVA_NAV_TITLES[en], en))

    # JVM
    nav_lines.append("    - JVM:")
    if "java-gc.md" in JAVA_NAV_TITLES:
        nav_lines.append("      - %s: Java/%s" % (JAVA_NAV_TITLES["java-gc.md"], "java-gc.md"))

    # Java 框架（含 Tomcat）
    nav_lines.append("    - Java 框架:")
    for en in ["tomcat-overview.md", "tomcat-architecture.md", "tomcat-server-config.md",
               "tomcat-source-build.md", "tomcat-core-process.md", "tomcat-classloader.md",
               "tomcat-classloader-deepdive.md", "tomcat-https.md", "tomcat-performance-tuning.md"]:
        if en in JAVA_NAV_TITLES:
            nav_lines.append("      - %s: Java/tomcat/%s" % (JAVA_NAV_TITLES[en], en))

    # Java 构建工具（Maven/Gradle + 00 总览）
    nav_lines.append("    - 构建工具:")
    nav_lines.append("      - 构建工具总览（Maven vs Gradle 选型）: Java/构建工具/buildtool-overview.md")
    nav_lines.append("      - Gradle 学习笔记（总览）: Java/构建工具/Gradle/gradle-overview.md")
    nav_lines.append("      - Maven 学习笔记（总览）: Java/构建工具/Maven/maven-overview.md")

    # ===== 服务器主题：Nginx（含 01-08 子分组）=====
    nav_lines.append("  - 服务器:")
    nav_lines.append("    - Nginx:")
    # Nginx 顶层文件（00 总览 + 28-99）
    top_files = nginx_renamed.get(".", {})
    for en, cn in sorted(top_files.items()):
        nav_lines.append("      - %s: Nginx/%s" % (cn, en))
    # Nginx 子目录分组（01-08）
    for dir_cn, dir_display in NGINX_DIRS.items():
        files = nginx_renamed.get(dir_cn, {})
        if not files:
            continue
        nav_lines.append("      - %s:" % dir_display)
        for en, cn in sorted(files.items()):
            nav_lines.append("        - %s: Nginx/%s/%s" % (cn, dir_cn, en))

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
    - navigation.collapse
    - navigation.sections
    - search.suggest

markdown_extensions:
  - admonition
  - codehilite
  - nl2br
  - toc:
      permalink: true
  - tables

%s
""" % "\n".join(nav_lines)

    with open(os.path.join(REPO, "mkdocs.yml"), "w", encoding="utf-8") as f:
        f.write(mkdocs)
    print("mkdocs.yml generated")


def prepare_source(src_dir, dst_sub, rename_map, convert, exclude_dirs=None):
    """通用：遍历源目录，复制 + 重命名 + 转换链接。
    src_dir: Java/ 或 Nginx/ 或 Java/构建工具/
    dst_sub: docs 下的子目录名（Java / Nginx / Java/构建工具）
    rename_map: 中文名→英文名映射（Nginx 用 nginx_slug 生成）
    convert: 是否转换内部链接
    exclude_dirs: 需要跳过的子目录名列表（如 Java 下独立处理的"构建工具"）
    返回 {相对目录: {英文名: 中文显示名}}
    """
    exclude_dirs = exclude_dirs or []
    renamed = {}
    copied = 0
    for root, dirs, files in os.walk(src_dir):
        # 跳过需独立处理的子目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        rel = os.path.relpath(root, src_dir)
        target_dir = os.path.join(DST, dst_sub, rel) if rel != "." else os.path.join(DST, dst_sub)
        os.makedirs(target_dir, exist_ok=True)
        if rel == ".":
            rel_key = "."
        else:
            rel_key = rel
        renamed.setdefault(rel_key, {})
        for f in files:
            src_path = os.path.join(root, f)
            if f in rename_map:
                dst_name = rename_map[f]
            else:
                dst_name = f  # assets 图片等原样复制
            dst_path = os.path.join(target_dir, dst_name)
            if f.endswith(".md") and convert:
                content = open(src_path, encoding="utf-8").read()
                content = convert_links(content, rename_map)
                with open(dst_path, "w", encoding="utf-8") as out:
                    out.write(content)
            else:
                shutil.copy2(src_path, dst_path)
            renamed[rel_key][dst_name] = nginx_nav_title(f) if dst_sub == "Nginx" else f
            copied += 1
    print("copied %d files to docs/%s" % (copied, dst_sub))
    return renamed


def prepare():
    # 1. 清理旧 docs
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    # 1.0 先构建 Nginx 映射（index.md 转换需要用到）
    nginx_map = {}
    if os.path.exists(NGINX_SRC):
        for root, dirs, files in os.walk(NGINX_SRC):
            for f in files:
                if f.endswith(".md"):
                    nginx_map[f] = nginx_slug(f)

    # 1.5 复制主页 index.md（nav 引用它），并转换内部链接
    src_index = os.path.join(REPO, "index.md")
    if os.path.exists(src_index):
        content = open(src_index, encoding="utf-8").read()
        # index.md 里可能引用 Java/Nginx/构建工具/Lua 笔记，用合并映射转换
        merged_map = dict(JAVA_RENAME_MAP)
        merged_map.update(nginx_map)
        merged_map.update(BUILDTOOL_RENAME_MAP)
        merged_map.update(LUA_RENAME_MAP)
        content = convert_links(content, merged_map)
        with open(os.path.join(DST, "index.md"), "w", encoding="utf-8") as out:
            out.write(content)
        print("index.md copied to docs/")
    else:
        print("WARNING: index.md not found in repo root")

    # 2. Java 目录（排除独立处理的"构建工具"子目录）
    if os.path.exists(JAVA_SRC):
        prepare_source(JAVA_SRC, "Java", JAVA_RENAME_MAP, convert=True, exclude_dirs=["构建工具"])
    else:
        print("WARNING: Java/ dir not found")

    # 2.5 构建工具目录（Java 下二级分组）
    if os.path.exists(BUILDTOOL_SRC):
        prepare_source(BUILDTOOL_SRC, "Java/构建工具", BUILDTOOL_RENAME_MAP, convert=True)
    else:
        print("WARNING: Java/构建工具 dir not found")

    # 3. Nginx 目录（通用 slug 规则）
    if os.path.exists(NGINX_SRC):
        nginx_renamed = prepare_source(NGINX_SRC, "Nginx", nginx_map, convert=True)
    else:
        print("WARNING: Nginx/ dir not found")
        nginx_renamed = {}

    # 3.5 其他语言目录（Lua）— 需合并 Nginx 映射（Lua 笔记链接指向 Nginx 系列）
    if os.path.exists(LUA_SRC):
        lua_merge_map = dict(LUA_RENAME_MAP)
        lua_merge_map.update(nginx_map)  # 让 Lua 里的 Nginx 链接也能转英文
        lua_renamed = prepare_source(LUA_SRC, "其他语言", lua_merge_map, convert=True)
    else:
        print("WARNING: 其他语言/ dir not found")
        lua_renamed = {}

    # 4. 生成 mkdocs.yml
    generate_mkdocs_yml(None, nginx_renamed, lua_renamed)


if __name__ == "__main__":
    prepare()