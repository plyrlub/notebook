---
tags: [Java, 安全框架, SpringSecurity, Shiro, 选型, 索引, 学习笔记]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/安全）
归属: 01-学习/Java/框架/安全
---

# 安全框架选型总览·Spring Security & Apache Shiro

> 本文是「Java 安全框架」学习笔记的**总览与选型入口**。
> 围绕两个主流 Java 安全框架（Spring Security 与 Apache Shiro）展开，给出完整知识域地图、系列篇目索引、总体选型建议。
> 关联笔记：[01-Spring Security核心架构详解](01-Spring Security核心架构详解.md)、[04-Apache Shiro核心架构详解](04-Apache Shiro核心架构详解.md)

## 📋 总纲

1. 为什么需要安全框架
2. 两大框架一句话定位
3. 知识域地图与系列篇目索引
4. 核心概念对比总览（认证/授权/会话/加密）
5. 选型决策：什么场景用哪个
6. 版本现状（2026-08）
7. 面试追问 Q&A
8. 参考

---

## 1. 为什么需要安全框架

**触发点**：任何对外暴露的 Java 应用（Web/服务/管理后台）都要回答四个安全问题——**你是谁、你能做什么、你的会话可信吗、数据是否被篡改**。

| 安全能力 | 解决的问题 | 典型手段 |
|---|---|---|
| **认证 Authentication** | 你是谁 | 用户名密码、OAuth2、JWT、指纹 |
| **授权 Authorization** | 你能做什么 | RBAC 角色、URL 权限、方法级权限 |
| **会话管理 Session** | 连接是否持续可信 | Session/Cookie/Token、rememberMe |
| **加密 Cryptography** | 数据是否泄密/篡改 | BCrypt/Argon2 哈希、AES、数字签名 |

> 💡 **一句话记忆**：认证是"进门验身份"，授权是"房内权限"，会话是"保持进门状态"，加密是"内容防偷防改"。四个能力安全框架**帮你标准化实现**，而不是从零手写。

**为什么不用手写**：
- 手写认证= 重复造轮子，且容易踩安全坑（密码明文存储、会话固定攻击、CSRF 缺失）
- 安全框架提供**经过社区验证的防护**（CSRF、XSS、点击劫持、会话固定防护），开箱即用
- 与生态集成（Spring 系、Spring Boot starter、注解驱动）

---

## 2. 两大框架一句话定位

| 框架 | 一句话定位 | 隶属 |
|---|---|---|
| **Spring Security** | 事实上的 Java 企业级安全标准，深度绑定 Spring 生态，安全能力**全面且灵活** | Spring（Pivotal/Broadcom） |
| **Apache Shiro** | "Simple. Java. Security."，**轻量易用**，认证/授权/会话/加密四合一，可独立于 Spring 使用 | Apache 基金会 |

> 💡 **记忆锚点**：Spring Security = **全家桶里的安全模块**（跟 Spring Boot 天然一体）；Shiro = **小而美的独立工具**（不依赖 Spring 也能用，适合非 Spring 或要更轻量的场景）。

---

## 3. 知识域地图与系列篇目索引

安全框架是一个**大主题**，拆成 7 篇笔记，每篇聚焦一个子域：

| 篇目 | 章节 | 说明 |
|---|---|---|
| 00 | 本页（总览） | 学习路线、章节索引、总体选型 |
| 01 | [01-Spring Security核心架构详解](01-Spring Security核心架构详解.md) | SecurityFilterChain、Filter 链、Lambda DSL、架构演进 |
| 02 | [02-Spring Security认证机制详解](02-Spring Security认证机制详解.md) | AuthenticationManager、UserDetailsService、PasswordEncoder、JWT |
| 03 | [03-Spring Security授权与安全防护详解](03-Spring Security授权与安全防护详解.md) | 方法级授权、URL 授权、CSRF/XSS/会话固定防护 |
| 04 | [04-Apache Shiro核心架构详解](04-Apache Shiro核心架构详解.md) | Subject/SecurityManager/Realm 三核心、认证授权流程 |
| 05 | [05-Apache Shiro认证与授权详解](05-Apache Shiro认证与授权详解.md) | Realm 实现、认证授权 API、注解驱动、加密 |
| 06 | [06-Apache Shiro会话管理与实战详解](06-Apache Shiro会话管理与实战详解.md) | SessionManager、rememberMe、Spring Boot 整合 |
| 07 | [07-Spring Security与Shiro对比选型详解](07-Spring Security与Shiro对比选型详解.md) | 全维度对比表 + 选型决策树 |
| 08 | [08-密码学库实战详解](08-密码学库实战详解.md) | JCA/JCE、Bouncy Castle、jjwt、jBCrypt（密码库用法） |

**学习路线建议**：
1. 先读本页（选型认知）+ 01/04（两个框架的**核心架构**，建立"它们怎么工作"的模型）
2. 再读 02/03（Spring Security 认证授权实战）和 05/06（Shiro 认证授权与会话实战）
3. 最后读 07（深度对比选型），回头确认选型决策

---

## 4. 核心概念对比总览

| 维度 | Spring Security | Apache Shiro |
|---|---|---|
| **当前主体** | Spring 生态（深度集成） | 独立框架（可配 Spring） |
| **认证核心** | AuthenticationManager + AuthenticationProvider | Subject.login() + Realm |
| **核心对象** | SecurityContext / Authentication | Subject / SecurityManager |
| **授权模型** | RBAC，URL + 方法级（注解） | RBAC，URL 过滤器 + 注解 |
| **会话** | 基于 Servlet Session / Token | 自有 SessionManager（不依赖 Servlet） |
| **密码加密** | DelegatingPasswordEncoder（BCrypt 默认） | 自带 Hash 工具（SHA/Bcrypt 等） |
| **生态扩展** | OAuth2/OIDC/SAML/LDAP 等极全 | 较弱，靠第三方 |
| **上手难度** | 陡峭（概念多、配置复杂） | 平缓（API 简单直观） |
| **Spring Boot 集成** | 原生 starter，自动配置 | 官方 shiro-spring-boot-web-starter |

> 🔍 **关键差异**：**Shiro 的核心优势是"易用 + 不依赖容器"**（SessionManager 甚至可脱离 Web 容器做单机应用会话）；**Spring Security 的核心优势是"生态全 + 安全防护完备 + 跟 Spring 一体"**。两者都能完成认证/授权，选型看**生态契合度**与**团队熟悉度**。

---

## 5. 选型决策：什么场景用哪个

| 场景 | 推荐 | 理由 |
|---|---|---|
| **Spring Boot/Spring Cloud 项目** | **Spring Security** | 原生 starter、自动配置、OAuth2/OIDC 生态、与 Spring 无缝 |
| **需要 OAuth2/OIDC/SAML/SSO** | **Spring Security** | 官方第一方支持，功能最全 |
| **需要最完善的安全防护**（CSRF/XSS/安全头） | **Spring Security** | 安全能力最全面 |
| **非 Spring 项目 / 轻量小应用** | **Apache Shiro** | 不依赖 Spring、轻量、上手快 |
| **需要脱离 Web 容器做会话**（如桌面/服务端 session） | **Apache Shiro** | 自有 SessionManager 不依赖 Servlet |
| **老项目维护 / 团队已熟练 Shiro** | Apache Shiro | 迁移成本高，稳定即可 |
| **团队是 Java 新手 / 要快速能跑** | Apache Shiro | 概念少、文档友好 |

> ⚠️ **选型提醒**：如果你**已经在用 Spring Boot**，默认选 **Spring Security**——它是 Spring 生态的标准安全方案，Shiro 在 Spring Boot 里是"外来者"，集成虽可行但生态和社区支持远不如原生。除非有强理由（轻量、团队熟悉、非 Spring 环境），否则**新项目 Spring Security 是更优解**。你的情况（Java 后端、Spring 生态）默认推荐 **Spring Security**，Shiro 作为对比/轻量备选理解即可。

---

## 6. 版本现状（2026-08 查证）

| 框架 | 最新版本 | 关键事实 |
|---|---|---|
| **Spring Security** | **7.1.x**（当前稳定） | 7.0.0 于 2025-11-17 GA（Spring Boot 4.x 默认），**硬移除 `.and()` 链式风格**（无运行时回退）、`SimpleGrantedAuthority` 构造参数 `role→authority` 改名、`getAuthority()` 标 JSpecify `@Nullable`；7.1 新增 InetAddressMatcher 等。Spring Boot 3.x 默认集成 6.x。核心架构 SecurityFilterChain（取代旧 WebSecurityConfigurerAdapter） |
| **Apache Shiro** | **3.0.0**（2026-06 发布） | 当前稳定版要求 **Java 17+**，有官方 shiro-spring-boot-web-starter:3.0.0；2.0-alpha~2.2.0 及 3.0.0-alpha-1 的 shiro-jakarta-ee 模块存在 **CVE-2026-48589**，注意版本 |

> ⚠️ **版本提醒**：写笔记时点（2026-08-09）查证。Shiro 3.0.0 较新，**Spring Boot 3.5 与部分 Shiro 版本存在兼容问题**（见 apache/shiro issue #2119）。若在生产，**优先选择生态更活跃、安全更新更及时的 Spring Security**。具体版本兼容性以官方 release notes 为准。

---

## 7. 面试追问 Q&A

### 7.1 为什么 Spring Security 成为事实标准？

因为它深度绑定 Spring 生态（Spring Boot starter 自动配置、@EnableWebSecurity 注解驱动），提供**最全面的安全防护**（认证、授权、OAuth2/OIDC、CSRF/XSS/会话固定防护），且社区活跃、安全更新及时。企业级 Spring 项目几乎默认集成。

### 7.2 Shiro 相比 Spring Security 的核心优势是什么？

**轻量 + 易用 + 不依赖容器**。Shiro 的 API 直观（Subject.login()/logout()），核心概念少（Subject/SecurityManager/Realm 三个），且 SessionManager 可脱离 Web 容器工作，适合非 Spring 或轻量应用。

### 7.3 什么时候不该选 Shiro？

当项目需要 **OAuth2/OIDC/SSO**、需要**最完善的安全防护**、或是 **Spring Boot 大型项目**时，Shiro 的生态和防护能力不足，应选 Spring Security。

### 7.4 OAuth2、JWT、SSO 是什么关系？

**OAuth2 是授权协议**（解决"第三方应用能否访问我的资源"），**JWT 是令牌格式**（解决"token 怎么携带身份信息"），**SSO 是单点登录方案**（一次登录多处可用）。三者互补不互斥：OAuth2 授权码流程常签发 JWT 作为 access token，企业多系统常基于 OAuth2/OIDC 实现 SSO。**OAuth2 管"授权"，JWT 管"凭证载体"，SSO 管"会话共享"**。协议细节见 **02-OAuth2授权码流程详解**（见知识库）、**01-JWT详解**（见知识库）、**03-SSO单点登录详解**（见知识库）。

### 7.5 Session、Token、JWT 三者的核心区别？

**Session**：服务端存储状态，客户端只存 sessionId（可主动失效，但占服务端内存、集群要共享存储）。**Token**：服务端签发、客户端保存，服务端无状态（但不透明，无法看内容）。**JWT**：一种自包含 Token（三段式，含身份信息+签名），服务端验签即可信任（无需查库），但**无法主动失效**。选型：传统 Web 用 Session，前后端分离用 JWT，需要共享/解耦用 OAuth2。详解见 **04-Session与Token机制详解**（见知识库）。

---

## 8. 参考

- Spring Security 官方文档：https://docs.spring.io/spring-security/reference/
- Apache Shiro 官方：https://shiro.apache.org/
- Apache Shiro 3.0.0 发布公告：https://shiro.apache.org/blog/2026/06/apache-shiro-300-released.html
- Spring Security 7 What's New：https://docs.spring.io/spring-security/reference/whats-new.html
- CVE-2026-48589（Shiro jakarta-ee 模块）：https://nvd.nist.gov/vuln/detail/CVE-2026-48589