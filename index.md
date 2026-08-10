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

### Linux

- [Linux总览](Linux/00-Linux总览.md)
    Ubuntu/CentOS 双版本：用户管理与登录授权/文件权限/常用命令/系统优化与性能排查/安全加固 5 篇
- 系列：00-Linux总览 → 01-用户管理与登录授权 → 02-文件权限与属主 → 03-常用命令速查 → 04-系统优化与性能排查 → 05-安全加固

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

## 规划中

- **数据库**（Redis）：数据类型/持久化/高可用/缓存问题与锁
- **安全框架**：Spring Security、Apache Shiro
- **服务器问题收集**：运维小问题速查

## DevOps

### CI/CD

- [CI/CD 学习笔记（总览）](CI-CD/00-CI-CD%20学习笔记（总览）.md)
    10 章系统学习：认知地基/工具选型/Actions/GitLab/Jenkins/容器化/K8s 部署/DevSecOps/可观测性 + S1~S12 补充专题（Secret/SBOM/Feature Flag/开源设施部署等）+ 可运行 Demo
- [面试题集锦](CI-CD/面试题集锦.md)
    8 大领域 45 道题（含难度与参考答案，高频题标 🔥）
- 系列：00-总览 → 01-认知地基 → 02-环境与前置技能 → 03-工具选型与对比 → 04-核心工具深入 → 05-构建与测试 → 06-容器化与制品管理 → 07-部署与发布策略 → 08-安全与质量门禁 → 09-监控可观测性与回滚 → 10-进阶与工程化
- 补充专题（12 篇）：S1-Secret管理 / S2-成本与配额 / S3-DORA四指标 / S4-供应链安全SBOM / S5-流水线自身安全 / S6-数据库迁移 / S7-FeatureFlag解耦部署 / S8-Lua场景CICD / S9-质量安全扫描集成 / S10-Pipeline各环节最佳实践 / S11-包仓库Nexus-Harbor-GitLabRegistry / S12-CICD开源设施部署指南