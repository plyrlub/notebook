---
tags: [Java, Guava, 三方库, net, graph, reflection, eventbus, hash, BloomFilter]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava net / graph / reflection / eventbus / hash详解

> 系列导航：[00-Guava概览与模块化辨析](00-Guava概览与模块化辨析.md)
> 低频域合篇：五个包域单独成篇内容不足，合篇精讲；标注 @Beta 的 API 注意稳定性

## 📋 总纲

1. net：域名、媒体类型、主机端口
2. graph：图数据结构（长期 @Beta）
3. reflection：TypeToken 与 ClassPath
4. eventbus：发布订阅（@Beta）
5. hash：Hashing 与 BloomFilter
6. 选型与易错点汇总

## 一、net：域名、媒体类型、主机端口

### InternetDomainName

域名解析与校验（基于公共后缀列表）：

| 方法 | 说明 |
| --- | --- |
| `from(String)` | 解析，非法抛 IllegalArgumentException |
| `isValid(String)` | 校验（不抛异常） |
| `topPrivateDomain()` | 取注册域（如 www.example.com → example.com） |
| `parent()` / `child(name)` | 父域/子域 |
| `hasPublicSuffix()` / `publicSuffix()` | 公共后缀判断 |

```java
InternetDomainName.from("www.example.co.uk").topPrivateDomain();  // "example.co.uk"
```

典型场景：Cookie 域校验、跨域安全判断、URL 规范化。

### MediaType

媒体类型解析与常量（APPLICATION_JSON、TEXT_HTML 等）：

```java
MediaType.parse("application/json; charset=utf-8").withoutParameters();  // application/json
```

典型场景：HTTP Content-Type 解析、文件类型判断。

### HostAndPort

```java
HostAndPort.fromString("192.168.1.1:8080").getHost();  // "192.168.1.1"
HostAndPort.fromString("[::1]:8080").getPort();        // 8080（IPv6 支持）
HostAndPort.fromHost("example.com").withDefaultPort(80);
```

典型场景：配置解析、连接地址拆分。

### HttpHeaders / HttpMethods

HTTP 头/方法名的常量类（`HttpHeaders.CONTENT_TYPE`、`HttpMethods.POST`），避免魔法字符串。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| HttpHeaders / HttpMethods | `java.net.http.HttpHeaders`（JDK 11 HTTP Client）；常量类可自建 |
| HostAndPort | `java.net.URI.getHost()` / `getPort()`（部分场景，IPv6 解析弱） |
| InternetDomainName | 无；公共后缀判断需自实现或引 publicsuffix 库 |
| MediaType | 无；`jakarta.ws.rs.core.MediaType`（有 JAX-RS 时）或自解析 |

结论：HTTP 头用 JDK 11；域名 / 媒体类型 Guava 仍最方便。

## 二、graph：图数据结构

**长期 @Beta**（自 20.0 引入至今未转正），生产用需评估稳定性。

| 接口 | 语义 |
| --- | --- |
| Graph<N> | 无向图（节点 + 边） |
| ValueGraph<N, V> | 带权图（边带值） |
| Network<N, E> | 网络（边是独立对象，可平行边） |

```java
MutableValueGraph<String, Integer> g = ValueGraphBuilder.directed().build();
g.addNode("A");
g.putEdgeValue("A", "B", 5);          // 带权边
g.successors("A");                    // [B]
g.edgeValueOrDefault("A", "B", 0);    // 5
```

| 能力 | 说明 |
| --- | --- |
| 构建 | GraphBuilder / ValueGraphBuilder（directed/undirected、允许自环/平行边） |
| 查询 | successors / predecessors / adjacentNodes / inDegree / outDegree |
| 遍历 | 无内置算法（BFS/DFS/最短路径需自写或换库） |
| 对比 | 需要算法（最短路径/拓扑）时用 JGraphT，Guava graph 只提供结构 |


**JDK 替代**：无。需要图算法（最短路径 / 拓扑排序 / 连通分量）用 **JGraphT**；Guava graph 只提供结构不提供算法，且长期 @Beta，生产场景慎重。

## 三、reflection：TypeToken 与 ClassPath

### TypeToken（核心价值：泛型类型字面量）

解决**运行时泛型擦除**问题，捕获"泛型类型"本身：

```java
TypeToken<List<String>> token = new TypeToken<List<String>>() {};
token.getRawType();                    // java.util.List
token.getType();                       // java.util.List<java.lang.String>（含泛型参数！）
token.resolveType(List.class.getMethod("get", int.class).getGenericReturnType());
```

| 方法 | 说明 |
| --- | --- |
| `getRawType()` | 原始类型 |
| `getType()` | 完整泛型类型 |
| `getSupertype(cls)` / `getSubtype(cls)` | 泛型继承链解析 |
| `resolveType(Type)` | 把方法泛型返回类型代入具体参数 |
| `isArray()` / `getComponentType()` | 数组判断 |

典型场景：泛型 DAO/反序列化（Jackson 的 TypeReference 就是同类思路）、泛型工具库。

### ClassPath

```java
ClassPath.from(ClassLoader.getSystemClassLoader())
         .getTopLevelClasses("com.example.biz");   // 扫描包下所有类
```

典型场景：包扫描（注解处理器、SPI 发现）。注意扫描全 classpath 成本高，慎用于启动路径。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| TypeToken | 第三方同思路：Jackson `TypeReference`、Spring `ParameterizedTypeReference`；或匿名类捕获 `(Type) new ArrayList<String>() {}.getClass().getGenericSuperclass()` |
| ClassPath 包扫描 | Spring `ClassPathScanningCandidateComponentProvider`；或手写文件遍历 |

结论：泛型类型解析优先用项目已有框架（Jackson / Spring）的工具；Guava 仅在无框架环境使用。

## 四、eventbus：发布订阅

**@Beta**。进程内发布订阅总线，注解驱动：

```java
// 订阅端：@Subscribe 标注处理方法
public class OrderListener {
    @Subscribe
    public void onOrder(OrderCreatedEvent event) { ... }
}

// 总线
EventBus bus = new EventBus("order");
bus.register(new OrderListener());
bus.post(new OrderCreatedEvent(123L));     // 同步派发给所有匹配订阅者
```

| 类型 | 说明 |
| --- | --- |
| EventBus | 同步派发（在 post 线程执行） |
| AsyncEventBus | 异步派发（构造传 Executor） |

关键规则：

- 订阅方法必须**只有一个参数**（事件类型），按参数类型路由。
- 事件无父类时只匹配精确类型；有继承时匹配父类订阅者。
- post 是"即发即忘"：订阅者异常被吞（DeadEvent 兜底），无返回值。

与 Spring 对比：Spring ApplicationEvent 功能类似且与容器深度集成（事务事件、异步 @Async 监听）；**Spring 项目直接用 Spring 事件**，Guava EventBus 仅在无 Spring 或轻量场景。


**JDK 替代**：Spring `ApplicationEvent` + `@EventListener`（与容器集成、支持事务与异步监听）——Spring 项目直接用 Spring 事件机制；无 Spring 的轻量进程内总线才考虑 Guava EventBus。

## 五、hash：Hashing 与 BloomFilter

### Hashing

统一的哈希函数门面：

```java
HashFunction hf = Hashing.murmur3_128();                 // 非加密哈希，性能好
HashCode hc = hf.newHasher()
        .putString("key", StandardCharsets.UTF_8)
        .putLong(42L)
        .hash();
long bits = hc.asLong();
```

| 函数 | 用途 |
| --- | --- |
| `murmur3_32()` / `murmur3_128()` | 非加密（布隆过滤器、分片键） |
| `sha256()` / `sha512()` | 加密哈希 |
| `consistentHash(hash, buckets)` | 一致性哈希（节点增减影响最小） |
| `crc32()` | 校验 |

典型场景：分片路由、负载均衡一致性哈希、去重指纹。

### BloomFilter（布隆过滤器）

概率性集合：**判断"一定不存在"或"可能存在"**，空间极小，有误判率（FPP）。

```java
BloomFilter<String> bf = BloomFilter.create(
        Funnels.stringFunnel(StandardCharsets.UTF_8),  // 对象→字节
        10_000_000,        // 预期元素数
        0.01);             // 期望误判率 1%
bf.put("order-123");
bf.mightContain("order-123");   // true（一定存在或误判）
bf.mightContain("order-999");   // false（一定不存在）
```

| 要点 | 说明 |
| --- | --- |
| 不可删除 | put 后无法 remove（计数布隆除外） |
| 误判率 | 创建时指定，越小越占内存 |
| 典型场景 | 缓存穿透防护（不存在则直接拦截）、爬虫去重、黑名单 |

实现：Guava BloomFilter 是教科书级实现，面试常考原理（k 个哈希函数 + m 位位图）。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| Hashing.sha256 | `MessageDigest.getInstance("SHA-256")`（JDK 标准，注意需自行处理流式 update） |
| murmur3（非加密哈希） | 无；需自行实现或引其他库 |
| consistentHash | 无；手写一致性哈希环 |
| BloomFilter | 无；JDK 无布隆过滤器，自实现（k 个哈希 + 位图）或引库（Redisson 等） |

```java
// JDK 等价写法：等价 Hashing.sha256().hashString(s, UTF_8)
MessageDigest md = MessageDigest.getInstance("SHA-256");
byte[] digest = md.digest(s.getBytes(StandardCharsets.UTF_8));
```

结论：加密哈希用 JDK MessageDigest；布隆过滤器 / 一致性哈希 Guava 仍是轻量首选。

## 六、选型与易错点汇总

- graph / eventbus 长期 @Beta，生产谨慎；图算法用 JGraphT，事件用 Spring。
- TypeToken 用匿名子类捕获泛型（`new TypeToken<...>() {}`），忘记 `{}` 则拿不到类型信息。
- BloomFilter 无法删除元素；误判率与内存是权衡。
- EventBus 订阅方法只允许单参数。
- 一致性哈希用 Hashing.consistentHash，别手写。

## 参考资料

- [Guava net javadoc（com.google.common.net）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/net/package-summary.html)，查询日期：2026-08-08
- [Guava graph javadoc（com.google.common.graph）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/graph/package-summary.html)，查询日期：2026-08-08
- [Guava eventbus javadoc（com.google.common.eventbus）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/eventbus/package-summary.html)，查询日期：2026-08-08
- [Guava hash javadoc（com.google.common.hash）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/hash/package-summary.html)，查询日期：2026-08-08
