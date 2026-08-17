---
tags: [AssertJ, 断言, 流式断言, 单元测试, 测试, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/测试）
归属: 01-学习/Java/测试
---

# 04-AssertJ与断言最佳实践

> 版本基线：AssertJ 3.x（Java 流式断言库，事实标准）
> 受众：Java 后端开发，已会 [01-JUnit 5详解](01-JUnit 5详解.md)，想让断言更可读。默认你懂 JUnit 基础断言。
> 关联笔记：[00-测试体系总览](00-测试体系总览.md)、[01-JUnit 5详解](01-JUnit 5详解.md)、[02-Mockito详解](02-Mockito详解.md)

## 📋 总纲

- 1. 为什么用 AssertJ
- 2. 快速上手
- 3. 常用断言（字符串/集合/异常）
- 4. 链式断言
- 5. 自定义断言
- 6. AssertJ vs JUnit vs Hamcrest
- 7. 断言最佳实践
- 8. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 AssertJ 的价值（流式 API、可读性、IDE 提示）
2. 用 assertThat 写字符串/集合/异常断言
3. 链式组合多个断言
4. 写自定义断言（领域对象）
5. 对比 AssertJ/JUnit/Hamcrest 并选型
6. 掌握断言最佳实践（避免脆弱断言）

## 前置知识

- [01-JUnit 5详解](01-JUnit 5详解.md)——测试框架基础
- 需掌握：Java 8+ lambda、Stream

---

## 1. 为什么用 AssertJ

**一句话记忆**：AssertJ 是**流式断言库**——`assertThat(actual).method().method()...` 链式调用，让断言像英语句子一样可读，且 IDE 自动补全提示丰富。

**对比 JUnit 断言**：

```java
// ❌ JUnit 断言: 方法多、参数顺序易混、错误信息差
assertEquals(3, list.size());
assertTrue(list.contains("a"));
assertTrue(list.contains("b"));

// ✅ AssertJ 流式: 自然语言可读, 一次断言多个
assertThat(list)
    .hasSize(3)
    .contains("a", "b");
```

**核心价值**：

| 优势 | 说明 |
|---|---|
| **可读性** | 链式断言像句子：`assertThat(list).hasSize(3).contains("a")` |
| **IDE 补全** | 类型感知，自动提示可用断言 |
| **错误信息** | 失败信息详细（期望 vs 实际） |
| **组合断言** | 一个 assertThat 链多个验证，失败汇总 |

**依赖**：
```xml
<dependency>
    <groupId>org.assertj</groupId>
    <artifactId>assertj-core</artifactId>
    <version>3.26.x</version>
    <scope>test</scope>
</dependency>
```

> 💡 **记忆锚点**：**AssertJ = "让断言说话"**——`assertThat(实际值).期望(条件)`，读起来就是一句人话。

---

## 2. 快速上手

```java
import static org.assertj.core.api.Assertions.assertThat;

@Test
void basic_assertions() {
    // 字符串
    assertThat("Hello World")
        .startsWith("Hello")
        .endsWith("World")
        .contains("lo Wo")
        .hasSize(11);

    // 数字
    assertThat(42)
        .isPositive()
        .isGreaterThan(40)
        .isLessThan(100);

    // 布尔
    assertThat(flag).isTrue();

    // 对象
    assertThat(user).isNotNull()
        .extracting(User::getName).isEqualTo("Alice");
}
```

---

## 3. 常用断言

### 3.1 字符串

```java
assertThat("Hello")
    .startsWith("He")
    .endsWith("lo")
    .contains("ell")
    .matches("H\\w+")
    .isNotEmpty()
    .hasSize(5);
```

### 3.2 集合

```java
assertThat(list)
    .hasSize(3)                    // 大小
    .contains("a", "b")            // 包含(无序)
    .containsExactly("a", "b", "c") // 完全匹配(有序)
    .containsAnyOf("x", "a")       // 任一包含
    .doesNotContain("z")           // 不包含
    .allMatch(s -> s.length() > 0) // 全部满足
    .anyMatch(s -> s.equals("a"))  // 任一满足
    .isEmpty();

// Map 断言
assertThat(map)
    .containsKey("name")
    .containsEntry("age", 30);
```

### 3.3 异常

```java
// 方式一: assertThatThrownBy
assertThatThrownBy(() -> service.divide(1, 0))
    .isInstanceOf(ArithmeticException.class)
    .hasMessage("/ by zero");

// 方式二: catchThrowable(拿到异常对象)
Throwable t = catchThrowable(() -> service.divide(1, 0));
assertThat(t).isInstanceOf(ArithmeticException.class);

// 方式三: assertThatCode(不需要异常时)
assertThatCode(() -> service.noop())
    .doesNotThrowAnyException();
```

---

## 4. 链式断言 ★

**核心优势：一条 assertThat 链多个断言**（失败时全报告，不会中断）：

```java
assertThat(user)
    .isNotNull()
    .extracting(User::getName, User::getAge)   // 提取多个字段
    .containsExactly("Alice", 30);

assertThat(users)
    .isNotEmpty()
    .allSatisfy(u -> {
        assertThat(u.getName()).isNotBlank();       // 嵌套断言
        assertThat(u.getAge()).isPositive();
    })
    .filteredOn(u -> u.getAge() > 18)              // 过滤后再断言
    .hasSize(2);

// extracting + flatExtracting
assertThat(users)
    .extracting(User::getOrders)                    // 提取嵌套集合
    .flatExtracting(Order::getId)
    .contains(1L, 2L);
```

> 💡 **记忆锚点**：**链式 = 一个 assertThat 到底**——isNotNull → extracting → 断言字段，一口气把"是什么、长啥样、对不对"全验证。

---

## 5. 自定义断言（领域断言）

**场景**：复杂领域对象，把断言封装成语义化的方法：

```java
// 自定义断言类
class UserAssert extends AbstractAssert<UserAssert, User> {

    UserAssert(User actual) {
        super(actual, UserAssert.class);
    }

    static UserAssert assertThatUser(User actual) {
        return new UserAssert(actual);
    }

    UserAssert hasAdultAge() {
        isNotNull();
        if (actual.getAge() < 18) {
            failWithMessage("Expected user to be adult, but age was %d", actual.getAge());
        }
        return this;
    }

    UserAssert hasValidName() {
        isNotNull();
        if (actual.getName() == null || actual.getName().isBlank()) {
            failWithMessage("Expected user to have valid name");
        }
        return this;
    }
}

// 使用
assertThatUser(user)
    .hasAdultAge()
    .hasValidName();
```

---

## 6. AssertJ vs JUnit vs Hamcrest

| 维度 | JUnit 断言 | Hamcrest | **AssertJ** |
|---|---|---|---|
| 风格 | 静态方法 | 匹配器组合 | **流式链** |
| 可读性 | 中 | 中 | **高** |
| IDE 补全 | 弱 | 中 | **强（类型感知）** |
| 错误信息 | 一般 | 好 | **详细** |
| 维护状态 | ✅ | ⚠️ 放缓 | **✅ 活跃** |
| 组合断言 | assertAll | 嵌套 | **天然链式** |

**选型**：**AssertJ 是主流推荐**（Spring Boot 测试默认引入）；Hamcrest 是历史方案（老项目）；JUnit 自带断言简单场景够用。

> ⚠️ **实事求是**：AssertJ 不是"必须"，但"更好用"——Spring Boot 官方测试文档默认用它，社区主流也是它。

---

## 7. 断言最佳实践

| 实践 | 说明 |
|---|---|
| **断言行为而非实现** | 测"返回什么"，不测"内部怎么调"（后者用 verify） |
| **避免脆弱断言** | 不断言精确时间/随机值/顺序（除非必要） |
| **一个测试一个关注点** | 但可用链式断言验证一个结果的多个面 |
| **用 extracting 聚焦字段** | 避免断言整个对象（脆弱） |
| **错误信息要可读** | 配合 @DisplayName 说明测试意图 |
| **集合断言用 containsExactly** | 顺序敏感时明确要求，防隐性变化 |

---

## 8. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #A1 | contains vs containsExactly 混淆 | 顺序不同也过/该过的没过 | 明确语义选择 |
| #A2 | 断言整个对象 | 字段变化即挂 | extracting 聚焦字段 |
| #A3 | 断言精确浮点 | 精度问题挂测试 | isCloseTo(期望, within(0.01)) |
| #A4 | 链式断言里混 JUnit 断言 | 风格不统一 | 统一用 AssertJ |
| #A5 | 异常断言方式选错 | 代码可读性差 | 用 assertThatThrownBy（见 3.3） |
| #A6 | 忘导入 assertThat | 编译错误 | static import Assertions.assertThat |

## 小结

- AssertJ 流式断言：`assertThat(actual).期望(...)` 链式可读
- 覆盖字符串/集合/异常/Map，IDE 补全强
- 链式 + extracting + filteredOn 组合强大
- 自定义断言封装领域语义
- 选型：AssertJ 是主流，配合 [02-Mockito详解](02-Mockito详解.md) 使用

## 下一篇

[05-Spring Boot测试与Testcontainers](05-Spring Boot测试与Testcontainers.md)——集成测试

## 参考资料

- [AssertJ 官方文档](https://assertj.github.io/doc/)，查询日期：2026-08-09
- [AssertJ GitHub](https://github.com/assertj/assertj)，查询日期：2026-08-09
- [Spring I/O 2025: Better Assertions with AssertJ](https://www.youtube.com/watch?v=k7sXn1v4fYc)，查询日期：2026-08-09
