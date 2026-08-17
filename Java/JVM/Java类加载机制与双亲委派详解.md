---
tags: [Java, JVM, 类加载, 双亲委派, ClassLoader, 机制]
创建日期: 2026-08-07
状态: ✅ 已归档（01-学习/Java/JVM）
归属: 01-学习/Java/JVM
---

# Java类加载机制与双亲委派详解（生命周期 / 加载器 / 打破与对比）

## 📋 总纲

1. 类加载生命周期：加载 → 验证 → 准备 → 解析 → 初始化
2. 类加载器层次：JDK 8 三层 → JDK 9 模块化调整
3. 双亲委派模型：机制、源码、三大好处
4. 打破双亲委派：SPI / Tomcat / 热部署三种方式
5. 类的唯一性与命名空间：ClassLoader + 全限定名（附热部署代码）
6. 类初始化时机：主动引用 vs 被动引用、`<clinit>` vs `<init>`
7. 常见误区
8. 版本差异
9. 面试追问 Q&A
10. 参考

---

## 1. 类加载生命周期

| 阶段 | 做什么 | 关键点 |
|---|---|---|
| **加载** Loading | 读取 class 字节流，生成 `Class` 对象 | 字节流来源不限：class 文件/jar/网络/动态生成 |
| **验证** Verification | 校验字节码合法性、安全性 | 防止恶意/损坏字节码危害 JVM |
| **准备** Preparation | 为**静态变量**分配内存并设**零值** | **注意：不是代码里的初值！** |
| **解析** Resolution | 符号引用转直接引用 | 把类名/方法名/字段名的符号引用解析为直接引用 |
| **初始化** Initialization | 执行 `<clinit>`，真正赋静态变量初值、执行静态块 | 多线程下只执行一次（JVM 保证） |

```java
public class Demo {
    public static int a = 10;      // 准备阶段: a = 0；初始化阶段: a = 10
    static { System.out.println("static block"); }  // 在 <clinit> 中执行
}
```

**要点**：
a. **准备阶段赋零值，初始化才赋真值**——`a` 先被设 0，执行 `<clinit>` 时才变 10
b. `<clinit>` 由编译器把**所有静态变量赋值 + 静态块按源码顺序**合并生成
c. JVM 保证 `<clinit>` 在多线程下**只执行一次**（类初始化有锁）——这是"静态内部类单例"线程安全的原理

> **`<clinit>` vs `<init>`**：
> - `<clinit>` = 类构造器：静态变量赋值 + 静态块，类加载初始化时执行一次，JVM 保证线程安全
> - `<init>` = 实例构造器：实例变量赋值 + 构造块 + 构造方法，每次 `new` 都执行
> - 所以"静态内部类单例"延迟初始化且线程安全，全靠 `<clinit>` 的特性

---

## 2. 类加载器层次（速览）

> 📌 **类加载器的完整详解**（职责 / API / 自定义实战 / 使用场景 / 最佳实践）见独立文档：[Java类加载器详解](Java类加载器详解.md)。本节只保留与本篇主题（双亲委派）相关的层次速览。

### 2.1 加载器层次与职责速览

| 加载器 | 加载范围 | 实现 | 职责一句话 |
|---|---|---|---|
| **启动类加载器 Bootstrap** | `java.*` 核心类 | C++ 实现，Java 中表现为 `null` | JVM 核心类，最高权限 |
| **平台类加载器 Platform**（JDK 8 为 Extension） | JDK 模块类 / `lib/ext` | Java 实现 | 中间层：JDK 扩展类 |
| **应用类加载器 Application** | classpath（用户类） | Java 实现，**默认加载器** | 我们写的类 |
| **自定义类加载器** | 自定义路径/来源 | 继承 `ClassLoader` | 网络/加密/热部署等特殊来源 |

**验证 Bootstrap 为 null**：

```java
System.out.println(String.class.getClassLoader());   // null → Bootstrap
System.out.println(Demo.class.getClassLoader());     // AppClassLoader...
```

### 2.2 委托链（本篇核心关注）

```
Bootstrap（顶层，C++/null）
   └── Platform（JDK 8: Extension）
         └── Application
               └── 自定义加载器（可多层）
```

**双亲委派就是沿这条链向上委托**——详细机制见第 3 节。

### 2.3 JDK 9 模块化调整

- **扩展类加载器 Extension → 平台类加载器 Platform ClassLoader**
- 引入**模块路径（module path）**：类来源从 classpath 转向模块化描述
- 双亲委派**思想不变**，层次结构有调整
- 反射访问内部模块需要 `--add-opens`（关联 [Java反射详解](../JDK基础库/核心机制/Java反射详解.md) 2.2 节）

---

## 3. 双亲委派模型

### 3.1 工作机制

类加载器收到加载请求时：**先向上委托给父加载器**，父再往上委托直到 Bootstrap；父加载器**加载不了**（找不到）时，才由子加载器自己尝试加载。

```
请求加载 com.example.Foo
    │
    ▼
AppClassLoader ──委托──▶ Ext/Platform ──委托──▶ Bootstrap
    ▲                    ▲                    │
    │                    │                    │ 能找到 java.* 核心类
    │                    │                    ▼
    └──── 父都失败，自己加载 ────┘         加载成功
```

### 3.2 源码逻辑（loadClass 简化）

```java
protected Class<?> loadClass(String name, boolean resolve) {
    Class<?> c = findLoadedClass(name);          // ① 已加载过？
    if (c == null) {
        try {
            if (parent != null) {
                c = parent.loadClass(name, false);  // ② 先委托父
            } else {
                c = findBootstrapClassOrNull(name); // 顶层 → Bootstrap
            }
        } catch (ClassNotFoundException e) {
            // 父加载器加载不了
        }
        if (c == null) {
            c = findClass(name);                   // ③ 父失败 → 自己加载
        }
    }
    return c;
}
```

**核心**：先向上委托，父失败才自己找。保证 `java.lang.String` 永远由 Bootstrap 加载——即使用户写了个同名 `java.lang.String` 也不会被加载。

### 3.3 三大好处

| 好处 | 说明 |
|---|---|
| **安全** | 核心类库无法被自定义类覆盖替换（防篡改） |
| **唯一性** | 同一个类只被加载一次，避免重复与冲突 |
| **层次清晰** | 类与加载器的从属关系稳定可控 |

---

## 4. 打破双亲委派

### 4.1 为什么需要打破

双亲委派的"唯一性"在特殊场景成了束缚：**核心类要加载外部实现 / 容器要隔离多个应用**——标准委托链解决不了。

### 4.2 三种典型打破方式

| 场景 | 为什么打破 | 怎么打破 | 方向 |
|---|---|---|---|
| **SPI**（JDBC、JNDI） | rt.jar 里的核心接口要加载 classpath 里的厂商实现，但 Bootstrap 看不到 classpath | **线程上下文类加载器** `Thread.getContextClassLoader()`，让 Bootstrap 加载的代码反向拿到应用类加载器 | 反向委托（父→子借道） |
| **Tomcat 等容器** | 多 Web 应用需类隔离、同名不同版本共存 | 每应用一个 `WebAppClassLoader`，**先自己加载**（违反"先委托父"） | 先子后父 |
| **热部署 / OSGi** | 运行时替换类、网状模块依赖 | 自定义类加载器，重写 `findClass` / 网状委托 | 换实例重载 |

**SPI 打破详解（以 JDBC 为例）**：
- `DriverManager` 在 rt.jar 中由 **Bootstrap** 加载
- 它要实例化 classpath 里的 `com.mysql.cj.jdbc.Driver`（厂商实现）
- Bootstrap 根本看不到 classpath → 标准委托链断掉
- 解决：`DriverManager` 通过**线程上下文类加载器**（应用类加载器）加载驱动——绕过标准自底向上委托

```java
// DriverManager 内部（简化）：用线程上下文类加载器加载驱动实现
ClassLoader cl = Thread.currentThread().getContextClassLoader();
Class<?> driverClass = Class.forName("com.mysql.cj.jdbc.Driver", true, cl);
```

### 4.3 Tomcat 打破双亲委派

→ **详见 [06-Tomcat类加载机制详解](../框架/网络底座/Web服务器/tomcat/06-Tomcat类加载机制详解.md)**（框架/tomcat）：WebAppClassLoader 先子后父、类隔离、java.* 硬过滤等完整对比。

**一句话**：Tomcat 为**类隔离**打破委派顺序，但 `java.*` 底线不破（仍 Bootstrap 加载）。

### 4.4 线程上下文类加载器补充

- 本质：Thread 上的一个 ClassLoader 引用，默认是 AppClassLoader
- 作用：让"上层加载器加载的代码"能加载"下层 classpath 的类"（反向）
- 应用：JDBC、JNDI、JAXB 等所有 SPI 机制
- 关联：[Java SPI机制详解](../JDK基础库/核心机制/Java SPI机制详解.md)（SPI 完整机制）

---

## 5. 类的唯一性与命名空间（附热部署代码）

### 5.1 核心结论

**类的唯一性 = ClassLoader + 全限定名**。同一个类名被两个不同 ClassLoader 加载后，是两个**互不相干**的类型。

```java
// 经典陷阱：同名类不同加载器 → 赋值抛 ClassCastException
Class<?> a = loader1.loadClass("com.example.Foo");
Class<?> b = loader2.loadClass("com.example.Foo");
a == b;                    // false，两个不同的 Class 对象
Object oa = a.newInstance();
((com.example.Foo) oa);    // 若 oa 由 loader2 加载，这里抛 ClassCastException
// 报错长这样: "com.example.Foo cannot be cast to com.example.Foo"
```

**这就是容器里 "X cannot be cast to X" 的根源**——同一个类被不同加载器加载了两次（如 Tomcat 热部署后新旧加载器并存、父子加载器各加载一份）。

### 5.2 热部署：自定义 ClassLoader

```java
public class HotDeployClassLoader extends ClassLoader {
    private final String classDir;

    public HotDeployClassLoader(String classDir, ClassLoader parent) {
        super(parent);              // 仍委托父加载 java.* 等核心类
        this.classDir = classDir;
    }

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        // 重写 findClass（不是 loadClass）→ 保留双亲委派给核心类
        byte[] bytes = loadClassBytes(classDir + "/" + name.replace('.', '/') + ".class");
        return defineClass(name, bytes, 0, bytes.length);   // 每次都是新 Class 对象
    }

    private byte[] loadClassBytes(String path) {
        try (var in = new java.io.FileInputStream(path)) {
            return in.readAllBytes();
        } catch (Exception e) { throw new RuntimeException(e); }
    }
}

// 重载 = 新建一个 ClassLoader 实例再加载 → 全新 Class 对象
public static Object reload(String className, String dir) throws Exception {
    HotDeployClassLoader cl = new HotDeployClassLoader(dir, HotDeployClassLoader.class.getClassLoader());
    Class<?> clazz = cl.loadClass(className);
    return clazz.getDeclaredConstructor().newInstance();
}
```

**要点**：
a. 重写 `findClass` 而非 `loadClass`——保留对 `java.*` 的双亲委派（父能加载的先给父）
b. 每次 reload 创建**新的 ClassLoader 实例** + `defineClass` → 全新的 `Class` 对象
c. **旧实例回收依赖旧 ClassLoader 不可达**：若旧类被静态变量/线程局部持有 → 旧加载器无法回收 → 元空间/堆泄漏
d. 这正是 Tomcat 反复热部署后元空间暴涨的原因（关联 [JVM调优实战](JVM调优实战.md) 3.6 元空间溢出）

---

## 6. 类初始化时机

### 6.1 主动引用（触发初始化）

a. `new` 实例（含反射 `newInstance`）
b. 访问/设置**静态字段**（非常量）
c. 调用静态方法
d. 反射（`Class.forName("xxx")` 默认初始化）
e. 初始化子类 → 先初始化父类
f. 启动类（main 所在类）

### 6.2 被动引用（不触发初始化）

a. 通过子类访问**父类的静态字段**（只初始化父类，不初始化子类）
b. 通过**数组**定义引用类：`Demo[] arr = new Demo[10]`（不触发 Demo 初始化）
c. 访问 `static final` **编译期常量**（已内联到调用方字节码）

```java
class Parent { static int x = 1; static { System.out.println("Parent init"); } }
class Child  extends Parent { static { System.out.println("Child init"); } }

System.out.println(Child.x);   // 只打印 "Parent init"——通过子类访问父类静态字段，子类不初始化
System.out.println(Parent.class.getName());  // 不触发初始化（只加载不初始化）
```

### 6.3 Class.forName vs ClassLoader.loadClass

| 方式 | 是否初始化 | 典型场景 |
|---|---|---|
| `Class.forName("xxx")` | **默认会**（可用 `forName(name, false, loader)` 只加载不初始化） | **JDBC 驱动注册**（`Class.forName` 触发 Driver 静态块注册到 DriverManager） |
| `ClassLoader.loadClass("xxx")` | 不会 | 只加载不初始化的场景 |

**JDBC 驱动加载的经典差异**：
- 老写法 `Class.forName("com.mysql.jdbc.Driver")`：初始化 Driver → 静态块执行 `DriverManager.registerDriver` → 驱动注册成功
- 若用 `ClassLoader.loadClass`：只加载不初始化 → 驱动没注册 → `DriverManager.getConnection` 找不到驱动
- JDBC 4.0+ 有 SPI 自动发现（META-INF/services），`Class.forName` 写法已不再必须

### 6.4 静态内部类单例（线程安全的原理）

```java
public class Singleton {
    private Singleton() {}
    private static class Holder {           // 静态内部类
        static final Singleton INSTANCE = new Singleton();
    }
    public static Singleton getInstance() {
        return Holder.INSTANCE;             // 首次访问才触发 Holder 的 <clinit>
    }
}
```

- **延迟**：`Holder` 只在首次 `getInstance()` 时才被加载并初始化
- **线程安全**：`<clinit>` 由 JVM 保证只执行一次（类初始化锁）
- **与饿汉式对比**：饿汉式类加载即初始化（`static final INSTANCE = new Singleton()` 在外部类 `<clinit>` 里），无延迟但实现更简单；静态内部类兼顾延迟 + 线程安全，是推荐写法

---

## 7. 常见误区

1. **把"双亲"理解成两个父加载器**——实际是单链向上委托，"双亲委派"是 parents-delegation 的翻译问题
2. **认为准备阶段就赋真值**——准备阶段是**零值**，初始化（`<clinit>`）才赋代码里的初值
3. **认为访问静态常量会触发初始化**——编译期常量 `static final` 已内联，不触发
4. **认为 Tomcat 完全遵守双亲委派**——WebAppClassLoader 为隔离打破了（先子后父）
5. **以为 `Class.forName` 只加载不初始化**——默认会初始化；`forName(name, false, loader)` 才只加载
6. **认为打破双亲委派后核心类也能被覆盖**——java.* 永远 Bootstrap 加载（Tomcat 也硬过滤）
7. **混淆"加载"和"初始化"**——加载只生成 Class 对象，初始化才执行静态代码

---

## 8. 版本差异

| 版本 | 变化 |
|---|---|
| JDK 8 | Bootstrap / Extension / Application 三层 |
| JDK 9 | 模块化（JPMS）：Extension → **Platform**；引入模块路径 |
| JDK 16+ | `sealed` 类影响类层次，类加载需校验 permitted subclasses |

---

## 9. 面试追问 Q&A

### 9.1 类的加载过程分哪几个阶段？

答：加载 → 验证 → 准备 → 解析 → 初始化（后四步合称"链接"）。加载生成 Class 对象；准备为静态变量分配内存赋零值；初始化执行 `<clinit>` 赋真值并执行静态块。

### 9.2 什么是双亲委派？有什么好处？

答：类加载请求先向上委托给父加载器，父失败才自己加载。好处：安全（核心类库无法被自定义类覆盖）、唯一性（同类只加载一次）、层次清晰。用户自定义 `java.lang.String` 永远不会被加载。

### 9.3 如何打破双亲委派？为什么要打破？

答：三种：SPI 用线程上下文类加载器反向委托；Tomcat 用 WebAppClassLoader 先子后父做类隔离；热部署/OSGi 用自定义 ClassLoader 换实例重载。打破是因为标准模型的核心类"唯一性"在需要加载外部实现/多版本隔离时成了束缚。

### 9.4 什么时候触发类初始化？

答：主动引用六种：new、访问/设置非静态常量字段、调静态方法、反射、初始化子类先初始化父类、main 启动类。被动引用不触发：子类访问父类静态字段、数组定义、编译期常量。

### 9.5 `<clinit>` 和 `<init>` 的区别？

答：`<clinit>` 是类构造器（静态变量赋值 + 静态块），类初始化时执行一次，JVM 保证线程安全；`<init>` 是实例构造器（实例变量 + 构造块 + 构造方法），每次 new 都执行。静态内部类单例的线程安全就依赖 `<clinit>` 的单次执行特性。

### 9.6 为什么静态内部类单例线程安全？

答：首次访问 `Holder.INSTANCE` 才触发 Holder 的类初始化，而 `<clinit>` 由 JVM 加锁保证只执行一次——既延迟加载又线程安全，且实现简单（对比双重检查锁无需 volatile/synchronized 手写）。

### 9.7 Class.forName 和 ClassLoader.loadClass 的区别？

答：forName 默认会初始化类（触发静态块），loadClass 只加载不初始化。JDBC 老写法 `Class.forName("驱动")` 就是靠初始化时静态块注册驱动；JDBC 4.0+ 用 SPI 自动发现后不再必须。

### 9.8 同一个类被两个 ClassLoader 加载，instanceof 结果如何？

答：类的唯一性由"ClassLoader + 全限定名"决定——两个不同加载器加载的同名类是互不相干的类型，`instanceof` 为 false、赋值抛 `ClassCastException`（经典的 "X cannot be cast to X"）。这也是容器热部署/类隔离出问题的根源，排查看类加载器命名空间。

### 9.9 Tomcat 打破了双亲委派，java.* 还会被重复加载吗？

答：不会。WebAppClassLoader 对 `java.*` 有硬编码过滤，直接交 Bootstrap 加载，保证核心类唯一安全。Tomcat 打破的只是应用自定义类的委派顺序（先子后父做隔离），JVM 核心类底线没破。

### 9.10 设计热部署机制，如何保证旧实例被回收？

答：每次重载新建 ClassLoader 实例并 defineClass 得到新 Class；旧 ClassLoader 及其类在**无任何引用**时被 GC（元空间）。关键坑：旧类若被静态变量、线程局部、监听器注册表持有 → 旧加载器无法回收 → 内存泄漏。设计时要确保旧加载器不可达（解绑监听器、清理 ThreadLocal、不用静态持有实例）。

---

## 10. 参考

- JVM Specification SE 8, Chapter 5: Loading, Linking, Initializing
- Java SE 8 ClassLoader API
- Tomcat Class Loader HOW-TO 官方文档
- 关联笔记：[Java类加载器详解](Java类加载器详解.md)（加载器完整详解）、[06-Tomcat类加载机制详解](../框架/网络底座/Web服务器/tomcat/06-Tomcat类加载机制详解.md)（Tomcat 打破双亲委派）、[Java SPI机制详解](../JDK基础库/核心机制/Java SPI机制详解.md)（SPI 线程上下文类加载器）、[Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)（类加载时的字节码介入）、[Java反射详解](../JDK基础库/核心机制/Java反射详解.md)（forName 初始化与 --add-opens）、[JVM调优实战](JVM调优实战.md)（元空间溢出与类加载器泄漏）
