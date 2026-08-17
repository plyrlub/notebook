---
tags: [Java, JDK, 基础库, 并发, 集合, 反射, 注解, 新特性, 总览, 学习笔记]
创建日期: 2026-08-16
状态: ✅ 已归档（01-学习/Java/JDK基础库）
归属: 01-学习/Java/JDK基础库
---

# JDK 基础库总览

> **Java JDK 内置基础库**：`java.*` / `jdk.*` 自带能力的学习索引域。与应用框架、网络底座、中间件等"外部"技术区分。
> 覆盖：并发、集合、核心机制（反射/代理/注解/SPI）、新特性（JDK 版本演进）。

## 📋 总纲

1. 本域定位：JDK 自带 vs 外部技术
2. 篇目索引（四个子主题）
3. 与其他域的边界
4. 参考

---

## 1. 本域定位：JDK 自带基础

**一句话**：本域收录 **JDK 内置**（`java.*`/`jdk.*`）的基础能力——不依赖任何第三方库、属于 Java 语言自带生态的基础。

| 主题 | 内容 | 来源 |
|---|---|---|
| **并发** | 多线程、volatile、JUC（锁/AQS/并发容器/原子）、线程池 | JDK `java.util.concurrent` |
| **集合** | 集合框架（List/Map/PriorityQueue 等） | JDK `java.util` |
| **核心机制** | 反射、代理、注解、SPI、String intern、字节码/Agent | JDK 语言能力 |
| **新特性** | 各版本新语法/新 API（如 Records）| JDK 版本演进 |

> 归属判据：**JDK 自带 = 本域**；第三方库（Guava/Caffeine/XXL-Job）= 各自域（三方库/中间件等）。

## 2. 篇目索引

### 2.1 并发（`Java.util.concurrent`）
[00-并发编程总览](并发/00-并发编程总览.md) —— 并发编程入口
[01-多线程基础详解](并发/01-多线程基础详解.md)、[Java volatile详解](并发/Java volatile详解.md)
[00-JUC总览](并发/JUC/00-JUC总览.md) —— JUC 全家桶（锁/AQS/并发容器/原子/工具类）
[01-Java线程池原理与参数详解](并发/线程池/01-Java线程池原理与参数详解.md) —— 线程池（+Executors/动态线程池）

### 2.2 集合
[Java-PriorityQueue详解](集合/Java-PriorityQueue详解.md) —— （待补集合框架更多篇）

### 2.3 核心机制
[Java反射详解](核心机制/Java反射详解.md)、[Java代理详解](核心机制/Java代理详解.md)、[Java注解机制详解](核心机制/Java注解机制详解.md)、[Java SPI机制详解](核心机制/Java SPI机制详解.md)、[Java String intern详解](核心机制/Java String intern详解.md)、[Java类型注解与静态校验详解](核心机制/Java类型注解与静态校验详解.md)、[Java Agent与字节码增强详解](核心机制/Java Agent与字节码增强详解.md)

### 2.4 新特性
[Records详解](新特性/Records详解.md) —— （待补更多版本特性）

## 3. 与其他域的边界

```
JDK基础库(本域) | 应用框架(spring/springboot/数据访问/mp中件) | 三方库(Guava/Caffeine)
JDK自带          | 外部企业级框架                          | 第三方可引库
```
- 并发/集合/反射 等 JDK 底层 → 本域
- Dubbo/Netty/MyBatis 等框架 → 框架域（框架/ 下相关子目录）
- 网络 IO → [00-网络底座总览](../框架/网络底座/00-网络底座总览.md)（NIO/Netty 虽是 JDK/三方但有网络定位单独成域）
- 独立部署服务 → [00-中间件总览](../中间件/00-中间件总览.md)

## 4. 参考

- 关联：[00-网络底座总览](../框架/网络底座/00-网络底座总览.md)、[00-中间件总览](../中间件/00-中间件总览.md)、框架域、三方库域
