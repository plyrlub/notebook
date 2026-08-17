---
tags: [Java, Guava, 三方库, 模块化, Maven, 依赖管理]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava概览与模块化辨析

> 实测环境：guava 33.6.0-jre + JDK 17.0.12（本机实测）
> 本系列：[01-Guava base与字符串处理详解](01-Guava base与字符串处理详解.md)、[02-Guava collect集合增强详解](02-Guava collect集合增强详解.md)、[03-Guava concurrent与cache详解](03-Guava concurrent与cache详解.md)、[04-Guava io math primitives详解](04-Guava io math primitives详解.md)、[05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md)

## 📋 总纲

1. Guava 是什么：Google 核心库定位与历史
2. 版本体系：-jre / -android、@Beta、最新版本
3. 模块化辨析（重点）：官方单 artifact 事实 vs 拆包传言
4. 官方真实拆出的小依赖：failureaccess 等（含实测踩坑）
5. 依赖引入：Maven 坐标与 classpath 教训
6. 知识域导航：12 个包域一览与系列笔记地图

## 一、Guava 是什么

Guava 是 Google 开源的 Java 核心工具库（google core libraries for Java），2010 年从 Google Collections Library（google-collections）独立而来，由 Google 内部长期使用的库提炼而成。

| 维度 | 说明 |
| --- | --- |
| 定位 | JDK 标准库的"增强补充"：集合、并发、IO、字符串、缓存、数学、图等 |
| 组织 | GitHub google/guava，官方文档 guava.dev |
| 许可证 | Apache 2.0 |
| 风格 | API 大量使用 @Beta 标注不稳定接口；方法级 javadoc 极详尽 |

Guava 的价值定位：**JDK 缺什么，Guava 补什么**——JDK 8 的 Optional、JDK 9 的 List.of 等都是在 Guava 验证多年后被反哺进 JDK 的。

## 二、版本体系

| 变体 | 适用 | 说明 |
| --- | --- | --- |
| 33.6.0-jre | JRE 8+ 标准环境 | 默认选择 |
| 33.6.0-android | Android / 受限环境 | 剔除 java.time 等 API，行为略有差异 |

最新稳定版：33.6.0-jre / 33.6.0-android（查询日期 2026-08-08）。

@Beta 注解：Guava 用 `@Beta` 标注**不稳定 API**——随时可能改动或删除，生产使用需谨慎（如 graph 包、EventBus 部分 API 长期 @Beta）。javadoc 中带 `@Beta` 的接口不要依赖其稳定性。

## 三、模块化辨析（重点）

### 事实：官方从未拆分成多个 Maven artifact

网上流传"Guava 33.0 起官方把大 jar 拆成 guava-base、guava-collect、guava-concurrent 等子库"的说法 **不准确**。事实核查：

1. **官方 POM（33.6.0-jre）确认仍是单个 artifact**：`com.google.guava:guava`，一个 jar 包含全部 com.google.common.* 包。
2. **官方"模块化"是 JPMS 层面**：jar 内带 module-info.java（通过 MR-JAR 支持 Java 9+ 模块系统），但 Maven 坐标不变。
3. **官方不拆 artifact 的理由**：拆包会造成 split package（多个 jar 含同一包名，JPMS 禁止）、版本碎片化（guava-collect 1.0 与 guava 33.x 混用风险）、兼容性维护成本。官方态度是"保持单 artifact，提供 JPMS 模块化"。

### 传言来源：第三方 fork（dev.mccue）

流传的拆包坐标（guava-base / guava-graph / guava-io / guava-math / guava-net / guava-primitives / guava-testlib / guava-concurrent）实际来自社区项目：

| 项目 | 说明 |
| --- | --- |
| GitHub | bowbahdoe/guava 系列（bowbahdoe/guava-base 等） |
| 定位 | "Guava repackaged and modularized"（soft-fork） |
| Maven 坐标 | dev.mccue:guava-base 等（**groupId 是 dev.mccue，不是 com.google.guava**） |
| 包名 | shaded 到 dev.mccue.guava.*（避开与官方包冲突） |
| 性质 | 个人维护的社区实验项目，Maven Central 有发布但**不建议生产使用** |

### 结论

学习与生产一律使用官方 `com.google.guava:guava` 单 artifact；遇到"拆包"资料先核对坐标的 groupId——`dev.mccue` 开头即第三方 fork。

## 四、官方真实拆出的小依赖

官方虽然没有拆主库，但确实拆出过几个独立小 artifact（这也是"拆包"传言的合理内核）：

| artifact | 内容 | 必要性 |
| --- | --- | --- |
| guava | 主库全部功能 | - |
| failureaccess | InternalFutureFailureAccess 等内部类 | **运行时必需**（实测：缺失则 LoadingCache 抛 NoClassDefFoundError） |
| listenenablefuture | ListenableFuture 接口的独立版（Android 场景用） | 通常可排除 |
| guava-testlib | 测试工具（GoogleCollectionTester 等） | 仅测试用 |
| guava-beta-checker | 编译期检查 @Beta 使用的注解 | 可选 |

> [!note]- 实测踩坑：failureaccess 缺失的真实报错（guava 33.6.0-jre + JDK 17）
> 只把 guava-33.6.0-jre.jar 放 classpath，调用 LoadingCache.get() 时报：
> `java.lang.NoClassDefFoundError: com/google/common/util/concurrent/internal/InternalFutureFailureAccess`
> 补上 failureaccess-1.0.2.jar 后正常。Maven 引入 guava 会自动传递 failureaccess，**手搭 classpath（curl 下载 jar）时容易漏**。
> 实测命令：`java -cp "guava-33.6.0-jre.jar:failureaccess-1.0.2.jar" ...`

## 五、依赖引入

```xml
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>33.6.0-jre</version>
</dependency>
```

Gradle：

```groovy
implementation("com.google.guava:guava:33.6.0-jre")
```

要点：

- Maven 传递依赖会自动带 failureaccess（compile 依赖），无需手动加。
- 需要 JDK 9+ 模块化时用 `requires com.google.common;`（jar 已内置 module-info）。
- Android 环境换 `-android` 变体。

## 六、知识域导航（12 包域）

| 包域 | 核心内容 | 详见解说 | 频率 |
| --- | --- | --- | --- |
| base | Preconditions、Strings、Joiner、Splitter、CharMatcher、CaseFormat、Throwables、Optional | [01-Guava base与字符串处理详解](01-Guava base与字符串处理详解.md) | 高频 |
| collect | Immutable 集合、Multimap、BiMap、Table、Multiset、RangeSet、Lists/Maps/Streams | [02-Guava collect集合增强详解](02-Guava collect集合增强详解.md) | 高频 |
| concurrent | ListenableFuture、MoreExecutors、ThreadFactoryBuilder、RateLimiter、Striped、Monitor、Service | [03-Guava concurrent与cache详解](03-Guava concurrent与cache详解.md) | 高频 |
| cache | CacheBuilder、LoadingCache、CacheStats、RemovalListener | [03-Guava concurrent与cache详解](03-Guava concurrent与cache详解.md) | 高频 |
| io | ByteSource/CharSource、Files、BaseEncoding | [04-Guava io math primitives详解](04-Guava io math primitives详解.md) | 中频 |
| math | IntMath、LongMath、Stats、Quantiles | [04-Guava io math primitives详解](04-Guava io math primitives详解.md) | 中频 |
| primitives | Ints、Longs、UnsignedInts、Range | [04-Guava io math primitives详解](04-Guava io math primitives详解.md) | 中频 |
| net | InternetDomainName、MediaType、HostAndPort | [05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md) | 低频 |
| graph | Graph、ValueGraph、Network | [05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md) | 低频 |
| reflection | TypeToken、ClassPath | [05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md) | 低频 |
| eventbus | EventBus、AsyncEventBus | [05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md) | 低频 |
| hash | Hashing、BloomFilter | [05-Guava net graph reflection eventbus hash详解](05-Guava net graph reflection eventbus hash详解.md) | 低频 |

关联笔记：[Lombok详解](../Lombok详解.md)（同为三方库）、[Caffeine Java缓存详解](../Caffeine Java缓存详解.md)（Guava Cache 的继任者，[03-Guava concurrent与cache详解](03-Guava concurrent与cache详解.md) 有专门对比）、[01-Java线程池原理与参数详解](../../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)（Guava ThreadFactoryBuilder 在其中的使用）。

## 参考资料

- [Guava 官网 guava.dev](https://guava.dev/)，查询日期：2026-08-08
- [GitHub google/guava（最新版本 33.6.0-jre）](https://github.com/google/guava)，查询日期：2026-08-08
- [Maven Central: com.google.guava:guava](https://central.sonatype.com/artifact/com.google.guava/guava)，查询日期：2026-08-08
- [Maven Central: dev.mccue:guava-base（第三方 fork 坐标核对）](https://mvnrepository.com/artifact/dev.mccue/guava-base)，查询日期：2026-08-08
- [GitHub bowbahdoe/guava-base（fork 源码）](https://github.com/bowbahdoe/guava-base)，查询日期：2026-08-08
