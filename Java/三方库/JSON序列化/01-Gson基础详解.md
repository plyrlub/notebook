---
tags:
  - Java
  - JSON
  - Gson
  - 序列化
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Gson 基础详解

## 📋 总纲

本篇讲 Gson 从零到精。读完你会：掌握 `Gson`/`GsonBuilder` 核心类、基础与泛型序列化（`TypeToken`）、字段控制（`@SerializedName`/`@Expose`）、自定义适配器、树模型与流式、版本化，以及与 Spring Boot 的最小集成。

> 前置：[00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)；相关踩坑：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 1. 概述与定位

- **出品**：Google。
- **机制**：反射驱动，遍历对象字段序列化。
- **依赖**：零外部依赖，轻量。
- **适用场景**：Android 移动端、轻量级服务、简单 POJO、需要极简 API 的项目。
- **性能**：中等（阿里 JMH 排序 Fastjson2 > Jackson > Gson），大数据量时劣于 Jackson/Fastjson2。

一句话定位：**API 极简、零依赖，够用就好**，适合 JSON 结构简单的轻项目。

## 2. 引入依赖

Gson 官方版本（Maven Central）：

Maven：

```xml
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.14.0</version>
</dependency>
```

Gradle：

```groovy
implementation 'com.google.code.gson:gson:2.14.0'
```

**代码说明**：仅一个坐标即可，无传递依赖，即「零外部依赖」。

## 3. 核心类 Gson 与 GsonBuilder

- `new Gson()`：默认实例，开箱即用。
- `GsonBuilder().create()`：链式配置后生成实例。
- **线程安全**：Gson 实例无状态、可复用，可安全全局共享（单例）。

```java
Gson gson = new Gson();
Gson pretty = new GsonBuilder().setPrettyPrinting().create();

// 复用单例
public class Json {
    public static final Gson G = new GsonBuilder().create();
}
```

**代码说明**：默认无配置实例用于常规转换；`setPrettyPrinting()` 生成美观输出实例。都无状态，适合做静态单例复用。

## 4. 基础序列化/反序列化

核心方法：

| 方法 | 说明 | 边界行为 |
|---|---|---|
| `toJson(Object)` | 对象→JSON 字符串 | null 字段默认忽略 |
| `toJson(Object, Type)` | 泛型对象→JSON | 需要显式类型 |
| `fromJson(String, Class<T>)` | JSON→对象（简单类型） | 泛型会丢类型 |
| `fromJson(String, Type)` | JSON→对象（带类型信息） | 泛型安全 |

```java
// 基本类型
String js = gson.toJson(42);          // "42"
int i = gson.fromJson("\"42\"", int.class);

// 简单对象
Gson gson = new Gson();
String json = gson.toJson(new User("bob", 18));       // {"name":"bob","age":18}
User u = gson.fromJson(json, User.class);

// 数组
int[] arr = gson.fromJson("[1,2,3]", int[].class);

// 简单集合（List<String> 可工作，因元素非泛型）
List<String> list = gson.fromJson("[\"a\",\"b\"]", new TypeToken<List<String>>(){}.getType());

// Map
Map<String,Object> map = gson.fromJson("{\"k\":1}", new TypeToken<Map<String,Object>>(){}.getType());
```

**代码说明**：简单类型与对象直接用 `.class` 即可；只要目标类型内嵌泛型（`List<User>` 之类），就必须用 `TypeToken`（见下节）。`int.class` 需注意 `fromJson` 会把 JSON 数字解析进 int。

> 📌 踩坑：`fromJson(json, new ArrayList<String>().getClass())` 会得到裸 `List`，元素变 `Double`。见踩坑 [99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 5. 泛型与 TypeToken（★重点）

**泛型擦除原理**：Java 中 `List<User>` 的在字节码里被擦除为 `List`。`userList.getClass()` 返回 `ArrayList`，拿不到 `User`；`fromJson(json, list.getClass())` 因缺类型信息，只能反序列化成 `List<LinkedHashMap>`。

`TypeToken<T>` 通过匿名内部类捕获带类型参数的超类，运行时保留类型信息：

```java
// 错误：丢类型
List<User> bad = gson.fromJson(json, new ArrayList<User>().getClass());

// 正确：TypeToken 保留泛型
Type listType = new TypeToken<List<User>>(){}.getType();
List<User> users = gson.fromJson(json, listType);

// 新版本（2.14 可直接传 token 对象）
List<User> users2 = gson.fromJson(json, new TypeToken<List<User>>(){});
```

**代码说明**：前一种写法事件是 `ArrayList` 类对象，丢失 `User`；`new TypeToken<List<User>>(){}.getType()` 生成的匿名子类天然携带类型参数，Gson 据此反序列化。2.14 支持 `fromJson(json, TypeToken)` 直接传。

## 6. 字段控制（★重点）

### 6.1 transient / static 默认排除

```java
class User {
    String name;
    transient String sessionToken;   // 默认被忽略
    static String VERSION = "1.0";    // 默认被忽略
}
// 输出：{"name":"..."}，sessionToken 与 VERSION 不序列化
```

**代码说明**：Gson 默认排除 `transient` 与 `static` 字段，是隐私/冗余字段的轻量手段。

### 6.2 @SerializedName

改名 + 把非法 Java 标识符映射到合法 JSON 键名；重名冲突抛 `RuntimeException`：

```java
public class User {
    @SerializedName("user_name")  String name;  // JSON 输出 user_name
}

class Conflict {
    @SerializedName("a") String x;
    @SerializedName("a") String y;  // 同名冲突 → RuntimeException
}
```

**代码说明**：`@SerializedName("user_name")` 让字段序列化/反序列化都叫 `user_name`；同对象两个字段绑同一 JSON 名会直接抛异常。

### 6.3 @Expose + excludeFieldsWithoutExposeAnnotation

默认 `@Expose` 不生效，需开 `excludeFieldsWithoutExposeAnnotation()` 才按注解过滤；两个属性控制序列化/反序列化：`serialize` 与 `deserialize`，默认都是 true：

```java
public class User {
    @Expose                 String name;    // 序列+反序都出现（默认两 true）
    @Expose(serialize=false) String id;     // 只反序列化，序列化省略
    String password;                        // 未标 @Expose → 若开过滤则忽略
}

Gson g = new GsonBuilder().excludeFieldsWithoutExposeAnnotation().create();
```

**说明**：开 `excludeFieldsWithoutExposeAnnotation()` 后，只有标 `@Expose` 的字段参与；可用 `serialize`/`deserialize` 单独开关方向（如只输出 id、不回显 password）。

### 6.4 FieldNamingPolicy

自动转换命名策略：

```java
Gson g = new GsonBuilder()
        .setFieldNamingPolicy(FieldNamingPolicy.UPPER_CAMEL_CASE)
        .create();
// user_name → 无效于此策略；对 userName 输出 UserName
```

| 策略 | 例子 |
|---|---|
| `UPPER_CAMEL_CASE` | `userName` → `UserName` |
| `LOWER_CASE_WITH_UNDERSCORES` | `userName` → `user_name` |
| `LOWER_CASE_WITH_DASHES` | `userName` → `user-name` |

### 6.5 ExclusionStrategy 自定义

精细排除，`shouldSkipClass`(按类)/`shouldSkipField`(按字段)：

```java
Gson g = new GsonBuilder()
    .addSerializationExclusionStrategy(new ExclusionStrategy() {
        public boolean shouldSkipField(FieldAttributes f) {
            return f.getName().equals("secret") || f.getAnnotation(Sensitive.class) != null;
        }
        public boolean shouldSkipClass(Class<?> clazz) {
            return clazz == Password.class;
        }
    }).create();
```

**说明**：比 `@Expose` 更灵活，可按字段名、注解、类类型动态排除；`@Sensitive` 为你自定义注解。

## 7. 自定义序列化/反序列化（★重点）

### 7.1 JsonSerializer / JsonDeserializer

```java
public class UserSerializer implements JsonSerializer<User> {
    public JsonElement serialize(User src, Type t, JsonSerializationContext c) {
        JsonObject o = new JsonObject();
        o.addProperty("fullName", src.getName() + " " + src.getAge());
        return o;
    }
}
public class UserDeserializer implements JsonDeserializer<User> {
    public User deserialize(JsonElement el, Type t, JsonDeserializationContext c) {
        JsonObject o = el.getAsJsonObject();
        User u = new User();
        u.setName(o.get("fullName").getAsString().split(" ")[0]);
        return u;
    }
}
// 注册
Gson g = new GsonBuilder()
    .registerTypeAdapter(User.class, new UserSerializer())
    .registerTypeAdapter(User.class, new UserDeserializer())
    .create();
```

**说明**：`JsonSerializer<T>`/`JsonDeserializer<T>` 签名如上；`registerTypeAdapter` 可各自注册序列化/反序列化器。适合字段映射、第三方不可改类的自定义转换。

### 7.2 InstanceCreator（无无参构造 / 库类 / inner class）

反序列化需要无参构造，否则报 `cannot invoke no-arg constructor`；可用 `InstanceCreator<T>` 强制实例化：

```java
class MyLib { private MyLib(int x) {} }        // 无无参构造
Gson g = new GsonBuilder()
    .registerTypeAdapter(MyLib.class, new InstanceCreator<MyLib>() {
        public MyLib createInstance(Type t) { return new MyLib(0); }
    }).create();
```

**说明**：`InstanceCreator` 为 Gson 提供「如何先造出空对象」的能力，库类/私有构造/inner class 场景常用。

### 7.3 @JsonAdapter（注解式，Gson 2.6+）

在字段/类上直接声明适配器，免去手动 register：

```java
@JsonAdapter(UserAdapter.class)
public class User { ... }
// 等价于 registerTypeAdapter(User.class, new UserAdapter())
```

**说明**：`@JsonAdapter` 是声明式替代 `registerTypeAdapter`，类/字段上声明即生效，依赖注入友好。

### 7.4 适配器共享状态注意

适配器需无状态；若要共享状态，三策略：`static` 字段 / 外层类持有 / `ThreadLocal`：

```java
public class SharedAdapter implements JsonSerializer<X> {
    private static final ThreadLocal<Map<String,Object>> CTX = new ThreadLocal<>();
    public JsonElement serialize(...) { ... CTX.get() ... }
}
```

**说明**：Gson 实例可能被多线程复用，适配器内可变成员有并发风险；用 `static`/外层类/`ThreadLocal` 隔离。

## 8. Null 与输出格式

- **默认 null 字段被忽略**（不输出）；`serializeNulls()` 后输出 `"field":null`。
- `setPrettyPrinting()` 美观多行 vs 默认紧凑单行。
- **collection/list 里的 null 元素仍输出** `null`，不受 serializeNulls 影响。

```java
class Box { String a; String b; }

new Gson().toJson(new Box());            // {}
new GsonBuilder().serializeNulls().create().toJson(new Box()); // {"a":null,"b":null}

new GsonBuilder().setPrettyPrinting().create().toJson(x);
// {
//   "a": "1"
// }
```

**说明**：对象字段为 null 时，`toJson` 默认直接丢键；`serializeNulls()` 保留。数组/集合内的 null 元素始终保留。美观输出适合调试与展示。

## 9. 版本化 @Since / setVersion（Gson 特色）

在字段/类上 `@Since(n)`，通过 `setVersion(n)` 控制版本内输出；无 `@Since` 则全版本输出：

```java
public class App {
    @Since(1.0) String name;    // 任意 >= 1.0 都输出
    @Since(2.0) String version2;// 仅版本 >= 2.0 输出
}
Gson g1 = new GsonBuilder().setVersion(1.0).create(); // 只输出 name
Gson g2 = new GsonBuilder().setVersion(2.0).create(); // name + version2
```

**说明**：`setVersion(n)` 时，字段 `@Since(n)`（n≤当前版本）才输出；未标 `@Since` 的总是输出。适合接口多版本兼容场景，是 Gson 独有特性。

## 10. 树模型与流式

### 10.1 树模型：JsonElement 系列

`JsonElement`（根）/`JsonObject`/`JsonArray`/`JsonPrimitive`（原始值）/`JsonNull`，配合 `JsonParser`：

```java
JsonElement el = JsonParser.parseString(json);
JsonObject obj = el.getAsJsonObject();
String name = obj.get("name").getAsString();
JsonArray arr = obj.getAsJsonArray("tags");
Double v = obj.get("age").getAsJsonPrimitive().getAsDouble();
```

**说明**：树模型对应「先整体读入，再按路径取」，无需 POJO；`getAsXxx()` 强转，取错会抛 `NumberFormatException`/`IllegalStateException`（用 `has()`/`isJsonNull()` 前置判断更稳）。

### 10.2 流式：JsonReader / JsonWriter

**轻内存、可组合**，适合大 JSON 流：

```java
try (JsonReader r = new JsonReader(new StringReader(json))) {
    String name = null;
    r.beginObject();
    while (r.hasNext()) {
        String key = r.nextName();
        if (key.equals("name")) name = r.nextString();
        else r.skipValue();
    }
    r.endObject();
    System.out.println(name);
}
```

**说明**：`JsonReader` 逐 token 读，不整体入内存；`nextXxx()` 取值、`skipValue()` 跳过无关分支。适合处理大文件/长流，可与树模型按需组合。

## 11. 与 Spring Boot 集成（最小必要）

依赖层面：

```xml
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
</dependency>
<!-- 引入 starter-web 时排除默认的 json(Jackson) -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-json</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

配置（application.yml）：

```yaml
spring:
  gson:
    pretty-printing: true
    serialize-nulls: false
```

机制说明：

- Boot 检测到 classpath 有 Gson 而**无 Jackson**时，自动配置（`@ConditionalOnClass`）注册 `GsonHttpMessageConverter`，并把 `spring.gson.*` 映射到 `GsonBuilder`。
- 手动覆盖：提供自定义 `Gson` Bean（见下），Boot 优先使用：

```java
@Bean
Gson gson() {
    return new GsonBuilder()
        .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
        .create();
}
```

**说明**：Boot 对 Gson 有官方自动配置但**配置项远少于 Jackson**；**WebFlux 不友好**（首选 Jackson）。手动 `Gson` Bean 会完全接管 `GsonHttpMessageConverter` 的实例。

> ⚠️ 踩坑：Boot 用 Gson 忘排除 Jackson 会双转换器冲突，见踩坑 [99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 12. 常见易错点

- **inner class 不能反序列化**：非 static 内部类无默认构造访问路径 → 必须 `static`。
- **循环引用**：互相持有对方，默认**无限递归** → `StackOverflowError`；需 `@Expose`/排除或 `ExclusionStrategy` 打破环。
- **Map key 用 toString 坑**：默认对非 String key 调 `toString()`；`enableComplexMapKeySerialization()` 可用（约束多）。
- **null 丢失**：默认 null 字段不输出，需 `serializeNulls()`。
- **大 JSON**：全部对象方式内存占用高，用流式 `JsonReader`/`JsonWriter` 逐段处理。

```java
// 循环引用示例（会触发栈溢出）
class A { B b; }
class B { A a; }
new Gson().toJson(new A());  // -> StackOverflowError
```

## 小结

- Gson 零依赖、极简 API，适合轻量/PAndroid/简单 POJO。
- 泛型反序列化必用 `TypeToken`；字段控制用 `transient`/`@SerializedName`/`@Expose`/`ExclusionStrategy`。
- 自定义用 `JsonSerializer`/`JsonDeserializer` + `registerTypeAdapter` 或 `@JsonAdapter`。
- null 默认忽略、需 `serializeNulls()`；`@Since`+`setVersion` 是 Gson 特有多版本能力。
- Boot 集成有官方自动配置但要排除 Jackson；WebFlux 不友好。

## 下一篇

下一篇：[02-Fastjson2基础详解](02-Fastjson2基础详解.md)（性能极致、Feature 默认全关、JSONB）。
