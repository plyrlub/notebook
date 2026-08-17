---
tags: [Java, 并发, 线程池, Executors, 阿里规约, OOM, 工厂方法]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/线程池）
归属: 01-学习/Java/JDK基础库/并发/线程池
---

# Executors工厂方法详解

> 前置知识：[01-Java线程池原理与参数详解](01-Java线程池原理与参数详解.md)（七参数、队列、拒绝策略）
> 本文把 Executors 每个工厂方法逐个拆解，并对照阿里规约说明"为什么不推荐"

## 📋 总纲

1. Executors 是什么：工具类与工厂方法全景
2. newFixedThreadPool：固定线程池（无界队列 OOM 风险）
3. newSingleThreadExecutor：单线程池（包装类陷阱）
4. newCachedThreadPool：缓存线程池（无限线程 OOM 风险）
5. newScheduledThreadPool：调度线程池（无界延迟队列）
6. newWorkStealingPool：工作窃取池（ForkJoinPool）
7. newVirtualThreadPerTaskExecutor：虚拟线程工厂（JDK 21）
8. 阿里规约条款原文与解读
9. 正确替代姿势：手动 ThreadPoolExecutor
10. 六个工厂方法对比总表

## 一、Executors 是什么

`java.util.concurrent.Executors` 是一个纯静态工具类，提供创建各种 ExecutorService 的工厂方法。按底层实现分六类：

| 工厂方法 | 底层实现 | 线程模型 |
| --- | --- | --- |
| newFixedThreadPool(n) | ThreadPoolExecutor | 固定 n 线程，无界队列 |
| newSingleThreadExecutor() | ThreadPoolExecutor 包装 | 单线程，无界队列 |
| newCachedThreadPool() | ThreadPoolExecutor | 0 核心，max 无限，SynchronousQueue |
| newScheduledThreadPool(n) | ScheduledThreadPoolExecutor | 定时/延迟任务，无限线程 |
| newWorkStealingPool(n) | ForkJoinPool | 工作窃取，并行度 n |
| newVirtualThreadPerTaskExecutor() | 虚拟线程（JDK 21+） | 每任务一个虚拟线程 |

## 二、newFixedThreadPool：固定线程池

源码（JDK 8）：

```java
public static ExecutorService newFixedThreadPool(int nThreads) {
    return new ThreadPoolExecutor(nThreads, nThreads,   // core = max = n
            0L, TimeUnit.MILLISECONDS,
            new LinkedBlockingQueue<Runnable>());       // 无界队列！
}
```

参数拆解：

- core = max = n：线程数恒定，不存在非核心线程，keepAliveTime 无意义（传 0）。
- 队列：`new LinkedBlockingQueue<>()` **无界版**（容量 Integer.MAX_VALUE）。

**OOM 风险**：任务提交速度持续大于消费速度时，任务在无界队列无限堆积，内存持续增长直至 OutOfMemoryError。由于队列永远不满，execute 流程第 3 步（扩容到 max）永远不触发，第 4 步（拒绝）也永远不触发——**线程池变成"无限缓冲 + 无拒绝"**，既不能扩容也不能兜底。

适用场景：线程数稳定、任务量可控的内部系统；**不适用**：流量不可预测的对外接口。

## 三、newSingleThreadExecutor：单线程池

源码：

```java
public static ExecutorService newSingleThreadExecutor() {
    return new Executors.FinalizableDelegatedExecutorService(
        new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS,
            new LinkedBlockingQueue<Runnable>()));
}
```

参数拆解：

- core = max = 1：永远只有一个线程，任务严格串行执行。
- 关键：外层包了 `FinalizableDelegatedExecutorService`——这是**包装类而非 ThreadPoolExecutor**。

两个必须知道的坑：

① **不能强转调参**：`(ThreadPoolExecutor) executor` 抛 ClassCastException。该池创建后无法用 set 方法动态调参（想调参需用 `Executors.newFixedThreadPool(1)` 替代，它返回裸 ThreadPoolExecutor）。

② **同样无界队列**：单线程消费慢，任务堆积更快，OOM 风险比 fixed 版更高。

适用场景：需要严格串行执行的任务链（如写文件顺序、MQ 消费保序）；线程数确实只需 1。

## 四、newCachedThreadPool：缓存线程池

源码：

```java
public static ExecutorService newCachedThreadPool() {
    return new ThreadPoolExecutor(0, Integer.MAX_VALUE,   // max = 无限！
            60L, TimeUnit.SECONDS,
            new SynchronousQueue<Runnable>());
}
```

参数拆解：

- core = 0：默认没有常驻线程（空闲 60s 后线程全部回收，池可缩回 0）。
- max = Integer.MAX_VALUE：**线程数理论上无上限**。
- 队列：SynchronousQueue，零缓冲，任务直接交接给线程。

行为推演（结合 [01-Java线程池原理与参数详解](01-Java线程池原理与参数详解.md)）：任务到达 → 核心线程数 0 < corePoolSize 不成立（0 个线程但 core=0，`workerCount < corePoolSize` 为 false）→ 尝试入 SynchronousQueue → 无空闲线程接 → 入队失败 → 创建非核心线程执行。即**来一个任务开一个线程**。

**OOM 风险**：高并发下线程数随任务数无限增长。每个线程默认栈约 512KB~1MB，10 万个并发任务就是几十 GB 内存；线程创建本身失败还会抛 OutOfMemoryError（无法创建原生线程）。

适用场景：任务执行时间极短、数量波动大、且明确不会爆发的场景（如纯内存计算的小任务）。生产上对不可控流量基本禁用。

## 五、newScheduledThreadPool：调度线程池

源码：

```java
public static ScheduledExecutorService newScheduledThreadPool(int corePoolSize) {
    return new ScheduledThreadPoolExecutor(corePoolSize);   // max = Integer.MAX_VALUE
}
```

参数拆解：

- 继承 ThreadPoolExecutor，但核心机制不同：任务不直接执行，按延迟时间放入 DelayedWorkQueue（无界），到点才取出执行。
- max = Integer.MAX_VALUE：delayedExecute 发现核心线程满且队列是延迟队列时，会直接创建新线程执行到点任务，**线程数可无限增长**。
- 队列：DelayedWorkQueue，**无界**，延迟任务无限堆积同样 OOM。

与 Timer 对比：Timer 单线程、任务异常会杀死 Timer 线程导致后续任务全部失效；ScheduledThreadPoolExecutor 多线程 + 任务异常不影响其他任务 + 支持 scheduleAtFixedRate / scheduleWithFixedDelay。

适用场景：定时/延迟任务（心跳、缓存刷新、批处理调度）。注意固定频率任务若执行时间超过周期会排队积压，需评估任务耗时。

## 六、newWorkStealingPool：工作窃取池

源码：

```java
public static ExecutorService newWorkStealingPool() {
    return new ForkJoinPool(Runtime.getRuntime().availableProcessors(),
            ForkJoinPool.defaultForkJoinWorkerThreadFactory, null, true);
}
```

参数拆解：

- 底层是 ForkJoinPool，默认并行度 = CPU 核数。
- 工作窃取：每个工作线程有自己的双端任务队列，线程空闲时从其他线程队列**尾部偷**任务，负载自动均衡。
- 注意：返回类型是 ExecutorService，但 **ForkJoinPool 不能保证 FIFO 执行顺序**（任务可能被窃取乱序执行）；不是通用的"线程池替代品"，适合可并行拆分的大任务（分治）。

适用场景：CPU 密集的并行计算、分治任务（配合 RecursiveTask）；不适合有顺序要求的任务队列。

## 七、newVirtualThreadPerTaskExecutor：虚拟线程工厂（JDK 21）

源码（JDK 21）：

```java
public static ExecutorService newVirtualThreadPerTaskExecutor() {
    ThreadFactory factory = Thread.ofVirtual().factory();
    return new VirtualThreadPerTaskExecutor(factory);
}
```

参数拆解：每个提交的任务创建一个新的虚拟线程执行，用完即弃，**无池化概念**——没有 core/max/队列/拒绝策略可调，天然规避了 Executors 的 OOM 问题（虚拟线程开销极小，百万级可承载）。

适用场景：IO 密集型任务（数据库访问、RPC 调用、文件读写）的"每请求一线程"模型。细节与选型见 [03-线程数设置与虚拟线程选型](03-线程数设置与虚拟线程选型.md)。

## 八、阿里规约条款原文与解读

《阿里巴巴Java开发手册》（泰山版/黄山版均保留）相关强制条款：

> **【强制】线程资源必须通过线程池提供，不允许在应用中自行显式创建线程。**
> 说明：使用线程池的好处是减少在创建和销毁线程上所花的时间以及系统资源的开销，解决资源不足的问题。如果不使用线程池，有可能造成系统创建大量同类线程而导致消耗完内存或者"过度切换"的问题。

> **【强制】线程池不允许使用 Executors 去创建，而是通过 ThreadPoolExecutor 的方式，这样的处理方式让写的同学更加明确线程池的运行规则，规避资源耗尽的风险。**
> 说明：Executors 返回的线程池对象的弊端如下：
> 1. FixedThreadPool 和 SingleThreadPool：允许的请求队列长度为 Integer.MAX_VALUE，可能会堆积大量的请求，从而导致 OOM。
> 2. CachedThreadPool 和 ScheduledThreadPool：允许的创建线程数量为 Integer.MAX_VALUE，可能会创建大量的线程，从而导致 OOM。

> **【强制】创建线程或线程池时请指定有意义的线程名称，方便出错时回溯。**

> **【参考】线程池大小设置：IO 密集型任务线程数为 CPU 核数 × 2；CPU 密集型任务线程数为 CPU 核数 + 1。**

逐条解读：

- 第一条堵"裸 new Thread"：线程生命周期无人管理，数量失控。
- 第二条点名两类 OOM：**队列无界 OOM**（fixed/single）与**线程数无限 OOM**（cached/scheduled）——正好对应本笔记第二~五章的风险分析。规约的本质是"强制显式写出每个参数，让风险可见"。
- 第三条呼应线程工厂自定义（见 [01-Java线程池原理与参数详解](01-Java线程池原理与参数详解.md)）。
- 第四条是经验值，精细公式见 [03-线程数设置与虚拟线程选型](03-线程数设置与虚拟线程选型.md)。

## 九、正确替代姿势：手动 ThreadPoolExecutor

```java
// 推荐：显式四个维度全部可控
ExecutorService pool = new ThreadPoolExecutor(
        10, 20,                         // core / max 显式
        60L, TimeUnit.SECONDS,          // 非核心空闲回收
        new ArrayBlockingQueue<>(1000), // 有界队列（防 OOM 的关键）
        new ThreadFactoryBuilder().setNameFormat("order-pool-%d").build(),
        new ThreadPoolExecutor.CallerRunsPolicy());   // 拒绝策略显式
```

与 Executors 默认值的对照（同样想表达"10 线程固定池"）：

| 写法 | 队列 | 拒绝 | OOM 风险 |
| --- | --- | --- | --- |
| Executors.newFixedThreadPool(10) | 无界 | 永不触发 | 高 |
| 手动 new ThreadPoolExecutor(10, 10, 0, ..., new ArrayBlockingQueue<>(1000), ...) | 有界 | 队列满即拒绝 | 可控 |

单线程串行需求改用 `new ThreadPoolExecutor(1, 1, ...)` 而非 newSingleThreadExecutor（避开包装类无法调参的问题）。

## 十、六个工厂方法对比总表

| 工厂方法 | core | max | 队列 | keepAlive | OOM 风险 | 典型场景 |
| --- | --- | --- | --- | --- | --- | --- |
| newFixedThreadPool(n) | n | n | LinkedBlockingQueue 无界 | 0（无效） | 队列堆积 OOM | 稳定负载 |
| newSingleThreadExecutor() | 1 | 1 | LinkedBlockingQueue 无界 | 0 | 队列堆积 OOM（最快） | 严格串行 |
| newCachedThreadPool() | 0 | MAX_VALUE | SynchronousQueue | 60s | 线程爆炸 OOM | 短任务爆发（慎用） |
| newScheduledThreadPool(n) | n | MAX_VALUE | DelayedWorkQueue 无界 | 0 | 线程/队列双 OOM | 定时调度 |
| newWorkStealingPool() | - | - | 工作窃取双端队列 | - | 低（CPU 密集受核数限制） | 并行计算 |
| newVirtualThreadPerTaskExecutor() | - | - | 无（每任务一线程） | - | 极低（虚拟线程廉价） | IO 密集 |

## 参考资料

- [Java SE 8 Executors 源码](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/Executors.html)，查询日期：2026-08-08
- [阿里巴巴Java开发手册](https://github.com/alibaba/p3c)，查询日期：2026-08-08
- [为什么阿里巴巴Java开发手册禁止使用Executors创建线程池（知乎）](https://zhuanlan.zhihu.com/p/32285925098)，查询日期：2026-08-08
- 桌面面试素材《线程池原理与参数.md》"为什么不用 Executors" 一节为本文索引来源
