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

- [Java SPI 机制详解](Java/Java%20SPI%20机制详解.md)
    JDK / Spring / Dubbo / Servlet 四机制全覆盖
- [Java volatile 详解](Java/Java%20volatile%20详解.md)
    JMM/硬件链路、MESI、内存屏障、假共享、面试 10 问
- [Java 反射详解](Java/Java%20反射详解.md)
    核心 API/为什么慢、缓存 → MethodHandle → LambdaMetafactory 四层优化、面试 8 问

### JVM

- [Java GC 详解](Java/Java%20GC%20详解.md)
    判活/算法/收集器演进（Serial→G1→ZGC）、三色标记、SafePoint、面试 11 问

### Java 框架

- [Tomcat 学习笔记（总览）](Java/tomcat/00-Tomcat%20学习笔记（总览）.md)
    基于 8.5.x：架构/Coyote/Catalina、server.xml 全标签、源码构建、启动流程、类加载、HTTPS、性能优化 7 大章 + 类加载深度篇

### 构建工具

- [构建工具总览·Maven vs Gradle 选型对比](Java/构建工具/00-构建工具总览·Maven%20vs%20Gradle%20选型对比.md)
    两大构建工具定位、核心差异与选型建议
- [Maven 总览](Java/构建工具/Maven/00-Maven%20总览.md)
    Maven 进阶 5 篇：依赖与仓库/生命周期与插件/私服与测试/版本与灵活构建
- [Gradle 学习笔记（总览）](Java/构建工具/Gradle/Gradle%20学习笔记（总览）.md)
    Gradle 核心模型：Task/生命周期/DSL/依赖冲突/多项目构建/性能优化

## 通用技术

### 前后端缓存

- [前后端缓存总览](通用技术/前后端缓存/00-前后端缓存总览.md)
    省什么坐标系（请求/流量/计算/轮询）+ 完整决策表 + 后端缓存导航桥接表（Redis 三大问题/多级缓存/一致性）
- [客户端缓存详解](通用技术/前后端缓存/01-客户端缓存详解.md)
    TTL / SWR / 防抖 / 请求合并，前端主缓存层
- [协商缓存详解](通用技术/前后端缓存/02-协商缓存详解.md)
    ETag/304 + Redis hash 设计 + 适用边界 + 归属表（静态归 CDN/动态归后端/实时别用）

## 服务器

### Nginx

- [Nginx 学习笔记（总览）](Nginx/00-Nginx%20学习笔记（总览）.md)
    基于 1.30.4：基础认知/配置/核心机制/反向代理/安全/性能/OpenResty 8 大主题（38 篇）

## 其他语言

### Lua

- [Lua 总览](其他语言/Lua/00-Lua%20总览.md)
    Lua 5.4 全体系 15 篇：基础语法/数据类型与 table/运算符/函数/字符串与 pattern/元表/面向对象/协程/错误处理/文件包管理/三方资源/沙箱/5.4 新特性/LuaJIT
- 系列：00-总览 → 01-基础语法 → 02-数据类型与 table → 03-运算符与流程控制 → 04-函数与闭包 → 05-字符串与模式匹配 → 06-元表与元方法 → 07-面向对象 → 08-协程 → 09-错误处理 → 10-文件与包管理 → 11-三方资源（MySQL/Redis）→ 12-环境隔离与沙箱 → 13-Lua 5.4 新特性 → 14-LuaJIT 与性能优化

## 分布式

_（待分享：一致性 Hash / CAP-BASE / 分布式锁 / 事务 / ID 与幂等）_

## 安全框架

_（待分享：Spring Security / Apache Shiro）_

## LLM / AI

_（待分享）_