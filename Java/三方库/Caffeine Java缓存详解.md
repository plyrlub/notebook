---
tags: [Java, 缓存, Caffeine, SpringBoot]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/三方库）
归属: 01-学习/Java/三方库
---

# Caffeine Java缓存详解

## 📋 总纲

1. 基本概念：本地缓存定位、三种形态、快速上手
2. 使用方法：依赖、构建配置、常用方法、淘汰策略、统计
3. Spring Boot 集成：注解、多缓存区、二级缓存架构
4. 使用注意点与坑：null、不可变、穿透击穿、两级缓存一致性
5. 原理（补充知识）：并发设计、W-TinyLFU、过期机制、性能对比
6. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 什么是 Caffeine

Caffeine 是 Java 的高性能**本地缓存库**，Google Guava Cache 的现代继任者。名字的梗：「咖啡因比咖啡（Guava）更提神」—— 定位就是**在内存里跑得飞快的那一层缓存**。

**核心特性**
- 淘汰算法：W-TinyLFU（不是简单的 LRU）
- 并发设计：无锁读、写入用 Striped 锁，读性能接近 ConcurrentHashMap
- API：与 Guava Cache 高度相似，迁移成本低
- 版本：当前 3.x（如 3.2.x），要求 Java 8+

### 1.2 缓存核心概念

- **命中 / 未命中**：get 时 key 存在 = 命中，直接返回值；不存在 = 未命中，触发加载
- **加载（Loading）**：未命中时如何补数据（自动加载/手动加载/异步加载）
- **淘汰（Eviction）**：容量满了踢谁走 —— Caffeine 用 W-TinyLFU 决定
- **过期（Expiration）**：数据多久失效 —— 基于写入时间或最后访问时间

### 1.3 三种缓存形态

| 形态 | 构建方式 | 未命中行为 | 适用场景 |
|------|---------|-----------|---------|
| `Cache<K,V>` | `Caffeine.newBuilder().build()` | 手动 get，自己处理 | 灵活控制 |
| `LoadingCache<K,V>` | `.build(CacheLoader)` | 自动加载 | 标准「查不到就去 DB」 |
| `AsyncCache<K,V>` | `.buildAsync()` | 异步加载（返回 CompletableFuture） | IO 耗时的加载 |

### 1.4 快速上手

```java
// Maven
// <dependency>
//     <groupId>com.github.ben-manes.caffeine</groupId>
//     <artifactId>caffeine</artifactId>
//     <version>3.2.4</version>
// </dependency>

Cache<String, User> cache = Caffeine.newBuilder()
        .maximumSize(10_000)                    // 最多 1 万个
        .expireAfterWrite(Duration.ofMinutes(5)) // 写入 5 分钟后过期
        .recordStats()                          // 开启命中统计
        .build();

User user = cache.get("u100", key -> userMapper.findById(key));
// 未命中 → 执行加载函数 → 存入缓存 → 返回
```

---

## 2. 使用方法

### 2.1 依赖引入

```xml
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
    <version>3.2.4</version>
</dependency>
```

Spring Boot 项目通常再加 `spring-boot-starter-cache`（见第 3 章）。

### 2.2 构建配置项详解

**① maximumSize / maximumWeight**
```java
Caffeine.newBuilder()
    .maximumSize(10_000)                                  // 按条数
    .maximumWeight(100_000)                               // 按权重（需配 weigher）
    .weigher((k, v) -> v.size())                          // 自定义权重
```
- 解释：容量上限，超过后按 W-TinyLFU 淘汰
- 注意点：**是近似值不是精确值**，基于频率窗口估算；`maximumSize` 和 `maximumWeight` 二选一，不能同时用

**② expireAfterWrite（写入后过期）**
```java
.expireAfterWrite(Duration.ofMinutes(5))
```
- 解释：写入/更新后固定 5 分钟失效，**不管有没有被访问**
- 适用：数据本身有 TTL 语义（如 Token、验证码）

**③ expireAfterAccess（访问后过期）**
```java
.expireAfterAccess(Duration.ofMinutes(5))
```
- 解释：距**最后一次访问** 5 分钟未使用才失效
- 适用：热数据常驻、冷数据让位（类 LRU 的时效语义）

**④ refreshAfterWrite（异步软刷新）**
```java
.refreshAfterWrite(Duration.ofMinutes(5))
```
- 解释：写入 5 分钟后，**下次访问时触发异步刷新**（旧值先返回，后台加载新值）
- 注意点：**只对 LoadingCache/AsyncCache 生效**；配合 `expireAfterWrite` 一起用效果最好（过期兜底 + 刷新保新鲜）

**⑤ removalListener（淘汰监听）**
```java
.removalListener((key, value, cause) ->
    log.info("淘汰: {} 原因: {}", key, cause))
```
- 解释：元素被移除时回调，`cause` 区分原因（SIZE/EXPIRED/EXPLICIT/REPLACED/COLLECTED）
- 适用：资源清理（关闭连接）、监控告警
- 注意点：回调是**异步**执行（默认 ForkJoinPool），别在回调里做重活

**⑥ recordStats（统计）**
```java
.recordStats()
CacheStats stats = cache.stats();
// stats.hitRate() / missCount() / loadSuccessCount() / evictionCount()
```
- 解释：记录命中率、加载次数、淘汰数
- 注意点：有少量性能开销，生产环境按需开；监控命中率用

### 2.3 常用方法详解

**① getIfPresent(K key)**
```java
User u = cache.getIfPresent("u100");   // 命中返回，未命中返回 null
```
- 解释：纯查询，不触发加载
- 注意点：**返回 null 不等于「值不存在」** —— 可能是未命中，也可能是缓存里没存过。无法区分，想区分用 `get(key, fn)` 的返回值或 Optional 包装

**② get(K key, Function<K,V> mappingFunction)**
```java
User u = cache.get("u100", k -> userMapper.findById(k));
```
- 解释：命中返回；未命中则**原子执行加载函数**并存入（其他线程同时 get 同一个 key 会被合并，只加载一次）
- 注意点：加载函数返回 null 时**不会缓存**；加载函数抛异常会传播给调用方且不缓存

**③ put(K key, V value)**
```java
cache.put("u100", user);   // 直接写入（覆盖旧值）
```
- 注意点：手动 put 绕过了加载逻辑，记得自己保证数据来源正确

**④ invalidate(K key) / invalidateAll()**
```java
cache.invalidate("u100");   // 失效单个
cache.invalidateAll();      // 清空全部（等价 cache.asMap().clear()）
```
- 解释：主动移除，触发 removalListener（cause=EXPLICIT）
- 注意点：**只作用于本地这一个 JVM** —— 多实例部署时，其他实例的本地缓存不知道，需要广播或依赖 TTL

**⑤ cleanUp()**
```java
cache.cleanUp();   // 立即清扫过期/待淘汰条目
```
- 解释：Caffeine 的过期清理是**惰性 + 定时**的（维护线程按节奏扫），cleanUp 是手动催促
- 注意点：正常不用调；测试里验证过期行为时有用

**⑥ asMap()**
```java
Map<String, User> map = cache.asMap();   // 以 Map 视角操作
map.computeIfAbsent("u100", k -> ...);   // 支持 ConcurrentMap 语义
```
- 注意点：asMap 返回的是**视图**，不能序列化、不能持有长期引用（避免绕过缓存语义）；`map.put` 等价 `cache.put`

### 2.4 三种加载方式对比

**① 手动加载（Cache）**

```java
Cache<String, User> cache = Caffeine.newBuilder().build();
User u = cache.get("u100", k -> dao.findById(k));   // 每次 get 都传加载函数
```
- 说明：加载逻辑写在使用处，每次 get 都要带函数
- 适用：加载逻辑不固定、不同调用方加载方式不同的场景
- 注意点：加载逻辑散落在各处容易重复，团队协作时容易写出不一致的加载代码

**② 自动加载（LoadingCache）**

```java
// 构建：加载逻辑集中在一个 CacheLoader 里
LoadingCache<String, User> cache = Caffeine.newBuilder()
        .maximumSize(10_000)
        .refreshAfterWrite(Duration.ofMinutes(5))   // 自动加载配刷新最爽
        .build(new CacheLoader<String, User>() {
            @Override
            public User load(String key) {
                return userMapper.findById(key);        // 未命中 → 自动加载
            }
            @Override
            public Map<String, User> loadAll(Iterable<? extends String> keys) {
                return userMapper.findByIds(keys);      // 批量加载（getAll 用）
            }
        });

User u = cache.get("u100");                        // 未命中自动加载
Map<String, User> all = cache.getAll(List.of("u1", "u2"));  // 批量走 loadAll
User u2 = cache.getUnchecked("u100");              // 抛异常包装为 UncheckedExecutionException
cache.refresh("u100");                             // 手动触发异步刷新
```
- 说明：加载逻辑**集中在一处**（CacheLoader），业务侧只调 get 什么都不用管；天然支持批量加载（loadAll）、异步刷新（refreshAfterWrite）
- 适用：大部分业务场景的首选 —— 「查不到就去 DB」是默认套路
- 异常处理：`get` 抛受检的 `ExecutionException`；`getUnchecked` 抛非受检的 `UncheckedExecutionException`；loader 里抛的异常最终都会被包一层
- 注意点：没实现 `loadAll` 时，`getAll` 会退化为逐 key 调 `load`（N 次单查）；`refreshAfterWrite` 只对 Loading/Async 缓存生效

**③ 异步加载（AsyncCache）**

```java
AsyncCache<String, User> cache = Caffeine.newBuilder().buildAsync();

// 异步加载：不阻塞调用线程，返回 CompletableFuture
CompletableFuture<User> f = cache.get("u100", k -> userMapper.findByIdAsync(k));
f.thenAccept(user -> log.info("加载完成: {}", user));

// 批量异步
CompletableFuture<Map<String, User>> all = cache.getAll(
        List.of("u1", "u2"), keys -> userMapper.findByIdsAsync(keys));

// 转回同步视角（拿到内部的 LoadingCache）
LoadingCache<String, User> sync = cache.synchronous();
User u = sync.get("u100");
```
- 说明：`get` 立即返回 `CompletableFuture`，加载在后台线程执行；内部实现是 `AsyncLoadingCache`
- 适用：加载是耗时 IO（远程调用、慢 SQL）、且不想阻塞业务线程的场景
- 注意点：异常**不会直接抛**，而是体现在 Future 里（get 时处理 ExecutionException，或用 exceptionally 接）；`synchronous()` 拿到的视图是同步阻塞的；多一层 Future 心智负担，简单场景未必需要

### 2.5 淘汰与过期策略配置

**四类配置速查**

    配置                  语义              适合场景
    expireAfterWrite     写入后固定过期     有明确 TTL 的数据
    expireAfterAccess    闲置 N 时间过期    热数据常驻
    refreshAfterWrite    到期后异步刷新     高频读+低频变的配置类
    maximumSize          容量上限+淘汰      防内存膨胀

**expireAfterWrite vs refreshAfterWrite 对比**

    维度        expireAfterWrite   refreshAfterWrite
    到期行为    直接删，下次 get 阻塞加载  旧值保留，后台异步刷新
    读延迟      到期瞬间有一次阻塞        无阻塞（旧值先用）
    并发穿透    到期瞬间可能击穿          无击穿
    组合使用    可同时配                + expire 兜底最佳

**注意点**：`expireAfterAccess` 会和 `refreshAfterWrite` 冲突（refresh 会重置 access 时间），一般不同时配。

### 2.6 统计与监控

```java
Caffeine.newBuilder().recordStats().build();
// 之后
CacheStats s = cache.stats();
s.hitRate();        // 命中率
s.missCount();      // 未命中次数
s.evictionCount();  // 淘汰次数
s.loadAverageMillis(); // 平均加载耗时
```

**生产建议**：把 hitRate 打到监控（Micrometer 有 Caffeine 集成：`cache.stats()` 配 `CacheMetricsRegistrar`），命中率低于阈值就是报警信号。

---

## 3. Spring Boot 集成

### 3.1 依赖与配置

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
```

**最简单方式（yaml 一行）**

```yaml
spring:
  cache:
    type: caffeine
    cache-names: user, order          # 预声明缓存区
    caffeine:
      spec: maximumSize=10000,expireAfterWrite=10m
```

**Java Config（更灵活）**

```java
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager cm = new CaffeineCacheManager();
        cm.setCaffeine(Caffeine.newBuilder()
                .maximumSize(50_000)
                .expireAfterWrite(Duration.ofMinutes(10))
                .recordStats());
        return cm;
    }
}
```

### 3.2 核心注解用法

```java
// ① 读缓存：命中直接返回，未命中执行方法并缓存结果
@Cacheable(cacheNames = "user", key = "#id")
public User getUser(Long id) { ... }

// ② 更新缓存：方法执行后把返回值写进缓存
@CachePut(cacheNames = "user", key = "#id")
public User updateUser(Long id) { ... }

// ③ 失效缓存：方法执行后删除缓存
@CacheEvict(cacheNames = "user", key = "#id")
public void deleteUser(Long id) { ... }
```

**注意点**
- `@Cacheable` 默认用方法的返回值和参数做 key，**key 用 SpEL 表达式**（`#id`、`#user.id`）
- `@Cacheable` 有 `sync = true` 选项：单实例内并发相同 key 只执行一次方法（防击穿）
- `@CacheEvict` 的 `allEntries = true` 清空整个缓存区；`beforeInvocation = true` 提前删除（方法抛异常也删）
- 注解**只对 Spring 代理生效**：同类内部调用（this.xxx()）不走代理，缓存不生效 —— 经典坑

### 3.3 多缓存区配置（不同数据不同策略）

**什么时候需要多缓存区**

一个缓存区（cacheNames）只有一套 TTL/容量，但业务里不同数据差异很大：

    数据        容量     过期策略            理由
    user 用户   5 万    10 分钟过期         变化中等，短 TTL 保新鲜
    token 令牌  1 万    30 分钟过期         明确 TTL，过期必须重查
    dict 字典表 5 千    1 小时 + 软刷新      低频变，刷新保新鲜不阻塞
    session 会话 2 千   15 分钟闲置过期     访问后重置，闲置才淘汰

如果全塞一个区，只能迁就最保守的策略 —— 要么用户数据过期太快，要么 token 过期太慢。多缓存区就是**按数据特性分区治理**。

**完整配置案例**

```java
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager cm = new CaffeineCacheManager();
        // 用户缓存：容量大、短 TTL
        cm.registerCustomCache("user", Caffeine.newBuilder()
                .maximumSize(50_000)
                .expireAfterWrite(Duration.ofMinutes(10))
                .recordStats()
                .build());
        // 令牌缓存：明确 TTL
        cm.registerCustomCache("token", Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterWrite(Duration.ofMinutes(30))
                .build());
        // 字典缓存：软刷新，读不阻塞
        cm.registerCustomCache("dict", Caffeine.newBuilder()
                .maximumSize(5_000)
                .expireAfterWrite(Duration.ofHours(1))
                .refreshAfterWrite(Duration.ofMinutes(10))
                .build());
        // 会话缓存：闲置过期
        cm.registerCustomCache("session", Caffeine.newBuilder()
                .maximumSize(2_000)
                .expireAfterAccess(Duration.ofMinutes(15))
                .build());
        return cm;
    }
}
```

**使用**：注解里用 cacheNames 指定区

```java
@Cacheable(cacheNames = "user", key = "#id")
public User getUser(Long id) { ... }

@Cacheable(cacheNames = "dict", key = "#type")
public List<DictItem> getDict(String type) { ... }
```

**注意点**
- `CaffeineCacheManager` 默认：`getCache` 找不到时会**动态新建**一个默认策略的缓存区 —— 小心拼错 cacheNames 悄悄创建一堆"裸缓存"（没有你的自定义策略）。解决：启动时预热（首次访问前调 getCache(name) 触发创建），或重写 getCache 校验
- 每个区独立统计：recordStats 后按区看命中率，热区冷区一目了然
- 缓存区数量别失控：几十个以内没问题，几百个说明分类粒度有问题
- yaml 里 `spring.cache.cache-names: user,token,dict` 预声明 + `caffeine.spec` 设全局默认，适合快速起步；要分区定制就走上面的 Java Config

### 3.4 高级注解用法

```java
// condition：满足条件才走缓存
@Cacheable(cacheNames = "user", key = "#id", condition = "#id > 0")

// unless：满足条件不缓存结果（返回值判断）
@Cacheable(cacheNames = "user", key = "#id", unless = "#result == null")

// 自定义 keyGenerator
@Cacheable(cacheNames = "user", keyGenerator = "userKeyGenerator")
```

### 3.5 一级 + 二级缓存架构（Caffeine + Redis）

**经典分层**

    请求 → Caffeine（本地内存，微秒级）
              ↓ 未命中
          Redis（分布式，毫秒级）
              ↓ 未命中
          DB（最慢，最后兜底）

**为什么这样搭**
- Caffeine：同一实例内的热点数据，零网络开销，读最快
- Redis：多实例共享，实例间数据一致，扛住 Caffeine 未命中的流量
- 双缓存让「单机热点」和「全局热点」都命中内存/高速层，DB 只接真正的漏网之鱼

**代价与注意点**
- 一致性变复杂：两级缓存 + DB 三方，更新时要有策略（见 4.6）
- 本地缓存各自为政：实例 A 更新了，实例 B 的 Caffeine 还是旧值 —— 只能靠短 TTL 或广播失效兜底
- 内存占用翻倍：每实例一份本地拷贝

### 3.6 缓存选型规范（统一 Caffeine，禁用 Guava Cache）

**团队约定**：

- 本地缓存一律用 Caffeine；业务代码**禁止出现 `com.google.common.cache.*`**（Guava Cache 类）
- 理由：Guava 官方不拆 Maven artifact（单 jar，见 [00-Guava概览与模块化辨析](Guava/00-Guava概览与模块化辨析.md)），无法"只引入 Guava 不引入 cache"；两套同构 API 并存会因个人使用习惯分裂，导致排查口径与调参规范混乱；Caffeine 与 Guava Cache API 同构，迁移成本≈改 import
- 校验手段：代码评审检查 `com.google.common.cache` import；或用 ArchUnit 加规则，出现即构建失败

**Spring Boot 最佳实践**：

- 业务代码只依赖 Spring 缓存抽象：`CacheManager` + `@Cacheable` 注解（见 3.1/3.2），**不直接 new Caffeine 实例**——两套 API 的差异进不了业务层，混乱从源头消失
- 需要 LoadingCache 语义（自动加载/刷新）的场景，由基建层统一封装 Caffeine 对外提供，业务侧注入封装类，不散落各处
- 多缓存区按数据特性分区治理（见 3.3）；两级缓存一致性按 4.6 约定执行

**Guava 侧定位**：Guava 仅用于 base / collect / 并发工具（如 ThreadFactoryBuilder，见 [01-Java线程池原理与参数详解](../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)）；其 cache 模块视为"历史实现"，迁移对比见 [03-Guava concurrent与cache详解](Guava/03-Guava concurrent与cache详解.md)。

---

## 4. 使用注意点与坑

### 4.1 null 值问题

Caffeine **不支持缓存 null**：
- `get(key, fn)` 中 fn 返回 null → 不缓存，下次仍穿透
- 想缓存「空结果」（比如查无此人）→ 用 Optional 包装

```java
Cache<String, Optional<User>> cache = ...;
Optional<User> u = cache.get("u100", k -> Optional.ofNullable(dao.findById(k)));
```

### 4.2 key/value 必须不可变

- key 的 hashCode/equals 变了 → 再也查不到（比如 key 是可变的 List/对象，改字段后 hash 变化）
- value 被外部修改 → 缓存数据被污染，且不触发任何淘汰/失效机制
- **规则**：key 用 String/Long 等不可变类型；value 尽量不可变对象或只读使用

### 4.3 maximumSize 是软限制

- 不是精确阈值，是 W-TinyLFU 频率窗口下的近似控制
- 别指望它做严格的内存上限；超大 value 用 `maximumWeight` + `weigher` 更合理
- 极端场景：想精确控制堆内存，配合 `-XX:MaxDirectMemorySize` 思路不适用 —— 用 JVM 堆监控 + 缓存容量调参

### 4.4 缓存穿透 / 击穿 / 雪崩

- **穿透**：查不存在的 key，每次打 DB
  应对：空值也缓存（Optional 包装）+ 布隆过滤器前置
- **击穿**：热点 key 过期瞬间，大量请求同时打 DB
  应对：`@Cacheable(sync = true)` / 加载合并（get 的 fn 本身原子合并）；不设过期只主动失效
- **雪崩**：大量 key 同时过期
  应对：过期时间加随机抖动（`expireAfterWrite(5m + random)`），避免整齐划一

### 4.5 expireAfterWrite vs refreshAfterWrite 怎么选

- 数据变化不频繁、能容忍短暂旧值 → **refreshAfterWrite**（读不阻塞，体验好）
- 数据过期即失效（Token、验证码）→ **expireAfterWrite**（过期必须重查）
- 组合拳：`expireAfterWrite(10m) + refreshAfterWrite(5m)` —— 5 分钟软刷新保新鲜，10 分钟硬过期兜底

### 4.6 两级缓存一致性（重点 ★）

**核心问题**：DB 更新后，Caffeine 和 Redis 里的旧数据怎么办？

**先说结论：不存在「真原子」操作** —— Caffeine 在 JVM 内存、Redis 是独立进程、DB 是另一个系统，单事务管不到三者。追求的是**极小窗口 + 最终一致**。

**① 一条注解同时失效两级（最接近直觉）**

```java
@CacheEvict(cacheNames = {"caffeine", "redis"}, key = "#id")
public void update(Long id) { ... }
```

注意：这只是**顺序执行两次删除**，不是原子 —— 中间一步失败，两级就脏了一个。适合容忍短窗口的场景。

**② 事务提交后再清理（推荐 ★）**

```java
@Transactional
public void updateUser(Long id) {
    userMapper.update(id);
    // 事务提交成功后，才清两级缓存
    TransactionSynchronizationManager.registerSynchronization(
        new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                caffeineCache.invalidate(id);   // ① 清本地
                redisTemplate.delete("user:" + id); // ② 清 Redis
            }
        });
}
```

**为什么必须在 afterCommit 清**：如果先清缓存、事务又回滚，缓存里就没数据了（下次穿透）；事务提交后才清，保证缓存要么是旧值（短暂）、要么是新值，永远对应「已提交」的状态。

**③ 延迟双删（并发写场景）**

```java
// 更新 DB 后：
redisTemplate.delete("user:" + id);        // 第一次删
Thread.sleep(500);                          // 等待可能读到旧值的并发读完成
redisTemplate.delete("user:" + id);        // 第二次删，兜底
```

- 解释：防「读线程在删除前把旧值写回缓存」的竞态窗口
- 本地 Caffeine 也同理：`invalidate` → 短延迟 → 再 `invalidate`
- 延迟时间经验值：几百 ms ~ 1s，按业务读耗时调
- 进阶：延迟删除用消息队列异步执行，避免 sleep 阻塞写线程

**④ 最终一致方案（大规模场景）**

更新 DB → 发 MQ 事件 → 各实例/Redis 监听后失效自己的缓存。适合集群规模大、要求不丢的场景。

**实践建议组合**：afterCommit 双清（主）+ 短 TTL 兜底（防漏）+ 关键数据手动延迟双删（强一致场景）。

---

## 5. 原理（补充知识）

### 5.1 整体架构与并发设计

**数据结构**
- 主体：类似 ConcurrentHashMap 的分段结构，但每个桶上是「访问顺序队列 + 淘汰窗口」
- 三块区域：**Eden（新生窗口）→ Probation（试用区）→ Protected（保护区）**，数据按访问频率晋级/降级

**并发设计**
- **读**：无锁（volatile + CAS），读路径几乎没有同步开销 → 读性能接近 ConcurrentHashMap
- **写**：Striped 细粒度锁（按 key 散列到不同锁），写之间互不阻塞
- **淘汰/过期**：后台维护线程定期清扫 + 读写时顺带惰性清理

### 5.2 W-TinyLFU 淘汰算法

**为什么不是 LRU / LFU**
- LRU：一次偶发访问就能把热点挤出（「缓存污染」）
- LFU：老数据计数只增不减，新热点永远进不来（「历史包袱」）

**W-TinyLFU 的三个组件**
① **Count-Min Sketch 频率估计**：布隆过滤器的变种，多个 hash 函数映射到计数数组，取最小值作为频率估计 —— 用极小内存近似统计访问频率（省空间、可调精度）
② **TinyLFU 准入策略**：新元素想进缓存，和「将被淘汰的候选」比频率，**频率高者留下**（不是无脑踢最旧的）
③ **窗口（Window）**：一个小的 LRU 窗口专门收留新元素，给它们积累频率的机会 —— 解决 LFU 的「新热点进不来」

**一句话总结**：用近似频率 + 小窗口 + 频率准入，兼顾「高频保留」和「新热点及时上位」。

### 5.3 过期机制

- 不是每个元素一个 Timer（那会爆炸），而是**时间桶/时钟分片**：按过期时间归类，维护线程批量扫描过期桶
- 读取时顺带检查（惰性过期），过期元素读到才清理
- 这就是为什么 `expireAfterAccess` 和 `refreshAfterWrite` 不能简单共存 —— 刷新会改写访问时间，干扰闲置判定

### 5.4 与 Guava Cache 对比

    维度          Caffeine            Guava Cache
    淘汰算法      W-TinyLFU           LRU
    读性能        接近 ConcurrentHashMap 慢 2~3 倍级别
    写性能        更优（Striped 锁）   全局锁，并发写差
    异步加载      AsyncCache 一等公民   支持但弱
    统计          recordStats 完整    基本统计
    维护          活跃               半维护状态
    迁移成本      API 几乎兼容        —

### 5.5 性能基准（官方 benchmark 量级）

- 读：Caffeine 数百万 OPS 级别，接近 ConcurrentHashMap
- 写：比 Guava 快一个量级（Guava 写路径全局锁）
- 官方建议：追求吞吐选 Caffeine，与 Guava 迁移只需改依赖 + 少量 API 微调

---

## 6. 面试追问清单（带答案）

### 6.1 Caffeine 为什么快？

A：读路径无锁（volatile + CAS 接近 ConcurrentHashMap），写用 Striped 细粒度锁；淘汰用概率型 Count-Min Sketch 省内存；过期是时间桶批量清理而非每元素定时器。

### 6.2 W-TinyLFU 怎么解决 LRU/LFU 的缺点？

A：LRU 会被一次性访问污染、LFU 老数据霸位。W-TinyLFU = 小 LRU 窗口给新元素机会 + Count-Min Sketch 近似频率 + 准入比较（新元素与候选淘汰者比频率，高者留下），既保高频又迎新热点。

### 6.3 maximumSize 为什么是近似值？

A：基于频率窗口和概率统计做淘汰决策，不是精确计数；目的是省内存和算力。精确容量控制用 maximumWeight + weigher。

### 6.4 expireAfterWrite 和 refreshAfterWrite 区别？

A：前者到期直接删、下次读阻塞加载；后者到期旧值先用、后台异步刷新，读不阻塞。refresh 只对 Loading/AsyncCache 生效，通常两者组合：refresh 保新鲜 + expire 兜底。

### 6.5 本地缓存和 Redis 怎么配合？一致性怎么保证？

A：Caffeine 做一级（实例内）、Redis 做二级（跨实例共享）、DB 兜底。一致性没有真原子方案，用「事务提交后 afterCommit 双清」+「延迟双删」+「短 TTL 兜底」把不一致窗口压到最小，达到最终一致。

### 6.6 缓存击穿怎么防？

A：热点 key 过期瞬间并发打 DB。方案：① @Cacheable(sync=true) 或 get(key, fn) 的原子合并加载；② 热点数据不设过期、靠主动失效；③ 布隆过滤器挡穿透，随机过期防雪崩。

### 6.7 Caffeine 能缓存 null 吗？怎么缓存空结果？

A：不能，null 视为未命中不缓存。想缓存空结果用 Optional 包装 value，get 时 `Optional.ofNullable(dao.findById(k))`。

### 6.8 多实例部署时 invalidate 有什么坑？

A：invalidate 只作用于当前 JVM 的本地缓存，其他实例不知道。要么广播失效（MQ 事件）、要么接受短 TTL 兜底、要么热点数据用 Redis 二级兜底。