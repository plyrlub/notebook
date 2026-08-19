---
tags: [Java, 微服务, Spring Cloud Gateway, GlobalFilter, 过滤器, 学习笔记]
创建日期: 2026-08-20
状态: ✅ 已归档（01-学习/Java/微服务/网关）
归属: 01-学习/Java/微服务/网关
上一篇: 04-内置过滤器详解
下一篇: 06-Actuator运维实操
---

# 内置全局过滤器 GlobalFilter 深度

> 承接 [01-Spring Cloud Gateway详解](01-Spring Cloud Gateway详解.md)。本文把「内置 GlobalFilter」从详解总篇拆出独立成章，深度覆盖：内置 GlobalFilter 清单与默认 order、关键过滤器逐个详解、过滤器链执行时序、合并与 pre/post 模型、自定义 GlobalFilter。
> 关联：内置断言与过滤器工厂见 [04-内置过滤器详解](04-内置过滤器详解.md)；三种过滤器对比见 [04-内置过滤器详解](04-内置过滤器详解.md) §3；Actuator 运行时观察见 [06-Actuator运维实操](06-Actuator运维实操.md)。

---
## 1. 内置全局过滤器 GlobalFilter 逐个详解

![](Pasted image 20260820003044.png)

> 上方截图即 `org.springframework.cloud.gateway.filter` 包下**内置 GlobalFilter 实现类一览**。生产可用 `GET /actuator/gateway/globalfilters` 查看当前运行时注册的全部全局过滤器及各自 order（会得到一个「类签名 → order」的 JSON）。

### 1.1 定位与前提

- **GlobalFilter 作用于所有路由**（区别于只绑单条路由的 GatewayFilter），实现跨切面、与应用无关的通用逻辑（鉴权、日志、转发、负载均衡、指标等）。
- 实现接口 `GlobalFilter`（与 `GatewayFilter` **同签名** `Mono<Void> filter(exchange, chain)`）+ 通过 `Ordered` 或 `@Order` 声明顺序。
- **前提：路由必须匹配成功**。`FilteringWebHandler` 只在断言命中后，才把全部 GlobalFilter Bean 与该路由的 GatewayFilters 合并成链。断言不匹配 → 直接 404 → GlobalFilter 不执行。

### 1.2 内置 GlobalFilter 清单（默认 order）

内置过滤器按默认 order 从高优先到低优先排列（order 越小越先进入 pre、越后进入 post）：

| 阶段 | GlobalFilter | 默认 order | 触发条件 | 作用 |
|---|---|---|---|---|
| 前置 | `RemoveCachedBodyFilter` | `Integer.MIN_VALUE` | 请求路由转发后 | 清理缓存请求体，防内存占用 |
| 前置 | `AdaptCachedBodyGlobalFilter` | `Integer.MIN_VALUE + 1000` | — | 装饰请求并**缓存请求体**（`GATEWAY_REQUEST_BODY_ATTR`），供后续需要读 body 的过滤器使用 |
| 后置写响应 | `NettyWriteResponseFilter` | `-1` | 存在下游响应属性 | 在其它过滤器全部完成后，把下游 Netty 响应写回客户端 |
| 前后 | `GatewayMetricsFilter` | `0` | 开启 metrics | 采集网关指标（`spring.cloud.gateway.requests` 等，见 Actuator/Prometheus） |
| 前置 | `ForwardPathFilter` | `0` | forward 协议路径 | forward 请求路径处理 |
| 前置 | `RouteToRequestUrlFilter` | `10000` | 存在 Route | 把 Route 的 uri 相对请求 URI 构造出新的目标 URI，写入 `GATEWAY_REQUEST_URL_ATTR` |
| 前置 | `ReactiveLoadBalancerClientFilter`（旧名 `LoadBalancerClientFilter`） | `10100` | uri 为 `lb://` | 用 `ReactorLoadBalancer` 把服务名解析为实际实例 host:port |
| 前置 | `WebsocketRoutingFilter` | `Integer.MAX_VALUE - 1` | uri 为 `ws://`/`wss://` | 用 WebSocket 基础设施转发 WebSocket 请求 |
| 中置 | `NettyRoutingFilter` | `Integer.MAX_VALUE` | uri 为 `http(s)://` | 用 Netty `HttpClient` 转发代理请求 |
| 前置 | `ForwardRoutingFilter` | `Integer.MAX_VALUE` | uri 为 `forward://` | 用 `DispatcherHandler` 在网关本地转发 |
| 实验 | `WebClientHttpRoutingFilter` / `WebClientWriteResponseFilter` | 同 Netty 类 | （可选） | 基于 WebClient 的转发/写回，不依赖 Netty，属实验特性 |

> **顺序要点**：主转发链路为 `AdaptCachedBodyGlobalFilter → RouteToRequestUrlFilter(10000) → ReactiveLoadBalancerClientFilter(10100) → NettyRoutingFilter / ForwardRoutingFilter / WebsocketRoutingFilter(≈MAX) → NettyWriteResponseFilter(-1 后置写回)`。自定义过滤器常用负数 order（如鉴权 `-100`）抢在转发过滤器前执行。

### 1.3 关键内置过滤器逐个详解

#### 1.3.1 AdaptCachedBodyGlobalFilter（缓存请求体）

给请求体缓存，使后续过滤器能多次读取 body（否则 body 只能读一次）。

```java
// 自定义过滤器可从 exchange 读到已被缓存的请求体
Mono<byte[]> body = exchange.getAttribute(ServerWebExchange.CACHED_REQUEST_BODY_ATTR);
```

#### 1.3.2 RouteToRequestUrlFilter（路由 → 目标 URL）

```java
// 核心逻辑（示意）：把 Route.uri 相对请求构造出转发目标 URI
public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
    Route route = exchange.getRequiredAttribute(GATEWAY_ROUTE_ATTR);
    URI uri = ...;                       // 由 request uri + route uri 组合
    exchange.getAttributes().put(GATEWAY_REQUEST_URL_ATTR, uri);   // 交给下游转发过滤器
    return chain.filter(exchange);
}
```
- 若 uri 带 scheme 前缀（如 `lb:ws://serviceid`），会把 `lb` 剥离存入 `GATEWAY_SCHEME_PREFIX_ATTR`，供后续使用。

#### 1.3.3 ReactiveLoadBalancerClientFilter（lb:// 负载均衡）

Spring Cloud Gateway 有两套 `lb://` 负载均衡过滤器，**一旧（Ribbon）、一新（Spring Cloud LoadBalancer）**，对应不同实现类：

| 过滤器 | 底层负载均衡实现 | 阻塞模型 | 状态 |
|---|---|---|---|
| `LoadBalancerClientFilter`（旧） | Ribbon `LoadBalancerClient` | 阻塞式 | 已废弃（Spring Cloud 2020.0 起移除） |
| `ReactiveLoadBalancerClientFilter`（新） | Spring Cloud LoadBalancer `ReactorLoadBalancer` | 响应式 | 当前默认/推荐 |

> 两者是**两个不同的类并存/交替**，并非「改名」关系——旧覆盖 Ribbon 路由、新覆盖 Spring Cloud LoadBalancer 路由。Spring Cloud 2020.0 之后 Ribbon 被废弃，只剩 `ReactiveLoadBalancerClientFilter`。

**配置（`lb://` 声明）：**

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order
          uri: lb://order-service      # lb:// + 服务名
          predicates: [ Path=/api/order/** ]
```
- 服务名经 `ReactorLoadBalancer` 解析为实例地址，替换 `GATEWAY_REQUEST_URL_ATTR` 中的 uri；找不到实例默认返回 **503**，设 `spring.cloud.gateway.loadbalancer.use404=true` 可改返回 404。
- 从 Spring Cloud Gateway 4.x 起，`spring-cloud-starter-loadbalancer` 被标为**可选依赖**——不显式引入会导致 `lb://` 无法解析、返回 503。

##### 场景一：老工程从 Ribbon 切到 Spring Cloud LoadBalancer（显式引入新依赖 + 排除旧依赖）

适用 Spring Cloud ≤ Hoxton（Boot 2.x）环境，默认负载均衡器仍是 Ribbon。切换三步：

```xml
<!-- 1. 显式引入新负载均衡器 -->
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>

<!-- 2. 排除 Ribbon（从其它 starter 传递引入时）-->
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-netflix-ribbon</artifactId>
  <exclusions>
    <exclusion>
      <groupId>org.springframework.cloud</groupId>
      <artifactId>spring-cloud-starter-netflix-ribbon</artifactId>
    </exclusion>
  </exclusions>
</dependency>

<!-- 3. Nacos Discovery 若自带 Ribbon，同样排除（spring-cloud-starter-alibaba-nacos-discovery 2.2.x 时）-->
```

```yaml
# 4. 关闭 Ribbon，启用 Spring Cloud LoadBalancer（关键开关）
spring:
  cloud:
    loadbalancer:
      ribbon:
        enabled: false
```

> 要点：若 Ribbon 与 LoadBalancer 同时存在，**为向后兼容默认仍用 Ribbon**；只有设 `spring.cloud.loadbalancer.ribbon.enabled=false` 才切到 Spring Cloud LoadBalancer。这步不配，光加依赖不会生效。

##### 场景二：新版工程（Spring Cloud 2020.0+ / 2023.0）——默认已无 Ribbon，只需显式引入 loadbalancer

Spring Cloud 2020.0 起 Ribbon 被废弃、从 `spring-cloud-starter-netflix-*` 移除；`spring-cloud-starter-loadbalancer` 成为唯一选项，但**在 Gateway 4.x 中不再默认包含**。以本库 `02-Spring Cloud Gateway实践.md` 的版本基线（Spring Cloud 2023.0.3 / Spring Boot 3.3 / Nacos 2023.0.1.0）为例：

```xml
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<!-- 必选：显式引入负载均衡，否则 lb:// 无法解析返回 503 -->
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
<dependency>
  <groupId>com.alibaba.cloud</groupId>
  <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
```

```yaml
spring:
  application:
    name: gateway
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
    gateway:
      discovery:
        locator:
          enabled: false   # 用显式路由而非自动发现路由，避免前缀冲突（见 [[07-动态路由与高可用]]）
      routes:
        - id: order-service
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
```

##### 对比：Ribbon（LoadBalancerClientFilter）vs Spring Cloud LoadBalancer（ReactiveLoadBalancerClientFilter）

| 维度 | Ribbon（旧，已废弃） | Spring Cloud LoadBalancer（新，推荐） |
|---|---|---|
| 过滤器类 | `LoadBalancerClientFilter` | `ReactiveLoadBalancerClientFilter` |
| 底层 | Netflix Ribbon `LoadBalancerClient` | Spring Cloud `ReactorLoadBalancer` |
| 阻塞模型 | 阻塞式 | 响应式（Reactor/Netty 契合） |
| 依赖 | `spring-cloud-starter-netflix-ribbon` | `spring-cloud-starter-loadbalancer` |
| 默认算法 | 轮询（可自定 IClientConfig） | 轮询（可自定 `ServiceInstanceListSupplier`） |
| 维护 | 早已停更 | 活跃维护，官方主流 |
| Spring Cloud 兼容 | ≤ Hoxton | 2020.0+ 唯一、Hoxton 可切换启用 |
| 排除/开关 | — | 需 `spring.cloud.loadbalancer.ribbon.enabled=false` 切换（旧环境）；新版本已无 Ribbon 无需此步 |
| Nacos 集成 | nacos-discovery 2.2.x 自带 ribbon，需排除 | nacos-discovery 与 loadbalancer 兼容良好 |

> **实践结论**：旧工程（Boot 2 / Hoxton）迁移 = 引入 `spring-cloud-starter-loadbalancer` + 排除 ribbon 依赖 + 设 `spring.cloud.loadbalancer.ribbon.enabled=false`。新工程（Boot 3 / 2023.x）Ribbon 已消失，只需显式加 `spring-cloud-starter-loadbalancer`（Gateway 4.x 不默认带）。

#### 1.3.4 NettyRoutingFilter / ForwardRoutingFilter / WebsocketRoutingFilter（转发）

按 `GATEWAY_REQUEST_URL_ATTR` 的 scheme 决定走哪个转发过滤器：

| scheme | 过滤器 | 转发方式 |
|---|---|---|
| `http` / `https` | `NettyRoutingFilter` | Netty `HttpClient` |
| `forward://` | `ForwardRoutingFilter` | 本地 `DispatcherHandler` 宏转发 |
| `ws` / `wss` | `WebsocketRoutingFilter` | Spring WebSocket + 负载均衡 `lb:ws://` |

#### 1.3.5 NettyWriteResponseFilter（响应写回）

在所有过滤器 post 阶段完成后，把下游响应（Netty `HttpClientResponse`）写回网关客户端。它 order 为 `-1`，保证在转发/写回链末段统一输出。

#### 1.3.6 GatewayMetricsFilter（指标）

依赖 `spring-boot-starter-actuator`；默认开启（`spring.cloud.gateway.metrics.enabled` 未显式 false）。产出定时指标 `spring.cloud.gateway.requests`，标签含 `routeId`/`routeUri`/`status`/`outcome`/`httpMethod` 等，可被 `/actuator/metrics/spring.cloud.gateway.requests` 抓取并对接 Prometheus/Grafana。

#### 1.3.7 案例透视：forward 路由的 URL 演化与「两次路径解析」

以下面这条路由为例，跟踪一次 `GET /fallback/abc` 请求的完整 URL 演化：

```yaml
routes:
  - id: fallback_route
    uri: forward:/local/fallback    # 配置的是目标 URI，不是 ForwardRoutingFilter 本身
    predicates:
      - Path=/fallback/**
```

> ForwardRoutingFilter 是内置 GlobalFilter，**从不配置在 route 下**。route 里配置的是 `uri` 的 **scheme**，转发行为由 scheme 自动派生（见 [04-内置过滤器详解](04-内置过滤器详解.md) §3.5（设计案例））。

![](gateway-forward-url-evolution.svg|697)

**URL 属性演化与两次"路径变化"**：

| 阶段 | 组件 | URL / 路径状态 | 性质 |
|---|---|---|---|
| ① 断言匹配 | `PathRoutePredicateFactory` | 只判定 `/fallback/abc` 是否匹配 `/fallback/**`，返回 boolean | 纯匹配，不看 URI、不转发；该路由所有断言**一起判定**，全通过才选中路由 |
| ② URL 改写 | `RouteToRequestUrlFilter`（order 10000） | `http://gateway/fallback/abc` → `forward:///local/fallback/abc`，写入 `GATEWAY_REQUEST_URL_ATTR` | **第 1 次变化**：纯内存改写，请求原地未动 |
| ③ 本地转发 | `ForwardRoutingFilter`（链尾） | 交给 `DispatcherHandler`，按 path=`/local/fallback/abc` 查找 Handler | **唯一一次真正移动请求**；`DispatcherHandler` 的 HandlerMapping 构成**第 2 次路径解析** |

**关键结论**：

- **真正"移动请求"的行为只有一次**——由按 scheme 自选择的终端过滤器完成；forward 场景连网络跳都没有，只是进程内移交控制权。
- 第 2 次路径解析是 **Spring WebFlux 内部的 HandlerMapping**（找网关本地 Controller/Handler），**不是 Gateway 路由匹配再来一遍**——不会再走断言、不会再进过滤器链。"感觉转发了两次"的本质是 **Gateway 选路一次 + WebFlux 找 Handler 一次**，两套路由机制接力。
- **配置外部 URI 时**（`uri: https://api.example.com`）：改写后 scheme 为 http/https，链尾由 `NettyRoutingFilter` 接管，真正建立 HTTP 连接发出请求；**没有第 2 次路径解析**。发出的路径是**改写后的请求路径**，可被 `StripPrefix` / `SetPath` / `RewritePath` 等路由过滤器继续修改——`lb://` 路由几乎总要配 StripPrefix 的原因即在于此：URL 合并时原始请求路径会被原样带上。
- **`isAlreadyRouted` 防双重转发**：终端过滤器接管时打上"已路由"标记，排在后面的其它终端过滤器看到标记直接跳过，保证最终发出请求的终端过滤器**有且只有一个**。

### 1.4 过滤器链的执行时序

一次请求的完整处理分为三个阶段，**严格串行**：

1. **Predicate 匹配路由**（`RoutePredicateHandlerMapping`）——遍历所有路由断言，找到第一个全部通过的路由。断言是 `Predicate<ServerWebExchange>`，返回 boolean。
2. **组装合并过滤器链**（`FilteringWebHandler`）——路由匹配成功后，把该路由的 GatewayFilters + 全部 GlobalFilters 合并成一个 List，按 order 排序。
3. **执行过滤器链**（`GatewayFilterChain`）——排好序后依次执行，pre 正序、post 逆序（洋葱模型）。

> **关键：断言不通过 → 直接 404，不进入过滤器链。** GlobalFilter 虽对"所有路由"生效，但前提是路由匹配成功——没有 Route 就没有 chain，GlobalFilter 也不执行。

![](gateway-request-flow.svg|692)

```java
// 简化版核心逻辑
public Mono<Void> handle(ServerWebExchange exchange) {
    // ① 断言匹配：遍历所有 route，找到第一个 predicate 全通过的
    Route route = routeLocator.getRoutes()
        .filter(r -> r.getPredicate().test(exchange))
        .next().block();
    if (route == null) return notFound(exchange);  // 没匹配上，直接 404

    // ② 组装：路由过滤器 + 全局过滤器，合并排序
    List<GatewayFilter> merged = new ArrayList<>();
    merged.addAll(route.getFilters());           // 路由级
    merged.addAll(globalFilters);                // 全局级
    merged.sort(Comparator.comparingInt(Ordered::getOrder));

    // ③ 执行：依次调用
    return new DefaultGatewayFilterChain(merged).filter(exchange);
}
```

### 1.5 过滤器链合并与 pre/post 执行模型

**核心：GatewayFilter 与 GlobalFilter 最终合并进同一条有序链**，不是各跑各的。请求匹配到路由后，`FilteringWebHandler` 把两者合并成一个 List，统一按 order 排序后依次执行。一个 `@Order(0)` 的 GlobalFilter 会跑在大部分路由过滤器之前。

![](gateway-filter-merge-chain.svg|696)

**pre / post 执行模型（洋葱 / 俄罗斯套娃）**：每个过滤器以 `chain.filter(exchange)` 为界：

- **pre 逻辑**（`chain.filter()` 之前）：按 order **正序**执行。
- **post 逻辑**（`chain.filter()` 之后 / `.then()` / `.doOnSuccess`）：按 order **逆序**执行。
- order 最小的过滤器在最外层：最先 pre，最后 post。

```java
@Component
@Order(-100)                        // 数值越小越先执行
public class AuthFilter implements GlobalFilter, Ordered {
    public Mono<Void> filter(ServerWebExchange ex, GatewayFilterChain chain) {
        // ① pre 逻辑：去程执行（鉴权、加头、限流判断）
        if (!checkToken(ex)) return unauthorized(ex);
        return chain.filter(ex)
            // ② post 逻辑：返程逆序执行（改响应、记耗时）
            .doOnSuccess(v -> logLatency(ex));
    }
    public int getOrder() { return -100; }
}
```

### 1.6 自定义 GlobalFilter

**GlobalFilter 最小实现**：

```java
@Component
public class AuthGlobalFilter implements GlobalFilter, Ordered {
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        // 前置逻辑：解析/校验 token、写审计日志、修改请求头
        ServerHttpRequest mutated = request.mutate()
            .header("X-User-Id", "123")   // 注入透传信息
            .build();
        return chain.filter(exchange.mutate().request(mutated).build());
        // 响应侧可在 .then(Mono.fromRunnable(() -> {...})) 后处理
    }

    @Override
    public int getOrder() { return -100; }   // order 越小越先执行
}
```

#### 1.6.1 过滤器链顺序规则

- 请求到达后，`FilteringWebHandler` 将 **GlobalFilter 列表**与路由 **GatewayFilter 列表**合并成一个链表，统一排序执行。
- **排序依据 `order`**：
  - **内置 GlobalFilter** 自带固定 order（见 §1.2）。
  - 自定义 GlobalFilter：实现 `Ordered` 或 `@Order` 则用其值；否则默认 `0`。
  - 路由 GatewayFilter：实现顺序接口则用其值；**否则从 1 开始按在路由中定义的先后顺序**递增。
- **同级 order 的执行次序**：`DefaultFilter`（内置默认）→ `GatewayFilter`（路由级）→ `GlobalFilter`（全局）。
- **执行约定**：order 越小越先执行；`getOrder()` 返回负数可置于默认过滤器之前（如鉴权过滤器用 `-100`，比转发的 `0` 级更早运行）。

```java
// 基于 GateFilterChain 的递归：filter() 前置 → chain.filter() 转发 → 返程后置
public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
    // PRE：转发前（修改请求、鉴权、判断是否放行）
    return chain.filter(exchange).then(
        Mono.fromRunnable(() -> { /* POST：响应返程后处理 */ }));
}
```

#### 1.6.2 短路（放行 / 拦截）

- 过滤器可在 PRE 阶段**中断链路**：调用 `chain.filter` 以外返回，或直接返回 `Mono.empty()` 即不再向下游转发；配合 `exchange.getResponse().setStatusCode(...)` 返回如 `401`/`429`。
- 认证失败典型写法：

```java
if (!valid(token)) {
    exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
    return exchange.getResponse().setComplete();   // 终止链路, 不再转发
}
return chain.filter(exchange);                     // 校验通过, 继续链
```

---

### 1.7 源码透视：FilteringWebHandler 与 GlobalFilter→GatewayFilter 适配

过滤器链真正执行器是 `org.springframework.cloud.gateway.handler.FilteringWebHandler`。其核心：**GlobalFilter 最终被包装成 GatewayFilter，再与路由过滤器合并成一条有序链**。

#### 1.7.1 构造 / 适配：GlobalFilter → GatewayFilter

`FilteringWebHandler` 构造时接收 `List<GlobalFilter>`，在 `loadFilters()` 里逐一把每个 GlobalFilter **适配**成 GatewayFilter（因为过滤器链只认 `GatewayFilter` 接口）：

```java
private static List<GatewayFilter> loadFilters(List<GlobalFilter> filters) {
    return filters.stream().map(filter -> {
        GatewayFilterAdapter adapter = new GatewayFilterAdapter(filter);  // ① 包成 GatewayFilter
        if (filter instanceof Ordered) {
            int order = ((Ordered) filter).getOrder();
            return new OrderedGatewayFilter(adapter, order);             // ② 带 order 再包一层
        }
        return adapter;
    }).collect(Collectors.toList());
}
```

```java
// GatewayFilterAdapter：把 GlobalFilter 适配成 GatewayFilter（版本不同可能是内嵌类或独立类）
private static class GatewayFilterAdapter implements GatewayFilter {
    private final GlobalFilter delegate;
    public GatewayFilterAdapter(GlobalFilter delegate) { this.delegate = delegate; }
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // 实际就是调用 GlobalFilter 的方法
        return this.delegate.filter(exchange, chain);
    }
}
```

> 适配的本质：`GlobalFilter` 与 `GatewayFilter` **接口签名完全相同**，只是语义不同（全局 vs 路由级）。`GatewayFilterAdapter` 做一层**类型适配**，`OrderedGatewayFilter` 再固定其 **order**——所以自定义 GlobalFilter / 路由 GatewayFilter 在链里都是 `GatewayFilter`，才能统一排序、统一递归。

#### 1.7.2 handle()：合并 + 排序 + 递归

```java
@Override
public Mono<Void> handle(ServerWebExchange exchange) {
    Route route = exchange.getRequiredAttribute(GATEWAY_ROUTE_ATTR);       // ① 取当前命中的 Route
    List<GatewayFilter> gatewayFilters = route.getFilters();               // ② 路由级过滤器(已是 GatewayFilter)
    List<GatewayFilter> combined = new ArrayList<>(this.globalFilters);     // ③ this.globalFilters 已是适配后的 List<GatewayFilter>
    combined.addAll(gatewayFilters);                                        // ④ 两个来源合并
    AnnotationAwareOrderComparator.sort(combined);                          // ⑤ 按 order 排序
    return new DefaultGatewayFilterChain(combined).filter(exchange);        // ⑥ 构建链递归执行
}
```

要点：
- `this.globalFilters`（构造时已 `loadFilters`）与 `route.getFilters()` 都是 `List<GatewayFilter>`，合并成一个 List。
- `AnnotationAwareOrderComparator.sort(combined)` 按 `Ordered.getOrder()` / `@Order` **升序**排序 —— **order 越小越先执行**（先进入 pre，后进入 post）。
- `DefaultGatewayFilterChain` 用迭代器递归执行 `Chain`——依次调用每个 filter，通过各自 `chain.filter()` 内联后置逻辑形成洋葱模型。

**「越小越先」的边界值（理解内置全局过滤器顺序的关键）**：

| 常量 | 值 | 含义 |
|---|---|---|
| `Ordered.HIGHEST_PRECEDENCE` | `Integer.MIN_VALUE`（-2^31） | 最高优先，最先进 pre |
| `Ordered.LOWEST_PRECEDENCE` | `Integer.MAX_VALUE`（2^31-1） | 最低优先，最后进 pre / 最先出 post |
| 未实现 `Ordered`/`@Order` | 视为 `LOWEST_PRECEDENCE` | 默认落在最次优先级 |

对照内置顺序：`RemoveCachedBodyFilter(MIN)` → `RouteToRequestUrlFilter(10000)` → `ReactiveLoadBalancerClientFilter(10100)` → `WebsocketRoutingFilter(MAX-1)` → `NettyRoutingFilter / ForwardRoutingFilter(MAX)`。**自定义鉴权等用负数 order**（如 `-100`）即排在 `10000` 的转发过滤器之前，先完成校验才放行。

> ⚠️ **版本差异**：早期版本适配器是 `FilteringWebHandler.GatewayFilterAdapter` 内嵌类；较新版本（Spring Cloud 2021+）使用独立 `GlobalFilterAdapter.generateOrder/filter` 配合 `loadFilters`，机制一致。写作时以你实际引入的版本为准（可看 `FilteringWebHandler` 源码第一行 `List<GlobalFilter> globalFilters` 与 `loadFilters` 方法）。

---
