---
tags: [Java, Tomcat, 索引, 学习笔记]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
来源: wolai 笔记转存（https://www.wolai.com/plyr/wq9uk2MQqaTtbaJMX3H6YA）
aliases: [Tomcat 学习笔记（总览）]
---

# Tomcat 学习笔记（总览）

> 本笔记体系转存自 wolai「Apache Tomcat」学习笔记，基于 **Tomcat 8.5.x** 整理。
> 官方网站：https://tomcat.apache.org/ ｜ 官方文档：https://tomcat.apache.org/tomcat-8.5-doc/index.html

![](assets/main_00.png)

## 📋 总纲

| # | 章节 | 说明 |
|---|---|---|
| 00 | 本页（总览） | 学习路线、章节索引、关联笔记 |
| 01 | [tomcat-architecture](tomcat-architecture.md) | 浏览器访问流程、Coyote 连接器、Catalina 容器、Container 组件体系 |
| 02 | [tomcat-server-config](tomcat-server-config.md) | server.xml 全标签：Server/Service/Executor/Connector/Engine/Host/Valve/Context |
| 03 | [tomcat-source-build](tomcat-source-build.md) | 源码下载、pom.xml、IDE 导入、Bootstrap 运行配置 |
| 04 | [tomcat-core-process](tomcat-core-process.md) | 启动流程（startup.sh→Bootstrap）、请求流程、源码跟踪 |
| 05 | [tomcat-classloader](tomcat-classloader.md) | 类加载器体系（简版，wolai 原文） |
| 06 | [tomcat-classloader-deepdive](tomcat-classloader-deepdive.md) | ⭐ 重点独立篇：双亲委派打破、类隔离、热部署原理（深度展开 05） |
| 07 | [tomcat-https](tomcat-https.md) | HTTPS 原理、握手流程、keytool 配置 |
| 08 | [tomcat-performance-tuning](tomcat-performance-tuning.md) | JVM 内存/GC 调优、线程池/连接器/IO 模式调优、动静分离 |

## 学习路线建议

1. **先读第 1 章**：建立整体架构认知（连接器 Coyote + 容器 Catalina 的分工）
2. **再读第 2 章**：server.xml 配置是日常开发/运维接触最多的部分
3. **第 4 章 + 第 3 章配合**：搭源码环境跑起来，打断点跟启动/请求流程
4. **第 5 → 6 章**：类加载是面试重点，05 简版入门后直接看深度版 [tomcat-classloader-deepdive](tomcat-classloader-deepdive.md)
5. **第 7、8 章**：按需查阅（HTTPS 配置、性能调优实战）

## 关联笔记

- [tomcat-classloader-deepdive](tomcat-classloader-deepdive.md) —— 类加载专题深度版（双亲委派打破、类隔离、热部署）
- **Java 类加载机制与双亲委派详解**（见知识库） —— JDK 侧前置知识
- **JVM 调优实战**（见知识库） —— JVM 参数与 GC 实战
- [tomcat-architecture](tomcat-architecture.md) —— 架构专题

---

*来源：wolai 笔记转存（Apache Tomcat 学习笔记主页面），2026-08-08 整理*
