# 📚 笔记分享库

个人学习笔记整理 · 面向后端开发者（Java / Python / Lua）

> **网页版**：https://plyrlub.github.io/notebook/ ｜ **仓库**：[GitHub](https://github.com/plyrlub/notebook) ｜ [Gitee](https://gitee.com/plyr/notebook)

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
    基于 8.5.x：架构/Coyote/Catalina、server.xml 全标签、源码构建、启动流程、类加载、HTTPS、性能优化 + 类加载深度篇

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

---

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

## 服务器

### Nginx

- [Nginx总览](Nginx/00-Nginx总览.md)
    基于 1.30.4：基础认知/配置/核心机制/反向代理/安全/性能/OpenResty 8 大主题
- 覆盖：基础认知、配置基础、核心机制、反向代理与负载均衡、安全与传输、高级与优化、OpenResty 与 Lua、专题补充（38 篇）

## 其他语言

### Lua

- [Lua总览](其他语言/Lua/00-Lua总览.md)
    Lua 5.4 全体系 15 篇：基础语法/数据类型与 table/运算符/函数/字符串与 pattern/元表/面向对象/协程/错误处理/文件包管理/三方资源/沙箱/5.4 新特性/LuaJIT
- 系列：00-Lua总览 → 01-基础语法 → 02-数据类型与table → 03-运算符与流程控制 → 04-函数与闭包 → 05-字符串与模式匹配 → 06-元表与元方法 → 07-面向对象 → 08-协程 → 09-错误处理 → 10-文件与包管理 → 11-三方资源（MySQL/Redis）→ 12-环境隔离与沙箱 → 13-Lua 5.4新特性 → 14-LuaJIT与性能优化

## 分布式

### 核心原理

- [分布式基础总览](分布式/00-分布式基础总览.md)
    知识域地图、学习路线（分布式为跨技术栈通用原理，独立成域）
- [一致性Hash算法详解](分布式/01-一致性Hash算法详解.md)
    Hash 环、虚拟节点、数据倾斜、Redis 哈希槽/Nginx 对照
- [CAP与BASE理论详解](分布式/02-CAP与BASE理论详解.md)
    CAP 定理、BASE 理论、一致性模型、选型
- [分布式锁原理详解](分布式/03-分布式锁原理详解.md)
    Redis/Zookeeper 实现、防死锁、可重入、Redlock
- [分布式事务详解](分布式/04-分布式事务详解.md)
    2PC/3PC、TCC、Saga、本地消息表、选型
- [分布式ID与幂等设计详解](分布式/05-分布式ID与幂等设计详解.md)
    雪花算法、UUID、号段模式、防重复提交
- [负载均衡详解](分布式/06-负载均衡详解.md)
    四层 vs 七层模型、LVS/HAProxy/Nginx/Envoy、调度算法、高可用选型

### ZooKeeper 系列

- [ZooKeeper总览](分布式/Zookeeper/00-ZooKeeper总览.md)
    定位/架构/安装/配置/生产建议 + etcd 选型 + 9 篇系列导航
- 系列：00-总览 → 01-数据模型与节点 → 02-会话与Watch → 03-集群与Leader选举 → 04-ZAB协议与一致性 → 05-ACL权限控制 → 06-Java客户端API → 07-Curator → 08-运维与监控 → 09-应用场景与分布式协同

## 规划中

- **数据库**（Redis）：数据类型/持久化/高可用/缓存问题与锁
- **安全框架**：Spring Security、Apache Shiro
- **服务器问题收集**：运维小问题速查