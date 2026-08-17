---
tags: [Java, SpringBoot, 总览, 自动装配, 配置, 框架, 接口文档, SpringDoc]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot体系总览

> 版本基线：Spring Boot 2.x/3.x（3.x 为当前主线，4.x 见模块化篇）
> 受众：Java 后端开发。假设已懂 Spring 核心与 SpringMVC（见 [00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot](../spring/00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md)）；本域聚焦 SpringBoot 独有的"怎么跑起来、怎么配置、怎么模块化"。
> 关联笔记：spring 域全部篇目（IoC/AOP/事务/SpEL/MVC）、数据访问层 域 [07-Spring Boot集成与配置详解](../数据访问层/07-Spring Boot集成与配置详解.md)

## 📋 总纲

1. SpringBoot 定位：让 Spring 零配置跑起来
2. 核心三大件：starter / 自动装配 / 外部化配置
3. 域知识地图（本目录全部篇目）
4. 学习路线
5. 面试考点索引

## 1. SpringBoot 定位

SpringBoot 不是替代 Spring/SpringMVC，而是**让它们开箱即用的整合器**。四大能力：

| 能力 | 解决什么 | 机制 |
| --- | --- | --- |
| starter 依赖 | 引一个包自动带齐依赖 | 依赖聚合 |
| 自动装配 | 免写 XML/JavaConfig 样板 | @EnableAutoConfiguration + 条件注解 |
| 外部化配置 | 一个 yml 统管所有配置 | Environment + @ConfigurationProperties |
| 内嵌容器 | java -jar 即启动 | 内置 Tomcat/Jetty/Undertow |

一句话：**约定优于配置**——默认值兜底，你只需覆盖差异。

## 2. 核心三大件

1. **Starter**：`spring-boot-starter-web` 等，引一个 = 拉齐所有依赖（含传递依赖），版本由 Boot 统一仲裁。
2. **自动装配**：启动时扫描 `AutoConfiguration.imports` 里的自动配置类，按条件注解（@ConditionalOnClass 等）决定哪些生效——这是 Boot 的灵魂，见 [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)。
3. **外部化配置**：application.yml + 17 级优先级覆盖，@ConfigurationProperties 结构化绑定——见 [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)。

## 3. 域知识地图

| 篇目 | 内容 | 深度 |
| --- | --- | --- |
| [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md) | @SpringBootApplication/自动装配/条件注解/starter | 深（重点） |
| [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md) | 配置优先级/@ConfigurationProperties/profile | 深（重点） |
| [03-SpringBoot配置体系与外部化配置实践](03-SpringBoot配置体系与外部化配置实践.md) | yml/多环境 profile/配置绑定/踩坑 | 实 |
| [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md) | Boot4 一个 jar→一组模块 | 深 |
| [05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md) | 双模块/starter 开发/元数据/测试 | 深 |
| [06-SpringBoot自定义Starter实践](06-SpringBoot自定义Starter实践.md) | 注解+AOP+自动配置类+.imports 完整 Starter | 实 |
| [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md) | @Async/线程池/失效场景 | 深 |
| [08-SpringBoot异步与线程池实践](08-SpringBoot异步与线程池实践.md) | 有界线程池/多池/@Async 失效/OOM 防坑 | 实 |
| [09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md) | logging/Logback/滚动/异步日志 | 深 |
| [10-SpringBoot日志配置实践](10-SpringBoot日志配置实践.md) | logback-spring.xml/滚动/MDC 链路/异步日志 | 实 |
| [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md) | health/metrics/Micrometer/Prometheus | 深 |
| [12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md) | Actuator/Prometheus/Grafana/自定义指标 | 实 |
| [13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md) | Mono/Flux/背压/SSE（AI agent） | 深（重点） |
| [14-Spring WebFlux响应式编程实践](14-Spring WebFlux响应式编程实践.md) | SSE 流式/AI 打字机/WebClient 透传/停止控制 | 实（重点） |
| [16-SpringDoc与OpenAPI集成详解](16-SpringDoc与OpenAPI集成详解.md) | SpringDoc 原理/性能/安全/注解/迁移 | 深（重点） |
| [17-SpringDoc与OpenAPI集成实践](17-SpringDoc与OpenAPI集成实践.md) | Boot3+SpringDoc 可运行示例/分组/JWT | 实 |
| [18-Knife4j增强与网关聚合详解](18-Knife4j增强与网关聚合详解.md) | 增强 UI/网关聚合两模式/生产安全关闭 | 深 |
| [19-协作平台Apifox与Postman详解](19-协作平台Apifox与Postman详解.md) | Apifox/Postman/YApi 对比/Mock/测试/工作流 | 深 |
| [07-Spring核心·AOP详解](../spring/07-Spring核心·AOP详解.md)（自 Java 迁入） | 见 spring 域 [07-Spring核心·AOP详解](../spring/07-Spring核心·AOP详解.md) | — |
| [09-Spring事务管理详解](../spring/09-Spring事务管理详解.md)（自 Java 迁入） | 见 spring 域 [09-Spring事务管理详解](../spring/09-Spring事务管理详解.md) | — |
| [11-SpEL表达式详解](../spring/11-SpEL表达式详解.md)（自 Java 迁入） | 见 spring 域 [11-SpEL表达式详解](../spring/11-SpEL表达式详解.md) | — |

> 注：原 springboot 域的 AOP/事务/SpEL 已按"属 Spring 核心"迁至 spring 域（见 [00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot](../spring/00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md)），本目录仅保留 Boot 专属内容。

**跨域关联**：
- Spring 核心：[00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot](../spring/00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md)
- 数据集成：[07-Spring Boot集成与配置详解](../数据访问层/07-Spring Boot集成与配置详解.md)（MyBatis/JPA 集成）
- 安全：[01-Spring Security核心架构详解](../安全/01-Spring Security核心架构详解.md)（Boot 自动装配 Security）
- 测试：[05-Spring Boot测试与Testcontainers](../../测试/05-Spring Boot测试与Testcontainers.md)

## 4. 学习路线

1. 先读 [00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot](../spring/00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md) 建立全局
2. [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)（核心，理解"怎么跑起来"）
3. [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md) → [03-SpringBoot配置体系与外部化配置实践](03-SpringBoot配置体系与外部化配置实践.md)（怎么配）
4. [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)（Boot4 演进）
5. [05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md) → [06-SpringBoot自定义Starter实践](06-SpringBoot自定义Starter实践.md)（怎么写 starter，进阶）
6. [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md) → [08-SpringBoot异步与线程池实践](08-SpringBoot异步与线程池实践.md)（异步与线程池）
7. [09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md) → [10-SpringBoot日志配置实践](10-SpringBoot日志配置实践.md)（日志）
8. [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md) → [12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md)（生产监控）
9. [13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md) → [14-Spring WebFlux响应式编程实践](14-Spring WebFlux响应式编程实践.md)（响应式/AI agent 流式）
10. [16-SpringDoc与OpenAPI集成详解](16-SpringDoc与OpenAPI集成详解.md) → [17-SpringDoc与OpenAPI集成实践](17-SpringDoc与OpenAPI集成实践.md)（接口文档：原理/性能/安全/示例）→ [18-Knife4j增强与网关聚合详解](18-Knife4j增强与网关聚合详解.md)（增强 UI/网关聚合）→ [19-协作平台Apifox与Postman详解](19-协作平台Apifox与Postman详解.md)（协作平台）
11. 需要集成时读 数据访问层/安全/测试各域

## 5. 面试考点索引

- 自动装配原理、@SpringBootApplication 组合注解、条件注解族
- 外部化配置优先级、@ConfigurationProperties vs @Value、profile
- starter 自定义原理（双模块）、内嵌容器替换
- Boot4 模块化（starter 改名 web→webmvc）
- 自定义 Starter 开发（详细见 [05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md) / [06-SpringBoot自定义Starter实践](06-SpringBoot自定义Starter实践.md)）
- @Async 异步与失效、线程池配置（[07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)）
- 日志配置 Logback、异步日志（[09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md)）
- Actuator 监控、Micrometer/Prometheus（[11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)）
- WebFlux 响应式、Mono/Flux/背压/SSE、AI 流式（[13-Spring WebFlux响应式编程详解](13-Spring WebFlux响应式编程详解.md) → [14-Spring WebFlux响应式编程实践](14-Spring WebFlux响应式编程实践.md)）
- SpringDoc 原理/性能/安全/注解（[16-SpringDoc与OpenAPI集成详解](16-SpringDoc与OpenAPI集成详解.md) → [17-SpringDoc与OpenAPI集成实践](17-SpringDoc与OpenAPI集成实践.md)）
- Knife4j 增强 UI/网关聚合/生产安全关闭（[18-Knife4j增强与网关聚合详解](18-Knife4j增强与网关聚合详解.md)）
- Apifox/Postman/YApi 选型与 OpenAPI 导入（[19-协作平台Apifox与Postman详解](19-协作平台Apifox与Postman详解.md)）

## 6. 参考资料

- 下一篇：[01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)
- Spring Boot 官方：https://spring.io/projects/spring-boot
- 官方文档：https://docs.spring.io/spring-boot
