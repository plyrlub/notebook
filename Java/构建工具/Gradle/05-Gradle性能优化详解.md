---
tags: [Gradle, 构建工具, 性能优化, Build Cache, Configuration Cache, 守护进程]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具/Gradle）
归属: 01-学习/Java/构建工具/Gradle
---

# 05-Gradle性能优化详解

> 版本基线：Gradle 8.x 为主线，标注 5.x 差异（本机实测 Gradle 5.1.1 + JDK 8）
> 受众：想提升 Gradle 构建速度、理解性能三大武器 + 配置缓存的后端开发。
> 关联笔记：[04-Gradle多项目构建详解](04-Gradle多项目构建详解.md)、**00-构建工具总览·Maven & Gradle选型对比**（见知识库）

## 📋 总纲

1. 三大性能武器（守护进程/构建缓存/并行）★
2. Configuration Cache（配置缓存）★
3. gradle.properties 性能配置
4. 最佳实践
5. 常见踩坑
6. 🧪 本机实测（2026-08-09）
7. 小结

## 学习目标

学完本篇你能：

1. 说出 Gradle 三大性能武器：守护进程、构建缓存、并行构建
2. 理解 Build Cache（执行缓存）与 Configuration Cache（配置缓存）的区别
3. 用 gradle.properties 正确配置性能参数
4. 遵循最佳实践，避免常见性能/兼容坑

## 前置知识

- [02-Gradle Task与生命周期详解](02-Gradle%20Task与生命周期详解.md)——理解三阶段生命周期（配置 vs 执行）

---

## 1. 三大性能武器 ★

| 武器 | 原理 | 效果 |
|---|---|---|
| **守护进程（Daemon）** | 常驻 JVM，构建信息热存内存，避免冷启动 | 小构建提速明显（实测 5.1.1 二次构建 1s） |
| **构建缓存（Build Cache）** | 缓存任务输出，**跨机器**复用（CI/本地共享） | 大项目可达数量级提速 |
| **并行构建** | `--parallel` 并行执行独立任务/子项目 | 多模块项目线性加速 |

> 💡 **记忆锚点**：**守护进程省"启动"，缓存省"执行"，并行省"等待"**——三管齐下就是 Gradle 快的原因。

---

## 2. Configuration Cache（配置缓存）★

### 2.1 什么是配置缓存

Gradle 的构建分**配置阶段**和**执行阶段**（见 [02-Gradle Task与生命周期详解](02-Gradle%20Task与生命周期详解.md)）。传统上每次构建都要重新执行配置阶段（解析所有 build.gradle）。

**Configuration Cache（配置缓存）**：缓存配置阶段的**结果（Task 图）**，如果构建脚本没变，**下次直接跳过配置阶段**，复用缓存的图。

| 阶段 | 缓存 | 缓存键 | 作用 |
|---|---|---|---|
| **配置阶段** | Configuration Cache | 构建逻辑/环境 | 跳过项目配置 |
| **执行阶段** | Build Cache | Task 输入 | 跳过任务执行 |

### 2.2 如何启用

`gradle.properties`：
```properties
org.gradle.configuration-cache=true                # 启用配置缓存
org.gradle.configuration-cache.problems=warn       # 有兼容问题时警告（而非失败）
```

或构建时命令行：
```bash
gradle build --configuration-cache
```

### 2.3 收益与限制

**收益**：
- 跳过配置阶段，增量开发/CI 提速明显
- 配置缓存下同一项目内任务可并行执行

**限制/注意**：
- 构建脚本里的"不纯"逻辑（访问系统属性、动态文件）可能不兼容
- 首次启用可能报"problems"，用 `problems=warn` 过渡
- 8.x 默认关闭，需显式开启

> 💡 **记忆锚点**：**Build Cache 缓存"任务执行结果"，Configuration Cache 缓存"配置阶段结果"**——两者叠加，从配置到执行全链路提速。

---

## 3. gradle.properties 性能配置

```properties
# 常用性能配置 gradle.properties
org.gradle.daemon=true                  # 开启守护进程(默认)
org.gradle.parallel=true                # 并行构建
org.gradle.caching=true                 # 开启构建缓存(8.x 需显式)
org.gradle.configuration-cache=true     # 配置缓存(8.x 需显式)
org.gradle.jvmargs=-Xmx2g               # 构建 JVM 内存
```

---

## 4. 最佳实践

- **新项目优先 Kotlin DSL + Wrapper**：类型安全 + 版本统一，团队协作零门槛
- **依赖用 implementation 不用 api**（除非是库需暴露）：依赖不泄漏，下游编译更快
- **配置逻辑保持轻量**：配置阶段会执行所有项目脚本，重逻辑放任务 doLast
- **gradle.properties 开并行、缓存、配置缓存**：多模块项目收益明显
- **版本冲突优先用 constraints 统一**，不滥用 force（force 是暴力手段，可能掩盖问题）
- **CI 共享构建缓存**：跨机器复用构建产物，节省大量时间（Develocity 等提供共享缓存）

---

## 5. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #G1 | 老版本 Gradle + 新 JDK | `NoClassDefFoundError: Could not initialize class org.codehaus.groovy.vmplugin.v7.Java7`（实测 Gradle 5.1.1 + JDK 17） | 升级 Gradle 或用兼容 JDK（5.x 用 JDK 8/11） |
| #G2 | Kotlin DSL 里 `java` 报错 | 语法错误 | 反引号包裹：`` `java` `` |
| #G4 | 以为配置阶段只跑当前项目 | 改一个子项目却配置了全部 | 理解三阶段：配置阶段全量执行是设计行为 |
| #G6 | 直接跑 gradle 不带 wrapper | 团队版本不一致，构建结果漂移 | 统一 gradlew + wrapper 指定版本 |
| #G8 | 启用配置缓存报 problems | 构建脚本有不纯逻辑 | 用 `problems=warn` 过渡，修正不纯逻辑 |

---

## 6. 🧪 本机实测（2026-08-09）

> 环境：Gradle 5.1.1 + JDK 8（1.8.0_281-o，SDKMAN 管理）；JDK 17 下 5.1.1 无法启动（见踩坑 #G1）

| 验证点 | 命令 | 真实输出 | 结论 |
|---|---|---|---|
| 任务列表 | `gradle tasks` | Build tasks: assemble/build/clean/jar... | Java 插件任务体系完整 ✓ |
| 依赖树 | `gradle dependencies --configuration compileClasspath` | `\--- org.apache.commons:commons-lang3:3.12.0` | 依赖声明解析成功 ✓ |
| 增量构建 | `gradle build` 二次执行 | `> Task :testClasses UP-TO-DATE` | 输入未变跳过任务 ✓ |
| clean build 耗时 | `gradle clean build` | BUILD SUCCESSFUL in 1s（含 daemon 热启动） | 守护进程生效 ✓ |
| 版本兼容 | JDK 17 下 `gradle tasks` | `NoClassDefFoundError ... Java7` | 老 Gradle 不兼容新 JDK ✓ |

---

## 7. 小结

- **三大武器**：守护进程（省启动）、Build Cache（省执行）、并行（省等待）
- **Configuration Cache**：缓存配置阶段结果，跳过配置——与 Build Cache 叠加全链路提速
- gradle.properties 配置：`daemon` / `parallel` / `caching` / `configuration-cache` / `jvmargs`
- 最佳实践：Kotlin DSL + Wrapper、implementation 优先、配置轻量、CI 共享缓存
- 老 Gradle 不兼容新 JDK 是常见坑（升级 Gradle 或用兼容 JDK）

## 上一篇

[04-Gradle多项目构建详解](04-Gradle多项目构建详解.md)

## 参考资料

- [Gradle 官方：Improve the Performance of Gradle Builds](https://docs.gradle.org/current/userguide/performance.html)，查询日期：2026-08-09
- [Gradle 官方：Configuration Cache](https://docs.gradle.org/current/userguide/configuration_cache.html)，查询日期：2026-08-09
- [Gradle 用户手册](https://docs.gradle.org/current/userguide/)，查询日期：2026-08-09
- 实测数据：Gradle 5.1.1 + JDK 8 本机运行（demo 位于 /tmp/gradle-demo）