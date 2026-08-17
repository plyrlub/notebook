---
tags: [Java, SpringBoot, WebFlux, 实践, Flux, SSE, AI, 流式, 网关, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# Spring WebFlux响应式编程实践

> 版本基线：Spring Boot 3.x + WebFlux（Project Reactor 3.x）、Spring AI
> 受众：先读 [13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md)（Mono/Flux/背压/原理），本篇给"能直接抄的项目级代码"——覆盖 AI agent 流式输出（SSE 打字机）、WebClient 透传上游流式、停止控制。本文在 AI 编程（LLM agent）里最常用。
> 前置：[13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md)；已有 WebFlux 工程或可新建。

## 📋 总纲

1. 起步：WebFlux 工程与依赖（替代 starter-web）
2. 响应式 Controller：Mono/Flux 写法
3. WebClient 非阻塞调用与远程 IO ★
4. SSE 流式：Flux + ServerSentEvent 实现"打字机" ★
5. 实战：SSE 对接大模型（Spring AI ChatClient.stream）★
6. 转发上游流式：WebClient 透传 SSE（网关中间层）
7. 停止生成/断连处理（节省 token）★
8. 背压与限流控制
9. 踩坑速查

## 1. 起步：WebFlux 工程与依赖

用 WebFlux **替代** `spring-boot-starter-web`（二者二选一，别同时引，端口冲突/Bean 冲突）：

```xml
<!-- pom.xml：WebFlux（响应式 web） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>

<!-- Spring AI（对接大模型，流式核心，见第 5 节） -->
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-model-openai</artifactId>
</dependency>
```

> 注意：WebFlux 默认跑在 **Netty**（非阻塞）上；`spring-boot-starter-web`（Tomcat）别同引。数据访问若用关系库要 **R2DBC**（响应式驱动），不能用阻塞 JDBC。

## 2. 响应式 Controller：Mono/Flux 写法

```java
import reactor.core.publisher.Mono;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/users")
public class UserController {

    private final ReactiveUserRepository repo;   // 响应式仓库（如 R2DBC / reactive Mongo）

    public UserController(ReactiveUserRepository repo) { this.repo = repo; }

    @GetMapping("/{id}")
    public Mono<User> getUser(@PathVariable Long id) {
        return repo.findById(id);                 // 非阻塞，0 或 1 个
    }

    @GetMapping
    public Flux<User> list() {
        return repo.findAll();                    // 0 到 N，流式
    }

    @GetMapping("/names")
    public Flux<String> names() {
        return repo.findAll().map(User::name);    // 类型转换
    }
}
```

> 关键：返回 `Mono`/`Flux` 而非实体。响应式是**惰性**的——只有 HTTP 框架订阅才真正执行。

## 3. WebClient 非阻塞调用与远程 IO

不再用 `RestTemplate`（阻塞），用 `WebClient`：

```java
import org.springframework.web.reactive.function.client.WebClient;

@Service
public class OrderGateway {
    private final WebClient client;

    public OrderGateway() {
        this.client = WebClient.builder()
                .baseUrl("http://order-service")
                .defaultHeader("X-Trace-Id", "order-trace")
                .build();
    }

    public Mono<Order> getOrder(Long id) {
        return client.get().uri("/orders/{id}", id)
                .retrieve()
                .bodyToMono(Order.class);          // 非阻塞拿单个
    }

    public Flux<Order> listByUser(Long uid) {
        return client.get().uri("/orders?uid={uid}", uid)
                .retrieve()
                .bodyToFlux(Order.class);          // 非阻塞拿列表
    }
}
```

> `WebClient` 建立在响应式 Netty 上，**IO 不占线程**——是 WebFlux 全链路非阻塞的关键一环。远程调用超时要配 `.timeout(...)`，否则慢上游会拖住整个流。

## 4. SSE 流式：Flux + ServerSentEvent 实现"打字机" ★

SSE（Server-Sent Events）是服务端**单向持续推送**到客户端（HTTP 长连接，`text/event-stream`）。AI 应用"打字机效果"就是靠它。

**最简单的流式接口（纯 Flux）**：

```java
@GetMapping(path = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<String> stream() {
    return Flux.just("春", "眠", "不", "觉", "晓")
            .delayElements(Duration.ofMillis(200));  // 模拟逐字/逐 token 出
}
```

浏览器 `.eventSource` / `fetch` 流式读到每个字，实现打字机。

**带事件元数据的版本（推荐，能区分 token/done/error）**：

```java
@GetMapping(path = "/chat/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<String>> chatEvents(String prompt) {
    return aiService.streamReply(prompt)                       // Flux<String> 逐 token
            .map(token -> ServerSentEvent.<String>builder()
                    .data(token)
                    .event("token")                            // 事件名
                    .build())
            .concatWith(Flux.just(ServerSentEvent.<String>builder()
                    .data("[DONE]")
                    .event("done")                             // 结束信号
                    .build()))
            .onErrorResume(e -> Flux.just(ServerSentEvent.<String>builder()
                    .data(e.getMessage())
                    .event("error")                            // 异常信号
                    .build()));
}
```

> **为什么必须发 done/error**：客户端靠事件判断结束。只有 token 没有 done，前端永远以为"还在生成"；异常必须显式事件，否则客户端挂死等。

## 5. 实战：SSE 对接大模型（Spring AI ChatClient.stream）★

AI 编程最核心的场景。Spring AI 的 `ChatClient.stream()` 天然返回 `Flux<String>`，配合 SSE 推送：

```java
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/ai")
public class AiStreamController {

    private final ChatClient chatClient;

    public AiStreamController(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    /** AI 流式对话：逐 token 打字机推送 */
    @GetMapping(path = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> chat(@RequestParam String prompt) {
        return chatClient.prompt(prompt)
                .stream()                    // 关键：stream() 返回 Flux<String>
                .content()                    // 取文本流
                .map(token -> ServerSentEvent.<String>builder()
                        .data(token).event("token").build())
                .concatWith(Flux.just(ServerSentEvent.<String>builder()
                        .data("[DONE]").event("done").build()));
    }
}
```

**要点**：
- `.call()` 是同步等全部；`.stream().content()` 是逐 token 出 → 打字机。
- 这样 OpenAI / 通义千问 / DeepSeek / Ollama 都能统一出流（配置 url/模型改 yml 即可）。
- 前端 `EventSource("/ai/chat?prompt=...")` 监听 `token` / `done` 事件即可渲染。

## 6. 转发上游流式：WebClient 透传 SSE（网关/中间层）★

企业场景常是"本服务调大模型/上游（也是流式），鉴权/审计/脱敏后 SSE 转发给前端"。WebClient 能流式接收再转发：

```java
@GetMapping(path = "/proxy/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<String>> proxyChat(String prompt) {
    return WebClient.create("http://llm-gateway")
            .get().uri("/generate?q={prompt}", prompt)
            .retrieve()
            .bodyToFlux(String.class)               // 上游也是流式 → Flux
            .map(t -> ServerSentEvent.<String>builder()
                    .data(sanitize(t))              // 可在中间层做脱敏/审计
                    .event("token").build())
            .doOnNext(ev -> audit(ev.data()))       // 埋点/审计副作用
            .onErrorResume(e -> Flux.just(
                    ServerSentEvent.<String>builder().data(e.getMessage()).event("error").build()));
}
```

> 这层可加：鉴权（拦截）、脱敏（包过滤敏感词）、审计（doOnNext 记日志）、限流——这就是"AI 网关"的雏形。

## 7. 停止生成 / 断连处理（★ 省 token 的关键）★

流式生成烧 token，用户点"停止"或关页面，后端必须**取消订阅停止生成**。

**用 Sinks + takeUntilOther 实现停止按钮**：

```java
import reactor.core.publisher.Sinks;
import reactor.core.publisher.SignalType;

@RestController
@RequestMapping("/ai")
public class AiController {
    private final Map<String, Sinks.One<Boolean>> cancelFlags = new ConcurrentHashMap<>();

    /** AI 流式：可被 /stop 取消 */
    @GetMapping(path = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> chat(@RequestParam String prompt,
                                              @RequestParam String sessionId) {
        Sinks.One<Boolean> cancel = Sinks.one();
        cancelFlags.put(sessionId, cancel);                  // 记录本次会话的取消信号

        return chatClient.prompt(prompt).stream().content()
                .takeUntilOther(cancel.asMono())             // 收到取消信号即停
                .map(t -> ServerSentEvent.<String>builder().data(t).event("token").build())
                .concatWith(Flux.just(ServerSentEvent.<String>builder()
                        .data("[DONE-OR-CANCEL]").event("done").build()))
                .doFinally(sig -> cancelFlags.remove(sessionId));  // 结束清理
    }

    @PostMapping("/stop")   // 前端点"停止"调用
    public void stop(@RequestParam String sessionId) {
        Sinks.One<Boolean> c = cancelFlags.get(sessionId);
        if (c != null) c.tryEmitValue(true);                 // 触发取消
    }
}
```

**断连处理**：也可用 Reactor 的 `doOnCancel` 检测客户端断开，立即停流（防 token 浪费）：

```java
Flux<String> stream = chatClient.prompt(prompt).stream().content()
        .doOnCancel(() -> log.info("客户端断开，停止生成为：{}", sessionId));
```

> 要点：`takeUntilOther` 优雅停；`doFinally` 清理会话状态防内存泄漏（并发 map 要 remove）。断连/停止不做，token 费用会白白烧掉——这是 AI 生产必踩的坑。

## 8. 背压与限流控制

流式生成太快、客户端处理不过来时，防积压/OOM：

```java
// 客户端消费慢：buffered + 上游限量拉取
chatClient.prompt(prompt).stream().content()
        .onBackpressureBuffer(500)          // 缓冲最多 500
        .limitRate(50)                       // 每次只请求 50 个
        .concatWith(...)
```

多客户端并发时可全局限流（Semaphore）：

```java
private final Semaphore semaphore = new Semaphore(20);   // 同一时刻最多 20 个流式会话

public Flux<ServerSentEvent<String>> chat(String prompt) {
    return Flux.defer(() -> Flux.just(null))
            .concatMap(ignored -> {
                if (!semaphore.tryAcquire()) {
                    return Flux.error(new RuntimeException("并发流式会话已满，稍后再试"));
                }
                return doStream(prompt)
                        .doFinally(sig -> semaphore.release());
            });
}
```

> 并发风口：每路 SSE 长连接占资源，且大模型流式耗 token，**务必限流 + 设超时**。

## 9. 踩坑速查

- **web 与 webflux 同引**：Tomcat + Netty 端口/Bean 冲突，二选一。
- **忘 subscribe / 不返回 Mono/Flux**：响应式惰性，框架订阅才执行。
- **WebFlux 里混阻塞 JDBC / Thread.sleep**：阻塞 Netty 事件循环线程，性能崩。用 R2DBC 或转异步。
- **流没有 done/error 事件**：前端永远等不到结束 → 挂死。
- **断连/停止不处理**：token 浪费、内存泄漏（Sinks map 不清）。
- **flatMap 乱序**：需要顺序用 concatMap。
- **没配 timeout**：上游慢拖死流。
- **背压没处理**：客户端慢积压 OOM。
- **响应式不贯穿**：Controller 响应式、Service 里阻塞 IO，白搭。

## 10. 小结

- WebFlux 依赖 `starter-webflux`（替代 web），返回 Mono/Flux，走 Netty。
- 远程 IO 用 WebClient（非阻塞），全链路响应式才有效果。
- AI 打字机 = `ChatClient.stream()` 返回 Flux + SSE（`text/event-stream`）推送，事件区分 token/done/error。
- 网关透传用 WebClient `bodyToFlux` 再转发，中间层可做鉴权/脱敏/审计。
- 停止/断连必须处理（takeUntilOther / doOnCancel）防烧 token；并发会话要限流。
- 这是 AI 编程里最常用的一套，务必吃透。

## 11. 关联笔记

- 理论篇：[13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md)
- [03-SpringBoot配置体系与外部化配置实践](03-SpringBoot配置体系与外部化配置实践.md)：Spring AI 模型配置中心化
- [12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md)：流式接口指标监控
- spring 域 [03-SpringMVC执行流程详解](../spring/03-SpringMVC执行流程详解.md)：对比的阻塞模型
- AI 域：LLM-AI（agent 流式输出）

## 12. 参考资料

- [Spring AI 官方：Streaming Chat](https://docs.spring.io/spring-ai/reference/api/chatclient.html)，查询日期 2026-08-15
- [Spring 中 SSE 实践指南（Baeldung 中文）](https://www.baeldung-cn.com/spring-server-sent-events)，查询日期 2026-08-15
- [Spring AI 流式输出深度实战：SSE + 停止按钮 + JSON 事件（掘金）](https://juejin.cn/post/7638889908924678185)，查询日期 2026-08-15
