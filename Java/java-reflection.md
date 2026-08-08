---
tags: [Java, 反射, 机制, JVM, 性能优化]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/核心机制）
归属: 01-学习/Java/核心机制
aliases: [Java 反射详解]
---

# Java 反射机制详解（API / 原理 / 性能优化）

## 📋 总纲

1. 反射是什么：概念 + Class 对象 + 类加载阶段的位置
2. 核心 API：获取 Class / 获取成员 / 调用 + 综合示例
3. 典型应用场景：Spring IoC & AOP、MyBatis、Jackson（框架源码视角）
4. 为什么慢：四大开销来源 + 基准数据
5. 优化方案（重点）：缓存 → MethodHandle → LambdaMetafactory → 编译期生成 + 对比表
6. 易错点清单
7. 面试追问 Q&A（带答案）
8. 补充·JVM 底层实现（殿后）：MethodAccessor / inflation / invokedynamic

---

## 1. 反射是什么

### 1.1 定义

**反射（Reflection）**：程序在**运行期**动态获取类的完整信息（类名、方法、字段、构造器、注解），并基于这些信息**动态创建对象、调用方法、读写字段**的能力。

```java
// 编译期写法：类型写死，调用的方法写死
User u = new User();
u.setName("robin");

// 反射写法：类型和成员都是运行期才知道的字符串/对象
Class<?> clazz = Class.forName("com.example.User");
Object obj = clazz.getDeclaredConstructor().newInstance();
Method setName = clazz.getMethod("setName", String.class);
setName.invoke(obj, "robin");
```

### 1.2 Class 对象与类加载

- JVM 中每个类（含接口、枚举、数组、基本类型）加载后都对应**唯一一个 `Class` 实例**，存放在方法区/元空间（JDK 8+）
- `Class` 对象由类加载器在「加载」阶段创建，反射就是围绕这个 `Class` 对象展开
- 类加载生命周期：加载 → 验证 → 准备 → 解析 → 初始化。**反射会在首次使用时触发类的初始化**（`Class.forName` 显式触发，见下）

### 1.3 获取 Class 的三种方式

| 方式 | 代码 | 特点 | 易错点 |
|---|---|---|---|
| 类字面量 | `User.class` | 编译期类型确定，**不触发静态初始化**，性能最好 | 类型写死，不适用于"只有类名字符串"的场景 |
| 实例获取 | `user.getClass()` | 拿到的是**运行期实际类型**（子类也返回子类） | 对象为 null 会 NPE |
| 全限定名 | `Class.forName("com.example.User")` | 最灵活，字符串驱动；**会触发类的静态初始化**（执行 static 块） | 类名拼错抛 ClassNotFoundException；init 副作用要留意 |

① 想加载不执行 static 块：`Class.forName(name, false, classLoader)`
② 想拿接口的方法默认值/注解信息：用反射的 `getAnnotation` / `getDeclaredMethod` 等

### 1.4 反射能做什么

a. 动态创建对象：`Constructor.newInstance()`
b. 动态调用方法：`Method.invoke()`
c. 动态读写字段：`Field.get() / set()`
d. 获取注解与泛型信息：`getAnnotation` / `getGenericType`
e. 生成动态代理：`java.lang.reflect.Proxy`（AOP 基石）

---

## 2. 核心 API

### 2.1 获取成员：getXxx vs getDeclaredXxx

| 方法 | 可见范围 | 是否含继承 | 典型坑 |
|---|---|---|---|
| `getMethod(name, params)` | 仅 **public** | ✅ 含父类/接口 | 拿 private 方法抛 `NoSuchMethodException` |
| `getDeclaredMethod(name, params)` | 本类**所有**权限 | ❌ 不含继承 | 拿父类方法抛 `NoSuchMethodException`，需向上遍历 |
| `getField(name)` | 仅 public | ✅ 含继承 | 同上 |
| `getDeclaredField(name)` | 本类所有 | ❌ 不含继承 | 同上 |
| `getConstructor(params)` | 仅 public | ✅ | 私有构造器要用 Declared 版 |
| `getDeclaredConstructor(params)` | 本类所有 | ❌ | 结合 `setAccessible(true)` 才能 new |

**一句话口诀**：`get` 拿 public（含继承），`getDeclared` 拿本类全部（不含继承）。私有成员必须 `setAccessible(true)`。

### 2.2 setAccessible(true)

```java
Method m = clazz.getDeclaredMethod("secretMethod");
m.setAccessible(true);   // 跳过 JVM 访问权限检查（本模块/非模块化代码）
m.invoke(obj);
```

- 作用是关闭访问控制检查，让 private 成员也能操作
- **JDK 9+ 模块系统限制**：若目标类在**其他命名模块**且未导出/开放，`setAccessible` 抛 `InaccessibleObjectException` → 启动参数加 `--add-opens 模块名/包名=ALL-UNNAMED`（Spring Boot 等框架的常见启动参数来源）
- 同模块内或 `classpath`（未命名模块）代码不受影响

> [!note]- 模块系统长什么样（认识即可，平时不用写）
> JDK 9 引入的模块描述文件 `module-info.java` 长这样——日常开发几乎不写它，但启动日志/框架文档里经常见到相关报错和 `--add-opens` 参数，认得即可：
>
> ```java
> // module-info.java —— 模块描述文件（JDK 9+，绝大多数应用不写）
> module com.example.demo {
>     requires spring.context;        // 依赖其他模块
>     exports com.example.demo.api;   // 对外只开放 api 包，其余包外界不可见
>     opens com.example.demo.internal; // 开放该包的反射访问（反射想碰它就靠这个/--add-opens）
> }
> ```
>
> 配套的常见启动参数就是 2.2 节说的 `--add-opens`，例如：
>
> ```bash
> java --add-opens java.base/java.lang=ALL-UNNAMED -jar app.jar
> # 含义：把 JDK 自己的 java.base 模块中 java.lang 包开放给未命名模块（classpath 代码），反射才能访问其内部
> ```
>
> 一句话：`module-info.java` 是 JDK 9 模块系统给"谁依赖谁、谁对谁开放"立规矩的文件，`opens`/`--add-opens` 专门管反射访问；应用开发基本用不到，见到能认出来就行。

### 2.3 核心调用 API

| API | 作用 | 边界/易错点 |
|---|---|---|
| `Method.invoke(obj, args...)` | 调用方法 | 静态方法 obj 传 null；抛出的业务异常被包成 `InvocationTargetException`，要 `.getCause()` 取真因 |
| `Constructor.newInstance(args...)` | 反射创建实例 | 无参构造器也要显式取；对比 `Class.newInstance()`（已废弃，仅无参 public） |
| `Field.get(obj)` / `Field.set(obj, v)` | 读写字段 | 基本类型字段注意装箱；final 字段 set 不一定生效（JIT 内联后读到的还是原值） |
| `getAnnotation(X.class)` | 拿类/方法上的注解 | 仅运行时保留的注解（`@Retention(RUNTIME)`）才拿得到 |

### 2.4 综合示例（完整可运行）

```java
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class ReflectionDemo {

    static class User {
        private String name;
        private int age;

        public User() {}
        public User(String name, int age) { this.name = name; this.age = age; }

        private String sayHello(String prefix) {
            return prefix + ", " + name + " (" + age + ")";
        }
        @Override public String toString() { return "User{name='" + name + "', age=" + age + "}"; }
    }

    public static void main(String[] args) throws Exception {
        // 1. 获取 Class（不触发 static 块：Class.forName(name, false, loader)）
        Class<?> clazz = Class.forName("ReflectionDemo$User");

        // 2. 无参构造 + 私有字段写入
        Object obj = clazz.getDeclaredConstructor().newInstance();
        Field nameField = clazz.getDeclaredField("name");
        Field ageField  = clazz.getDeclaredField("age");
        nameField.setAccessible(true);
        ageField.setAccessible(true);
        nameField.set(obj, "robin");
        ageField.set(obj, 18);

        // 3. 调用 private 方法
        Method sayHello = clazz.getDeclaredMethod("sayHello", String.class);
        sayHello.setAccessible(true);
        Object result = sayHello.invoke(obj, "Hi");     // 返回 Object，基本类型会装箱
        System.out.println(result);                      // Hi, robin (18)

        // 4. 有参构造器
        Constructor<?> ctor = clazz.getDeclaredConstructor(String.class, int.class);
        Object obj2 = ctor.newInstance("alice", 20);
        System.out.println(obj2);

        // 5. InvocationTargetException 取真实异常
        try {
            sayHello.invoke(obj);   // 少传参数 → InvocationTargetException(内层是参数错误)
        } catch (java.lang.reflect.InvocationTargetException e) {
            System.out.println("真实异常: " + e.getCause().getClass().getSimpleName());
        }
    }
}
```

---

## 3. 典型应用场景（框架源码视角）

### 3.1 Spring IoC

- 扫描注解（`@Component` 等）→ `Class.forName` / 类元数据读取 → 反射调构造器实例化 Bean
- 依赖注入用 `BeanWrapper` 反射调用 setter / 写字段
- 关键优化：Spring 缓存反射结果（`CachedIntrospectionResults` 缓存 Bean 的 PropertyDescriptor），不在每次注入时重复 `getMethod`

### 3.2 Spring AOP / JDK 动态代理

- `Proxy.newProxyInstance(classLoader, interfaces, InvocationHandler)` 生成代理类
- 每次方法调用进入 `InvocationHandler.invoke`，内部再通过反射/`MethodHandle` 调目标方法
- CGLIB（子类代理）走字节码生成，不走反射——这也是 CGLIB 比 JDK 代理快的原因之一（Spring Boot 2+ 默认 CGLIB）

### 3.3 MyBatis Mapper

- Mapper 接口没有实现类 → 运行时 `MapperProxy` 动态代理
- 每次查询：代理拦截 → 反射读接口方法的注解（`@Select` 等）与参数 → 绑定 SQL
- 优化：MyBatis 缓存 `MapperMethod`（方法签名 → SQL 语句的映射），反射只在首次解析时发生

### 3.4 Jackson 反序列化

- 反序列化时按字段名/Setter 反射赋值（`BeanDeserializer`）
- Jackson 2.x 用字节码生成（`ASM`）生成序列化/反序列化器，避免热路径上的反射

### 3.5 运行时反射 vs 编译期生成

| 方案 | 代表 | 时机 | 运行时开销 |
|---|---|---|---|
| 运行时反射 | Spring IoC、JDK 代理 | 运行期查 + 调 | 每次调用都有开销 |
| 运行时字节码生成 | CGLIB、Byte Buddy、ASM、Jackson | 运行期生成类 | 生成后调用接近直接调用 |
| 编译期注解处理（APT） | Lombok、MapStruct | 编译期生成源码/字节码 | **零反射**，最快 |

**结论**：能编译期解决就不运行期反射；必须运行期，就用"生成后接近直接调用"的方案（见第 5 节）。

---

## 4. 为什么慢

### 4.1 四大开销来源

① **访问检查**：`invoke` 前 JVM 校验调用者权限（类加载器、模块、可访问性）
② **参数装箱**：`invoke(Object... args)` 要求基本类型变 `Integer` 等包装类
③ **Object[] 数组**：每次调用都要构造参数数组，产生分配与 GC 压力
④ **无法内联**：反射调用点对 JIT 不透明（黑盒），方法内联、逃逸分析全失效

另外还有首次调用的一次性开销：`Method` 内部访问器（Accessor）的生成（见第 8 节）。

### 4.2 基准数据（引用公开基准，JDK 8）

| 调用方式 | 耗时 (ns/op) | 相对直接调用 |
|---|---|---|
| 直接调用 | ~2.6 | 1x |
| LambdaMetafactory 绑定 | ~3.5 | ~1.33x |
| 反射 `Method.invoke` | ~5.3 | ~2x |
| 动态查找的 MethodHandle | ~6.1 | ~2.36x（JDK 8 上比反射还慢！） |

> 数据来源：Timefold《Java Reflection, but much faster》JDK8 基准。**注意**：
> a. 绝对数值随 JDK 版本、JVM 参数、调用形态变化，工程决策以 JMH 实测为准
> b. MethodHandle 的"快"依赖用法：`static final` 缓存 + 类型精确（`invokeExact`）才接近直接调用；JDK 17+ 上表现通常优于 JDK 8
> c. 反射在 JDK 8+ 有 inflation 优化（native → Java 访问器切换），超过阈值后比冷启动快，但依旧慢于直接调用

---

## 5. 优化方案（重点）

四层递进：**先缓存，再换 API，最后编译期干掉反射**。

### 5.1 方案一：缓存反射对象 + setAccessible

最基础的优化，把昂贵的"查找"一次做完，后续只做"调用"。

```java
public class CachedInvoker {
    // 静态缓存：类加载一次，全局复用
    private static final Method SET_NAME = initSetName();
    private static final Field NAME_FIELD = initNameField();

    private static Method initSetName() {
        try {
            Method m = User.class.getMethod("setName", String.class);
            m.setAccessible(true);          // 跳过访问检查
            return m;
        } catch (NoSuchMethodException e) { throw new ExceptionInInitializerError(e); }
    }
    private static Field initNameField() {
        try {
            Field f = User.class.getDeclaredField("name");
            f.setAccessible(true);
            return f;
        } catch (NoSuchFieldException e) { throw new ExceptionInInitializerError(e); }
    }

    public static void setName(Object user, String name) throws Exception {
        SET_NAME.invoke(user, name);
    }
}
```

要点：
- `getMethod` / `getDeclaredField` 等查找操作本身昂贵（要遍历类结构），**务必缓存**，禁止循环里每次查
- 缓存建议 `static final` 字段（初始化时一次性完成）
- `setAccessible(true)` 只影响检查跳过，`invoke` 的装箱/数组开销依旧在 → 想更快看方案二、三

### 5.2 方案二：MethodHandle（static final + invokeExact）

`MethodHandle` 是强类型可调用实体，JIT 能更好地优化它；`invokeExact` 不装箱、不塞 Object[]。

```java
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;

public class HandleInvoker {
    // 关键：static final 缓存；JDK 17+ 上接近直接调用
    private static final MethodHandle SET_NAME;

    static {
        try {
            SET_NAME = MethodHandles.lookup().findVirtual(
                    User.class, "setName",
                    MethodType.methodType(void.class, String.class));
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    public static void setName(User user, String name) throws Throwable {
        // invokeExact：类型必须完全匹配，不装箱、不转换
        SET_NAME.invokeExact(user, name);
    }
}
```

要点：
- **必须 `static final` 缓存**：每次 `findVirtual` 都重新生成，等于没优化；动态查找的 MH 在 JDK 8 上甚至比反射慢
- `invokeExact` 参数类型必须与签名完全一致（包括接收者），否则抛 `WrongMethodTypeException`；`invoke` 则允许转型/装箱（有额外开销）
- 首次调用有 LambdaForm 编译开销（一次性），热身后可内联
- 私有方法：`MethodHandles.privateLookupIn` 或 `lookup().findVirtual` 前先 `setAccessible`（JDK 9+ 有模块限制，同第 2.2 节）

### 5.3 方案三：LambdaMetafactory 生成函数式接口（最优）

把 MethodHandle 一次性"绑定"成普通函数式接口，之后就是**普通接口调用**，最接近直接调用。

```java
import java.lang.invoke.*;
import java.util.function.BiConsumer;

public class LambdaFactoryInvoker {
    // 绑定后：调用点就是普通接口方法，JIT 可完全内联
    private static final BiConsumer<Object, Object> SET_NAME = build();

    @SuppressWarnings("unchecked")
    private static BiConsumer<Object, Object> build() {
        try {
            MethodHandles.Lookup lookup = MethodHandles.lookup();
            MethodHandle target = lookup.findVirtual(
                    User.class, "setName",
                    MethodType.methodType(void.class, String.class));

            CallSite site = LambdaMetafactory.metafactory(
                    lookup,
                    "accept",                                            // 接口方法名
                    MethodType.methodType(BiConsumer.class),             // 工厂签名
                    MethodType.methodType(void.class, Object.class, Object.class), // 擦除签名
                    target,                                              // 实际目标
                    MethodType.methodType(void.class, User.class, String.class));  // 实例化签名
            return (BiConsumer<Object, Object>) site.getTarget().invokeExact();
        } catch (Throwable e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    public static void setName(Object user, String name) {
        SET_NAME.accept(user, name);   // 与直接调用同量级
    }
}
```

要点：
- 一次性构建开销较大（约几十 µs），**只在静态初始化/启动阶段构建一次**
- 生成的函数式接口类型要能表达目标签名；`BiConsumer` 的泛型擦除适配多数 setter 场景
- 返回值非 void 时选 `Function` / `BiFunction`，多参数用自定义函数式接口
- 这是 Spring、MyBatis 等框架内部"既灵活又快速"的底层手段

### 5.4 方案四：编译期/字节码生成（运行时零反射）

| 层 | 技术 | 代表 | 特点 |
|---|---|---|---|
| 编译期注解处理 | APT / 注解处理器 | Lombok（getter/setter）、MapStruct（Bean 拷贝）、Dagger | 零运行时开销，代码生成在编译期完成 |
| 运行期字节码生成 | ASM / Byte Buddy / CGLIB | Jackson、Spring AOP(CGLIB)、Mockito | 生成后调用接近直接调用 |
| 手写普通代码 | —— | 直接 new + 调用 | 最快，但失去动态性 |

**选型建议**：
① 纯样板代码（getter/setter、DTO 转换）→ Lombok / MapStruct
② 需要动态代理/拦截 → 优先 CGLIB（Spring Boot 默认）
③ 高性能序列化 → 用生成序列化器的库（Jackson 2.x），别自己反射
④ 只有"运行时才知道类名/方法名"才需要反射，能缩小范围就缩小（如只反射一次，之后走函数式接口缓存）

### 5.5 性能对比与选型总结

| 方案 | 相对直接调用 | 实现成本 | 适用 |
|---|---|---|---|
| 直接调用 | 1x | 零 | 编译期类型已知 |
| 缓存 Method + setAccessible | ~1.5-2x | 低 | 反射次数少、通用 |
| 缓存 MethodHandle（static final + invokeExact） | 接近直接调用（JDK 17+） | 中 | 热路径 + 签名固定 |
| LambdaMetafactory 绑定 | ~1.3x | 中高 | 热路径 + 需通用封装（框架层） |
| 编译期生成（APT/字节码） | ~1x（零反射） | 高 | 大量样板/强性能要求 |

**通用决策链**：
① 编译期能搞定 → APT/字节码生成（Lombok、MapStruct、CGLIB）
② 必须运行期反射 → 缓存 Method/Field + setAccessible
③ 热路径 → MethodHandle（static final + invokeExact）或 LambdaMetafactory 绑定成函数式接口
④ 业务代码里**不要**在循环内裸调 `getMethod(...).invoke(...)`

---

## 6. 易错点清单

1. **getMethod vs getDeclaredMethod 混淆**：`getMethod` 拿不到 private，`getDeclaredMethod` 拿不到父类方法——父类私有方法要沿继承链向上遍历
2. **忘记 setAccessible(true)**：直接 `invoke` private 成员抛 `IllegalAccessException`
3. **JDK 9+ 模块限制**：跨模块私有成员 `setAccessible` 抛 `InaccessibleObjectException` → 需要 `--add-opens`；框架（如 Spring）启动失败先查这个
4. **不缓存反射对象**：循环里每次 `getMethod`/`getDeclaredField`，性能直接爆炸（查找比调用更贵）
5. **基本类型装箱**：`invoke` 返回 `Object`，`int` 变 `Integer`；空值/拆箱要小心 NPE
6. **InvocationTargetException**：业务异常被包裹，必须 `.getCause()` 取真因，否则排错时看不到真实堆栈
7. **`Class.forName` 触发静态初始化**：有 static 块副作用的类，用 `forName(name, false, loader)` 规避
8. **final 字段 set 无效**：JIT 内联后 `Field.set` 可能改不到实际读取值（不要依赖反射改 final）
9. **Class 泄漏**：缓存反射对象时若持有 ClassLoader 引用（框架/插件热部署场景），会导致类无法卸载、元空间增长
10. **动态代理 ≠ 反射**：JDK 动态代理底层用反射（`InvocationHandler`），CGLIB 是字节码生成——"代理慢"要分清是哪种

---

## 7. 面试追问 Q&A

### 7.1 反射为什么慢？

答：四大开销——调用前的访问权限检查、基本类型装箱、`Object[]` 参数数组构造、以及 JIT 无法内联（调用点不透明）。此外首次调用还有访问器（Accessor）生成的一次性开销。

### 7.2 怎么优化反射？

答：四层递进：① 缓存 Method/Field + `setAccessible(true)` 跳过检查；② 热路径换 MethodHandle（`static final` + `invokeExact` 避免装箱）；③ LambdaMetafactory 一次性绑定成函数式接口，调用接近直接调用；④ 编译期/字节码生成（Lombok、MapStruct、CGLIB）运行时零反射。业务代码避免循环内裸调反射。

### 7.3 getMethod 和 getDeclaredMethod 的区别？

答：`getMethod` 只返回 public 方法且包含继承链；`getDeclaredMethod` 返回本类声明的所有权限方法但不含继承。private 方法必须用 Declared 版 + `setAccessible(true)`。

### 7.4 JDK 9+ 模块系统对反射的影响？

答：跨命名模块的私有成员默认禁止强反射访问，`setAccessible` 抛 `InaccessibleObjectException`；需 `--add-opens 模块/包=ALL-UNNAMED` 开放。classpath（未命名模块）内代码不受影响，这也是框架启动文档里常见 `--add-opens` 参数的原因。

### 7.5 反射会破坏封装吗？

答：`setAccessible(true)` 在 JDK 8 前能绕过几乎所有访问控制；JDK 9+ 模块系统收紧了这一能力——模块可明确控制哪些包对外开放，未开放的包即使 setAccessible 也无法访问，属于"默认开放、显式收紧"的转变。

### 7.6 动态代理和反射的关系？

答：JDK 动态代理基于反射实现（`Proxy.newProxyInstance` + `InvocationHandler`，方法调用经反射转发）；CGLIB 通过字节码生成子类，不走反射，因此更高效。Spring Boot 2+ 默认 CGLIB 代理。

### 7.7 Spring 怎么让反射不那么慢？

答：三个手段：① 缓存反射结果（`CachedIntrospectionResults`，Bean 的 setter/getter 元数据只解析一次）；② 大部分场景用 CGLIB 字节码代理而非 JDK 反射代理；③ 高版本 Spring/Jackson 底层用 MethodHandle/生成代码替代裸反射。

### 7.8 invoke 抛出的异常为什么拿不到真实堆栈？

答：因为业务异常被包在 `InvocationTargetException` 里，需要 `e.getCause()` 取出原始异常再打印。这是反射 API 的设计：统一包装底层抛出的 Throwable。

---

## 8. 补充·JVM 底层实现（殿后）

### 8.1 MethodAccessor 与 inflation

- `Method.invoke` 内部委托给 `MethodAccessor`（每个 Method 惰性创建，首次调用时才生成）
- **inflation 机制**（JDK 8）：调用次数低于阈值时用 native 版 Accessor（启动快、单次慢）；超过阈值（默认 15 次，`-Dsun.reflect.inflationThreshold` 可调，JDK 9+ 参数移除）后切换到由 `MethodAccessorGenerator` **字节码生成**的 Java 版 Accessor，之后执行更快
- 所以反射冷启动更慢、热调用会"变快"，但依旧有装箱/数组/内联损失

### 8.2 invokedynamic 与 LambdaForm

- `MethodHandle.invoke`、Lambda 表达式的字节码是 `invokedynamic` 指令
- 首次执行时引导方法（BootstrapMethod，如 `LambdaMetafactory.metafactory`）生成 `CallSite` + `LambdaForm`（JVM 内部优化模板）
- 热身后 LambdaForm 会被 JIT 编译，`invokeExact` 的强类型让 JIT 能**内联展开**——这就是 MethodHandle/LambdaMetafactory 接近直接调用的底层原因

### 8.3 JDK 版本差异速查

| JDK | 反射相关变化 |
|---|---|
| 8 | inflation 可调（`-Dsun.reflect.inflationThreshold`） |
| 9+ | 模块系统：跨模块强封装，`--add-opens` 开放；`sun.reflect.inflationThreshold` 移除 |
| 17+ | 强封装默认启用；`Class.newInstance()` 废弃（JDK 9 起）改用 `getDeclaredConstructor().newInstance()`；`java.lang.reflect.Proxy` 等 API 有性能改进，MethodHandle 表现整体优于早期版本 |

- 关联笔记：**代码混淆详解**（见知识库）（混淆会重命名反射目标类/方法，反射场景必须 keep）、**Java 注解机制详解**（见知识库）（反射读取注解）、**Java Agent 与字节码增强详解**（见知识库）（运行期动态机制对比）

---

## 参考

- Timefold《Java Reflection, but much faster》（JDK8 基准：反射 ~5.3ns vs 直接 ~2.6ns，LambdaMetafactory ~3.5ns）
- Hazelcast《Turbocharging Java Reflection Performance with MethodHandle》（MethodHandle 3.6x / LambdaMetafactory 2.2x 数据）
- PVS-Studio《Method Handles are faster than reflection (sometimes)》（MethodHandle 的 LambdaForm 编译与首次调用开销）
- OpenJDK 官方文档：`java.lang.invoke` 包（MethodHandle / LambdaMetafactory / VarHandle）
