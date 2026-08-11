---
tags: [Java, Spring, AOP, 切面, 动态代理, CGLIB, 切点, 通知]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Java AOP详解

> 前置知识：**Java注解机制详解**（见知识库）（注解如何被处理）、**Java代理详解**（见知识库）（动态代理基础）
> 关联笔记：[05-Spring事务管理详解](05-Spring事务管理详解.md)（AOP 的典型应用）、**Java Agent与字节码增强详解**（见知识库）（另一种增强方式）

## 📋 总纲

1. AOP 概念：横切关注点与六个核心术语
2. Spring AOP 原理：JDK 动态代理 vs CGLIB
3. 五种通知类型与执行顺序
4. 切点表达式：execution / @annotation / within 等
5. 完整示例：自定义注解 + 切面闭环
6. Spring AOP vs AspectJ：三种织入方式
7. 常见误区与失效场景

## 一、AOP 概念

AOP（Aspect Oriented Programming，面向切面编程）：把**横切关注点**（日志、事务、权限、监控——散落在所有业务方法里的共性逻辑）从业务代码中抽离，统一织入。

| 术语 | 说明 | 类比 |
| --- | --- | --- |
| 切面 Aspect | 横切逻辑的模块化（@Aspect 类） | 规则集合 |
| 连接点 JoinPoint | 可被拦截的位置（Spring AOP 仅方法） | 候选点 |
| 切点 Pointcut | 匹配连接点的表达式（哪些方法被拦） | 筛选规则 |
| 通知 Advice | 拦截后执行的动作（@Before/@Around 等） | 具体逻辑 |
| 目标对象 Target | 被代理的业务 Bean | - |
| 织入 Weaving | 把通知应用到目标的过程 | 生效动作 |

## 二、Spring AOP 原理：动态代理

Spring AOP 的本质：**为匹配切点的 Bean 创建代理对象，替代原始 Bean 注入容器**。调用方法时先走代理，代理按切点匹配执行通知链，再调用真实方法。

### JDK 动态代理 vs CGLIB

| 维度 | JDK 动态代理 | CGLIB |
| --- | --- | --- |
| 原理 | 实现目标类的接口，Proxy + InvocationHandler | 生成目标类的**子类**，方法拦截 |
| 要求 | 目标必须实现接口 | 无接口要求；final 类/方法无法代理 |
| 性能 | 代理类生成快，调用稍慢 | 生成慢，调用快（Spring 6 优化后接近） |
| 选择 | 默认（有接口时） | 无接口时自动用；**Spring Boot 2.x+ 默认强制 CGLIB** |

注意：Spring Boot 2.x 起默认 `spring.aop.proxy-target-class=true`（CGLIB），不再依赖接口——因此**自调用失效**问题在 Boot 项目里普遍存在（见下文误区）。

### 代理链

多个切面命中同一方法时组成**责任链**：按 @Order 排序（数值小优先，默认无序），@Around 通知层层包裹，最内层执行真实方法。@Transactional 本身就是一个内置切面（Ordered.LOWEST_PRECEDENCE 附近），所以自定义切面与其顺序由 @Order 决定（见 [05-Spring事务管理详解](05-Spring事务管理详解.md)）。

## 三、五种通知类型与执行顺序

| 通知 | 注解 | 执行时机 | 典型场景 |
| --- | --- | --- | --- |
| 前置 | @Before | 方法调用前 | 校验、鉴权 |
| 后置 | @After | 方法结束后（无论成败） | 清理资源 |
| 返回后 | @AfterReturning | 正常返回后（可拿返回值） | 记录结果 |
| 异常后 | @AfterThrowing | 抛出异常后 | 告警 |
| 环绕 | @Around | 完全包裹（可控制是否执行） | 事务、幂等、限流 |

```java
@Aspect
@Component
@Order(1)                       // 切面排序，小值先执行
public class LogAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object around(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = pjp.proceed();          // 调用链继续（执行真实方法）
        long cost = System.currentTimeMillis() - start;
        System.out.println(pjp.getSignature().getName() + " cost " + cost + "ms");
        return result;
    }
}
```

@Around 中调用 `pjp.proceed()` 才执行真实方法；不调用则"短路"（幂等拦截重复请求就是靠不 proceed 直接抛异常）。

## 四、切点表达式

| 表达式 | 匹配 | 示例 |
| --- | --- | --- |
| execution | 方法签名 | `execution(* com.example.service.OrderService.*(..))` |
| within | 类型内所有方法 | `within(com.example.service..*)` |
| @annotation | 方法带指定注解 | `@annotation(com.example.LogExec)` |
| @within | 类带指定注解 | `@within(org.springframework.stereotype.Service)` |
| args | 参数类型 | `args(String, ..)` |
| bean | Bean 名 | `bean(orderService)` |
| 组合 | && \|\| ! | `@annotation(log) && execution(public * *(..))` |

`@annotation(注解类型)` 切点可直接把注解对象绑定进通知方法参数：

```java
@Around("@annotation(logExec)")     // 命中带 @LogExec 的方法，并注入注解实例
public Object around(ProceedingJoinPoint pjp, LogExec logExec) throws Throwable {
    System.out.println("log tag: " + logExec.value());   // 读取注解属性
    return pjp.proceed();
}
```

这就是"注解 + AOP"的经典组合：**注解只是标记，切面通过 @annotation 切点读取它并赋予行为**（呼应 **Java注解机制详解**（见知识库） 的"处理者"概念）。

## 五、完整示例：注解 + 切面闭环

接口幂等拦截（完整闭环，来自 **Java注解机制详解**（见知识库） 的面试场景）：

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)      // 必须 RUNTIME
public @interface Idempotent {
    String key();                         // SpEL 表达式计算幂等键（见 [06-SpEL表达式详解](06-SpEL表达式详解.md)）
    int expireSeconds() default 10;
}

@Aspect
@Component
public class IdempotentAspect {
    @Autowired private StringRedisTemplate redis;

    @Around("@annotation(idempotent)")
    public Object guard(ProceedingJoinPoint pjp, Idempotent idempotent) throws Throwable {
        String key = spel(pjp, idempotent.key());       // SpEL 解析业务键
        Boolean acquired = redis.opsForValue()
            .setIfAbsent("idem:" + key, "1", idempotent.expireSeconds(), TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(acquired)) {
            throw new BusinessException("duplicate request within window");  // 不 proceed = 短路
        }
        try {
            return pjp.proceed();         // 首个请求放行
        } finally {
            // 成功删除 key 允许重试，或保留到过期，业务决策
        }
    }
}
```

要点：@Around 的"短路"能力（不调 proceed）是拦截类功能的根基；SpEL 取参细节见 [06-SpEL表达式详解](06-SpEL表达式详解.md)；幂等原理与四大实现见 **05-分布式ID与幂等设计详解**（见知识库）（跨语言），本段是其 Spring 注解式落地。

## 六、Spring AOP vs AspectJ

| 维度 | Spring AOP | AspectJ |
| --- | --- | --- |
| 织入方式 | **运行期动态代理**（JDK/CGLIB） | 编译期/加载期织入（改字节码） |
| 连接点 | 仅 Spring 管理的 public 方法 | 字段、构造器、static、任意方法 |
| 自调用 | 不支持（代理外调用无效） | 支持（织入字节码） |
| 性能 | 反射/代理调用开销 | 织入后无运行时开销 |
| 使用 | Spring 项目标配 | 需编译器插件/agent，重 |

结论：Spring 项目 99% 场景用 Spring AOP 即可；AspectJ 的编译期织入只在需要"自调用也生效/字段级拦截"时考虑。

## 七、常见误区与失效场景

① **自调用失效（最经典）**：`this.xxx()` 调用不走代理，切面不生效。同类内 `@Transactional`/`@Idempotent` 方法互相调用即失效。解法：注入自身代理、拆到别的 Bean、或 AopContext.currentProxy()（需 exposeProxy=true）。

② **非 public 方法**：Spring AOP 只代理 public 方法（CGLIB 对 protected/public 可增强但惯例 public）。

③ **final 类/方法**：CGLIB 靠继承，final 无法代理（Spring 6 起对 final 方法有部分支持，但别依赖）。

④ **切点表达式写错**：`@annotation` 必须用全限定名；execution 修饰符/包名笔误 → 静默不拦截（无报错，排查最坑）。

⑤ **对象没进容器**：new 出来的对象不走代理，必须由 Spring 管理。

⑥ **多个切面顺序混乱**：不配 @Order 时执行顺序不确定，事务与自定义切面的嵌套顺序需显式控制。

## 参考资料

- [Spring 官方文档：AOP 章节](https://docs.spring.io/spring-framework/reference/core/aop.html)，查询日期：2026-08-08
- [Spring AOP 实现原理（阿里云开发者社区）](https://developer.aliyun.com/article/1662505)，查询日期：2026-08-08
- [深度解析 Spring AOP 核心原理与源码（腾讯云）](https://cloud.tencent.com/developer/article/2560612)，查询日期：2026-08-08
- 关联：**Java代理详解**（见知识库）（JDK 动态代理/CGLIB 原理）、**Java注解机制详解**（见知识库）（注解如何被切面读取）
