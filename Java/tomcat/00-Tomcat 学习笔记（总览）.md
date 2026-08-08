---
tags: [Java, Tomcat, 索引, 学习笔记]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
来源: wolai 笔记转存（https://www.wolai.com/plyr/wq9uk2MQqaTtbaJMX3H6YA）
---

# Tomcat 学习笔记（总览）

> 本笔记体系转存自 wolai「Apache Tomcat」学习笔记，基于 **Tomcat 8.5.x** 整理。
> 官方网站：https://tomcat.apache.org/ ｜ 官方文档：https://tomcat.apache.org/tomcat-8.5-doc/index.html

![](assets/main_00.png)

## 📋 总纲

| # | 章节 | 说明 |
|---|---|---|
| 00 | 本页（总览） | 学习路线、章节索引、关联笔记 |
| 01 | [01-Tomcat 系统架构与原理剖析](01-Tomcat%20系统架构与原理剖析.md) | 浏览器访问流程、Coyote 连接器、Catalina 容器、Container 组件体系 |
| 02 | [02-Tomcat 服务器核心配置详解](02-Tomcat%20服务器核心配置详解.md) | server.xml 全标签：Server/Service/Executor/Connector/Engine/Host/Valve/Context |
| 03 | [03-Tomcat 源码构建](03-Tomcat%20源码构建.md) | 源码下载、pom.xml、IDE 导入、Bootstrap 运行配置 |
| 04 | [04-Tomcat 核心流程剖析](04-Tomcat%20核心流程剖析.md) | 启动流程（startup.sh→Bootstrap）、请求流程、源码跟踪 |
| 05 | [05-Tomcat 类加载机制剖析](05-Tomcat%20类加载机制剖析.md) | 类加载器体系（简版，wolai 原文） |
| 06 | [06-Tomcat 类加载机制详解](06-Tomcat%20类加载机制详解.md) | ⭐ 重点独立篇：双亲委派打破、类隔离、热部署原理（深度展开 05） |
| 07 | [07-Tomcat 对 HTTPS 的支持](07-Tomcat%20对%20HTTPS%20的支持.md) | HTTPS 原理、握手流程、keytool 配置 |
| 08 | [08-Tomcat 性能优化策略](08-Tomcat%20性能优化策略.md) | JVM 内存/GC 调优、线程池/连接器/IO 模式调优、动静分离 |

## 学习路线建议

1. **先读第 1 章**：建立整体架构认知（连接器 Coyote + 容器 Catalina 的分工）
2. **再读第 2 章**：server.xml 配置是日常开发/运维接触最多的部分
3. **第 4 章 + 第 3 章配合**：搭源码环境跑起来，打断点跟启动/请求流程
4. **第 5 → 6 章**：类加载是面试重点，05 简版入门后直接看深度版 [06-Tomcat 类加载机制详解](06-Tomcat%20类加载机制详解.md)
5. **第 7、8 章**：按需查阅（HTTPS 配置、性能调优实战）

## 关联笔记

- [06-Tomcat 类加载机制详解](06-Tomcat%20类加载机制详解.md) —— 类加载专题深度版（双亲委派打破、类隔离、热部署）
- **Java 类加载机制与双亲委派详解** —— JDK 侧前置知识
- **JVM 调优实战** —— JVM 参数与 GC 实战
- [01-Tomcat 系统架构与原理剖析](01-Tomcat%20系统架构与原理剖析.md) —— 架构专题

---

*来源：wolai 笔记转存（Apache Tomcat 学习笔记主页面），2026-08-08 整理*
