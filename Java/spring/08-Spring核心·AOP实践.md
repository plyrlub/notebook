---
tags: [Java, Spring, AOP, 实践, 切面, 通知, AspectJ]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring核心·AOP实践

> 版本基线：Spring 5.x/6.x，Spring AOP（AspectJ 注解式）。先读 [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)。
> 前置：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（五通知/切点/动态代理）；本篇给"切面怎么写 + 切点表达式含义 + 失效场景"。

## 📋 总纲

1. 依赖与启用
2. 一个完整切面（注解式）
3. 切点表达式逐个含义
4. 五种通知与执行顺序
5. 获取参数/返回值/异常
6. 失效场景（重点）
7. 注意点与踩坑

## 1. 依赖与启用

```xml
<!-- pom/依赖：spring-aop + aspectjweaver -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-aop</artifactId>
</dependency>
<dependency>
    <groupId>org.aspectj</groupId>
    <artifactId>aspectjweaver</artifactId>
</dependency>

<!-- XML 开启 aspect 自动代理 -->
<aop:aspectj-autoproxy/>
<!-- 或 JavaConfig：@EnableAspectJAutoProxy -->
```

**开启注解**：AspectJ 注解切面要生效，必须有 `<aop:aspectj-autoproxy/>`（XML）或 `@EnableAspectJAutoProxy`（JavaConfig）——忘了它切面全部不执行，代码无错但不拦截。

## 2. 一个完整切面

```java
@Aspect                       // 声明这是切面类
@Component                    // 作为 Spring bean 管理
public class LogAspect {

    // 切点：命中哪些方法
    @Pointcut("execution(* com.example.service.*.*(..))")
    public void svcPointcut() {}

    @Before("svcPointcut()")                       // 方法执行前
    public void logBefore(JoinPoint jp) {
        System.out.println("before " + jp.getSignature().getName());
    }

    @Around("svcPointcut()")                       // 环绕（最灵活）
    public Object logAround(ProceedingJoinPoint pjp) throws Throwable {
        System.out.println("进入 " + pjp.getSignature());
        Object ret = pjp.proceed();                // 放行目标方法，别忘了
        System.out.println("返回 " + ret);
        return ret;
    }
}
```

## 3. 切点表达式逐个含义（重点）

| 表达式片段 | 含义 |
| --- | --- |
| `execution(` | 方法执行切点 |
| `* com.example.service.*.*(..)` ↓ | modifiers 返回类型 包.类.方法(参数) |
| `* ` | 返回类型（`*`=任意，`void` 特指） |
| `com.example.service.*` | 类：`.*=`当前包，`..*`=含子包 |
| `.*.*(..)` | 方法：`.*`任意方法，`(..)`任意参数（`(String,..)` 首参 String） |
| `within(com.example..*)` | 按类类型切（不限方法） |
| `@annotation(com.a.Anno)` | 命中带指定注解的方法（配自定义注解很常用） |
| `@within(...)` / `@target(...)` | 类级注解 / 目标类注解 |

**常用模板**：
- `execution(* com.example.service..*.*(..))` → service 包及其子包所有方法
- `@annotation(com.example.Log)` → 所有标 `@Log` 的方法

## 4. 五种通知与执行顺序

| 通知 | 注解 | 时机 | 注意 |
| --- | --- | --- | --- |
| 前置 | `@Before` | 方法前 | 不能终止 |
| 后置 | `@AfterReturning` | 正常返回后 | 拿不到异常，拿返回值 `returning=` |
| 异常 | `@AfterThrowing` | 抛异常后 | `throwing="e"` 绑定异常 |
| 最终 | `@After` | 无论成败（finally） | |
| 环绕 | `@Around` | 全包（前+后+异常） | 必须调 `pjp.proceed()` |

> 多个切面多通知嵌套：默认按 `@Order` 值，小值先进（外）；`@Order(1)` 在前（更外）。

## 5. 取参数 / 返回值 / 异常

```java
@Before("svcPointcut() && args(id)")   // 取出参数 id（args 绑定）
public void before(Long id) { ... }    // 形参与 args 名对应

@AfterReturning(pointcut="svcPointcut()", returning="result")
public void after(Object result) { ... }   // result = 返回值

@AfterThrowing(pointcut="svcPointcut()", throwing="e")
public void catchErr(Exception e) { ... }  // e = 抛出的异常
```

**args 绑定的坑**：`args(id)` 必须先声明形参类型匹配，绑定不成功会抛 `IllegalStateException`——参数类型/顺序要跟方法签名一致。

## 6. 失效场景（重点）

- **同类内部调用**：`this.foo()` 调本类 `@Transactional/@Log` 方法，代理不经过 → 内部方法**不拦截**（自调用绕过代理）。要代理生效需注入自身或被外部调。
- **final 类/方法**：CGLIB 靠生成子类，`final` 无法被继承/重写 → 不能代理。
- **非 public**：Spring AOP 默认只拦 `public` 方法，private 不代理。
- **没开 `<aop:aspectj-autoproxy/>`**：切面类在但不生效。
- **切点范围没覆盖到**：`execution(* com.example.x.*(..))` 只匹配包内一层，子包方法不中（要 `..*`）。
- **静态/私有方法**：无法切。

## 7. 注意点与踩坑

- **`@Around` 忘调 `pjp.proceed()`**：目标方法不执行，接口静默返回 null。
- **事务切面 + 自定义切面顺序**：事务默认 `LOWEST_PRECEDENCE`；你自定义 `@Order` 更小，则通知在事务内执行（见详解 [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)）。
- **getSignature().getName() vs Long 全名**：`getName()` 只方法名。
- **切点用字符串无法编译期校验**，写错（如 `returning` 名不匹配）运行期才报 `error at ::0 0 formal unbound`——按上面表核对占位名。

## 8. 关联

- 详解：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)
- 下一篇：[09-Spring事务管理详解](09-Spring事务管理详解.md)（@Transactional 本质是一个 AOP 切面）
- 上一篇：[06-Spring与SpringMVC整合实践](06-Spring与SpringMVC整合实践.md)
