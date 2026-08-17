---
tags: [JUnit, JUnit5, 单元测试, 测试框架, 参数化测试, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/测试）
归属: 01-学习/Java/测试
---

# 01-JUnit 5详解

> 版本基线：JUnit 5（Jupiter 模型）；**JUnit 6 已发布（2026），核心 Jupiter 模型延续、版本号统一**，本篇内容对 JUnit 6 同样适用（见第 7 节）
> 受众：Java 后端开发，要写单元测试。默认你懂 Java 注解、Maven/Gradle（[00-构建工具总览·Maven & Gradle选型对比](../构建工具/00-构建工具总览·Maven & Gradle选型对比.md)）。
> 关联笔记：[00-测试体系总览](00-测试体系总览.md)、[02-Mockito详解](02-Mockito详解.md)、[04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)

## 📋 总纲

- 1. JUnit 5 架构（Platform/Jupiter/Vintage）
- 2. 快速上手
- 3. 常用注解
- 4. 生命周期与执行顺序
- 5. 参数化测试
- 6. 嵌套测试与动态测试
- 7. 扩展模型与 JUnit 6 现状
- 8. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 JUnit 5 三件套（Platform/Jupiter/Vintage）架构
2. 用 @Test/@BeforeEach/@AfterEach/@DisplayName 写基础测试
3. 用 @ParameterizedTest 做参数化测试（@ValueSource/@CsvSource/@MethodSource）
4. 用 @Nested 组织嵌套测试
5. 理解生命周期回调与执行顺序
6. 知道 JUnit 6 现状（Jupiter 模型延续）
7. 避开常见坑（命名/单测隔离/随机顺序）

## 前置知识

- 需掌握：Maven/Gradle 依赖、Java 注解

---

## 1. JUnit 5 架构（Platform/Jupiter/Vintage）

JUnit 5 由三个子项目组成：

```
JUnit 5
├── JUnit Platform     ← 启动测试的"底座"(Launcher/TestEngine API)
├── JUnit Jupiter      ← 编程模型(写测试的注解/API) + 扩展模型
└── JUnit Vintage      ← 兼容 JUnit 4(老测试不用改)
```

| 组件 | 作用 |
|---|---|
| **Platform** | 在 JVM 上启动测试框架的根基，对接 IDE/Maven/Gradle |
| **Jupiter** | 你写测试用的：@Test/@BeforeEach/断言等 |
| **Vintage** | 运行 JUnit 3/4 老测试的兼容引擎 |

**依赖**（Maven）：
```xml
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.11.x</version>   <!-- 聚合依赖: API+Engine+Params -->
    <scope>test</scope>
</dependency>
```

> 💡 **记忆锚点**：**Platform 是底座，Jupiter 是笔，Vintage 是翻译器**——三者协作让 JUnit 5 既能写新测试又能跑老测试。

---

## 2. 快速上手

```java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {

    @Test
    void add_should_return_sum() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(2, 3), "2+3 应该等于 5");
    }

    @Test
    void divide_by_zero_should_throw() {
        Calculator calc = new Calculator();
        assertThrows(ArithmeticException.class, () -> calc.divide(1, 0));
    }
}
```

**断言速查**：

| 断言 | 作用 |
|---|---|
| `assertEquals/assertNotEquals` | 相等/不等 |
| `assertTrue/assertFalse` | 布尔 |
| `assertNull/assertNotNull` | 空/非空 |
| `assertSame/assertNotSame` | 引用同一 |
| `assertThrows` | 断言抛异常 |
| `assertAll` | 组合断言（全部执行，汇总失败） |
| `assertTimeout` | 超时断言 |

---

## 3. 常用注解

| 注解 | 作用 |
|---|---|
| `@Test` | 标记测试方法 |
| `@DisplayName` | 测试显示名（中文可读） |
| `@BeforeEach/@AfterEach` | 每个测试前后执行 |
| `@BeforeAll/@AfterAll` | 所有测试前后执行（static） |
| `@Disabled` | 禁用测试 |
| `@Tag` | 打标签（分组运行） |
| `@Nested` | 嵌套测试类 |
| `@ParameterizedTest` | 参数化测试 |

```java
@DisplayName("计算器测试")
class CalculatorTest {

    @BeforeAll
    static void initAll() { /* 类加载时执行一次 */ }

    @BeforeEach
    void init() { /* 每个测试前执行 */ }

    @Test
    @DisplayName("加法：2 + 3 = 5")
    void add() { ... }

    @Test
    @Disabled("待实现")
    void notReady() { ... }
}
```

---

## 4. 生命周期与执行顺序

```
@BeforeAll (static, 一次)
  └─ 每个测试:
      @BeforeEach
         @Test  ← 被测方法
      @AfterEach
@AfterAll (static, 一次)
```

**执行顺序**：默认**不确定**（刻意不保证顺序，鼓励测试独立）。需要顺序时用 `@TestMethodOrder`：

```java
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class OrderedTest {
    @Test @Order(1) void first() { }
    @Test @Order(2) void second() { }
}
```

> ⚠️ **原则**：测试之间应**相互独立**（不依赖执行顺序），这是单元测试的黄金法则。

---

## 5. 参数化测试 ★

**场景**：同一逻辑多组输入验证。

```java
@ParameterizedTest
@ValueSource(strings = {"racecar", "radar", "level"})
void isPalindrome_should_return_true(String word) {
    assertTrue(PalindromeChecker.isPalindrome(word));
}

@ParameterizedTest
@CsvSource({"1,1,2", "2,3,5", "10,20,30"})
void add(int a, int b, int expected) {
    assertEquals(expected, calc.add(a, b));
}

@ParameterizedTest
@MethodSource("provideNames")
void testWithMethodSource(String name) { ... }

static Stream<String> provideNames() {
    return Stream.of("Alice", "Bob", "Charlie");
}
```

| 数据源 | 说明 |
|---|---|
| `@ValueSource` | 简单值（strings/ints/...） |
| `@CsvSource` | CSV 多参数 |
| `@CsvFileSource` | CSV 文件 |
| `@MethodSource` | 方法返回 Stream |
| `@EnumSource` | 枚举 |

> 💡 **记忆锚点**：**参数化 = 一份测试逻辑 + 多组数据**——@ValueSource 给单参，@CsvSource 给多参，@MethodSource 最灵活。

---

## 6. 嵌套测试与动态测试

### 6.1 @Nested 嵌套测试（按业务分组）

```java
@DisplayName("Stack 测试")
class StackTest {

    @Nested
    @DisplayName("空栈时")
    class WhenEmpty {
        @Test void is_empty() { assertTrue(stack.isEmpty()); }
        @Test void throws_when_peek() { assertThrows(Exception.class, stack::peek); }
    }

    @Nested
    @DisplayName("压入元素后")
    class AfterPush {
        @BeforeEach void push() { stack.push(1); }
        @Test void not_empty() { assertFalse(stack.isEmpty()); }
    }
}
```

### 6.2 动态测试 @TestFactory（运行时生成）

```java
@TestFactory
Collection<DynamicTest> dynamicTests() {
    return List.of(
        DynamicTest.dynamicTest("1+1=2", () -> assertEquals(2, calc.add(1, 1))),
        DynamicTest.dynamicTest("2+2=4", () -> assertEquals(4, calc.add(2, 2)))
    );
}
```

---

## 7. 扩展模型与 JUnit 6 现状 ★

### 7.1 扩展模型（@ExtendWith）

JUnit 5 的核心设计：**扩展点**（Extension）替代 JUnit 4 的 Runner：

| 扩展点 | 场景 |
|---|---|
| `BeforeEachCallback/AfterEachCallback` | 每个测试前后 |
| `ParameterResolver` | 自定义参数注入 |
| `TestExecutionExceptionHandler` | 异常处理 |
| `TestWatcher` | 测试结果监听（报告） |

```java
// 自定义扩展示例
public class MyExtension implements BeforeEachCallback {
    @Override
    public void beforeEach(ExtensionContext context) {
        System.out.println("before: " + context.getDisplayName());
    }
}

@ExtendWith(MyExtension.class)
class MyTest { ... }
```

### 7.2 JUnit 6 现状（2026-08 查证）

- **JUnit 6 已发布**（官方 2025-09-30 发布，当前 6.1.2），基于 Jupiter 模型**延续演进**
- 主要变化：**平台统一版本号**（不再 Platform/Jupiter/Vintage 分开版本）、清理废弃 API、强化模块化
- **JUnit 5 → 6 迁移**：核心注解/断言几乎不变，主要改依赖坐标（junit-jupiter → junit）
- **存量项目**：JUnit 5 仍稳定可用；**新项目**可考虑直接用 JUnit 6

> ⚠️ **实事求是**：JUnit 6 不是重写，是"JUnit 5 的延续+清理"。本篇的 Jupiter 知识（@Test/参数化/嵌套/扩展）在 6 里完全适用。

---

## 8. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #J1 | 测试依赖执行顺序 | 单独跑过、全量跑挂 | 测试独立，用 @TestMethodOrder 显式排序 |
| #J2 | @BeforeAll 忘 static | 启动报错 | @BeforeAll/@AfterAll 必须 static |
| #J3 | 断言消息写反 | 失败信息误导 | assertEquals(期望, 实际, 消息) |
| #J4 | 多断言中断 | 只看第一个失败 | assertAll 汇总 |
| #J5 | 参数化数据源写错 | 找不到方法 | @MethodSource 方法必须 static |
| #J6 | 测试访问外部资源 | CI 环境挂 | 用 Testcontainers/Mock（见 [05-Spring Boot测试与Testcontainers](05-Spring Boot测试与Testcontainers.md)） |

## 小结

- JUnit 5 = Platform（底座）+ Jupiter（编程模型）+ Vintage（兼容 4）
- 注解体系：@Test/@BeforeEach/@AfterEach/@DisplayName/@Disabled
- 参数化测试：@ValueSource/@CsvSource/@MethodSource 一份逻辑多组数据
- @Nested 组织嵌套，@TestFactory 动态生成
- 扩展模型 @ExtendWith 替代 Runner；**JUnit 6 延续 Jupiter，核心不变**

## 下一篇

[02-Mockito详解](02-Mockito详解.md)——单元测试的 Mock 利器

## 参考资料

- [JUnit 5 用户指南（官方）](https://junit.org/junit5/docs/current/user-guide/)，查询日期：2026-08-09
- [JUnit 6 Release Notes（官方）](https://docs.junit.org/6.1.2/release-notes.html)，查询日期：2026-08-09
- [JUnit 5 is dead, long live JUnit 6!](https://medium.com/javarevisited/junit-5-is-dead-long-live-junit-6-e142806c11a6)，查询日期：2026-08-09
