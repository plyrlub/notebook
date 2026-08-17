---
tags:
  - Java
  - JSON
  - Fastjson2
  - 序列化
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Fastjson2 基础详解

## 📋 总纲

本篇讲 Fastjson2 日常 JSON 使用核心：包结构、静态类 `JSON`、树模型 `JSONObject`/`JSONArray`、JavaBean 序列化、`@JSONField`/`@JSONType` 注解、Feature 配置、过滤器、自定义 Writer/Reader，以及 Spring Boot 集成。

> 前置：[00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)；安全先行见 [04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)；二进制与 JSONPath 见 [03-Fastjson2高级·JSONB与JSONPath详解](03-Fastjson2高级·JSONB与JSONPath详解.md)；相关踩坑：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 1. 概述与定位

- **来历**：Fastjson 2.0 升级换代，API 重构，性能极致（阿里官方 JMH 基准）。
- **包名/坐标变化**：`com.alibaba.fastjson` → `com.alibaba.fastjson2`；`groupId` 变化。
- **特点**：静态方法 + 树模型 + JavaBean 三种方式；Feature 默认全关更安全；独有 JSONB 二进制。
- **定位**：性能优先，适合高吞吐内部调用、二进制通信、JSONB 缓存。

> ⚠️ 注意：Fastjson2 不等于「安全升级版 Fastjson」——它换掉了 API 与默认行为，AutoType 默认关闭更安全，但一旦主动开启 autoType 有未修复 RCE，见 04 篇。

## 2. 引入依赖

核心坐标：

```xml
<dependency>
    <groupId>com.alibaba.fastjson2</groupId>
    <artifactId>fastjson2</artifactId>
    <version>2.0.64</version>
</dependency>
```

可选模块：

| 模块 | 用途 |
|---|---|
| `com.alibaba:fastjson:2.0.64` | v1 兼容模块（`com.alibaba.fastjson` 包），**不能 100% 兼容须测试** |
| `fastjson2-kotlin` | Kotlin 支持 |
| `fastjson2-extension-spring5` / `-spring6` | Spring Boot/WebMvc 集成 |

Gradle：

```groovy
implementation 'com.alibaba.fastjson2:fastjson2:2.0.64'
```

**代码说明**：只用 `fastjson2` 即可获得 `com.alibaba.fastjson2.*` 全部能力。v1 兼容模块用于旧代码迁移，但不保证行为一致。

## 3. JSON 静态类快速上手

`JSON` 是所有操作的静态入口：

```java
String text = JSON.toJSONString(user);          // 对象 → 字符串
User u = JSON.parseObject(text, User.class);    // JSON → 对象
List<User> list = JSON.parseArray(text, User.class); // JSON 数组 → List
byte[] bytes = JSON.toJSONBytes(user);          // 对象 → JSON 字节（非 JSONB）
```

| 方法 | 说明 |
|---|---|
| `JSON.parseObject(text, Class)` | 字符串→对象 |
| `JSON.parseArray(text, Class)` | 字符串→List |
| `JSON.toJSONString(obj)` | 对象→字符串 |
| `JSON.toJSONBytes(obj)` | 对象→JSON 字节数组 |

**说明**：`JSON` 静态类最常用；`toJSONBytes` 是 JSON 文本字节（不是 JSONB，JSONB 用 `JSONB.toBytes`，见 03 篇）。泛型集合用 `parseObject` + `TypeReference`。

## 4. JSONObject 与 JSONArray（树模型）

动态取值，无需 POJO：

```java
JSONObject obj = JSON.parseObject(json);
int id = obj.getIntValue("id");              // 原生 int
String name = obj.getString("name");
User u = obj.getObject("user", User.class);  // 子对象转 JavaBean
List<Item> items = obj.getList("items", Item.class); // 子数组转 List

JSONArray arr = JSON.parseArray(jsonArray);
String first = arr.getString(0);
User u0 = arr.getObject(0, User.class);
```

| 方法 | 说明 |
|---|---|
| `getIntValue`/`getLongValue`/`getString` | 基本类型快速取值 |
| `getInteger`/`getLong` | 包装类型（可为 null） |
| `getObject(key, Class)` | 子对象/泛型转 JavaBean |
| `getList(key, Class)` | 子数组转 List |
| `toJavaObject(Class)` / `toJavaList(Class)` | 整棵树转 JavaBean/List |

**说明**：`getXxx` 缺键时 `getString` 返回 null，`getIntValue` 返回 0——注意区分（缺失 vs 真实 0）。`JSONObject`/`JSONArray` 本质是可嵌套 Map/List 树。

## 5. 序列化为 JavaBean + 泛型

```java
// 对象 ↔ JavaBean
User u = obj.toJavaObject(User.class);

// 泛型
List<User> us = JSON.parseObject(text, new TypeReference<List<User>>() {});
```

**说明**：与 Jackson `TypeReference`、Gson `TypeToken` 同理，泛型集合需 `new TypeReference<List<User>>(){}` 保留泛型信息，否则得到 List<JSONObject>。

## 6. 注解（★重点）

### 6.1 @JSONField

字段/方法级：

```java
public class User {
    @JSONField(name = "user_name")   String name;   // 改名
    @JSONField(format = "yyyy-MM-dd") LocalDate birth; // 日期格式
    @JSONField(serialize = false)    String secret;  // 不序列化
    @JSONField(deserialize = false)  String readOnly;// 不反序列化
    @JSONField(ordinal = 1)          String first;   // 输出顺序
    @JSONField(serializeUsing = MyWriter.class) Object custom; // 自定义 writer
}
```

| `@JSONField` 属性 | 说明 |
|---|---|
| `name` | JSON 键名映射 |
| `format` | 日期/数字格式 |
| `serialize`/`deserialize` | 是否序列化/反序列化 |
| `ordinal` | 输出字段顺序（小→大） |
| `serializeUsing`/`deserializeUsing` | 自定义 Writer/Reader |

### 6.2 @JSONType（类级）

```java
@JSONType(ignores = {"password"})
public class User { ... }
```

**说明**：类级聚合配置（忽略字段、命名策略等）。

### 6.3 @JSONCreator（构造器/工厂）

用于无默认构造或需定制入参：

```java
public class Point {
    private int x, y;
    @JSONCreator
    public Point(@JSONField(name="x") int x, @JSONField(name="y") int y) {
        this.x = x; this.y = y;
    }
}
```

**说明**：`@JSONCreator` 标注构造器或静态工厂，参数用 `@JSONField(name=...)` 与 JSON 键绑定，解决无无参构造场景。

## 7. Feature 配置（★重点）

Fastjson2 用 **`JSONWriter.Feature` / `JSONReader.Feature`** 配置，**默认全关**（与 1.x 全部默认开形成鲜明对比）。用 `JSON.toJSONString(obj, feature...)` 或 `JSON.parseObject(text, type, feature...)` 传参：

```java
// 序列化 Feature
String json = JSON.toJSONString(user,
    JSONWriter.Feature.WriteNulls,       // 输出 null 字段
    JSONWriter.Feature.PrettyFormat);    // 美化缩进

// 反序列化 Feature
User u = JSON.parseObject(text, User.class,
    JSONReader.Feature.SupportSmartMatch); // 允许 snake_case 匹配驼峰
```

| 常用 Feature | 方向 | 说明 |
|---|---|---|
| `WriteNulls` | Writer | 输出 null 字段（默认不输出） |
| `PrettyFormat` | Writer | 美化缩进 |
| `WriteClassName` | Writer | 输出类型信息（配 autoType，危险） |
| `SupportSmartMatch` | Reader | camelCase/snake_case 智能匹配 |
| `SupportAutoType` | Reader | 自动识别类型（**危险，见 04**） |
| `IgnoreNoneSerializable` | Writer | 忽略未标记字段 |

> ⚠️ 与 1.x 对比：1.x 默认开启智能匹配/循环引用检测/AutoType 白名单，2.x **所有 Feature 默认全关**，更安全但行为需显式开启。见 04 篇迁移表。

## 8. 过滤器

在序列化时按需改写/过滤字段：

```java
// 值过滤器：改写特定字段值
String json = JSON.toJSONString(user, new ValueFilter() {
    public Object process(Object object, String name, Object value) {
        return "name".equals(name) ? String.valueOf(value).toUpperCase() : value;
    }
});
```

| 过滤器 | 作用 |
|---|---|
| `ValueFilter` | 改写字段值 |
| `NameFilter` | 改写字段名 |
| `PropertyFilter` | 按条件保留/剔除字段 |
| `BeforeFilter` / `AfterFilter` | 序列化前/后注入字段 |
| `LabelFilter` | `@JSONField(label=)` 按标签过滤 |

**说明**：过滤器在序列化阶段对字段名/值做变换，适合脱敏、改键、条件包含等；`LabelFilter` 结合 `@JSONField(label="xxx")` 按标签动态取舍字段。

## 9. 自定义序列化/反序列化

用 `ObjectWriter`/`ObjectReader` 自定义对象的整体读写：

```java
class UserWriter implements ObjectWriter {
    public void write(JSONWriter jsonWriter, Object object, Object fieldName,
                      Type fieldType, long features) {
        User u = (User) object;
        jsonWriter.writeStartObject();
        jsonWriter.writeName("fullName");
        jsonWriter.writeString(u.getName() + "_" + u.getAge());
        jsonWriter.writeEndObject();
    }
}
// 注册
JSON.register(User.class, new UserWriter());
```

**说明**：实现 `ObjectWriter`（写）或 `ObjectReader`（读）接口，`JSON.register(Type, Writer)` 全局注册；适合复杂类型/第三方类的序列化控制。日常用 `@JSONField(serializeUsing=)` 更简单。

## 10. JSONB 概览

- **定义**：Fastjson2 **独有二进制 JSON**，体积更小、读写更快。
- **关系**：`JSONB.toBytes`/`JSONB.parseObject` 是独立 API，与 JSON 文本互转。
- 详见 [03-Fastjson2高级·JSONB与JSONPath详解](03-Fastjson2高级·JSONB与JSONPath详解.md)。

## 11. JSONPath 概览

- **定义**：不完全反序列化、按路径提取字段，SQL:2016 语法。
- **用法**：`JSONPath.of("$.id").extract(reader)` 等，性能高可复用。
- 详见 [03-Fastjson2高级·JSONB与JSONPath详解](03-Fastjson2高级·JSONB与JSONPath详解.md)。

## 12. Spring Boot 集成（最小必要）

依赖 + 排除 Jackson + 注册转换器：

```xml
<dependency>
    <groupId>com.alibaba.fastjson2</groupId>
    <artifactId>fastjson2-extension-spring6</artifactId>
    <version>2.0.64</version>
</dependency>
```

```yaml
spring:
  mvc:
    message-converters-strategy: fbc   # 或使用 WebMvcConfigurer 手动注册
```

```java
@Configuration
public class FastJsonConfig {
    @Bean
    public HttpMessageConverter<?> fastJsonMessage() {
        FastJsonHttpMessageConverter c = new FastJsonHttpMessageConverter();
        c.setFastJsonConfig(new FastJsonConfig());
        return c;
    }
}
```

<-- 说明：`FastJsonHttpMessageConverter` 常以无参构造 + `setFastJsonConfig` 配置；实际构造签名/注册方式随扩展版本演进，**具体到 2.0.64 请据官方文档复核** -->

**说明**：**⛔ 非官方自动配置**——Boot 官方只声明 Jackson/Gson 为默认消息转换器；Fastjson2 需第三方 `fastjson2-extension-spring5/6` 扩展并自行 `FastJsonHttpMessageConverter`，还需从 `spring-boot-starter-web` 里排除 Jackson，否则双转换器冲突（见踩坑 [99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)）。

## 13. 安全提醒

> ⚠️ 一句话：**Fastjson2 默认全关 autoType 是安全的**；但**显式开启 `SupportAutoType` 有未修复 RCE（2026-07 长亭披露，issue #7702，PR #7695 未合并）**。生产非必要不开启 autoType，公网场景禁用。详见 [04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)。

## 小结

- Fastjson2 通过 `JSON` 静态类 + `JSONObject`/`JSONArray` 树模型 + JavaBean 三种方式使用。
- `@JSONField` 控制改名/格式/序列化开关，`@JSONCreator` 解决无默认构造。
- **Feature 默认全关**是 2.x 相对 1.x 的最大安全改进，需按需显式开启。
- 过滤器与 `ObjectWriter`/`ObjectReader` 提供字段级/对象级定制。
- Boot 集成为第三方扩展、非官方，须排除 Jackson 并自行注册转换器。

## 下一篇

- 进阶：[03-Fastjson2高级·JSONB与JSONPath详解](03-Fastjson2高级·JSONB与JSONPath详解.md)
- 安全：[04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)
