---
tags: [Java, Tomcat, 类加载, 双亲委派, WebAppClassLoader, 容器]
创建日期: 2026-08-07
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
来源: wolai 笔记转存第 5 章深度展开（[tomcat-classloader](tomcat-classloader.md)）
aliases: [Tomcat 类加载机制详解]
---

# Tomcat 类加载机制详解（双亲委派的打破与类隔离）

> 本篇聚焦 Tomcat 的**类加载机制**（WebAppClassLoader 与双亲委派的关系），是 [tomcat-classloader](tomcat-classloader.md) 的深度展开篇。
> 前置知识：**Java 类加载机制与双亲委派详解**（见知识库）（JDK 侧的双亲委派模型）
> 系列索引：[tomcat-overview](tomcat-overview.md)

## 📋 总纲

1. Tomcat 为什么必须打破双亲委派：类隔离需求
2. 目录结构决定了类加载顺序：lib / classes / 各 Web 应用
3. 类加载器体系：Common / Catalina / Shared / WebAppClassLoader 层次
4. WebAppClassLoader 的加载顺序（先自己后父，与 JDK 相反）
5. java.* 为什么不会被重复加载（双亲委派的底线）
6. 热部署原理：ClassLoader 换新 + 旧类回收
7. 常见误区
8. 面试追问 Q&A
9. 与 JDK 双亲委派对比表

---

## 1. 为什么必须打破双亲委派

**需求**：一个 Tomcat 可以部署多个 Web 应用，每个应用**可能用不同版本的同一个 jar**（如 A 应用用 Spring 4、B 应用用 Spring 5）。

**若完全遵守双亲委派**：类加载请求全部向上委托，第一个加载了 Spring 4 的应用类加载器会"垄断"该类，B 应用想用 Spring 5 会拿到同一个类（版本错误）→ 冲突。

**打破方式**：每个 Web 应用一个独立的 `WebAppClassLoader`，**优先自己加载**（先找自己的 WEB-INF/classes 和 WEB-INF/lib），自己找不到才委托父加载器——与标准双亲委派"先父后子"**相反**。

---

## 2. 目录结构与类加载顺序

```
tomcat/
├── lib/                    ← 全局共享（Common 类加载器加载）
│   ├── servlet-api.jar     ← 容器提供的 API，所有应用共享
│   └── ...
├── conf/
└── webapps/
    ├── appA/
    │   ├── WEB-INF/
    │   │   ├── classes/    ← 应用自己的 class（优先加载）
    │   │   └── lib/        ← 应用自己的 jar（优先加载，可与其他应用版本不同）
    │   └── ...
    └── appB/
        └── WEB-INF/...     ← 独立隔离
```

**加载优先级（WebAppClassLoader 视角）**：
① 自己 WEB-INF/classes 和 WEB-INF/lib（**先看自己的**）
② 委托父加载器（JVM 类、Tomcat 共享类）
③ 都找不到 → ClassNotFoundException

**注意例外**：`java.*` 和 `javax.servlet.*`（容器 API）**不走这个顺序**——见第 5 节。

---

## 3. 类加载器体系层次

| 加载器 | 加载范围 | 说明 |
|---|---|---|
| Bootstrap（JVM 自带） | `java.*` 核心类 | 最顶层，C++ 实现 |
| Platform / Extension | JDK 扩展 | JDK 9 后为 Platform |
| Common ClassLoader | `$CATALINA_HOME/lib` | 容器与所有应用共享（含 servlet-api） |
| Catalina ClassLoader | Tomcat 容器内部类 | 对应用不可见 |
| Shared ClassLoader | 所有应用共享（可选） | 默认合并到 Common |
| **WebAppClassLoader** | 单个应用的 WEB-INF | **每个 Web 应用一个实例**，核心所在 |

**委托链**：WebAppClassLoader → Shared → Catalina → Common → Platform → Bootstrap

---

## 4. WebAppClassLoader 加载顺序（与 JDK 相反）

**JDK 标准双亲委派**：先父后子（父加载不了才自己加载）

**Tomcat WebAppClassLoader**：先子后父（自己找不到才委托父）——**这就是"打破双亲委派"**

```
WebAppClassLoader.loadClass(name):
  1. 查自己已加载的类（缓存）
  2. findLoadedClass → 看父加载器是否已加载（避免重复加载）
  3. 系统类（java.*）→ 直接交 Bootstrap（例外，见第 5 节）
  4. 过滤（javax.servlet.* 等容器 API → 交父）
  5. 自己 findClass：WEB-INF/classes → WEB-INF/lib
  6. 找不到 → 委托父加载器
```

**对比表：JDK vs Tomcat 委托顺序**

| 步骤 | JDK 标准模型 | Tomcat WebAppClassLoader |
|---|---|---|
| 1 | 查缓存 | 查缓存 |
| 2 | **委托父加载** | 查父是否已加载过 |
| 3 | 父失败才自己加载 | **自己先加载**（WEB-INF） |
| 4 | —— | 自己失败才委托父 |
| 结果 | 先父后子 | **先子后父**（打破） |

---

## 5. java.* 为什么不会被重复加载

**问题**：Tomcat 打破了双亲委派，那用户写个 `java.lang.String` 或应用里塞个 `java.*` 类，会不会被 WebAppClassLoader 抢先加载、污染核心类？

**答案：不会**。WebAppClassLoader 有**系统类保护**机制：
- 凡是 `java.*` 开头的类，**直接交给 Bootstrap 加载**（代码第 3 步，硬编码过滤）
- 目的：保证 JVM 核心类永远唯一、安全，**防止用户自定义 java.* 覆盖核心类**（这和双亲委派的初衷一致）
- 这也是面试高频题："Tomcat 打破了双亲委派，那 java.* 类还会被重复加载吗？"——答：不会，WebAppClassLoader 对 java.* 有硬过滤，仍由 Bootstrap 加载

**打破的边界**：Tomcat 打破的只是"**应用自己的类**"的委派顺序（为了隔离），**核心 Java 类这条底线没破**。

---

## 6. 热部署原理（关联）

- Tomcat 检测到 WEB-INF/classes 或 lib 变化 → **新建一个 WebAppClassLoader 实例** → 重新加载应用类
- 新 ClassLoader 加载出**全新的 Class 对象**（即使类名相同）
- 旧 ClassLoader 及其加载的类，在**没有引用后**被 GC 回收（元空间）
- **坑**：若旧类被外部持有引用（如静态变量、线程局部），旧 ClassLoader 无法回收 → 元空间泄漏（经典问题）
- 详细热部署机制见 **Java 类加载机制与双亲委派详解**（见知识库） 第 6 节（类唯一性 + 自定义 ClassLoader 代码）

---

## 7. 常见误区

1. **认为 Tomcat 完全遵守双亲委派**——错了，WebAppClassLoader 是"先子后父"，为隔离而打破
2. **认为打破后 java.* 也能被覆盖**——错了，java.* 有硬过滤，永远 Bootstrap 加载
3. **混淆 Common 和 WebApp 的职责**——lib 全局共享、WEB-INF 应用隔离，层级不同
4. **认为所有应用共享所有类**——每个 WebAppClassLoader 独立，同名不同版本 jar 可以共存
5. **热部署后旧类立即消失**——旧 ClassLoader 要等无引用才被回收，有引用就泄漏

---

## 8. 面试追问 Q&A

### 8.1 Tomcat 为什么打破双亲委派？

答：为了**类隔离**——多个 Web 应用可能用不同版本的同一 jar，若严格双亲委派，先加载的应用会垄断该类，其他应用无法用自己版本。每个应用独立的 WebAppClassLoader 优先自己加载，实现版本隔离。

### 8.2 WebAppClassLoader 的加载顺序？

答：先查缓存 → 查父是否已加载 → 系统类（java.*）交 Bootstrap → 容器 API（servlet.*）交父 → 自己加载 WEB-INF/classes 和 lib → 找不到才委托父。整体是"先子后父"，与 JDK 标准双亲委派相反。

### 8.3 Tomcat 打破双亲委派，java.* 类会被重复加载吗？

答：不会。WebAppClassLoader 对 `java.*` 有硬编码过滤，直接交给 Bootstrap 加载，保证核心类唯一安全。Tomcat 打破的只是应用自定义类的委派顺序，JVM 核心类这条底线始终没破。

### 8.4 两个 Web 应用能用不同版本的 Spring 吗？

答：能。每个应用有独立 WebAppClassLoader，各自优先加载自己 WEB-INF/lib 里的 Spring 版本，互不干扰。这也是"先子后父"隔离设计的目的。

### 8.5 Tomcat 热部署为什么可能内存泄漏？

答：热部署创建新 WebAppClassLoader 加载新类，旧加载器要无引用才被 GC。若旧类被静态变量、线程局部等外部持有，旧加载器无法回收，其加载的类常驻元空间 → 泄漏。这也是反复热部署后元空间暴涨的原因。

---

## 9. 与 JDK 双亲委派对比总表

| 维度 | JDK 标准模型 | Tomcat WebAppClassLoader |
|---|---|---|
| 委托方向 | **先父后子** | **先子后父**（打破） |
| 目标 | 类唯一性 + 安全 | 类隔离（多应用多版本） |
| java.* 处理 | Bootstrap 加载 | 硬过滤 → Bootstrap（底线不破） |
| 核心 API（servlet） | —— | 父加载器加载，应用不可覆盖 |
| 应用自己的类 | Application 加载 | 各自 WebApp 加载 |
| 重载 | 不支持 | 支持（换 ClassLoader 实例） |

---

## 参考

- Tomcat 官方架构文档（Class Loader HOW-TO）
- 关联笔记：**Java 类加载机制与双亲委派详解**（见知识库）（JDK 侧机制）、[java-spi](java-spi.md)（另一种打破方式：线程上下文类加载器）
