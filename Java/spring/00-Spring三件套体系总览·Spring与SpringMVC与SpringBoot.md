---
tags: [Java, Spring, SpringMVC, SpringBoot, 总览, 框架]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring三件套体系总览·Spring与SpringMVC与SpringBoot

> 版本基线：2026-08 整理，覆盖 Spring 核心 / SpringMVC / SpringBoot 三件套的定位、演进与知识域地图
> 受众：Java 后端开发。假设已懂 Java 基础；需理解三件套各自解决什么问题、如何演进、如何配套使用。
> 关联笔记：spring 域（01-03 新篇 + 04 AOP + 05 事务 + 06 SpEL + 15 Filter + 16 拦截器）、springboot 域（00-03）

## 📋 总纲

1. 三件套是什么：各自的定位
2. 演进关系：为何 SpringBoot 是最终归宿
3. 职责边界与依赖层级
4. 全库知识域地图（三件套 → 相关域）
5. 学习路线与推荐顺序

## 1. 三件套是什么

| 框架 | 全称 | 定位 | 一句话 |
| --- | --- | --- | --- |
| **Spring** | Spring Framework | 核心 IoC 容器 + 通用能力 | 管对象的容器（创建/装配/生命周期） |
| **SpringMVC** | Spring Web MVC | Web 层 MVC 框架 | 处理 HTTP 请求路由到方法 |
| **SpringBoot** | Spring Boot | 快速装配/脚手架 | 让上面两件"零配置"跑起来 |

三者不是并列的技术，而是**层层叠加**：Spring 是地基（容器/AOP/事务），SpringMVC 是建在地基上的 Web 模块，SpringBoot 是让整体免配置、开箱即用的整合器。

## 2. 演进关系

```
传统 Spring（XML 时代）
  ├─ 要手动配 XML：bean 定义、扫描、数据源、事务管理器
  ├─ 要手动集成 SpringMVC：web.xml + DispatcherServlet + 视图解析器
  └─ 每引入一个库（redis/kafka/mybatis）都要写一堆 XML/JavaConfig

        ↓ 演进（配置简化 + 约定优于配置）

SpringBoot
  ├─ starter 依赖：引一个 starter 自动带上所需 jar + 自动配置
  ├─ 自动装配：@EnableAutoConfiguration 按 classpath 自动配好 Bean
  ├─ 内嵌容器：内置 Tomcat/Jetty，java -jar 即启动
  └─ 约定优于配置：默认值兜底，只需覆盖差异
```

核心思想一句话：**SpringBoot 把「Spring 核心 + SpringMVC + 第三方集成」的样板配置全部默认化**，开发只关注业务。

## 3. 职责边界与依赖层级

```
┌─────────────────────────────────────────┐
│  SpringBoot（装配层）                      │
│  starter / 自动装配 / 外部化配置 / 内嵌容器  │
│  ┌───────────────────────────────────┐  │
│  │  SpringMVC（Web 层）               │  │
│  │  DispatcherServlet / 控制器/拦截器  │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Spring 核心（容器层）       │  │  │
│  │  │  IoC / DI / AOP / 事务      │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

- **Spring**：对象管理（IoC）、依赖注入、AOP 切面、声明式事务、SpEL、数据访问抽象
- **SpringMVC**：请求路由、参数绑定、返回值处理、拦截器、全局异常、视图解析
- **SpringBoot**：启动引导、自动装配、外部化配置、starter、内嵌容器、监控

## 4. 全库知识域地图

| 本域篇目 | 内容 | 深度 |
| --- | --- | --- |
| [01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md) | IoC/Bean 生命周期/三级缓存/装配 | 深 |
| [02-Spring核心·IoC与Bean生命周期实践](02-Spring核心·IoC与Bean生命周期实践.md) | IoC：XML/注解/JavaConfig 装配 + 配置值含义 | 实操 |
| [03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md) | 请求全流程/参数绑定/拦截器 | 深 |
| [04-SpringMVC执行流程实践](04-SpringMVC执行流程实践.md) | web.xml/控制器/传参 代码 | 实操 |
| [05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md) | 双容器/父子容器/扫描切分 | 深 |
| [06-Spring与SpringMVC整合实践](06-Spring与SpringMVC整合实践.md) | 双容器 web.xml 完整清单 | 实操 |
| [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md) | 切面/动态代理/五通知 | 深 |
| [08-Spring核心·AOP实践](08-Spring核心·AOP实践.md) | 切面代码/切点表达式/失效场景 | 实操 |
| [09-Spring事务管理详解](09-Spring事务管理详解.md) | @Transactional/传播/隔离/失效 | 深 |
| [10-Spring事务管理实践](10-Spring事务管理实践.md) | 事务配置/属性值/自调用坑 | 实操 |
| [11-SpEL表达式详解](11-SpEL表达式详解.md) | 表达式语言/注解取参 | 深 |
| [12-SpEL表达式实践](12-SpEL表达式实践.md) | @Value ${}#{} 用法 | 实操 |
| [13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md) | 观察者模式/事务事件 | 深 |
| [14-Spring事件驱动机制实践](14-Spring事件驱动机制实践.md) | 事件/监听器/发布代码 | 实操 |
| [15-Filter过滤器详解与三层对比](15-Filter过滤器详解与三层对比.md) | 过滤器/容器级/与拦截器·AOP对比 | 深 |
| [16-拦截器Interceptor详解](16-拦截器Interceptor详解.md) | 拦截器（HandlerInterceptor） | 深 |
| [17-全局异常与国际化详解](17-全局异常与国际化详解.md) | 全局异常/错误码/MessageSource/i18n | 深 |
| springboot 域 [00-SpringBoot体系总览](../springboot/00-SpringBoot体系总览.md) | Boot 体系地图 | 深 |
| springboot 域 [01-SpringBoot启动原理与自动装配详解](../springboot/01-SpringBoot启动原理与自动装配详解.md) | 启动流程/自动装配 | 深（重点） |
| springboot 域 [02-SpringBoot配置体系与外部化配置详解](../springboot/02-SpringBoot配置体系与外部化配置详解.md) | 配置优先级/Properties | 深（重点） |
| springboot 域 [03-SpringBoot模块化详解](../springboot/03-SpringBoot模块化详解.md) | Boot4 模块化 | 深 |
| springboot 域 [04-SpringBoot自定义Starter详解](../springboot/04-SpringBoot自定义Starter详解.md) | 自定义 Starter 开发 | 深 |
| springboot 域 [05-SpringBoot异步与线程池详解](../springboot/05-SpringBoot异步与线程池详解.md) | @Async/线程池 | 深 |
| springboot 域 [06-SpringBoot日志配置详解](../springboot/06-SpringBoot日志配置详解.md) | 日志配置 | 深 |
| springboot 域 [07-SpringBoot Actuator监控详解](../springboot/07-SpringBoot Actuator监控详解.md) | 生产监控 | 深 |
| springboot 域 [08-Spring WebFlux响应式编程详解](../springboot/08-Spring WebFlux响应式编程详解.md) | 响应式/AI agent 流式 | 深（重点） |

**跨域关联**：
- Web/HTTP 底层：**00-网络传输协议总览**（见知识库）、Tomcat（spring 内嵌容器）
- 安全：**00-安全框架选型总览·Spring Security & Apache Shiro**（见知识库）（Spring Security 是 MVC 过滤链的典型应用）
- 数据：**00-ORM全家桶总览与选型**（见知识库）（Spring 集成 MyBatis/JPA）
- 分布式：[05-分布式ID与幂等设计详解](../../分布式/核心原理/05-分布式ID与幂等设计详解.md)（幂等落地示例）
- 测试：**05-Spring Boot测试与Testcontainers**（见知识库）

## 5. 学习路线

按「详解 → 实践」交错读（每个知识点先懂原理、再上手代码）：

1. **先读本总览**：建立三件套心智模型
2. **Spring 核心**：[01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)→[02-Spring核心·IoC与Bean生命周期实践](02-Spring核心·IoC与Bean生命周期实践.md)→[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)→[08-Spring核心·AOP实践](08-Spring核心·AOP实践.md)→[09-Spring事务管理详解](09-Spring事务管理详解.md)→[10-Spring事务管理实践](10-Spring事务管理实践.md)→[13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md)→[14-Spring事件驱动机制实践](14-Spring事件驱动机制实践.md)（容器→切面→事务→事件）
3. **SpringMVC**：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)→[04-SpringMVC执行流程实践](04-SpringMVC执行流程实践.md)→[05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md)→[06-Spring与SpringMVC整合实践](06-Spring与SpringMVC整合实践.md)
4. **SpringBoot**（重点）：springboot 域 [01-SpringBoot启动原理与自动装配详解](../springboot/01-SpringBoot启动原理与自动装配详解.md) → [02-SpringBoot配置体系与外部化配置详解](../springboot/02-SpringBoot配置体系与外部化配置详解.md) → [03-SpringBoot模块化详解](../springboot/03-SpringBoot模块化详解.md) → [04-SpringBoot自定义Starter详解](../springboot/04-SpringBoot自定义Starter详解.md) → [05-SpringBoot异步与线程池详解](../springboot/05-SpringBoot异步与线程池详解.md) → [06-SpringBoot日志配置详解](../springboot/06-SpringBoot日志配置详解.md) → [07-SpringBoot Actuator监控详解](../springboot/07-SpringBoot Actuator监控详解.md)
5. 补件：[11-SpEL表达式详解](11-SpEL表达式详解.md)→[12-SpEL表达式实践](12-SpEL表达式实践.md)（随 AOP/缓存用到再读）、[15-Filter过滤器详解与三层对比](15-Filter过滤器详解与三层对比.md)→[16-拦截器Interceptor详解](16-拦截器Interceptor详解.md)（请求横切链）→[17-全局异常与国际化详解](17-全局异常与国际化详解.md)（异常+多语言）、[08-Spring WebFlux响应式编程详解](../springboot/08-Spring WebFlux响应式编程详解.md)（AI agent/高并发 IO）

## 6. 面试考点索引

- Spring：Bean 生命周期、三级缓存循环依赖、IoC/DI 区别、AOP 原理、事务传播、事件机制
- SpringMVC：DispatcherServlet 流程、[拦截器 vs Filter](15-Filter过滤器详解与三层对比.md)、参数绑定、全局异常
- SpringBoot：自动装配原理、@SpringBootApplication 组合注解、条件注解、外部化配置优先级、starter、@Async 异步、日志、Actuator 监控、WebFlux 响应式

## 7. 参考资料

- 下一篇：[01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)（进入 Spring 核心）
- Spring 官方：https://spring.io/projects/spring-boot
