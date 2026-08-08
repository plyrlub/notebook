# 📚 笔记分享库

个人学习笔记整理 · 面向后端开发者（Java / Python / Lua）

> **网页版**：https://plyrlub.github.io/notebook/ ｜ **仓库**：[GitHub](https://github.com/plyrlub/notebook) ｜ [Gitee](https://gitee.com/plyr/notebook)

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
    基于 8.5.x：架构/Coyote/Catalina、server.xml 全标签、源码构建、启动流程、类加载、HTTPS、性能优化 + 类加载深度篇

---

## 服务器

### Nginx

- [Nginx 学习笔记（总览）](Nginx/00-Nginx%20学习笔记（总览）.md)
    基于 1.30.4：基础认知/配置/核心机制/反向代理/安全/性能/OpenResty 8 大主题
- 覆盖：基础认知、配置基础、核心机制、反向代理与负载均衡、安全与传输、高级与优化、OpenResty 与 Lua、专题补充（38 篇）

## 通用技术

### Lua

- [Lua 语言详解](通用技术/Lua%20语言详解.md)
    Lua 5.4 全体系：8 种数据类型/table 三形态/运算符/流程控制/table+String API/可变参数/元表/面向对象/协程/文件/包管理/MySQL+Redis/沙箱环境隔离

## 规划中

- **数据库**（Redis）：数据类型/持久化/高可用/缓存问题与锁
- **分布式**：一致性 Hash、CAP/BASE、分布式锁、事务、ID 与幂等
- **安全框架**：Spring Security、Apache Shiro
- **服务器问题收集**：运维小问题速查