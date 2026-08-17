---
tags: [Java, Spring, SpEL, 表达式, 注解, AOP]
创建日期: 2026-08-08
更新日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# SpEL表达式详解

> 前置知识：[Java注解机制详解](../../JDK基础库/核心机制/Java注解机制详解.md)（注解元数据 + 处理者）、[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（@annotation 切点读注解）
> 关联笔记：[Java反射详解](../../JDK基础库/核心机制/Java反射详解.md)（反射取参名）、[11-SpEL表达式详解](11-SpEL表达式详解.md)（本文）实际是被注解取参场景引用
> 主题范围：SpEL 语法基础、在 Spring 注解（@Cacheable/@Idempotent）中取参、在 AOP 切面中手动解析 SpEL、与 OGNL/JSP EL 对比

## 📋 总纲

1. SpEL 是什么：Spring 表达式语言
2. 语法基础：字面量 / 属性 / 方法 / 集合 / 三目 / 安全导航
3. 典型场景一：注解内联取参（@Cacheable/@Value/@Idempotent）
4. 典型场景二：AOP 切面中手动解析 SpEL（核心，含完整代码）
5. 上下文变量：#root / 方法参数 / 返回值
6. 与 OGNL / JSP EL 对比
7. 常见坑

## 1. 学习目标

1. 写出 `#order.userId` 这类注解取参表达式
2. 在 AOP 切面里用 `ExpressionParser` 解析注解上的 SpEL 字符串取方法参数
3. 区分 SpEL 与 OGNL/EL 的定位差异
4. 处理 SpEL 解析失败的常见坑

## 2. 前置知识

- [Java注解机制详解](../../JDK基础库/核心机制/Java注解机制详解.md)：理解注解只是元数据、处理者赋予意义（SpEL 就是注解 key 的处理者）
- [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)：@annotation 切点把注解实例绑定进切面

## 3. 核心知识点

### 3.1 SpEL 是什么

**是什么**：SpEL（Spring Expression Language）是 Spring 内置的表达式语言，可在运行时求值对象属性、方法调用、集合运算、逻辑判断。写法 `#{...}`（配置占位）或字符串表达式。

**为什么**：注解/配置里的 key 往往依赖方法运行时参数（如幂等键取 `userId`），但注解是静态元数据拿不到参数——需要一个"运行时从参数里取值的表达式"，SpEL 就是这个桥。

**怎么用**：核心三个组件——`ExpressionParser` 解析器、`StandardEvaluationContext` 上下文（放入参数/对象）、`Expression` 求值。

### 3.2 语法基础

| 语法 | 写法 | 求值结果 |
| --- | --- | --- |
| 字面量 | `'hello'`、`123`、`true` | 常量 |
| 属性访问 | `#order.userId` | 调用 getUserId() |
| 方法调用 | `#order.getId().length()` | 链式调用 |
| 集合/数组 | `#ids[0]`、`#list.?[price>100]` | 取元素/过滤 |
| 三目 | `cond ? a : b` | 条件选择 |
| 安全导航 | `#user?.name` | null 时返回 null 不抛 NPE |
| Elvis | `#name ?: '默认值'` | null/空用默认 |
| 拼接 | `#a + '_' + #b` | 字符串拼接 |
| 正则 | `'abc' matches '^a.*'` | 布尔 |

`#变量` 前缀表示从上下文取变量（方法参数/自定义变量）；`@bean` 前缀引用容器 Bean。

### 3.3 场景一：注解内联取参

Spring 的注解 key 支持 SpEL，运行时用方法参数求值：

```java
@Cacheable(cacheNames = "user", key = "#userId")        // 取参数 userId
@Cacheable(cacheNames = "user", key = "#order.userId")  // 取参数 order 的属性
@Value("#{systemProperties['user.region']}")            // 取系统属性
```

关键：注解里的 `#参数名` 由 Spring 的注解处理逻辑解析，参数名通过 `ParameterNameDiscoverer`（默认 -parameters 编译或 LocalVariableTable）拿到。

### 3.4 场景二：AOP 切面手动解析 SpEL（核心）★

注解方法上 SpEL 的 key 字符串，切面里需要**手动解析**（Spring 不会自动帮你解析自定义注解的 key）：

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Idempotent {
    String key();            // SpEL 表达式，如 "#order.userId"
    int expireSeconds() default 10;
}

@Aspect
@Component
public class IdempotentAspect {
    @Autowired private StringRedisTemplate redis;

    @Around("@annotation(idempotent)")
    public Object guard(ProceedingJoinPoint pjp, Idempotent idempotent) throws Throwable {
        String key = parseKey(idempotent.key(), pjp);   // ① 解析 SpEL 取参
        Boolean acquired = redis.opsForValue()
            .setIfAbsent("idem:" + key, "1", idempotent.expireSeconds(), TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(acquired)) {
            throw new BusinessException("duplicate request within window");
        }
        try { return pjp.proceed(); } finally { /* 成功删 key 或保留到过期 */ }
    }

    private String parseKey(String expression, ProceedingJoinPoint pjp) {
        // ① 取方法签名与方法对象
        MethodSignature sig = (MethodSignature) pjp.getSignature();
        Method method = sig.getMethod();
        // ② 用参数名发现器拿到方法参数名（需 -parameters 编译参数）
        ParameterNameDiscoverer pnd = new DefaultParameterNameDiscoverer();
        String[] paramNames = pnd.getParameterNames(method);
        Object[] args = pjp.getArgs();

        // ③ 构造求值上下文，把参数放进变量
        EvaluationContext ctx = new StandardEvaluationContext();
        if (paramNames != null) {
            for (int i = 0; i < paramNames.length; i++) {
                ctx.setVariable(paramNames[i], args[i]);
            }
        }
        // ④ 解析并求值
        ExpressionParser parser = new SpelExpressionParser();
        return parser.parseExpression(expression).getValue(ctx, String.class);
    }
}
```

> **要点**：① 切面拿不到方法参数值，得 `pjp.getArgs()`；② 参数名要 `DefaultParameterNameDiscoverer` 从字节码或 -parameters 取；③ `StandardEvaluationContext.setVariable` 把参数以 `#参数名` 注入；④ `parseExpression().getValue(ctx, String.class)` 求值转 String。完整幂等闭环见 [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md) 知识点五。

### 3.5 上下文变量与返回值

| 变量 | 含义 | 示例 |
| --- | --- | --- |
| `#root` | 根对象 | `#root.toString()` |
| 方法参数 | `#参数名` | `#order.userId` |
| 自定义 | ctx.setVariable | `#customVar` |
| 返回值 | 某些注解 | `@CachePut(key="#result.id")` |
| 当前用户/请求 | SecurityContext 支持 | 需扩展上下文 |

### 3.6 与 OGNL / JSP EL 对比

| 维度 | SpEL | OGNL | JSP EL |
| --- | --- | --- | --- |
| 归属 | Spring 生态 | 独立库（Struts2/OGNL） | JSP 规范 |
| 写法 | `#var.prop` | `#var.prop` | `${var.prop}` |
| 能力 | 强（集合投影/方法调用） | 强 | 弱（只读导航） |
| 典型场景 | Spring 注解/配置 | 模板/OGNL 表达式 | JSP 页面 |
| 注意 | 需解析器 | 有安全历史漏洞 | 仅视图层 |

## 4. 最佳实践

- 注解 key 尽量简单（属性访问级），复杂逻辑放切面代码而非 SpEL
- 编译加 `-parameters`，保证反射能拿到参数名（否则 `#order` 这种取参失效）
- 幂等键组合多字段：`#order.userId + '_' + #order.goodsId`
- 对不可信外部输入的 SpEL 求值要防注入（SpEL 可执行任意方法）

## 5. 常见踩坑

- **参数名拿不到** → SpEL 取参为空/null，需 `-parameters` 编译或确认 ParameterNameDiscoverer
- **`#` 忘写** → 当普通字符串不解析，key 恒为字面量
- **NPE** → 属性为 null，用安全导航 `?.`
- **SpEL 注入** → 外部可控表达式可调用任意 Bean 方法，勿对不可信输入求值
- **表达式解析性能** → 高频路径缓存 `Expression` 对象，避免每次 reparse

## 6. 小结

- SpEL = Spring 运行时表达式语言，`#参数` 从上下文取值。
- 核心：ExpressionParser + StandardEvaluationContext + Expression。
- 注解内联 key 由 Spring 自动解析；自定义注解需切面手动 `parseExpression().getValue(ctx)`。
- 参数名靠 -parameters；安全导航 `?.` 防空指针。

## 7. 关联笔记

- [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)：@Idempotent 注解 + 切面完整落地（本文是其 SpEL 取参支撑）
- [Java注解机制详解](../../JDK基础库/核心机制/Java注解机制详解.md)：注解元数据 + 处理者概念
- [Java反射详解](../../JDK基础库/核心机制/Java反射详解.md)：反射 getAnnotation / 参数名获取
- [05-分布式ID与幂等设计详解](../../../分布式/核心原理/05-分布式ID与幂等设计详解.md)：幂等原理（跨语言）

## 8. 参考资料

- [Spring 官方文档：Spring Expression Language](https://docs.spring.io/spring-framework/reference/core/expressions.html)，查询日期 2026-08-08
- [Spring SpEL 语法详解（个人/社区整理）]，查询日期 2026-08-08

---
- 上一篇：[10-Spring事务管理实践](10-Spring事务管理实践.md)
- 下一篇：[12-SpEL表达式实践](12-SpEL表达式实践.md)（本知识点代码实盀）
