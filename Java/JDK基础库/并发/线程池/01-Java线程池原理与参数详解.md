---
tags: [Java, 并发, 线程池, ThreadPoolExecutor, 源码, 七参数, Worker, 拒绝策略]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/线程池）
归属: 01-学习/Java/JDK基础库/并发/线程池
---

# Java线程池原理与参数详解

> 适用版本：JDK 8 源码为主线（ThreadPoolExecutor 核心机制 JDK 8~21 基本未变），版本差异见文末
> 关联笔记：[02-Executors工厂方法详解](02-Executors工厂方法详解.md)、[03-线程数设置与虚拟线程选型](03-线程数设置与虚拟线程选型.md)、[04-线程池监控、故障排查与动态调参方案对比](04-线程池监控、故障排查与动态调参方案对比.md)

## 📋 总纲

1. 为什么用线程池：new Thread 的四大问题
2. 七参数逐个详解：每个参数的语义、边界行为与坑
3. execute 源码级执行流程：先入队后扩容的设计原因
4. Worker 线程复用机制：Worker 结构、runWorker、getTask、线程回收
5. 任务队列选型：四种 BlockingQueue 的数据结构与适用场景
6. 拒绝策略：四种内置策略源码、反压原理、自定义
7. execute vs submit：FutureTask 包装与异常路径
8. 任务异常处理：UncaughtExceptionHandler 与 submit 吞异常
9. 状态机与 ctl：高低位位运算、五状态流转
10. 优雅关闭：shutdown / shutdownNow / awaitTermination 源码流程
11. 运行期动态调参 API：六个 set 方法源码语义与易错点
12. 常见误区与版本差异

## 一、为什么用线程池

每次 `new Thread()` 直接开线程的四大问题：

| 问题 | 说明 |
| --- | --- |
| 创建/销毁开销大 | 创建线程要分配栈内存（默认 512KB~1MB）、走系统调用，销毁还要回收，高频场景开销可观 |
| 线程数无上限 | 无节流地 new Thread，高并发下线程数失控，耗尽内存（每个线程栈）与 CPU |
| 上下文切换开销 | 线程过多时 CPU 时间大量耗在切换上，吞吐反而下降 |
| 生命周期无人管 | 线程跑完即死、异常无人兜底、无法统一监控与优雅关闭 |

线程池解决方式：

| 收益 | 机制 |
| --- | --- |
| 降低开销 | 复用已创建线程（Worker 循环取任务），省去创建/销毁 |
| 控制并发 | core/max 双重上限，配合有界队列保护资源 |
| 统一管理 | 线程命名、监控指标、优雅关闭、拒绝策略全部可管 |
| 提升响应 | 有任务即由空闲线程执行，无需等待线程创建 |

## 二、七参数逐个详解

```java
public ThreadPoolExecutor(
    int corePoolSize,                  // ① 核心线程数
    int maximumPoolSize,               // ② 最大线程数
    long keepAliveTime,                // ③ 空闲存活时间
    TimeUnit unit,                     // ④ 时间单位
    BlockingQueue<Runnable> workQueue, // ⑤ 任务队列
    ThreadFactory threadFactory,       // ⑥ 线程工厂
    RejectedExecutionHandler handler)  // ⑦ 拒绝策略
```

### ① corePoolSize 核心线程数

- 定义：常驻线程数。默认**即使空闲也不回收**（keepAliveTime 对核心线程无效）。
- 边界行为：设为 0 时，新任务会**直接入队**而不是先建线程（见 execute 流程第 1 步判断）；只要 `workerCount < corePoolSize` 就新建核心线程，即使有线程空闲（`prestartCoreThread` 可预创建）。
- 与 `allowCoreThreadTimeOut(true)`：开启后核心线程空闲超 keepAliveTime 也会被回收（参考文档提到的方法，源码见 getTask）。
- 易错点：调大/调小要配合 maximumPoolSize 保持 core ≤ max（详见文末动态调参章节）。

### ② maximumPoolSize 最大线程数

- 定义：核心 + 非核心的总上限。`workerCount < maximumPoolSize` 且队列满时才创建非核心线程。
- 边界行为：**队列无界时永远达不到 max**（任务不排队满，扩容分支不触发），max 形同虚设——这是 Executors 默认池的致命伤（见 [02-Executors工厂方法详解](02-Executors工厂方法详解.md)）。
- 校验：构造与 `setMaximumPoolSize` 都要求 max ≥ core，否则抛 IllegalArgumentException。

### ③④ keepAliveTime + unit 空闲存活时间

- 定义：**非核心**线程空闲超过该时长后被回收（getTask 中 poll 超时返回 null）。
- 边界行为：设为 0 表示空闲立即回收（注意仍要等当前任务执行完）；`allowCoreThreadTimeOut(true)` 后对核心线程同样生效。
- 实践：IO 密集池可适当调大（如 60s）避免流量抖动时频繁创建线程。

### ⑤ workQueue 任务队列

- 定义：核心线程满后任务排队等待的容器，必须是 BlockingQueue。
- 关键：**队列容量与 OOM 直接相关**——无界队列（LinkedBlockingQueue 默认）会让任务无限堆积吃光内存。
- 四种队列选型与源码结构见第四章。

### ⑥ threadFactory 线程工厂

- 定义：创建线程的工厂，默认工厂生成 `pool-N-thread-M` 命名、非 daemon、默认优先级的线程。
- 为什么必须自定义：线上 jstack / Arthas 排查时，`pool-1-thread-1` 无法定位是哪个业务池，自定义 `order-pool-%d` 才能快速定位；还可设置 daemon 标志与优先级。
- 实现方式：Guava `new ThreadFactoryBuilder().setNameFormat("order-pool-%d").build()`，或手写 lambda：

```java
ThreadFactory factory = r -> {
    Thread t = new Thread(r, "order-pool-" + counter.incrementAndGet());
    t.setDaemon(false);
    return t;
};
```

### ⑦ handler 拒绝策略

- 定义：队列满且线程达 max 时如何处理新任务。
- 四种内置策略源码与选型见第五章。

## 三、execute 源码级执行流程

JDK 8 `ThreadPoolExecutor.execute()` 完整源码：

```java
public void execute(Runnable command) {
    if (command == null) throw new NullPointerException();
    int c = ctl.get();
    // 第一步：workerCount < corePoolSize → 创建核心线程执行
    if (workerCountOf(c) < corePoolSize) {
        if (addWorker(command, true)) return;
        c = ctl.get();                      // 创建失败（如状态已变）重新读取
    }
    // 第二步：核心线程已满 → 尝试入队
    if (isRunning(c) && workQueue.offer(command)) {
        int recheck = ctl.get();
        // 双重检查：入队后线程池被 shutdown → 移除任务并拒绝
        if (!isRunning(recheck) && remove(command))
            reject(command);
        // 入队后线程数变为 0（核心线程全被回收）→ 补一个空任务线程
        else if (workerCountOf(recheck) == 0)
            addWorker(null, false);
    }
    // 第三步：入队失败（队列满）→ 尝试创建非核心线程
    else if (!addWorker(command, false))
        reject(command);                    // 线程也达 max → 拒绝
}
```

对应决策顺序：

```
1. 运行线程数 < corePoolSize        → 创建核心线程执行
2. 核心线程满 → 任务入 workQueue    → 排队等待
3. 队列满 → 线程数 < maximumPoolSize → 创建非核心线程执行
4. 队列满且线程达 max              → 执行拒绝策略
```

### 为什么"先入队后扩容"

三个设计原因（面试高频追问）：

| 原因 | 说明 |
| --- | --- |
| 队列是缓冲层 | 先让队列吸收突发流量，避免流量尖峰立刻引发线程创建风暴 |
| 线程创建有成本 | 线程创建/销毁走系统调用，非核心线程空闲还会被回收，频繁创建反而劣化性能 |
| 资源控制 | 队列满才扩容，保证 max 只在真正需要时被触及，拒绝策略兜底防失控 |

## 四、Worker 线程复用机制

Worker 是线程池内部"线程 + 任务"的载体类，**线程复用、空闲回收的核心都在这里**。

### Worker 结构

```java
private final class Worker extends AbstractQueuedSynchronizer implements Runnable {
    final Thread thread;          // 实际执行任务的线程
    Runnable firstTask;           // 首次执行的任务（可为 null）
    volatile long completedTasks; // 完成任务数（用于统计）
}
```

要点：Worker 继承 AQS（简化版），用 AQS 的 state 表示线程忙闲（0=空闲，1=忙），`interruptIdleWorkers` 靠它判断能否安全中断。

### addWorker：创建并启动线程

```java
private boolean addWorker(Runnable firstTask, boolean core) {
    // 双重检查：状态是否允许（RUNNING 或 SHUTDOWN+firstTask==null），
    // workerCount 是否 < corePoolSize(core) / maximumPoolSize(!core)
    ...
    Worker w = new Worker(firstTask);
    Thread t = w.thread;
    workers.add(w);              // 加入 workers 集合（HashSet，重入锁保护）
    t.start();                   // 启动线程 → 执行 runWorker
    ...
}
```

### runWorker：线程主循环（复用的本质）

```java
final void runWorker(Worker w) {
    Thread wt = Thread.currentThread();
    Runnable task = w.firstTask;
    w.firstTask = null;
    ...
    while (task != null || (task = getTask()) != null) {
        w.lock();                       // 标记忙
        beforeExecute(wt, task);        // 钩子
        task.run();                     // 执行任务
        afterExecute(task, null);       // 钩子
        w.completedTasks++;
        w.unlock();
    }
    processWorkerExit(w);               // 拿不到任务 → 线程退出
}
```

**复用的本质**：一个 Worker 线程执行完一个任务后，循环回到 `getTask()` 取下一个任务，不销毁线程——这就是"复用"。

### getTask：取任务与线程回收逻辑

```java
private Runnable getTask() {
    boolean timedOut = false;
    for (;;) {
        ...
        int wc = workerCountOf(c);
        // 关键：是否需要超时回收
        boolean timed = allowCoreThreadTimeOut || wc > corePoolSize;
        ...
        Runnable r = timed ?
            workQueue.poll(keepAliveTime, TimeUnit.NANOSECONDS) :  // 非核心：带超时
            workQueue.take();                                      // 核心：无限阻塞
        if (r != null) return r;
        timedOut = true;                    // poll 超时没取到任务
        ...
        if (timedOut && timed) {            // 超时且允许回收
            if (compareAndDecrementWorkerCount(c)) return null;    // 线程退出
            continue;
        }
    }
}
```

| 场景 | 取任务方式 | 行为 |
| --- | --- | --- |
| 核心线程（默认） | `take()` 无限阻塞 | 队列空则一直挂起等待，永不超时回收 |
| 非核心线程 | `poll(keepAliveTime)` | 空闲超过 keepAliveTime → 返回 null → 线程退出回收 |
| 开启 allowCoreThreadTimeOut | `poll(keepAliveTime)` | 核心线程也按超时回收 |

配套方法：`prestartCoreThread()` 预创建一个核心线程（避免首批任务排队等创建）；`prestartAllCoreThreads()` 预创建全部核心线程。

## 五、任务队列选型

| 队列 | 数据结构 | 锁/公平 | 容量 | 适用场景 | 坑 |
| --- | --- | --- | --- | --- | --- |
| ArrayBlockingQueue | 数组环形 | 单锁，可公平/非公平 | 必须指定 | 通用首选，容量明确 | 容量小容易触发拒绝 |
| LinkedBlockingQueue | 链表 | 双锁（put/take 分离） | 可无界可有界 | 高吞吐；Executors 默认用无界版 | 无界 → 任务堆积 OOM |
| SynchronousQueue | 无存储（交接） | 可公平/非公平 | 0（不存任务） | CachedThreadPool 配套，零缓冲 | 必须立即有线程接走，否则扩容/拒绝 |
| PriorityBlockingQueue | 二叉堆 | 单锁 | 无界 | 任务带优先级 | 无界 → OOM；任务需实现 Comparable |

选型要点：

- **ArrayBlockingQueue vs LinkedBlockingQueue**：性能差异不大；ABQ 容量必须显式给出（天然有界，推荐）；LBQ 无界版有隐患（见 [02-Executors工厂方法详解](02-Executors工厂方法详解.md)）。
- **SynchronousQueue 行为**：提交的任务不排队，直接尝试交给空闲线程；无空闲线程时触发扩容（非核心），达到 max 后直接拒绝——所以 CachedThreadPool 用 SynchronousQueue + max=MAX_VALUE 组合实现"来任务即开线程"。
- **容量与 OOM**：任务对象本身占内存，无界队列 + 任务产生速度 > 消费速度 = 内存持续增长直至 OOM。有界队列 + 拒绝策略是唯一安全的组合。

## 六、拒绝策略

四种内置策略源码级对比：

```java
// AbortPolicy（默认）：直接抛异常
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    throw new RejectedExecutionException("Task " + r.toString() + " rejected from " + e.toString());
}

// CallerRunsPolicy：提交线程自己执行（不丢任务 + 天然反压）
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    if (!e.isShutdown()) r.run();          // 谁提交谁执行 → 提交方被迫降速
}

// DiscardPolicy：静默丢弃
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) { }

// DiscardOldestPolicy：丢队首最老任务，再重试提交
public void rejectedExecution(Runnable r, ThreadPoolExecutor e) {
    if (!e.isShutdown()) {
        e.getQueue().poll();               // 丢弃最老任务
        e.execute(r);                      // 重新尝试提交新任务
    }
}
```

| 策略 | 行为 | 适用 | 代价 |
| --- | --- | --- | --- |
| AbortPolicy | 抛 RejectedExecutionException | 不允许丢任务、可接受异常中断 | 调用方要处理异常 |
| CallerRunsPolicy | 提交线程自己跑 | 降速不丢任务（反压） | 提交线程被阻塞，接口 RT 上升 |
| DiscardPolicy | 静默丢弃 | 允许丢数据 | 无声无息，易被忽视 |
| DiscardOldestPolicy | 丢最老任务重试 | 允许丢旧任务、业务看重新数据 | 老任务可能已产生副作用 |

**CallerRunsPolicy 反压原理**：任务由提交线程（如 Tomcat 工作线程）同步执行，该线程被占住 → 后续请求没有线程处理 → 服务天然降速 → 上游积压反馈。这是"降速而不丢任务"的首选。

自定义拒绝策略（生产常用）：落库 + 告警 + 投递 MQ 重试，把"被拒"当做过载信号显式处理：

```java
executor.setRejectedExecutionHandler((r, e) -> {
    log.warn("task rejected, queue={}, active={}", e.getQueue().size(), e.getActiveCount());
    retryStore.save(r);   // 落库待补偿
    alert.notify("线程池过载");
});
```

## 七、execute vs submit

| 维度 | `execute(Runnable)` | `submit(Runnable/Callable)` |
| --- | --- | --- |
| 返回值 | 无 | `Future<T>` |
| 底层包装 | 直接执行 | 包装成 `FutureTask` 后执行 |
| 异常处理 | 抛给线程（UncaughtExceptionHandler 兜底） | 封装进 Future，`get()` 时抛 ExecutionException |
| 入参 | Runnable | Runnable / Callable / 任意值 |

submit 的源码本质（AbstractExecutorService）：

```java
public <T> Future<T> submit(Callable<T> task) {
    ...
    FutureTask<T> ft = new FutureTask<>(task);   // 包装
    execute(ft);                                  // 最终还是 execute
    return ft;
}
```

```java
Future<Integer> future = pool.submit(() -> compute());
try {
    Integer result = future.get();          // 阻塞等待；任务异常时抛 ExecutionException
} catch (ExecutionException e) {
    Throwable cause = e.getCause();         // 真正的业务异常
}
```

易错点：submit 的异常被吞进 Future，**不调 get() 永远发现不了**；调 get() 又可能阻塞——用 `get(timeout)` 或 `isDone()` 轮询规避。

## 八、任务异常处理

| 提交方式 | 异常去向 | 兜底手段 |
| --- | --- | --- |
| execute(Runnable) | 任务 run() 抛出 → 线程终止，异常打印到 stderr | ① 任务内 try-catch ② 自定义 ThreadFactory 设置 UncaughtExceptionHandler |
| submit(...) | 包装进 Future，线程不终止 | get() 时显式捕获 |

```java
// 自定义 UncaughtExceptionHandler：execute 任务异常的统一兜底
ThreadFactory factory = r -> {
    Thread t = new Thread(r, "order-pool-" + counter.incrementAndGet());
    t.setUncaughtExceptionHandler((thread, e) -> log.error("task failed: {}", thread.getName(), e));
    return t;
};
```

注意：UncaughtExceptionHandler 只能兜 execute 的异常；submit 的异常仍在 Future 里，需业务侧 get() 处理。最佳实践是任务内部自行 try-catch 保证不中断线程。

## 九、状态机与 ctl

ctl 是一个 AtomicInteger，**高 3 位 = 运行状态，低 29 位 = worker 线程数**（一个 int 存两份信息，保证状态+线程数原子更新）：

```java
private final AtomicInteger ctl = new AtomicInteger(ctlOf(RUNNING, 0));
private static final int COUNT_BITS = Integer.SIZE - 3;   // 29
private static final int CAPACITY   = (1 << COUNT_BITS) - 1;

// 状态值（依次增大，可比较大小）
private static final int RUNNING    = -1 << COUNT_BITS;
private static final int SHUTDOWN   =  0 << COUNT_BITS;
private static final int STOP       =  1 << COUNT_BITS;
private static final int TIDYING    =  2 << COUNT_BITS;
private static final int TERMINATED =  3 << COUNT_BITS;

// 位运算取数
private static int runStateOf(int c)     { return c & ~CAPACITY; }   // 取高 3 位
private static int workerCountOf(int c)  { return c & CAPACITY; }     // 取低 29 位
```

| 状态 | 值（高位） | 接受新任务 | 处理队列任务 | 中断执行中任务 |
| --- | --- | --- | --- | --- |
| RUNNING | 负数 | ✅ | ✅ | 否 |
| SHUTDOWN | 0 | ❌ | ✅（跑完队列） | 否 |
| STOP | 正数 | ❌ | ❌（清空队列） | ✅ |
| TIDYING | 更大 | 线程数=0，准备执行 terminated() | - | - |
| TERMINATED | 最大 | terminated() 已执行完毕 | - | - |

状态流转（不可逆，只能单向推进）：

```
RUNNING --shutdown()--> SHUTDOWN --队列清空+线程归零--> TIDYING --terminated()--> TERMINATED
   |                        |
   |--shutdownNow()--------> STOP --中断全部线程--> TIDYING -----------------------> TERMINATED
```

## 十、优雅关闭

### shutdown()：温和关闭

```java
public void shutdown() {
    final ReentrantLock mainLock = this.mainLock;
    mainLock.lock();
    try {
        advanceRunState(SHUTDOWN);        // 状态置 SHUTDOWN：不再接受新任务
        interruptIdleWorkers();           // 中断空闲线程（忙线程不打断）
        onShutdown();                     // 钩子（ScheduledThreadPoolExecutor 用来处理延迟队列）
    } finally { mainLock.unlock(); }
    tryTerminate();
}
```

### shutdownNow()：强制关闭

```java
public List<Runnable> shutdownNow() {
    ...
    advanceRunState(STOP);                // 状态置 STOP
    interruptWorkers();                   // 中断所有线程（含忙线程）
    tasks = drainQueue();                 // 清空队列，返回未执行任务列表
    ...
}
```

### 完整关闭模板

```java
pool.shutdown();                                        // ① 不再收新任务
if (!pool.awaitTermination(60, TimeUnit.SECONDS)) {     // ② 等待队列任务跑完
    List<Runnable> dropped = pool.shutdownNow();        // ③ 超时强制中断
    // ④ dropped 中未执行的任务落库/投递补偿，避免任务丢失
    if (!pool.awaitTermination(30, TimeUnit.SECONDS)) {
        log.error("线程池未能完全终止");                   // ⑤ 仍然没停 → 告警
    }
}
```

易错点：

- `shutdownNow` 只发中断信号，任务若吞掉 InterruptedException 仍会继续跑。
- `shutdownNow` 返回未执行任务列表，需自行补偿，否则任务静默丢失。
- 任务内要响应中断（处理 InterruptedException 时恢复中断位 `Thread.currentThread().interrupt()`），否则关闭流程会被卡住。

## 十一、运行期动态调参 API

ThreadPoolExecutor 运行期间无需重建实例即可调整参数（动态调参是[04-线程池监控、故障排查与动态调参方案对比](04-线程池监控、故障排查与动态调参方案对比.md)的基础）：

| 方法 | 语义 | 生效范围 |
| --- | --- | --- |
| `setCorePoolSize(int)` | 调整核心线程数 | 立即影响后续任务决策 |
| `setMaximumPoolSize(int)` | 调整最大线程数 | 立即影响后续扩容/拒绝 |
| `setKeepAliveTime(long, TimeUnit)` | 调整空闲线程存活时间 | 立即影响空闲线程回收节奏 |
| `setThreadFactory(ThreadFactory)` | 替换线程工厂 | 新创建的线程生效 |
| `setRejectedExecutionHandler(...)` | 替换拒绝策略 | 新被拒任务生效 |
| `setAllowCoreThreadTimeOut(boolean)` | 开关核心线程超时回收 | 立即生效 |

### 实时生效原理

相关字段均为 volatile（或在锁内读取），execute/addWorker/getTask 每次决策现读现值，无配置缓存，set 后下一次决策立即按新值走。

### setCorePoolSize 源码语义

```java
int delta = corePoolSize - this.corePoolSize;
this.corePoolSize = corePoolSize;
if (workerCountOf(ctl.get()) > corePoolSize)
    interruptIdleWorkers();                    // 缩小：只中断空闲 worker
else if (delta > 0) {
    int k = Math.min(delta, workQueue.size()); // 放大：按队列积压量启发式预创建
    while (k-- > 0 && addWorker(null, true)) {
        if (workQueue.isEmpty()) break;
    }
}
```

### setMaximumPoolSize 源码语义

```java
if (maximumPoolSize <= 0 || maximumPoolSize < corePoolSize)
    throw new IllegalArgumentException();      // 必须 >= core
this.maximumPoolSize = maximumPoolSize;
if (workerCountOf(ctl.get()) > maximumPoolSize)
    interruptIdleWorkers();                    // 缩小：只中断空闲 worker
```

### 边界与易错点

① **正在执行的线程不打断**：interruptIdleWorkers 只针对空闲线程（借助 Worker 的 AQS 状态判断），已运行任务跑完为止。动态调参控制"池规模决策"，不中断任务。

② **core > max 的坑**：setCorePoolSize 不做 max 校验，core 一旦超过 max，addWorker 按 core 为基准判断，核心线程可突破 maximumPoolSize。口诀：**调大先 max 后 core，调小先 core 后 max**。

③ **Executors 包装类陷阱**：newFixedThreadPool/newCachedThreadPool 返回 ThreadPoolExecutor 可直接强转；newSingleThreadExecutor 返回 FinalizableDelegatedExecutorService 包装，强转抛 ClassCastException（详见 [02-Executors工厂方法详解](02-Executors工厂方法详解.md)）。

④ **keepAliveTime 触发**：由空闲 worker 的 getTask 中 poll 超时自然触发，无需额外动作。

## 十二、常见误区

- 认为提交任务"先扩容到 max 再入队"（实际先入队）。
- 用 Executors 图省事，埋下 OOM 隐患（详见 [02-Executors工厂方法详解](02-Executors工厂方法详解.md)）。
- 不给线程命名，线上 dump 无法定位是哪个池。
- 用无界队列还指望 maximumPoolSize 生效。
- 线程池用完不 shutdown，线程泄漏导致应用关不掉。
- submit 的任务异常不 get() 发现不了。
- 调整参数把 core 调到超过 max，产生诡异行为。
- shutdownNow 后不补偿未执行任务，任务静默丢失。
- 以为 allowCoreThreadTimeOut 默认开启（实际默认 false，核心线程常驻）。

## 十三、版本差异

| 版本 | 变化 |
| --- | --- |
| JDK 8 | 上述源码对应版本；CompletableFuture 增强异步编排 |
| JDK 19/21 | 虚拟线程（JEP 444）落地，IO 密集可用海量虚拟线程替代传统池（详见 [03-线程数设置与虚拟线程选型](03-线程数设置与虚拟线程选型.md)） |
| JDK 21~23 | synchronized 阻塞虚拟线程仍会 pin 载体线程（JEP 491 于 JDK 24 修复） |
| JDK 24 | JEP 491：synchronized 不再 pin 虚拟线程，JFR 新增 jdk.VirtualThreadPinned 事件用于检测残余 pin |

ThreadPoolExecutor 核心机制（ctl/Worker/execute/getTask/拒绝策略）自 JDK 5 定稿后基本稳定，JDK 8 与 JDK 21 源码几乎一致，学习以 JDK 8 源码为准即可。

## 参考资料

- [Java SE 8 ThreadPoolExecutor 源码](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/ThreadPoolExecutor.html)，查询日期：2026-08-08
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)，查询日期：2026-08-08
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491)，查询日期：2026-08-08
- [美团技术团队：Java线程池实现原理及其在美团业务中的实践](https://tech.meituan.com/2020/04/02/java-pooling-pratice-in-meituan.html)，查询日期：2026-08-08
- 桌面面试素材《线程池原理与参数.md》为本文知识点索引来源
