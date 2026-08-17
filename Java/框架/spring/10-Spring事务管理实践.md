---
tags: [Java, Spring, 事务, 实践, Transactional, 传播, 隔离]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring事务管理实践

> 版本基线：Spring 5.x + 声明式事务（@Transactional）。先读 [09-Spring事务管理详解](09-Spring事务管理详解.md)。
> 前置：[09-Spring事务管理详解](09-Spring事务管理详解.md)（@Transactional 本质是 AOP 切面）；本篇给"怎么配 + 传播/隔离属性值含义 + 失效排查"。

## 📋 总纲

1. 事务管理器配置（XML + JavaConfig）
2. 开启注解事务
3. @Transactional 属性逐个含义
4. 传播行为 7 种速查
5. 隔离级别 & 回滚规则
6. 失效场景排查（重点）
7. 注意点与踩坑

## 1. 事务管理器配置

```xml
<!-- 数据源 -->
<bean id="dataSource" class="com.zaxxer.hikari.HikariDataSource">...</bean>

<!-- 事务管理器，绑定数据源 -->
<bean id="txManager" class="org.springframework.jdbc.datasource.DataSourceTransactionManager">
    <property name="dataSource" ref="dataSource"/>
</bean>

<!-- 开启注解驱动事务：@Transactional 生效的关键 -->
<tx:annotation-driven transaction-manager="txManager"/>
```

> 📌 **必须两步**：事务管理器**(1)** + 开启注解**(2)**。只配管理器没开 `tx:annotation-driven`（或 JavaConfig 的 `@EnableTransactionManagement`）→ `@Transactional` 完全不生效。

JavaConfig 版：
```java
@Configuration
@EnableTransactionManagement
public class TxConfig {
    @Bean
    public PlatformTransactionManager txManager(DataSource ds) {
        return new DataSourceTransactionManager(ds);
    }
}
```

## 2. @Transactional 属性逐个含义

```java
@Transactional(propagation = Propagation.REQUIRED,   // 传播行为
               isolation  = Isolation.DEFAULT,       // 隔离级别
               timeout    = 30,                      // 秒，超时回滚
               readOnly   = false,                   // 只读优化
               rollbackFor = Exception.class,        // 哪些异常回滚
               noRollbackFor = IllegalStateException.class)  // 哪些不回滚
public void transfer(...) {}
```

| 属性 | 取值 | 含义 |
| --- | --- | --- |
| `propagation` | REQUIRED(默认) 等 | 事务传播：见下 |
| `isolation` | DEFAULT/READ_COMMITTED 等 | 隔离级别，DEFAULT=用 DB 默认 |
| `timeout` | 秒 | 超时自动回滚 |
| `readOnly` | true/false | 只读，DB/连接池可优化，写操作会报错 |
| `rollbackFor` | 异常类型 | **默认只回滚 RuntimeException/Error**；checked 异常不回滚（需显式 rollbackFor） |
| `noRollbackFor` | 异常类型 | 指定异常即使抛也不回滚 |

> ⚠️ **最大坑**：`@Transactional` **默认只回滚运行时异常**，`Exception`（checked）不回滚！写文件/IO 抛 `Exception` 时发现没回滚，就是忘了 `rollbackFor=Exception.class`。

## 3. 传播行为 7 种速查

| 传播 | 含义 | 场景 |
| --- | --- | --- |
| `REQUIRED`(默认) | 有就用当前事务，没有新建 | 普通 |
| `REQUIRES_NEW` | **总是新开**事务，挂起当前 | 独立记录日志，自身失败不影响外层 |
| `NESTED` | 嵌套事务，外层失败内层也回滚 | 保存点回滚 |
| `SUPPORTS` | 有事务就在事务里，没有也行 | 只读查询 |
| `NOT_SUPPORTED` | 总在非事务下执行 | 无事务方法 |
| `MANDATORY` | 必须已有事务，否则报错 | 强制事务内 |
| `NEVER` | 必须无事务，否则报错 | 禁止事务 |

**REQUIRED vs REQUIRES_NEW**：REQUIRED 加入同一事务（同滚）；REQUIRES_NEW = 新事务物理独立，内外互不影响。同库内 REQUIRES_NEW 会因锁等待超时，注意。

## 4. 隔离级别 & 回滚规则（简）

- 隔离级别 4 大：READ_UNCOMMITTED（脏读）/ READ_COMMITTED（默认常见）/ REPEATABLE_READ / SERIALIZABLE——越高并发越低越安全，见详解。
- **回滚触发**：`rollbackFor=Exception.class` 覆盖 checked；`noRollbackFor` 豁免个别；默认 RuntimeException/Error。
- **try-catch 在方法内部**：事务切面只看抛没抛异常——你在方法里 `catch` 住就**不回滚**。

## 5. 失效场景排查（重点）

| 场景 | 会失效吗 | 原因/对策 |
| --- | --- | --- |
| 没配管理器或没开 `tx:annotation-driven` | ❌ 完全不生效 | 补配置 |
| 非 public 方法 | ❌ | 默认只拦 public |
| **同类自调用** `this.b()` | ❌ | 自调用绕过代理，注自身或拆分 |
| final 方法/类 | ❌ | 无法生成代理子类 |
| checked 异常 | ⚠️ 默认不回滚 | 加 `rollbackFor=Exception.class` |
| 方法内 try-catch 吞了异常 | ❌ 不回滚 | 别在事务方法内 catch |
| 多容器重复扫描 service | ⚠️ 面错实例 | 事务切面没贴到被用的实例，见整合实践 |

**自调用**是线上最常见"事务没生效"：`A.saveOrder()` 调 `this.doInner()`，内部 `doInner` 上的 `@Transactional` 因没经过代理**不生效**。
```java
@Service
public class OrderService {
    public void saveOrder() { this.refund(); }   // this 调，refund 的事务不受控
    @Transactional
    public void refund() { ... }
}
// 修：注入 self 再用，或把 refund 拆到另一个 bean/接口
```

## 6. 注意点与踩坑

- **回滚只针对 RuntimeException(默认)**：手写 checked 场景务必备 `rollbackFor`。
- **事务方法要短**：长事务持锁久，高并发性能与死锁风险上升。事务内别做外部调用/耗时 IO（把非必要逻辑移出）。
- **延迟/异步 vs 事务**：`@Async` 子线程无外层事务上下文，`REQUIRED` 会新建；跨线程事务不共享。
- **只读 + 写**：`readOnly=true` 里写 DB 会报错或忽略。
- **嵌套事务锁**：同库内 REQUIRES_NEW 嵌套可能锁等待超时——考虑 NESTED 或重构。

## 7. 关联

- 详解：[09-Spring事务管理详解](09-Spring事务管理详解.md)
- 上一篇：[08-Spring核心·AOP实践](08-Spring核心·AOP实践.md)（事务切面就落在 AOP）
- 下一篇：[11-SpEL表达式详解](11-SpEL表达式详解.md)
