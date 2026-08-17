---
tags: [Java, SpringBoot, WebFlux, 响应式, Reactor, Mono, Flux, 背压, SSE, AI, 框架]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# Spring WebFlux响应式编程详解

> 版本基线：Project Reactor 3.x、Spring WebFlux 5.x/6.x
> 受众：Java 后端开发，尤其做 AI agent / 高并发 IO 场景。响应式编程是 WebFlux/Reactor 的基础，AI agent 流式输出（SSE）依赖此思想。本篇讲清响应式原理、Mono/Flux、背压、操作符与 WebFlux 应用。
> 前置知识：[07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)（异步基础）、Java 8 函数式（lambda/Stream）、[01-Java线程池原理与参数详解](../../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)
> 关联笔记：[11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)（响应式指标）、[03-SpringMVC执行流程详解](../spring/03-SpringMVC执行流程详解.md)（对比 MVC）

## 📋 总纲

1. 响应式编程是什么：非阻塞 + 异步 + 数据流
2. 阻塞 vs 非阻塞（为什么 AI agent/高并发需要）
3. 两大类型：Mono（0/1）与 Flux（0-N）★
4. 背压 Backpressure：生产快消费慢怎么控
5. 核心操作符：map / flatMap / concatMap 等
6. Spring WebFlux 应用：响应式 Web
7. SSE 流式输出与 AI agent 结合 ★
8. WebFlux vs Web MVC 选型
9. 常见坑

## 1. 学习目标

1. 说清响应式编程"非阻塞 + 异步 + 数据流"三要素
2. 区分 Mono 与 Flux
3. 理解背压及背压策略
4. 用 map/flatMap 组装响应式链路
5. 用 WebFlux + SSE 实现流式输出（AI agent 关键）
6. 判断 WebFlux vs MVC 选型

## 2. 前置知识

- [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)：异步执行
- Java lambda/Stream、CompletableFuture、[01-Java线程池原理与参数详解](../../JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)
- [03-SpringMVC执行流程详解](../spring/03-SpringMVC执行流程详解.md)：对比的阻塞模型

## 3. 核心知识点

### 3.1 响应式编程是什么

响应式编程 = **非阻塞 + 异步 + 数据流**：数据以**流（Stream）**的形式随时间推送给订阅者，订阅者用声明式操作符（map/filter）处理，无需阻塞等待。

```
传统: 数据一次给完，处理一个等一个
响应式: 数据流式推送，订阅者随到随处理，可背压
```

**类比**：传统是"去饭店点菜，等整桌菜做好端上来再吃"；响应式是"流水线自助餐，盘子里有就吃，可跟厨房说慢点上"（背压）。

### 3.2 阻塞 vs 非阻塞（为什么需要）

| 维度 | 阻塞（MVC） | 非阻塞（WebFlux） |
| --- | --- | --- |
| 线程 | 一请求一线程，线程阻塞等 IO | 少量线程处理大量请求，IO 不阻塞 |
| 高并发 | 线程耗尽崩（线程数有限） | 少量线程扛高并发 |
| IO 密集 | 线程利用率低 | 高（IO 等待时线程可处理别的） |
| 心智 | 直观 | 陡峭（需要响应式思维） |

**为什么 AI agent 需要**：AI 流式输出是**长时间、多 token、逐步返回**的 IO——MVC 阻塞模型会长期占线程；WebFlux 非阻塞 + SSE 流式推送正合适（见 3.7）。

### 3.3 Mono 与 Flux ★

| 类型 | 元素数 | 类比 | 典型 |
| --- | --- | --- | --- |
| Mono | 0 或 1 | 单个异步结果 | 查单个记录、HTTP 单响应 |
| Flux | 0 到 N | 异步序列 | 列表、流式输出 token 流 |

```java
Mono<String> mono = Mono.just("hello");
Mono<Void> empty = Mono.empty();
Flux<Integer> flux = Flux.just(1, 2, 3);
Flux<Integer> fromIterable = Flux.fromIterable(list);
Flux<Long> interval = Flux.interval(Duration.ofSeconds(1));   // 每秒一个
```

**惰性**：响应式序列是**惰性**的——不订阅（subscribe）不执行。构造只是定义，`subscribe()` 才触发。

### 3.4 背压 Backpressure ★

**问题**：生产快、消费慢时，不控制会导致消费者积压/OOM。

**背压**：消费者告诉生产者"我能处理多少"，生产者按需发送。Reactor 通过 `request(n)` 控制上游元素量。

```java
Flux.range(1, 1000)
    .limitRate(100)                    // 每次只请求 100 个
    .map(expensive::process)
    .subscribe();
```

**背压策略**：`onBackpressureBuffer`（缓冲）、`onBackpressureDrop`（丢弃）、`onBackpressureLatest`（留最新）、`onBackpressureError`（报错）。

> **AI agent 关联**：流式生成 token 时，客户端处理慢要用背压（限流/缓冲），避免服务端一股脑推爆客户端（见 3.7）。

### 3.5 核心操作符

| 操作符 | 作用 | 类比 |
| --- | --- | --- |
| map | 1→1 转换 | Stream.map |
| flatMap | 1→N 或异步拼接（无序） | 每个元素变流，扁平化 |
| concatMap | 1→N，保序 | 顺序拼接 |
| filter | 过滤 | Stream.filter |
| zip | 合并多个流 | 多数据源合并 |
| doOnNext | 副作用（打日志） | peek |
| timeout / retry / repeat | 超时/重试/重复 | 健壮性 |

```java
Flux.just("a", "b", "c")
    .map(String::toUpperCase)                     // A B C
    .flatMap(this::asyncFetchDetail)              // 每个变异步流，扁平化
    .filter(detail -> detail.isValid())
    .subscribe(detail -> log.info("{}", detail));
```

> **map vs flatMap**：map 是同步 1→1 同步转换；flatMap 返回新的 Publisher（异步/1→N），是响应式里最常用的异步拼接管。concatMap 保证顺序，flatMap 无序但更并发。

### 3.6 Spring WebFlux 应用

```java
// 响应式 Controller：返回 Mono/Flux
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public Mono<User> getUser(@PathVariable Long id) {
        return userRepository.findById(id);   // 响应式仓库，非阻塞
    }

    @GetMapping("/users")
    public Flux<User> listUsers() {
        return userRepository.findAll();
    }
}
```

- 依赖：`spring-boot-starter-webflux`（替代 starter-web）
- 数据层：需响应式驱动（R2DBC 数据库 / reactive Mongo / WebClient 调远程）
- 客户端：`WebClient`（非阻塞 HTTP 客户端，替代 RestTemplate）

```java
// WebClient 非阻塞调用
WebClient client = WebClient.builder().baseUrl("http://api.example.com").build();
Mono<User> user = client.get().uri("/users/{id}", 1)
    .retrieve().bodyToMono(User.class);
```

### 3.7 SSE 流式输出与 AI agent 结合 ★

**SSE（Server-Sent Events）**：服务端单向推送流式数据到客户端（HTTP 长连接，`text/event-stream`）。AI agent 流式 token 输出正是此模式。

**WebFlux + Flux 天然支持流式**（做 AI agent 的核心）：

```java
@GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<String>> chatStream(String prompt) {
    return aiClient.stream(prompt)                    // Flux<String>：模型逐 token 流
        .map(token -> ServerSentEvent.<String>builder()
            .data(token)
            .event("token")                           // 事件类型
            .build());
}
```

**要点**（来自生产实践，AI agent 流式的 4 大坑）：
- **流不能静默吞掉**：异常/结束必须发明确事件（done/error），客户端据此停止
- **连接断开处理**：用户关页签，服务端要检测并停止生成（省 token）
- **背压/限流**：客户端处理不过来用背压控制，防积压
- **重连与幂等**：断线重连时 SSE Last-Event-ID 续传；任务不丢

> 前端 EventSource 或 fetch 流式读 `text/event-stream`；服务端 Flux 每 emit 一个 token 客户端即收到——这就是流式 AI 输出的基础。

### 3.8 WebFlux vs Web MVC 选型

| 维度 | Web MVC | WebFlux |
| --- | --- | --- |
| 模型 | 阻塞（一请求一线程） | 非阻塞（事件驱动） |
| 高并发 | 线程数瓶颈 | 少量线程扛大量连接 |
| 流式/SSE | 需异步 servlet 配合 | 原生支持（Flux） |
| 数据库 | JDBC（阻塞） | R2DBC/响应式驱动 |
| 心智 | 直观 | 陡峭 |
| 适用 | 常规业务/团队熟悉 | 高并发 IO / 流式 / 网关 / AI |

**结论**：做 AI agent 流式输出、高并发 IO、网关 → WebFlux 优势明显；常规 CRUD/团队不熟响应式 → MVC 更稳。可混合（部分接口响应式）。

### 3.9 常见坑

- **Mono/Flux 忘 subscribe** → 不执行（惰性）
- **WebFlux 里用了阻塞 JDBC/Thread.sleep** → 阻塞事件循环线程，性能崩
- **flatMap 乱序** → 需要顺序用 concatMap
- **背压没处理** → 消费慢积压 OOM
- **响应式贯穿不彻底** → Controller 响应式但 Service 里阻塞 IO，白搭

## 4. 最佳实践

- 响应式必须贯穿全链路（Controller→Service→数据访问），一处阻塞全白搭
- 用 WebClient 而非 RestTemplate（非阻塞）
- 流式用 SSE + Flux，明确 done/error 事件
- 消费端用背压控制（limitRate/onBackpressure）
- 关注线程池隔离（配合 [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)）

## 5. 常见踩坑

- WebFlux 里混入阻塞代码（JDBC 同步调用）→ 用 R2DBC 或转异步
- 没配 timeout/retry → 远程慢导致流挂死
- AI 流式连接断开不处理 → token 浪费、任务丢失
- 背压策略选错 → 丢弃数据/OOM

## 6. 小结

- 响应式 = 非阻塞 + 异步 + 数据流，Mono（0/1）+ Flux（0-N）。
- 背压让消费慢时控制生产，防积压。
- map 同步 1→1、flatMap 异步拼接。
- WebFlux + SSE 是 AI agent 流式输出的基础。
- 响应式须贯穿全链路，选型看高并发 IO/流式需求。

## 7. 关联笔记

- 上一篇：[12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md)
- [03-SpringMVC执行流程详解](../spring/03-SpringMVC执行流程详解.md)：对比的阻塞模型
- [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)：异步与线程池
- [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)：响应式指标监控
- AI 相关：LLM-AI 域（AI agent 流式输出）

## 8. 参考资料

- [Reactor 官方文档（中文）](https://easywheelsoft.github.io/reactor-core-zh/index.html)，查询日期 2026-08-11
- [Spring 官方：WebFlux](https://spring.io/reactive)，查询日期 2026-08-11
- [Baeldung：Spring MVC Async vs WebFlux](https://www.baeldung-cn.com/spring-mvc-async-vs-webflux)，查询日期 2026-08-11
