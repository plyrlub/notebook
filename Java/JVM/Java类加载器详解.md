---
tags: [Java, JVM, 类加载器, ClassLoader, 机制]
创建日期: 2026-08-07
状态: ✅ 已归档（01-学习/Java/JVM）
归属: 01-学习/Java/JVM
---

# Java类加载器详解（职责 / API / 自定义 / 场景 / 最佳实践）

## 📋 总纲

1. 类加载器是什么：定位 + 与 Class 对象的关系（含数组类特殊机制）
2. 各加载器职责详解：Bootstrap / Platform / Application / 自定义——逐个讲
3. 核心 API 逐个讲：loadClass / findClass / defineClass / resolveClass / getParent
4. 自定义类加载器实战：目录加载 / 网络加载 / 字节码加密解密
5. 常见使用场景：热部署、插件化、依赖隔离、Spring 的 TCCL
6. 线程上下文类加载器（TCCL）：原理与"反向"原因
7. 注意点与最佳实践：类卸载、元空间泄漏、同名类陷阱
8. 面试追问 Q&A
9. 参考

> 前置：类加载的五个阶段与双亲委派模型见 [Java类加载机制与双亲委派详解](Java类加载机制与双亲委派详解.md)；本篇聚焦"加载器"本身。

---

## 1. 类加载器是什么

### 1.1 定位

**类加载器（ClassLoader）**：负责"加载"阶段的核心组件——根据**全限定名**找到或生成类的字节码，交给 JVM 定义出 `Class` 对象。

```java
// Class 对象里持有它的加载器引用
public final class Class<T> {
    private final ClassLoader classLoader;   // 谁加载的我
    public ClassLoader getClassLoader() { ... }
}
```

### 1.2 与 Class 对象的关系（关键）

**类的唯一性 = ClassLoader + 全限定名**——同一个全限定名被不同加载器加载，得到两个互不相干的 Class 对象（详见 [Java类加载机制与双亲委派详解](Java类加载机制与双亲委派详解.md) 第 5 节）。

### 1.3 数组类的特殊机制（面试冷门考点）

数组类**不是**通过 ClassLoader 创建的，而是 JVM 在需要时**自动创建**：

| 数组类型 | 类加载器 | 说明 |
|---|---|---|
| 引用类型数组（如 `String[]`） | 与**组件类型**的加载器一致 | `new String[10]` 的加载器 = String 的加载器 |
| 基本类型数组（如 `int[]`） | **无**，`getClassLoader()` 返回 null | JVM 内置 |

```java
String[].class.getClassLoader();   // = String.class.getClassLoader() → null（Bootstrap）
int[].class.getClassLoader();      // null（基本类型数组没有加载器）
```

---

## 2. 各加载器职责详解

### 2.1 启动类加载器 Bootstrap

| 项 | 说明 |
|---|---|
| 职责 | 加载 JVM 核心类：`java.*`、`javax.*` 核心部分（JDK 8 的 rt.jar） |
| 实现 | **C++ 实现**，不是 ClassLoader 的子类 |
| Java 中表示 | **null**（`String.class.getClassLoader()` 返回 null） |
| 来源 | `<JAVA_HOME>/lib`、`-Xbootclasspath` 指定的路径 |
| 权限 | 最高——核心类被它加载后，用户无法覆盖（安全基石） |

```java
System.out.println(String.class.getClassLoader());   // null → Bootstrap
System.out.println(Object.class.getClassLoader());   // null
```

**易错点**：看到 `getClassLoader()` 返回 null **不要以为"没有加载器"**——是 Bootstrap 在 Java 层不可见，用 null 表示。

### 2.2 平台类加载器 Platform（JDK 9+） / 扩展类加载器 Extension（JDK 8）

| 项 | 说明 |
|---|---|
| JDK 8 | 扩展类加载器 Extension：加载 `<JAVA_HOME>/lib/ext` 下的扩展类 |
| JDK 9+ | 更名**平台类加载器 Platform**：加载 JDK 的模块化类（如 `java.sql`、`java.xml` 等模块） |
| 实现 | Java 实现，`ClassLoader` 子类 |
| 定位 | Bootstrap 之下、Application 之上 |

```java
// JDK 9+：平台加载器
System.out.println(java.sql.DriverManager.class.getClassLoader());
// jdk.internal.loader.ClassLoaders$PlatformClassLoader...
```

**版本差异要点**：JDK 9 模块化后 Extension 没了，但"中间层"职责延续为 Platform；`-Djava.ext.dirs` 机制也被移除。

### 2.3 应用类加载器 Application / 系统类加载器 System

| 项 | 说明 |
|---|---|
| 职责 | 加载 **classpath**（用户自己写的类、第三方 jar） |
| 实现 | Java 实现，`ClassLoader` 子类 |
| 地位 | **默认加载器**——没有自定义加载器时，用户类都由它加载 |
| 获取 | `ClassLoader.getSystemClassLoader()` |

```java
System.out.println(MyClass.class.getClassLoader());
// jdk.internal.loader.ClassLoaders$AppClassLoader...
```

### 2.4 自定义类加载器

| 项 | 说明 |
|---|---|
| 职责 | 从**非标准来源**加载：网络、数据库、加密字节码、动态生成 |
| 实现 | 继承 `ClassLoader`，重写 `findClass()`（第 4 节详解） |
| 典型 | Tomcat 的 WebAppClassLoader、热部署加载器、插件框架 |

**层级总结**（JDK 9+）：

```
Bootstrap（C++，null）
   └── Platform（JDK 模块类）
         └── Application（classpath）
               └── 自定义加载器（可多层）
```

---

## 3. 核心 API 逐个讲

| API | 作用 | 何时用 | 易错点 |
|---|---|---|---|
| `loadClass(name)` | 入口：加载类（含**双亲委派逻辑**） | 外部调用加载 | **默认不初始化**（不执行静态块） |
| `findClass(name)` | **自己找**类字节码并 defineClass | **自定义加载器重写它** | 重写这个而不是 loadClass！ |
| `defineClass(name, bytes, off, len)` | 把字节码变成 Class 对象 | findClass 内部调用 | 字节码必须合法，否则 ClassFormatError |
| `resolveClass(c)` | 完成类的**链接**（可选） | 一般不需要主动调 | loadClass 的 resolve 参数默认 false |
| `getParent()` | 拿父加载器 | 查看委托链 | Bootstrap 的 parent 是 null |
| `getSystemClassLoader()` | 拿应用类加载器 | 自定义加载器的默认父 | —— |

### 3.1 loadClass vs findClass（面试重点）

```java
protected Class<?> loadClass(String name, boolean resolve) {
    // ① 查缓存 → ② 委托父（双亲委派）→ ③ 父失败才 findClass
    Class<?> c = findLoadedClass(name);
    if (c == null) {
        // ... 委托 parent.loadClass ...
        if (c == null) {
            c = findClass(name);   // ← 自定义加载器只需重写这个
        }
    }
    return c;
}

protected Class<?> findClass(String name) {
    // 默认实现抛 ClassNotFoundException——子类重写
}
```

**结论**：
a. 自定义加载器**重写 findClass**（保留双亲委派给核心类）
b. 只有想**打破双亲委派**才重写 loadClass（Tomcat 的做法）
c. `findLoadedClass` 是缓存检查——**同一个加载器不会重复加载同名类**

### 3.2 defineClass 细节

```java
// 把字节数组转为 Class 对象（findClass 的标准收尾）
byte[] bytes = readClassBytes(path);
return defineClass(name, bytes, 0, bytes.length);
```

**注意**：
a. 字节码必须符合 JVM 规范（可先 `verify`，defineClass 默认做验证）
b. 同一加载器重复 defineClass 同名类 → `LinkageError`
c. 类加载是**线程安全**的：JVM 保证同一加载器同一类名只定义一次（有锁）

---

## 4. 自定义类加载器实战

### 4.1 从目录加载（基础模板）

```java
public class DirClassLoader extends ClassLoader {
    private final String classDir;

    public DirClassLoader(String classDir, ClassLoader parent) {
        super(parent);                    // 父默认给 Application
        this.classDir = classDir;
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        try {
            String path = classDir + "/" + name.replace('.', '/') + ".class";
            byte[] bytes = java.nio.file.Files.readAllBytes(java.nio.file.Path.of(path));
            return defineClass(name, bytes, 0, bytes.length);   // 字节码 → Class
        } catch (Exception e) {
            throw new ClassNotFoundException(name, e);
        }
    }
}

// 使用
DirClassLoader cl = new DirClassLoader("/tmp/classes", ClassLoader.getSystemClassLoader());
Class<?> clazz = cl.loadClass("com.example.Plugin");
Object instance = clazz.getDeclaredConstructor().newInstance();
```

**要点**：
a. 构造器传 parent——**委托链由此建立**
b. 只重写 findClass → `java.*` 等核心类仍走双亲委派，安全
c. loadClass 默认**不初始化**，需要静态块执行时用 `Class.forName(name, true, cl)`

### 4.2 网络加载（远程类）

```java
public class NetClassLoader extends ClassLoader {
    private final String baseUrl;    // 如 http://host/classes/

    protected Class<?> findClass(String name) throws ClassNotFoundException {
        try {
            String url = baseUrl + name.replace('.', '/') + ".class";
            byte[] bytes = new java.net.URL(url).openStream().readAllBytes();
            return defineClass(name, bytes, 0, bytes.length);
        } catch (Exception e) {
            throw new ClassNotFoundException(name, e);
        }
    }
}
```

**场景**：远程插件分发、代码热更新——类字节流来源是网络。

### 4.3 字节码加密 / 解密加载

```java
public class EncryptedClassLoader extends ClassLoader {
    private final byte[] key;

    protected Class<?> findClass(String name) throws ClassNotFoundException {
        byte[] encrypted = readEncrypted(name);       // 读加密后的 .class
        byte[] decrypted = xorDecrypt(encrypted, key); // 解密
        return defineClass(name, decrypted, 0, decrypted.length);
    }
}
```

**场景**：商业软件防反编译——class 文件加密存储，运行时解密加载。

---

## 5. 常见使用场景

| 场景 | 怎么做 | 代表 |
|---|---|---|
| **热部署** | 监控 class 变化 → 新建 ClassLoader 实例重载 | Tomcat、Spring Boot devtools、JRebel |
| **插件化** | 每个插件一个加载器，隔离 + 动态加载 | Eclipse/IDEA 插件、SPI 框架 |
| **依赖隔离** | 不同模块用不同加载器加载不同版本 | Tomcat 多应用、OSGi、Java 9 模块 |
| **字节码加密** | 加密 class，自定义加载器解密 | 商业软件 |
| **动态生成类** | 加载运行期生成的字节码 | CGLIB/ASM 产物、Groovy 脚本编译结果 |
| **TCCL 反向加载** | 框架代码（Bootstrap 侧）加载用户实现 | Spring、JDBC、日志桥接 |

**关联**：
- Tomcat 的类隔离见 [06-Tomcat类加载机制详解](../框架/网络底座/Web服务器/tomcat/06-Tomcat类加载机制详解.md)
- 动态生成字节码见 [Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)

---

## 6. 线程上下文类加载器（TCCL）

### 6.1 为什么需要

**矛盾**：核心接口（如 `DriverManager`）由 Bootstrap 加载，但**实现**（JDBC 驱动）在 classpath——Bootstrap 按双亲委派**看不到** classpath，标准委托链断了。

**解决**：给线程挂一个"上下文类加载器"（默认 = Application），让 Bootstrap 侧的代码**反向**用它加载实现类。

### 6.2 机制

```java
// 原理：加载器存在线程私有数据里，跟线程绑定
Thread.currentThread().getContextClassLoader();   // 取
Thread.currentThread().setContextClassLoader(cl); // 设

// Spring 获取（经典用法）
ClassLoader cl = Thread.currentThread().getContextClassLoader();
```

**继承链**：线程没设置时，**继承父线程**的上下文类加载器（默认链：main → Application）。

### 6.3 使用场景

a. **JDBC**：`DriverManager`（Bootstrap 侧）通过 TCCL 加载 `com.mysql.cj.jdbc.Driver`
b. **Spring**：从容器（父加载器侧）加载用户配置类
c. **日志桥接**（slf4j 等）：找绑定实现
d. **JNDI**：加载 JNDI 实现

> ⚠️ TCCL 是**打破双亲委派**的方式之一（父借子），与 Tomcat 的"先子后父"方向不同——详见 [Java类加载机制与双亲委派详解](Java类加载机制与双亲委派详解.md) 第 4 节对比表。

---

## 7. 注意点与最佳实践

### 7.1 类卸载条件（内存相关）

- **类卸载 = 该类的加载器不可达（可被 GC）**——不是类没引用就行，是**加载器**没引用
- 热部署反复换加载器 → 旧加载器被静态引用持有 → **元空间泄漏**（经典线上问题）
- 排查见 [JVM调优实战](JVM调优实战.md) 3.6 元空间溢出（jstat -class 看 Loaded 数持续增长）

### 7.2 同名类陷阱

- 两个加载器加载同名类 = 两个类型，`instanceof` 为 false、强转抛 `ClassCastException`（"X cannot be cast to X"）
- 定位：打印 `clazz.getClassLoader()` 看是不是被不同加载器加载

### 7.3 加载顺序与可见性（最佳实践清单）

a. **自定义加载器只重写 findClass**，除非明确要打破双亲委派
b. **类加载器不要缓存 Class 引用在静态字段**（防泄漏）
c. **插件/热部署场景**：用完的加载器主动置空引用，配合元空间监控
d. **高版本 JDK 注意**：JDK 9+ 模块系统下，自定义加载器加载 `java.*` 会被拒绝（强封装）
e. **线程上下文类加载器要 restore**：框架里设置完 TCCL 记得用完还原（try-finally），避免"污染"后续线程
f. **loadClass 不初始化**：需要执行静态块用 `Class.forName(name, true, loader)`
g. **调试技巧**：`-XX:+TraceClassLoading` 看类被谁加载；`clazz.getClassLoader()` 打印加载器

### 7.4 性能注意

- 类加载是**一次性的**（加载后缓存），业务热路径无感
- 但**反复 new 加载器 + 重复加载**（热部署频繁）会显著消耗元空间和 CPU——节流：只在真正变更时重载

---

## 8. 面试追问 Q&A

### 8.1 类加载器有哪些？各自职责？

答：Bootstrap（C++，null，加载 java.* 核心类）、Platform/Extension（JDK 模块/扩展类）、Application（classpath 用户类，默认加载器）、自定义（网络/加密/热部署等特殊来源）。层级：Bootstrap → Platform → Application → 自定义。

### 8.2 自定义类加载器重写 findClass 还是 loadClass？

答：默认重写 **findClass**——loadClass 里的双亲委派逻辑（缓存→委托父→自己）是 JVM 设计好的，重写 findClass 保留它对核心类的委派；只有要**打破双亲委派**（如 Tomcat 隔离）才重写 loadClass。

### 8.3 defineClass 是干嘛的？

答：把字节数组转换为 Class 对象的底层方法，自定义加载器的 findClass 用它收尾。字节码必须合法；同一加载器重复定义同名类抛 LinkageError。

### 8.4 数组类的类加载器是什么？

答：数组类不是 ClassLoader 创建的，JVM 自动创建。引用类型数组的加载器与组件类型一致；基本类型数组没有加载器，getClassLoader() 返回 null。

### 8.5 什么是线程上下文类加载器？为什么需要？

答：线程私有的 ClassLoader 引用（默认 Application）。因为核心接口由 Bootstrap 加载但实现类在 classpath（Bootstrap 看不到），框架代码通过 TCCL 反向加载实现——JDBC、Spring、日志桥接都用它。本质是打破双亲委派的一种方式。

### 8.6 类什么时候被卸载？

答：**加载它的类加载器不可达（可被 GC）时**，该类才能被卸载。所以热部署反复新建加载器，若旧加载器被静态引用持有，类无法卸载 → 元空间泄漏。

### 8.7 ClassLoader.loadClass 和 Class.forName 区别？

答：loadClass 默认只加载不初始化（不执行静态块）；forName 默认会初始化（可传 false 关掉）。需要触发静态块（如 JDBC 驱动注册）用 forName。

### 8.8 怎么让两个加载器加载的"同名类"不冲突？

答：天然不冲突——不同加载器的同名类本来就是两个类型，各自使用各自命名空间。冲突只出现在"一个代码里强转另一个加载器的实例"时（ClassCastException）。隔离设计（Tomcat/OSGi）正是利用这点。

---

## 9. 参考

- Oracle：ClassLoader API 文档（java.lang.ClassLoader）
- JavaGuide《类加载器详解（重点）》
- 关联笔记：[Java类加载机制与双亲委派详解](Java类加载机制与双亲委派详解.md)（生命周期与委派模型）、[06-Tomcat类加载机制详解](../框架/网络底座/Web服务器/tomcat/06-Tomcat类加载机制详解.md)（类隔离应用）、[Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)（动态生成类）、[Java SPI机制详解](../JDK基础库/核心机制/Java SPI机制详解.md)（TCCL 与 SPI）、[JVM调优实战](JVM调优实战.md)（元空间泄漏排查）
