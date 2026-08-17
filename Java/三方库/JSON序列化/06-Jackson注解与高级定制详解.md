---
tags:
  - Java
  - JSON
  - Jackson
  - 注解
  - 多态
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Jackson 注解与高级定制详解

## 📋 总纲

本篇是 Jackson 的「注解全家 + 多态 + 自定义」篇。读完你会：看懂大部分 Jackson 注解、做接口/抽象类多态反序列化（并避开 `enableDefaultTyping` 的 RCE 陷阱）、用 `JsonSerializer`/`JsonDeserializer` 自定义转换、正确处理日期时间、用 MixIn/视图做字段级控制。

> 前置：[05-Jackson核心与ObjectMapper详解](05-Jackson核心与ObjectMapper详解.md)；Boot 配合见 [07-Jackson与SpringBoot集成详解](07-Jackson与SpringBoot集成详解.md)；踩坑：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 1. 注解总表（★）

| 注解 | 作用 | 示例 |
|---|---|---|
| `@JsonProperty` | 改键名/必填 | `@JsonProperty("user_name")` |
| `@JsonIgnore` | 忽略字段 | `@JsonIgnore String secret` |
| `@JsonIgnoreProperties` | 类级忽略若干/`ignoreUnknown` | `@JsonIgnoreProperties({"a"}, ignoreUnknown=true)` |
| `@JsonInclude` | 值包含策略 | `@JsonInclude(Include.NON_NULL)` |
| `@JsonFormat` | 日期格式/时区 | `@JsonFormat(pattern="yyyy-MM-dd")` |
| `@JsonAutoDetect` | 覆写字段/getter 检测范围 | `@JsonAutoDetect(fieldVisibility=ANY)` |
| `@JsonGetter`/`@JsonSetter` | 指定序列化/反序列化方法 | `@JsonGetter("name")` |
| `@JsonAnyGetter`/`@JsonAnySetter` | 收集未知字段到 Map | 见下 |
| `@JsonPropertyOrder` | 字段输出顺序 | `@JsonPropertyOrder({"b","a"})` |
| `@JsonRawValue` | 原样输出字符串（不转义） | `@JsonRawValue String html` |
| `@JsonView` | 视图按场景字段 | 见下 |
| `@JsonNaming` | 按命名策略 | `@JsonNaming(SnakeCaseStrategy.class)` |

### 1.1 未知字段收纳：@JsonAnySetter / @JsonAnyGetter

```java
public class Extensible {
    Map<String, Object> ext = new HashMap<>();

    @JsonAnySetter
    void set(String key, Object val) { ext.put(key, val); }

    @JsonAnyGetter
    Map<String, Object> get() { return ext; }
}
```

**说明**：动态结构用 `@JsonAnySetter` 把未知键收进 Map、`@JsonAnyGetter` 把 Map 拍平输出，适合前后端传参扩展字段。

### 1.2 常见用法示例

```java
@JsonIgnoreProperties({"internal"}, ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
public class User {
    @JsonProperty("uid")
    private Long id;
    private LocalDateTime createdAt;
}
```

**说明**：类级一次声明忽略+空值省略+日期格式；字段级 `@JsonProperty` 改键名。日期需 JavaTimeModule 配合（见 4 节）。

## 2. 多态反序列化（★）

### 2.1 问题

接口/抽象类/`Object` 字段反序列化时，Jackson 默认不知道具体实现类：

```java
public class Zoo {
    public Animal animal;   // 接口：Jackson 默认不知具体类型 → 报错或退化 Map
}
```

### 2.2 @JsonTypeInfo + @JsonSubTypes + @JsonTypeName

```java
@JsonTypeInfo(
    use = JsonTypeInfo.Id.NAME,            // 用类型名区分
    include = JsonTypeInfo.As.PROPERTY,
    property = "type")
@JsonSubTypes({
    @JsonSubTypes.Type(value = Dog.class, name = "dog"),
    @JsonSubTypes.Type(value = Cat.class, name = "cat")
})
public abstract class Animal { }

@JsonTypeName("dog")  public class Dog extends Animal { public boolean barking; }
@JsonTypeName("cat")  public class Cat extends Animal { public boolean meows; }

// 序列化带 type 字段，反序列化按 type 恢复具体类
```

| `JsonTypeInfo.Id` | 说明 |
|---|---|
| `CLASS` | 用全限定类名 |
| `MINIMAL_CLASS` | 缩写类名 |
| `NAME` | 用 `@JsonSubTypes` 定义的短名（推荐） |
| `EXTERNAL_PROPERTY` | 类型信息在外部属性 |

**说明**：`use=Id.NAME` + `@JsonSubTypes` 白名单式最安全；带 `type:"dog"` 的 JSON 能正确反序列化为 `Dog`。

### 2.3 ⚠️ enableDefaultTyping（危险，禁止用）

```java
// 🚨 危险：全局开启「任意具体类型自动识别」
om.enableDefaultTyping();
```

**说明**：`enableDefaultTyping` 与 Gson/fastjson 类似地向 JSON 注入类型名并自动实例化，是**多态 RCE 的根源**——攻击者可指定任意类触发 gadget。**生产禁止用**全局 `enableDefaultTyping`。安全做法：用 `@JsonTypeInfo` + 显式 `@JsonSubTypes` 白名单（具体类），或后端维护白名单/具体类校验。

> 安全姿态：Jackson 默认**不**启用 `enableDefaultTyping`，是多态安全的天然基线；**只要不全局开它，多态 RCE 攻击面即关闭**，配 `@JsonSubTypes` 白名单更可控。注：CVE-2026-59889（@JsonView + @JsonUnwrapped 校验绕过）、CVE-2026-54515（大小写不敏感 @JsonIgnoreProperties 误用）等，是解析器与注解处理层的漏洞，**并非** DefaultTyping 触发；但保持默认不开 `enableDefaultTyping` 仍是反序列化安全基线。

## 3. 自定义序列化/反序列化（★）

### 3.1 JsonSerializer / JsonDeserializer

```java
public class MoneySerializer extends JsonSerializer<Money> {
    public void serialize(Money v, JsonGenerator g, SerializerProvider sp) throws IOException {
        g.writeString(v.getValue() + " " + v.getCurrency());
    }
}
public class MoneyDeserializer extends JsonDeserializer<Money> {
    public Money deserialize(JsonParser p, DeserializationContext c) throws IOException {
        String[] parts = p.getText().split(" ");
        return new Money(parts[0], parts[1]);
    }
}
```

### 3.2 注册：SimpleModule

```java
ObjectMapper om = new ObjectMapper();
SimpleModule m = new SimpleModule();
m.addSerializer(Money.class, new MoneySerializer());
m.addDeserializer(Money.class, new MoneyDeserializer());
om.registerModule(m);
```

**说明**：自定义转换分三步——写 `JsonSerializer`/`JsonDeserializer`（签名如上），`SimpleModule` 注册，`ObjectMapper.registerModule` 挂载。也可用注解式 `@JsonSerialize(using=)` / `@JsonDeserialize(using=)`：

```java
@JsonSerialize(using = MoneySerializer.class)
@JsonDeserialize(using = MoneyDeserializer.class)
public class Money { ... }
```

## 4. 日期时间处理（★）

### 4.1 JavaTimeModule（JDK8 time 必需）

```java
ObjectMapper om = new ObjectMapper();
om.registerModule(new JavaTimeModule());
// 需要 jsr310 模块坐标
// jackson-datatype-jsr310（Boot 默认已含）
```

依赖：官方推荐 **`jackson-datatype-jsr310`** 的 `JavaTimeModule`。

### 4.2 LocalDate / LocalDateTime

```java
public class Order {
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createdAt;
    private LocalDate date;
}
```

### 4.3 WRITE_DATES_AS_TIMESTAMPS

```java
om.registerModule(new JavaTimeModule());
om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS); // 默认 LocalDateTime 写数字数组/时间戳
```

**说明**：注册 `JavaTimeModule` 后，若不开 `WRITE_DATES_AS_TIMESTAMPS`，`LocalDateTime` 默认以**时间戳/数字数组**输出；`.disable(...)` 切回 ISO 字符串。Boot 默认 `Jackson2ObjectMapperBuilder` 已自动注册 JSR310 且关闭 timestamp。Java 8 time 迁移注意：`java.util.Date` 用 `setDateFormat`；**JSR310 必须注册模块**。

> 踩坑：#42 `@JsonFormat` 日期不生效常因没注册 JavaTimeModule，见 [99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 5. 属性与命名单

```java
ObjectMapper om = new ObjectMapper();
om.setPropertyNamingStrategy(
    PropertyNamingStrategies.SNAKE_CASE);   // 全局下划线

// 注解式
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class User { private String userName; }   // JSON: user_name
```

| 策略 | 作用 |
|---|---|
| `SNAKE_CASE` | `userName` → `user_name` |
| `KEBAB_CASE` | `userName` → `user-name` |
| `LOWER_CASE` | 全小写 |

**说明**：全局 `setPropertyNamingStrategy` 或局部 `@JsonNaming` 改名，前后端下划线 vs 驼峰对决靠它统一。

## 6. MixIn：为不可改类注入注解

对第三方/不可改类无法加注解，用 MixIn 类映射：

```java
// 只定义注解，不实现任何逻辑
abstract class UserMixIn {
    @JsonIgnore abstract String getPassword();
    @JsonProperty("user_name") abstract String getName();
}

// 挂载
om.addMixIn(User.class, UserMixIn.class);
```

**说明**：`addMixIn` 让 Jackson 把 MixIn 上的注解视为目标类注解，不改第三方类即可控制字段命名/忽略。可与自定义 serializers 结合（见踩坑 #8）。

## 7. 过滤/视图

### 7.1 @JsonView 动态字段

```java
public class Views { public static class Public {}; public static class Admin extends Public {} }

public class User {
    @JsonView(Views.Public.class) public String name;
    @JsonView(Views.Admin.class)  public String email;
}

// 序列化时指定视图
String publicJson = om.writerWithView(Views.Public.class).writeValueAsString(user); // 只有 name
String adminJson  = om.writerWithView(Views.Admin.class).writeValueAsString(user);  // name+email
```

**说明**：`@JsonView` 支持按场景输出不同字段集（公开只含 name，管理含 email）。

### 7.2 @JsonFilter

```java
@JsonFilter("dynamic")   // 目标类声明过滤器名
public class User { private String a,b; }

FilterProvider fp = new SimpleFilterProvider().addFilter("dynamic",
        SimpleBeanPropertyFilter.filterOutAllExcept("a"));
String json = om.writer(fp).writeValueAsString(user);   // 只输出 a
```

**说明**：`@JsonFilter` + `FilterProvider` 在**运行时**动态决定字段取舍，比固定 `@JsonIgnoreProperties` 灵活。

## 8. 常见坑

- **Mixin 与自定义冲突**：同名注解同时经由 MixIn 和类自身声明时可能冲突/覆盖，需明确优先级；MixIn 只补不重复。
- **多态安全**：`enableDefaultTyping` 全局开 = RCE 风险；多态一律走 `@JsonTypeInfo` + 显式 `@JsonSubTypes` 白名单；对接外部未知输入时校验类型。
- **日期不生效**：JSR310 未注册 `JavaTimeModule`。
- **自定义 Deserializer 无默认构造/不可变类**：可能需要 `JsonCreator` 或 Builder（Jackson 不支持无构造，可用 `@JsonCreator` 或 `setter`）。

```java
// 不可变类：@JsonCreator 工厂反序列化
public class Point {
    private final int x, y;
    @JsonCreator
    public Point(@JsonProperty("x") int x, @JsonProperty("y") int y) { this.x=x; this.y=y; }
}
```

**说明**：不可变类（final 字段、无 setter）用 `@JsonCreator` 标注带 `@JsonProperty` 的构造器，Jackson 据此构造，摆脱可变性限制。

## 小结

- 注解全家掌握 `@JsonProperty/@JsonIgnore/@JsonInclude/@JsonFormat/@JsonNaming/@JsonView/@JsonAny*` 即可覆盖大部分定制。
- 多态用 `@JsonTypeInfo` + `@JsonSubTypes` 白名单；**禁用全局 `enableDefaultTyping`**（多态 RCE 根源）。
- 自定义转换用 `JsonSerializer/Deserializer` + `SimpleModule`；日期需 `JavaTimeModule`。
- MixIn 处理第三方类；视图/过滤器做动态字段。
- 不可变类用 `@JsonCreator` 构造。

## 下一篇

[07-Jackson与SpringBoot集成详解](07-Jackson与SpringBoot集成详解.md)（全自动集成、spring.jackson.*、自定义 Bean、Jackson 3）。
