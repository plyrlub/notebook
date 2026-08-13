---
tags: [Gradle, 构建工具, 多项目, 组合构建, Composite Build, include]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具/Gradle）
归属: 01-学习/Java/构建工具/Gradle
---

# 04-Gradle多项目构建详解

> 版本基线：Gradle 8.x 为主线，标注 5.x 差异（本机实测 Gradle 5.1.1 + JDK 8）
> 受众：需要搭建/理解多模块（多项目）构建的后端开发。
> 关联笔记：[03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)、[05-Gradle性能优化详解](05-Gradle性能优化详解.md)

## 📋 总纲

1. 多项目结构（settings.gradle include）
2. 子项目间依赖
3. 根项目统一配置（subprojects / allprojects）
4. 组合构建（Composite Build）★
5. 多项目最佳实践 ★
6. 小结

## 学习目标

学完本篇你能：

1. 用 settings.gradle 的 include 声明多项目结构
2. 配置子项目间依赖（project()）
3. 用 subprojects/allprojects 统一配置共享逻辑
4. 理解组合构建（Composite Build）与多项目构建的区别
5. 遵循多项目最佳实践（避免配置陷阱）

## 前置知识

- [03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)——依赖声明基础
- [02-Gradle Task与生命周期详解](02-Gradle Task与生命周期详解.md)——理解"配置阶段全量执行"

---

## 1. 多项目结构（settings.gradle include）

```groovy
// settings.gradle
rootProject.name = 'my-project'
include 'common', 'service', 'web'    // 声明 3 个子项目
```

目录结构：
```
my-project/
├── settings.gradle
├── build.gradle            # 根项目(公共配置)
├── common/                 # 子项目
│   └── build.gradle
├── service/
│   └── build.gradle
└── web/
    └── build.gradle
```

**关键**：`include` 声明参与构建的子项目，每个子项目可有自己的 `build.gradle`。

---

## 2. 子项目间依赖

```groovy
// service/build.gradle
dependencies {
    implementation project(':common')    // 依赖 common 子项目
}
```

- 用 `project(':模块名')` 引用同构建内的其他子项目
- 子项目间用 `implementation` 控制可见性（见 [03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)）

---

## 3. 根项目统一配置（subprojects / allprojects）★

```groovy
// 根 build.gradle:所有子项目统一 Java 版本和仓库
subprojects {
    apply plugin: 'java'
    repositories {
        mavenCentral()
    }
}
```

**subprojects vs allprojects**：

| 作用域 | 作用 |
|---|---|
| `subprojects {}` | 作用于**所有子项目**（不含根项目） |
| `allprojects {}` | 作用于**根项目 + 所有子项目** |
| `project(':xxx') {}` | 作用于**指定项目** |

> ⚠️ **易错点**：`subprojects`/`allprojects` 里的配置会在**配置阶段**应用到所有项目。配置逻辑放这里会全量执行（见 #G4 踩坑），保持轻量。

---

## 4. 组合构建（Composite Build）★

多个独立构建组合在一起（如 A 项目用 B 项目的源码而非发布的 jar）：

```bash
gradle --include-build ../library-b build
```

或在 `settings.gradle` 里声明（更持久）：
```groovy
// settings.gradle 声明 includeBuild
includeBuild('../library-b')   // 引入独立构建 B
```

**多项目构建 vs 组合构建**：

| | 多项目构建 | 组合构建（Composite/Included Build） |
|---|---|---|
| 组成 | subprojects（同一 settings.gradle） | 整个独立 builds |
| 用途 | 同一仓库的多个模块 | 跨仓库/独立项目联调 |
| 改源码生效 | 是（project 依赖） | 是（includeBuild 替代发布 jar） |
| 典型场景 | 单体多模块 | 多仓库微服务、共享库联调 |

**组合构建的好处**：改 B 源码立即生效，不用先发布 jar 到仓库——多仓库微服务联调神器。

**插件组合构建**（pluginManagement.includeBuild）：
```groovy
pluginManagement {
    includeBuild("my-plugin")   // 引入本地的插件构建
    repositories {
        gradlePluginPortal()
    }
}
```

---

## 5. 多项目最佳实践 ★

1. **共享配置适度**：`subprojects` 里只放真正公共的（Java 版本/仓库），别把每个模块的特殊配置都塞进去
2. **配置逻辑轻量**：`subprojects`/`allprojects` 配置阶段全量执行，重逻辑放任务 `doLast`
3. **用 Configuration 控制依赖可见性**：模块间 `implementation` 优先，避免依赖泄漏
4. **版本统一用 Version Catalog**：跨模块依赖版本走 `libs.versions.toml`（见 [03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)）
5. **独立构建联调用 Composite Build**：跨仓库用 `includeBuild`，不发布临时 jar
6. **合理拆模块**：按业务/层拆分，避免过度拆分导致配置爆炸

---

## 6. 小结

- 多项目 = `settings.gradle` 的 `include` 声明子项目，`project(':模块')` 引用
- 共享配置用 `subprojects`（子项目）/ `allprojects`（含根）
- **组合构建（Composite Build）**用 `includeBuild` 组合独立构建，跨仓库联调不发布 jar
- 多项目最佳实践：配置适度、逻辑轻量、依赖 implementation、版本走 Catalog

## 上一篇 / 下一篇

[03-Gradle依赖管理详解](03-Gradle依赖管理详解.md) / [05-Gradle性能优化详解](05-Gradle性能优化详解.md)

## 参考资料

- [Gradle 官方：Composite Builds](https://docs.gradle.org/current/userguide/composite_builds.html)，查询日期：2026-08-09
- [Gradle 用户手册：多项目](https://docs.gradle.org/current/userguide/multi_project_builds.html)，查询日期：2026-08-09