---
tags: [分布式, Session, 会话管理, Redis, Token, JWT, 粘性会话, 无状态, SSO]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/分布式）
归属: 01-学习/分布式
---

# 分布式 Session 详解

> 本文是分布式系列第 9 篇，把**分布式会话管理**讲透：Session 的本质、集群化后的四大方案（粘性会话/Session 复制/Session 共享/无状态 Token）、Redis 会话共享实战（Spring Session）、JWT 与 SSO、以及"有状态 vs 无状态"的架构选型。
> **版本基线**：Spring Session 3.x、Spring Boot 3.x、JWT（RFC 7519）| 创建日期：2026-08-10
> **受众**：后端开发熟手（熟悉 Java/Spring/Redis），已懂 HTTP、Cookie、负载均衡，准备架构面试或做登录系统。
> 前置知识：[00-分布式基础总览](../00-分布式基础总览.md)、[06-负载均衡详解](06-负载均衡详解.md)（会话保持）、[03-分布式锁原理详解](03-分布式锁原理详解.md)（登录防重）
> 关联笔记：[04-分布式事务详解](04-分布式事务详解.md)（登录态与事务无直接关系，但多服务一致性思路相通）、[02-CAP与BASE理论详解](02-CAP与BASE理论详解.md)（Session 共享的一致性取舍）

---

## 1. 学习目标

学完本文你应当能够：

- 说清 **Session 的本质**（服务端状态 + 标识），为什么单机 Session 在集群下失效。
- 对比**四大方案**：粘性会话（Sticky）、Session 复制、Session 共享（集中式）、无状态 Token——各有什么优劣。
- 用 **Redis + Spring Session** 实现会话共享，说出 key 结构、过期策略、序列化注意点。
- 讲清 **JWT** 的结构（Header/Payload/Signature）、优缺点、与 Session 的本质区别（有状态 vs 无状态）。
- 理解 **SSO（单点登录）** 与 CAS 的流程，知道分布式登录态的几种形态。
- 做**架构选型**：什么场景用 Session 共享、什么场景用 JWT、什么场景用 OAuth2。

## 2. 前置知识

- [06-负载均衡详解](06-负载均衡详解.md)——集群负载均衡 + 会话保持（sticky）是方案一的基础。
- [02-CAP与BASE理论详解](02-CAP与BASE理论详解.md)——Session 共享的"一致性与可用性"取舍。
- 需掌握：HTTP 无状态、Cookie、登录流程、Spring 基础。

---

## 3. 核心知识点

### 知识点一：Session 的本质——服务端状态 + 标识

**一句话记忆**：**HTTP 是无状态的，Session 就是"服务器为每个用户开的小本本"——小本本放在服务端，客户端只拿一把钥匙（SessionId）**。

#### ① 是什么

| 概念 | 位置 | 内容 |
|---|---|---|
| **Session** | **服务端**内存/存储 | 登录态、购物车、验证码等用户状态数据 |
| **SessionId** | **客户端**（Cookie/URL） | 标识"这个小本本是哪个用户的" |
| **Cookie** | 客户端 | 携带 SessionId 的载体（默认 `JSESSIONID`） |

```
登录流程:
1. 用户提交账号密码
2. 服务端校验通过 → 创建 Session（服务端存用户信息）→ 生成 SessionId
3. 返回 Set-Cookie: JSESSIONID=xxx
4. 后续请求带 Cookie → 服务端凭 SessionId 找到 Session → 识别用户
```

#### ② 为什么集群下会失效（核心问题）

```
单机: 所有请求打到同一台 → Session 就在这台内存里 ✅

集群(3台):
请求1 打到 ServerA → 登录 → Session 存在 A 的内存
请求2 被 LB 分发到 ServerB → B 没有这个 Session → 用户"掉登录" ❌
```

**根因**：Session 是**服务端本地状态**，而请求被负载均衡分发到不同机器 → 状态和请求不在一起。

> 💡 **记忆锚点**：**Session 问题的本质 = "状态在 A 机器，请求到了 B 机器"**。所有解决方案都是让"状态跟着请求走"或"状态集中存放"。

#### ③ 追问

- 面试官："为什么不用 URL 重写带 SessionId？"→ 老式 Servlet 支持，但会泄露会话 ID、污染链接、不利于 CDN 缓存，现代框架默认 Cookie。

---

### 知识点二：方案一——粘性会话（Sticky Session）

**一句话记忆**：**让 LB 把同一个用户的请求永远分到同一台服务器——人还是那个人，就去原来那个窗口办**。

#### ① 是什么

负载均衡器按**用户标识**（IP / Cookie）把请求固定路由到同一台后端：

```
LB 规则: 同 IP / 同 Cookie 值 → 永远分到 ServerA
→ Session 在 A 上创建，后续请求也全去 A → 不会掉登录
```

实现方式：`ip_hash`（Nginx）、`sticky` Cookie 插入、一致性哈希（按用户 key）。

#### ② 优缺点

| 优点 | 缺点 |
|---|---|
| 实现最简单（LB 一个配置） | **单点热点**：该用户的请求全压一台机，无法水平扩展 |
| 不改应用代码 | **机器故障丢 Session**：A 挂了，用户的 Session 没了，仍掉登录 |
| | 机器间负载不均（热点用户聚集） |

> ⚠️ **易错点**：粘性会话是"治标不治本"——它只是**避免** Session 跨机器，Session 仍是本机内存状态，故障/扩容都不行。适合**中小规模、允许重建登录态**的场景。

#### ③ 追问

- 面试官："粘性会话和会话复制能一起用吗？"→ 可以，粘性保证平时走一台，复制保证那台挂了状态还在（但复制有延迟窗口）。

---

### 知识点三：方案二——Session 复制（Replication）

**一句话记忆**：**每台机器都有一份全量 Session 副本，谁拿到请求都能认人——但同步有延迟、内存有浪费**。

#### ① 是什么

Session 创建/变更后，**广播同步到集群所有节点**（Tomcat 集群的 DeltaManager 即此方案）：

```
ServerA 创建 Session → 广播给 B、C → 三台都有
请求到任何一台 → 都能找到 Session ✅
```

#### ② 优缺点

| 优点 | 缺点 |
|---|---|
| 任何机器都能服务，无路由依赖 | **广播风暴**：Session 多、节点多时同步量大 |
| 实现简单（Tomcat 自带） | **内存浪费**：每台存全量副本 |
| | **同步延迟**：广播未完成时可能读到旧/无 Session |
| | 节点多时性能急剧下降（N² 广播） |

> ⚠️ **易错点**：Session 复制适合 **节点少（2~5 台）** 的场景；节点一多广播开销爆炸，**大型集群不用**。

#### ③ 追问

- 面试官："Tomcat 的 Session 复制靠谱吗？"→ 小集群可用；生产大集群基本被"集中式共享"取代，因为广播延迟和内存开销不可控。

---

### 知识点四：方案三——Session 共享（集中式存储）★主流

**一句话记忆**：**把 Session 从"每台机器的内存"搬到"一个大家都连得上的地方"（Redis/DB）——状态集中放，谁都能取**。

#### ① 是什么

```
Session 存 Redis（或 DB/Memcached）
所有后端连同一个 Redis → 任何机器都能按 SessionId 取到 Session ✅
```

- **Redis 首选原因**：内存快、支持过期（TTL 自动清 Session）、数据结构丰富、天然分布式。
- Spring Session + Redis 是最主流实现（Java 生态）。
- Session 数据量小、读多写少、需要过期 → 与 Redis 特性完美契合。

#### ② Spring Session 实战（代码级）

```xml
<!-- Spring Boot 引入 -->
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-data-redis</artifactId>
</dependency>
```

```yaml
spring:
  session:
    timeout: 30m          # Session 过期时间（默认 30 分钟）
  data:
    redis:
      host: redis-master  # 连 Redis（生产用哨兵/集群）
```

```java
@Configuration
public class SessionConfig {
    // 引入依赖后自动配置，无需额外代码:
    // - HttpSession 自动存 Redis（默认 RedisIndexedSessionRepository）
    // - 序列化默认 JDK，可自定义为 JSON（见下）
}
```

**Redis 里的 key 结构**（理解内部机制）：

```
spring:session:sessions:<sessionId>          # Session 数据（hash）
spring:session:expirations:<时间戳>           # 过期索引（用于精确删除）
spring:session:sessions:expires:<sessionId>  # 过期占位
```

**序列化注意**：默认 JDK 序列化（对象需 Serializable、不可读）；生产常配 JSON 序列化（`GenericJackson2JsonRedisSerializer`）便于排查和跨语言。

#### ③ 与 Cookie 的关系

- SessionId 仍存客户端 Cookie（`SESSION`），只是**数据**搬到 Redis。
- 多域名/前后端分离 → SessionId 通过 Header（`X-Auth-Token`）或跨域 Cookie 传递。

#### ④ 优缺点与易错点

| 优点 | 缺点/注意 |
|---|---|
| 无状态后端（水平扩展随便加机器） | **Redis 是单点** → 需 Redis 高可用（主从/哨兵/集群） |
| 故障无感（机器挂了 Session 还在） | **一次 Redis 访问延迟**（可接受，本地缓存优化） |
| 集中管理（过期/统计方便） | 大 value 会话注意 Redis 内存 |

> ⚠️ **易错点**：Session 存 Redis 后，**后端机器本身无状态了**，但"会话数据"仍然是有状态资源——Redis 挂了等于全体掉登录，所以 **Redis 高可用是硬前提**。

#### ⑤ 追问

- 面试官："Session 共享和分布式锁都依赖 Redis，有什么区别？"→ 会话共享是"读改写数据存储"，锁是"原子互斥操作"；锁对原子性要求极高（见 [03-分布式锁原理详解](03-分布式锁原理详解.md)），会话数据允许短暂不一致（写后读有窗口）。

---

### 知识点五：方案四——无状态 Token（JWT）★现代趋势

**一句话记忆**：**不存 Session，把"用户身份"签名后交给客户端保管——服务器不用记任何状态，验签通过就认人**。

#### ① 是什么：JWT 结构

JWT（JSON Web Token）三段式：`Header.Payload.Signature`

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

Header:   {"alg":"HS256","typ":"JWT"}              ← 签名算法
Payload:  {"sub":"1001","name":"robin","exp":...}  ← 用户信息+过期时间
Signature: HMAC(header.payload, 密钥)               ← 防篡改签名
```

```java
// 生成 JWT（jjwt 库示例）
String token = Jwts.builder()
    .subject("1001")
    .claim("name", "robin")
    .expiration(new Date(System.currentTimeMillis() + 30*60*1000))
    .signWith(secretKey)
    .compact();

// 校验（每次请求）
Claims claims = Jwts.parser().verifyWith(secretKey)
    .build().parseSignedClaims(token).getPayload();
```

#### ② 为什么：无状态的好处

| 优点 | 说明 |
|---|---|
| **服务器无状态** | 不存 Session，任意机器验签即可 → 水平扩展零成本 |
| **天然跨域/跨服务** | Token 放 Header，移动端/多服务/微服务网关都认 |
| **防篡改** | 签名保证内容不可伪造（密钥在服务端） |
| **减少存储** | 不需要 Redis 存会话（对比方案三） |

#### ③ 缺点与易错点（面试重点）

| 缺点 | 说明 |
|---|---|
| **无法主动失效** | Token 在过期前一直有效，**踢人下线/改密码后旧 Token 仍可用**（需黑名单/版本号兜底） |
| **泄密即被盗** | 密钥泄露 = 所有 Token 可伪造；Token 被偷无法撤销 |
| **载荷膨胀** | 用户信息塞太多 → 每次请求携带变大 |
| **无服务端状态** | 拿不到"服务端视角的登录设备列表/踢人"等能力 |

> ⚠️ **易错点**：JWT 的"无状态"是把状态**转移**给客户端，不是没有状态——**退出登录、强制下线这类"状态变更"JWT 天生做不了**，需要黑名单（Redis 记 revoked token）或短期 token + 刷新机制。

#### ④ 追问

- 面试官："JWT 和 Session 怎么选？"→ ① 需要踢人/管理会话 → Session 共享；② 纯 API/移动端/多端、服务器无状态优先 → JWT；③ 生产常用**混合**：JWT 做短时访问令牌 + Redis 存可撤销的 refresh token（见 SSO/OAuth2）。

---

### 知识点六：SSO（单点登录）与登录态形态

**一句话记忆**：**SSO = 多个系统共用一个登录中心——在 A 登录了，去 B、C 不用再登**。

#### ① 为什么需要 SSO

多系统（订单中心/支付中心/后台管理）各自登录 → 用户要登 N 次。SSO 统一认证中心，一次登录全站通行。

#### ② CAS 经典流程（理解模型）

```
1. 用户访问系统A → 未登录 → 302 跳转 SSO 认证中心
2. 用户在认证中心登录 → 认证中心发 Ticket（一次性票据）给 A
3. A 拿 Ticket 向认证中心验证 → 通过 → 建立 A 的本地会话
4. 用户再访问系统B → 同样 302 到认证中心 → 已有全局登录态 → 直接发 Ticket
   → B 验证后放行 → 用户无感登录 B ✅
```

**要点**：认证中心维护**全局会话**（可存 Redis），各系统维护**本地会话**；Ticket 一次性、短期、需验证。

#### ③ 登录态形态演进（架构面试进阶）

| 形态 | 载体 | 特点 |
|---|---|---|
| 传统 Session | Cookie + 服务端内存 | 单机/小集群 |
| Session 共享 | Cookie + Redis | 集群标配（Spring Session） |
| Token（JWT） | Header + 签名 | 无状态、跨端（移动端首选） |
| **SSO + 统一认证** | 认证中心 + 各系统会话 | 多系统、企业内网 |
| **OAuth2/授权码** | 第三方授权 + 访问令牌 | 开放平台、第三方登录（微信/GitHub） |

**分布式登录态设计建议**：核心内部系统用 **Redis Session 共享**（可踢人、可管理）；开放 API/移动端用 **JWT + refresh token**；多系统统一入口用 **SSO 认证中心**。

#### ④ 追问

- 面试官："SSO 的 Ticket 为什么是一次性的？"→ 防重放攻击：Ticket 用一次就废，即使被抓包也不能重复使用；配合短有效期 + 绑定目标系统。

---

### 知识点七：选型决策与最佳实践

**一句话记忆**：**粘性会话=应急，Session 复制=小集群，Redis 共享=生产标配，JWT=无状态/跨端；SSO/OAuth2 管多系统**。

#### ① 四大方案总对比

| 维度 | 粘性会话 | Session 复制 | Session 共享(Redis) | 无状态(JWT) |
|---|---|---|---|---|
| 后端状态 | 有(本机) | 有(全量副本) | 有(集中存储) | **无** |
| 水平扩展 | ✗ | ✗(节点受限) | ✓ | ✓✓ |
| 故障容忍 | ✗(机器挂=会话丢) | 部分(有延迟窗口) | ✓(Redis HA) | ✓✓(验签即可) |
| 主动失效(踢人) | ✓ | ✓ | ✓ | ✗(需黑名单) |
| 实现成本 | 低(LB 配置) | 低(Tomcat 自带) | 中(Spring Session) | 中(引入 JWT 库) |
| 适用 | 小规模应急 | 2~5 台小集群 | **生产主流** | API/移动端/微服务 |

#### ② 最佳实践清单

- **默认方案**：Java 后端集群 → Spring Session + Redis（生产最稳、可管理）。
- **Redis 高可用是前提**：主从 + 哨兵或 Cluster，别让会话存储成单点。
- **Session 只存必要数据**：用户 ID + 少量信息即可，别塞大对象（购物车等重数据落库）。
- **JWT 场景**：短时效（15~30 分钟）+ refresh token 续期 + 敏感操作校验。
- **Cookie 安全**：`HttpOnly`（防 XSS 读 Cookie）、`Secure`（仅 HTTPS）、`SameSite`（防 CSRF）。
- **登录防重/防爆破**：失败次数用 Redis 计数 + 限流（见 [03-分布式锁原理详解](03-分布式锁原理详解.md) 思路）。
- **Session 与幂等**：登录接口本身要幂等设计（防重复提交），见 [05-分布式ID与幂等设计详解](05-分布式ID与幂等设计详解.md)。

#### ③ 追问

- 面试官："Redis 存 Session，Redis 挂了怎么办？"→ ① Redis 高可用（哨兵/集群）自动切换；② 降级：读本地缓存兜底（短暂容忍踢出）；③ 核心系统双写/多级缓存。**没有银弹，关键是让"会话存储"的可用性级别匹配业务**。

---

## 4. 常见踩坑

- 集群不配会话方案 → 用户随机掉登录（最基础错误）。
- 粘性会话当长期方案 → 热点/单点/无法扩容。
- Session 复制用在大型集群 → 广播风暴。
- Redis 单点存 Session → Redis 挂 = 全体掉登录（必须 HA）。
- JWT 当"万能" → 踢人、改密失效做不到。
- JWT 密钥写死在代码/配置明文 → 泄露即全量可伪造（密钥走配置中心/环境变量）。
- Cookie 不设 HttpOnly/Secure/SameSite → XSS/中间人/CSRF 风险。
- Session 存大对象（购物车全量）→ Redis 内存膨胀、序列化慢。

## 5. 小结

- Session 本质 = **服务端状态 + SessionId 标识**；集群问题 = 状态与请求分离。
- 四方案：**粘性（路由绑定）→ 复制（全量副本）→ 共享（集中存储）→ 无状态（Token 验签）**，一路走向"后端无状态"。
- 生产主流：**Redis Session 共享**（可管理、可踢人、可扩展）；API/移动端：**JWT**。
- SSO 统一登录、OAuth2 管开放授权；Ticket 一次性防重放。
- 选型看三问：要不要踢人？要不要跨端？要不要无状态？

## 6. 关联笔记

- 基础：[06-负载均衡详解](06-负载均衡详解.md)（sticky/会话保持）、[02-CAP与BASE理论详解](02-CAP与BASE理论详解.md)（一致性取舍）。
- 协同：[03-分布式锁原理详解](03-分布式锁原理详解.md)（登录防重/限流）、[05-分布式ID与幂等设计详解](05-分布式ID与幂等设计详解.md)（登录幂等）。
- 扩展：[00-ZooKeeper总览](../Zookeeper/00-ZooKeeper总览.md)（注册中心与服务发现，配合无状态服务）、[01-一致性Hash算法详解](01-一致性Hash算法详解.md)（LB 按用户路由的底层）。

## 7. 参考资料

- Spring Session 官方文档（Redis 集成、序列化）
- JWT 规范：RFC 7519
- CAS 协议文档（SSO 流程）
- JavaGuide：分布式会话专题（面试整理）
- 面试素材：`/Users/lub/Desktop/学习/跟AI学技术/面试笔记/后端工程师面试/分布式系统/`（分布式相关已吸收）
