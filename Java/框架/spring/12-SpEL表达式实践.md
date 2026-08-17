---
tags: [Java, Spring, SpEL, 实践, @Value, 表达式]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# SpEL表达式实践

> 版本基线：Spring 5.x。先读 [11-SpEL表达式详解](11-SpEL表达式详解.md)；本篇给 @Value/#{} 最常用的写法与 SpEL 语法速查。
> 前置：[11-SpEL表达式详解](11-SpEL表达式详解.md)。

## 📋 总纲

1. @Value 两种引用（${} vs #{}）辨析
2. SpEL 坐标 / 运算符 / 方法调用
3. 在注解里的典型用法
4. 注意点与踩坑

## 1. @Value：${} 与 #{} 辨析（核心）

| 写法 | 含义 | 示例 |
| --- | --- | --- |
| `${app.name}` | **Spring 占位符**：读配置文件 property | `@Value("${app.name}") String name;` |
| `#{...}` | **SpEL 表达式**：求值 Java 表达式 | `@Value("#{systemProperties['os.name']}")` |
| `${a:default}` | 占位符带默认值（冒号后） | `@Value("${retry.count:3}")` |
| `${a}${b}` | 占位符拼接 | |
| `#{'str1'+'str2'}` | SpEL 字符串拼接 | |

> **区别一句话**：`${}` 是"读配置"，`#{}` 是"算表达式"。配置中引用另一个 key 或做运算，必须 `#{}` 包 `${}`：`#{'${host}:${port}'}`。

## 2. SpEL 常用语法速查

```java
@Value("#{100 + 20}")                                           // 算术 → 120
@Value("#{T(java.lang.Math).PI}")                                // 静态字段/方法 T(...)
@Value("#{beanName.method()}")                                   // 调用另一个 bean 的方法
@Value("#{list.contains('a')}")                                  // 集合方法
@Value("#{config.retry > 3 ? '高' : '低'}")                      // 三元
@Value("#{@dataSource.password}")                                // @bean 引用（@前缀）
@Value("#{systemEnvironment['HOME']}")                           // 系统环境变量
@Value("#{new java.util.Date()}")                                // new 对象
```

**`@beanName.方法()` 的坑**：`#{beanName.method()}` 里 `beanName` 是 Spring bean 的 **id**（可用 `@` 强调 `#{@beanName.method()}`，Spring 自动注入该 bean 再调）。

## 3. 典型注解用法（AOP/缓存/条件里很常用）

```java
// 切点表达式里用 SpEL（配自定义注解参数）
@annotation(log) && args(order)   // 见 AOP 实践 args 绑定

// @Cacheable 里 SpEL 生成 key
@Cacheable(key = "#id")                               // 方法参数 id 作 key
@Cacheable(key = "#user.id + '-' + #user.name")       // 拼接
@Cacheable(key = "#root.methodName")                  // 内置变量 root

// @Scheduled 表达式
@Scheduled(cron = "#{'${cron.exp}'}")                 // cron 从配置读
```

## 4. 注意点与踩坑

- **`#id` 能否取到**：方法参数要在 `@Cacheable/#{}` 可见，参数得有名字（编译 `-parameters` 或注解）否则取不到报错。
- **`${}` 找不到 key**：没配默认值启动直接报 `Could not resolve placeholder`；要么给默认值 `:`,要么确认 key 在配置里。
- **SpEL 抛空/类型错**：表达式写错在 **Bean 初始化时执行**，启动即报错；调 bean 方法返回类型与注入类型不一致。
- **性能**：反射调用 SpEL 有开销，热路径尽量静态绑定或用参数直接取，别滥用表达式。
- 参考：详解 [11-SpEL表达式详解](11-SpEL表达式详解.md) 有完整语法表。

## 5. 关联

- 详解：[11-SpEL表达式详解](11-SpEL表达式详解.md)
- 上一篇：[10-Spring事务管理实践](10-Spring事务管理实践.md)
- 下一篇：[13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md)
