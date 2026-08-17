---
tags: [JUC, CompletableFuture, ForkJoinPool, StampedLock, Exchanger, Phaser, 并发, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/JUC）
归属: 01-学习/Java/JDK基础库/并发/JUC
---

# 05-JUC其他类与场景补充

> 版本基线：JDK 8+（CompletableFuture JDK8 / ForkJoinPool JDK7 / StampedLock JDK8）
> 受众：Java 后端开发，已掌握 JUC 四大重点（[01-JUC之锁与AQS](01-JUC之锁与AQS.md)~[04-JUC之工具类](04-JUC之工具类.md)），本片作为补充速览。
> 关联笔记：[00-JUC总览](00-JUC总览.md)、[04-JUC之工具类](04-JUC之工具类.md)、[01-Java线程池原理与参数详解](../线程池/01-Java线程池原理与参数详解.md)

## 📋 总纲

- 1. CompletableFuture（异步编程）★
- 2. ForkJoinPool（分治并行）
- 3. StampedLock（乐观读锁）
- 4. Exchanger（数据交换）
- 5. Phaser（分阶段协作）
- 6. 其他小工具
- 7. 场景速查

## 学习目标

学完本篇你能：

1. 用 CompletableFuture 做异步任务编排（thenApply/whenComplete/allOf）
2. 理解 ForkJoinPool 的分治思想
3. 用 StampedLock 优化读多写少
4. 认识 Exchanger/Phaser 等小众工具的使用场景
5. 按场景快速定位工具类

## 前置知识

- [04-JUC之工具类](04-JUC之工具类.md)——线程协作基础
- [01-Java线程池原理与参数详解](../线程池/01-Java线程池原理与参数详解.md)——ForkJoinPool 是特殊线程池
- 需掌握：线程池、Future 概念

---

## 1. CompletableFuture（异步编程）★

**场景**：异步任务 + 回调编排（替代回调地狱/手动 Future.get 阻塞）。

**代码**：

```java
// 异步执行 + 结果处理
CompletableFuture.supplyAsync(() -> {
    return "结果";                    // 异步任务(默认 ForkJoinPool.commonPool)
}).thenApply(r -> r + " 处理")        // 串行转换
  .thenAccept(System.out::println);   // 消费

// 两个任务并行聚合
CompletableFuture<Integer> f1 = CompletableFuture.supplyAsync(() -> 10);
CompletableFuture<Integer> f2 = CompletableFuture.supplyAsync(() -> 20);
f1.thenCombine(f2, (a, b) -> a + b)
  .thenAccept(sum -> System.out.println("合计: " + sum));   // 30

// 等待多个任务全部完成
CompletableFuture.allOf(f1, f2).join();

// 异常处理
CompletableFuture.supplyAsync(() -> {
    if (true) throw new RuntimeException("失败");
    return 1;
}).exceptionally(e -> {
    System.out.println("兜底: " + e.getMessage());
    return 0;
});
```

**常用方法**：

| 方法 | 作用 |
|---|---|
| `supplyAsync()` | 异步执行（返回结果） |
| `thenApply/thenAccept/thenRun` | 串行：转换/消费/执行 |
| `thenCombine` | 两个任务合并 |
| `allOf/anyOf` | 等待全部/任一完成 |
| `exceptionally/handle` | 异常处理 |
| `thenCompose` | 异步组合（扁平化） |

> 💡 **记忆锚点**：**CompletableFuture = 异步任务 + 回调编排**，把"Future 的阻塞等待"变成"回调链"。

---

## 2. ForkJoinPool（分治并行）

**场景**：大任务拆小任务并行处理（**分治**），如大数据求和、归并排序。

**代码**：

```java
// 1~100 求和(递归拆分)
class SumTask extends RecursiveTask<Long> {
    private final long[] arr; private final int lo, hi;
    private static final int THRESHOLD = 10;

    SumTask(long[] arr, int lo, int hi) { this.arr = arr; this.lo = lo; this.hi = hi; }

    @Override
    protected Long compute() {
        if (hi - lo <= THRESHOLD) {          // 足够小: 直接算
            long sum = 0;
            for (int i = lo; i < hi; i++) sum += arr[i];
            return sum;
        }
        int mid = (lo + hi) / 2;
        SumTask left = new SumTask(arr, lo, mid);
        SumTask right = new SumTask(arr, mid, hi);
        left.fork();                          // 拆分并行
        return right.compute() + left.join(); // 合并结果
    }
}

// 使用
long[] arr = new long[1000];
ForkJoinPool pool = new ForkJoinPool();      // 或 ForkJoinPool.commonPool()
long sum = pool.invoke(new SumTask(arr, 0, arr.length));
```

**要点**：`RecursiveTask`（有返回）/ `RecursiveAction`（无返回），`fork` 拆分 + `join` 合并。CompletableFuture 默认用 ForkJoinPool.commonPool。

---

## 3. StampedLock（乐观读锁）

**场景**：读多写少 + 要求比 ReadWriteLock 更高吞吐（**乐观读不阻塞写**）。

**代码**：

```java
StampedLock lock = new StampedLock();
double x = 1.0, y = 2.0;

// 乐观读(不真正加锁)
long stamp = lock.tryOptimisticRead();       // 拿"版本号"
double cx = x, cy = y;
if (!lock.validate(stamp)) {                 // 期间被写过?
    stamp = lock.readLock();                 // 升级为悲观读锁
    try { cx = x; cy = y; } finally { lock.unlockRead(stamp); }
}

// 写
long ws = lock.writeLock();
try { x = 10; } finally { lock.unlockWrite(ws); }
```

| 特点 | 说明 |
|---|---|
| 乐观读 | 不阻塞写线程（读时若有写则重试） |
| 悲观读/写 | 与 ReadWriteLock 类似 |
| 不可重入 | ⚠️ 使用需谨慎（锁降级/升级复杂） |
| 适用 | 极高并发读 + 低写频率 |

> ⚠️ **注意**：StampedLock 不可重入，且不支持 Condition——复杂场景用 ReadWriteLock 更稳。

---

## 4. Exchanger（数据交换）

**场景**：**两个线程**交换数据（配对交换），如生产者-消费者交换缓冲。

**代码**：

```java
Exchanger<String> exchanger = new Exchanger<>();

new Thread(() -> {
    try {
        String received = exchanger.exchange("线程A的数据");   // 阻塞等对方交换
        System.out.println("A 收到: " + received);
    } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
}).start();

new Thread(() -> {
    try {
        String received = exchanger.exchange("线程B的数据");
        System.out.println("B 收到: " + received);
    } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
}).start();
// 输出: A 收到: 线程B的数据 / B 收到: 线程A的数据
```

**特点**：必须**成对**（单线程 exchange 会一直阻塞）；经典场景：双缓冲数据流水线。

---

## 5. Phaser（分阶段协作）

**场景**：CyclicBarrier 的增强版——**多阶段**任务（每阶段等齐再进入下一阶段），可动态增减参与者。

**代码**：

```java
Phaser phaser = new Phaser(3);   // 3 个参与者

// 每线程执行多阶段
for (int stage = 1; stage <= 3; stage++) {
    // 阶段工作...
    phaser.arriveAndAwaitAdvance();   // 等本阶段所有人到齐, 进入下一阶段
}
phaser.arriveAndDeregister();         // 完成, 注销参与者
```

**对比**：CountDownLatch 一次性、CyclicBarrier 单阶段循环、**Phaser 多阶段 + 动态参与者**。

---

## 6. 其他小工具

| 类 | 场景 | 代码要点 |
|---|---|---|
| **ThreadLocalRandom** | 并发随机数（比 Random 线程安全） | `ThreadLocalRandom.current().nextInt(100)` |
| **TimeUnit** | 时间单位（sleep 可读） | `TimeUnit.SECONDS.sleep(3)` |
| **ThreadLocal** | 线程私有变量 | `ThreadLocal.withInitial(() -> "")` |
| **ConcurrentLinkedQueue** | CAS 无锁队列 | add/poll 无阻塞 |

---

## 7. 场景速查

```
异步回调/任务编排 → CompletableFuture
大任务递归拆分并行 → ForkJoinPool
超高并发读+低频写 → StampedLock
两线程配对交换 → Exchanger
多阶段协作(动态人数) → Phaser
并发随机数 → ThreadLocalRandom
线程私有上下文 → ThreadLocal
```

## 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #O1 | CompletableFuture 忘异常处理 | 异常静默丢失 | exceptionally/handle |
| #O2 | StampedLock 重入 | 死锁 | 不可重入,注意用法 |
| #O3 | Exchanger 单线程调用 | 永久阻塞 | 必须成对 |
| #O4 | ForkJoin 拆分过细 | 开销大于收益 | 合理阈值 THRESHOLD |
| #O5 | 默认 commonPool 线程数少 | 吞吐受限 | 自定义 ForkJoinPool |

## 小结

- CompletableFuture：异步编排利器（最常用补充类）
- ForkJoinPool：分治并行（RecursiveTask fork/join）
- StampedLock：乐观读（极高端并发读）
- Exchanger/Phaser：小众但特定场景有用
- 选型先看场景（见速查表）

## 下一篇

[00-JUC总览](00-JUC总览.md)——回顾 JUC 全景

## 参考资料

- [CompletableFuture 官方 Javadoc](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/CompletableFuture.html)，查询日期：2026-08-09
- [JavaGuide: CompletableFuture](https://javaguide.cn/java/concurrent/completablefuture-intro.html)，查询日期：2026-08-09
- [StampedLock 官方 Javadoc](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/locks/StampedLock.html)，查询日期：2026-08-09
