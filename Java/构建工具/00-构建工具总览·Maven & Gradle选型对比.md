---
tags: [构建工具, Maven, Gradle, 选型, Java, 对比]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具）
归属: 01-学习/Java/构建工具
---

# 00-构建工具总览·Maven & Gradle选型对比

> 版本基线：Maven 3.9.x / Gradle 8.x 为主线（本机实测：Maven 3.9.16 + JDK 17；Gradle 5.1.1 + JDK 8，见 [01-Gradle核心机制详解](Gradle/01-Gradle核心机制详解.md) 🧪 小节）
> 受众：Java 后端开发，已掌握至少一种构建工具的基础用法，想系统理解 Maven 与 Gradle 的差异并做选型决策。
> 关联笔记：[01-依赖与仓库](Maven/01-依赖与仓库.md)、[01-Gradle核心机制详解](Gradle/01-Gradle核心机制详解.md)

## 📋 总纲

- 1. 为什么需要构建工具
- 2. 核心差异总览（一张表）
- 3. 构建模型：生命周期 vs Task 图
- 4. 依赖管理：scope vs Configuration
- 5. 冲突解析：最短路径 vs 最高版本
- 6. 性能：为什么 Gradle 快
- 7. 生态与场景
- 8. 选型决策指南

## 学习目标

学完本篇你能：

1. 一句话说清 Maven 与 Gradle 的本质差异
2. 从构建模型、依赖管理、性能三个维度对比两者
3. 说出 Gradle 比 Maven 快的三个核心机制
4. 根据项目类型/团队情况给出选型建议
5. 知道什么时候不该换构建工具

## 前置知识

- [01-依赖与仓库](Maven/01-依赖与仓库.md)——Maven 的依赖配置、生命周期、插件机制
- [01-Gradle核心机制详解](Gradle/01-Gradle核心机制详解.md)——Gradle 的 Task、Configuration、DSL 机制
- 需掌握：Java 项目结构、依赖坐标（groupId:artifactId:version）基本概念

---

## 1. 为什么需要构建工具

Java 项目天然复杂：依赖管理（下载/传递/冲突）、编译、测试、打包、发布、多模块协作。构建工具把这些固化成可重复、可自动化的流程。

**两个主流选择**：
- **Maven**（Apache 基金会，2004 年发布）：XML 声明式，约定优于配置，标准化
- **Gradle**（Gradle Inc.，2007 年发布）：DSL 可编程，Task 驱动，性能优先

> 💡 **一句话记忆**：**Maven 是"填表"（XML 声明），Gradle 是"编程"（DSL 代码）**——前者稳定易懂，后者灵活高效。

---

## 2. 核心差异总览（一张表）

| 维度 | Maven | Gradle |
|---|---|---|
| 构建脚本 | pom.xml（XML） | build.gradle / build.gradle.kts（Groovy/Kotlin） |
| 本质 | 项目管理工具（Java 为主） | 通用构建自动化工具（任意语言） |
| 执行模型 | 生命周期（phase）+ 插件目标（goal） | Task 图（DAG） |
| 依赖范围 | scope（compile/test/provided/runtime/system/import） | Configuration（implementation/api/compileOnly/...） |
| 冲突解析 | 最短路径优先 + 第一声明者 | 最高版本优先 + 可强制/降级 |
| 增量构建 | 无（每次全量） | 有（输入/输出快照，UP-TO-DATE 跳过） |
| 构建缓存 | 需 Develocity（商业） | 内置 Build Cache |
| 守护进程 | 无 | 有（Daemon 常驻 JVM） |
| 并行构建 | 1.9+ 支持 `-T` | 原生支持 `--parallel` |
| IDE 支持 | 非常成熟 | 快速追赶（Kotlin DSL 类型安全） |
| 官方背书 | Apache | Google（Android 官方） |
| 学习曲线 | 低（XML 简单） | 中高（脚本灵活但概念多） |

---

## 3. 构建模型：生命周期 vs Task 图

### Maven：三套生命周期

```
clean 生命周期: pre-clean → clean → post-clean
default 生命周期: validate → compile → test → package → verify → install → deploy
site 生命周期: pre-site → site → post-site → site-deploy
```

执行 `mvn package` = 从 validate 一路执行到 package。**结构固定**，扩展靠插件绑定到固定 phase。

### Gradle：Task 图（DAG）

```groovy
tasks.register('compile') { ... }
tasks.register('test') { dependsOn 'compile' }
tasks.register('package') { dependsOn 'test' }
```

执行 `gradle package` → 构建任务依赖图（DAG）→ 只执行 package 及其依赖链。**任务可任意命名、任意编排**。

**本质差异**：
- Maven：阶段是固定的"跑道"，插件选择在哪一站做动作
- Gradle：任务是自由的"节点图"，依赖关系自己定义

> 💡 **记忆锚点**：Maven 是**固定流水线**（阶段不可增删），Gradle 是**自由流程图**（任务随意连）。

---

## 4. 依赖管理：scope vs Configuration

### Maven scope（6 种）

| scope | 编译 | 测试 | 运行 | 典型 |
|---|---|---|---|---|
| compile（默认） | ✅ | ✅ | ✅ | 核心库 |
| test | ❌ | ✅ | ❌ | JUnit |
| provided | ✅ | ✅ | ❌ | servlet-api |
| runtime | ❌ | ✅ | ✅ | JDBC 驱动 |
| system | ✅ | ✅ | ❌ | 本地 jar（需 systemPath） |
| import | 仅 dependencyManagement 导入 | | | BOM |

### Gradle Configuration（核心 7 种）

| configuration | 说明 | 对应 Maven |
|---|---|---|
| implementation | 内部依赖，不暴露给使用方 | compile |
| api | 公开依赖，使用方可见 | compile（库项目） |
| compileOnly | 仅编译期 | provided |
| runtimeOnly | 仅运行期 | runtime |
| testImplementation | 测试用 | test |
| testRuntimeOnly | 仅测试运行 | - |
| annotationProcessor | 注解处理器 | - |

**Gradle 优势**：`implementation` vs `api` 分离 → 依赖不泄漏，下游编译快、依赖图干净；`annotationProcessor` 专门管理注解处理器（Lombok/MapStruct）；**可自定义 Configuration**（如 integrationTestCompile 区分集成测试）。

---

## 5. 冲突解析：最短路径 vs 最高版本

### Maven：最短路径优先

```
A → B → C → X(1.0)    路径长度 3
A → D → X(2.0)        路径长度 2  ← 选这个（路径更短）
```

路径相同时：**第一声明者优先**（pom 里谁先声明听谁的）——受声明顺序影响。

### Gradle：最高版本优先

```
A → B → C → X(1.0)    版本 1.0
A → D → X(2.0)        版本 2.0  ← 选这个（版本更高）
```

全图扫描取 max 版本，**不受声明顺序影响**。且支持：
- `resolutionStrategy.force` 强制版本
- strict 版本声明（允许降级）
- constraints 依赖约束（统一传递依赖版本）

**实用差异**：Maven 的冲突结果可能因 pom 顺序变化而"漂移"；Gradle 结果可预测，且强制/约束手段更丰富。

---

## 6. 性能：为什么 Gradle 快

官方基准（Apache Commons Lang 构建对比，Gradle vs Maven）：

| 场景 | Gradle | Maven |
|---|---|---|
| clean build（含测试） | ~14.7s | ~25.8s |
| clean build + 缓存 | ~0.6s | ~18.2s |
| 单文件改动编译 | ~0.5s | ~24.1s |

（数据来源：Gradle 官方对比页，Gradle 5.4 vs Maven 3.6）

**三大机制**：

| 机制 | 原理 | 类比 |
|---|---|---|
| 增量构建 | 任务输入/输出快照，未变则 UP-TO-DATE 跳过 | "只看改动的部分" |
| 构建缓存 | 输出跨机器复用（hash 命中直接拿） | "别人的成品直接拿来用" |
| 守护进程 | 常驻 JVM 热加载 | "饭店常开的灶火" |

> ⚠️ **实事求是**：官方数据是 Gradle 自家基准，真实项目差距因场景而异；但增量+缓存是 Maven 原生没有的机制，大项目多模块时差距客观存在。Maven 也可用 Develocity（商业）获得缓存能力。

---

## 7. 生态与场景

| 场景 | 首选 | 原因 |
|---|---|---|
| **Android** | Gradle（唯一选择） | Google 官方指定 |
| **Kotlin 项目** | Gradle | Kotlin DSL 同语言、官方支持最好 |
| **Java 微服务（Spring Boot）** | 两者皆可 | Spring 官方同时支持，生成器两种都有 |
| **多模块企业级项目** | Gradle 优势明显 | 并行+缓存+implementation 隔离 |
| **标准化、团队新人多** | Maven | XML 简单统一，可预测 |
| **C/C++ 原生开发** | Gradle | 官方支持 native 构建 |
| **遗留项目** | 不折腾 | 迁移成本 > 收益时维持现状 |

**注意**：Spring Boot 官方脚手架（start.spring.io）Maven/Gradle 都支持；`mvn wrapper` 也存在但远不如 `gradlew` 普及。

---

## 8. 选型决策指南

**选 Gradle 当**：
- 项目用 Kotlin / Android
- 多模块复杂构建，性能敏感（CI 时间成本高）
- 需要灵活自定义构建逻辑（代码生成、多平台）
- 团队熟悉 Groovy/Kotlin，愿意学习 DSL

**选 Maven 当**：
- 纯 Java 标准化项目，追求最低学习成本和最大可预测性
- 团队习惯 XML，无特殊构建需求
- 公司规范/存量基础设施绑定 Maven（如私服、CI 模板）
- 项目简单，Gradle 优势用不上

**决策框架**：先看**约束条件**（Android/Kotlin → Gradle；公司标准 → 跟随），再看**收益**（多模块/性能敏感 → Gradle），最后看**成本**（团队学习曲线）。

> 💡 **记忆锚点**：**没有"最好"的构建工具，只有"最适合当前项目"的**——约束 > 收益 > 成本。

## 最佳实践

- **不要为了"潮"换构建工具**：构建工具是基础设施，迁移成本包含 CI、私服、团队习惯
- **新项目按约束条件选**：Android/Kotlin 直接 Gradle，纯 Java 两者皆可看团队
- **无论选哪个，用 wrapper 锁版本**（gradlew / mvnw），避免版本漂移
- **依赖管理优先用 implementation / constraints**，不要堆 force
- **CI 上开启构建缓存/并行**：Gradle 内置，Maven 需配置或商业方案

## 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #B1 | 老 Gradle 跑新 JDK | `NoClassDefFoundError: Java7` | 升级 Gradle 或换兼容 JDK（见 [01-Gradle核心机制详解](Gradle/01-Gradle核心机制详解.md) #G1） |
| #B2 | Maven 冲突结果漂移 | 换依赖顺序构建结果变 | 理解最短路径+第一声明者，用 dependencyManagement 固定 |
| #B3 | 换工具迁移一半后悔 | 构建脚本、CI、插件全要重写 | 选型前先小范围试点验证 |
| #B4 | 误以为 Gradle 一定快 | 小项目感受不到差距 | 增量/缓存收益在大项目才明显，小项目选熟悉的 |
| #B5 | 混合使用两套工具 | 同一项目 pom.xml + build.gradle 并存 | 确定主构建工具，另一套仅作迁移过渡 |

## 小结

- Maven = 声明式 XML + 固定生命周期；Gradle = 可编程 DSL + 自由 Task 图
- 依赖管理：scope vs Configuration（implementation/api 隔离是 Gradle 亮点）
- 冲突解析：最短路径（Maven）vs 最高版本（Gradle，更可预测）
- 性能三件套（增量/缓存/守护进程）是 Gradle 核心优势
- 选型看约束（Android/Kotlin → Gradle）> 收益（多模块/性能）> 成本（团队学习）

## 相关笔记（导航）

**Maven 系列**：
- [01-依赖与仓库](Maven/01-依赖与仓库.md)——依赖配置/范围/调解 + 仓库/镜像/私服
- [02-生命周期与插件](Maven/02-生命周期与插件.md)——三套生命周期/插件绑定 + 聚合与继承
- [03-私服与测试](Maven/03-私服与测试.md)——Nexus 私服搭建 + surefire 测试
- [04-版本与灵活构建](Maven/04-版本与灵活构建.md)——版本约定/发布 + 属性/Profile/Archetype

**Gradle 系列**：
- [01-Gradle核心机制详解](Gradle/01-Gradle核心机制详解.md)——定位/构建脚本/DSL/Wrapper
- **02-Gradle Task与生命周期详解**（见知识库）——Task DAG/增量构建/命令
- [03-Gradle依赖管理详解](Gradle/03-Gradle依赖管理详解.md)——Configuration/冲突解析/Version Catalog
- [04-Gradle多项目构建详解](Gradle/04-Gradle多项目构建详解.md)——include/子项目依赖/Composite Build
- [05-Gradle性能优化详解](Gradle/05-Gradle性能优化详解.md)——守护进程/缓存/配置缓存/实测

## 参考资料

- [Gradle 与 Maven 对比（官方中文页）](https://gradle.org.cn/maven-vs-gradle/)，查询日期：2026-08-09
- [Gradle and Maven Comparison（官方英文）](https://gradle.org/maven-and-gradle/)，查询日期：2026-08-09
- [Gradle vs Maven 性能对比（官方）](https://gradle.org/gradle-and-maven-performance/)，查询日期：2026-08-09
