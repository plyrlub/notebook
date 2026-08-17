---
tags: [Java, ORM, MyBatis, MyBatis-Plus, SpringBoot, 框架, 配置]
创建日期: 2026-08-11
状态: ✅ 已归档
归属: 01-学习/Java/框架/数据访问层
---

# MyBatis/MyBatis-Plus 集成与配置详解

> 适用版本：MyBatis 3.5.x、MyBatis-Spring 2.x、MyBatis-Plus 3.5.x、Spring Boot 2.7/3.x、JDK 8/17 为主线
> 最后更新：2026-08-11
> 主题范围：Spring Boot 集成两种方式（starter / 原生）、`mybatis` 配置前缀全表、MyBatis 核心 settings 全表（含默认值）、mybatis-config.xml 方式、Mapper 扫描机制、MyBatis-Plus 全局配置（global-config/db-config）、多数据源方案、通用坑
> 关联笔记：[01-MyBatis核心机制详解](01-MyBatis核心机制详解.md)（执行链路）、[02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md)（缓存/代理）、[05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md)（MP 机制）、[00-ORM全家桶总览与选型](00-ORM全家桶总览与选型.md)

## 📋 总纲

- ① Spring Boot 集成两条路线：`mybatis-spring-boot-starter` vs 原生 `mybatis-config.xml`
- ② `mybatis.*` 配置前缀逐个拆（mapper-locations/type-aliases-package/configuration 等）
- ③ MyBatis 核心 settings 全表：默认值 + 作用 + 调优建议（官方查证 2026-08-11）
- ④ Mapper 扫描三种方式与绑定原理
- ⑤ MyBatis-Plus 全局配置 `global-config.db-config` 全表
- ⑥ 多数据源方案（@DS 动态数据源 / 手动分包）
- ⑦ 配置相关坑汇总

## 一、Spring Boot 集成两条路线

### 1.1 方式一：mybatis-spring-boot-starter（Spring Boot 生态推荐）

```xml
<!-- Spring Boot 2.x -->
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>2.3.2</version>
</dependency>

<!-- Spring Boot 3.x（jakarta，用 3.0.x+） -->
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>3.0.3</version>
</dependency>
```

**代码说明**：starter 自动完成四件事——① 装配 `SqlSessionFactory`；② 装配 `SqlSessionTemplate`（线程安全）；③ 扫描 `@Mapper` 注解的接口注册到 Spring 容器；④ 读取 `application.yml` 里 `mybatis.*` 配置。这是 Spring Boot 项目最常用的方式，配置全走 yml，不写 mybatis-config.xml。

### 1.2 方式二：原生 mybatis-config.xml（传统/非 Spring Boot）

```xml
<!-- mybatis-config.xml -->
<configuration>
  <settings>
    <setting name="mapUnderscoreToCamelCase" value="true"/>
    <setting name="cacheEnabled" value="false"/>
  </settings>
  <typeAliases>
    <package name="com.example.domain"/>
  </typeAliases>
  <environments default="development">
    <environment id="development">
      <transactionManager type="JDBC"/>
      <dataSource type="POOLED">
        <property name="driver" value="com.mysql.cj.jdbc.Driver"/>
        <property name="url" value="jdbc:mysql://localhost:3306/db"/>
        <property name="username" value="root"/>
        <property name="password" value="xxx"/>
      </dataSource>
    </environment>
  </environments>
  <mappers>
    <package name="com.example.mapper"/>
  </mappers>
</configuration>
```

**代码说明**：方式二的数据源、事务、连接池全部自己管（或交给 Spring 后精简），适合非 Boot 项目或对配置有极致掌控的场景。**Spring Boot 下通常不这样用**——数据源/事务交给 Spring Boot 自动装配，MyBatis 只负责 ORM 部分。

### 1.3 对比

| 维度 | starter 方式 | mybatis-config.xml 方式 |
| --- | --- | --- |
| 配置位置 | `application.yml` 的 `mybatis.*` | 独立 XML |
| 数据源 | 复用 Spring Boot 数据源（HikariCP） | 自己在 XML 配 |
| 事务 | Spring 事务管理 | 可配 JDBC/MANAGED |
| 适用 | Spring Boot 项目（主流） | 传统 SSM / 非 Boot |
| yml 里能否配置 | 全部 | 需 `mybatis.config-location` 指外部 XML |

> ⚠️ 若用了 `mybatis.config-location` 指向外部 XML，**yml 里的 `mybatis.configuration` 子项会冲突报错**——二者只能选一（详见第七节坑 ⑦）。

## 二、`mybatis.*` 配置前缀全表（starter 方式）

| 配置项 | 说明 | 示例 |
| --- | --- | --- |
| `mybatis.mapper-locations` | Mapper XML 位置，支持通配 | `classpath*:/mapper/**/*.xml` |
| `mybatis.type-aliases-package` | 类型别名包扫描（`com.example.domain`） | `com.example.domain` |
| `mybatis.type-handlers-package` | 自定义 TypeHandler 包 | `com.example.typehandler` |
| `mybatis.config-location` | 外部 mybatis-config.xml 位置 | `classpath:mybatis-config.xml` |
| `mybatis.configuration` | 内联 MyBatis 核心 settings（见第三节） | 见下 |
| `mybatis.configuration-properties` | 传给 Configuration 的变量 | `mybatis.configuration-properties.default-statement-timeout=30` |
| `mybatis.check-config-location` | 是否检查 config-location 存在（默认 true） | `true` |

```yaml
# 完整示例（Spring Boot 3 + MyBatis starter）
mybatis:
  mapper-locations: classpath*:/mapper/**/*.xml
  type-aliases-package: com.example.domain
  type-handlers-package: com.example.typehandler
  configuration:
    map-underscore-to-camel-case: true
    cache-enabled: false
    lazy-loading-enabled: true
```

**代码说明**：`mybatis.configuration.*` 下的键就是 MyBatis settings 的**连字符版本**（`mapUnderscoreToCamelCase` → `map-underscore-to-camel-case`），值直接映射到 `Configuration` 对象。这是 Spring Boot 项目配置 MyBatis 行为的主入口。

## 三、MyBatis 核心 settings 全表（官方查证 2026-08-11）

以下默认值均来自 MyBatis 3.5.x 官方文档，生产调优常用项加粗。

| setting | 说明 | 默认值 | 建议 |
| --- | --- | --- | --- |
| **cacheEnabled** | 全局二级缓存开关 | true | 生产多关（false），见 [02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md) |
| **lazyLoadingEnabled** | 全局懒加载开关 | false | 需要时开 |
| **aggressiveLazyLoading** | 访问任一属性是否加载全部懒加载属性（≤3.4.1 默认 true，之后默认 false） | false | 保持默认 |
| **mapUnderscoreToCamelCase** | 下划线列名 → 驼峰属性自动映射（`user_name` → `userName`） | false | **生产强烈建议 true** |
| autoMappingBehavior | 自动映射级别：NONE/PARTIAL/FULL | PARTIAL | 保持默认 |
| autoMappingUnknownColumnBehavior | 未知列处理：NONE/WARNING/FAILING | NONE | 调试时可 WARNING |
| defaultExecutorType | 默认 Executor：SIMPLE/REUSE/BATCH | SIMPLE | 见 [01-MyBatis核心机制详解](01-MyBatis核心机制详解.md) |
| defaultStatementTimeout | Statement 超时秒数 | null | 建议设置防慢 SQL 拖死连接 |
| defaultFetchSize | 默认 fetchSize | null | 流式查询配合（见 [04-MyBatis插件、分页与流式查询详解](04-MyBatis插件、分页与流式查询详解.md)） |
| **localCacheScope** | 一级缓存作用域：SESSION/STATEMENT | SESSION | 生产保持 SESSION |
| useGeneratedKeys | 是否使用数据库自增主键回填 | false | 插入回填 id 时 true |
| logImpl | 日志实现：SLF4J/STDOUT_LOGGING/LOG4J2 等 | 自动探测 | 用 SLF4J |
| logPrefix | 日志前缀 | 无 | 多数据源区分时用 |
| callSettersOnNulls | 结果 null 时是否调用 setter | false | 通常不必 |
| returnInstanceForEmptyRow | 空行是否返回空实例 | false | 少用 |
| shrinkWhitespacesInSql | 是否压缩 SQL 空白 | false | 日志美观时 true |

```yaml
# 生产推荐模板（application.yml）
mybatis:
  mapper-locations: classpath*:/mapper/**/*.xml
  configuration:
    map-underscore-to-camel-case: true   # ★ 下划线转驼峰，默认 false 必开
    cache-enabled: false                  # 关二级缓存，用 Redis 替代
    default-statement-timeout: 30         # 防慢 SQL
```

**代码说明**：`mapUnderscoreToCamelCase` 是**新建项目必开**的一项——否则 `user_name` 列无法自动映射到 `userName` 属性，必须手写 resultMap。`cache-enabled` 生产建议 false（原因见 02 篇脏数据场景）。

## 四、Mapper 扫描机制

### 4.1 三种注册方式

| 方式 | 用法 | 适用 |
| --- | --- | --- |
| `@Mapper` 注解 | 每个 Mapper 接口上加 `@Mapper` | starter 自动扫描 |
| `@MapperScan` | 配置类上 `@MapperScan("com.example.mapper")` 指定包 | **推荐**：一次扫全包 |
| XML `<package>` | mybatis-config 里 `<mappers><package name="..."/></mappers>` | 方式二 |

```java
@Configuration
@MapperScan("com.example.mapper")   // 扫整个包，接口不用一个个加 @Mapper
public class MyBatisConfig {
}
```

**代码说明**：`@MapperScan` 背后调 `MapperScannerConfigurer`（`ClassPathMapperScanner`），启动时扫描包下所有接口，注册为 Spring Bean（Bean 名 = 接口简单名小写开头）。**@Mapper 和 @MapperScan 选一个即可**，混用会重复注册（通常无害但冗余）。

### 4.2 绑定原理回顾

```mermaid
flowchart LR
    A["@MapperScan 扫描包"] --> B["MapperFactoryBean 创建代理"]
    B --> C["SqlSessionTemplate 注入"]
    C --> D["MapperProxy 动态代理执行 SQL"]
```

> 详细代理链路见 [02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md) 第六节。

## 五、MyBatis-Plus 全局配置（global-config / db-config）

MP 用 `mybatis-plus.*` 前缀，与 MyBatis 的 `mybatis.*` 并存（MP 内部仍读 MyBatis 的 mapper-locations 等）。

### 5.1 完整配置示例

```yaml
mybatis-plus:
  mapper-locations: classpath*:/mapper/**/*.xml
  type-aliases-package: com.example.domain
  configuration:
    map-underscore-to-camel-case: true
    cache-enabled: false
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl   # 开发期打印 SQL
  global-config:
    banner: false                       # 关启动 banner
    db-config:
      id-type: assign_id                # 主键策略：雪花（默认）
      table-prefix: tbl_                # 全局表前缀
      logic-delete-field: deleted       # 逻辑删除字段
      logic-delete-value: 1             # 已删除值
      logic-not-delete-value: 0         # 未删除值
      # 字段填充策略
      insert-strategy: not_null
      update-strategy: not_null
      select-strategy: not_null
      # 数据库关键字转义（防关键字冲突）
      column-format: "`%s`"
```

### 5.2 db-config 关键项全表

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `id-type` | 主键类型（ASSIGN_ID/AUTO/ASSIGN_UUID/INPUT） | assign_id |
| `table-prefix` | 全局表名前缀 | 空 |
| `table-format` | 表名格式化模板 | 空 |
| `column-format` | 列名格式化（如加反引号 `` `%s` `` 防关键字） | 空 |
| `logic-delete-field` | 逻辑删除字段（实体属性名） | 空 |
| `logic-delete-value` | 已删除值 | 1 |
| `logic-not-delete-value` | 未删除值 | 0 |
| `insert-strategy` | 插入字段策略（NOT_NULL/NOT_EMPTY/ALWAYS/IGNORED） | NOT_NULL |
| `update-strategy` | 更新字段策略 | NOT_NULL |
| `select-strategy` | 查询字段策略 | NOT_NULL |
| `capital-mode` | 是否大写 | false |
| `schema` | 表 schema | 空 |

> 字段策略 `NOT_NULL`（默认）= 只操作非 null 字段，这就是 [05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md) 里「updateById 不更新 null 字段」的配置来源。

### 5.3 configuration（MP 复用 MyBatis settings）

MP 的 `mybatis-plus.configuration.*` 与 MyBatis 的 `mybatis.configuration.*` **同一套 setting**，任选一个配即可（MP 内部最终 merge 进同一个 Configuration）。上表第三节的 settings 同样适用。

## 六、多数据源方案

### 6.1 方案对比

| 方案 | 原理 | 适用 |
| --- | --- | --- |
| **@DS 动态数据源**（dynamic-datasource-spring-boot-starter） | 基于 Spring AOP + 数据源路由（ThreadLocal），注解切换 | **主流推荐**，读写分离/多库 |
| 手动分包 | 多个 SqlSessionFactory，各扫各的 Mapper 包 | 分库边界清晰、互不掺和 |
| 路由数据源 AbstractRoutingDataSource | 内置路由，按 key 选数据源 | 轻量、不用第三方 |

### 6.2 @DS 动态数据源（推荐）

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>dynamic-datasource-spring-boot-starter</artifactId>
    <version>4.x</version>
</dependency>
```

```yaml
spring:
  datasource:
    dynamic:
      primary: master                 # 默认数据源
      strict: false                   # 未匹配到 ds 时是否报错
      datasource:
        master:
          url: jdbc:mysql://localhost:3306/master_db
          username: root
          password: xxx
          driver-class-name: com.mysql.cj.jdbc.Driver
        slave:
          url: jdbc:mysql://localhost:3306/slave_db
          username: root
          password: xxx
          driver-class-name: com.mysql.cj.jdbc.Driver
```

```java
// 方法或类上注解切换
@DS("slave")               // 走从库
public List<User> queryFromSlave() { ... }

@DS("master")              // 走主库（写操作）
public void insert(User u) { ... }
```

**代码说明**：`@DS` 用 AOP 拦截，把数据源 key 存进 ThreadLocal，底层 `AbstractRoutingDataSource.determineCurrentLookupKey()` 返回 key 选数据源。**坑**：`@DS` 要配合 `@Transactional` 生效时，**事务注解最好在同类/外层**，且多数据源下事务要配对（见坑 ⑤）。

### 6.3 手动分包（分库清晰场景）

```java
// 主库 SqlSessionFactory
@Bean
@Primary
public SqlSessionFactory masterSqlSessionFactory(@Qualifier("masterDataSource") DataSource ds) {
    SqlSessionFactoryBean f = new SqlSessionFactoryBean();
    f.setDataSource(ds);
    f.setMapperLocations(new PathMatchingResourcePatternResolver()
            .getResources("classpath*:mapper/master/*.xml"));
    return f.getObject();
}
// 从库类似，MapperScan 指定不同包
```

## 七、配置相关坑汇总

① **mapUnderscoreToCamelCase 没开**：`user_name` 查出来是 null，属性名匹配不上。新建项目必开 true。
② **mapper-locations 路径错**：XML 没被加载，启动报 `Invalid bound statement (not found)`。检查 `classpath*:/mapper/**/*.xml` 通配与包名。
③ **namespace 没写对**：`namespace` 必须 = Mapper 接口全限定名，id = 方法名，否则绑定失败（见 [02-MyBatis缓存与Mapper代理详解](02-MyBatis缓存与Mapper代理详解.md) 6.5）。
④ **config-location 与 configuration 冲突**：`mybatis.config-location` 指定外部 XML 后，yml 里 `mybatis.configuration.*` 会报 `Property 'configuration' and 'configLocation' can not specified with together`——二者只能选一。
⑤ **多数据源 + 事务**：`@DS` 切换 + `@Transactional`，事务管理器要匹配；跨库事务要么用分布式事务（见 [Seata分布式事务框架详解](../../中间件/分布式协调/分布式事务/Seata分布式事务框架详解.md)），要么避免跨库事务。
⑥ **MP 没配 db-config 的 logic-delete**：`@TableLogic` 字段若全局没配 logic-delete-value，默认 1/0；手写 join SQL 不自动过滤 `deleted=0`（见 [05-MyBatis Plus核心机制详解](05-MyBatis Plus核心机制详解.md)）。
⑦ **开发期要打印 SQL**：配 `configuration.log-impl: org.apache.ibatis.logging.stdout.StdOutImpl`（MP）或 `logging.level.com.example.mapper: debug`（MyBatis）。
⑧ **Spring Boot 3 依赖版本**：必须用 `mybatis-spring-boot-starter 3.0.x`（jakarta），`2.x` 是 javax 只适配 Boot 2。

## 八、面试问答与场景题

### Q1: Spring Boot 集成 MyBatis，配置放 yml 还是 mybatis-config.xml？

**答案**：Spring Boot 项目主流用 `mybatis-spring-boot-starter`，配置全走 `application.yml` 的 `mybatis.*`（mapper-locations + configuration 内联 settings）。只有非 Boot 项目或特殊需要才用独立 mybatis-config.xml。二者不可同时配 configuration 与 config-location。

### Q2: mapUnderscoreToCamelCase 是什么？为什么必开？

**答案**：开启下划线列名到驼峰属性自动映射（`user_name` → `userName`），默认 false。不开则列名与属性名不一致时映射为 null，需手写 resultMap。生产强烈建议 true。

### Q3: @Mapper 和 @MapperScan 区别？

**答案**：@Mapper 是逐接口标注；@MapperScan 在配置类扫整个包一次注册，底层是 MapperScannerConfigurer。推荐 @MapperScan，免去每个接口加注解。

### Q4: MP 全局配置里字段策略 NOT_NULL 影响什么？

**答案**：insert-strategy/update-strategy 默认 NOT_NULL，即只操作非 null 字段——所以 updateById 不更新 null 字段。要更新 null 用 UpdateWrapper.set 或改字段策略。

### 场景题：多数据源读写分离怎么做？

**答案**：引入 dynamic-datasource-spring-boot-starter，配置 primary + 各数据源，读写方法上加 `@DS("master"/"slave")`。底层 AbstractRoutingDataSource + ThreadLocal 路由。注意事务边界与跨库事务。

## 参考资料

- [MyBatis-Spring-Boot 官方文档：配置属性](https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/)，查询日期：2026-08-11
- [MyBatis 3 官方文档：Configuration / Settings](https://mybatis.org/mybatis-3/configuration.html)，查询日期：2026-08-11
- [MyBatis-Plus 官方文档：使用配置](https://baomidou.com/reference/)，查询日期：2026-08-11
- [MyBatis-Plus GlobalConfig.DbConfig API](https://javadoc.io/static/com.baomidou/mybatis-plus-core/3.5.4/)，查询日期：2026-08-11
- [dynamic-datasource 官方文档](https://github.com/baomidou/dynamic-datasource-spring-boot-starter)，查询日期：2026-08-11
