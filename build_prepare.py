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
    "00-Tomcat总览.md": "tomcat-overview.md",
    "01-Tomcat系统架构与原理剖析.md": "tomcat-architecture.md",
    "02-Tomcat服务器核心配置详解.md": "tomcat-server-config.md",
    "03-Tomcat源码构建.md": "tomcat-source-build.md",
    "04-Tomcat核心流程剖析.md": "tomcat-core-process.md",
    "05-Tomcat类加载机制剖析.md": "tomcat-classloader.md",
    "06-Tomcat类加载机制详解.md": "tomcat-classloader-deepdive.md",
    "07-Tomcat对HTTPS的支持.md": "tomcat-https.md",
    "08-Tomcat性能优化策略.md": "tomcat-performance-tuning.md",
    # 独立笔记
    "Java SPI机制详解.md": "java-spi.md",
    "Java volatile详解.md": "java-volatile.md",
    "Java反射详解.md": "java-reflection.md",
    "Java GC详解.md": "java-gc.md",
}

# 英文文件名 → 导航显示名（中文）
JAVA_NAV_TITLES = {
    "tomcat-overview.md": "Tomcat总览",
    "tomcat-architecture.md": "01 系统架构与原理剖析",
    "tomcat-server-config.md": "02 服务器核心配置详解",
    "tomcat-source-build.md": "03 源码构建",
    "tomcat-core-process.md": "04 核心流程剖析",
    "tomcat-classloader.md": "05 类加载机制剖析",
    "tomcat-classloader-deepdive.md": "06 类加载机制详解",
    "tomcat-https.md": "07 对 HTTPS 的支持",
    "tomcat-performance-tuning.md": "08 性能优化策略",
    "java-spi.md": "Java SPI机制详解",
    "java-volatile.md": "Java volatile详解",
    "java-reflection.md": "Java反射详解",
    "java-gc.md": "Java GC详解",
}

# ============ Nginx：通用 slug 规则 ============
NGINX_SRC = os.path.join(REPO, "Nginx")

# ============ 构建工具：Java 下二级分组（Maven/Gradle 子目录 + 00 总览）============
BUILDTOOL_SRC = os.path.join(REPO, "Java", "构建工具")
# basename → 英文 slug
BUILDTOOL_RENAME_MAP = {
    "00-构建工具总览·Maven & Gradle选型对比.md": "buildtool-overview.md",
    # Gradle 系列（拆分 5 篇）
    "01-Gradle核心机制详解.md": "gradle-01.md",
    "02-Gradle Task与生命周期详解.md": "gradle-02.md",
    "03-Gradle依赖管理详解.md": "gradle-03.md",
    "04-Gradle多项目构建详解.md": "gradle-04.md",
    "05-Gradle性能优化详解.md": "gradle-05.md",
    # Maven 系列（4 篇，00 总览已并入构建工具总览）
    "01-依赖与仓库.md": "maven-01.md",
    "02-生命周期与插件.md": "maven-02.md",
    "03-私服与测试.md": "maven-03.md",
    "04-版本与灵活构建.md": "maven-04.md",
}

# ============ 前后端缓存：通用技术下主题（NN- 系列）============
CACHE_SRC = os.path.join(REPO, "通用技术", "前后端缓存")
CACHE_RENAME_MAP = {
    "00-前后端缓存总览.md": "cache-00.md",
    "01-客户端缓存详解.md": "cache-01.md",
    "02-协商缓存详解.md": "cache-02.md",
    "03-后端缓存补充·缓存更新策略.md": "cache-03.md",
    "04-后端缓存补充·CDN协同.md": "cache-04.md",
    "05-后端缓存补充·缓存监控.md": "cache-05.md",
}
CACHE_NAV_TITLES = {
    "cache-00.md": "前后端缓存总览",
    "cache-01.md": "客户端缓存详解",
    "cache-02.md": "协商缓存详解",
    "cache-03.md": "补充·缓存更新策略",
    "cache-04.md": "补充·CDN协同",
    "cache-05.md": "补充·缓存监控",
}

# ============ 软件保护：通用技术下主题（NN- 系列）============
SPROTECT_SRC = os.path.join(REPO, "通用技术", "软件保护")
SPROTECT_RENAME_MAP = {
    "00-软件保护总览.md": "protect-00.md",
    "01-代码混淆详解.md": "protect-01.md",
    "02-License授权详解.md": "protect-02.md",
}
SPROTECT_NAV_TITLES = {
    "protect-00.md": "软件保护总览",
    "protect-01.md": "代码混淆详解",
    "protect-02.md": "License授权详解",
}

# ============ 其他语言：Lua 主题（NN- 子目录系列）============
LUA_SRC = os.path.join(REPO, "其他语言")
# Lua 子目录（中文目录名 → 导航分组显示名）
LUA_DIRS = {
    "Lua": "Lua",
}

# ============ Linux：服务器主题（NN- 系列）============
LINUX_SRC = os.path.join(REPO, "Linux")


def linux_slug(filename):
    """Linux 中文文件名 → 英文 slug（linux-NN.md）
    '00-Linux总览.md' → 'linux-00.md'
    '01-用户管理与登录授权.md' → 'linux-01.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "linux-%s.md" % m.group(1)
    return filename


def linux_nav_title(filename):
    """Linux 英文 slug → 中文导航标题（原中文文件名）"""
    return os.path.splitext(filename)[0]

def lua_slug(filename):
    """Lua 中文文件名 → 英文 slug（lua-NN.md）
    '00-Lua 总览.md' → 'lua-00.md'
    '01-基础语法.md' → 'lua-01.md'
    '11-三方资源（MySQL与Redis）.md' → 'lua-11.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "lua-%s.md" % m.group(1)
    return filename

def lua_nav_title(filename):
    """Lua 英文 slug → 中文导航标题（原中文文件名）"""
    return os.path.splitext(filename)[0]

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


# ============ 分布式：核心原理（根目录 dist-NN）+ ZooKeeper 子目录（zk-NN）============
DIST_SRC = os.path.join(REPO, "分布式")


def dist_slug(filename):
    """分布式根目录中文文件名 → 英文 slug（dist-NN.md）
    '00-分布式基础总览.md' → 'dist-00.md'
    '06-负载均衡详解.md' → 'dist-06.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "dist-%s.md" % m.group(1)
    return filename


def zk_slug(filename):
    """Zookeeper 子目录中文文件名 → 英文 slug（zk-NN.md）
    '00-ZooKeeper总览.md' → 'zk-00.md'
    '09-应用场景与分布式协同.md' → 'zk-09.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "zk-%s.md" % m.group(1)
    return filename


def dist_nav_title(filename):
    """分布式英文 slug → 中文导航标题（原中文文件名）"""
    return os.path.splitext(filename)[0]


# ============ CI-CD：主章节（根目录 ci-NN）+ 补充专题（子目录 sp-NN）============
CICD_SRC = os.path.join(REPO, "CI-CD")

# CI-CD 根目录无编号文件 → 英文 slug（单独映射）
CICD_ROOT_MAP = {
    "00-CI-CD 学习笔记（总览）.md": "cicd-00.md",
    "我的实践记录.md": "cicd-practice.md",
    "新团队最佳实践方案.md": "cicd-newteam.md",
    "老项目改进方案.md": "cicd-legacy.md",
    "面试题集锦.md": "cicd-interview.md",
    "踩坑经验集锦.md": "cicd-pitfalls.md",
    "补充专题.md": "cicd-topics.md",
}


def cicd_slug(filename):
    """CI-CD 根目录中文文件名 → 英文 slug（ci-NN.md）
    '01-认知地基.md' → 'ci-01.md'
    '10-进阶与工程化.md' → 'ci-10.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "ci-%s.md" % m.group(1)
    return CICD_ROOT_MAP.get(filename, filename)


def sp_slug(filename):
    """CI-CD 补充专题子目录中文文件名 → 英文 slug（sp-NN.md）
    'S1-Secret管理.md' → 'sp-01.md'
    'S12-CICD开源设施部署指南.md' → 'sp-12.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^S(\d+)-", base)
    if m:
        return "sp-%02d.md" % int(m.group(1))
    return filename


def cicd_nav_title(filename):
    """CI-CD 英文 slug → 中文导航标题（原中文文件名）"""
    return os.path.splitext(filename)[0]


def build_dist_map():
    """构建分布式全文件名 → 英文 slug 映射（00 总览 + 核心原理 dist-NN，Zookeeper 子目录 zk-NN）"""
    dist_map = {}
    if os.path.exists(DIST_SRC):
        for root, dirs, files in os.walk(DIST_SRC):
            for f in files:
                if f.endswith(".md"):
                    rel = os.path.relpath(root, DIST_SRC)
                    dist_map[f] = zk_slug(f) if rel == "Zookeeper" else dist_slug(f)
    return dist_map


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



def _java_dir_title(rel):
    """相对路径 → 导航显示标题（取最后一段）"""
    return rel.split(os.sep)[-1]


def _java_md_title(en, cn):
    return cn[:-3] if cn.endswith(".md") else cn


def _append_java_full_nav(lines, renamed):
    """由 java_renamed {rel: {dst_en: cn}} 渲染整个 Java 导航（多级缩进）。
    排除 assets 目录与其图片，保证缩进随目录层级递增。
    """
    # 只保留非根、非 assets 的目录
    rels = [r for r in renamed.keys() if r != "." and not r.startswith("assets") and os.sep + "assets" not in r]
    # 过滤每个 rel 下的图片/非 md（assets 已排除，这里再保险过滤 png 等）
    def md_files(files):
        return {en: cn for en, cn in files.items() if en.endswith(".md") or cn.endswith(".md") or "." not in os.path.splitext(en)[1] or en.lower().endswith((".md",".mermaid")) if en.endswith(".md")}
    rel_items = sorted(rels, key=lambda r: (len(r.split(os.sep)), r))

    def depth_of(r):
        return len(r.split(os.sep))

    # 用栈式迭代输出：按 rel 层级，父目录先出，子目录缩进更深
    def emit(parent_prefix):
        # 找直接子项（路径前缀 == parent_prefix，且层级恰好+1）
        if parent_prefix:
            ch = [r for r in rel_items if os.path.dirname(r) == parent_prefix]
        else:
            ch = [r for r in rel_items if os.sep not in r]
        ch.sort()
        for cr in ch:
            files = md_files(renamed.get(cr, {}))
            pad = "  " * (depth_of(cr) + 2)
            lines.append("%s- %s:" % (pad, _java_dir_title(cr)))
            for en, cn in sorted(files.items()):
                title = _java_md_title(en, cn)
                lines.append("%s  - %s: Java/%s/%s" % (pad, title, cr, en))
            emit(cr)   # 递归子目录

    emit("")


def generate_mkdocs_yml(java_renamed, nginx_renamed, lua_renamed, cache_renamed, dist_renamed=None, cicd_renamed=None, sprotect_renamed=None, linux_renamed=None, spring_renamed=None, springboot_renamed=None):
    """生成 mkdocs.yml（nav 两级折叠：主题 → 子域分组 → 笔记，默认收起）"""
    nav_lines = []
    nav_lines.append("nav:")
    nav_lines.append("  - 主页: index.md")

    # ===== 分布式主题：核心原理 + ZooKeeper 子目录 =====
    if dist_renamed:
        nav_lines.append("  - 分布式:")
        # 核心原理组 = 00 总览(根目录) + 核心原理 子目录(dist-NN)
        core_files = {}
        for key in (".", "核心原理"):
            core_files.update(dist_renamed.get(key, {}))
        if core_files:
            nav_lines.append("    - 核心原理:")
            # 00 总览排最前(文件名 dist-00 自然最前)
            for en, cn in sorted(core_files.items()):
                prefix = "分布式/核心原理/" if en.startswith("dist-") and en != "dist-00.md" else "分布式/"
                nav_lines.append("      - %s: %s%s" % (cn, prefix, en))
        # ZooKeeper 子目录（zk-NN）
        zk_files = dist_renamed.get("Zookeeper", {})
        if zk_files:
            nav_lines.append("    - ZooKeeper:")
            for en, cn in sorted(zk_files.items()):
                nav_lines.append("      - %s: 分布式/Zookeeper/%s" % (cn, en))

    # ===== 通用技术主题：前后端缓存 =====
    nav_lines.append("  - 通用技术:")
    nav_lines.append("    - 前后端缓存:")
    if cache_renamed:
        for en, cn in sorted(cache_renamed.get(".", {}).items()):
            title = CACHE_NAV_TITLES.get(en, cn)
            nav_lines.append("      - %s: 通用技术/前后端缓存/%s" % (title, en))

    # ===== 通用技术主题：软件保护 =====
    nav_lines.append("    - 软件保护:")
    if sprotect_renamed:
        for en, cn in sorted(sprotect_renamed.get(".", {}).items()):
            title = SPROTECT_NAV_TITLES.get(en, cn)
            nav_lines.append("      - %s: 通用技术/软件保护/%s" % (title, en))

    # ===== 其他语言主题：Lua（NN- 子目录系列）=====
    nav_lines.append("  - 其他语言:")
    if lua_renamed:
        for dir_cn, dir_display in LUA_DIRS.items():
            files = lua_renamed.get(dir_cn, {})
            if not files:
                continue
            nav_lines.append("    - %s:" % dir_display)
            for en, cn in sorted(files.items()):
                nav_lines.append("      - %s: 其他语言/%s/%s" % (cn, dir_cn, en))

    # ===== Java 主题：两级折叠（核心机制 / JVM / 框架含 Tomcat）=====
    nav_lines.append("  - Java:")
    if java_renamed:
        _append_java_full_nav(nav_lines, java_renamed)

    # ===== 服务器主题：Nginx（含 01-08 子分组）=====
    nav_lines.append("  - 服务器:")
    nav_lines.append("    - Linux:")
    if linux_renamed:
        for en, cn in sorted(linux_renamed.get(".", {}).items()):
            title = cn[:-3] if cn.endswith(".md") else cn
            nav_lines.append("      - %s: Linux/%s" % (title, en))
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

    # ===== DevOps 主题：CI/CD（主章节 ci-NN + 补充专题 sp-NN）=====
    nav_lines.append("  - DevOps:")
    nav_lines.append("    - CI/CD:")
    if cicd_renamed:
        # 根目录主章节 + 实战文档（ci-NN / cicd-*）
        top_files = cicd_renamed.get(".", {})
        for en, cn in sorted(top_files.items()):
            nav_lines.append("      - %s: CI-CD/%s" % (cn, en))
        # 补充专题子目录（sp-NN）
        sp_files = cicd_renamed.get("补充专题", {})
        if sp_files:
            nav_lines.append("      - 补充专题:")
            for en, cn in sorted(sp_files.items()):
                nav_lines.append("        - %s: CI-CD/补充专题/%s" % (cn, en))

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
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.tabbed:
      alternate_style: true
  - nl2br
  - toc:
      permalink: true
  - tables

extra_javascript:
  - javascripts/mermaid.mjs

%s
""" % "\n".join(nav_lines)

    with open(os.path.join(REPO, "mkdocs.yml"), "w", encoding="utf-8") as f:
        f.write(mkdocs)
    print("mkdocs.yml generated")


def prepare_source(src_dir, dst_sub, rename_map, convert, exclude_dirs=None, convert_map=None):
    """通用：遍历源目录，复制 + 重命名 + 转换链接。
    src_dir: Java/ 或 Nginx/ 或 Java/构建工具/
    dst_sub: docs 下的子目录名（Java / Nginx / Java/构建工具）
    rename_map: 中文名→英文名映射（Nginx 用 nginx_slug 生成）
    convert: 是否转换内部链接
    exclude_dirs: 需要跳过的子目录名列表（如 Java 下独立处理的"构建工具"）
    convert_map: 若提供，链接转换用此映射（跨主题链接）而非 rename_map
    返回 {相对目录: {英文名: 中文显示名}}
    """
    exclude_dirs = exclude_dirs or []
    renamed = {}
    copied = 0
    conv_map = convert_map if convert_map else rename_map
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
                content = convert_links(content, conv_map)
                with open(dst_path, "w", encoding="utf-8") as out:
                    out.write(content)
            else:
                shutil.copy2(src_path, dst_path)
            renamed[rel_key][dst_name] = cicd_nav_title(f) if dst_sub == "CI-CD" else (nginx_nav_title(f) if dst_sub in ("Nginx", "其他语言", "分布式") else f)
            copied += 1
    print("copied %d files to docs/%s" % (copied, dst_sub))
    return renamed


# ============ Spring 三件套：spring（Spring/SpringMVC）+ springboot（重点）子目录 ============
SPRING_SRC = os.path.join(REPO, "Java", "框架", "spring")
SPRINGBOOT_SRC = os.path.join(REPO, "Java", "框架", "springboot")


def spring_slug(filename):
    """spring 子目录中文文件名 → 英文 slug（spring-NN.md）
    '00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md' → 'spring-00.md'
    '04-Spring核心·AOP详解.md' → 'spring-04.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "spring-%s.md" % m.group(1)
    return filename





# ============ 新 Java 规范结构：通用 prefix slug ============
# 各主题英文 URL 前缀（新 11 主题：JDK基础库 / JVM / 三方库 / 设计模式 /
# 测试 / 微服务 / 中间件 / 代码片段 / 框架下多子主题）。
JAVA_PREFIX_MAP = {
    "JDK基础库": "jdk",
    "JVM": "jvm",
    "三方库": "lib",
    "设计模式": "dp",
    "测试": "test",
    "微服务": "ms",
    "中间件": "mid",
    "代码片段": "snippet",
}
FRAMEWORK_PREFIX_MAP = {
    "安全": "security",
    "定时任务": "sched",
    "数据访问层": "orm",
    "通用实践": "common",
    "服务通信": "rpc",
    "网络底座": "net",
}
FRAMEWORK_SUB_PREFIX_MAP = {
    ("数据访问层", "分库分表"): "shard",
    ("网络底座", "网络通信"): "nio",
    ("网络底座", "Web服务器"): "web",
}


def java_subdir_slug(filename, prefix):
    """通用编号文件名 → <prefix>-NN.md；无编号则用中文名（MkDocs 兼容 URL）。"""
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-+", base)
    if m:
        return "%s-%s.md" % (prefix, m.group(1))
    return filename


def build_java_full_map():
    """遍历分享区 Java/ 全目录，生成「中文文件名 → 英文 slug」映射。
    规则：
      - 框架/spring → spring-NN（复用 spring_slug）
      - 框架/springboot → sb-NN（复用 sb_slug）
      - 构建工具 → 沿用 BUILDTOOL_RENAME_MAP
      - 其余目录按 JAVA_PREFIX_MAP / FRAMEWORK_PREFIX_MAP 前缀生成
    """
    m = {}
    if os.path.exists(SPRING_SRC):
        for f in os.listdir(SPRING_SRC):
            if f.endswith(".md"):
                m[f] = spring_slug(f)
    if os.path.exists(SPRINGBOOT_SRC):
        for f in os.listdir(SPRINGBOOT_SRC):
            if f.endswith(".md"):
                m[f] = sb_slug(f)
    m.update(BUILDTOOL_RENAME_MAP)
    java_root = os.path.join(REPO, "Java")
    if not os.path.isdir(java_root):
        return m
    for root, dirs, files in os.walk(java_root):
        dirs[:] = [d for d in dirs if d != "assets"]
        rel = os.path.relpath(root, java_root)
        parts = [] if rel == "." else rel.split(os.sep)
        for f in files:
            if not f.endswith(".md") or f in m:
                continue
            prefix = None
            if len(parts) >= 1 and parts[0] in FRAMEWORK_PREFIX_MAP:
                if len(parts) == 1:
                    prefix = FRAMEWORK_PREFIX_MAP[parts[0]]
                elif tuple(parts[:2]) in FRAMEWORK_SUB_PREFIX_MAP:
                    prefix = FRAMEWORK_SUB_PREFIX_MAP[tuple(parts[:2])]
            elif len(parts) >= 1 and parts[0] in JAVA_PREFIX_MAP:
                prefix = JAVA_PREFIX_MAP[parts[0]]
            if prefix:
                m[f] = java_subdir_slug(f, prefix)
    return m

def sb_slug(filename):
    """springboot 子目录中文文件名 → 英文 slug（sb-NN.md）
    '01-SpringBoot启动原理与自动装配详解.md' → 'sb-01.md'
    '08-Spring WebFlux响应式编程详解.md' → 'sb-08.md'
    """
    base = os.path.splitext(filename)[0]
    m = re.match(r"^(\d+)-", base)
    if m:
        return "sb-%s.md" % m.group(1)
    return filename


def build_spring_map():
    """构建 spring + springboot 全文件名 → 英文 slug 映射（两子目录合并，链接可跨域互转）"""
    spring_map = {}
    if os.path.exists(SPRING_SRC):
        for f in os.listdir(SPRING_SRC):
            if f.endswith(".md"):
                spring_map[f] = spring_slug(f)
    if os.path.exists(SPRINGBOOT_SRC):
        for f in os.listdir(SPRINGBOOT_SRC):
            if f.endswith(".md"):
                spring_map[f] = sb_slug(f)
    return spring_map


def prepare():
    # 1. 清理旧 docs
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    # 1.0 拷贝自定义 Mermaid JS（放大图内文字）到 docs/javascripts/
    mermaid_src = os.path.join(REPO, "custom-mermaid.mjs")
    mermaid_dst_dir = os.path.join(DST, "javascripts")
    os.makedirs(mermaid_dst_dir, exist_ok=True)
    if os.path.exists(mermaid_src):
        shutil.copy2(mermaid_src, os.path.join(mermaid_dst_dir, "mermaid.mjs"))
        print("copied custom-mermaid.mjs -> docs/javascripts/mermaid.mjs")

    # 1.1 先构建 Nginx 映射（index.md 转换需要用到）
    nginx_map = {}
    if os.path.exists(NGINX_SRC):
        for root, dirs, files in os.walk(NGINX_SRC):
            for f in files:
                if f.endswith(".md"):
                    nginx_map[f] = nginx_slug(f)

    # 1.2 构建 Lua 映射（子目录系列 → lua-NN.md）+ 合并 Nginx（Lua 内链接指向 Nginx）
    lua_map = {}
    lua_merge_map = {}
    if os.path.exists(LUA_SRC):
        for root, dirs, files in os.walk(LUA_SRC):
            for f in files:
                if f.endswith(".md"):
                    lua_map[f] = lua_slug(f)
        lua_merge_map = dict(lua_map)
        lua_merge_map.update(nginx_map)  # 让 Lua 里的 Nginx 链接也能转英文

    # 1.5 复制主页 index.md（nav 引用它），并转换内部链接
    java_full_map = build_java_full_map()  # 全量 Java 映射（供 index 与后续转换）
    src_index = os.path.join(REPO, "index.md")
    if os.path.exists(src_index):
        content = open(src_index, encoding="utf-8").read()
        # index.md 里可能引用 Java/Nginx/构建工具/Lua/分布式/CI-CD 笔记，用合并映射转换
        merged_map = dict(java_full_map)
        merged_map.update(nginx_map)
        merged_map.update(BUILDTOOL_RENAME_MAP)
        merged_map.update(lua_map)
        merged_map.update(CACHE_RENAME_MAP)
        merged_map.update(SPROTECT_RENAME_MAP)
        if os.path.exists(LINUX_SRC):
            for f in os.listdir(LINUX_SRC):
                if f.endswith(".md"):
                    merged_map[f] = linux_slug(f)
        if os.path.exists(DIST_SRC):
            dist_map = build_dist_map()
            merged_map.update(dist_map)
        if os.path.exists(CICD_SRC):
            for root, dirs, files in os.walk(CICD_SRC):
                for f in files:
                    if f.endswith(".md"):
                        rel = os.path.relpath(root, CICD_SRC)
                        merged_map[f] = sp_slug(f) if rel != "." else cicd_slug(f)
        content = convert_links(content, merged_map)
        with open(os.path.join(DST, "index.md"), "w", encoding="utf-8") as out:
            out.write(content)
        print("index.md copied to docs/")
    else:
        print("WARNING: index.md not found in repo root")

    # 2. Java 全量镜像（含 spring/springboot/构建工具 · 全部新主题通用 slug）
    java_full_map = build_java_full_map()
    # 跨主题链接转换：合并所有已存在主题的英文映射，使 Java 内指向
    # 分布式 / 通用技术/软件保护 / 前后端缓存 / Nginx / Lua / CI-CD 的链接可转英文
    java_convert_map = dict(java_full_map)
    java_convert_map.update(nginx_map)
    java_convert_map.update(lua_map)
    if os.path.exists(DIST_SRC):
        java_convert_map.update(build_dist_map())
    java_convert_map.update(CACHE_RENAME_MAP)
    java_convert_map.update(SPROTECT_RENAME_MAP)
    if os.path.exists(LINUX_SRC):
        for f in os.listdir(LINUX_SRC):
            if f.endswith(".md"):
                java_convert_map[f] = linux_slug(f)
    if os.path.exists(CICD_SRC):
        for root, dirs, files in os.walk(CICD_SRC):
            for f in files:
                if f.endswith(".md"):
                    rel = os.path.relpath(root, CICD_SRC)
                    java_convert_map[f] = sp_slug(f) if rel != "." else cicd_slug(f)
    java_renamed = {}
    if os.path.exists(JAVA_SRC):
        java_renamed = prepare_source(JAVA_SRC, "Java", java_full_map, convert=True, convert_map=java_convert_map)
    else:
        print("WARNING: Java/ dir not found")
    spring_renamed = {".": java_renamed.get("spring", {})}
    springboot_renamed = {".": java_renamed.get("springboot", {})}

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

    # 3.5 其他语言目录（Lua）— 用 lua_slug 映射（已合并 Nginx 链接）
    if os.path.exists(LUA_SRC):
        lua_renamed = prepare_source(LUA_SRC, "其他语言", lua_merge_map, convert=True)
    else:
        print("WARNING: 其他语言/ dir not found")
        lua_renamed = {}

    # 3.6 通用技术/前后端缓存（NN- 系列）— 合并 Nginx 映射（缓存篇链接指向 Nginx 缓存机制）
    if os.path.exists(CACHE_SRC):
        cache_merge_map = dict(CACHE_RENAME_MAP)
        cache_merge_map.update(nginx_map)
        cache_renamed = prepare_source(CACHE_SRC, "通用技术/前后端缓存", cache_merge_map, convert=True)
    else:
        print("WARNING: 通用技术/前后端缓存 dir not found")
        cache_renamed = {}

    # 3.6.5 通用技术/软件保护（NN- 系列）— 合并缓存/Nginx/Java 映射（混淆篇链接指向 Java 反射等）
    sprotect_renamed = {}
    if os.path.exists(SPROTECT_SRC):
        sprotect_merge_map = dict(SPROTECT_RENAME_MAP)
        sprotect_merge_map.update(nginx_map)
        sprotect_merge_map.update(CACHE_RENAME_MAP)
        sprotect_merge_map.update(java_full_map)
        sprotect_renamed = prepare_source(SPROTECT_SRC, "通用技术/软件保护", sprotect_merge_map, convert=True)
    else:
        print("WARNING: 通用技术/软件保护 dir not found")

    # 3.7 分布式目录（核心原理 dist-NN + ZooKeeper 子目录 zk-NN）— 合并 Nginx 映射（ZK 篇链接指向 Nginx）
    dist_renamed = {}
    if os.path.exists(DIST_SRC):
        dist_map = build_dist_map()
        dist_merge_map = dict(dist_map)
        dist_merge_map.update(nginx_map)
        dist_renamed = prepare_source(DIST_SRC, "分布式", dist_merge_map, convert=True)
    else:
        print("WARNING: 分布式/ dir not found")

    # 3.8 CI-CD 目录（主章节 ci-NN + 补充专题 sp-NN）— 合并 Nginx 映射（Lua/S8 篇链接指向 Nginx）
    cicd_renamed = {}
    cicd_map = {}
    if os.path.exists(CICD_SRC):
        for root, dirs, files in os.walk(CICD_SRC):
            for f in files:
                if f.endswith(".md"):
                    rel = os.path.relpath(root, CICD_SRC)
                    cicd_map[f] = sp_slug(f) if rel != "." else cicd_slug(f)
        cicd_merge_map = dict(cicd_map)
        cicd_merge_map.update(nginx_map)
        cicd_renamed = prepare_source(CICD_SRC, "CI-CD", cicd_merge_map, convert=True)
    else:
        print("WARNING: CI-CD/ dir not found")

    # 3.9 Linux 目录（NN- 系列）— 合并 Nginx/CI-CD 映射（总览篇链接指向 Nginx/CI-CD）
    linux_renamed = {}
    if os.path.exists(LINUX_SRC):
        linux_map = {}
        for f in os.listdir(LINUX_SRC):
            if f.endswith(".md"):
                linux_map[f] = linux_slug(f)
        linux_merge_map = dict(linux_map)
        linux_merge_map.update(nginx_map)
        linux_merge_map.update(cicd_map if os.path.exists(CICD_SRC) else {})
        linux_renamed = prepare_source(LINUX_SRC, "Linux", linux_merge_map, convert=True)
    else:
        print("WARNING: Linux/ dir not found")

    # 4. 生成 mkdocs.yml
    generate_mkdocs_yml(java_renamed, nginx_renamed, lua_renamed, cache_renamed, dist_renamed, cicd_renamed, sprotect_renamed, linux_renamed, spring_renamed, springboot_renamed)


if __name__ == "__main__":
    prepare()