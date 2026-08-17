---
tags: [Java, SpringBoot, Starter, 自定义, 自动配置, AutoConfiguration, 框架]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot自定义Starter详解

> 版本基线：Spring Boot 2.7+/3.x（@AutoConfiguration + .imports 注册）
> 受众：Java 后端开发。假设已懂自动装配机制（见 [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)）。本篇把"自己写一个 starter"讲透：模块拆分、注解、条件、元数据、测试。
> 前置知识：[01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)（自动装配/条件注解/.imports）、[02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)（@ConfigurationProperties）
> 关联笔记：[04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)（Boot4 模块化对 starter 的影响）

## 📋 总纲

1. Starter 是什么：定位与两模块结构
2. 双模块拆分：autoconfigure 模块 + starter 模块 ★
3. 命名规范（官方）
4. 自动配置类核心写法（@AutoConfiguration + 条件）
5. 属性绑定与配置元数据
6. 注册：.imports 文件
7. 测试自动配置
8. 完整示例：一个文件上传 starter
9. 常见坑

## 1. 学习目标

1. 说清 starter 为什么要拆 autoconfigure + starter 两模块
2. 用 @AutoConfiguration + 条件注解写自动配置类
3. 生成 spring-autoconfigure-metadata 配置元数据
4. 在 .imports 注册自动配置类
5. 用 @AutoConfigureTestDatabase 等测试 starter
6. 构建一个完整可用的自定义 starter

## 2. 前置知识

- [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)：自动装配三步、@ConditionalOnXxx、@ConditionalOnMissingBean 覆盖机制
- [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)：@ConfigurationProperties 绑定

## 3. 核心知识点

### 3.1 Starter 是什么

**Starter** 是 SpringBoot 的"依赖聚合 + 自动配置"封装，让使用者引一个依赖就能拿到功能。本质是**一个可复用的 jar**。

官方文档明确：starter 拆成**两个模块**——逻辑与聚合分离：

```
{name}-spring-boot-autoconfigure    ← 自动配置逻辑（配置类/条件/属性绑定）
{name}-spring-boot-starter          ← 依赖聚合（只声明依赖，无代码）
```

| 模块 | 职责 | 内容 |
| --- | --- | --- |
| autoconfigure 模块 | 自动配置逻辑 | @AutoConfiguration 类、条件注解、@ConfigurationProperties |
| starter 模块 | 依赖聚合 | pom 声明依赖 autoconfigure + 所需库；无 Java 代码 |

> **为什么拆两个**：① 使用者可只引 autoconfigure（不引 starter 避免传递依赖）；② starter 只做聚合，关注点分离；③ 便于模块化（呼应 [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)）。

### 3.2 双模块拆分 ★

```
my-spring-boot-autoconfigure/        ← 核心逻辑模块
├── src/main/java/com/example/
│   ├── MyFileUploadAutoConfiguration.java
│   └── MyFileUploadProperties.java
└── src/main/resources/META-INF/spring/
    └── org.springframework.boot.autoconfigure.AutoConfiguration.imports

my-spring-boot-starter/              ← 聚合模块（无代码）
├── pom.xml 依赖 my-spring-boot-autoconfigure
└── （无 java 源码，只有依赖声明）
```

**starter 模块 pom**（关键：只声明依赖，不打包业务代码）：

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-spring-boot-autoconfigure</artifactId>
    <version>1.0.0</version>
</dependency>
```

### 3.3 命名规范（官方）

| 场景 | 规范 | 示例 |
| --- | --- | --- |
| 自动配置类 | 后缀 `AutoConfiguration` | `MyFileUploadAutoConfiguration` |
| autoconfigure 模块 | `{name}-spring-boot-autoconfigure` | `my-spring-boot-autoconfigure` |
| starter 模块 | `{name}-spring-boot-starter` | `my-spring-boot-starter` |
| 官方/第三方 starter | 前缀 `spring-boot-starter-`（官方） | `spring-boot-starter-web` |

> 自动配置类尽量排在 .imports 文件**靠前**，且避免使用 `spring.factories`（旧机制，Boot 2.7+ 用 .imports）。

### 3.4 自动配置类核心写法（@AutoConfiguration + 条件）★

Boot 2.7+ 用 `@AutoConfiguration`（元注解含 @Configuration）替代 @Configuration：

```java
@AutoConfiguration                                  // = @Configuration + 自动配置标识
@ConditionalOnClass(MyFileUploadClient.class)       // 有依赖类才生效
@EnableConfigurationProperties(MyFileUploadProperties.class)  // 启用属性绑定
public class MyFileUploadAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean                        // 用户自定义则跳过默认
    public MyFileUploadClient myFileUploadClient(MyFileUploadProperties props) {
        return new MyFileUploadClient(props.getEndpoint());
    }

    @Bean
    @ConditionalOnMissingBean
    public MyFileUploadHealthIndicator health(MyFileUploadClient client) {
        return new MyFileUploadHealthIndicator(client);
    }
}
```

要点：
- `@ConditionalOnClass` 判断依赖类是否存在（缺 jar 不装配）
- `@ConditionalOnMissingBean` 让用户自定义优先（覆盖默认）
- `@EnableConfigurationProperties` 注册属性绑定类
- 依赖其他自动配置的 Bean 时用 `@AutoConfigurationAfter`/`@AutoConfigurationBefore` 声明顺序

### 3.5 属性绑定与配置元数据

属性绑定类（同 [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)）：

```java
@ConfigurationProperties(prefix = "app.upload")      // 前缀
public class MyFileUploadProperties {
    private String endpoint = "http://localhost:8080";  // 默认值
    private long maxSize = 10 * 1024 * 1024;             // 默认值
    private boolean enabled = true;
    // getter/setter（必须）
}
```

**配置元数据**（给 IDE 提示）：生成 `spring-autoconfigure-metadata.properties` 或使用 IDE 插件生成 `additional-spring-configuration-metadata.json`，让使用者写配置时有自动补全和说明。

```json
// src/main/resources/META-INF/additional-spring-configuration-metadata.json
{
  "properties": [
    { "name": "app.upload.endpoint", "type": "java.lang.String", "description": "上传服务地址" }
  ]
}
```

### 3.6 注册：.imports 文件

自动配置类必须在 `.imports` 注册才生效：

```
# src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.example.MyFileUploadAutoConfiguration
```

每行一个全限定类名，启动时 `AutoConfigurationImportSelector` 读取并按条件筛选（见 [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md) 3.4/3.5）。

### 3.7 测试自动配置

```java
@SpringBootTest
@AutoConfigureWebTestClient
class MyFileUploadAutoConfigurationTest {

    @Test
    void whenNoUserBean_thenDefaultCreated(@Autowired MyFileUploadClient client) {
        assertNotNull(client);
    }

    @Test
    void whenUserBean_thenDefaultSkipped(@Autowired(required = false) MyFileUploadClient client) {
        // 用户自定义 MyFileUploadClient 时，默认不注册
    }
}
```

用 `@AutoConfigureTestDatabase`（数据库）、`@AutoConfigureMockMvc`（Web）等配套测试注解隔离测试环境。

### 3.8 完整示例：文件上传 starter

**① 自动配置类**：

```java
@AutoConfiguration
@ConditionalOnClass(MyFileUploadClient.class)
@ConditionalOnProperty(prefix = "app.upload", name = "enabled", havingValue = "true", matchIfMissing = true)
@EnableConfigurationProperties(MyFileUploadProperties.class)
public class MyFileUploadAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public MyFileUploadClient myFileUploadClient(MyFileUploadProperties props) {
        return new MyFileUploadClient(props.getEndpoint(), props.getMaxSize());
    }
}
```

**② 使用方配置**：

```yaml
app:
  upload:
    endpoint: http://file-server:9000
    max-size: 10485760
```

**③ 使用方依赖**：

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>my-spring-boot-starter</artifactId>
    <version>1.0.0</version>
</dependency>
```

**④ 效果**：应用启动时自动创建 `MyFileUploadClient` Bean，用 `@Autowired` 直接注入即可——零配置拿到完整功能。

### 3.9 常见坑

- **自动配置类没注册 .imports** → 不生效（最常犯）
- **@ConditionalOnClass 引不存在的类** → 编译失败；用 name 字符串全限定名
- **属性类无 getter/setter** → 绑定静默失败
- **@ConditionalOnMissingBean 泛型/接口边界** → 误匹配
- **starter 模块误放代码** → 逻辑和聚合没分离
- **版本冲突**：starter 传递依赖与主项目冲突 → 版本仲裁/排除

## 4. 最佳实践

- 拆 autoconfigure + starter 两模块（官方推荐）
- 自动配置类命名 `XxxAutoConfiguration`，注册进 .imports
- 用 @ConditionalOnClass（判依赖）+ @ConditionalOnMissingBean（用户可覆盖）+ @ConditionalOnProperty（开关）
- 属性提供默认值，prefix 语义化
- 生成配置元数据给 IDE 提示
- 提供测试注解（@AutoConfigureXxx）配套
- 依赖顺序用 @AutoConfigurationBefore/After 声明

## 5. 常见踩坑

- **@ConditionalOnClass 用 Class 引用缺失类** → 启动失败；改 name 字符串
- **多条件叠加顺序**：@ConditionalOnMissingBean 判断依赖已创建的 Bean，注意 bean 创建顺序
- **与 Boot4 兼容**：包名重构（模块化）后 starter 需同步升级，见 [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)
- **测试漏配**：自动配置测试要覆盖"用户覆盖默认"的场景（@ConditionalOnMissingBean 生效）

## 6. 小结

- Starter = autoconfigure（逻辑）+ starter（聚合）双模块。
- 自动配置类用 @AutoConfiguration + 条件注解 + @ConfigurationProperties。
- 注册到 .imports，生成配置元数据。
- @ConditionalOnMissingBean 是"用户自定义优先"的关键。
- 测自动配置要覆盖默认创建与用户覆盖两场景。

## 7. 关联笔记

- 上一篇：[04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)
- 下一篇：[06-SpringBoot自定义Starter实践](06-SpringBoot自定义Starter实践.md)
- [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)：自动装配机制（本篇的基石）
- [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)：@ConfigurationProperties 绑定
- orm 域 [07-Spring Boot集成与配置详解](../数据访问层/07-Spring Boot集成与配置详解.md)：现有集成 starter 的实际写法

## 8. 参考资料

- [Spring Boot 官方：Developing Auto-configuration](https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html)，查询日期 2026-08-11
- [Baeldung：Creating a Custom Starter with Spring Boot](https://www.baeldung.com/spring-boot-custom-starter)，查询日期 2026-08-11
- [Spring Boot 3: Creating a custom starter](https://bplo.net/posts/spring-boot-3-custom-starter.html)，查询日期 2026-08-11
