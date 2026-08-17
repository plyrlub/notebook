---
tags:
  - Java
  - JSON
  - Jackson
  - ObjectMapper
  - 序列化
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Jackson 核心与 ObjectMapper 详解

## 📋 总纲

本篇讲 Jackson 核心基础——它是 Spring Boot 默认库。读完你会：掌握三大模块关系、`ObjectMapper` 的读写/配置、`JsonNode` 树模型、泛型 `TypeReference`、流式 API 与入门注解、核心 Feature 配置。

> 前置：[00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)；注解与高级定制见 [06-Jackson注解与高级定制详解](06-Jackson注解与高级定制详解.md)；Boot 集成见 [07-Jackson与SpringBoot集成详解](07-Jackson与SpringBoot集成详解.md)；踩坑：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 1. 概述

- **出品**：FasterXML。
- **定位**：Spring Boot 默认、生态最全、模块化程度高。
- **三大核心模块**：
  - `jackson-core`：底层流式 API（`JsonParser`/`JsonGenerator`）。
  - `jackson-annotations`：注解（`@JsonProperty`/`@JsonIgnore` 等）。
  - `jackson-databind`：对象绑定，`ObjectMapper` 所在。
- **核心类**：`ObjectMapper`，一切对象↔JSON 的入口。

依赖关系：`jackson-databind` 依赖 `jackson-core` + `jackson-annotations`，引它即全家。

## 2. 引入依赖

三模块关系（`jackson-databind` 传递依赖另两个）：

```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.22.1</version>
</dependency>
```

**说明**：`jackson-databind` 传递引入 `jackson-core` 与 `jackson-annotations`。2.22.1 为最新版本；**仅在 Spring Boot 中，版本由 `spring-boot-dependencies` BOM 管理，不需手写 version**。

```xml
<!-- Boot 项目无需写版本 -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

## 3. ObjectMapper 核心（★）

### 3.1 读写方法表

| 方法 | 说明 |
|---|---|
| `writeValueAsString(obj)` | 对象→JSON 字符串 |
| `writeValue(writer/OutputStream, obj)` | 对象→流 |
| `readValue(String, Class)` | 字符串→对象（简单类） |
| `readValue(String, TypeReference<T>)` | 字符串→泛型对象 |
| `readTree(String)` | 字符串→JsonNode |
| `updateValue(pojo, JSON)` | 用 JSON 部分更新已有对象 |

```java
ObjectMapper om = new ObjectMapper();

String json = om.writeValueAsString(user);       // 写
User u = om.readValue(json, User.class);         // 读（简单类）
JsonNode node = om.readTree(json);               // 树
// 部分更新
User target = new User();
om.updateValue(target, "{\"age\":20}");          // target.age = 20
```

### 3.2 流程与线程安全

- **序列化流程**：Bean→`JsonSerializer`（递归解析字段）→`JsonGenerator`→文本。
- **反序列化流程**：文本→`JsonParser`→`JsonDeserializer`（构造 Bean 填字段）→Bean。
- **线程安全**：`ObjectMapper` **无共享可变状态、可全局复用**（配置一次性设置后并发只读安全）。
- ⚠️ 注意：若用**自定义 JAXB 注解/部分 MixIn** 或每次动态改配置（`configure`/setter）会引入非线程安全，建议**配置完成后冻结复用**；官方建议用不可变 Builder 一次性建。

```java
// 推荐：全局单例（配置完成后不可变）
public static final ObjectMapper OM = new ObjectMapper()
        .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
```

**说明**：`ObjectMapper` 配置好即为无状态只读单例，多线程安全共享，是业界通行做法。**不要**在请求内反复 `setXxx` 改配置。

## 4. 创建与配置 ObjectMapper

```java
ObjectMapper om = new ObjectMapper();

// 序列化时忽略 null 字段
om.setSerializationInclusion(JsonInclude.Include.NON_NULL);

// 反序列化：未知字段不报错
om.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

// 深拷贝（改配置不影响原实例）
ObjectMapper copy = om.copy();
copy.configure(SerializationFeature.INDENT_OUTPUT, true);

// 日期格式与时区
om.setDateFormat(new SimpleDateFormat("yyyy-MM-dd"));
om.setTimeZone(TimeZone.getTimeZone("Asia/Shanghai"));
```

| 方法/配置 | 说明 |
|---|---|
| `setSerializationInclusion` | 顶层 null 忽略策略 |
| `configure(Feature, boolean)` | 开关某 Feature |
| `copy()` | 深拷贝独立实例 |
| `setDateFormat` / `setTimeZone` | 全局日期格式/时区 |

**说明**：`copy()` 返回互不影响的新实例，适合"基础实例 + 派生配置"模式。注意 `setDateFormat` 只影响 `java.util.Date`；**LocalDate/LocalDateTime 需注册 `JavaTimeModule`**（见 06 篇）。

## 5. JsonNode 树模型（★）

### 5.1 读取与导航

```java
JsonNode root = om.readTree(json);

String name = root.get("name").asText();
// path：缺子节点返回 NullNode（不抛）
JsonNode miss = root.path("notExist").asText(null);
// has：判断存在
if (root.has("age")) root.get("age").asInt();
// 类型判断
root.isTextual(); root.isObject(); root.isArray();
```

| 方法 | 说明 |
|---|---|
| `get(key)` | 取节点，缺返回 null |
| `path(key)` | 取节点，缺返回 NullNode 不抛 |
| `has(key)` | 是否有该字段 |
| `asText()`/`asInt()`/`asDouble()` | 转基本类型（缺转默认值） |

**说明**：`get` 缺值返 null 需判空；`path` 优雅回退；树模型适合**试探性**取数据/动态结构，不用固定 POJO。

### 5.2 数组与嵌套

```java
JsonNode arr = root.get("items");
for (JsonNode item : arr) {
    System.out.println(item.get("name").asText());
}
// ArrayNode/ObjectNode 可变增改
((ObjectNode) root).put("extra", "value");
ArrayNode newArr = ((ArrayNode) root).putArray("tags").add("a").add("b");
```

**说明**：`ArrayNode`/`ObjectNode` 是可变子类，可用 `put`/`putArray`/`putObject` 操作构建/修改树。

### 5.3 树 → JavaBean

```java
User u = om.treeToValue(root, User.class);
JsonNode nodeBack = om.valueToTree(u);
```

**说明**：`treeToValue` 树→Bean，`valueToTree` Bean→树，实现树与 POJO 互转。

## 6. 泛型 TypeReference（★）

**类型擦除**导致 `readValue(json, new ArrayList<User>().getClass())` 拿不到 `User`（变成 `List`）。用 `TypeReference`：

```java
List<User> users = om.readValue(json,
    new TypeReference<List<User>>() {});

Map<String, List<User>> map = om.readValue(json,
    new TypeReference<Map<String, List<User>>>() {});

// 嵌套泛型
Result<Page<User>> res = om.readValue(json,
    new TypeReference<Result<Page<User>>>() {});
```

**说明**：`new TypeReference<...>(){}` 匿名子类捕获持有泛型信息；`List<User>`/`Map<String,List<User>>`/嵌套 `Result<Page<User>>` 都能正确解析。**不能直接用 `.class`**（会丢泛型）。

## 7. 流式 API

底层 `JsonParser`/`JsonGenerator` 逐 token、轻内存：

```java
// 读
JsonParser p = om.getFactory().createParser(json);
while (p.nextToken() != null) {
    if (p.getCurrentToken() == JsonToken.FIELD_NAME
            && "name".equals(p.getCurrentName())) {
        p.nextToken();                    // 移到值
        System.out.println(p.getText());  // name 的值
    }
}
p.close();

// 写
JsonGenerator g = om.getFactory().createGenerator(System.out);
g.writeStartObject();
g.writeStringField("name", "bob");
g.writeNumberField("age", 18);
g.writeEndObject();
g.close();
```

**说明**：`createParser`/`createGenerator` 逐字段处理，不整体入内存，适合超大 JSON。可与树模型组合（先流式找某字段，再 `readTree` 局部）。

## 8. 基础注解（入门）

`@JsonProperty`（改名/必填）与 `@JsonIgnore`（忽略）先讲，详解见高级篇：

```java
public class User {
    @JsonProperty("user_name")
    private String name;

    @JsonIgnore
    private String secret;

    @JsonProperty(required = true)   // 反序列化必填，缺失抛异常
    private Long id;
}
```

**说明**：`@JsonProperty("user_name")` 映射键名；`@JsonIgnore` 忽略字段（不序列化/反序列化）；`required=true` 校验必填。完整注解全家在 [06-Jackson注解与高级定制详解](06-Jackson注解与高级定制详解.md)。

## 9. 核心配置项表

### 9.1 SerializationFeature（序列化）

| Feature | 默认 | 作用 |
|---|---|---|
| `INDENT_OUTPUT` | off | 美化缩进 |
| `WRITE_DATES_AS_TIMESTAMPS` | on | 日期写为时间戳（注册 JavaTimeModule 后需留意） |
| `FAIL_ON_EMPTY_BEANS` | on | 空 Bean 抛异常，可关 |
| `WRITE_NULL_MAP_VALUES` | on | Map 的 null 值写出为 null |

### 9.2 DeserializationFeature（反序列化）

| Feature | 默认 | 作用 |
|---|---|---|
| `FAIL_ON_UNKNOWN_PROPERTIES` | on | 未知字段抛异常（对接外部常需关掉） |
| `FAIL_ON_NULL_FOR_PRIMITIVES` | on | 原始类型收到 null 抛异常 |
| `ACCEPT_SINGLE_VALUE_AS_ARRAY` | off | 单值当单元素数组 |
| `USE_BIG_DECIMAL_FOR_FLOATS` | off | 浮点用 BigDecimal |

```java
// 常用组合
ObjectMapper om = new ObjectMapper()
    .configure(SerializationFeature.INDENT_OUTPUT, true)
    .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
```

**说明**：Boot 默认 `FAIL_ON_UNKNOWN_PROPERTIES` 为 **off**（配合全局字段可容忍新增）；独立用 ObjectMapper 时默认 on 易报错，按需关。

## 小结

- 三大模块 core / annotations / databind；`ObjectMapper` 是其入口。
- 读写用 `writeValue`/`readValue`/`readTree`；泛型必用 `TypeReference`。
- `JsonNode` 树模型支持 `get`/`path`/`has` 探勘与 `treeToValue` 转 Bean。
- 流式 API 轻内存应对大 JSON；配置一次性冻结保证线程安全。

## 下一篇

[06-Jackson注解与高级定制详解](06-Jackson注解与高级定制详解.md)（注解全家、多态、自定义序列化、日期处理）。
