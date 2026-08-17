---
tags: [Java, ORM, MyBatis, MyBatis-Plus, JPA, 框架]
创建日期: 2026-08-08
状态: ✅ 已归档
归属: 01-学习/Java/框架/数据访问层
---

# ORM全家桶总览与选型

> 适用版本：MyBatis 3.5.x、MyBatis-Plus 3.5.x、Spring Data JPA 3.x（Hibernate 6.x）、JDK 17 为主线
> 最后更新：2026-08-08
> 主题范围：MyBatis / MyBatis-Plus / JPA(Hibernate+Spring Data JPA) 三框架定位对比、选型指南、知识域导航

## 📋 总纲

- ① 三框架各自定位：半自动 SQL Mapper / 增强型 SQL Mapper / 全自动 ORM
- ② 对比维度：SQL 控制力、开发效率、缓存、学习曲线、生态
- ③ 选型指南：什么场景选什么，国内互联网主流与理由
- ④ 面试速查：三框架最高频考点一览
- ⑤ 知识域导航：系列笔记地图

## 一、三框架定位一句话

| 框架 | 一句话定位 | 核心思想 | SQL 谁写 |
| --- | --- | --- | --- |
| MyBatis | 半自动持久层框架（SQL Mapper） | SQL 完全可控，帮你做参数绑定+结果映射 | 开发者手写 |
| MyBatis-Plus | MyBatis 的增强工具（不侵入） | 单表 CRUD 零 SQL，复杂查询仍用 MyBatis | 单表自动生成，多表手写 |
| JPA（Hibernate 实现） | 全自动 ORM 规范 | 面向对象操作，框架自动生成 SQL | 框架自动生成 |

**代码说明**：三者的本质区别在于「SQL 谁来写、对象与表怎么对应」。MyBatis 系列是**开发者掌控 SQL**（半自动），JPA 是**框架掌控 SQL**（全自动）。MyBatis-Plus 站在 MyBatis 肩膀上，把**单表 CRUD 自动化**（开发效率向 JPA 看齐），但**复杂查询仍手写 SQL**（可控性向 MyBatis 看齐）——这是它能成为国内主流的重要原因。

## 二、三框架核心对比表

| 维度 | MyBatis | MyBatis-Plus | JPA/Hibernate |
| --- | --- | --- | --- |
| 类型 | 半自动 SQL Mapper | MyBatis 增强（不侵入） | 全自动 ORM 规范 |
| 入门 CRUD | 手写 SQL + XML/注解 | 继承 BaseMapper 零 SQL | 继承 Repository 零 SQL |
| 复杂查询 | 手写 SQL 完全可控 | 手写 SQL（Wrapper 也支持多表拼接） | @Query/JPQL/Criteria，复杂 SQL 别扭 |
| 动态 SQL | 强大（if/foreach/where/set/choose） | 继承 MyBatis 全部 + Wrapper 条件构造 | 弱（需 Specification/Criteria 拼） |
| SQL 优化空间 | 强（直接改 SQL） | 强（直接改 SQL） | 弱（SQL 是框架生成的） |
| 数据库移植 | 差（方言相关） | 差（方言相关） | 好（方言抽象） |
| 开发效率 | 低（全手写） | 高（单表自动化） | 高（面向对象） |
| 一级缓存 | SqlSession 级（默认开） | 同 MyBatis | PersistenceContext 级（EntityManager） |
| 二级缓存 | namespace 级（默认关，生产不建议） | 同 MyBatis | Hibernate 二级缓存（需配置） |
| 懒加载 | 支持（需配置，默认关） | 同 MyBatis | 支持（默认开，@ManyToOne 等） |
| 分页 | 手写 LIMIT 或 PageHelper 插件 | 内置分页插件（PaginationInnerInterceptor） | Pageable 内置（物理分页） |
| 批量操作 | 手写（ExecutorType.BATCH） | saveBatch/批量方法内置 | 需注意（批量插入效率低） |
| 学习曲线 | 平缓 | 平缓（多了 Wrapper 要学） | 较陡（生命周期/状态/级联） |
| 社区生态 | 成熟 | 国内主流（苞米豆） | 国际主流（Spring 官方） |
| 典型场景 | 复杂报表、多表关联、性能敏感 | 国内互联网单体/微服务 CRUD 主力 | 规整 CRUD、跨数据库、DDD |

**代码说明**：这张表是面试「MyBatis 和 JPA 有什么区别」的完整答案骨架。记住核心逻辑线：**SQL 控制力**（MyBatis > MP > JPA）与**开发效率**（JPA ≈ MP > MyBatis）是跷跷板，而 **MP 恰好站在中间**——单表零 SQL、复杂查询可控，所以国内互联网最流行。JPA 的优势在**对象模型驱动**（DDD、领域事件、级联管理）和**数据库移植**。

## 三、选型指南

### 3.1 选型决策树

```
项目要建持久层
├─ 单表 CRUD 为主 + 少量复杂查询 → MyBatis-Plus（国内主流推荐）
├─ 复杂 SQL 多 / 报表 / 性能调优敏感 → 原生 MyBatis（或 MP + 手写 SQL）
├─ 规整 CRUD + 面向对象建模 + 跨数据库 → JPA（Spring Data JPA）
└─ 极端性能 + 全 SQL 掌控 → 原生 JDBC / MyBatis（避免 JPA 生成低效 SQL）
```

### 3.2 国内互联网为什么偏爱 MyBatis 系

★ 原因一：**SQL 可控、可优化**——慢查询直接改 SQL，DBA 介入方便
★ 原因二：**动态 SQL 强大**——复杂多表查询、报表聚合用 XML 写最顺手
★ 原因三：**团队历史惯性**——老项目都是 MyBatis，招人容易
★ 原因四：MP 补齐了 MyBatis 单表开发慢的短板，且**不侵入**（用了 MP 仍能用原生 MyBatis 语法）

### 3.3 什么场景果断选 JPA

- ① 领域驱动设计（DDD）：聚合根、值对象、级联持久化，对象模型优先
- ② 多数据库移植需求：JPA 方言抽象，换库不用改代码
- ③ Spring 官方生态深度集成：Spring Data JPA 的 Repository 抽象（方法名派生查询）
- ④ 团队已经熟悉 Hibernate（学习成本已付）

### 3.4 对比追问：能不能混用？

**可以，但要分层清晰**：主 ORM 用一个，另一个只做局部补充。常见组合：
- **MP 为主 + JPA 只做只读查询**（不同 mapper 包分开，事务要小心）
- **JPA 为主 + 复杂报表走 MyBatis**（两个事务管理器，注意 @Transactional 归属）

**代码说明**：混用的最大坑是**事务与缓存不一致**——两套框架各有各的 Session/上下文，同一事务里混用可能读到不一致数据。生产上建议**一个事务内只用一套 ORM**，跨框架只用于查询（只读）。

## 四、面试速查（三框架最高频考点）

### 4.1 MyBatis 速查

- ① `#{}` 预编译占位符防注入 vs `${}` 字符串拼接有风险（详见 [01-MyBatis核心机制详解](01-MyBatis核心机制详解.md)）
- ② 执行链路：SqlSessionFactory → SqlSession → Executor → StatementHandler → ParameterHandler/ResultSetHandler
- ③ Executor 三种：Simple（默认）/ Reuse / Batch
- ④ 一级缓存 SqlSession 级默认开，二级缓存 namespace 级默认关且生产不建议开（详见 [02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md)）
- ⑤ Mapper 接口无实现类 → JDK 动态代理（MapperProxy）
- ⑥ 插件拦截四大对象：Executor/ParameterHandler/ResultSetHandler/StatementHandler（详见 [04-MyBatis插件、分页与流式查询详解](04-MyBatis插件、分页与流式查询详解.md)）
- ⑦ resultMap vs resultType、N+1 问题（详见 [03-MyBatis动态SQL与结果映射详解](03-MyBatis动态SQL与结果映射详解.md)）

### 4.2 MyBatis-Plus 速查

- ① 增强不侵入：BaseMapper/IService 提供单表 CRUD，SQL 由「SQL 注入器」在启动时生成
- ② 条件构造器：QueryWrapper（字符串字段）/ LambdaQueryWrapper（方法引用，类型安全）
- ③ 分页插件 PaginationInnerInterceptor：物理分页 + count 自动优化（详见 [05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md)）
- ④ 主键策略默认雪花算法（ASSIGN_ID），@TableId(type=IdType.AUTO) 可切回自增
- ⑤ 逻辑删除 @TableLogic / 乐观锁 @Version / 自动填充 MetaObjectHandler

### 4.3 JPA 速查

- ① JPA 是规范，Hibernate 是实现，Spring Data JPA 是 Repository 封装
- ② 实体四态：transient / managed / removed / detached（详见 [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md)）
- ③ 持久化上下文 = 一级缓存 + 脏检查，事务 flush 时自动生成 UPDATE
- ④ N+1 问题：懒加载集合逐个查询 → 用 JOIN FETCH / @EntityGraph 解决
- ⑤ LazyInitializationException：懒加载超出 Session 作用域 → @Transactional 内取数据 或 open-in-view

## 五、知识域导航

本系列 9 篇，建议按顺序阅读：

- [00-ORM全家桶总览与选型](00-ORM全家桶总览与选型.md)（本篇）——三框架定位对比与选型
- [01-MyBatis核心机制详解](01-MyBatis核心机制详解.md)——执行流程、#{} vs ${}、Executor 三类型
- [02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md)——一级/二级缓存源码、MapperProxy 动态代理
- [03-MyBatis动态SQL与结果映射详解](03-MyBatis动态SQL与结果映射详解.md)——动态 SQL 全标签、resultMap、N+1、懒加载
- [04-MyBatis插件、分页与流式查询详解](04-MyBatis插件、分页与流式查询详解.md)——拦截器机制、PageHelper、Cursor 流式
- [05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md)——Wrapper、分页插件、逻辑删除、乐观锁、自动填充、SQL 注入器
- [07-Spring Boot集成与配置详解](07-Spring Boot集成与配置详解.md)——Spring Boot 集成、mybatis 配置、settings 全表、MP 全局配置、多数据源
- [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md)——实体映射、生命周期、JPQL、Spring Data JPA、N+1
- [08-Spring Data JPA实战进阶](08-Spring Data JPA实战进阶.md)——Auditing、DTO 投影、方法族辨析、继承/复合主键、性能优化

## 参考资料

- [MyBatis 官方文档](https://mybatis.org/mybatis-3/)，查询日期：2026-08-08
- [MyBatis-Plus 官方文档](https://baomidou.com/)，查询日期：2026-08-08
- [Spring Data JPA 官方文档](https://docs.spring.io/spring-data/jpa/reference/)，查询日期：2026-08-08
- 参考素材：《MyBatis核心机制.md》（面试笔记，MyBatis 部分）
