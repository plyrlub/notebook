---
tags: [Java, ORM, JPA, Hibernate, Spring Data JPA, 框架, 实战]
创建日期: 2026-08-11
状态: ✅ 已归档
归属: 01-学习/Java/框架/数据访问层
---

# Spring Data JPA 实战进阶

> 适用版本：Spring Data JPA 3.x、Hibernate 6.x、Spring Boot 3、JDK 17 为主线
> 最后更新：2026-08-11
> 主题范围：Auditing 审计字段（@CreatedDate/@LastModifiedDate/@CreatedBy/@LastModifiedBy）、DTO 投影（interface/constructor/native）、Repository 方法族辨析（save/saveAndFlush/saveAll、findById/getReferenceById）、继承映射三策略、复合主键（@IdClass/@EmbeddedId）、性能优化（@DynamicUpdate/@BatchSize/default_batch_fetch_size）、公司实战坑汇总
> 关联笔记：[06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md)（JPA 原理）、[00-ORM全家桶总览与选型](00-ORM全家桶总览与选型.md)（选型对比）、[05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md)（对照阅读）

## 📋 总纲

- ① 理论见 [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md)，本篇只讲**实战怎么用**
- ② Auditing：一行注解搞定 create_time/update_time/create_by 自动填充（对比 MP MetaObjectHandler）
- ③ DTO 投影：避免实体泄漏给前端，接口投影/构造投影/原生投影三选
- ④ Repository 方法族：save vs saveAndFlush vs saveAll、findById vs getReferenceById 逐个辨析
- ⑤ 继承映射三策略：SingleTable/Joined/TablePerClass 怎么选
- ⑥ 复合主键：@IdClass vs @EmbeddedId 两套写法
- ⑦ 性能优化：@DynamicUpdate / @BatchSize / default_batch_fetch_size 实测结论
- ⑧ 公司实战坑汇总

## 一、Auditing 审计字段（@CreatedDate 等）

### 1.1 目标

实体里 create_time/update_time/create_by/update_by 四个字段，**插入/更新时自动填充**，业务代码不手动 set。公司实体类几乎都是标配。

### 1.2 三步配置（完整可运行）

```java
// ① 开启审计（启动类或配置类）
@SpringBootApplication
@EnableJpaAuditing          // ★ 不写这行，注解不生效！
public class Application { }

// ② 抽取可复用的审计基类（@MappedSuperclass：子类映射时继承字段）
@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)   // ★ 监听器，负责填充
public abstract class AuditableEntity {
    @CreatedBy
    @Column(name = "created_by", updatable = false)
    private String createdBy;

    @CreatedDate
    @Column(name = "created_time", updatable = false)
    private LocalDateTime createdTime;

    @LastModifiedBy
    @Column(name = "updated_by")
    private String updatedBy;

    @LastModifiedDate
    @Column(name = "updated_time")
    private LocalDateTime updatedTime;
    // getter/setter 略
}

// ③ 业务实体继承基类，自动获得审计字段
@Entity
@Table(name = "user")
public class User extends AuditableEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    // 不用管 createTime 等，框架自动填
}
```

### 1.3 当前操作者从哪来（@CreatedBy / @LastModifiedBy）

Spring 不知道「当前是谁」，要提供一个 `AuditorAware` Bean 返回当前用户：

```java
@Configuration
public class AuditorConfig {
    @Bean
    public AuditorAware<String> auditorProvider() {
        // 从 SecurityContext / ThreadLocal 拿当前登录用户；拿不到返回 system
        return () -> Optional.ofNullable(SecurityContextHolder.getContext().getAuthentication())
                .map(auth -> auth.getName())
                .or(() -> Optional.of("system"));
    }
}
```

**代码说明**：`@CreatedDate/@LastModifiedDate` 由 `AuditingEntityListener` 自动填时间，无需 AuditorAware；但 `@CreatedBy/@LastModifiedBy` 必须配 `AuditorAware`（返回用户标识），否则填充 null。`modifyOnCreate`（@EnableJpaAuditing 属性，默认 true）控制创建时是否也填充 `@LastModifiedDate`。

### 1.4 对比 MyBatis-Plus 自动填充

| 维度 | Spring Data JPA Auditing | MyBatis-Plus MetaObjectHandler |
| --- | --- | --- |
| 开启 | `@EnableJpaAuditing` + 实体 `@EntityListeners` | 实现 MetaObjectHandler Bean |
| 字段注解 | `@CreatedDate/@LastModifiedDate/@CreatedBy/@LastModifiedBy` | `@TableField(fill = FieldFill.INSERT/INSERT_UPDATE)` |
| 当前用户 | `AuditorAware` Bean | MetaObjectHandler 里手动取 |
| 时机 | JPA 生命周期事件（@PrePersist/@PreUpdate 前） | MP SQL 生成阶段 |

> 两者思想一致：**都是「插入/更新前自动赋值」，不用业务手动 set**。JPA 用生命周期监听器实现，MP 在 SQL 生成阶段内嵌填充。详见 [05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md) 第八节。

## 二、DTO 投影（避免实体泄漏）

### 2.1 为什么用

把 `User` 实体直接返回给前端 = ① 返回全部字段（含密码/内部字段，**数据泄漏**）；② 可能带出懒加载代理（序列化炸）。生产惯例：**Repository 返回 DTO/投影，不返回实体**。

### 2.2 三种投影方式

| 方式 | 写法 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 接口投影 | 定义接口，方法返回属性 | 类型安全、Spring 生成代理 | 不能用于 `new`，字段路径有限 |
| 构造投影 | JPQL `select new XxxDTO(...)`，DTO 有全参构造 | 灵活、可用 List | DTO 要在实体类路径可访问，全限定名 |
| 原生投影 | `nativeQuery=true` + 接口（别名映射） | 复杂 SQL 性能好 | 列名与接口方法要对应 |

```java
// ① 接口投影（Spring Data JPA 特色，最简单）
public interface UserNameOnly {
    String getName();
    Integer getAge();
}
public interface UserRepository extends JpaRepository<User, Long> {
    // 返回接口投影，Spring 运行时生成代理，只查这俩列
    List<UserNameOnly> findAllProjectedByStatus(Integer status);
}

// ② 构造投影（DTO + JPQL，最常用）
public record UserDTO(Long id, String name, Integer age) {}   // record 天然全参构造
public interface UserRepository extends JpaRepository<User, Long> {
    // JPQL new + 全限定名 + 全参构造
    @Query("select new com.example.dto.UserDTO(u.id, u.name, u.age) from User u where u.status = :status")
    List<UserDTO> findUserDTOs(@Param("status") Integer status);
}
```

**代码说明**：**接口投影** Spring 运行时为每个结果生成代理对象，只 SELECT 接口声明的方法对应列；**构造投影**用 JPQL `new 全限定类名(字段...)`，DTO 必须有无参之外的**全参构造**（record 或 Lombok @AllArgsConstructor 都行）。两者都会减少查询列（性能好），且返回的是**非托管对象**（改了不脏检查，安全）。

### 2.3 投影 + 分页（公司列表页标配）

```java
// 接口投影 + 分页（返回 Page<UserNameOnly>）
@Query("select u from User u where u.status = :status")
Page<UserNameOnly> findByStatusProjected(@Param("status") Integer status, Pageable pageable);

// 用法
Page<UserNameOnly> page = repo.findByStatusProjected(1, PageRequest.of(0, 10));
List<UserNameOnly> list = page.getContent();
```

## 三、Repository 方法族辨析（高频踩坑）

### 3.1 save vs saveAndFlush vs saveAll

| 方法 | 行为 | 何时用 |
| --- | --- | --- |
| `save(entity)` | persist（新）或 merge（有 id）。**不一定立即 flush**，可能攒到事务提交 | 一般持久化 |
| `saveAndFlush(entity)` | save + 立即 flush（立刻发 SQL） | 需要立即拿到主键/立即落库 |
| `saveAll(list)` | 循环 save，**不是批量 SQL**（每行一个 INSERT） | 存集合（注意慢） |

```java
// save 的坑：不返回新 id 就急着用
User u = new User();
userRepository.save(u);          // 可能还没 flush
System.out.println(u.getId());   // ★ IDENTITY 策略下 save 内部已 flush，id 有值；但 SEQUENCE 可能为 null

// 需要立即落库 / 立即拿 id → saveAndFlush
User saved = userRepository.saveAndFlush(u);
```

★ **save 返回的实体就是入参实体本身**（Spring Data 的 save 直接返回入参，不像 JPA 原生 merge 返回新副本）——所以 `u = userRepository.save(u)` 里 `u` 和返回值是同一个对象，别以为返回的是新副本。但 **`em.merge()` 返回的才是新托管副本**（见 [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md) 3.1）。

### 3.2 findById vs getReferenceById

| 方法 | 行为 | 使用注意 |
| --- | --- | --- |
| `findById(id)` | 真正查库，返回 `Optional<T>` | **推荐默认**，能判断是否存在 |
| `getReferenceById(id)`（旧 getById/getOne） | **返回懒加载代理**（不查库，访问时才查） | 只用于「确定存在、只需引用」（如设置外键） |

```java
// findById：查库 + Optional
User user = userRepository.findById(1L).orElseThrow(() -> new NotFoundException("用户不存在"));

// getReferenceById：不查库，拿懒加载代理（设置关联外键时省一次查询）
Order order = new Order();
order.setUser(userRepository.getReferenceById(1L));  // 只设 user_id=1，不查 user 表
// ★ 但访问 user.getName() 才发查询；若实体 Detached 后再访问会 LazyInitializationException
```

**代码说明**：`getReferenceById` 的价值 = **给新实体设置已存在的外键时，不查关联表**（`order.setUser(getReferenceById(userId))` 比 `findById` 少一条 SELECT）。**坑**：代理在事务外访问懒属性会报 `LazyInitializationException`（见 [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md) 六节）。`getById/getOne` 已废弃，用 `getReferenceById`。

## 四、继承映射三策略

### 4.1 三种策略对比

| 策略 | 表结构 | 优点 | 缺点 |
| --- | --- | --- | --- |
| `SINGLE_TABLE`（默认） | 一张大表 + `dtype` 鉴别列 | 查询快、无需 join、简单 | 子类独有字段为 null、NOT NULL 约束难建 |
| `JOINED` | 每类一张表（父表 + 子表，id 关联） | 字段不冗余、规范化 | 查询要 join、性能略差 |
| `TABLE_PER_CLASS` | 每类独立完整表 | 无 join、各自完整 | 字段冗余、多态查询慢（union） |

```java
// SINGLE_TABLE（默认）：一张 publication 表 + dtype 列
@Entity
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "dtype")
public abstract class Publication {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String title;
}

@Entity
public class Book extends Publication {
    private String isbn;        // book 表没有，就在 publication 表加 isbn 列（Book 有值，其他为 null）
}

@Entity
public class Magazine extends Publication {
    private int issueNumber;    // publication 表加 issue_number 列
}
```

**代码说明**：默认 `SINGLE_TABLE`——所有子类字段**全部塞进父表**（用 `dtype` 列区分类型），子类独有字段对其他类型为 null。适合**子类差异小**（共用字段多、独有字段少）的场景。若子类字段差异大或要求 NOT NULL，用 `JOINED`（各子类独立表，父 id 关联）。生产**优先 SINGLE_TABLE**（简单、查询快），子类差异大再考虑 JOINED。`TABLE_PER_CLASS` 较少用（多态查询走 union，性能差）。

> ★ Hibernate 官方（Vlad Mihalcea）倾向：**优先用 SINGLE_TABLE 或 TABLE_PER_CLASS，避免 JOINED**（join 性能差）；但 JOINED 在规范化和 NOT NULL 约束上有优势。实际按「子类字段差异 + 查询模式」权衡。

## 五、复合主键：@IdClass vs @EmbeddedId

### 5.1 两套写法对比

| 方式 | 主键类 | 实体写法 |
| --- | --- | --- |
| `@IdClass` | 普通类（字段与实体重复声明） | 实体里用 `@Id` 标多个字段，类上标 `@IdClass(XxxId.class)` |
| `@EmbeddedId` | `@Embeddable` 类 | 实体里单个 `@EmbeddedId` 字段 |

★ 主键类三要求（两者通用）：**public + 无参构造 + 实现 equals/hashCode（+ Serializable）**。

```java
// ① @IdClass：主键类字段在实体里重复声明
public class OrderEntryId implements Serializable {
    private Long orderId;
    private Long productId;
    // 无参构造 + equals/hashCode
}
@Entity
@IdClass(OrderEntryId.class)
public class OrderEntry {
    @Id private Long orderId;      // 实体里重复声明，标 @Id
    @Id private Long productId;
    private int quantity;
}

// ② @EmbeddedId：主键类用 @Embeddable，实体只嵌一个字段
@Embeddable
public class OrderEntryKey implements Serializable {
    private Long orderId;
    private Long productId;
    // 无参构造 + equals/hashCode
}
@Entity
public class OrderEntry {
    @EmbeddedId
    private OrderEntryKey key;     // 实体只一个字段
    private int quantity;
}
```

**代码说明**：`@IdClass` 主键字段拆散在实体里（表字段直观），`@EmbeddedId` 主键封装成一个对象（更 OO）。**equal/hashCode 是硬要求**（JPA 靠它们判断实体标识/去重），漏了会导致 `detached entity passed to persist` 等诡异问题。查询按复合主键：`findById(new OrderEntryId(1L, 2L))`。

## 六、性能优化（@DynamicUpdate / @BatchSize）

### 6.1 @DynamicUpdate：只更新脏字段

```java
// 默认：UPDATE 全部字段（即使只改一个）
// @DynamicUpdate：UPDATE 只含脏字段（改了哪些才更新哪些）
@Entity
@DynamicUpdate
public class User {
    // name 变了，只 UPDATE name 和 version，其他字段不进 SET
}
```

**适用**：实体**字段多（尤其含 LOB 大字段）但每次只改少数**的场景——减少 UPDATE 的 SET 列和传输量。**不适用**：字段少/经常全字段更新的场景（@DynamicUpdate 反而要多算脏字段，无收益甚至略慢）。**注意**：@DynamicUpdate 与二级缓存/乐观锁 version 一起用没问题，但**别期望它提升 UPDATE 行数**（行的 WHERE 条件不变）。

### 6.2 @BatchSize / default_batch_fetch_size：批量抓取（N+1 克星）

```java
// 类级：批量加载关联实体
@Entity
@BatchSize(size = 100)
public class Order {
    @ManyToOne(fetch = FetchType.LAZY)
    private Customer customer;
}

// 集合级：批量加载集合
@Entity
public class User {
    @OneToMany(mappedBy = "user", fetch = FetchType.LAZY)
    @BatchSize(size = 20)
    private List<Order> orders;
}
```

```yaml
# 全局配置（推荐，避免每处注解）
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 50
```

**实测结论**（对比 101 条 N+1 查询场景）：

| 加载方式 | 查询次数 | 时间(ms) | 内存 |
| --- | --- | --- | --- |
| 默认懒加载（N+1） | 101 | 1200 | 高 |
| JOIN FETCH | 1 | 80 | 最高 |
| @BatchSize(20) | 5 | 150 | 中 |
| EntityGraph | 1 | 90 | 高 |

**代码说明**：`@BatchSize` / `default_batch_fetch_size` = 懒加载时**按 IN 批量**加载一批未初始化的代理（N 次查询 → `ceil(N/size)` 次）。对比 JOIN FETCH：**JOIN FETCH 一条 SQL 最快但内存最高（笛卡尔积）且与分页冲突**；**@BatchSize 多几次查询但内存友好、与分页兼容**。生产列表页大量场景，`@BatchSize` 是比 JOIN FETCH 更稳妥的默认选择。这是 N+1 的**第四板斧**（见 [06-JPA与Spring Data JPA详解](06-JPA与Spring Data JPA详解.md) 5.2）。

## 七、公司实战坑汇总

① **@EnableJpaAuditing 没加**：@CreatedDate 等注解全不生效，时间字段一直是 null。漏配是最常见的坑。
② **@CreatedBy 不填 AuditorAware**：created_by 为 null（时间戳不用 AuditorAware，操作人必须配）。
③ **直接返回实体给前端**：序列化炸（懒加载代理）或**字段泄漏**（密码等）。生产一律 DTO 投影。
④ **saveAll 以为是批量 SQL**：它只是循环 save，每行一个 INSERT，性能未必好。真批量用 `saveAllAndFlush` + `batch_size` 配置。
⑤ **getById/getOne 已废弃**：用 `getReferenceById`。且它返回懒加载代理，事务外访问会 LazyInitializationException。
⑥ **@IdClass/@EmbeddedId 主键类漏 equals/hashCode**：导致实体标识判断错乱，`detached entity passed to persist`。
⑦ **复合主键 + @GeneratedValue 不能共存**：复合主键一般是业务主键（INPUT 手动），不能靠数据库自增。
⑧ **@DynamicUpdate 乱用**：字段少/全量更新的场景用了反而慢；只在「字段多、改得少」时用。
⑨ **继承映射选错**：子类差异大却用 SINGLE_TABLE → 表里一堆 null 列；多态频繁查询用 TABLE_PER_CLASS → union 慢。
⑩ **DTO 投影的构造类路径**：JPQL `new` 要用**全限定名**，且 DTO 需有全参构造；record 或 @AllArgsConstructor 才行。

## 八、面试问答与场景题

### Q1: Spring Data JPA 怎么自动填充 create_time/update_time？

**答案**：三件套——① 启动类加 `@EnableJpaAuditing`；② 抽取 `@MappedSuperclass` + `@EntityListeners(AuditingEntityListener.class)` 基类，字段标 `@CreatedDate/@LastModifiedDate/@CreatedBy/@LastModifiedBy`；③ 当前用户用 `AuditorAware` Bean 提供。业务继承基类即可。

### Q2: save 和 saveAndFlush 区别？

**答案**：save 不一定立即 flush（可能攒到事务提交，IDENTITY 策略除外）；saveAndFlush 立即发 SQL。需要立刻拿主键/落库时用 saveAndFlush。save 返回的就是入参对象本身。

### Q3: findById 和 getReferenceById 区别？

**答案**：findById 真正查库返回 Optional，能判断存在；getReferenceById 返回懒加载代理（不查库），适合确定存在只需引用（如设外键）时省一次查询。代理事务外访问会 LazyInitializationException。

### Q4: DTO 投影有哪些方式？为什么不用实体返回？

**答案**：接口投影（Spring 生成代理，只查声明列）、构造投影（JPQL `new DTO(...)`）、原生投影。用投影避免字段泄漏、减少查询列、且返回非托管对象安全。

### 场景题：列表页加载 100 个用户各带 orders，怎么避免 N+1 且兼容分页？

**答案**：用 `@BatchSize(size=50)` 或 `hibernate.default_batch_fetch_size=50`——懒加载时 IN 批量加载，N+1 → ceil(N/50) 次查询，内存友好、**与分页兼容**（对比 JOIN FETCH 集合+分页会破坏 LIMIT 语义触发内存分页警告）。再配合 DTO 投影减少列。

## 参考资料

- [Spring Data JPA 官方文档：Auditing](https://docs.spring.io/spring-data/jpa/reference/auditing.html)，查询日期：2026-08-11
- [Spring Data JPA 官方文档：Projections](https://docs.spring.io/spring-data/jpa/reference/repositories/projections.html)，查询日期：2026-08-11
- [JpaRepository API（save/saveAndFlush/saveAll/findById/getReferenceById）](https://docs.spring.io/spring-data/jpa/docs/current/api/org/springframework/data/jpa/repository/JpaRepository.html)，查询日期：2026-08-11
- [Thorben Janssen：save vs saveAndFlush vs saveAll](https://thorben-janssen.com/spring-data-jpa-save-saveandflush-and-saveall/)，查询日期：2026-08-11
- [Vlad Mihalcea：Spring Data JPA DTO Projection](https://vladmihalcea.com/spring-jpa-dto-projection/)，查询日期：2026-08-11
- [Vlad Mihalcea：entity inheritance strategies](https://vladmihalcea.com/the-best-way-to-use-entity-inheritance-with-jpa-and-hibernate/)，查询日期：2026-08-11
- [Baeldung：JPA 复合主键（@IdClass / @EmbeddedId）](https://baeldung.cn/jpa-composite-primary-keys)，查询日期：2026-08-11
- [Hibernate 官方：Improving performance（@BatchSize）](https://docs.hibernate.org/orm/4.3/manual/en-US/html/ch20.html)，查询日期：2026-08-11
