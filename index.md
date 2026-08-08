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

## 其他语言

### Lua

- [Lua 总览](其他语言/Lua/00-Lua%20总览.md)
    Lua 5.4 全体系 15 篇：基础语法/数据类型与 table/运算符/函数/字符串与 pattern/元表/面向对象/协程/错误处理/文件包管理/三方资源/沙箱/5.4 新特性/LuaJIT
- 系列：00-总览 → 01-基础语法 → 02-数据类型与 table → 03-运算符与流程控制 → 04-函数与闭包 → 05-字符串与模式匹配 → 06-元表与元方法 → 07-面向对象 → 08-协程 → 09-错误处理 → 10-文件与包管理 → 11-三方资源（MySQL/Redis）→ 12-环境隔离与沙箱 → 13-Lua 5.4 新特性 → 14-LuaJIT 与性能优化

## 规划中

- **数据库**（Redis）：数据类型/持久化/高可用/缓存问题与锁
- **分布式**：一致性 Hash、CAP/BASE、分布式锁、事务、ID 与幂等
- **安全框架**：Spring Security、Apache Shiro
- **服务器问题收集**：运维小问题速查