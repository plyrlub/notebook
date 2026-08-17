---
tags:
  - Java
  - JSON
  - Fastjson2
  - JSONB
  - JSONPath
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Fastjson2 高级 · JSONB 与 JSONPath 详解

## 📋 总纲

本篇讲 Fastjson2 独有高级能力：**JSONB 二进制格式**、**JSONPath 路径提取**、**JSON Schema 校验**。这些是 Fastjson2 相对 Jackson/Gson 的差异化价值（高性能二进制、内置 JSONPath、内置 Schema）。

> 前置：[02-Fastjson2基础详解](02-Fastjson2基础详解.md)；安全见 [04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)；踩坑：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)。

## 1. JSONB 二进制格式（★）

### 1.1 是什么

JSONB 是 **Fastjson2 独有的二进制 JSON 格式**，数据更紧凑、读写更快，但**不是 JSON 文本**（不可直接被前端/日志阅读）。它是 `JSONB` 包下的独立 API。

```java
import com.alibaba.fastjson2.JSONB;
import com.alibaba.fastjson2.util.TypeReference;

// 序列化
byte[] bytes = JSONB.toBytes(user);

// 反序列化
User u = JSONB.parseObject(bytes, User.class);
List<User> list = JSONB.parseObject(bytes, new TypeReference<List<User>>() {});
```

**代码说明**：`JSONB.toBytes` 生成 `byte[]`，`JSONB.parseObject` 读回；泛型同样需要 `TypeReference`。

### 1.2 紧凑模式：BeanToArray Feature

把 JavaBean 打成**字段名不带类型的紧凑数组**，进一步缩小体积：

```java
// 序列化为数组（不写字段名）
byte[] bytes = JSONB.toBytes(user, JSONWriter.Feature.BeanToArray);

// 读回，支持数组还原
User u = JSONB.parseObject(bytes, User.class, JSONReader.Feature.SupportArrayToBean);
```

| Feature | 方向 | 作用 |
|---|---|---|
| `BeanToArray` | 写 | JavaBean 变字段数组，省掉键名，更小 |
| `SupportArrayToBean` | 读 | 把数组还原为 JavaBean |

**说明**：`BeanToArray` 牺牲可读性换体积/速度，字段跟具清单确定才安全；配 `SupportArrayToBean` 读回。适合字段结构稳定、对存储敏感的场景。

### 1.3 JSONB vs JSON 文本、Hessian/Kryo

| 对比项 | JSON 文本 | JSONB | Hessian/Kryo |
|---|---|---|---|
| 格式 | 文本 | 二进制 | 二进制 |
| 体积 | 大 | 更小 | 小 |
| 速度 | 一般 | 更快 | 快 |
| 跨语言 | ✅ | ⚠️ 仅能由 fastjson2/envoy 等特定读 | 依赖协议 |
| 可读性 | ✅ | ⊘ | ⊘ |

- **JSONB vs JSON 文本**：体积/速度都占优，但丧失可读性与泛跨语言性。
- **JSONB vs Hessian/Kryo**：它是 **Dubbo 新默认序列化**，替代旧 Hessian，生态在阿里系/微服务内推进。

### 1.4 适用场景

- **Kafka / 消息队列**：紧凑省带宽。
- **内部通信（RPC/Dubbo）**：快、小。
- **高性能缓存（本地/Redis）**：`byte[]` 直接存取，省序列化开销。

```java
// Redis 缓存 JSONB（伪代码）
byte[] cached = redis.get(key);
if (cached == null) {
    cached = JSONB.toBytes(data);
    redis.set(key, cached);
} else {
    data = JSONB.parseObject(cached, Data.class);
}
```

**说明**：JSONB 适合「同一进程/同一技术栈」，最大化序列化性能；跨语言场景应回退 JSON 文本。

## 2. JSONPath（★）

### 2.1 是什么/语法

- **定义**：不完全反序列化，直接按路径提取目标字段，避免整棵解析。
- **语法**：SQL:2016 JSONPath 风格（`$.id`、`$.items[0]`、过滤 `$.items[?@.price>100]` 等）。

### 2.2 JSONPath.of + extract

```java
import com.alibaba.fastjson2.JSONPath;

String json = "...";
// 预编译缓存复用
JSONPath path = JSONPath.of("$.id");
int id = (Integer) path.extract(json);

// 从 String 提取
Object r2 = JSONPath.of("$.user.name").extract(jsonText);

// 从 JSONReader / JSONB 字节提取（签名可能随版本变化，据官方文档请复核）
Object r3 = JSONPath.of("$.user.name").extract(JSONB.parseObject(bytes));
```

| API | 说明 |
|---|---|
| `JSONPath.of(path)` | 预编译路径，可缓存复用，提升性能 |
| `path.extract(String/byte[])` | 对输入提取结果 |
| `path.extract(reader)` | 从 JSONReader/JSONBReader 提取 |

**说明**：`JSONPath.of` 编译一次可反复使用（放静态字段缓存），比每次现用字符串解析快；`extract` 接受 String、byte[]（JSONB）或 reader。

### 2.3 高级能力

过滤表达式 / 数组切片 / 聚合：

```java
// 过滤：价格大于 100 的第一项
Object item = JSONPath.of("$.items[?(@.price > 100)][0]").extract(json);
// 切片：取前 2 个
Object head = JSONPath.of("$.items[0:2]").extract(json);
// 聚合：数量/length
Object n = JSONPath.of("$.items.length()").extract(json);
```

**说明**：过滤表达式用 `?(@.cond)`，嵌套条件、数组切片 `[start:end]`、聚合函数（`length()`/`sum()` 等）均支持；细节以 Fastjson2 官方文档为准（据官方文档请复核）。

## 3. JSON Schema 校验

### 3.1 内置高性能校验

Fastjson2 内置 JSON Schema 校验器，无需引入 networknt 等第三方：

```java
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.schema.JSONSchema;

String schemaText = """
    {"type":"object",
     "required":["name"],
     "properties":{"name":{"type":"string"},
                   "age":{"type":"integer","minimum":0}}}
    """;
JSONSchema schema = JSONSchema.of(JSONObject.parseObject(schemaText));

JSONObject data = JSONObject.parseObject("{\"name\":\"bob\",\"age\":18}");
boolean ok = schema.isValid(data);            // true
// 带错误信息
var result = schema.validate(data);           // 返回结果对象，含错误明细
```

**说明**：`JSONSchema.of` 解析 Schema 定义，`isValid` 返回布尔，`validate` 返回带错误路径/消息的明细结果。

### 3.2 与 networknt 对比

| | Fastjson2 内置 | networknt json-schema-validator |
|---|---|---|
| 引入方式 | 随 `fastjson2` | 独立依赖 |
| 性能 | 内建、快 | 通用但较重 |
| 生态 | 随 Fastjson2 使用 | 独立、可配很多库 |

**说明**：Fastjson2 内置 Schema 主打「同库即用、性能好」；networknt 适合独立、跨库/多方言的标准校验。

### 3.3 场景

- 入参/出参校验（简单、性能敏感）。
- **AI/LLM 结构化输出**：先用 Schema 校验模型输出是否符合预期结构，再做反序列化——即「定义结构 → 校验 → 解析」管线，一句话就能带出。

```java
// AI 结构化输出校验伪代码
String llmOutput = llm.chat(prompt);        // 返回 JSON 文本
JSONSchema schema = JSONSchema.of(expectSchema);
if (!schema.isValid(JSONObject.parseObject(llmOutput))) {
    // 重试/修正提示词
}
```

**说明**：LLM 输出不稳定，Schema 前置校验可减少解析崩溃，是结构化输出的常见护栏。

## 小结

- **JSONB**：Fastjson2 独有二进制，`BeanToArray` 再省体积，Dubbo 新默认序列化，适合同栈高频/缓存场景。
- **JSONPath**：`JSONPath.of` 预编译 + `extract`，不整列反序列化直接取字段，支持过滤/切片/聚合。
- **JSON Schema**：内置高性能校验，`JSONSchema.of` + `isValid`/`validate`，适合入参校验与 LLM 结构化输出。
- 三者都是 Fastjson2 相对 Jackson/Gson 的差异化能力；**用于公网前仍须先看安全篇**。

## 相关笔记

- 前置：[02-Fastjson2基础详解](02-Fastjson2基础详解.md)
- 安全：[04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)
