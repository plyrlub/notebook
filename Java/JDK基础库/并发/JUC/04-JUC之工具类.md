---
tags: [JUC, CountDownLatch, CyclicBarrier, Semaphore, 工具类, 并发, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/JUC）
归属: 01-学习/Java/JDK基础库/并发/JUC
---

# 04-JUC之工具类

> 版本基线：JDK 5 引入（CountDownLatch/CyclicBarrier/Semaphore），均基于 AQS 实现
> 受众：Java 后端开发，需要线程协作/同步控制。默认你懂 [01-JUC之锁与AQS](01-JUC之锁与AQS.md)（AQS 原理）。
> 关联笔记：[00-JUC总览](00-JUC总览.md)、[01-JUC之锁与AQS](01-JUC之锁与AQS.md)、[05-JUC其他类与场景补充](05-JUC其他类与场景补充.md)

## 📋 总纲

- 1. 工具类全景
- 2. CountDownLatch（倒数门闩）★
- 3. CyclicBarrier（循环栅栏）★
- 4. Semaphore（信号量）★
- 5. CountDownLatch vs CyclicBarrier
- 6. 常见踩坑

## 学习目标

学完本篇你能：

1. 说出三大工具类的用途（一等多/齐头并进/限流）
2. 熟练使用 CountDownLatch（await/countDown）
3. 熟练使用 CyclicBarrier（可复用，支持回调）
4. 用 Semaphore 实现限流/控制并发数
5. 对比 CountDownLatch 与 CyclicBarrier 并正确选型

## 前置知识

- [01-JUC之锁与AQS](01-JUC之锁与AQS.md)——AQS 原理（工具类都基于 AQS）
- 需掌握：线程创建、ExecutorService 基础

---

## 1. 工具类全景

| 工具 | 一句话 | 核心场景 |
|---|---|---|
| **CountDownLatch** | 倒计数，数到 0 放行 | 主线程等 N 个任务完成 |
| **CyclicBarrier** | 栅栏，人到齐才继续 | N 线程互相等待齐头并进 |
| **Semaphore** | 信号量，控制同时访问数 | 限流/资源池 |

三者都基于 [01-JUC之锁与AQS](01-JUC之锁与AQS.md) 的 AQS 实现（CountDownLatch/Semaphore 用共享模式，CyclicBarrier 用 ReentrantLock+Condition）。

---

## 2. CountDownLatch（倒数门闩）★

**用途**：一个或多个线程等待其他线程完成操作（**一等多**）。

```java
// 场景: 主线程等 3 个任务全部完成再继续
CountDownLatch latch = new CountDownLatch(3);   // 计数值 3

ExecutorService pool = Executors.newFixedThreadPool(3);
for (int i = 0; i < 3; i++) {
    pool.submit(() -> {
        try {
            Thread.sleep(1000);        // 模拟任务
            System.out.println("任务完成");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            latch.countDown();          // 计数减 1(必须 finally!)
        }
    });
}

latch.await();                          // 主线程阻塞, 计数到 0 才放行
System.out.println("所有任务完成, 继续");
```

**核心方法**：

| 方法 | 作用 |
|---|---|
| `CountDownLatch(int count)` | 构造，初始计数 |
| `await()` | 阻塞直到计数为 0 |
| `await(timeout, unit)` | 限时等待 |
| `countDown()` | 计数减 1 |
| `getCount()` | 当前计数 |

> ⚠️ **不可复用**：计数到 0 后 Latch 失效，不能重置（可复用场景用 CyclicBarrier/Phaser）。

---

## 3. CyclicBarrier（循环栅栏）★

**用途**：N 个线程互相等待，**全部到达栅栏**后才继续（**齐头并进**），且可循环使用。

```java
// 场景: 3 个线程各自准备, 全部就绪后同时开始
CyclicBarrier barrier = new CyclicBarrier(3, () -> {
    System.out.println("=== 全部就绪, 开跑 ===");   // 可选: 到达时回调
});

ExecutorService pool = Executors.newFixedThreadPool(3);
for (int i = 0; i < 3; i++) {
    pool.submit(() -> {
        try {
            System.out.println(Thread.currentThread().getName() + " 准备中...");
            Thread.sleep(500);
            barrier.await();            // 等待其他线程(都到齐才放行)
            System.out.println(Thread.currentThread().getName() + " 出发!");
        } catch (Exception e) {
            // InterruptedException / BrokenBarrierException
        }
    });
}
```

**核心特性**：

| 特性 | 说明 |
|---|---|
| 可复用 | 计数到 0 自动重置（循环栅栏） |
| 回调 | 构造参数可传 Runnable（全部到达时执行） |
| BrokenBarrierException | 某线程中断/超时，栅栏"破碎"，其余线程抛此异常 |

---

## 4. Semaphore（信号量）★

**用途**：控制同时访问资源的线程数（**限流**），类似"停车场车位"。

```java
// 场景: 限流, 最多 3 个线程同时执行
Semaphore semaphore = new Semaphore(3);   // 3 个许可

ExecutorService pool = Executors.newFixedThreadPool(10);
for (int i = 0; i < 10; i++) {
    pool.submit(() -> {
        try {
            semaphore.acquire();         // 获取许可(无则阻塞)
            System.out.println(Thread.currentThread().getName() + " 进入");
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            semaphore.release();          // 释放许可(必须 finally!)
        }
    });
}
```

**核心方法**：

| 方法 | 作用 |
|---|---|
| `Semaphore(int permits)` | 构造，许可数 |
| `Semaphore(int permits, boolean fair)` | 可配公平 |
| `acquire()` | 获取许可（阻塞） |
| `acquire(n)` | 获取 n 个许可 |
| `tryAcquire()` | 尝试获取（立即返回） |
| `release()` | 释放许可 |

**经典场景**：数据库连接池、接口限流、信号灯。

> ⚠️ **易错**：`release()` 必须放在 finally（忘释放 = 许可泄漏 = 后续线程全阻塞）。

---

## 5. CountDownLatch vs CyclicBarrier

| 维度 | CountDownLatch | CyclicBarrier |
|---|---|---|
| 语义 | 一等多（主线程等任务） | 多等多（互相等待） |
| 计数方向 | 递减（countDown） | 不减（到达 await 即可） |
| 可复用 | ❌ 一次性 | ✅ 可循环 |
| 回调 | ❌ | ✅ 支持 |
| 底层 | AQS 共享模式 | ReentrantLock + Condition |
| 典型场景 | 任务汇总/启动等待 | 分阶段并行/数据对齐 |

**选型**：
- 主线程等子任务完成 → **CountDownLatch**
- 多个线程同时出发/分阶段 → **CyclicBarrier**
- 控制并发数 → **Semaphore**

---

## 6. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #U1 | countDown 不在 finally | 任务异常时主线程永远等待 | finally 中 countDown |
| #U2 | release 不在 finally | Semaphore 许可泄漏 | finally 中 release |
| #U3 | Latch 用完想复用 | 第二次 await 无效 | 换 CyclicBarrier |
| #U4 | await 无超时 | 死等（任务挂了） | await(timeout) 限时 |
| #U5 | CyclicBarrier 线程中断 | BrokenBarrierException 混乱 | 统一异常处理 |
| #U6 | 计数设错（大于任务数） | 永远等不到 | 计数 = 任务数精确设置 |

## 小结

- CountDownLatch：一等多（倒数门闩），一次性
- CyclicBarrier：多等多（栅栏），可复用 + 回调
- Semaphore：限流（信号量），acquire/release 必须配对
- 三者基于 AQS，选型看场景：汇总/等待/限流

## 下一篇

[05-JUC其他类与场景补充](05-JUC其他类与场景补充.md)——CompletableFuture/ForkJoinPool 等

## 参考资料

- [JavaGuide: JUC 工具类](https://javaguide.cn/java/concurrent/java-concurrent-questions-02.html)，查询日期：2026-08-09
- [java.util.concurrent 官方文档](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)，查询日期：2026-08-09
