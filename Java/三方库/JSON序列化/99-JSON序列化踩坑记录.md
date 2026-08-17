---
tags:
  - Java
  - JSON
  - 踩坑
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# JSON 序列化踩坑记录

## 📋 总纲

本库收录 JSON 序列化/反序列化高频采坑，结构统一为 **现象 → 原因 → 解决方案**，编号 `#分类.序号`：

- `#1 配置` / `#2 性能` / `#3 安全` / `#4 序列化行为` / `#5 泛型` / `#6 Boot 集成`

各详解篇文末「常见踩坑」小节引用 `#x.x` 跳转到本库。新坑先入库再被引用。

> 安全相关条目调研时间：2026-08-14（联网已查证）。

## #1 配置

### 1.1 Boot 用 Gson/Fastjson2 忘排除 Jackson 冲突

- **现象**：项目引入 Gson/Fastjson2 后，接口返回仍被 Jackson 序列化，或同时出现两个转换器报错/优先级混乱。
- **原因**：`spring-boot-starter-web` 自带 `spring-boot-starter-json`（Jackson）。Boot 检测到 Jackson 存在就自动装配 `MappingJackson2HttpMessageConverter`，与 Gson/Fastjson2 的转换器并存，产生冲突。
- **解决方案**：不用 Jackson 时从 starter-web 排除 `spring-boot-starter-json`；或用 `spring.mvc.message-converters-strategy`/自定义 `configureMessageConverters` 明确优先级。Fastjson2 还要排除其自身与 Jackson 共存的转换器（见 02 篇）。

> 参考：[01-Gson基础详解](01-Gson基础详解.md)、[02-Fastjson2基础详解](02-Fastjson2基础详解.md)

### 1.2 spring.jackson.* 配置不生效

- **现象**：改了 `spring.jackson.date-format` 等，序列化没变化。
- **原因**：① 自定义了 `ObjectMapper` Bean 但 `new ObjectMapper()` 绕过了 Boot Builder，`spring.jackson.*` 不再绑定；② 用了 `@JsonFormat` 但没注册相应对应模块。
- **解决方案**：用 `ObjectMapperBuilderCustomizer` 追加而非整 Bean 覆盖；字段级格式确保 JSR310 已注册（见 07 篇 3.3）。

## #2 性能

### 2.1 大 JSON 全量绑内存 → 流式/JsonNode

- **现象**：超大 JSON（如全量日志/大列表）用 `readValue(json, POJO.class)` 直接 OOM 或 GC 抖动。
- **原因**：对象绑定一次性把整棵 JSON 结构读入内存，再分配对象树，双份内存压力。
- **解决方案**：改用流式 `JsonParser`/`JsonReader` 逐 token 处理；只取少数字段用 JSONPath（Fastjson2）/ `readTree`+局部；需整体但只读用 `JsonNode` 而非 POJO。见 [05-Jackson核心与ObjectMapper详解](05-Jackson核心与ObjectMapper详解.md)、[03-Fastjson2高级·JSONB与JSONPath详解](03-Fastjson2高级·JSONB与JSONPath详解.md)。

## #3 安全

### 3.1 🚨 Fastjson2 为功能全局开 autoType → 未修复 RCE（本次新发现，高亮）

- **现象**：为了让 `@type`/多态反序列化生效，直接给 `JSON.parseObject` 传 `JSONReader.Feature.SupportAutoType`，服务暴露公网后可能被反序列化攻击。
- **原因**：**2026-07 长亭科技披露 fastjson2 autoType 反序列化路径安全风险；官方 issue #7702 确认当前所有已发布版本（含 2.0.64）均不含修复（PR #7695 未合并）**。显式开启 `SupportAutoType` 即暴露攻击面，当前没有已修复版本。
- **解决方案**：
  1. **非必要不开 autoType**，保持默认关闭（默认即安全）。
  2. 确需多态/类型信息用 `JSONReader.autoTypeFilter(AutoTypeBeforeHandler)` 精确白名单（黑名单类写全类名，2.0.63 起 accept 前缀不覆盖黑名单）。
  3. 公网场景禁用 autoType；开启 `-Dfastjson2.parser.safeMode=true` 总闸兜底。
  4. 升级前查官方公告是否有新补丁。

> 深度见 [04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)。

### 3.2 Jackson 多态 / defaultTyping 反序列化 → RCE 风险

- **现象**：为了接口/抽象类自动识别具体类型，全局调用了 `ObjectMapper.enableDefaultTyping()`，或手写反序列化信任了任意类型名。
- **原因**：`enableDefaultTyping` 向 JSON 注入类型名并自动实例化，攻击者可指定任意可利用类（gadget）触发反序列化 RCE；相关 CVE（如 CVE-2026-59889）多绑定此类链路。
- **解决方案**：**禁用全局 `enableDefaultTyping`**；多态用 `@JsonTypeInfo` + `@JsonSubTypes` 显式白名单；服务端校验具体类型；保持 Jackson 在安全版本线（2.22.1+ 等）。见 [06-Jackson注解与高级定制详解](06-Jackson注解与高级定制详解.md)。

## #4 序列化行为

### 4.1 Gson inner class 反序列化失败 → static

- **现象**：`gson.fromJson(json, InnerType.class)` 报 `cannot invoke inner class constructor` 或 `InstantiationException`。
- **原因**：非 static 内部类隐含持有外部类引用，且无真正的无参构造，Gson/反射无法直接实例化。
- **解决方案**：将内部类声明为 `static`；或用 `InstanceCreator` 显式提供实例化（配外部引用）。见 [01-Gson基础详解](01-Gson基础详解.md)。

### 4.2 Jackson @JsonFormat 日期格式不生效

- **现象**：`@JsonFormat(pattern="yyyy-MM-dd")` 对 `LocalDate`/`LocalDateTime` 无效，仍输出 ISO `2026-08-14T...` 或时间戳。
- **原因**：`LocalDate`/`LocalDateTime` 是 JSR310 类型，需要注册 **`JavaTimeModule`**（`jackson-datatype-jsr310`）；不注册则 Jackson 用默认序列化器，`@JsonFormat` 不走。
- **解决方案**：`om.registerModule(new JavaTimeModule())`；Boot 中已自动注册。配 `@JsonFormat` + `WRITE_DATES_AS_TIMESTAMPS` 关闭。见 [06-Jackson注解与高级定制详解](06-Jackson注解与高级定制详解.md)。

### 4.3 Fastjson2 日期默认格式与 Jackson 不同

- **现象**：同一日期，Fastjson2 默认输出 `2026-08-14 12:00:00`（`yyyy-MM-dd HH:mm:ss`），Jackson（字符串模式）输出 `2026-08-14T12:00:00`。
- **原因**：两库对 JSR310/Date 的默认格式不同——Fastjson2 用 `yyyy-MM-dd HH:mm:ss` 风格。
- **解决方案**：跨库/跨端对接时显式用 `@JSONField(format=...)` / `@JsonFormat(pattern=...)` 统一格式，不要依赖默认。见 [02-Fastjson2基础详解](02-Fastjson2基础详解.md)。

### 4.4 Gson null 字段丢失（默认忽略）

- **现象**：`gson.toJson(obj)` 后，值为 null 的字段完全不见了。
- **原因**：Gson **默认忽略 null 字段**（不输出键）。
- **解决方案**：需要输出 null 用 `new GsonBuilder().serializeNulls().create()`。注意集合内的 null 元素始终输出。见 [01-Gson基础详解](01-Gson基础详解.md)。

## #5 泛型

### 5.1 泛型 List 反序列化成 LinkedHashMap → TypeReference/TypeToken

- **现象**：`om.readValue(json, new ArrayList<User>().getClass())` 或 `gson.fromJson(json, list.getClass())`、`JSON.parseObject(json)`（无 TypeReference）得到 `List<LinkedHashMap>`，转不回 `User`。
- **原因**：Java **泛型擦除**——`.getClass()`/裸 `List` 丢失了 `User` 类型信息，库只能退化为 `LinkedHashMap` 存放。
- **解决方案**：
  - Jackson：`new TypeReference<List<User>>() {}`
  - Gson：`new TypeToken<List<User>>(){}.getType()`
  - Fastjson2：`new TypeReference<List<User>>() {}`
  见 [05-Jackson核心与ObjectMapper详解](05-Jackson核心与ObjectMapper详解.md)、[01-Gson基础详解](01-Gson基础详解.md)。

## #6 Boot 集成

### 6.1 Boot 排除 Jackson 影响其他依赖

- **现象**：为切到 Gson/Fastjson2，在 `spring-boot-starter-web` 排除 `spring-boot-starter-json`，结果其他依赖（如 Spring Data REST、SpringDoc、actuator health）的 JSON 序列化异常或缺失。
- **原因**：`spring-boot-starter-json` 也被其他 starter 传递依赖（REST 文档、监控、部分中间件），排除后这些模块失去 Jackson 默认 JSON 能力。
- **解决方案**：优先保留 Jackson 作为默认，只在特定端点替换转换器；确要全局切库，排查所有传递依赖并对受影响模块补偿配置/转换器；用 `@JsonComponent` 或自定义消息转换器按需接管而非全局排除。

## 本文档被引用索引

各详解篇文末「常见踩坑」小节引用 `#x.x` 跳转本库：

| 编号 | 涉及篇 |
|---|---|
| #1.1 | 01 Gson、02 Fastjson2 |
| #2.1 | 03/05 性能 |
| #3.1 | 00 总览、04 Fastjson2 安全（新发现，高亮） |
| #3.2 | 06 Jackson 多态 |
| #4.1 | 01 Gson |
| #4.2 | 06/07 Jackson 日期 |
| #4.3 | 02 Fastjson2 |
| #4.4 | 01 Gson |
| #5.1 | 01/02/05 泛型 |
| #6.1 | 07 Boot |
