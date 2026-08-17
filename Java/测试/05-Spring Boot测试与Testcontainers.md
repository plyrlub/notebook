---
tags: [SpringBoot, 测试, Testcontainers, 集成测试, "@SpringBootTest", "@WebMvcTest", Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/测试）
归属: 01-学习/Java/测试
---

# 05-Spring Boot测试与Testcontainers

> 版本基线：Spring Boot 3.x/4.x（测试切片注解 + Testcontainers 1.19+/1.20）；Spring Boot 4.1 起 @MockitoBean 替代 @MockBean
> 受众：Java 后端开发，Spring Boot 项目要写集成测试。默认你懂 [01-JUnit 5详解](01-JUnit 5详解.md)、[02-Mockito详解](02-Mockito详解.md)、Spring Boot 基础。
> 关联笔记：[00-测试体系总览](00-测试体系总览.md)、[01-JUnit 5详解](01-JUnit 5详解.md)、[02-Mockito详解](02-Mockito详解.md)、[04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)

## 📋 总纲

- 1. Spring Boot 测试体系
- 2. 依赖与基础
- 3. @SpringBootTest（全量集成测试）
- 4. 切片测试（@WebMvcTest/@DataJpaTest）★
- 5. Mock 与 Bean 覆盖（@MockitoBean）
- 6. Testcontainers（真实依赖测试）★
- 7. 测试金字塔实践
- 8. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 Spring Boot 测试体系（全量 vs 切片）
2. 用 @SpringBootTest 写集成测试（MockMvc/随机端口）
3. 用 @WebMvcTest/@DataJpaTest 写切片测试（快、聚焦）
4. 用 @MockitoBean 替换 Bean（注意 4.x 新 API）
5. 用 Testcontainers 起真实数据库/中间件测试
6. 按测试金字塔规划测试策略
7. 避开常见坑（上下文重启/切片漏配/容器泄漏）

## 前置知识

- [01-JUnit 5详解](01-JUnit 5详解.md)、[02-Mockito详解](02-Mockito详解.md)——测试基础
- 需掌握：Spring Boot、Maven/Gradle、Docker 基础

---

## 1. Spring Boot 测试体系

**两大类型**：

| 类型 | 注解 | 加载内容 | 速度 |
|---|---|---|---|
| **全量测试** | @SpringBootTest | 整个应用上下文 | 慢 |
| **切片测试** | @WebMvcTest/@DataJpaTest 等 | 只加载某层 | 快 |

```
单元测试(JUnit+Mockito) ← 最多, 最快
   ↓
切片测试(@WebMvcTest/@DataJpaTest) ← 中, 快
   ↓
集成测试(@SpringBootTest + Testcontainers) ← 少, 慢
```

---

## 2. 依赖与基础

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

**starter-test 自带**：JUnit 5、Mockito、AssertJ、Hamcrest、JSONPath、MockMvc（全打包好）。

---

## 3. @SpringBootTest（全量集成测试）

```java
@SpringBootTest   // 启动完整应用上下文
class UserServiceIT {

    @Autowired
    UserService userService;

    @Test
    void register_should_work() {
        // 走真实 Bean 链(可能连数据库)
    }
}

// Web 层测试: 随机端口 + MockMvc
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class UserControllerIT {

    @LocalServerPort
    int port;

    @Autowired
    TestRestTemplate restTemplate;

    @Test
    void getUser_should_return_200() {
        ResponseEntity<User> resp = restTemplate
            .getForEntity("/api/users/1", User.class);
        assertThat(resp.getStatusCode().value()).isEqualTo(200);
    }
}
```

**webEnvironment 选项**：

| 值 | 说明 |
|---|---|
| `MOCK`（默认） | MockMvc 模拟，不起真实服务器 |
| `RANDOM_PORT` | 随机端口起真实服务器 |
| `DEFINED_PORT` | 指定端口 |
| `NONE` | 不起 Web 环境 |

---

## 4. 切片测试（@WebMvcTest/@DataJpaTest）★

**切片 = 只加载某一层的 Bean**，快且聚焦。

### 4.1 @WebMvcTest（只测 Controller 层）

```java
@WebMvcTest(UserController.class)          // 只加载 MVC 相关 Bean
class UserControllerTest {

    @Autowired
    MockMvc mockMvc;                        // 或 MockMvcTester(Boot 4)

    @MockitoBean                            // mock 依赖(替代 @MockBean, Boot 4.1+)
    UserService userService;

    @Test
    void getUser_should_return_name() throws Exception {
        given(userService.getUsername(1L)).willReturn("Alice");   // BDDMockito

        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("Alice"));
    }
}
```

**@WebMvcTest 只加载**：@Controller/@ControllerAdvice/Filter/Converter 等 Web 组件——**不加载** @Component/@Service/@Repository（所以依赖要 mock）。

### 4.2 @DataJpaTest（只测 JPA 层）

```java
@DataJpaTest                    // 只加载 JPA 相关: Repository/Entity
class UserRepositoryTest {

    @Autowired
    UserRepository userRepository;

    @Test
    void findByEmail_should_find() {
        userRepository.save(new User("a@b.com"));
        Optional<User> found = userRepository.findByEmail("a@b.com");
        assertThat(found).isPresent();
    }
}
```

**默认行为**：事务回滚（每个测试独立）、替换数据源为内嵌库（H2）——**想用真实库用 @AutoConfigureTestDatabase(replace = NONE)** 或 Testcontainers。

**其他切片**：@DataMongoTest/@DataRedisTest/@JsonTest/@RestClientTest 等。

> 💡 **记忆锚点**：**切片测试 = "只切一层测"**——@WebMvcTest 切 Web 层（mock 服务），@DataJpaTest 切数据层（内嵌库），各测各的、快。

---

## 5. Mock 与 Bean 覆盖（@MockitoBean）

**替换上下文里的 Bean 为 mock**（集成测试中隔离外部依赖）：

```java
@SpringBootTest
class OrderServiceIT {

    @MockitoBean                     // Boot 3.4+/4.x 新注解(替代 @MockBean)
    PaymentClient paymentClient;

    @Autowired
    OrderService orderService;

    @Test
    void createOrder_should_call_payment() {
        given(paymentClient.pay(any())).willReturn(true);

        orderService.createOrder(...);

        verify(paymentClient).pay(any());
    }
}
```

| 注解 | 版本 | 说明 |
|---|---|---|
| `@MockBean` | 旧 | ⚠️ 已弃用（Spring Framework 6.2+） |
| **`@MockitoBean`** | Boot 3.4+/4.x | ✅ 推荐（Bean 覆盖更精确） |
| `@MockitoSpyBean` | 新 | spy Bean |

> ⚠️ **实事求是**：老教程大量用 @MockBean，新项目用 @MockitoBean；功能等价，只是 API 位置变了。

---

## 6. Testcontainers（真实依赖测试）★

**痛点**：@DataJpaTest 默认 H2 内嵌库——**和真实 MySQL/PG 行为有差异**（方言/锁/事务）。
**方案**：Testcontainers 在测试时用 **Docker 起真实数据库/中间件**。

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)  // 不用 H2
@Testcontainers
class UserRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource                       // 动态注入连接配置
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", postgres::getJdbcUrl);
        r.add("spring.datasource.username", postgres::getUsername);
        r.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    UserRepository userRepository;

    @Test
    void findByEmail_should_find() {
        // 走真实 PostgreSQL!
    }
}
```

**依赖**：
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>   <!-- 按需: mysql/redis/kafka... -->
    <scope>test</scope>
</dependency>
```

**支持范围**：PostgreSQL/MySQL/Redis/Kafka/RabbitMQ/Elasticsearch 等（模块化）。

> 💡 **记忆锚点**：**Testcontainers = "测试时的 Docker 工具箱"**——每次测试起一个真实中间件容器，测完销毁，环境一致、不留垃圾。

---

## 7. 测试金字塔实践

```
        /\   E2E(少量, 最慢)
       /  \  契约测试(微服务)
      /----\  集成测试(@SpringBootTest+Testcontainers, 适量)
     /------\  切片测试(@WebMvcTest/@DataJpaTest, 较多)
    /--------\  单元测试(JUnit5+Mockito, 最多, 最快)
```

**实践建议**：

| 层 | 工具 | 数量 |
|---|---|---|
| 单元 | JUnit5 + Mockito + AssertJ | 最多（70%+） |
| 切片 | @WebMvcTest/@DataJpaTest | 较多（20%） |
| 集成 | @SpringBootTest + Testcontainers | 适量（10%） |
| 性能 | JMH（[03-JMH基准测试详解](03-JMH基准测试详解.md)） | 专项 |

---

## 8. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #S1 | 每个测试类都 @SpringBootTest | 上下文反复重启,极慢 | 用切片测试 + @DirtiesContext 按需 |
| #S2 | 切片里忘了 mock 依赖 | UnsatisfiedDependencyException | @MockitoBean 补齐依赖 |
| #S3 | @MockBean 用旧 API | 弃用警告 | 换 @MockitoBean |
| #S4 | Testcontainers 忘配 Docker | 容器启动失败 | 本地装 Docker Desktop, CI 配 docker |
| #S5 | H2 与真实库行为差异 | 本地过/生产挂 | 关键 SQL 用 Testcontainers 真实库 |
| #S6 | @DataJpaTest 事务未回滚 | 测试互相污染 | 默认回滚别关; 需提交用 @Commit |
| #S7 | 容器每类都起 | 慢 | 静态 @Container 复用同一容器 |

## 小结

- Spring Boot 测试两大类型：@SpringBootTest 全量 + 切片（快）
- 切片：@WebMvcTest（Web 层 + mock 服务）/ @DataJpaTest（数据层 + 内嵌库）
- @MockitoBean 替换 Bean（Boot 4.x 新 API，替代 @MockBean）
- Testcontainers：Docker 起真实数据库/中间件，消除 H2 差异
- 测试金字塔：单元多、切片中、集成少

## 下一篇

[00-测试体系总览](00-测试体系总览.md)——回顾整个测试体系

## 参考资料

- [Spring Boot 官方: Testing](https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html)，查询日期：2026-08-09
- [Testcontainers 官方 Guide](https://testcontainers.com/guides/testing-spring-boot-rest-api-using-testcontainers/)，查询日期：2026-08-09
- [JetBrains: Testing Spring Boot with Testcontainers](https://blog.jetbrains.com/idea/2024/12/testing-spring-boot-applications-using-testcontainers/)，查询日期：2026-08-09
