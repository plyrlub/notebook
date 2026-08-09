---
tags: [Gradle, 构建工具, Java, 依赖管理, Groovy, Kotlin DSL]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具）
归属: 01-学习/Java/构建工具
---

# Gradle 学习笔记（总览）

> 版本基线：Gradle 8.x 为主线，标注 5.x 差异（本机实测环境为 Gradle 5.1.1 + JDK 8，见 🧪 实测小节）
> 受众：Java 后端开发，已会用 Maven（坐标/依赖/生命周期），想系统掌握 Gradle 的核心机制与差异。默认你懂构建工具基本概念，但「Task 增量构建」「Configuration 依赖范围」「Kotlin DSL」从零讲起。
> 关联笔记：[00-构建工具总览·Maven vs Gradle 选型对比](../00-构建工具总览·Maven%20vs%20Gradle%20选型对比.md)、[Maven 总览](../Maven/00-Maven%20总览.md)

## 📋 总纲

- 1. Gradle 是什么：定位与核心特性
- 2. 构建脚本与项目结构：build.gradle / settings.gradle / gradlew
- 3. Groovy DSL vs Kotlin DSL
- 4. Task 与构建生命周期：三阶段 + 增量构建
- 5. 依赖管理：Configuration 体系与冲突解析
- 6. 多项目构建：settings include / 组合构建
- 7. 性能优化：守护进程 / 构建缓存 / 并行
- 8. Gradle vs Maven：全维度对比
- 9. 常用命令速查

## 学习目标

学完本篇你能：

1. 说清 Gradle 的定位：为什么叫"构建自动化工具"而非"项目管理工具"，与 Maven 的根本差异
2. 独立创建 Gradle 项目：settings.gradle + build.gradle + gradlew wrapper 完整闭环
3. 看懂两种 DSL：Groovy DSL 与 Kotlin DSL 的语法对照与选型
4. 讲透 Task 机制：任务声明/依赖/增量构建（up-to-date）原理
5. 用对依赖声明：implementation vs api vs compileOnly 的区别与场景
6. 说清 Gradle 冲突解析策略（最高版本优先）与 Maven（最短路径）的差异
7. 配置多项目构建：include 子模块、依赖项目间引用
8. 说出 3 大性能武器：守护进程、构建缓存、并行构建

## 前置知识

- [Maven 总览](../Maven/00-Maven%20总览.md)——坐标、依赖范围、生命周期概念是 Gradle 的对照基础
- [00-构建工具总览·Maven vs Gradle 选型对比](../00-构建工具总览·Maven%20vs%20Gradle%20选型对比.md)——两者定位差异先建立
- 需掌握：Java 项目基本结构（src/main/java、src/test/java）

---

## 1. Gradle 是什么：定位与核心特性

**一句话记忆**：Gradle 是**基于 JVM 的构建自动化工具**，把构建脚本当"代码"写（DSL），以 Task 为执行单元，用增量构建和缓存把构建做到极致快。

| 维度 | Gradle | Maven |
|---|---|---|
| 本质 | 通用构建自动化工具（可构建任意语言/项目） | 项目管理工具（聚焦 Java 项目约定） |
| 构建脚本 | Groovy/Kotlin 代码（可编程） | XML 声明（静态） |
| 执行单元 | Task（任务图） | Phase（生命周期阶段） |
| 设计哲学 | 约定优于配置 + **可扩展优先** | 约定优于配置 + **严格模型** |
| 官方背书 | Google 选为 Android 官方构建工具 | Apache 基金会 |

**核心特性**（官方文档定位）：

- **Task 驱动**：一切构建动作都是 Task，Task 间构成有向无环图（DAG），按依赖关系执行
- **增量构建**：Task 记录输入/输出，输入没变则标记 UP-TO-DATE 跳过
- **构建缓存**：跨机器/跨项目复用构建产物（缓存命中时甚至跳过任务执行）
- **守护进程（Daemon）**：常驻 JVM 进程，避免每次构建都冷启动 JVM
- **双 DSL**：Groovy DSL（传统）与 Kotlin DSL（现代，IDE 支持更好）

> 💡 **记忆锚点**：Maven 是"声明我要什么"，Gradle 是"编程实现怎么构建"——一个是配置，一个是代码。

---

## 2. 构建脚本与项目结构

### 2.1 核心文件

| 文件 | 作用 |
|---|---|
| `settings.gradle` / `settings.gradle.kts` | 项目名、包含哪些子项目（include）、插件管理仓库 |
| `build.gradle` / `build.gradle.kts` | 项目构建脚本：插件、仓库、依赖、任务定义 |
| `gradle.properties` | 全局属性（JVM 参数、缓存配置等） |
| `gradlew` / `gradlew.bat` | Wrapper 启动脚本，自动下载指定版本 Gradle |
| `gradle/wrapper/gradle-wrapper.properties` | 指定 Gradle 版本（团队统一版本的关键） |

### 2.2 最小项目示例（实测）

`settings.gradle`：
```groovy
rootProject.name = 'demo'
```

`build.gradle`：
```groovy
plugins {
    id 'java'          // 应用 Java 插件：提供 build/test/jar 等任务
}
repositories {
    mavenCentral()     // 依赖仓库
}
dependencies {
    implementation 'org.apache.commons:commons-lang3:3.12.0'
    testImplementation 'junit:junit:4.13.2'
}
```

**目录约定**（Java 插件）：

```
src/main/java      → 主代码
src/main/resources → 主资源
src/test/java      → 测试代码
src/test/resources → 测试资源
build/             → 构建产物（相当于 Maven 的 target/）
```

### 2.3 Wrapper 机制

```bash
gradle wrapper --gradle-version 8.10.2   # 生成指定版本的 wrapper
./gradlew build                          # 团队统一用 wrapper 构建
```

Wrapper 的价值：**团队成员无需安装 Gradle**，gradlew 会自动下载 `gradle-wrapper.properties` 里指定的版本——避免"我机器上能构建"的版本地狱。

---

## 3. Groovy DSL vs Kotlin DSL

Gradle 支持两种脚本语言，文件扩展名区分：`.gradle`（Groovy）、`.gradle.kts`（Kotlin）。

| 对比 | Groovy DSL | Kotlin DSL |
|---|---|---|
| 文件 | build.gradle | build.gradle.kts |
| 类型安全 | 弱（动态类型） | **强类型**（编译期检查） |
| IDE 支持 | 一般 | **优秀**（自动补全、重构、跳转） |
| 学习成本 | 低（语法灵活） | 需懂 Kotlin 基础 |
| 性能 | 略快（少编译） | 配置阶段稍慢（需编译脚本） |
| 官方态度 | 仍是主流（存量项目多） | **推荐新项目使用** |

**语法对照示例**：

```groovy
// Groovy DSL
plugins {
    id 'java'
}
dependencies {
    implementation 'org.apache.commons:commons-lang3:3.12.0'
}
```

```kotlin
// Kotlin DSL
plugins {
    `java`                    // 反引号包裹是 Kotlin DSL 特有语法
}
dependencies {
    implementation("org.apache.commons:commons-lang3:3.12.0")
}
```

> ⚠️ **易错点**：Kotlin DSL 里 `java` 是 Kotlin 关键字，必须用反引号 `` `java` `` 包裹；依赖用 `implementation("group:artifact:version")` 括号写法，不是 Groovy 的空格分隔。

---

## 4. Task 与构建生命周期

### 4.1 三阶段生命周期

Gradle 构建分为三个阶段（与 Maven 的生命周期概念不同）：

| 阶段 | 做什么 | 触发 |
|---|---|---|
| **初始化（Initialization）** | 解析 settings.gradle，确定哪些项目参与构建 | 每次构建 |
| **配置（Configuration）** | 执行所有项目的 build.gradle，构建 Task 图（DAG） | 每次构建（**所有项目都会配置**） |
| **执行（Execution）** | 只执行本次要运行的任务及其依赖 | 按需 |

**关键认知**：配置阶段会**执行所有项目的构建脚本**（即使只构建一个子项目），所以配置逻辑要轻量；执行阶段才按任务图选择性运行。

### 4.2 Task 声明与依赖

```groovy
// 声明任务
tasks.register('hello') {
    doLast {
        println 'Hello Gradle!'
    }
}

// 任务依赖
tasks.register('world') {
    dependsOn 'hello'    // world 执行前先执行 hello
    doLast {
        println 'World!'
    }
}
```

```bash
gradle world
# 输出: Hello Gradle! 然后 World!
```

### 4.3 增量构建（up-to-date）原理 ★

Gradle 的核心性能武器：每个 Task 有**输入（inputs）**和**输出（outputs）**。

- 首次执行：正常运行，记录输入快照
- 再次执行：如果**输入没变**，Task 标记 `UP-TO-DATE` 直接跳过
- 输出还存在且输入未变 → 跳过；输入变了 → 重跑

```bash
> Task :compileJava UP-TO-DATE    # 输入没变,跳过编译
> Task :test UP-TO-DATE           # 同理
```

**实测**（Gradle 5.1.1 + JDK 8，`gradle build` 二次执行）：
```
> Task :processTestResources NO-SOURCE
> Task :testClasses UP-TO-DATE
> Task :test NO-SOURCE
BUILD SUCCESSFUL in 1s
```

自定义任务想支持增量构建，声明 inputs/outputs：
```groovy
tasks.register('myTask') {
    inputs.file('src/data.txt')          // 声明输入
    outputs.file('build/result.txt')     // 声明输出
    doLast {
        // 只有输入变化才执行到这里
    }
}
```

---

## 5. 依赖管理：Configuration 体系与冲突解析

### 5.1 Configuration（依赖范围）

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

**api vs implementation 是核心考点**：

```groovy
// library 模块
dependencies {
    api 'com.google.guava:guava:33.0.0-jre'        // 使用方能看到 Guava
    implementation 'org.apache.commons:commons-lang3:3.12.0'  // 使用方看不到
}
```

**为什么用 implementation 而不是 api**：编译依赖不泄漏给使用方 → 使用方编译更快、依赖图更干净、升级内部依赖不影响下游。

### 5.2 冲突解析策略（与 Maven 本质差异）★

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

### 5.3 依赖排除与约束

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

---

## 6. 多项目构建

### 6.1 settings.gradle 声明子项目

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

### 6.2 子项目间依赖

```groovy
// service/build.gradle
dependencies {
    implementation project(':common')    // 依赖 common 子项目
}
```

### 6.3 根项目统一配置

```groovy
// 根 build.gradle:所有子项目统一 Java 版本和仓库
subprojects {
    apply plugin: 'java'
    repositories {
        mavenCentral()
    }
}
```

### 6.4 组合构建（Composite Build）

多个独立构建组合在一起（如 A 项目用 B 项目的源码而非发布的 jar）：

```bash
gradle --include-build ../library-b build
```

适用场景：多仓库微服务、共享库联调——改 B 源码立即生效，不用先发布。

---

## 7. 性能优化：三大武器

| 武器 | 原理 | 效果 |
|---|---|---|
| **守护进程（Daemon）** | 常驻 JVM，构建信息热存内存，避免冷启动 | 小构建提速明显（实测 5.1.1 二次构建 1s） |
| **构建缓存（Build Cache）** | 缓存任务输出，**跨机器**复用（CI/本地共享） | 大项目可达数量级提速 |
| **并行构建** | `--parallel` 并行执行独立任务/子项目 | 多模块项目线性加速 |

```bash
# 常用性能配置 gradle.properties
org.gradle.daemon=true                  # 开启守护进程(默认)
org.gradle.parallel=true                # 并行构建
org.gradle.caching=true                 # 开启构建缓存(8.x 默认)
org.gradle.jvmargs=-Xmx2g               # 构建 JVM 内存
```

> 💡 **记忆锚点**：**守护进程省"启动"，缓存省"执行"，并行省"等待"**——三管齐下就是 Gradle 快的原因。

---

## 8. Gradle vs Maven：全维度对比

（详细版见 [00-构建工具总览·Maven vs Gradle 选型对比](../00-构建工具总览·Maven%20vs%20Gradle%20选型对比.md)）

| 维度 | Maven | Gradle | 结论 |
|---|---|---|---|
| **灵活性** | 严格模型，自定义受限 | DSL 可编程，扩展无限 | Gradle 胜 |
| **构建性能** | 无增量缓存机制 | 增量+缓存+守护进程，官方宣称至少快 2 倍 | Gradle 胜 |
| **依赖冲突** | 最短路径（受声明顺序影响） | 最高版本+可强制/降级 | Gradle 更可控 |
| **IDE 支持** | 历史久，生态成熟 | Kotlin DSL 提升快，已追平 | 平手 |
| **学习曲线** | XML 简单但冗长 | 脚本灵活但概念多 | Maven 略易 |
| **项目约定** | 约定严格统一 | 约定+可编程 | 看团队 |
| **适合场景** | 标准化企业项目、快速上手 | 复杂构建、Android、性能敏感、多项目 | 看需求 |

**选型建议**：
- 纯 Java 标准化项目、团队习惯 XML、要最低学习成本 → **Maven**
- Android、Kotlin 项目、复杂/多模块构建、追求构建速度 → **Gradle**
- 大项目多模块：Gradle 的并行+缓存收益明显

---

## 9. 常用命令速查

| 命令 | 作用 |
|---|---|
| `gradle tasks` | 列出所有可用任务 |
| `gradle build` | 完整构建（编译+测试+打包） |
| `gradle clean` | 清理 build/ 目录 |
| `gradle test` | 运行测试 |
| `gradle dependencies` | 查看依赖树 |
| `gradle dependencies --configuration compileClasspath` | 查看指定依赖范围 |
| `gradle projects` | 查看多项目结构 |
| `gradle --parallel build` | 并行构建 |
| `gradle --build-cache build` | 开启构建缓存 |
| `gradle init` | 初始化项目（交互式） |
| `gradle wrapper --gradle-version 8.10.2` | 生成指定版本 wrapper |
| `./gradlew build` | 用 wrapper 构建（团队统一） |

## 最佳实践

- **新项目优先 Kotlin DSL + Wrapper**：类型安全 + 版本统一，团队协作零门槛
- **依赖用 implementation 不用 api**（除非是库需暴露）：依赖不泄漏，下游编译更快
- **配置逻辑保持轻量**：配置阶段会执行所有项目脚本，重逻辑放任务 doLast
- **gradle.properties 开并行和缓存**：多模块项目收益明显
- **版本冲突优先用 constraints 统一**，不滥用 force（force 是暴力手段，可能掩盖问题）
- **CI 共享构建缓存**：跨机器复用构建产物，节省大量时间

## 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #G1 | 老版本 Gradle + 新 JDK | `NoClassDefFoundError: Could not initialize class org.codehaus.groovy.vmplugin.v7.Java7`（实测 Gradle 5.1.1 + JDK 17） | 升级 Gradle 或用兼容 JDK（5.x 用 JDK 8/11） |
| #G2 | Kotlin DSL 里 `java` 报错 | 语法错误 | 反引号包裹：`` `java` `` |
| #G3 | 用 api 过度暴露依赖 | 使用方编译慢、依赖图脏 | 库项目才用 api，内部用 implementation |
| #G4 | 以为配置阶段只跑当前项目 | 改一个子项目却配置了全部 | 理解三阶段：配置阶段全量执行是设计行为 |
| #G5 | 版本冲突用 force 硬压 | 掩盖真实冲突，运行期出怪问题 | 优先 constraints，force 需谨慎 |
| #G6 | 直接跑 gradle 不带 wrapper | 团队版本不一致，构建结果漂移 | 统一 gradlew + wrapper 指定版本 |

## 小结

- Gradle = 基于 JVM 的构建自动化工具，Task 驱动 + DSL 可编程，与 Maven"声明式 XML"根本不同
- 三阶段生命周期：初始化 → 配置（全量）→ 执行（按任务图）
- 增量构建（UP-TO-DATE）+ 守护进程 + 构建缓存 = 性能三件套
- 依赖用 Configuration（implementation/api/compileOnly...），冲突解析**最高版本优先**（区别于 Maven 最短路径）
- Kotlin DSL 是新项目推荐方向，Wrapper 保证团队版本一致

## 下一篇

[00-构建工具总览·Maven vs Gradle 选型对比](../00-构建工具总览·Maven%20vs%20Gradle%20选型对比.md)——两个构建工具的完整对比与选型指南

## 🧪 本机实测（2026-08-09）

> 环境：Gradle 5.1.1 + JDK 8（1.8.0_281-o，SDKMAN 管理）；JDK 17 下 5.1.1 无法启动（见踩坑 #G1）

| 验证点 | 命令 | 真实输出 | 结论 |
|---|---|---|---|
| 任务列表 | `gradle tasks` | Build tasks: assemble/build/clean/jar... | Java 插件任务体系完整 ✓ |
| 依赖树 | `gradle dependencies --configuration compileClasspath` | `\--- org.apache.commons:commons-lang3:3.12.0` | 依赖声明解析成功 ✓ |
| 增量构建 | `gradle build` 二次执行 | `> Task :testClasses UP-TO-DATE` | 输入未变跳过任务 ✓ |
| clean build 耗时 | `gradle clean build` | BUILD SUCCESSFUL in 1s（含 daemon 热启动） | 守护进程生效 ✓ |
| 版本兼容 | JDK 17 下 `gradle tasks` | `NoClassDefFoundError ... Java7` | 老 Gradle 不兼容新 JDK ✓ |

## 参考资料

- [Gradle 用户手册（官方）](https://docs.gradle.org/current/userguide/)：Kotlin DSL、依赖管理、构建缓存等章节，查询日期：2026-08-09
- [Gradle 与 Maven 对比（官方中文）](https://gradle.org.cn/maven-vs-gradle/)：灵活性/性能/用户体验/依赖管理对比，查询日期：2026-08-09
- 实测数据：Gradle 5.1.1 + JDK 8 本机运行（demo 位于 /tmp/gradle-demo）
