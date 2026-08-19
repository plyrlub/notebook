# 📚 笔记分享库

个人学习笔记整理 · 面向后端开发者（Java / Python / Lua）

> **仓库镜像**
> - Gitee：https://gitee.com/plyr/notebook
> - GitHub：https://github.com/plyrlub/notebook
>
> **网页版（GitHub Pages，推荐阅读）**：https://plyrlub.github.io/notebook/

---

## Java

### JDK 基础库

- [JDK基础库总览](Java/JDK基础库/00-JDK基础库总览.md)
    并发 / 集合 / 核心机制 / 新特性统一入口

#### 并发编程

- [并发编程总览](Java/JDK基础库/并发/00-并发编程总览.md)
    多线程 / JUC / 线程池知识域地图
- [多线程基础详解](Java/JDK基础库/并发/01-多线程基础详解.md)
    线程状态、start/join/yield、CAS、锁基础
- [Java volatile详解](Java/JDK基础库/并发/Java%20volatile详解.md)
    JMM/硬件链路、MESI、内存屏障、假共享、面试 10 问
- [JUC之锁与AQS](Java/JDK基础库/并发/JUC/01-JUC之锁与AQS.md)
    AQS、ReentrantLock、读写锁、StampedLock、Condition
- [JUC之原子类与CAS](Java/JDK基础库/并发/JUC/02-JUC之原子类与CAS.md)
    Atomic 系列、CAS ABA、LongAdder
- [JUC之并发容器](Java/JDK基础库/并发/JUC/03-JUC之并发容器.md)
    ConcurrentHashMap、CopyOnWrite、阻塞队列
- [Java线程池原理与参数详解](Java/JDK基础库/并发/线程池/01-Java线程池原理与参数详解.md)
    ThreadPoolExecutor 七参、提交流程、拒绝策略
- [线程数设置与虚拟线程选型](Java/JDK基础库/并发/线程池/03-线程数设置与虚拟线程选型.md)
    CPU/IO 密集、线程池调优、虚拟线程

#### 核心机制

- [Java SPI机制详解](Java/JDK基础库/核心机制/Java SPI机制详解.md)
    JDK / Spring / Dubbo / Servlet 四机制全覆盖
- [Java反射详解](Java/JDK基础库/核心机制/Java反射详解.md)
    核心 API/为什么慢、缓存 → MethodHandle → LambdaMetafactory 四层优化、面试 8 问
- [Java注解机制详解](Java/JDK基础库/核心机制/Java注解机制详解.md)
    自定义注解、Annotation 处理、与反射配合
- [Java代理详解](Java/JDK基础库/核心机制/Java代理详解.md)
    JDK 动态代理 / CGLIB、用途与选型
- [Java Agent与字节码增强详解](Java/JDK基础库/核心机制/Java%20Agent与字节码增强详解.md)
    premain/agentmain、Instrumentation、字节码增强原理

### JVM

- [JVM总览](Java/JVM/00-JVM总览.md)
    内存/GC/类加载/调优知识域地图
- [JMM内存模型详解](Java/JVM/JMM内存模型详解.md)
    JMM、happens-before、主存/工作内存、volatile/synchronized 语义
- [Java类加载机制与双亲委派详解](Java/JVM/Java类加载机制与双亲委派详解.md)
    类加载过程、双亲委派、打破场景
- [Java GC详解](Java/JVM/Java%20GC详解.md)
    判活/算法/收集器演进（Serial→G1→ZGC）、三色标记、SafePoint、面试 11 问
- [JVM调优实战](Java/JVM/JVM调优实战.md)
    参数调优、GC 日志、内存泄漏排查
- [Arthas在线诊断](Java/JVM/Arthas在线诊断.md)
    JVM 诊断命令、线上排障实战

### Spring 三件套（Spring / SpringMVC / SpringBoot）

- [Spring三件套体系总览](Java/框架/spring/00-Spring三件套体系总览·Spring与SpringMVC与SpringBoot.md)
    三件套定位/演进/职责边界/知识域地图/学习路线
- [Spring核心·IoC与Bean生命周期详解](Java/框架/spring/01-Spring核心·IoC与Bean生命周期详解.md)
    IoC/DI、Bean 生命周期、三种装配、循环依赖三级缓存、作用域
- [Spring核心·IoC与Bean生命周期实践](Java/框架/spring/02-Spring核心·IoC与Bean生命周期实践.md)
    注解式装配实战、常用注解、XML/注解混用
- [SpringMVC执行流程详解](Java/框架/spring/03-SpringMVC执行流程详解.md)
    DispatcherServlet 流程、参数绑定、拦截器、全局异常
- [Spring核心·AOP详解](Java/框架/spring/07-Spring核心·AOP详解.md)
    动态代理/CGLIB、五种通知、切点、失效场景
- [Spring事务管理详解](Java/框架/spring/09-Spring事务管理详解.md)
    @Transactional、7 传播、隔离级别、12 类失效
- [SpEL表达式详解](Java/框架/spring/11-SpEL表达式详解.md)
    SpEL 语法、注解取参、AOP 切面手动解析
- [Filter过滤器详解与三层对比](Java/框架/spring/15-Filter过滤器详解与三层对比.md)
    Servlet规范、三方法、两种配置、Filter/拦截器/AOP 三层对比
- [全局异常与国际化详解](Java/框架/spring/17-全局异常与国际化详解.md)
    @ControllerAdvice、BusinessException、错误码、MessageSource/i18n

#### SpringBoot（详解 + 实践）

- [SpringBoot体系总览](Java/框架/springboot/00-SpringBoot体系总览.md)
    定位/核心三大件/知识域地图/学习路线
- [启动原理与自动装配详解](Java/框架/springboot/01-SpringBoot启动原理与自动装配详解.md)
    @SpringBootApplication、自动装配、.imports、条件注解
- [配置体系与外部化配置详解](Java/框架/springboot/02-SpringBoot配置体系与外部化配置详解.md)
    外部化配置优先级、@ConfigurationProperties vs @Value、profile
- [模块化详解](Java/框架/springboot/04-SpringBoot模块化详解.md)
    Boot4 一个 jar→一组模块、starter 改名
- [自定义Starter详解](Java/框架/springboot/05-SpringBoot自定义Starter详解.md)
    双模块、@AutoConfiguration、.imports 注册、元数据
- [异步与线程池详解](Java/框架/springboot/07-SpringBoot异步与线程池详解.md)
    @Async、线程池配置、CompletableFuture、失效场景
- [日志配置详解](Java/框架/springboot/09-SpringBoot日志配置详解.md)
    SLF4J+Logback、logback-spring.xml、滚动策略、MDC
- [Actuator监控详解](Java/框架/springboot/11-SpringBoot%20Actuator监控详解.md)
    health、Micrometer、Prometheus/Grafana、安全暴露
- [WebFlux响应式编程详解](Java/框架/springboot/13-Spring%20WebFlux响应式编程详解.md)
    Mono/Flux、背压、SSE 流式输出（AI agent）、MVC vs WebFlux
- [SpringDoc与OpenAPI集成详解](Java/框架/springboot/16-SpringDoc与OpenAPI集成详解.md)
    OpenAPI 3、springdoc 配置、注解派生产品文档

### 安全框架

- [安全框架选型总览·Spring Security & Apache Shiro](Java/框架/安全/00-安全框架选型总览·Spring%20Security%20&%20Apache%20Shiro.md)
    两大框架定位、对比选型
- [Spring Security核心架构详解](Java/框架/安全/01-Spring%20Security核心架构详解.md)
    FilterChain、SecurityContext、认证/授权架构
- [Spring Security认证机制详解](Java/框架/安全/02-Spring%20Security认证机制详解.md)
    UsernamePassword、JWT/OAuth2、认证流程
- [Apache Shiro核心架构详解](Java/框架/安全/04-Apache%20Shiro核心架构详解.md)
    Subject/SecurityManager/Realm、认证授权流程
- [Spring Security与Shiro对比选型详解](Java/框架/安全/07-Spring%20Security与Shiro对比选型详解.md)
    核心差异、社区、适用场景、迁移建议

### 定时任务

- [定时任务框架选型总览](Java/框架/定时任务/00-定时任务框架选型总览.md)
    Quartz / XXL-Job / Elastic-Job / PowerJob 对比
- [Quartz详解](Java/框架/定时任务/01-Quartz详解.md)
    JobDetail/Trigger/Scheduler、集群、持久化
- [XXL-Job详解](Java/框架/定时任务/02-XXL-Job详解.md)
    调度中心/执行器、分片、路由策略

### 数据访问层（ORM / 分库分表）

- [ORM全家桶总览与选型](Java/框架/数据访问层/00-ORM全家桶总览与选型.md)
    MyBatis / MyBatis-Plus / JPA 定位与选型
- [MyBatis核心机制详解](Java/框架/数据访问层/01-MyBatis核心机制详解.md)
    动态代理、SqlSession、四大对象、生命周期
- [MyBatisPlus核心机制详解](Java/框架/数据访问层/05-MyBatis%20Plus核心机制详解.md)
    通用 CRUD、条件构造器、分页插件
- [JPA与Spring Data JPA详解](Java/框架/数据访问层/06-JPA与Spring%20Data%20JPA详解.md)
     实体映射、Repository、@Query 派生查询
- [分库分表总览与选型](Java/框架/数据访问层/分库分表/00-分库分表总览与选型.md)
    垂直/水平拆分、中间件选型
- [分片键与分片算法详解](Java/框架/数据访问层/分库分表/02-分片键与分片算法详解.md)
    分片键设计、哈希/范围/区间分片
- [ShardingSphere-JDBC集成与配置详解](Java/框架/数据访问层/分库分表/04-ShardingSphere-JDBC集成与配置详解.md)
    集成配置、读写分离、分片实战

### 服务通信 / 网络底座

- [RPC与远程调用总览](Java/框架/服务通信/00-RPC与远程调用总览.md)
    RPC 原理、序列化/协议、对比选型
- [Apache Dubbo详解](Java/框架/服务通信/04-Apache%20Dubbo详解.md)
    注册中心、负载均衡、SPI 扩展、线程模型
- [gRPC详解](Java/框架/服务通信/05-gRPC详解.md)
    Protobuf、HTTP/2、流式 RPC
- [OpenFeign详解](Java/框架/服务通信/06-OpenFeign详解.md)
    声明式 HTTP 客户端、编码器/解码器、日志
- [网络底座总览](Java/框架/网络底座/00-网络底座总览.md)
    Socket/NIO/Netty/Web服务器 知识域
- [Socket与IO模型](Java/框架/网络底座/网络通信/01-Socket与IO模型.md)
    BIO/NIO/AIO、事件驱动、reactor
- [Java NIO详解](Java/框架/网络底座/网络通信/02-Java%20NIO详解.md)
    Channel/Buffer/Selector、零拷贝
- [Netty核心机制详解](Java/框架/网络底座/网络通信/03-Netty核心机制详解.md)
    EventLoop/ChannelPipeline、编解码、心跳
- [Tomcat总览](Java/框架/网络底座/Web服务器/tomcat/00-Tomcat总览.md)
    基于 8.5.x：架构/Coyote/Catalina、server.xml、源码、类加载、HTTPS、性能优化
- [Tomcat类加载机制详解](Java/框架/网络底座/Web服务器/tomcat/06-Tomcat类加载机制详解.md)
   ⭐ 双亲委派打破、类隔离、热部署
- [Tomcat性能优化策略](Java/框架/网络底座/Web服务器/tomcat/08-Tomcat性能优化策略.md)
    JVM/GC 调优、线程池、连接器/IO 模式调优

### 三方库

- [Caffeine Java缓存详解](Java/三方库/Caffeine%20Java缓存详解.md)
    本地缓存选型、缓存淘汰、统计
- [Guava概览与模块化辨析](Java/三方库/Guava/00-Guava概览与模块化辨析.md)
    Guava 模块划分与取舍
- [Guava collect集合增强详解](Java/三方库/Guava/02-Guava%20collect集合增强详解.md)
    Immutable、Multimap、BiMap、RangeSet
- [Guava concurrent与cache详解](Java/三方库/Guava/03-Guava%20concurrent与cache详解.md)
    ListenableFuture、RateLimiter、Cache 构建器
- [JSON序列化与反序列化总览](Java/三方库/JSON序列化/00-JSON序列化与反序列化总览.md)
    Gson/Fastjson2/Jackson 定位与选型
- [Jackson核心与ObjectMapper详解](Java/三方库/JSON序列化/05-Jackson核心与ObjectMapper详解.md)
    核心注解、配置、ObjectMapper 定制
- [Jackson与SpringBoot集成详解](Java/三方库/JSON序列化/07-Jackson与SpringBoot集成详解.md)
    WebMvc 配置、JSON 视图、日期处理
- [Lombok详解](Java/三方库/Lombok详解.md)
    注解处理器、常用注解、与编译期增强
- [MapStruct详解](Java/三方库/MapStruct详解.md)
    Bean 映射、编译期代码生成、性能

### 设计模式

- [设计模式总览](Java/设计模式/00-设计模式总览.md)
    GoF 23 与高频面试模式地图
- [单例模式详解](Java/设计模式/01-单例模式详解.md)
    饿汉/懒汉/DCL/枚举、反射与序列化防破坏
- [工厂方法与简单工厂详解](Java/设计模式/02-工厂方法与简单工厂详解.md)
    简单工厂/工厂方法/抽象工厂定位
- [建造者模式详解](Java/设计模式/04-建造者模式详解.md)
    Builder 链式、与构造函数对比
- [代理模式详解](Java/设计模式/07-代理模式详解.md)
    JDK 动态代理/CGLIB、静态与动态
- [设计模式踩坑记录](Java/设计模式/99-设计模式踩坑记录.md)
    过度设计、必填校验绕过等反模式

### 构建工具

- [构建工具总览·Maven & Gradle选型对比](Java/构建工具/00-构建工具总览·Maven%20&%20Gradle选型对比.md)
    两大构建工具定位、核心差异与选型建议
- [Maven 依赖与仓库](Java/构建工具/Maven/01-依赖与仓库.md)
    依赖配置/范围/调解 + 仓库/镜像/私服
- [Maven 生命周期与插件](Java/构建工具/Maven/02-生命周期与插件.md)
    三套生命周期/插件绑定 + 聚合与继承
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

### 测试

- [测试体系总览](Java/测试/00-测试体系总览.md)
    单元/集成/基准/契约测试布局
- [JUnit 5详解](Java/测试/01-JUnit%205详解.md)
    JUnit5 架构、断言、参数化、生命周期
- [Mockito详解](Java/测试/02-Mockito详解.md)
    打桩、verify、ArgumentMatcher、spy
- [JMH基准测试详解](Java/测试/03-JMH基准测试详解.md)
    微基准、死代码消除、黑名单
- [Spring Boot测试与Testcontainers](Java/测试/05-Spring%20Boot测试与Testcontainers.md)
    @SpringBootTest、切片测试、容器集成测试

### 微服务

- [微服务总览](Java/微服务/00-微服务总览.md)
    架构演进、拆分、治理知识域
- [Spring Cloud Gateway详解](Java/微服务/网关/01-Spring%20Cloud%20Gateway详解.md)
    路由、过滤器、负载均衡集成（索引/骨架）
- [内置过滤器详解](Java/微服务/网关/04-内置过滤器详解.md)
    断言、过滤器工厂、三过滤器对比、跨域/重试/熔断
- [内置GlobalFilter深度](Java/微服务/网关/05-内置GlobalFilter深度.md)
    GlobalFilter 清单/顺序、FilteringWebHandler 源码、自定义
- [Actuator运维实操](Java/微服务/网关/06-Actuator运维实操.md)
    Actuator 运行时观察与动态增删路由
- [动态路由与高可用](Java/微服务/网关/07-动态路由与高可用.md)
    WebSocket、动态路由(Nacos)、配置实战、生产实践
- [网关鉴权详解](Java/微服务/网关/08-网关鉴权详解.md)
    统一鉴权、JWT、TokenRelay
- [Spring Cloud Gateway实践](Java/微服务/网关/02-Spring%20Cloud%20Gateway实践.md)
    工程骨架与联调
- [Sentinel流量控制详解](Java/微服务/治理/01-Sentinel流量控制详解.md)
    限流/熔断/降级、控制台、规则持久化
- [熔断限流降级·原理与组件选型](Java/微服务/治理/02-熔断限流降级·原理与组件选型.md)
    Sentinel / Hystrix / resilience4j 对比选型

### 中间件

- [中间件总览](Java/中间件/00-中间件总览.md)
    分布式协调 / 配置中心 / 注册中心知识域
- [Seata分布式事务框架详解](Java/中间件/分布式协调/分布式事务/Seata分布式事务框架详解.md)
    AT/TCC/SAGA 模式、事务协调
- [Apollo配置中心详解](Java/中间件/配置中心/Apollo/01-Apollo配置中心详解.md)
    分层配置、热加载、灰度发布
- [Nacos配置·动态热加载详解](Java/中间件/配置中心/Nacos/01-Nacos配置·动态热加载详解.md)
    Nacos 配置中心、监听与刷新
- [Nacos服务注册与发现详解](Java/中间件/配置中心/Nacos/03-服务注册与发现详解.md)
    NamingService、健康检查、负载均衡

### 代码片段

- [IP转换（IPv4 ↔ long / IPv6 ↔ BigInteger）](Java/代码片段/IP转换.md)
    通用 IP 数值化工具方法（JDK 17 实测）

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