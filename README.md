# 📚 笔记分享库

个人学习笔记整理 · 面向后端开发者（Java / Python / Lua）

> **仓库镜像**
> - Gitee：https://gitee.com/plyr/notebook
> - GitHub：https://github.com/plyrlub/notebook
>
> **网页版（GitHub Pages，推荐阅读）**：https://plyrlub.github.io/notebook/

---

## Java

### Java 核心机制

- [Java SPI机制详解](Java/Java%20SPI机制详解.md)
    JDK / Spring / Dubbo / Servlet 四机制全覆盖
- [Java volatile详解](Java/Java%20volatile详解.md)
    JMM/硬件链路、MESI、内存屏障、假共享、面试 10 问
- [Java反射详解](Java/Java反射详解.md)
    核心 API/为什么慢、缓存 → MethodHandle → LambdaMetafactory 四层优化、面试 8 问

### JVM

- [Java GC详解](Java/Java%20GC详解.md)
    判活/算法/收集器演进（Serial→G1→ZGC）、三色标记、SafePoint、面试 11 问

### Java 框架

- [Tomcat总览](Java/tomcat/00-Tomcat总览.md)
    基于 8.5.x：架构/Coyote/Catalina、server.xml 全标签、源码构建、启动流程、类加载、HTTPS、性能优化 7 大章 + 类加载深度篇

### Spring 三件套（Spring / SpringMVC / SpringBoot）

- [Spring三件套体系总览](Java/spring/00-Spring%E4%B8%89%E4%BB%B6%E5%A5%97%E4%BD%93%E7%B3%BB%E6%80%BB%E8%A7%88%C2%B7Spring%E4%B8%8ESpringMVC%E4%B8%8ESpringBoot.md)
    三件套定位/演进/职责边界/知识域地图/学习路线
- [Spring核心·IoC与Bean生命周期](Java/spring/01-Spring%E6%A0%B8%E5%BF%83%C2%B7IoC%E4%B8%8EBean%E7%94%9F%E5%91%BD%E5%91%A8%E6%9C%9F%E8%AF%A6%E8%A7%A3.md)
    IoC/DI、Bean 生命周期、三种装配、循环依赖三级缓存、作用域
- [SpringMVC执行流程](Java/spring/02-SpringMVC%E6%89%A7%E8%A1%8C%E6%B5%81%E7%A8%8B%E8%AF%A6%E8%A7%A3.md)
    DispatcherServlet 流程、参数绑定、拦截器、全局异常
- [Spring与SpringMVC整合实践](Java/spring/03-Spring%E4%B8%8ESpringMVC%E6%95%B4%E5%90%88%E5%AE%9E%E8%B7%B5%E8%AF%A6%E8%A7%A3.md)
    双容器、web.xml→Boot 演进、扫描分离坑
- [Spring核心·AOP详解](Java/spring/04-Spring%E6%A0%B8%E5%BF%83%C2%B7AOP%E8%AF%A6%E8%A7%A3.md)
    动态代理/CGLIB、五种通知、切点、失效场景
- [Spring事务管理详解](Java/spring/05-Spring%E4%BA%8B%E5%8A%A1%E7%AE%A1%E7%90%86%E8%AF%A6%E8%A7%A3.md)
    @Transactional、7 传播、隔离级别、12 类失效
- [SpEL表达式详解](Java/spring/06-SpEL%E8%A1%A8%E8%BE%BE%E5%BC%8F%E8%AF%A6%E8%A7%A3.md)
    SpEL 语法、注解取参、AOP 切面手动解析
- [Spring事件驱动机制详解](Java/spring/07-Spring%E4%BA%8B%E4%BB%B6%E9%A9%B1%E5%8A%A8%E6%9C%BA%E5%88%B6%E8%AF%A6%E8%A7%A3.md)
    观察者模式、@EventListener、@TransactionalEventListener 事务事件
- [Filter过滤器详解与三层对比](Java/spring/15-Filter%E8%BF%87%E6%BB%A4%E5%99%A8%E8%AF%A6%E8%A7%A3%E4%B8%8E%E4%B8%89%E5%B1%82%E5%AF%B9%E6%AF%94.md)
    Servlet规范、三方法、两种配置、为何Boot少用、Filter/拦截器/AOP三层对比、响应式 Netty/WebFilter
- [拦截器Interceptor详解](Java/spring/16-%E6%8B%A6%E6%88%AA%E5%99%A8Interceptor%E8%AF%A6%E8%A7%A3.md)
    HandlerInterceptor 三方法、HandlerMethod、注册鉴权、vs Filter/AOP、常见坑
- [全局异常与国际化详解](Java/spring/17-%E5%85%A8%E5%B1%80%E5%BC%82%E5%B8%B8%E4%B8%8E%E5%9B%BD%E9%99%85%E5%8C%96%E8%AF%A6%E8%A7%A3.md)
    @ControllerAdvice、BusinessException、数字分段错误码、MessageSource/i18n、LocaleResolver

#### SpringBoot（重点）

- [SpringBoot体系总览](Java/springboot/00-SpringBoot%E4%BD%93%E7%B3%BB%E6%80%BB%E8%A7%88.md)
    定位/核心三大件/知识域地图/学习路线/面试考点
- [SpringBoot启动原理与自动装配详解](Java/springboot/01-SpringBoot%E5%90%AF%E5%8A%A8%E5%8E%9F%E7%90%86%E4%B8%8E%E8%87%AA%E5%8A%A8%E8%A3%85%E9%85%8D%E8%AF%A6%E8%A7%A3.md)
    @SpringBootApplication、自动装配、.imports、条件注解
- [SpringBoot配置体系与外部化配置详解](Java/springboot/02-SpringBoot%E9%85%8D%E7%BD%AE%E4%BD%93%E7%B3%BB%E4%B8%8E%E5%A4%96%E9%83%A8%E5%8C%96%E9%85%8D%E7%BD%AE%E8%AF%A6%E8%A7%A3.md)
    外部化配置优先级、@ConfigurationProperties vs @Value、profile
- [SpringBoot模块化详解](Java/springboot/03-SpringBoot%E6%A8%A1%E5%9D%97%E5%8C%96%E8%AF%A6%E8%A7%A3.md)
    Boot4 一个 jar→一组模块、starter 改名
- [SpringBoot自定义Starter详解](Java/springboot/04-SpringBoot%E8%87%AA%E5%AE%9A%E4%B9%89Starter%E8%AF%A6%E8%A7%A3.md)
    双模块、@AutoConfiguration、.imports 注册、元数据、测试
- [SpringBoot异步与线程池详解](Java/springboot/05-SpringBoot%E5%BC%82%E6%AD%A5%E4%B8%8E%E7%BA%BF%E7%A8%8B%E6%B1%A0%E8%AF%A6%E8%A7%A3.md)
    @Async、线程池配置、CompletableFuture、失效场景
- [SpringBoot日志配置详解](Java/springboot/06-SpringBoot%E6%97%A5%E5%BF%97%E9%85%8D%E7%BD%AE%E8%AF%A6%E8%A7%A3.md)
    SLF4J+Logback、logback-spring.xml、滚动策略、MDC
- [SpringBoot Actuator监控详解](Java/springboot/07-SpringBoot%20Actuator%E7%9B%91%E6%8E%A7%E8%AF%A6%E8%A7%A3.md)
    health、Micrometer、Prometheus/Grafana、安全暴露
- [Spring WebFlux响应式编程详解](Java/springboot/08-Spring%20WebFlux%E5%93%8D%E5%BA%94%E5%BC%8F%E7%BC%96%E7%A8%8B%E8%AF%A6%E8%A7%A3.md)
    Mono/Flux、背压、SSE 流式输出（AI agent）、MVC vs WebFlux

### 构建工具

- **构建工具总览·Maven & Gradle选型对比**（见知识库）
    两大构建工具定位、核心差异与选型建议
- [Maven 依赖与仓库](Java/构建工具/Maven/01-依赖与仓库.md)
    依赖配置/范围/调解 + 仓库/镜像/私服
- [Maven 生命周期与插件](Java/构建工具/Maven/02-生命周期与插件.md)
    三套生命周期/插件绑定 + 聚合与继承
- [Maven 私服与测试](Java/构建工具/Maven/03-私服与测试.md)
    Nexus 私服搭建 + surefire 测试
- [Maven 版本与灵活构建](Java/构建工具/Maven/04-版本与灵活构建.md)
    版本约定/发布 + 属性/Profile/Archetype
- [Gradle核心机制详解](Java/构建工具/Gradle/01-Gradle核心机制详解.md)
    Gradle 定位/构建脚本/DSL/Wrapper
- [Gradle Task与生命周期详解](Java/构建工具/Gradle/02-Gradle%20Task与生命周期详解.md)
    Task DAG/增量构建/常用命令
- [Gradle依赖管理详解](Java/构建工具/Gradle/03-Gradle依赖管理详解.md)
    Configuration/冲突解析/Version Catalog
- [Gradle多项目构建详解](Java/构建工具/Gradle/04-Gradle多项目构建详解.md)
    include/子项目依赖/Composite Build
- [Gradle性能优化详解](Java/构建工具/Gradle/05-Gradle性能优化详解.md)
    守护进程/构建缓存/配置缓存/实测

## 数据库

### DB 通用理论（跨库通用概念层）

- [数据库总览](数据库/00-数据库总览.md)
    知识域统一入口，4 大分支索引：MySQL / PostgreSQL / Redis / DB 通用理论
- [关系型DB事务详解](数据库/DB通用理论/01-关系型DB事务详解.md)
    ACID/事务边界/隔离级别(脏读/不可重复读/幻读)/保存点/各库默认级别
- [关系型DB锁详解](数据库/DB通用理论/02-关系型DB锁详解.md)
    乐观vs悲观/锁粒度/共享排他/锁升级/死锁四条件
- [关系型DB-MVCC详解](数据库/DB通用理论/03-关系型DB-MVCC详解.md)
    MVCC 是什么/两套方案对比/快照机制/各库差异

### PostgreSQL（已同步篇目）

- [PostgreSQL 事务详解](数据库/PostgreSQL/01-基础/06-事务详解.md)
    PG 事务语法/默认隔离级别/保存点 SQL/本机实测
- [PostgreSQL 锁详解](数据库/PostgreSQL/01-基础/07-锁详解.md)
    7 种表锁/行锁 SQL/pg_locks/咨询锁/死锁/实测
- [PostgreSQL MVCC 深入原理](数据库/PostgreSQL/02-设计原理/03-MVCC深入原理.md)
    元组头/clog/hint bits/VM/HOT/VACUUM/快照构建/表膨胀

## 通用技术

### 前后端缓存

- [前后端缓存总览](通用技术/前后端缓存/00-前后端缓存总览.md)
    省什么坐标系（请求/流量/计算/轮询）+ 完整决策表 + 后端缓存导航桥接表（Redis 三大问题/多级缓存/一致性）
- [客户端缓存详解](通用技术/前后端缓存/01-客户端缓存详解.md)
    TTL / SWR / 防抖 / 请求合并，前端主缓存层
- [协商缓存详解](通用技术/前后端缓存/02-协商缓存详解.md)
    ETag/304 + Redis hash 设计 + 适用边界 + 归属表（静态归 CDN/动态归后端/实时别用）
- [补充·缓存更新策略](通用技术/前后端缓存/03-后端缓存补充·缓存更新策略.md)
    TTL vs 主动失效 vs 事件驱动全景对比（增量视角）
- [补充·CDN协同](通用技术/前后端缓存/04-后端缓存补充·CDN协同.md)
    CDN 层缓存与前后端协同：s-maxage / 三级失效（增量视角）
- [补充·缓存监控](通用技术/前后端缓存/05-后端缓存补充·缓存监控.md)
    命中率/容量/运行时三级监控指标与告警（增量视角）

### 软件保护

- [软件保护总览](通用技术/软件保护/00-软件保护总览.md)
    代码混淆（防读懂代码）+ 软件授权 License（防白嫖使用）模块导航
- [代码混淆详解](通用技术/软件保护/01-代码混淆详解.md)
    ProGuard/R8/PyArmor、混淆原理、keep 规则、堆栈还原、常见误区
- [License授权详解](通用技术/软件保护/02-License授权详解.md)
    非对称签名原理、机器码绑定、四方案对比、Java/Python 实例、微服务 Entitlement 功能约束

## 服务器

### Linux

- [Linux总览](Linux/00-Linux总览.md)
    Ubuntu/CentOS 双版本：用户管理与登录授权/文件权限/常用命令/系统优化与性能排查/安全加固 5 篇，后端视角命令组合与排障套路

### Nginx

- [Nginx总览](Nginx/00-Nginx总览.md)
    基于 1.30.4：基础认知/配置/核心机制/反向代理/安全/性能/OpenResty 8 大主题（38 篇）

## 其他语言

### Lua

- [Lua总览](其他语言/Lua/00-Lua总览.md)
    Lua 5.4 全体系 15 篇：基础语法/数据类型与 table/运算符/函数/字符串与 pattern/元表/面向对象/协程/错误处理/文件包管理/三方资源/沙箱/5.4 新特性/LuaJIT
- 系列：00-Lua总览 → 01-基础语法 → 02-数据类型与table → 03-运算符与流程控制 → 04-函数与闭包 → 05-字符串与模式匹配 → 06-元表与元方法 → 07-面向对象 → 08-协程 → 09-错误处理 → 10-文件与包管理 → 11-三方资源（MySQL/Redis）→ 12-环境隔离与沙箱 → 13-Lua 5.4新特性 → 14-LuaJIT与性能优化

## 分布式

### 核心原理

- [分布式基础总览](分布式/00-分布式基础总览.md)
    知识域地图、学习路线（分布式为跨技术栈通用原理，独立成域）
- [一致性Hash算法详解](分布式/核心原理/01-一致性Hash算法详解.md)
    Hash 环、虚拟节点、数据倾斜、Redis 哈希槽/Nginx 对照
- [CAP与BASE理论详解](分布式/核心原理/02-CAP与BASE理论详解.md)
    CAP 定理、BASE 理论、一致性模型、选型
- [分布式锁原理详解](分布式/核心原理/03-分布式锁原理详解.md)
    Redis/Zookeeper 实现、防死锁、可重入、Redlock
- [分布式事务详解](分布式/核心原理/04-分布式事务详解.md)
    2PC/3PC、TCC、Saga、本地消息表、选型
- [分布式ID与幂等设计详解](分布式/核心原理/05-分布式ID与幂等设计详解.md)
    雪花算法、UUID、号段模式、防重复提交
- [负载均衡详解](分布式/核心原理/06-负载均衡详解.md)
    四层 vs 七层模型、LVS/HAProxy/Nginx/Envoy、调度算法、高可用选型
- [Raft与Paxos共识算法详解](分布式/核心原理/07-Raft与Paxos共识算法详解.md)
    Raft 选举/日志复制/安全性、Paxos 思想、ZAB 三方对比
- [分布式Session详解](分布式/核心原理/09-分布式Session详解.md)
    Session 同步方案、粘性会话、分布式会话存储选型

### ZooKeeper 系列

- [ZooKeeper总览](分布式/Zookeeper/00-ZooKeeper总览.md)
    定位/架构/安装/配置/生产建议 + etcd 选型 + 9 篇系列导航
- 系列：00-总览 → 01-数据模型与节点 → 02-会话与Watch → 03-集群与Leader选举 → 04-ZAB协议与一致性 → 05-ACL权限控制 → 06-Java客户端API → 07-Curator → 08-运维与监控 → 09-应用场景与分布式协同

## 安全框架

_（待分享：Spring Security / Apache Shiro）_

## DevOps

### CI/CD

- [CI/CD 学习笔记（总览）](CI-CD/00-CI-CD%20学习笔记（总览）.md)
    10 章系统学习：认知地基/工具选型/Actions/GitLab/Jenkins/容器化/K8s 部署/DevSecOps/可观测性 + S1~S12 补充专题（Secret/SBOM/Feature Flag/开源设施部署等）+ 可运行 Demo
- [面试题集锦](CI-CD/面试题集锦.md)
    8 大领域 45 道题（含难度与参考答案，高频题标 🔥）
- 系列：00-总览 → 01-认知地基 → 02-环境与前置技能 → 03-工具选型与对比 → 04-核心工具深入 → 05-构建与测试 → 06-容器化与制品管理 → 07-部署与发布策略 → 08-安全与质量门禁 → 09-监控可观测性与回滚 → 10-进阶与工程化
- 补充专题（12 篇）：S1-Secret管理 / S2-成本与配额 / S3-DORA四指标 / S4-供应链安全SBOM / S5-流水线自身安全 / S6-数据库迁移 / S7-FeatureFlag解耦部署 / S8-Lua场景CICD / S9-质量安全扫描集成 / S10-Pipeline各环节最佳实践 / S11-包仓库Nexus-Harbor-GitLabRegistry / S12-CICD开源设施部署指南

## LLM / AI

_（待分享）_