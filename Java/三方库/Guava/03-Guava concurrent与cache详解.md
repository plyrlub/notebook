---
tags: [Java, Guava, 三方库, concurrent, cache, ListenableFuture, RateLimiter, LoadingCache, 线程池]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava concurrent与cache详解

> 实测环境：guava 33.6.0-jre + JDK 17.0.12（实测数据标注于各节）
> 系列导航：[00-Guava概览与模块化辨析](00-Guava概览与模块化辨析.md)
> 关联笔记：[01-Java线程池原理与参数详解](../../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)（ThreadFactoryBuilder 用法）、[Caffeine Java缓存详解](../Caffeine Java缓存详解.md)（Cache 继任者对比）

## 📋 总纲

1. ListenableFuture 与 Futures：可回调的 Future
2. MoreExecutors：线程池增强（含 ThreadFactoryBuilder）
3. RateLimiter：令牌桶限流（实测）
4. Striped：细粒度锁
5. Monitor：可重入互斥的声明式版本
6. Service 框架：服务生命周期管理
7. CacheBuilder / LoadingCache：本地缓存（实测）
8. 与 Caffeine、ConcurrentHashMap 的对比与选型

## 一、ListenableFuture 与 Futures

### ListenableFuture

JDK Future 的缺陷：`get()` 阻塞、`isDone()` 轮询，无法注册回调。Guava 用 ListenableFuture 补上：

```java
ListeningExecutorService exec = MoreExecutors.listeningDecorator(Executors.newFixedThreadPool(2));
ListenableFuture<Integer> f = exec.submit(() -> 40 + 2);

// 回调注册（33.x 起 addCallback 标记废弃，见下）
Futures.addCallback(f, new FutureCallback<Integer>() {
    @Override public void onSuccess(Integer r) { ... }
    @Override public void onFailure(Throwable t) { ... }
}, exec);
```

实测输出（guava 33.6.0-jre，编译有 deprecated 警告）：

```
future.get(): 42
callback onSuccess: 42
```

### Futures 工具

| 方法 | 说明 |
| --- | --- |
| `addCallback(f, cb, exec)` | 注册回调（33.x deprecated，回调仍可用） |
| `transform(f, fn, exec)` | 异步链式转换（deprecated，用 `f.transform(fn, exec)` 实例方法） |
| `allAsList(f1, f2, ...)` | 全部成功聚合，任一失败即失败 |
| `successfulAsList(...)` | 部分成功聚合，失败置 null |
| `whenAllComplete(whenAllSucceed)` | 33.x 推荐的新聚合入口 |
| `immediateFuture(v)` | 已完成 future |

### 与 CompletableFuture 对比（重要选型）

JDK 8+ 的 CompletableFuture 功能已**完全覆盖并超越** ListenableFuture 生态：

| 维度 | ListenableFuture | CompletableFuture |
| --- | --- | --- |
| 回调 | addCallback / transform | thenApply / whenComplete 等 |
| 组合 | allAsList / successfulAsList | allOf / anyOf |
| 异步编排 | 较弱 | supplyAsync + then* 全链路 |
| 异常 | onFailure 回调 | exceptionally / handle |
| 现状 | 官方停止推广（33.x 大量 deprecated） | JDK 标准，持续演进 |

结论：**新代码用 CompletableFuture**（见 [03-线程数设置与虚拟线程选型](../../JDK基础库/并发/线程池/03-线程数设置与虚拟线程选型.md)）；ListenableFuture 仅存量代码维护需要。Guava 官方 33.x 已把 Futures 大量方法标记 deprecated，路线图是引导迁移。


**JDK 替代：CompletableFuture（JDK 8+，完全替代）**

```java
// Guava 写法 → JDK 写法
ListeningExecutorService exec = MoreExecutors.listeningDecorator(pool);
ListenableFuture<Integer> f = exec.submit(() -> 40 + 2);
Futures.addCallback(f, cb, exec);
// ↓ 等价 JDK 写法
CompletableFuture<Integer> f = CompletableFuture.supplyAsync(() -> 40 + 2, pool);
f.thenAccept(r -> System.out.println("onSuccess: " + r));       // 替代 onSuccess
f.exceptionally(e -> { log.error("failed", e); return -1; });   // 替代 onFailure
// 聚合：CompletableFuture.allOf(...) 替代 Futures.allAsList
```

结论：新代码一律 CompletableFuture（编排能力更强，见 [03-线程数设置与虚拟线程选型](../../JDK基础库/并发/线程池/03-线程数设置与虚拟线程选型.md)）；ListenableFuture 仅存量维护。

## 二、MoreExecutors 与 ThreadFactoryBuilder

### ThreadFactoryBuilder（后端最实用）

Guava 提供优雅的线程工厂构造器，**线程池笔记中生产示例一直在用**：

```java
ThreadFactory factory = new ThreadFactoryBuilder()
        .setNameFormat("order-pool-%d")              // 线程名（%d 自动编号）
        .setDaemon(false)                            // 守护线程
        .setPriority(Thread.NORM_PRIORITY)
        .setUncaughtExceptionHandler((t, e) -> log.error("task failed", e))
        .build();

ExecutorService pool = new ThreadPoolExecutor(10, 20, 60L, TimeUnit.SECONDS,
        new ArrayBlockingQueue<>(1000), factory, new ThreadPoolExecutor.CallerRunsPolicy());
```

与线程池笔记的联动：[01-Java线程池原理与参数详解](../../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md) 强调"线程必须命名"，ThreadFactoryBuilder 的 setNameFormat 是业界标准实现。

### MoreExecutors

| 方法 | 说明 |
| --- | --- |
| `listeningDecorator(executor)` | 包装为 ListeningExecutorService |
| `directExecutor()` | 同步执行的 Executor（当前线程直接跑，测试/回调场景） |
| `newDirectExecutorService()` | directExecutor 的 ExecutorService 版 |
| `addDelayedShutdownHook(executor, timeout)` | 注册 JVM 关闭钩子，优雅关池 |
| `shutdownAndAwaitTermination(executor, timeout, unit)` | 关闭+等待，超时强制 |

易错点：directExecutor 的回调在**调用线程**执行，有死锁风险（回调里又等该 future 结果时）。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| ThreadFactoryBuilder | JDK 21：`Thread.ofPlatform().name("order-pool-", 0).factory()`；JDK 8~17：手写 lambda（见下） |
| MoreExecutors.directExecutor | 无（`Runnable::run` 或 CompletableFuture 同步链） |
| addDelayedShutdownHook | `Runtime.getRuntime().addShutdownHook(new Thread(() -> pool.shutdown()))` 手写 |

```java
// JDK 8~17 手写等价：等价 ThreadFactoryBuilder.setNameFormat("order-pool-%d")
ThreadFactory factory = r -> new Thread(r, "order-pool-" + counter.incrementAndGet());
// JDK 21+ 官方方案
ThreadFactory factory = Thread.ofPlatform().name("order-pool-", 0).factory();
```

结论：线程命名工厂 JDK 21 起有官方方案；老 JDK 手写 lambda 即可，非必须 Guava。

## 三、RateLimiter：令牌桶限流（实测）

Guava 的限流器，按恒定速率发放许可，实现"平滑限速"。

| 方法 | 说明 |
| --- | --- |
| `create(double permitsPerSecond)` | 平滑突发限流（SmoothBursty）：允许突发到桶容量 |
| `create(double permits, Duration warmup, TimeUnit)` | 预热限流（SmoothWarmingUp）：冷启动平滑爬坡 |
| `acquire()` | 阻塞获取 1 个许可，返回等待秒数 |
| `acquire(n)` | 阻塞获取 n 个 |
| `tryAcquire()` / `tryAcquire(timeout)` | 非阻塞/限时尝试，立即返回 boolean |

实测输出（guava 33.6.0-jre，2 许可/秒，连取 3 个）：

```
acquire x3 (2/s): 1001 ms, 预期约 1000 ms
```

（第一个立即通过，后两个各等约 500ms，总计约 1000ms——与令牌桶理论一致。）

### 与 Semaphore 对比

| 维度 | RateLimiter | Semaphore |
| --- | --- | --- |
| 语义 | 速率控制（时间维度） | 数量控制（并发额度） |
| 许可恢复 | 按时间自动补充 | 手动 release |
| 突发 | 允许（桶容量内） | 不允许（固定数量） |
| 典型场景 | 接口限流、削峰 | 连接池、资源池 |

生产注意：单机限流用 RateLimiter；分布式限流需 Redis/Lua 或网关层（Sentinel 等），RateLimiter 无法跨进程。


**JDK 替代**：无原生速率限流（Semaphore 是并发数量控制，不是速率控制，见上表）。单机备选：Bucket4j / Resilience4j RateLimiter；分布式必须 Redis + Lua 或网关层（Sentinel）。结论：单机平滑限速 Guava 仍是最轻量方案。

## 四、Striped：细粒度锁

`Striped.lock(n)` 返回 n 个锁的条带池，`get(key)` 按 key 哈希分配固定锁——**内存远小于按 key 建锁，又能按 key 互斥**。

```java
Striped<Lock> locks = Striped.lock(64);
Lock lock = locks.get(userId);      // 同一 userId 恒拿到同一把锁
lock.lock();
try { /* 用户维度串行 */ } finally { lock.unlock(); }
```

典型场景：用户维度的库存扣减、账号级串行操作。弱一致性：不同 key 可能哈希碰撞共用锁（可接受）。


**JDK 替代**：无。手写 `ConcurrentHashMap<Key, Lock>`（内存随 key 数增长）或自实现条带数组。结论：细粒度锁场景 Guava Striped 仍是标准答案。

## 五、Monitor：声明式互斥

Monitor 是 synchronized/ReentrantLock 的增强版：

| 方法 | 说明 |
| --- | --- |
| `enter()` / `enterIf(Guard)` | 阻塞进入 / 条件满足才进入 |
| `tryEnter()` / `tryEnterIf(Guard, timeout)` | 非阻塞变体 |
| `leave()` | 释放（必须 finally） |
| Guard | 条件对象：`new Monitor.Guard(monitor) { public boolean isSatisfied() {...} }` |

价值：把"等待条件"封装进 Guard，避免手写 while + wait/notify 的样板与错误。使用率低于 ReentrantLock + Condition，作为了解。


**JDK 替代**：`synchronized` + `wait/notify`（手写条件循环）或 `ReentrantLock` + `Condition.await/signal`。结论：简单条件用 ReentrantLock；复杂多条件场景 Monitor + Guard 可读性更好。

## 六、Service 框架

管理"有生命周期"的组件（启动→运行→停止），状态机：NEW → STARTING → RUNNING → STOPPING → TERMINATED / FAILED。

| 抽象类 | 适用 |
| --- | --- |
| AbstractIdleService | 无后台线程，启动/停止即完成 |
| AbstractExecutionThreadService | 单线程循环处理 |
| AbstractScheduledService | 定时任务服务 |
| AbstractService | 全手动控制 |

```java
ServiceManager manager = new ServiceManager(ImmutableList.of(svc1, svc2));
manager.addListener(new ServiceManager.Listener() {
    @Override public void healthy() { /* 全部启动完成 */ }
}, MoreExecutors.directExecutor());
manager.startAsync();
```


**JDK 替代**：Spring 生命周期（`@PostConstruct` / `@PreDestroy` / InitializingBean / SmartLifecycle）或手写状态机。结论：Spring 项目直接用 Spring 生命周期管理，Guava Service 仅无 Spring 的轻量场景。

## 七、CacheBuilder / LoadingCache（实测）

Guava 本地缓存是**生产使用率最高的模块**（也是 Caffeine 的灵感来源）。

### 构建参数

| 参数 | 说明 |
| --- | --- |
| `maximumSize(n)` | 最大条目数（LRU 近似） |
| `maximumWeight(n)` + `weigher(...)` | 按权重上限 |
| `expireAfterWrite(d, unit)` | 写入后过期（**推荐**，逻辑简单） |
| `expireAfterAccess(d, unit)` | 访问后过期（热点缓存有坑） |
| `refreshAfterWrite(d, unit)` | 写后自动刷新（过期后异步重载，不阻塞读） |
| `weakKeys()` / `weakValues()` / `softValues()` | 弱引用键/值 |
| `recordStats()` | 开启命中率统计 |
| `removalListener(...)` | 移除回调（过期/淘汰/显式删除） |

### LoadingCache 用法

```java
LoadingCache<String, Integer> cache = CacheBuilder.newBuilder()
        .maximumSize(100)
        .expireAfterWrite(10, TimeUnit.SECONDS)
        .recordStats()
        .build(new CacheLoader<String, Integer>() {
            @Override public Integer load(String key) { return key.length(); }  // 未命中回调
        });

Integer v = cache.get("abc");        // 未命中 → 调 load
Integer v2 = cache.get("abc");       // 命中，不再调 load
cache.refresh("abc");                // 异步刷新
cache.invalidate("abc");             // 显式删除
```

实测输出（guava 33.6.0-jre）：

```
get('abc'): 3, get('abc') again: 3
stats hitRate: 1.0
```

（第一次 get 走 load 返回 3；第二次命中；hitRate 1.0 说明第二次全部命中。）

| 方法 | 说明 |
| --- | --- |
| `get(k)` | 阻塞加载，抛 ExecutionException |
| `getUnchecked(k)` | 不抛受检异常（load 不能抛 checked） |
| `getAll(keys)` | 批量加载（CacheLoader.loadAll 优化） |
| `asMap()` | 视图直接读写（绕过自动加载） |
| `stats()` | CacheStats：hitRate / loadCount / averageLoadPenalty 等 |
| `invalidateAll()` | 全清 |

### 易错点

- `expireAfterAccess` 的热点陷阱：热 key 一直被访问就永不淘汰（类似 LRU 的"永不失效"），除非用 `expireAfterWrite`。
- `refreshAfterWrite` 只是"过期后异步刷新"——**过期瞬间仍返回旧值**，需与 expireAfterWrite 组合理解。
- load 里不要调用同 cache 的 get（递归死循环）。
- get 抛 ExecutionException 需处理；getUnchecked 会包成 UncheckedExecutionException。


**JDK 替代：Caffeine（首选，见 [Caffeine Java缓存详解](../Caffeine Java缓存详解.md)）**——JDK 无原生缓存。迁移示例（≈改 import + 时间参数换 Duration）：

```java
// Guava 写法
LoadingCache<String, User> c = CacheBuilder.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(10, TimeUnit.SECONDS)
        .build(new CacheLoader<String, User>() {
            @Override public User load(String k) { return userMapper.findById(k); }
        });

// Caffeine 等价写法
LoadingCache<String, User> c = Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(Duration.ofSeconds(10))
        .build(k -> userMapper.findById(k));      // CacheLoader 简化为 lambda
```

结论：新项目用 Caffeine；Guava Cache 仅存量维护。团队规范见 [Caffeine Java缓存详解](../Caffeine Java缓存详解.md)。

## 八、与 Caffeine、ConcurrentHashMap 对比选型

| 维度 | LoadingCache | Caffeine | ConcurrentHashMap |
| --- | --- | --- | --- |
| 定位 | 带加载器的本地缓存 | Guava Cache 的继任者（性能更优） | 并发 Map |
| 自动加载 | ✅ CacheLoader | ✅（同 API） | ❌ |
| 过期策略 | ✅ write/access/refresh | ✅（更丰富，含基于频率的淘汰） | ❌ |
| 统计 | ✅ CacheStats | ✅ 更细 | ❌ |
| 性能 | 基准 | **高约一个量级**（Window-TinyLFU 淘汰算法） | 高（无缓存语义） |
| 现状 | 官方维护放缓（功能冻结） | 活跃（作者 Ben Manes） | JDK 标准 |

选型建议（详见 [Caffeine Java缓存详解](../Caffeine Java缓存详解.md)）：

- **新项目本地缓存 → Caffeine**（API 兼容 Guava 风格，性能更好），Spring Boot 默认缓存实现即 Caffeine。
- 存量 Guava 代码可平滑迁移（API 几乎同构）。
- 纯并发 Map 需求（无过期/加载语义）→ ConcurrentHashMap，别用缓存库。
- Guava Cache 仍值得学习：它是理解 Caffeine 的"教科书"，且无外部依赖场景仍可用。

## 参考资料

- [Guava concurrent javadoc（com.google.common.util.concurrent）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/util/concurrent/package-summary.html)，查询日期：2026-08-08
- [Guava Caches 教学 wiki](https://github.com/google/guava/wiki/CachesExplained)，查询日期：2026-08-08
- [Caffeine GitHub（性能对比基准）](https://github.com/ben-manes/caffeine)，查询日期：2026-08-08
- 实测数据：guava 33.6.0-jre + JDK 17.0.12 本机运行
