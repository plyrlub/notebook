---
tags: [Java, Tomcat, 类加载, 双亲委派, WebAppClassLoader]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
---

# Tomcat类加载机制剖析

> 本文是 Tomcat 学习笔记第 5 章。原笔记仅列了 JDK 三大类加载器，未展开 Tomcat 特有的类加载体系。
> **深度展开见 [06-Tomcat类加载机制详解](06-Tomcat类加载机制详解.md)**（WebAppClassLoader 与双亲委派的打破、类隔离、热部署原理，已单独成篇）。
> 关联笔记：[00-Tomcat总览](00-Tomcat总览.md)、**Java类加载机制与双亲委派详解**（见知识库）

## 📋 总纲

1. Tomcat 中的类加载器（原文）
2. 补充：Tomcat 类加载器体系全貌（指向详解笔记）

---

## 1. Tomcat 中类加载器（原文）

Tomcat 基于 JDK 的类加载器体系：

| 类加载器 | 加载范围 |
|---|---|
| **引导类加载器**（Bootstrap） | `rt.jar`（JDK 核心类） |
| **扩展类加载器**（Extension） | `ext/*.jar`（JDK 扩展） |
| **系统类加载器**（System/AppClassLoader） | `classpath` 下的类 |

当然可以**继承系统类加载器，来创建自定义类加载器**——Tomcat 正是这么做的。

---

## 2. 补充：Tomcat 类加载器体系全貌

> 原文到此为止。原笔记对类加载只做了引出，**完整机制（为什么打破双亲委派、WebAppClassLoader 加载顺序、java.* 保护、热部署原理、易错点、面试 Q&A）已整理在 [06-Tomcat类加载机制详解](06-Tomcat类加载机制详解.md)**，本节仅列体系骨架：

```
Bootstrap（JVM 自带，java.* 核心类）
 └── Platform / Extension（JDK 扩展）
      └── Common ClassLoader（$CATALINA_HOME/lib，容器与所有应用共享）
           ├── Catalina ClassLoader（Tomcat 容器内部类，对应用不可见）
           └── Shared ClassLoader（所有应用共享，默认合并到 Common）
                └── WebAppClassLoader（每个 Web 应用一个，WEB-INF/classes + WEB-INF/lib）
```

**核心结论**（详见 [06-Tomcat类加载机制详解](06-Tomcat类加载机制详解.md)）：

1. Tomcat **打破双亲委派**：WebAppClassLoader **先自己后父**（先加载 WEB-INF 的类），目的是**类隔离**（不同应用可共存不同版本 jar）
2. **java.\* 不受影响**：WebAppClassLoader 对 java.* 有硬过滤，仍由 Bootstrap 加载（底线不破）
3. **热部署原理**：检测到 WEB-INF 变化 → 新建 WebAppClassLoader 重新加载，旧类无引用后回收

---

## 面试追问 Q&A

### Q1：Tomcat 类加载和 JDK 双亲委派什么关系？

答：JDK 标准是先父后子；Tomcat 的 WebAppClassLoader **先子后父**（先找自己 WEB-INF，再委托父），这是为类隔离而打破双亲委派。但 java.* 和容器 API 仍走父加载器。

### Q2：Tomcat 为什么必须打破双亲委派？

答：多个 Web 应用可能依赖同一 jar 的不同版本（如 Spring 4 vs Spring 5）。若完全双亲委派，先加载的版本会垄断类；打破后每个应用独立 WebAppClassLoader，版本互不干扰。

---

> 深度内容并入 [06-Tomcat类加载机制详解](06-Tomcat类加载机制详解.md)
