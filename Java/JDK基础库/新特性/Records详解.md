---
tags: [Java, JDK17, record, 语言特性]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/JDK基础库/新特性）
归属: 01-学习/Java/JDK基础库/新特性
---

# Records详解

## 📋 总纲

1. 基本概念：record 是什么、演进历史、快速上手
2. 语法与特性：声明式数据类、compact constructor、静态成员
3. 与 Lombok 注解对比（关联 [Lombok详解](../../三方库/Lombok详解.md)）
4. 使用注意点与坑
5. 原理与设计（补充知识）
6. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 record 是什么

record 是 Java 的**语言原生不可变数据载体**：一行声明，编译器自动生成构造器、访问器、equals/hashCode/toString，杜绝样板代码：

```java
// 等价于手写：final 类 + final 字段 + 全参构造 + 访问器 + equals/hashCode/toString
public record Point(int x, int y) {}
```

- **演进**：Java 14 preview（JEP 359）→ Java 16 正式（JEP 395）→ **JDK 17 LTS 起全面可用**（本笔记面向 JDK17+）
- **定位**：和 Lombok 的 @Value/@Data 解决同一类问题，但是**语言级**方案，零依赖
- 与 Lombok 对比的完整内容见 [Lombok详解](../../三方库/Lombok详解.md) 4.5 节（两个文档互相关联）

### 1.2 一句话特性

    record 组件（component）→ 自动生成：
    ① final 类（不可继承）
    ② private final 字段（每个组件一个）
    ③ 全参构造器
    ④ 访问器（命名 = 组件名，如 x()，不是 getX()）
    ⑤ equals / hashCode / toString（基于所有组件）

### 1.3 快速上手

```java
public record User(Long id, String name, Integer age) {}

// 使用
User u = new User(1L, "robin", 30);
u.id();                // 1L  访问器（无 get 前缀）
u.name();              // "robin"
System.out.println(u); // User[id=1, name=robin, age=30]
u.equals(new User(1L, "robin", 30));   // true，按组件全比较
```

---

## 2. 语法与特性

### 2.1 基本声明

```java
// 泛型 record
public record Pair<K, V>(K key, V value) {}

// 实现接口
public record Point(int x, int y) implements Comparable<Point> {
    @Override
    public int compareTo(Point o) { return Integer.compare(x, o.x); }
}

// 局部 record（方法内声明，Java 16+）
public void demo() {
    record Local(int a) {}
    Local l = new Local(1);
}

// 嵌套 record（类内部）
public class Outer {
    public record Inner(String name) {}
}
```

### 2.2 compact constructor（紧凑构造器）

可以自定义构造逻辑（校验/归一化），但不用重复写参数列表：

```java
public record Range(int min, int max) {
    // compact constructor：参数列表省略，隐式 this.min=min; this.max=max 在体后执行
    public Range {
        if (min > max) {
            throw new IllegalArgumentException("min 不能大于 max");
        }
        // 归一化：给【参数】重新赋值（参数非 final）
        // 注意：不能指望 this.min = xxx 生效 —— 会被体后的隐式赋值覆盖
    }
}
```

**关键细节**
- compact constructor 里**字段赋值会被隐式赋值覆盖**（隐式 `this.min = min` 在体后执行）
- 归一化的正确姿势是**给参数重新赋值**（参数不是 final）
- 校验抛异常会阻止对象创建 → 保证「record 对象永远合法」

### 2.3 静态成员与工厂方法

```java
public record User(Long id, String name) {
    public static final User EMPTY = new User(0L, "");   // 静态常量

    public static User of(Long id, String name) {          // 静态工厂
        return new User(id, name == null ? "" : name);
    }
}
```

### 2.4 自定义业务方法

```java
public record User(Long id, String name) {
    public String displayName() {       // 额外方法随便加
        return name == null ? "匿名" : name;
    }
}
```

### 2.5 序列化

- record 序列化走**构造器**（反序列化时调用全参构造，参数校验依然生效）—— 比普通 JavaBean 反序列化（不经过构造器）更安全
- **不强制 serialVersionUID**：record 的序列化形式由组件决定，组件变化即序列化形式变化
- 兼容旧版本：若实现 Serializable 且组件不变，序列化兼容性 OK

---

## 3. 与 Lombok 注解对比

> 📎 关联：[Lombok详解](../../三方库/Lombok详解.md)（Lombok 全注解详解，本表是双向对比）

| 维度 | record（JDK17+） | Lombok @Value | Lombok @Data |
|------|-----------------|---------------|-------------|
| 引入方式 | 语言原生，零依赖 | 三方库 + 编译期处理器 | 三方库 + 编译期处理器 |
| 可变性 | 不可变（final 字段） | 不可变 | 可变（有 setter） |
| 继承 | 不可继承（隐式 final） | final 类 | 可继承 |
| 访问器命名 | `x()`（无 get） | `getX()` | `getX()` |
| 全参构造 | 自动 | 自动 | 不自动（需 @AllArgsConstructor） |
| Builder | 无（可配合外部 Builder） | 可加 @Builder | 可加 @Builder |
| 序列化 | 走构造器，更安全 | 普通 JavaBean 序列化 | 普通 JavaBean 序列化 |
| 校验/归一化 | compact constructor | @NonNull 等 | @NonNull 等 |
| 与 JPA 实体 | 不友好（final+无无参构造） | 可用 | 常用（但 @Data 有懒加载坑） |
| JDK 兼容风险 | 无 | 有（依赖 javac 内部 API） | 有 |

**选型建议**

    record 优先的场景
    ① DTO / 返回值 / 不可变数据载体
    ② 需要 equals/hashCode 的值对象（Map key）
    ③ 团队想少一个依赖

    Lombok 保留的场景
    ① JPA 实体（需要无参构造、可变、继承）
    ② 需要 @Builder 链式 + 继承链（@SuperBuilder）
    ③ 字段可变的业务对象
    ④ 存量项目不想动

**结论**：record 吃下「简单不可变数据」的大头，Lombok 留在「实体/可变/构建器」场景 —— 两者共存是现代 Java 项目的主流形态。

---

## 4. 使用注意点与坑

### 4.1 不可变性的边界

- 字段是 final，但**引用类型指向的对象本身可变**：

```java
public record Holder(List<String> list) {}
var h = new Holder(new ArrayList<>());
h.list().add("x");   // 编译通过！list 指向的 ArrayList 被改了 —— record 只保证引用不可变
```
- 要真正不可变：组件用不可变类型（List.of() 等），构造时防御性拷贝（compact constructor 里 `list = List.copyOf(list)`）

### 4.2 访问器命名与框架兼容

- `x()` 而非 `getX()` → 不符合 JavaBean 规范，**老框架可能不认**（BeanUtils、部分序列化库）
- Jackson 支持 record：**Jackson 2.12+** 原生支持（Spring Boot 2.6+/Spring 6 无痛）
- MyBatis 等 ORM 对 record 支持有限（无无参构造）—— 别拿 record 当实体

### 4.3 与 JPA / MyBatis 不友好

- 无无参构造 → JPA 实体要求无参构造，冲突
- final 字段 + 无 setter → 持久化框架难赋值
- **结论**：record 用于传输/值对象，实体继续用 Lombok 或手写

### 4.4 compact constructor 的赋值陷阱

- 在 compact constructor 里 `this.x = 归一化值` **会被隐式赋值覆盖**（见 2.2）
- 正确做法：给参数重新赋值；或干脆用静态工厂做归一化

### 4.5 序列化版本注意

- 不写 serialVersionUID 时，**组件列表变化 = 序列化形式变化** → 长期存储/跨版本传输的 record 要小心（显式声明 serialVersionUID 可以缓解，但组件变化仍会破坏兼容）
- 反序列化走构造器 → 老数据反序列化时 compact constructor 校验可能抛异常（好事：坏数据进不来）

### 4.6 与反射/代理

- 反射可以读组件，但不能通过反射改 final 字段值（不可变性在字节码层面）
- Spring 的 CGLIB 代理对 final 类无效 → record 不能被 CGLIB 子类化；需要代理时用 JDK 动态代理（接口）

---

## 5. 原理与设计（补充知识）

### 5.1 编译期生成机制

- record 是 **javac 语言级语法糖**：编译器在 AST 阶段识别 record 声明，自动生成 final 类、final 字段、构造器、访问器、equals/hashCode/toString
- 与 Lombok 的异同：**殊途同归** —— Lombok 靠注解处理器改 AST（依赖 javac 内部 API），record 是 javac 原生支持（无兼容风险）
- 反编译验证：`javap -p Point.class` 能看到所有生成的方法

### 5.2 设计意图

- 解决「数据载体样板代码」这一普遍痛点（Java 一直被吐槽啰嗦）
- 选择「不可变」为默认：不可变对象天然线程安全、可安全共享、适合函数式风格
- 访问器命名与组件一致（`x()`）：简单直接，避免 get/set 冗余

### 5.3 与 Kotlin data class 对比（扩展视角）

    Kotlin data class：copy() 方法、解构、componentN() —— record 没有 copy/解构
    record：语言更克制，只做最小必要

---

## 6. 面试追问清单（带答案）

### 6.1 record 是 JDK 几引入的？

A：Java 14 以 preview 引入（JEP 359），**Java 16 正式化**（JEP 395），JDK 17 LTS 起全面可用。生产项目按 JDK17+ 使用即可。

### 6.2 record 和 Lombok @Value 有什么区别？

A：@Value 生成 final 类 + final 字段 + getter（getX 前缀）+ 全参构造；record 是语言原生，访问器叫 x() 不带 get，且反序列化走构造器更安全。record 零依赖零兼容风险，@Value 依赖编译期处理器。功能上高度重合，record 优先。

### 6.3 record 能继承吗？能实现接口吗？

A：不能继承也不能被继承（隐式 final）。可以实现接口（如 Comparable、自定义接口），也可以嵌套、局部声明、泛型化。

### 6.4 compact constructor 是什么？怎么归一化参数？

A：record 的自定义构造器写法，省略参数列表，隐式在体后执行 this.x = x。用于校验和归一化。归一化要给**参数重新赋值**（如 num = num / gcd），不能 this.x = 归一化 —— 那会被隐式赋值覆盖。

### 6.5 record 和 Jackson 怎么配合？

A：Jackson 2.12+ 原生支持 record（按组件名反序列化，走构造器）。Spring Boot 2.6+/Spring 6 无感使用。老版本需要 Jackson 参数名模块（-parameters 编译参数）。

### 6.6 record 能做 JPA 实体吗？

A：不适合。JPA 要求无参构造、可变字段、可继承 —— record 全占反方向。record 用在 DTO/值对象/传输层，实体用 Lombok 或手写。

### 6.7 record 会取代 Lombok 吗？

A：部分取代。DTO/不可变值对象场景 record 完胜；但实体（可变+无参构造）、@Builder 链式+继承（@SuperBuilder）、日志等场景 Lombok 仍有价值。结论：共存。

### 6.8 record 不可变，为什么还会被修改？

A：record 只保证**引用不可变**，不保证引用指向的对象不可变（List 组件可以被 add）。要真不可变：组件用不可变类型 + compact constructor 防御性拷贝（List.copyOf）。