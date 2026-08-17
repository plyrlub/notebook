---
tags: [Java, 代理, 动态代理, CGLIB, Spring, AOP]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/JDK基础库/核心机制）
归属: 01-学习/Java/JDK基础库/核心机制
---

# Java代理详解（静态 / 动态 / 对比）

## 📋 总纲

1. 代理模式：是什么、为什么需要、核心三要素
2. 静态代理：实现 + 优缺点
3. JDK 动态代理：Proxy + InvocationHandler + Demo
4. CGLIB 动态代理：Enhancer + MethodInterceptor + Demo
5. 三种方式对比表 + 选型建议
6. 补充：Spring AOP 的代理选择、底层原理（殿后）
7. 易错点清单
8. 面试追问 Q&A（带答案）

---

## 1. 代理模式

### 1.1 是什么

**代理（Proxy）**：不直接操作目标对象，而是通过一个"代理对象"间接访问，在目标方法执行前后**插入额外逻辑**（日志、鉴权、事务、延迟加载等）。

```java
// 客户端视角：只认接口，不知道背后是代理还是真实对象
UserService service = new UserServiceProxy(new UserServiceImpl());
service.save(user);   // 代理里先记日志/开事务，再调真实对象
```

### 1.2 为什么需要

① 不侵入业务代码：横切逻辑（日志/事务/权限）与业务解耦
② 控制访问：代理可拦截、校验、降级
③ 延迟加载：真实对象很重时，代理先顶上，用时再创建
④ 远程调用：RPC 中代理负责网络传输，对调用方透明

### 1.3 核心三要素

a. **接口/目标类**：要代理的抽象
b. **真实对象**：真正干活的类
c. **代理对象**：持有真实对象引用，包装增强逻辑

---

## 2. 静态代理

### 2.1 实现（编译期就写死的代理类）

```java
// ① 接口
public interface UserService {
    void save(String name);
}

// ② 真实对象
public class UserServiceImpl implements UserService {
    public void save(String name) {
        System.out.println("保存用户: " + name);
    }
}

// ③ 代理对象：编译期手动编写，一个接口一个代理类
public class UserServiceProxy implements UserService {
    private final UserService target;   // 持有真实对象

    public UserServiceProxy(UserService target) { this.target = target; }

    public void save(String name) {
        System.out.println("[日志] 开始保存...");     // 增强逻辑
        target.save(name);                          // 调用真实对象
        System.out.println("[日志] 保存完成");
    }
}

// 使用
UserService service = new UserServiceProxy(new UserServiceImpl());
service.save("robin");
```

### 2.2 优缺点

| 优点 | 缺点 |
|---|---|
| 实现简单、直观 | 每个接口都要手写代理类 → 类爆炸 |
| 性能最好（普通调用） | 接口新增方法，代理类必须同步改 |
| 逻辑清晰可读 | 增强逻辑写死在代码里，不灵活 |

**结论**：只适合接口极少、增强逻辑固定的场景（如工具类装饰），生产上几乎不用。

---

## 3. JDK 动态代理

### 3.1 机制

- 运行期用 `java.lang.reflect.Proxy` **动态生成**实现指定接口的代理类
- 代理类把方法调用转发给 `InvocationHandler.invoke`
- **只能代理接口**（生成的代理类 implements 接口）
- 底层：代理类的每次方法调用 → `InvocationHandler.invoke` → 内部用**反射**调用真实对象

### 3.2 Demo（完整可运行）

```java
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

public class JdkProxyDemo {

    public interface UserService {
        void save(String name);
    }

    public static class UserServiceImpl implements UserService {
        public void save(String name) {
            System.out.println("保存用户: " + name);
        }
    }

    public static void main(String[] args) {
        UserService target = new UserServiceImpl();

        // ① InvocationHandler：所有方法调用都会进这里
        InvocationHandler handler = (proxy, method, methodArgs) -> {
            System.out.println("[日志] 开始保存...");
            Object result = method.invoke(target, methodArgs);  // 反射调用真实对象
            System.out.println("[日志] 保存完成");
            return result;
        };

        // ② Proxy.newProxyInstance：生成代理对象
        UserService proxy = (UserService) Proxy.newProxyInstance(
                target.getClass().getClassLoader(),   // 类加载器
                new Class[]{UserService.class},       // 要实现的接口列表
                handler);                             // 调用处理器

        proxy.save("robin");
    }
}
```

### 3.3 关键 API

| API | 作用 | 易错点 |
|---|---|---|
| `Proxy.newProxyInstance(loader, interfaces, handler)` | 生成代理对象 | interfaces 必须是接口，不能是类；loader 要能加载这些接口 |
| `InvocationHandler.invoke(proxy, method, args)` | 所有调用的统一入口 | `method.invoke(target, args)` 里 target 别传成 proxy → 死循环 |
| `Proxy.isProxyClass(cls)` | 判断是否代理类 | —— |
| `Proxy.getInvocationHandler(proxy)` | 拿代理的 handler | 仅限 JDK 代理对象 |

### 3.4 易错点

① `newProxyInstance` 的第二个参数传**类**会抛 `IllegalArgumentException`（不是接口）
② handler 里反射调用时 target 传错成 proxy → 无限递归 StackOverflow
③ 被代理的接口新增方法，handler 无需改动（天然适配）

---

## 4. CGLIB 动态代理

### 4.1 机制

- **字节码生成**：运行期生成目标类的**子类**，覆写非 final 方法实现拦截
- **不要求接口**：直接代理类（Spring Boot 2+ 默认）
- 底层：ASM 生成子类字节码 + `MethodInterceptor.intercept` 回调
- 注意：**final 类无法被继承、final 方法无法被覆写** → 不能被 CGLIB 代理

### 4.2 Demo（完整可运行，需引入 cglib 依赖；Spring 内置 fork 版）

```java
import net.sf.cglib.proxy.Enhancer;
import net.sf.cglib.proxy.MethodInterceptor;
import net.sf.cglib.proxy.MethodProxy;

public class CglibProxyDemo {

    // 没有接口也能代理
    public static class UserService {
        public void save(String name) {
            System.out.println("保存用户: " + name);
        }
    }

    public static void main(String[] args) {
        Enhancer enhancer = new Enhancer();
        enhancer.setSuperclass(UserService.class);           // 目标类 = 父类
        enhancer.setCallback((MethodInterceptor) (obj, method, methodArgs, methodProxy) -> {
            System.out.println("[日志] 开始保存...");
            Object result = methodProxy.invokeSuper(obj, methodArgs);  // 调父类原方法
            System.out.println("[日志] 保存完成");
            return result;
        });

        UserService proxy = (UserService) enhancer.create();  // 生成子类代理
        proxy.save("robin");
    }
}
```

### 4.3 关键 API

| API | 作用 | 易错点 |
|---|---|---|
| `Enhancer.setSuperclass(cls)` | 指定目标类 | 不能是 final 类 |
| `Enhancer.setCallback(interceptor)` | 设置拦截器 | 可设多个，配合 `CallbackFilter` 按方法路由 |
| `MethodProxy.invokeSuper(obj, args)` | 调用父类原方法 | 传错对象/调 `invoke` 自身 → 死循环 |
| `Enhancer.create()` | 生成代理 | 目标类无默认构造器时需 `Enhancer` 传参构造 |

### 4.4 易错点

① final 类/方法 → 直接报错或被跳过增强
② `methodProxy.invokeSuper` 写成 `methodProxy.invoke(obj, ...)` 或误调 `method.invoke(obj, ...)` → 递归栈溢出
③ 目标类无无参构造器：`Enhancer` 无法默认创建（可用 `Objenesis` 绕过，Spring 用 `Objenesis` 处理）

---

## 5. 三种方式对比 + 选型

| 维度 | 静态代理 | JDK 动态代理 | CGLIB 动态代理 |
|---|---|---|---|
| 代理产生时机 | 编译期 | 运行期 | 运行期 |
| 是否要求接口 | 是（按接口写） | **必须**接口 | 不需要 |
| 代理形式 | 手写类 | 动态生成接口实现类 | 动态生成目标类子类 |
| 调用性能 | 最快（普通调用） | 较慢（反射转发） | 快（接近直接调用） |
| 灵活度 | 差（改一个方法改一遍） | 好（handler 统一） | 好 |
| 限制 | 类爆炸 | 无接口不可用 | final 类/方法不可用 |
| 依赖 | 无 | JDK 自带 | cglib 库（Spring 内置） |

**选型建议**：
① 目标有接口 + 调用不频繁 → JDK 动态代理（零依赖，Spring 默认配置可切回）
② 无接口 / 追求性能 → CGLIB（Spring Boot 2+ 默认）
③ 静态代理 → 基本只在教学/超简单装饰场景用

---

## 6. 补充：Spring AOP 的代理选择与底层原理（殿后）

### 6.1 Spring AOP 怎么选代理

- 默认策略（Spring Boot 2+）：**CGLIB 优先**
  - 目标类实现接口时，经典 Spring 默认用 JDK 代理；Boot 2+ 改为默认 CGLIB 类代理（`spring.aop.proxy-target-class=true`）
- 何时退回 JDK 代理：`spring.aop.proxy-target-class=false`，或目标没有可用的类代理方式时
- 为什么 Boot 2+ 默认 CGLIB：
  a. 类型安全：`@Autowired` 按类型注入时，JDK 代理只能转成接口类型，注入具体类报错
  b. 性能更好：CGLIB 调用不走反射
  c. 一致性：接口和非接口统一用类代理

### 6.2 Spring 为什么用 CGLIB 而不是 ByteBuddy / ASM

① **ASM 太底层**：Spring 只用 ASM 做"读"（类扫描、注解解析，内部 fork 为 `org.springframework.asm`），生成代理交给 CGLIB 封装
② **CGLIB 足够快**：代理调用性能瓶颈在拦截器链，不在生成器；三者产出代理运行速度几乎一样
③ **Spring 收编 CGLIB**：Spring 5.3 起自己维护 fork（`org.springframework.cglib`），锁版本、打补丁、不被上游停更绑架
④ **ByteBuddy 能力过剩**：它的强项（运行时重定义已加载类 / agent）Spring AOP 用不上，引入它徒增复杂度

### 6.3 底层原理（了解即可）

- **JDK 代理**：`ProxyGenerator` 在运行期生成 `$Proxy0` 字节码（实现接口），方法调用转发 `InvocationHandler.invoke` → 反射调真实对象
- **CGLIB**：ASM 生成目标类的子类字节码，覆写方法插入拦截逻辑；调用链为 代理方法 → `MethodInterceptor.intercept` → `MethodProxy.invokeSuper` → 原方法
- **性能差异根源**：JDK 代理每次调用有反射开销（检查/装箱/无法内联），CGLIB 子类方法调用与普通调用接近，可被 JIT 内联

---

## 7. 易错点清单

1. **JDK 代理只认接口**：传类给 `newProxyInstance` 抛 `IllegalArgumentException`
2. **handler 里 target 传错**：`method.invoke(proxy, ...)` → 无限递归
3. **CGLIB 代理 final**：final 类不能继承、final 方法不能覆写，直接失败或静默不增强
4. **`invokeSuper` vs `invoke`**：CGLIB 里用错会栈溢出（`invokeSuper` 走父类原方法，`invoke` 走拦截器 → 递归）
5. **Spring 注入类型不匹配**：JDK 代理对象是 `$Proxy0`，按实现类类型 `@Autowired` 会注入失败 → 这也是 Boot 默认 CGLIB 的原因
6. **代理对象 == 不成立**：`proxy instanceof UserServiceImpl` 为 true（CGLIB 子类），但 `proxy.getClass()` 不是 `UserServiceImpl`，是 `UserService$$EnhancerByCGLIB`
7. **无参构造器缺失**：CGLIB 默认需要目标类有无参构造（或用 Objenesis 绕过）
8. **静态代理维护成本**：接口一变，代理类跟着变，别在业务里手写一堆静态代理

---

## 8. 面试追问 Q&A

### 8.1 JDK 动态代理和 CGLIB 的区别？

答：JDK 代理要求目标实现接口，运行期生成接口实现类，方法调用经 InvocationHandler 反射转发，性能较慢；CGLIB 不要求接口，用 ASM 生成目标类子类并覆写方法，经 MethodInterceptor 拦截，调用接近直接调用，更快。但 final 类/方法无法被 CGLIB 代理。

### 8.2 Spring AOP 默认用哪种代理？

答：Spring Boot 2+ 默认 CGLIB 类代理（`spring.aop.proxy-target-class=true`）。原因：类型安全（可按具体类注入）、性能更好（不走反射）、接口/非接口统一。经典 Spring 默认在有接口时用 JDK 代理。

### 8.3 为什么 CGLIB 比 JDK 代理快？

答：JDK 代理每次调用经反射（访问检查、装箱、Object[]、无法内联）；CGLIB 生成的子类方法调用与普通调用同构，能被 JIT 内联，接近直接调用速度。

### 8.4 静态代理和动态代理的区别？

答：静态代理编译期手写代理类，一个接口一个类，类爆炸且不灵活；动态代理运行期由 JDK（Proxy）或字节码库（CGLIB/ASM）自动生成代理类，统一拦截逻辑，灵活、可扩展、无侵入。

### 8.5 哪些类不能被 CGLIB 代理？

答：final 类（无法继承）、final 方法（无法覆写）、以及没有可用构造器且无法绕过创建的对象。private/static 方法不受拦截（子类无法覆写/不参与动态分派）。

### 8.6 JDK 代理能否代理类、CGLIB 能否代理接口？

答：JDK 代理只能代理接口（生成的类 implements 接口）；CGLIB 能代理类和接口，但代理接口时同样生成实现类。Spring 中 CGLIB 主要面向类代理场景。

### 8.7 动态代理在框架中的应用？

答：Spring AOP（事务、日志、安全）、MyBatis Mapper 接口代理（无实现类的 SQL 执行）、RPC 框架（远程调用伪装成本地调用）、Mockito（测试替身）、Hibernate（懒加载代理）。

---

## 参考

- Oracle JDK 文档：`java.lang.reflect.Proxy` / `InvocationHandler`
- Spring Framework 源码：`ProxyFactory`、`CglibAopProxy`、`JdkDynamicAopProxy`
- CGLIB 官方文档：`Enhancer` / `MethodInterceptor` / `MethodProxy`
- 关联笔记：[Java反射详解](Java反射详解.md)（JDK 代理底层反射调用与优化）、[Java SPI机制详解](Java SPI机制详解.md)（框架可插拔扩展对比）
