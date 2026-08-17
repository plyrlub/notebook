---
tags: [Java, 微服务, Spring Cloud Gateway, 网关, 路由, 过滤, 鉴权, Nacos, Redis, 实践, 学习笔记]
创建日期: 2026-08-18
状态: ✅ 已归档（01-学习/Java/微服务/网关）
归属: 01-学习/Java/微服务/网关
---

# Spring Cloud Gateway 实践

> 配套 [01-Spring Cloud Gateway详解](01-Spring Cloud Gateway详解.md) 的**可照抄工程模板**：搭建一个生产向 Spring Boot 3 + Spring Cloud Gateway 网关，集成 **Nacos 服务发现 + Redis 令牌桶限流 + Spring Security(JWT) 统一鉴权 + 自定义全局过滤器 + 动态路由刷新**。全流程可据本模板落地。
> 环境要求：JDK 17+、Maven、Nacos Server、Redis。若本机未起 Nacos/Redis，可先按 §4 逐步验证非依赖环节（如路由、过滤器、JWT）后再补环境。

## 📋 目录

1. 工程骨架与依赖
2. 基础配置（端口 / 数据源）
3. Nacos 服务发现 + 静态路由
4. 自定义全局过滤器（日志 / 身份透传）
5. Redis 令牌桶限流
6. Spring Security(JWT) 统一鉴权
7. TokenRelay 透传 token
8. 动态路由刷新（Nacos）
9. 联合验证流程

---

## 1. 工程骨架与依赖

`pom.xml`：

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
    <relativePath/>
</parent>
<properties>
    <java.version>17</java.version>
    <spring-cloud.version>2023.0.3</spring-cloud.version>
    <spring-cloud-alibaba.version>2023.0.1.0</spring-cloud-alibaba.version>
</properties>
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>${spring-cloud-alibaba.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency> <!-- 网关 -->
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-gateway</artifactId>
    </dependency>
    <dependency> <!-- Nacos 注册 + 配置 -->
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
    </dependency>
    <dependency> <!-- Redis 限流 -->
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
    </dependency>
    <dependency> <!-- 安全(JWT ResourceServer) -->
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

> 版本基线：Spring Boot 3.3 / Spring Cloud 2023.0.3 / Nacos Alibaba 2023.0.1.0。若沿用本项目其它笔记的 Boot 2.x 堆栈，需对应下调版本并适配 `jakarta.*

---

## 2. 基础配置

`application.yml`：

```yaml
server:
  port: 8080
  shutdown: graceful                        # 优雅停机
spring:
  application:
    name: gateway
  lifecycle:
    timeout-per-shutdown-phase: 30s
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        namespace: public                    # 生产建议独立 namespace
      config:
        server-addr: 127.0.0.1:8848
        file-extension: yml
        namespace: public
    gateway:
      discovery:
        locator:
          enabled: false                     # 明确关闭自动发现, 只走显式路由
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "https://front.example.com"
            allowedMethods: "*"
            allowedHeaders: "*"
            allowCredentials: true
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: http://127.0.0.1:9000/.well-known/jwks.json   # 认证服务公钥源

logging:
  level:
    org.springframework.cloud.gateway: DEBUG   # 开发期查看路由/过滤链; 生产降为 INFO
management:
  endpoints:
    web:
      exposure:
        include: gateway,health,info
```

---

## 3. Nacos 服务发现 + 静态路由

`application.yml` 追加路由（静态，随配置装载）：

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          order: 10
          predicates:
            - Path=/api/user/**
          filters:
            - StripPrefix=2                       # /api/user/xx → /xx
            - AddRequestHeader=X-Source, gateway
        - id: order-service
          uri: lb://order-service
          order: 10
          predicates:
            - Path=/api/order/**
          filters:
            - StripPrefix=2
        - id: detailed-path (示例: 精确路径路由置于通配前)
          uri: lb://user-service
          order: 0
          predicates:
            - Path=/api/user/detail
          filters:
            - StripPrefix=2
```

**验证路由**：启动后查看
```bash
curl http://localhost:8080/actuator/gateway/routes
```
输出为当前生效的路由（含 uri、predicates、filters、order），可用于核对匹配顺序。

---

## 4. 自定义全局过滤器

### 4.1 请求日志 + 耗时

```java
@Component
public class AccessLogFilter implements GlobalFilter, Ordered {
    private static final Logger log = LoggerFactory.getLogger(AccessLogFilter.class);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long start = System.currentTimeMillis();
        return chain.filter(exchange)
            .then(Mono.fromRunnable(() -> {
                ServerHttpResponse resp = exchange.getResponse();
                log.info("path={} method={} status={} cost={}ms",
                    exchange.getRequest().getURI().getPath(),
                    exchange.getRequest().getMethod(),
                    resp.getStatusCode(),
                    System.currentTimeMillis() - start);
            }));
    }

    @Override
    public int getOrder() { return -200; }   // 靠前, 先记日志
}
```

### 4.2 身份透传（下游读取 userId/roles）

```java
@Component
public class UserContextFilter implements GlobalFilter, Ordered {
    @Override
    public Mono<Void> filter(ServerWebExchange ex, GatewayFilterChain chain) {
        // 认证态已由 Spring Security 放在 Principal 中
        String uid = ex.getPrincipal()
            .cast(Authentication.class)
            .blockOptional().map(Authentication::getName).orElse("");
        ServerHttpRequest req = ex.getRequest().mutate()
            .header("X-User-Id", uid)
            .header("X-Gateway", "true")
            .build();
        return chain.filter(ex.mutate().request(req).build());
    }
    @Override
    public int getOrder() { return -100; }   // 鉴权透传在安全校验之后、转发之前
}
```

---

## 5. Redis 令牌桶限流

### 5.1 KeyResolver

```java
@Configuration
public class RateLimitConfig {
    @Bean
    public KeyResolver remoteAddrKeyResolver() {
        // 按来源 IP 限流
        return exchange -> Mono.just(
            exchange.getRequest().getRemoteAddress().getAddress().getHostAddress());
    }

    // 按用户头限流(与 UserContextFilter 配合): 取 X-User-Id
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> Mono.just(
            exchange.getRequest().getHeaders().getFirstOrDefault("X-User-Id", "anon"));
    }
}
```

> 多个 `KeyResolver` 并存时用 `#{@beanName}` 在路由中显式指定，避免默认注入冲突。

### 5.2 路由挂限流

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
          filters:
            - StripPrefix=2
            - name: RequestRateLimiter
              args:
                key-resolver: "#{@userKeyResolver}"
                redis-rate-limiter.replenishRate: 10    # 平均 10 QPS
                redis-rate-limiter.burstCapacity: 20    # 突发桶 20
```

**验证**：Redis 中写入限流 key（按维度），压测观察 200 / 429 分布。

---

## 6. Spring Security(JWT) 统一鉴权

### 6.1 Reactive 安全配置

```java
@Configuration
@EnableWebFluxSecurity
public class GatewaySecurityConfig {
    @Bean
    public SecurityWebFilterChain gatewaySecurity(ServerHttpSecurity http) {
        return http
            .csrf(c -> c.disable())
            .authorizeExchange(auth -> auth
                .pathMatchers("/auth/**", "/actuator/**").permitAll()
                .pathMatchers("/api/order/**").hasAuthority("SCOPE_order:read")
                .anyExchange().authenticated())
            .oauth2ResourceServer(o -> o.jwt())
            .build();
    }
}
```

> scope 匹配用 `hasAuthority("SCOPE_xxx")`；角色可用 `hasRole("ADMIN")`。如需把 JWT 中的自定义 claims（如 userId）暴露给后续过滤器读取，可在 `lambda` 中配置 `JwtAuthenticationConverter` 添加 Authority。

### 6.2 生效链路

```
请求 → Spring Security(Reactive) 过滤链 → oauth2ResourceServer 校验 JWT 签名(公钥源)
     → scope/authority 路由级鉴权 → 放行(Principal 含认证信息) → UserContextFilter 透传身份头 → 转发
```

---

## 7. TokenRelay 透传 token

当下游服务也是 OAuth2 Resource Server、需要继续校验原始 Access Token 时，用 `TokenRelay` 把网关已认证用户的 token 原样透传：

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
          filters:
            - TokenRelay            # 从 SecurityContext 取 token 传给下游
```

前提：网关通过 `spring.security.oauth2.client.registration.*` 配置了 ClientRegistration（或经 resource server / oauth2Login 完成认证并持有 token）。

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          gateway-client:
            provider: auth-server
            client-id: gateway-client
            client-secret: secret
            authorization-grant-type: authorization_code
            scope: openid,order:read
        provider:
          auth-server:
            issuer-uri: http://127.0.0.1:9000
```

---

## 8. 动态路由刷新（Nacos）

把路由配置放入 Nacos 配置中心，变更后网关自动刷新，无需重启。

### 8.1 Nacos 配置（dataId）

`gateway-routes`（group `DEFAULT_GROUP`，格式 yml）：
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates: [ Path=/api/order/** ]
          filters: [ StripPrefix=2 ]
        - id: user-service
          uri: lb://user-service
          predicates: [ Path=/api/user/** ]
          filters: [ StripPrefix=2 ]
```

### 8.2 网关加载 + 刷新监听

方式一：`bootstrap.yml` 声明 Nacos Config 配置源，网关路由随配置刷新而更新（依赖 Config 客户端自动触发 Refresh）：

```yaml
# bootstrap.yml (仅作为配置源声明, 新版可直接用 application.yml + import)
spring:
  cloud:
    config:
      import: nacos:gateway-routes?group=DEFAULT_GROUP&refreshEnabled=true
```

方式二：监听刷新事件，手动触发 `RefreshRoutesEvent` 以确保路由源已重载：

```java
@Component
public class NacosGatewayRefresher
        implements ApplicationEventPublisherAware, ApplicationListener<RefreshScopeRefreshedEvent> {

    private ApplicationEventPublisher publisher;

    @Override
    public void setApplicationEventPublisher(ApplicationEventPublisher publisher) {
        this.publisher = publisher;
    }

    @Override
    public void onApplicationEvent(RefreshScopeRefreshedEvent event) {
        // 配置变更后重发路由刷新事件, 让 RouteDefinitionLocator 重新加载
        this.publisher.publishEvent(new RefreshRoutesEvent(this));
    }
}
```

> 依赖说明：若从自定义数据源（MySQL/Redis JSON）加载路由，则实现 `RouteDefinitionRepository` 并在此监听变更后 `publishEvent(new RefreshRoutesEvent(this))`（详见详解 §12）。

---

## 9. 联合验证流程

按顺序启动并验证：

1. 启动 Nacos（`:8848`）、Redis、认证服务（`:9000`，提供 JWK）、下游服务（`user-service` / `order-service` 注册 Nacos）。
2. 启动网关（`:8080`）。
3. `GET http://localhost:8080/actuator/gateway/routes` → 确认 3 条路由及其顺序。
4. 未带 token 访问 `http://localhost:8080/api/order/**` → 期望 `401`。
5. 向认证服务换取 JWT 后，带 `Authorization: Bearer <token>` 再访问 → 期望 `200` 并在下游日志确认收到 `X-User-Id`、`X-Gateway` 头。
6. 快速重复请求触发限流 → 期望出现 `429`。
7. 在 Nacos 修改 `gateway-routes`，观察待命后路由变化（日志或再次 query `/actuator/gateway/routes`）。

> 排查起点：`/actuator/gateway/routes`（匹配是否生效）、`/actuator/gateway/globalfilters`（过滤器顺序）、日志开关（生产关闭 DEBUG）。

---

## 参考

- [01-Spring Cloud Gateway详解](01-Spring Cloud Gateway详解.md)（原理 / 配置速查）
- [Spring Cloud Gateway 官方参考](https://docs.spring.io/spring-cloud-gateway/reference/)
- [Getting Started · Building a Gateway（官方 Guide）](https://spring.io/guides/gs/gateway)
- 关联：[00-微服务总览](../00-微服务总览.md)、[01-Sentinel流量控制详解](../治理/01-Sentinel流量控制详解.md)、[00-安全框架选型总览·Spring Security & Apache Shiro](../../框架/安全/00-安全框架选型总览·Spring Security & Apache Shiro.md)、[00-中间件总览](../../中间件/00-中间件总览.md)
