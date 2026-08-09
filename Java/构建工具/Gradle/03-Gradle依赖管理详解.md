---
tags: [Gradle, 构建工具, 依赖管理, Configuration, Version Catalog, 冲突解析]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具/Gradle）
归属: 01-学习/Java/构建工具/Gradle
---

# 03-Gradle依赖管理详解

> 版本基线：Gradle 8.x 为主线，标注 5.x 差异（本机实测 Gradle 5.1.1 + JDK 8）
> 受众：想深入理解 Gradle 依赖管理（Configuration 体系、冲突解析、Version Catalog）的后端开发。
> 关联笔记：[02-Gradle Task与生命周期详解](02-Gradle%20Task与生命周期详解.md)、[00-构建工具总览·Maven & Gradle选型对比](00-构建工具总览·Maven%20&%20Gradle选型对比.md)

## 📋 总纲

1. Configuration（依赖范围）体系
2. api vs implementation（核心考点）
3. 冲突解析策略（vs Maven 本质差异）★
4. 依赖排除与约束（constraints）
5. Version Catalog（版本目录）★
6. 常见踩坑
7. 小结

## 学习目标

学完本篇你能：

1. 用对依赖声明：implementation vs api vs compileOnly 的区别与场景
2. 说清 Gradle 冲突解析策略（最高版本优先）与 Maven（最短路径）的差异
3. 用 exclude 排除传递依赖、用 constraints 统一版本
4. 用 Version Catalog（libs.versions.toml）集中管理依赖版本

## 前置知识

- [01-依赖与仓库](01-依赖与仓库.md)——依赖范围（scope）、dependencyManagement 是对照基础
- [02-Gradle Task与生命周期详解](02-Gradle%20Task与生命周期详解.md)——构建脚本基础

---

## 1. Configuration（依赖范围）

Gradle 用 **Configuration** 表达依赖范围（对应 Maven 的 scope，但更细更可扩展）：

| Configuration | 类似 Maven | 说明 |
|---|---|---|
| `implementation` | compile | **内部依赖**：编译和运行用，但不暴露给使用方 |
| `api` | compile（暴露） | 公开依赖：使用方可见（Java Library 插件） |
| `compileOnly` | provided | 仅编译期（如 Lombok、servlet-api） |
| `runtimeOnly` | runtime | 仅运行期（如 JDBC 驱动实现） |
| `testImplementation` | test | 测试编译+运行 |
| `testRuntimeOnly` | - | 仅测试运行 |
| `annotationProcessor` | - | 注解处理器（Lombok/MapStruct 用） |

---

## 2. api vs implementation（核心考点）★

```groovy
// library 模块
dependencies {
    api 'com.google.guava:guava:33.0.0-jre'        // 使用方能看到 Guava
    implementation 'org.apache.commons:commons-lang3:3.12.0'  // 使用方看不到
}
```

**为什么用 implementation 而不是 api**：编译依赖不泄漏给使用方 → 使用方编译更快、依赖图更干净、升级内部依赖不影响下游。

> ⚠️ **过度用 api 的危害**（踩坑 #G3）：使用方编译慢、依赖图脏。**库项目**且确实需要暴露类型时才用 api，内部依赖一律 implementation。

---

## 3. 冲突解析策略（vs Maven 本质差异）★

| | Maven | Gradle |
|---|---|---|
| 策略 | **最短路径优先**（路径相同时第一声明者优先） | **最高版本优先**（全图扫描取 max） |
| 声明顺序影响 | 有（同深度时） | 无 |
| 降级 | 不支持（除非排除） | 支持（strict 版本强制） |
| 自定义规则 | 无 | 丰富（resolutionStrategy.force / substitution） |

Gradle 示例：
```groovy
configurations.all {
    resolutionStrategy {
        force 'commons-codec:commons-codec:1.9'   // 强制版本
        // 或 failOnVersionConflict() 版本冲突时构建失败
    }
}
```

---

## 4. 依赖排除与约束（constraints）★

```groovy
dependencies {
    implementation('org.apache.httpcomponents:httpclient:4.5.4') {
        exclude group: 'commons-logging', module: 'commons-logging'  // 排除传递依赖
    }
}

// 依赖约束：统一传递依赖版本（类似 Maven dependencyManagement）
dependencies {
    constraints {
        implementation 'com.google.guava:guava:33.0.0-jre'
    }
}
```

**exclude vs constraints 对比**：

| | exclude | constraints |
|---|---|---|
| 作用 | 排除某个传递依赖 | 统一/固定传递依赖版本 |
| 场景 | 去掉不需要的依赖 | 强制某版本，防版本漂移 |
| 滥用风险 | 可能引入缺失类 | 用 force 硬压掩盖真实冲突 |

> 💡 **记忆锚点**：**exclude 删依赖，constraints 定版本**。冲突优先用 constraints 统一，不滥用 force（force 是暴力手段，可能掩盖问题）。

---

## 5. Version Catalog（版本目录）★

Version Catalog（版本目录）是 Gradle 现代依赖管理的核心：**用一个中心文件统一管理所有依赖版本**，多模块项目不再重复写版本号。

### 5.1 配置文件 `gradle/libs.versions.toml`

```toml
[versions]
guava = "33.0.0-jre"
junit = "4.13.2"

[libraries]
guava = { group = "com.google.guava", name = "guava", version.ref = "guava" }
junit = { group = "junit", name = "junit", version.ref = "junit" }

[plugins]
java-library = { id = "java-library", version = "8.x" }
```

### 5.2 在 build.gradle.kts 中引用

```kotlin
dependencies {
    // 通过 libs.xxx 访问（自动生成的类型安全访问器）
    implementation(libs.guava)
    testImplementation(libs.junit)
}
```

### 5.3 好处

| 好处 | 说明 |
|---|---|
| **集中管理** | 所有版本在一个 toml，改一处全生效 |
| **类型安全** | Kotlin DSL 下 `libs.guava` 编译期检查 |
| **多模块一致** | 所有子项目引用同一版本，避免漂移 |
| **插件统一** | plugins 块也走 catalog |

> 💡 **记忆锚点**：Version Catalog = "Gradle 的 dependencyManagement 进化版"——`libs.versions.toml` 集中管版本，Kotlin DSL 类型安全访问。**新项目强烈推荐**。

---

## 6. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #G3 | 用 api 过度暴露依赖 | 使用方编译慢、依赖图脏 | 库项目才用 api，内部用 implementation |
| #G5 | 版本冲突用 force 硬压 | 掩盖真实冲突，运行期出怪问题 | 优先 constraints，force 需谨慎 |
| #G7 | 依赖版本各处写死 | 多模块版本不一致、升级漏改 | 用 Version Catalog 统一管理 |

---

## 7. 小结

- 依赖用 **Configuration**（implementation/api/compileOnly...），冲突解析**最高版本优先**（区别于 Maven 最短路径）
- **implementation 优先**，库项目且需暴露才用 api
- **exclude 删依赖，constraints 定版本**，不滥用 force
- **Version Catalog（libs.versions.toml）**是现代化依赖管理，集中 + 类型安全，新项目推荐

## 上一篇 / 下一篇

[02-Gradle Task与生命周期详解](02-Gradle%20Task与生命周期详解.md) / [04-Gradle多项目构建详解](04-Gradle多项目构建详解.md)

## 参考资料

- [Gradle 官方：依赖管理（第 3 部分）](https://docs.gradle.org/current/userguide/part3_gradle_dep_man.html)，查询日期：2026-08-09
- [Gradle 官方：版本目录](https://docs.gradle.org/current/userguide/platforms.html)，查询日期：2026-08-09
- [Android 官方：迁移到版本目录](https://developer.android.com/build/migrate-to-catalogs)，查询日期：2026-08-09