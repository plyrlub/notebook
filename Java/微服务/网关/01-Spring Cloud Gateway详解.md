---
tags: [Java, 微服务, Spring Cloud Gateway, 网关, 路由, 过滤, 鉴权, Spring Security, 学习笔记]
创建日期: 2026-08-16
状态: ✅ 已归档（01-学习/Java/微服务/网关）
归属: 01-学习/Java/微服务/网关
---

# Spring Cloud Gateway 详解

> 微服务**流量统一入口**（WebFlux + Netty 响应式网关，Spring 官方第二代网关方案）。讲透：路由/断言/过滤器三大件、**内置过滤器工厂**、限流、以及与 **Spring Security 的关联鉴权**（重点）。
> 前置：微服务架构([00-微服务总览](../00-微服务总览.md))、响应式基础([14-Spring WebFlux响应式编程实践](../../框架/springboot/14-Spring WebFlux响应式编程实践.md))、Spring Security 基础(**00-安全框架选型总览**（见知识库） Apache Shiro]]).

## 📋 总纲

1. Gateway 是什么、为什么
2. 三大核心：路由 Route / 断言 Predicate / 过滤器 Filter
3. 内置断言与过滤器工厂（⭐常用）
4. 自定义全局过滤器 GlobalFilter + 顺序
5. 限流：RequestRateLimiter(Redis 令牌桶) ⭐
6. 跨域 / 重试 / 熔断
7. **与 Spring Security 的关联鉴权（⭐重点）**
8. 配置实战（Nacos 服务发现 + 路由）
9. 生产最佳实践
10. 面试高频 Q&A
11. 参考

---

## 1. Gateway 是什么、为什么

**一句话**：微服务**统一流量入口**，做路由转发、统一鉴权、限流、跨域、日志、重试等"网关横切"，让下游服务专注业务。

**为什么需要**：
- 客户端不该直连一堆微服务（暴露端口、难以统一处理）。
- 统一入口做**认证/限流/路由/日志**，一次配置全局生效。
- **Zuul1 已过时**（Servlet 阻塞式）；Spring Cloud Gateway 基于 **WebFlux + Netty + Reactor**，非阻塞、性能高，是官方推荐。

```
客户端 → Spring Cloud Gateway(Netty/WebFlux)
              ├─ 路由匹配(Predicate)
              ├─ 过滤器链(Global+Route)
              ├─ 限流RequestRateLimiter
              ├─ 统一鉴权(此处可组合Spring Security/JWT)
              └→ 转发到 lb://service-micro
```

> ⚠️ 注意：Gateway 是 **WebFlux(Reactive)** 应用，**不能依赖 MVC/Servlet** 那套；Spring Security 需用 **Reactive** 配置。

---

## 2. 三大核心：路由 / 断言 / 过滤器

```
Route = id + uri(目标) + 一组 Predicate(匹配条件) + 一组 Filter(处理)
路由匹配: 请求满足所有 Predicate → 路由命中 → 按过滤器链处理 → 转发到 uri
```

| 概念 | 英文 | 作用 |
|---|---|---|
| **路由** | Route | 一条转发规则：id + 目标 uri + 断言 + 过滤器 |
| **断言** | Predicate | 匹配条件（路径/Header/Query/时间…），满足才走该路由 |
| **过滤器** | Filter | 请求/响应处理（改头/重写路径/限流/鉴权…）|

**配置长这样：**
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service          # 路由id
          uri: lb://order-service    # 目标(服务发现 lb:// + 服务名)
          predicates:                # 断言(匹配条件)
            - Path=/api/order/**     # 路径前缀匹配
            - Method=GET,POST
          filters:                   # 过滤器(处理)
            - StripPrefix=2          # 去掉前2段前缀(/api/order/xxx→/xxx)
            - AddRequestHeader=X-Request-ID, abc-123
```

> 路由优先级：**先匹配先命中**，`order` 字段可调；避免**路径前缀重复**。

---

## 3. 内置断言与过滤器工厂（⭐ 常用）

### 3.1 内置断言（12+ 种）

| 断言 | 说明 | 例 |
|---|---|---|
| `Path` | 路径匹配 | `Path=/api/**` |
| `Method` | 请求方法 | `Method=GET,POST` |
| `Header` | 请求头含值 | `Header=X-Token,^\d+$` |
| `Query` | 查询参数 | `Query=page,\d+` |
| `Cookie` | Cookie 匹配 | `Cookie=name,value` |
| `Host` | Host(域名) | `Host=**.example.com` |
| `Before/After/Between` | 时间窗口 | `After=2026-01-01T00:00:00Z[Asia/Shanghai]` |
| `RemoteAddr` | 客户端 IP | `RemoteAddr=192.168.0.0/16` |
| `Weight` | 加权路由 | `Weight=group1, 8` |

> 多个断言组合用 **逻辑 and**：所有满足才命中。

### 3.2 内置过滤器工厂（30+）

| 过滤器 | 作用 | 例 |
|---|---|---|
| `StripPrefix` | 去路径前缀 | `StripPrefix=2` |
| `RewritePath` | 路径重写 | `RewritePath=/api/(?<seg>.*), /$\{seg}` |
| `AddRequestHeader` | 加请求头 | `AddRequestHeader=X-Id, 123` |
| `AddResponseHeader` | 加响应头(跨域) | `AddResponseHeader=Access-Control-Allow-Origin, *` |
| `RemoveRequestHeader` | 删请求头 | — |
| `RequestRateLimiter` | 限流 | 见 §5 |
| `Retry` | 重试 | 见 §6 |
| `SetStatus` | 设状态码(熔断降级) | `SetStatus=503` |
| `CircuitBreaker` | 熔断(配合 Resilience4j) | — |
| `PrefixPath` | 加前缀 | — |

> 🔑 **别再手写通用功能**：官方内置 30+ 过滤器工厂，Header/路径/限流/重试/熔断多靠配置即可，少写 80% 重复代码。

---

## 4. 自定义全局过滤器 GlobalFilter + 顺序

**GlobalFilter** 对所有路由生效（vs GatewayFilter 仅绑定指定路由）；实现 `GlobalFilter` + `Ordered`，用 `order`(数字越小越先) 控制链顺序。

```java
@Component
public class AuthGlobalFilter implements GlobalFilter, Ordered {
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        // 预: 解析/校验 token、记日志、改头
        ServerHttpRequest mutated = request.mutate()
            .header("X-User-Id", "123")   // 塞入透传信息
            .build();
        return chain.filter(exchange.mutate().request(mutated).build());
        // 响应侧可用 .then(...) 后处理
    }
    @Override
    public int getOrder() { return -100; }  // 越小越先,负数=全局过滤器之前/更前
}
```

> 执行顺序：`GlobalFilter` + 路由 `GatewayFilter` 合并成链，按 `Ordered` 排序。**鉴权过滤器 order 要小**(先执行)，限流/路由其后。

---

## 5. 限流：RequestRateLimiter（Redis 令牌桶）⭐

网关级限流用 `RequestRateLimiter`，底层 **Redis 令牌桶**(`RedisRateLimiter`)：

```
请求 → 匹配路由 → RequestRateLimiter → KeyResolver解析key → RedisRateLimiter令牌桶判断
                                    └ 超限返回 429 Too Many Requests
```

**配置：**
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
          filters:
            - name: RequestRateLimiter
              args:
                key-resolver: "#{@userKeyResolver}"   # 用哪个 bean 解析限流维度
                redis-rate-limiter.replenishRate: 10    # 令牌补充速率(每秒填10个)
                redis-rate-limiter.burstCapacity: 20   # 桶容量(允许突发20)
```
**KeyResolver（按用户/IP/接口限流）：**
```java
@Bean
public KeyResolver userKeyResolver() {
    // 按请求头 X-User-Id 或 IP 作为限流 key
    return exchange -> Mono.just(
        exchange.getRequest().getHeaders().getFirst("X-User-Id")
    );
}
```

> 🔑 限流维度由 KeyResolver 决定：按**用户/接口/IP**分别建令牌桶。超限默认返回 **429**。这正好与治理域 $\leftarrow$ [01-Sentinel流量控制详解](../治理/01-Sentinel流量控制详解.md) 网关层限流协同（网关限流挡住入口，Sentinel 服务内限流兜底）。

---

## 6. 跨域 / 重试 / 熔断

```yaml
spring:
  cloud:
    gateway:
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "https://front.example.com"   # 限域名(别用 *)
            allowedMethods: "*"
            allowedHeaders: "*"
      routes:
        - id: retry-route
          uri: lb://backend
          predicates: [ Path=/api/** ]
          filters:
            - name: Retry
              args:
                retries: 3              # 最多重试3次
                statuses: BAD_GATEWAY,SERVICE_UNAVAILABLE   # 500/502/503 重试
                backoff:
                  firstBackoff: 10ms
                  maxBackoff: 1s
                  factor: 2
            - name: CircuitBreaker       # 网关熔断(配合Resilience4j)
              args:
                name: cb
                fallbackUri: forward:/fallback
```

> 说明：`Retry` 对可重试状态码(502/503)退避重试提升可用；`CircuitBreaker` 网关做服务级熔断转发 fallback。跨域 `CORS` 统一在网关配(比各服务各配省事)。

---

## 7. 与 Spring Security 的关联鉴权（⭐ 重点）

### 7.1 两种组合方式

**方式 A：网关用 Spring Security(Reactive) 过滤链做统一鉴权**（推荐，OAuth2 Resource Server）
```
请求 → Gateway 的 Spring Security 过滤链(Reactive)
        → JWT校验(Resource Server/OAuth2)  → 提取 claims(权限)
        → 路由级鉴权 → 放行转发(透传用户上下文)
```
**方式 B：自定义 GlobalFilter + JwtDecoder 做 JWT 统一校验**（轻量自定义）
```
请求 → AuthGlobalFilter(order最小)
        → 解析/校验 JWT → 不合法 401
        → 合法: 解析claims → 塞入header(UserContext) → 转发下游
```

> 🔑 两者本质相同（网关统一认证），区别：**方式A用 Spring Security 官方 OAuth2 Resource Server**（标准、支持 scope/authority 体系）；**方式B手写 GlobalFilter**（轻、灵活、少依赖）。生产常用 **A（Security + JWT）** 或 **A-B 混合**。

### 7.2 职责分工：网关看"能不能进来"，服务内看"能不能做"

| 层 | 职责 | 用啥 |
|---|---|---|
| **网关(统一认证+入口鉴权)** | Token/JWT 是否有效、是否放行进系统、限流、路由 | Gateway + Security Resource Server(Gateway的Reactive) |
| **下游服务(细粒度授权)** | 登录用户能否做某操作(角色/权限) | 服务内 Spring Security(@PreAuthorize 方法级) |

```
客户端 → [网关: JWT校验 → 通过则塞X-User-Id头] → 下游服务
                                          ↓ 服务内 Security 再校验方法级权限
```
- **网关统一认证**：验 JWT、边界安全(80% 漏洞在服务边界)，下游不用重复实现认证。
- **透传身份头**：网关把解析出的 userId/角色写进 header(如 `X-User-Id`、`X-User-Roles`)，下游服务读取(或下游也用 Security 解析一次)。
- **服务内最终授权**：敏感操作仍需服务内 `@PreAuthorize("hasRole('ADMIN')")` 兜底（网关只做入口级）。

### 7.3 集成代码（方式 A，Spring Security Resource Server）

```xml
<!-- Gateway 模块 -->
<dependency>org.springframework.cloud:spring-cloud-starter-gateway</dependency>
<dependency>org.springframework.boot:spring-boot-starter-oauth2-resource-server</dependency>
<dependency>com.nimbusds:nimbus-jose-jwt</dependency>
```
```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: http://auth-server/.well-known/jwks.json   # 验证JWT的公钥源
```
```java
// Gateway 内 Reactive Security 配置: 放行白名单 + 其余需JWT
@Configuration
@EnableWebFluxSecurity
public class GatewaySecurityConfig {
    @Bean
    public SecurityWebFilterChain gatewaySecurity(ServerHttpSecurity http) {
        http
            .csrf(c -> c.disable())
            .authorizeExchange(auth -> auth
                .pathMatchers("/auth/**", "/actuator/**").permitAll()   // 白名单
                .anyExchange().authenticated())                          // 其余需登录(token)
            .oauth2ResourceServer(o -> o.jwt());                        // JWT 校验
        return http.build();
    }
}
```
```java
// 透传: 自定义 GlobalFilter 把 JWT 里的 userId 塞进 header 给下游
@Component
public class UserContextFilter implements GlobalFilter, Ordered {
    public Mono<Void> filter(ServerWebExchange ex, GatewayFilterChain chain) {
        Authentication auth = ex.getPrincipal()
            .cast(Authentication.class)
            .blockOptional().map(a -> (Authentication)a).orElse(null);
        String uid = (auth != null) ? auth.getName() : null;
        ServerHttpRequest r = ex.getRequest().mutate()
            .header("X-User-Id", uid == null ? "" : uid).build();
        return chain.filter(ex.mutate().request(r).build());
    }
    public int getOrder() { return -100; }
}
```

> ⚠️ 关键点：Gateway 是 WebFlux，Security 配置用 `@EnableWebFluxSecurity` + `SecurityWebFilterChain`（**不是** MVC 的 WebSecurityConfigurerAdapter）。`oauth2ResourceServer` 自动做 JWT 校验，`authenticated()` 做入口鉴权。

### 7.4 你能回答的关联本质

> 🔑 **网关 × Spring Security 的关系**：
> - **Spring Security 不是"必须要在网关"**，也不"只能服务内"——它是**可插的安全框架**，在网关(Reactive)做入口统一认证，在服务内(MVC)做细粒度授权。
> - 网关 + Security = **一次验 JWT、全局防线、透传身份**；服务内 Security = **方法级权限兜底**。分层互补。
> - 简单/小项目：网关只做路由+JWT，服务内接管全部授权；复杂：网关做统一认证+路由鉴权，服务内做业务级权限。

---

## 8. 配置实战（Nacos 服务发现 + 路由）

```xml
<dependency>org.springframework.cloud:spring-cloud-starter-gateway</dependency>
<dependency>com.alibaba.cloud:spring-cloud-starter-alibaba-nacos-discovery</dependency>
```
```yaml
server:
  port: 8080
spring:
  application:
    name: gateway
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848   # Nacos 注册中心
    gateway:
      discovery:
        locator:
          enabled: true    # 自动为已注册服务生成路由(可选)
      routes:
        - id: user-service
          uri: lb://user-service            # lb 负载均衡到服务发现实例
          predicates: [ Path=/api/user/** ]
          filters: [ StripPrefix=2 ]
        - id: order-service
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
          filters: [ StripPrefix=2 ]
```
```
启动 Gateway → 注册到 Nacos → 客户端访问 http://网关:8080/api/user/xx
→ 路由匹配 → 转发到 user-service 实例
```

> ⚠️ 路由注意：`lb://服务名` 走服务发现负载均衡；**路径前缀避免重复**(`/api/user/**` 与 `/api/**` 别同时这样配)。

---

## 9. 生产最佳实践

- **统一鉴权放网关**：Reactive Security/JWT 一次配置，下游免重复认证；透传身份头。
- **网关限流挡入口**：RequestRateLimiter(Redis) 按用户/IP/接口，超限 429；再配服务内 Sentinel 兜底。
- **CORS 网关统一配**：别在各服务各配。
- **重试/熔断**：网关 Retry(可重试状态)、CircuitBreaker(fallback) 提升可用。
- **白名单**：/auth、/actuator 等 permitAll，其余 authenticated。
- **简洁路由**：避免前缀重复、用 order 排优先级。
- **监控**：配合 Actuator/Metric，观察限流 429 数、熔断事件。

### 9.1 网关 vs Nginx 边界（遗漏补充 ⭐）

```
客户端 → [Nginx(服务端/LB) → Spring Cloud Gateway(应用网关) → 微服务]
            ↑ 7层LB/静态资源/SSL      ↑ 业务路由/鉴权/限流/转发
```

| 维度 | Nginx | Spring Cloud Gateway |
|---|---|---|
| 定位 | **服务端入口/LB**(反向代理) | **应用/业务网关** |
| 主要能力 | 静态资源、7层负载均衡、SSL、反向代理 | 业务路由、统一鉴权、限流、重试、熔断 |
| 关注点 | 网络/流量分发 | 业务/微服务协作 |
| 运维 | 运维主导 | 开发主导 |
| QoS控制 | 基本 | 强(令牌桶/Resilience4j/Sentinel) |
| 动态路由/服务发现 | 配置为主 | 支持(Nacos/CI) |

> 一句话：**Nginx 管"流量进不进、分给谁"(LB/静态/SSL)，Gateway 管"业务请求怎么处理、鉴权限流、转发到哪个微服务"**。大流量通常 Nginx 在前、Gateway 在后双网关，也可 Nginx 直连服务(简单场景)。

### 9.2 网关高可用 / 横向扩展（遗漏补充 ⭐）

- **网关无状态** → 可**多实例横向扩展** + 前置负载均衡（Nginx/云 LB），提升吞吐与可用。
- **多实例**：`Gateway` 实例注册到 Nacos，LB 分发；无 session(除限流/熔断状态存 Redis)。
- **依赖外部状态**：请求限流状态(Redis)、规则/路由配置(配置中心/Nacos)、熔断状态(Redis 可选)——**无状态化**才能水平扩。
- **健康检查/优雅**：接 Actuator `/actuator/health`，LB 自动摘除故障实例；下线先摘流量再停。

```
Client → LB(Nginx/SLB) → Gateway实例1 / 实例2 / 实例3(都注册Nacos,共享Redis) → 微服务
```
> 结论：**网关要能扩，前置 LB + 无状态 + 外部存储(Redis/Nacos)**。这是生产网关可靠性的关键。

---

### 9.3 背压 Backpressure（遗漏补充 ⭐）

**背压 = 协调上下游速度不匹配**——消费者处理慢时，信号反馈给生产者"慢点发"，防止内存溢出/崩溃。响应式(Reactive)核心机制。

```
生产者(快) ──request(n)──> 消费者(慢)
          <── 背压信号 ──
request(n): 消费者按自己能处理的量向生产者"请求"数据数 → 生产者只发 n 个 → 防积压
```

**背压 vs 限流/熔断**：

| 机制 | 维度 | 区别 |
|---|---|---|
| 背压 | 流式数据量订阅 | 响应式 `request(n)`，消费者主动控制拉取速率 |
| 限流 | 请求速率 | 限 QPS，超限拒/队列 |
| 熔断 | 下游故障 | 持续故障切断 |

> 背压是"消费者保护自己"（慢点接）；限流是"生产者保护自己"（少放点）。网关是 WebFlux 响应式，接收/转发天然可用背压协调。

**WebFlux/Gateway 里的背压策略**：
- **限流（RateLimiter）**：网关用 Redis 令牌桶限流 = 防过量的背压手段。
- **缓冲/丢弃/抛异常**：`onBackpressureBuffer/drop/error` 处理超出能力的数据。
- **端到端**：gRPC/RSocket/HTTP2 流式自带背压控制（Dubbbo Triple 有 send/receive-side backpressure）。

```java
Flux<Item> stream = source.onBackpressureDrop();  // 超出能力直接丢弃(可聚合告警)
// 或 onBackpressureBuffer(容量) / onBackpressureError
```
> 一句话：**响应式下背压用 `request(n)` + 背压策略(buffer/drop/error) 控流量**，防止消费者被生产者压垮。

---

### 9.4 优雅停机 / 服务下线（遗漏补充 ⭐）

**为什么不能裸 kill**：`kill -9` 强杀 → ①正在执行的任务中断 ②**没从注册中心下线**，consumer/网关仍调用 → 报 Connection refused（请求打挂）。

**优雅下线三步**（发布/扩容时的用户无感知）：

```
① 摘流量: 先从 LB/注册中心把实例摘除或标记下线使不再收新请求
② 停等处理中请求: kill -15 / 触发优雅停机 → 处理完在途请求(E起 in-flight)再退出
③ 安全关资源: 关闭连接池/线程池/后台任务, 再真正退出进程
```

**Spring Boot 配置优雅停机**：

```yaml
server:
  shutdown: graceful      # Boot 2.3+ 优雅停机
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s   # 最多等30s处理在途请求
```

**配合注册中心下线**：
- 发布脚本先调 `POST /actuator/shutdown`（或 kill -15）+ 从注册中心 `deregister`，等 consumer 列表刷新后再停。
- **K8s**：配合 `preStop` hook + 就绪探针（等注册完成才对外），避免新旧实例交替空窗。

> 一句话：**优雅下线 = 先摘流量(注册中心/LB) + 处理在途 + 再退出**。直接 kill -9 既不处理在途工作、又不摘注册中心，会造成调用失败。这是微服务发布稳定性关键（防"服务还没注册完就被下线"空窗）。

---

## 10. 面试高频 Q&A

- **Spring Cloud Gateway 和 Zuul？** Gateway 基于 WebFlux/Netty 响应式非阻塞性能高，官方推荐；Zuul1 阻塞 Servlet 过时。
- **三大核心？** Route、Predicate(匹配)、Filter(处理)；请求满足 Predicate 命中 Route，按 Filter 链转发。
- **GatewayFilter vs GlobalFilter？** 路由级 vs 全局；合并链按 Ordered 排序。
- **RequestRateLimiter 怎么限流？** Redis 令牌桶 + KeyResolver(按用户/IP/接口维度)。
- **网关怎么做统一鉴权？** Reactive Security(oauth2ResourceServer + jwt) 或自定义 GlobalFilter 校验 JWT + 透传身份头。
- **网关和 Spring Security 什么关系？** 网关(Reactive Security)做入口统一认证，服务内 Security 做方法级授权，分层互补。
- **网关 vs Nginx？** Nginx 服务端入口/LB(流量分发/静态/SSL)，Gateway 应用网关(业务路由/鉴权/限流)，可 Nginx+Gateway 双网关叠加。
- **网关怎么保证高可用？** 无状态 + 多实例 + 前置 LB + 外部存储(Redis限流/Nacos) + 健康检查。
- **Gateway 为什么是 WebFlux？** 底层 Netty + Reactor 响应式，不能用 MVC/Servlet。

---

## 11. 参考

- [Spring Cloud Gateway 中文文档（路由断言/过滤器）](https://springdoc.cn/spring-cloud-gateway/)
- [Spring Cloud Gateway 配置路由谓词工厂和过滤器工厂](https://docs.springjava.cn/spring-cloud-gateway/reference/spring-cloud-gateway/configuring-route-predicate-factories-and-filter-factories.html)
- [Spring Cloud Gateway GlobalFilter（官方）](https://docs.spring.io/spring-cloud-gateway/reference/spring-cloud-gateway-server-webflux/global-filters.html)
- [RequestRateLimiter Filter（官方）](https://docs.spring.io/spring-cloud-gateway/reference/4.3/spring-cloud-gateway-server-webflux/gatewayfilter-factories/requestratelimiter-factory.html)
- [Spring Cloud Gateway 与 Spring Security 整合（JWT）](https://codechina.net/article/weixin_32466193/100634)
- [Spring Cloud Gateway 统一 JWT 校验（CSDN）](https://wenku.csdn.net/answer/39yrr22djm)
- 查证 2026-08
- 关联：[00-微服务总览](../00-微服务总览.md)、[01-Sentinel流量控制详解](../治理/01-Sentinel流量控制详解.md)（限流兜底）、[00-安全框架选型总览·Spring Security & Apache Shiro](../../框架/安全/00-安全框架选型总览·Spring Security & Apache Shiro.md)（Security 基础）、[00-中间件总览](../../中间件/00-中间件总览.md)（Nacos）
