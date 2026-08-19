---
tags: [Java, 微服务, Spring Cloud Gateway, Actuator, 运维, 调试, 学习笔记]
创建日期: 2026-08-20
状态: ✅ 已归档（01-学习/Java/微服务/网关）
归属: 01-学习/Java/微服务/网关
上一篇: 05-内置GlobalFilter深度
下一篇: 07-动态路由与高可用
---

# Actuator 端点实操：运行时观察网关

> 承接 [01-Spring Cloud Gateway详解](01-Spring Cloud Gateway详解.md)。运用于应用运行时通过 `/actuator/gateway/*` 观察路由/全局过滤器/断言的实际状态，是理解「由配置到运行时」的利器，也是编写与排障网关的好帮手。

---
## 1. Actuator 端点实操：运行时观察网关（调试 / 后期友好）

> Spring Cloud Gateway 通过 Spring Boot Actuator 暴露一组 `/actuator/gateway/*` 端点，可在应用**运行时**反复 `GET` 各接口，观察路由、过滤器、断言、predicates 的实际状态与字段——编写 / 排障时无需杀进程改配置，直接问网关「现在生效的路由有哪些 / GlobalFilter 谁在 / order 是什么」，是理解本文前面「由配置到运行时」极友好的利器。

### 1.1 开启步骤（默认关闭）

`/gateway` 端点在 Spring Boot 中**默认禁用**，需两步开启：设置访问级别 + 通过 HTTP 暴露。

```properties
# application.properties
management.endpoint.gateway.access=read-only
management.endpoints.web.exposure.include=gateway
```

```yaml
# 等价 yaml 写法
management:
  endpoint:
    gateway:
      access: read-only
  endpoints:
    web:
      exposure:
        include: gateway
```

- `access=read-only`：**只读推荐**，禁用增 / 删 / 刷新路由；如需通过端点改路由，设 `unrestricted`（此时务必做权限控制，避免生产被改）。
- `exposure.include=gateway`：把 `gateway` 端点暴露到 HTTP。
- 依赖：`spring-boot-starter-actuator`（Metrics 过滤器等也依赖它，见 [05-内置GlobalFilter深度](05-内置GlobalFilter深度.md) §1.3.6）。

开启后访问根端点可列出全部子端点及方法：

```json
[
  {"href": "/actuator/gateway/", "methods": ["GET"]},
  {"href": "/actuator/gateway/routedefinitions", "methods": ["GET"]},
  {"href": "/actuator/gateway/globalfilters", "methods": ["GET"]},
  {"href": "/actuator/gateway/routefilters", "methods": ["GET"]},
  {"href": "/actuator/gateway/routes", "methods": ["POST", "GET"]},
  {"href": "/actuator/gateway/routepredicates", "methods": ["GET"]},
  {"href": "/actuator/gateway/refresh", "methods": ["POST"]},
  {"href": "/actuator/gateway/routes/{route-id}/combinedfilters", "methods": ["GET"]},
  {"href": "/actuator/gateway/routes/{route-id}", "methods": ["POST", "DELETE", "GET"]}
]
```

### 1.2 核心端点逐个实操

#### 1.2.1 `/actuator/gateway/globalfilters` — 查看全部全局过滤器及其 order

返回「全局过滤器字符串表示 → order」的 JSON。**这是[05-内置GlobalFilter深度](05-内置GlobalFilter深度.md) 内置 GlobalFilter 的运行时实据**。

```bash
curl -s http://localhost:8080/actuator/gateway/globalfilters | jq
```

```json
{
  "org.springframework.cloud.gateway.filter.ReactiveLoadBalancerClientFilter@77856cc5": 10100,
  "org.springframework.cloud.gateway.filter.RouteToRequestUrlFilter@4f6fd101": 10000,
  "org.springframework.cloud.gateway.filter.NettyWriteResponseFilter@32d22650": -1,
  "org.springframework.cloud.gateway.filter.ForwardRoutingFilter@106459d9": 2147483647,
  "org.springframework.cloud.gateway.filter.NettyRoutingFilter@1fbd5e0": 2147483647,
  "org.springframework.cloud.gateway.filter.ForwardPathFilter@33a71d23": 0,
  "org.springframework.cloud.gateway.filter.AdaptCachedBodyGlobalFilter@135064ea": 2147483637,
  "org.springframework.cloud.gateway.filter.WebsocketRoutingFilter@23c05889": 2147483646
}
```

- 每个键 = 过滤器的**类全名 + @实例hash**，值 = 该过滤器在链中的 **order**。
- 作用：核对当前实际注册了哪些全局过滤器、各自顺序，验证你对 filter 链顺序的理解与配置是否生效。

#### 1.2.2 `/actuator/gateway/routefilters` — 查看已应用的 GatewayFilter 工厂

```bash
curl -s http://localhost:8080/actuator/gateway/routefilters | jq
```

```json
{
  "[AddRequestHeaderGatewayFilterFactory@570ed9c configClass = AbstractNameValueGatewayFilterFactory.NameValueConfig]": null,
  "[SecureHeadersGatewayFilterFactory@fceab5d configClass = Object]": null,
  "[SaveSessionGatewayFilterFactory@4449b273 configClass = Object]": null
}
```

- 返回各 `GatewayFilterFactory` 的字符串表示（含 `configClass`），值为 `null`（该端点对工厂对象不设置 order，属已知简化实现）。
- 作用：查看哪些过滤器工厂被应用到路由链上。

#### 1.2.3 `/actuator/gateway/routes` — 查看所有生效路由（verbose 格式，默认开启）

```bash
curl -s http://localhost:8080/actuator/gateway/routes | jq
```

```json
[
  {
    "predicate": "(Hosts: [**.addrequestheader.org] && Paths: [/headers], match trailing slash: true)",
    "route_id": "add_request_header_test",
    "filters": [
      "[[AddResponseHeader X-Response-Default-Foo = 'Default-Bar'], order = 1]",
      "[[AddRequestHeader X-Request-Foo = 'Bar'], order = 1]",
      "[[PrefixPath prefix = '/httpbin'], order = 2]"
    ],
    "uri": "lb://testservice",
    "order": 0
  }
]
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `route_id` | String | 路由 id |
| `predicate` | String | 人类可读的路由断言描述（verbose 格式） |
| `filters` | Array | 路由挂载的过滤器（含 order） |
| `uri` | String | 目标地址 |
| `order` | Number | 路由优先级 |

- verbose 格式默认开，`.predicate`/`.filters` 是人类可读文本；设 `spring.cloud.gateway.server.webflux.actuator.verbose.enabled=false` 会退回原始 Java 类字符串。

#### 1.2.4 `/actuator/gateway/routes/{id}` — 查看单条路由

```bash
curl -s http://localhost:8080/actuator/gateway/routes/first_route | jq
```

```json
{
  "route_id": "first_route",
  "predicate": "(Paths: [/first], match trailing slash: true)",
  "filters": [],
  "uri": "https://www.uri-destination.org",
  "order": 0
}
```

- 单条路由返回的 `predicate` 为单个人类可读字符串；与 `POST` 建路由用的 Shortcut DSL 格式不同（见下）。

#### 1.2.5 `/actuator/gateway/refresh` — 刷新路由缓存

```bash
curl -X POST http://localhost:8080/actuator/gateway/refresh
# 返回 200，无 body
```

- 清空路由缓存，使新 / 改 / 删的路由生效，**无需重启**。
- 可按 metadata 选择刷新：`POST /actuator/gateway/refresh?metadata=group:group-1` 只刷新 `metadata.group=group-1` 的路由。
- 需 `access=unrestricted` 才能调用。

#### 1.2.6 `routes/{id}` 的 POST / DELETE — 运行时动态增删路由（需 unrestricted）

仅**通过端点创建**的路由可被删 / 改；**配置文件 / @Bean 定义的路由对 Actuator 只读**，删它返回 `404 Not Found`。

```bash
# 创建（predicates/filters 用 Shortcut DSL 字符串）
curl -X POST http://localhost:8080/actuator/gateway/routes/my_route \
  -H "Content-Type: application/json" \
  -d '{"predicates":["Path=/mypath/**","Weight=mygroup,20"],"filters":["StripPrefix=1"],"uri":"http://backend-service:8080","order":0}'
# 成功返回 201 Created，之后调 refresh 生效

# 删除
curl -X DELETE http://localhost:8080/actuator/gateway/routes/my_route
# 返回 200 OK，之后调 refresh 生效
```

- **改路由必须「先 DELETE 再 POST」**：不要直接对已存在 id POST（会内部重复，导致后续 `GET /routes` 返回 500）。
- 更新流程：`DELETE /routes/{id}` → `POST /routes/{id}` → `POST /refresh`。

### 1.3 常用 Debug 技巧与 postman / IDE 建议

- **观察过滤器执行顺序**：靠 `globalfilters`（全局）与 `routes/{id}/combinedfilters`（单路由合并链）对照[05-内置GlobalFilter深度](05-内置GlobalFilter深度.md) 的 order 排序规则逐一核对。
- **观察路由命中**：`routes` 的 verbose `predicate` 直接展示已 compiled 后的断言条件，可判断自己写的 Path/Host 是否被正确解析。
- **配合断点**：在自定义 GlobalFilter 的 `filter()` 打断点，经 `exchange` 的 attributes 查看 `GATEWAY_REQUEST_URL_ATTR` / `GATEWAY_ROUTE_ATTR` 等在链逐步传递的值。
- **HTTP 工具**：Postman / IDEA HTTP Client / curl 均可，`jq` 格式化 JSON 便于观览；生产务必给 Actuator 加鉴权。

---
