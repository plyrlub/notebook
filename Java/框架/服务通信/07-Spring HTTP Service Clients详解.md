---
tags: [Spring, HTTP Interface, HttpExchange, RestClient, 声明式, HTTP客户端, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/服务通信）
归属: 01-学习/Java/框架/服务通信
---

# 07-Spring HTTP Service Clients详解

> 版本基线：Spring Framework 6.1+ 引入的声明式 HTTP 客户端（@HttpExchange / HTTP Interface），**Spring 官方推荐替代 OpenFeign 的方案**
> 受众：Java 后端开发，新项目选型 HTTP 调用方案，或从 OpenFeign 迁移。默认你懂 Spring Boot、REST。
> 关联笔记：[00-RPC与远程调用总览](00-RPC与远程调用总览.md)、[06-OpenFeign详解](06-OpenFeign详解.md)、[05-gRPC详解](05-gRPC详解.md)

## 📋 总纲

- 1. 是什么：官方推荐的声明式 HTTP 客户端
- 2. Spring REST Clients 全景
- 3. 核心 API：@HttpExchange 系列注解
- 4. 客户端创建：HttpServiceProxyFactory
- 5. 方法参数与返回值
- 6. Spring Boot 集成
- 7. HTTP Service Groups（分组配置）
- 8. 与 OpenFeign 对比与迁移
- 9. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 HTTP Service Clients 的定位：Spring 官方推荐、替代 OpenFeign
2. 用 @HttpExchange/@GetExchange 等注解定义接口
3. 用 HttpServiceProxyFactory 创建客户端代理
4. 在 Spring Boot 中注册并注入 HTTP Service 接口
5. 对比它和 OpenFeign 的差异，知道迁移路径
6. 从 [06-OpenFeign详解](06-OpenFeign详解.md) 平滑迁移过来

## 前置知识

- [06-OpenFeign详解](06-OpenFeign详解.md)——对照理解（官方建议从它迁移）
- [00-RPC与远程调用总览](00-RPC与远程调用总览.md)——服务间调用方案全景
- 需掌握：Spring Boot、REST API 基础

---

## 1. 是什么：官方推荐的声明式 HTTP 客户端

**一句话记忆**：HTTP Service Clients（又称 HTTP Interface）是 Spring Framework 6.1+ 内置的**声明式 HTTP 客户端**——用 `@HttpExchange` 注解定义接口，框架生成代理，是 **Spring 官方推荐替代 OpenFeign 的方案**。

**为什么官方推荐**（OpenFeign feature-complete 公告背景，见 [06-OpenFeign详解](06-OpenFeign详解.md) §9）：

- **无第三方依赖**：Spring Framework 内置，不需要 OpenFeign 库
- **同一接口双端复用**：接口既是客户端契约，服务端 @Controller 可实现同一接口（契约统一）
- **三套后端可选**：底层可用 RestClient / WebClient / RestTemplate 三种 adapter
- **官方持续演进**：HTTP Service Groups（分组）、ApiVersionInserter 等新特性在加

```java
// 定义接口(契约)
public interface UserService {
    @GetExchange("/api/users/{id}")
    User getUserById(@PathVariable Long id);
}
```

> 💡 **记忆锚点**：**HTTP Interface = OpenFeign 的"官方平替"**——同样的声明式体验，但由 Spring 自己维护、无外部依赖。

---

## 2. Spring REST Clients 全景

Spring Framework 官方把 HTTP 客户端分为四类（官方文档 REST Clients 章节）：

| 客户端 | 类型 | 状态 | 适用 |
|---|---|---|---|
| **RestClient** | 同步流式 API | ✅ 推荐 | 通用同步调用（替代 RestTemplate） |
| **WebClient** | 响应式（非阻塞） | ✅ 维护 | 响应式/高并发 |
| **RestTemplate** | 模板方法 | ⚠️ 已弃用（官方建议换 RestClient） | 老代码 |
| **HTTP Service Clients** | 声明式接口 | ✅ 官方推荐新方案 | 接口化调用（替代 OpenFeign） |

**演进主线**：RestTemplate（老）→ RestClient（同步新宠）→ HTTP Interface（声明式，6.1+）。

---

## 3. 核心 API：@HttpExchange 系列注解

### 3.1 注解总览

| 注解 | 作用 |
|---|---|
| `@HttpExchange` | 类/方法级通用注解（可定义 url/headers 等公共属性） |
| `@GetExchange` | GET 请求 |
| `@PostExchange` | POST 请求 |
| `@PutExchange` | PUT 请求 |
| `@DeleteExchange` | DELETE 请求 |
| `@PatchExchange` | PATCH 请求 |

### 3.2 基本用法

```java
// 方法级:每个方法独立声明
public interface RepositoryService {

    @GetExchange("/repos/{owner}/{repo}")
    Repository getRepository(@PathVariable String owner, @PathVariable String repo);

    @PostExchange("/repos/{owner}/{repo}/issues")
    Issue createIssue(@PathVariable String owner, @PathVariable String repo,
                      @RequestBody IssueRequest request);
}

// 类级:公共属性(所有方法继承)
@HttpExchange(url = "/api/v1", accept = "application/json")
public interface OrderService {

    @GetExchange("/orders/{id}")     // 实际路径: /api/v1/orders/{id}
    Order getOrder(@PathVariable Long id);

    @PostExchange("/orders")
    Order create(@RequestBody OrderRequest request);
}
```

### 3.3 请求头/参数

```java
public interface SecureService {

    @GetExchange(value = "/users/{id}", accept = "application/json")
    User getUser(@PathVariable Long id,
                 @RequestHeader("Authorization") String token);   // 动态头

    @GetExchange("/search")
    List<User> search(@RequestParam("name") String name,
                      @RequestParam("age") Integer age);          // 查询参数
}
```

---

## 4. 客户端创建：HttpServiceProxyFactory

### 4.1 三种 adapter（底层客户端可选）

```java
// ① RestClient(推荐,同步)
RestClient restClient = RestClient.builder()
        .baseUrl("https://api.example.com")
        .defaultHeader("Accept", "application/json")
        .build();
RestClientAdapter adapter = RestClientAdapter.create(restClient);

// ② WebClient(响应式)
WebClient webClient = WebClient.builder().baseUrl("https://api.example.com").build();
WebClientAdapter adapter = WebClientAdapter.create(webClient);

// ③ RestTemplate(老代码迁移)
RestTemplate restTemplate = new RestTemplate();
RestTemplateAdapter adapter = RestTemplateAdapter.create(restTemplate);
```

### 4.2 创建代理

```java
HttpServiceProxyFactory factory = HttpServiceProxyFactory
        .builderFor(adapter)
        .build();

UserService userService = factory.createClient(UserService.class);
User user = userService.getUserById(42L);   // 像本地方法一样调用
```

---

## 5. 方法参数与返回值

| 参数/返回 | 注解/类型 | 说明 |
|---|---|---|
| 路径变量 | `@PathVariable` | URL 模板 `{id}` 占位 |
| 查询参数 | `@RequestParam` | 拼接到 URL |
| 请求头 | `@RequestHeader` | 请求头 |
| 请求体 | `@RequestBody` | 序列化为 body |
| Cookie | `@CookieValue` | Cookie |
| 返回值 | 任意类型 | 自动反序列化 |
| 泛型返回 | `ParameterizedTypeReference` | `List<User>` 等 |

```java
// 泛型返回示例
public interface PageService {
    @GetExchange("/users")
    List<User> listUsers();          // 直接 List<User>
}

// 或者用 ParameterizedTypeReference
@GetExchange("/users")
ParameterizedTypeReference<List<User>> usersRef();
```

---

## 6. Spring Boot 集成

### 6.1 依赖

HTTP Interface 是 Spring Framework 核心功能，**无需额外依赖**（Spring Boot 3.2+ / Framework 6.1+ 自带）：

```xml
<!-- 只需 Spring Boot Web 即可 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

### 6.2 注册为 Bean

```java
@Configuration
public class HttpClientConfig {

    @Bean
    public UserService userService(RestClient.Builder restClientBuilder) {
        RestClient restClient = restClientBuilder
                .baseUrl("http://user-service")
                .build();
        HttpServiceProxyFactory factory = HttpServiceProxyFactory
                .builderFor(RestClientAdapter.create(restClient))
                .build();
        return factory.createClient(UserService.class);
    }
}
```

### 6.3 注入使用

```java
@Service
public class UserQueryService {
    private final UserService userService;

    public UserQueryService(UserService userService) {
        this.userService = userService;
    }

    public User getUser(Long id) {
        return userService.getUserById(id);   // 直接调用
    }
}
```

---

## 7. HTTP Service Groups（分组配置）

> Spring Framework 7 / Boot 4 新增能力：把多个接口归为一组共享配置，避免重复创建 factory。

```java
// 声明分组:一组接口共享客户端配置
@Configuration
@ImportHttpServices(group = "echo", types = {EchoServiceA.class, EchoServiceB.class})
@ImportHttpServices(group = "greeting", basePackageClasses = GreetServiceA.class)
public class ClientConfig {

    // 按组定制配置
    @Bean
    public RestClientHttpServiceGroupConfigurer groupConfigurer() {
        return groups -> {
            groups.filterByName("echo").forEachClient((group, builder) -> {
                builder.baseUrl("http://echo-service");
            });
        };
    }
}

// 自动注入(Bean 已注册)
@RestController
public class EchoController {
    private final EchoServiceA echoService;
    public EchoController(EchoServiceA echoService) {
        this.echoService = echoService;
    }
}
```

**多组同名接口**：同一接口在多个组时无法按类型注入，用 `HttpServiceProxyRegistry` 按组获取：

```java
@RestController
public class EchoController {
    public EchoController(HttpServiceProxyRegistry registry) {
        EchoServiceA a = registry.getClient("echo1", EchoServiceA.class);
        EchoServiceA b = registry.getClient("echo2", EchoServiceA.class);
    }
}
```

---

## 8. 与 OpenFeign 对比与迁移

| 维度 | OpenFeign | HTTP Service Clients |
|---|---|---|
| 提供方 | Netflix → Spring Cloud | **Spring Framework 官方** |
| 依赖 | spring-cloud-starter-openfeign | **无额外依赖**（Framework 6.1+） |
| 注解 | @FeignClient + Spring MVC 注解 | @HttpExchange 系列（专用） |
| 底层 | 自研 + LoadBalancer | RestClient/WebClient/RestTemplate |
| 负载均衡 | Spring Cloud LoadBalancer | 需 Spring Cloud 集成（Boot 4 支持） |
| 熔断降级 | fallback/fallbackFactory | 需配合 CircuitBreaker/自定义 |
| 维护状态 | ⚠️ feature-complete（官方建议迁移） | ✅ 官方持续演进 |
| 服务端契约复用 | ❌ | ✅ 同一接口服务端可实现 |

**迁移路径（OpenFeign → HTTP Interface）**：

```java
// ① OpenFeign 写法(旧)
@FeignClient(name = "user-service")
public interface UserClient {
    @GetMapping("/api/users/{id}")
    User getUserById(@PathVariable("id") Long id);
}

// ② HTTP Interface 写法(新): 注解换成 @GetExchange, 注册方式换成 factory
public interface UserClient {
    @GetExchange("/api/users/{id}")
    User getUserById(@PathVariable Long id);
}

// ③ 注册 Bean 替代 @EnableFeignClients 扫描
@Bean
UserClient userClient(RestClient.Builder builder) {
    return HttpServiceProxyFactory.builderFor(
            RestClientAdapter.create(builder.baseUrl("http://user-service").build()))
            .build().createClient(UserClient.class);
}
```

> 💡 **迁移要点**：注解从 Spring MVC 风格（@GetMapping）换成 @*Exchange 风格；注册从 @FeignClient 扫描换成显式 @Bean factory；方法签名基本不变。

---

## 9. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #I1 | 版本不够 | 找不到 @HttpExchange | Spring Framework 6.1+ / Boot 3.2+ |
| #I2 | 忘记配置 baseUrl | 相对路径无法解析 | factory 前在 RestClient 配 baseUrl |
| #I3 | 泛型返回直接写 List | 反序列化类型擦除 | 用 ParameterizedTypeReference |
| #I4 | 与服务端契约不一致 | 调用 404/序列化错 | 接口可被 @Controller 实现，契约统一 |
| #I5 | 负载均衡/熔断没配 | 直连单实例/无降级 | Boot 4 集成 LoadBalancer，熔断配 CircuitBreaker |
| #I6 | 从 Feign 迁移只换注解 | @PathVariable 名不匹配 | Feign 的 name 属性写法与 @GetExchange 模板对齐 |

## 小结

- HTTP Service Clients = Spring 官方推荐声明式 HTTP 客户端（Framework 6.1+）
- @HttpExchange 系列注解定义接口，HttpServiceProxyFactory 生成代理
- 底层三选一：RestClient（推荐）/ WebClient / RestTemplate
- 与 OpenFeign 对比：无第三方依赖、官方维护、服务端契约可复用
- **选型建议**：新项目 HTTP 调用优先 HTTP Interface；存量 OpenFeign 可平滑迁移

## 下一篇

[00-RPC与远程调用总览](00-RPC与远程调用总览.md)——回到总览回顾整个服务通信体系

## 参考资料

- [Spring Framework: REST Clients（官方）](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html)，查询日期：2026-08-09
- [Spring Framework: HTTP Interface 注解](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html#rest-http-service-client)，查询日期：2026-08-09
- [Spring Cloud OpenFeign 官方（feature-complete 公告与迁移建议）](https://docs.spring.io/spring-cloud-openfeign/reference/)，查询日期：2026-08-09
