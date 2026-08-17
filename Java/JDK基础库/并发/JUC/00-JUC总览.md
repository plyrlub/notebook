---
tags: [JUC, java.util.concurrent, 并发, 总览, 锁, 原子类, 并发容器, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/JUC）
归属: 01-学习/Java/JDK基础库/并发/JUC
---

# 00-JUC总览

> 版本基线：java.util.concurrent（JDK 5 引入，Doug Lea 设计），JDK 8+ 全面成熟
> 受众：Java 后端开发，已懂 [01-多线程基础详解](../01-多线程基础详解.md) 和 [JMM内存模型详解](../../../JVM/JMM内存模型详解.md)，要系统掌握 JUC 工具包。默认你懂 synchronized、线程。
> 关联笔记：[00-并发编程总览](../00-并发编程总览.md)、[01-多线程基础详解](../01-多线程基础详解.md)、[JMM内存模型详解](../../../JVM/JMM内存模型详解.md)、[Java volatile详解](../Java volatile详解.md)、[01-Java线程池原理与参数详解](../线程池/01-Java线程池原理与参数详解.md)

## 📋 总纲

- 1. JUC 是什么：并发工具全家桶
- 2. 四大核心板块
- 3. 本系列导航
- 4. 其他类速览表
- 5. 选型速查

## 学习目标

学完本篇你能：

1. 说清 JUC 包的四大部分（锁/原子类/并发容器/工具类）
2. 按场景快速找到对应工具类
3. 规划 JUC 学习路径（本系列各篇）
4. 了解 JUC 全貌（含不展开的其他类）

## 前置知识

- [01-多线程基础详解](../01-多线程基础详解.md)——synchronized/线程基础
- [JMM内存模型详解](../../../JVM/JMM内存模型详解.md)——可见性/有序性原理
- 需掌握：线程、锁、队列基本概念

---

## 1. JUC 是什么：并发工具全家桶

**一句话记忆**：JUC（java.util.concurrent）是 JDK 自带的**并发编程工具包**——把并发场景的高频需求（锁/原子操作/安全容器/协作）都封装好，比手写 synchronized 更强大、更精细。

**为什么需要 JUC**（对比 synchronized）：

| 场景 | synchronized | JUC |
|---|---|---|
| 锁超时/中断 | ❌ 不可中断 | ✅ ReentrantLock.tryLock(超时) |
| 读写分离 | ❌ | ✅ ReentrantReadWriteLock |
| 原子计数 | ❌ 需加锁 | ✅ AtomicInteger（CAS 无锁） |
| 线程安全 Map | ❌ Hashtable 性能差 | ✅ ConcurrentHashMap |
| 线程协作 | ⚠️ wait/notify 易错 | ✅ CountDownLatch/Semaphore 等 |

---

## 2. 四大核心板块

| 板块 | 代表类 | 解决什么 |
|---|---|---|
| **锁与 AQS** | ReentrantLock/ReadWriteLock/StampedLock | 比 synchronized 更灵活的锁 |
| **原子类** | AtomicInteger/AtomicReference/LongAdder | CAS 无锁原子操作 |
| **并发容器** | ConcurrentHashMap/BlockingQueue/CopyOnWriteArrayList | 线程安全的高性能容器 |
| **工具类** | CountDownLatch/CyclicBarrier/Semaphore/Exchanger | 线程协作与同步 |

---

## 3. 本系列导航

| 篇目 | 内容 | 状态 |
|---|---|---|
| [01-JUC之锁与AQS](01-JUC之锁与AQS.md) | ReentrantLock/AQS 原理/读写锁 | 重点 |
| [02-JUC之原子类与CAS](02-JUC之原子类与CAS.md) | CAS 原理/Atomic*/LongAdder | 重点 |
| [03-JUC之并发容器](03-JUC之并发容器.md) | ConcurrentHashMap/BlockingQueue/CopyOnWrite | 重点 |
| [04-JUC之工具类](04-JUC之工具类.md) | CountDownLatch/CyclicBarrier/Semaphore | 重点 |
| [05-JUC其他类与场景补充](05-JUC其他类与场景补充.md) | ForkJoinPool/CompletableFuture/StampedLock/Exchanger 等 | 速览 |

---

## 4. 其他类速览表

（详细见 [05-JUC其他类与场景补充](05-JUC其他类与场景补充.md)）

| 类 | 一句话 | 场景 |
|---|---|---|
| **CompletableFuture** | 异步编程利器（回调编排） | 异步任务链/并行聚合 |
| **ForkJoinPool** | 分治并行框架 | 大任务拆分递归 |
| **StampedLock** | 乐观读锁（读多写少极致优化） | 高并发读 |
| **Exchanger** | 两线程交换数据 | 配对交换 |
| **Phaser** | 可复用分阶段协作 | 多阶段任务 |
| **ThreadLocalRandom** | 线程安全随机数 | 并发随机 |
| **TimeUnit** | 时间单位枚举（sleep 可读） | 时间转换 |

---

## 5. 选型速查

```
需要更灵活的锁(超时/中断/公平) → ReentrantLock (01篇)
读多写少 → ReentrantReadWriteLock / StampedLock
原子计数/累加 → AtomicInteger / LongAdder (02篇)
线程安全 Map → ConcurrentHashMap (03篇)
生产者消费者 → BlockingQueue (03篇)
一等多线程(任务都完成) → CountDownLatch (04篇)
多线程互相等待齐头并进 → CyclicBarrier (04篇)
限流/控制并发数 → Semaphore (04篇)
异步回调/编排 → CompletableFuture (05篇)
```

## 最佳实践

- **synchronized 仍是首选**：简单临界区用它（JDK 6+ 优化后性能与 ReentrantLock 接近）
- **JUC 用于复杂需求**：需要超时/中断/公平/多条件时升级到 ReentrantLock
- **高并发计数用 LongAdder**：AtomicInteger 在极高竞争下 CAS 自旋损耗大
- **容器优先 ConcurrentHashMap**：Hashtable 全表锁已过时
- **线程协作优先 JUC 工具**：少用 wait/notify（易错，见 [01-多线程基础详解](../01-多线程基础详解.md) 踩坑）

## 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #J1 | 工具类选错 | 死锁/提前返回 | 先明确场景（见选型速查） |
| #J2 | CountDownLatch 不可复用 | 第二次 await 无效 | 可复用场景用 CyclicBarrier/Phaser |
| #J3 | Semaphore 忘记 release | 信号量耗尽 | finally 中 release |
| #J4 | 原子类替代一切 | 复合操作仍不安全 | CAS 只保证单操作原子（见 02篇） |
| #J5 | 并发容器遍历时修改 | ConcurrentModificationException | 用迭代器/弱一致性设计（见 03篇） |

## 小结

- JUC = 锁/原子类/并发容器/工具类 四大板块
- synchronized 简单够用，JUC 应对复杂并发需求
- 学习路径：锁与 AQS → 原子类 → 并发容器 → 工具类 → 其他补充
- 选型先想场景，再选工具（见速查表）

## 下一篇

[01-JUC之锁与AQS](01-JUC之锁与AQS.md)——并发编程的基石

## 参考资料

- [java.util.concurrent 官方文档](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)，查询日期：2026-08-09
- [JavaGuide: JUC 并发编程](https://javaguide.cn/java/concurrent/)，查询日期：2026-08-09
