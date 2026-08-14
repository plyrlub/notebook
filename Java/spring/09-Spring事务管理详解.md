---
tags: [Java, Spring, 事务, Transactional, 传播行为, 回滚, AOP]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring事务管理详解

> 前置知识：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（@Transactional 本质是一个 AOP 切面）、**Java注解机制详解**（见知识库）（注解如何被处理）
> 关联笔记：**Java代理详解**（见知识库）（代理机制）、**Java参数校验详解**（见知识库）（同属 springboot 框架知识域）

## 📋 总纲

1. 事务基础：ACID 与编程式/声明式对比
2. @Transactional 原理：AOP 代理 + 事务管理器
3. 传播行为：7 种传播机制全解
4. 回滚规则：默认回滚什么、rollbackFor 怎么配
5. 隔离级别与数据库对应
6. 失效场景（重点）：12 类逐个拆解
7. 接口 vs 类注解、常见坑

## 一、事务基础

事务（Transaction）：一组要么全部成功、要么全部回滚的操作。ACID：原子性、一致性、隔离性、持久性。

| 方式 | 实现 | 适用 |
| --- | --- | --- |
| 编程式 | TransactionTemplate / PlatformTransactionManager 手动 begin/commit/rollback | 灵活控制、动态边界 |
| 声明式 | @Transactional 注解（AOP 自动管理） | 默认首选，声明即生效 |

Spring 声明式事务的核心：**@Transactional 只是一个标记，真正生效靠 AOP 代理**（呼应 **Java注解机制详解**（见知识库）："注解只是元数据，处理者赋予意义"）。

## 二、@Transactional 原理

```
调用方 → 代理对象（@Transactional 切面）
          ├─ 事务管理器开启事务（connection.setAutoCommit(false)）
          ├─ 执行业务方法
          ├─ 无异常 → commit
          └─ 可回滚异常 → rollback
```

关键组件：

| 组件 | 职责 |
| --- | --- |
| 事务管理器 PlatformTransactionManager | 数据源事务 DataSourceTransactionManager / JPA/JTA 各自实现 |
| 事务切面 | 拦截 @Transactional 方法，编排 begin/commit/rollback |
| 事务状态 TransactionStatus | 当前事务上下文（传播行为依赖它判断"已有事务"） |
| 事务同步管理器 | ThreadLocal 保存当前事务，同线程共享 |

**为何 @Transactional 不依赖 @Inherited**：Spring 自己扫描目标类及其父类/接口方法上的注解（Spring 5.3+ 默认注解继承查找包括接口），而不是靠 Java 的 @Inherited（那只对类级别生效）。所以子类方法、甚至接口方法上的 @Transactional 都可能被识别——但**实际建议标在实现类方法上**（见第七节）。

## 三、传播行为（7 种）

### 3.1 前提：什么叫"已有事务"

**"已有事务" = 当前线程进入此方法时，已被更外层 `@Transactional` 方法新建并绑定的那本事务包裹着**。它是传播行为表格中"已有事务时"列的判断前提。

**判断来源——事务同步管理器 `TransactionSynchronizationManager`**：用 **ThreadLocal** 保存"当前线程正在执行的事务资源"。只要有事务方法开了一道门，当前线程就被标记为"已有事务"；没有则视作"无事务"。

- 当前线程若无事务资源 → 视为"无事务"（最外层时）
- 当前线程若已被外层事务方法绑定 → 视为"已有事务"（嵌套时）
- 事务资源随事务方法**返回而释放**，不赖在当前线程上

**事务生命周期（方法级，不是线程级）**：

| 维度 | 线程 | 事务 |
| --- | --- | --- |
| 生命周期 | 贯穿整个请求/任务 | **仅在最外层 `@Transactional` 方法执行期间** |
| 谁创建/结束 | 容器/线程池持有 | 进入事务方法新建、返回即提交/回滚 |
| 绑定 | 线程存在就有 | 方法执行期间才绑 ThreadLocal，返回即解除 |

**何时"有门" vs "没门"**：

```java
@Transactional
public void A() {          // 进入：无事务 → 新建 T，绑定当前线程
    dao.update();          // 处于 T 门内
}                          // A() 返回 → 提交/回滚 T，解除绑定（门关）

public void B() {          // 普通方法（无 @Transactional）
    // 当前线程已"没门"：A() 虽然刚返回，B() 也看不到任何事务
}
```

门只跟着"最外层事务方法"走，不是跟着方法数量：
**在一个事务方法没返回期间，内部调用的所有普通方法都处于该事务门内；一旦最外层事务方法返回，门即关闭，后续调用全是普通方法——除非再进一个新的 `@Transactional` 方法重新开门**。

> ⚠️ 自助调失效关系：若内层 `@Transactional` 因**同类 `this` 自调用**而没走代理，它不会新建事务，而是直接加入外层已有事务（见失效场景 ⑥）。

### 3.2 七种传播行为

| 传播行为          | 已有事务时           | 无事务时     | 场景                          |
| ------------- | --------------- | -------- | --------------------------- |
| REQUIRED（默认）  | 加入当前事务          | 新建事务     | 绝大多数业务                      |
| REQUIRES_NEW  | **挂起当前，新建独立事务** | 新建事务     | **审计/流水**日志记录<br>（失败不影响主事务） |
| SUPPORTS      | 加入              | 以非事务方式执行 | 查询（有事务就参与）                  |
| NOT_SUPPORTED | 挂起当前，非事务执行      | 非事务      | 大查询释放连接                     |
| MANDATORY     | 加入              | **抛异常**  | 强制要求已有事务                    |
| NEVER         | **抛异常**         | 非事务      | 禁止事务环境                      |
| NESTED        | 创建**保存点**（嵌套）   | 新建事务     | 部分回滚（子事务失败只回滚子段）            |

```java
// 经典组合：主业务 REQUIRED + 日志 REQUIRES_NEW
@Transactional(propagation = Propagation.REQUIRED)
public void biz() {
    orderDao.update();       // 主事务
    logService.save();       // 独立事务：失败不回滚主事务
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void save() { ... }
```

注意：NESTED 依赖数据库保存点（savepoint）能力，与 REQUIRES_NEW 不同——REQUIRES_NEW 是两套独立事务，NESTED 是同一事务内的保存点回滚。

#### 3.2.1 REQUIRES_NEW / NESTED 的代价

| 方案 | 连接数 | 回滚粒度 | 独立提交 | 代价 |
| --- | --- | --- | --- | --- |
| REQUIRED（全包） | 1 | 全回滚 | 否 | 最短 |
| **REQUIRES_NEW**（另开连接） | 峰值 **+1** | 子段独立 | **能** | 多占连接 + 拉长主事务 |
| **NESTED**（保存点） | 1 | 子段 `ROLLBACK TO savepoint` | 不能（跟随外层） | 保存点 write/undo 开销 |

- **REQUIRES_NEW 的"另开连接"**：
  从连接池再拿一条独立待机的连接承载全新事务（可能复用到同一条物理连接对象，但语义是独立事务）；MySQL 不支持 begin 嵌套，故必须另拿连接；Oracle 不豁免——REQUIRES_NEW 同样另拿连接。所谓"同一条连接"是连接对象复用，**不是**同连接上 `begin;begin` 嵌套。
- **NESTED 的"保存点"**：
  同一条连接上用 `SAVEPOINT`（Oracle/MySQL 均支持），子段失败 `ROLLBACK TO savepoint` 只回滚子段；但子段不能独立提交（随外层），且有 undo 累积开销。
- **性能铁律**：REQUIRES_NEW 贵在**多占连接 + 主事务被拉长**（夹提交点时主连接持有时间变长、锁/undo 占用久）；NESTED 贵在**保存点 undo**。二者都是"用性能换独立性"。
- **反模式**：
  在 for 循环里反复调 REQUIRES_NEW（每次另拿连接+独立提交）会严重劣化——应改批量/自定义保存点。同理，想"缩短当前事务"应去事务/换 NOT_SUPPORTED，而不是 REQUIRES_NEW（那恰恰是延长）。

## 四、回滚规则

**默认规则**：只回滚 `RuntimeException` 及其子类和 `Error`；**受检异常（Exception 子类）不回滚**——这是最高频的"事务没生效"误解。

```java
@Transactional
public void a() { throw new RuntimeException("滚"); }        // ✓ 回滚

@Transactional
public void b() throws Exception { throw new Exception("不滚"); }  // ✗ 不回滚！

// 修正：
@Transactional(rollbackFor = Exception.class)
public void c() throws Exception { throw new Exception("滚"); }    // ✓ 回滚

// 指定不回滚：
@Transactional(noRollbackFor = BusinessException.class)
public void d() { throw new BusinessException("不滚"); }
```

要点：业务异常自定义类时，要么继承 RuntimeException，要么显式 rollbackFor；`rollbackFor = Exception.class` 是覆盖受检异常的常规写法。

## 五、隔离级别

> 📌 **通用知识**：四隔离级别表、脏读/不可重复读/幻读定义、各库默认隔离级别对比见 **[01-关系型DB事务详解](../../数据库/DB通用理论/01-关系型DB事务详解.md) §4 / §5**。本节只讲 Spring 层的配置入口。

Spring 通过 `@Transactional(isolation=...)` 指定当前事务的隔离级别（对应数据库的 four-level 模型）：

```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void query() { ... }
```

**结果性要点**：Spring 默认 `Isolation.DEFAULT`（沿用数据库默认）；MySQL InnoDB 默认 `REPEATABLE_READ`，但靠 MVCC + 间隙锁实际避免了大部分幻读（PG 默认 `Read Committed`）。

## 六、失效场景（重点 ★）

① **自调用**（最经典）：`this.save()` 同类内调用，不走代理，切面不生效。

```java
@Service
public class OrderService {
    public void outer() { this.inner(); }        // ✗ 自调用，事务失效
    @Transactional
    public void inner() { ... }
}
// 解法：注入自身代理 / 拆到别的 Bean / AopContext.currentProxy()（需 exposeProxy=true）
```

② **非 public 方法**：@Transactional 只对 public 生效（Spring 代理限制；CGLIB 可增强 protected 但事务切面惯例仅 public）。

③ **final 方法/类**：CGLIB 靠子类继承，final 无法增强。

④ **类未被 Spring 管理**：new OrderService() 或没加 @Service/@Component。

⑤ **异常被吞**：方法内 try-catch 捕获异常不抛出，事务管理器看不到异常，不回滚。

```java
@Transactional
public void bad() {
    try { dao.update(); } catch (Exception e) { log.error(e); }   // ✗ 吞异常，不回滚
}
// 解法：catch 后手动 TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()，或 rethrow
```

⑥ **多线程**：事务绑定当前线程（ThreadLocal 同步管理器），子线程里抛异常不影响主线程事务；子线程事务需单独开启。

⑦ **传播行为配置错误**：如 SUPPORTS/NOT_SUPPORTED 下无事务时不会新建，异常自然不回滚。

⑧ **rollbackFor 未配受检异常**：见第四节，默认不回滚 checked 异常。

⑨ **数据库引擎不支持事务**：MyISAM 表无事务，DDL/DCL 隐式提交也会打断事务。

⑩ **异常类型与代理边界**：抛出 Error（如 OOM）不一定被事务切面捕获（默认回滚 Error 但内存都炸了意义有限）。

## 七、接口 vs 类注解与常见坑

- **推荐标在实现类方法上**：标接口方法上，JDK 动态代理能识别，但 CGLIB 代理（Boot 默认）对接口注解的识别依赖 Spring 的注解查找逻辑，易出"注解不生效"的模糊问题；标实现类最稳。
- 事务方法里**长事务**：一个事务里做多次远程调用/大循环，长时间持有数据库连接 → 用 REQUIRES_NEW 或拆分事务。
- 事务与锁：先查后更（check-then-act）要配合悲观锁（SELECT FOR UPDATE）或乐观锁版本号，事务本身不解决并发覆盖（锁的通用原理与优化/悲现锁对比见 [02-关系型DB锁详解](../../数据库/DB通用理论/02-关系型DB锁详解.md)）。
- @Transactional 与自定义切面顺序：事务切面默认优先级最低（LOWEST_PRECEDENCE），自定义 @Order 数值小于它时自定义通知在事务内执行（见 [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)）。

## 八、边界：单服务 vs 分布式事务

本篇（@Transactional + 传播行为）只覆盖**单服务内部同一调用链**（同线程/同数据源）。一旦跨服务、跨数据源或跨进程，ThreadLocal 共享事务的机制即断，传播行为不再适用，进入**分布式事务**领域（XA/2PC、TCC、SAGA/本地消息表等），且很多跨服务场景可用最终一致替代强一致。

> 指引：**[04-分布式事务详解](../../分布式/核心原理/04-分布式事务详解.md)**（理论/模型/Seata）、****Seata分布式事务框架详解**（见知识库）**

## 参考资料

- [Spring 官方文档：Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction.html)，查询日期：2026-08-08
- [Spring 事务实现机制传播行为与常见失效场景深度解析（阿里云）](https://developer.aliyun.com/article/1666013)，查询日期：2026-08-08
- [一口气说出 6 种 @Transactional 注解的失效场景](https://www.cnblogs.com/chengxy-nds/p/12523241.html)，查询日期：2026-08-08
- 关联：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（事务切面原理）、**Java注解机制详解**（见知识库）（注解扫描机制）

---
- 上一篇：[08-Spring核心·AOP实践](08-Spring核心·AOP实践.md)
- 下一篇：[10-Spring事务管理实践](10-Spring事务管理实践.md)（本知识点代码实盀）
