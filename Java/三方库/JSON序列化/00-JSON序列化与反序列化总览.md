---
tags:
  - Java
  - JSON
  - Gson
  - Fastjson2
  - 序列化
  - 反序列化
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Java JSON 三大库序列化与反序列化总览

## 📋 总纲

本篇是「Java JSON 三大库」系列的总入口，回答三个问题：

1. 三大库（Gson / Fastjson2 / Jackson）分别是什么、怎么选？
2. 各自的序列化/反序列化怎么做？详解在后面的分解篇。
3. 安全上有什么红线？尤其是 Fastjson 1.x 的 AutoType 与 Fastjson2 未修复 RCE。

系列共 9 篇，本篇负责**导航 + 对比 + 选型 + 安全总纲**；每篇详解的内部 API、注解、代码示例在各自分解篇展开。

> 系列已联网查证的安全信息，本次调研时间统一为 **2026-08-14**，口径全系列一致。

## 1. 版本基线

本目录三库版本基线（整理时间 2026-08，以 Maven 中央仓库当前稳定版为准）：

| 库 | 当前版本 | 定位 | 备注 |
|---|---|---|---|
| Gson | 2.14.0 | Google 出品，轻量反射库 | Android 常用 |
| Jackson-databind | 2.22.1 | FasterXML 出品，Spring Boot 默认 | `jackson-databind` 核心 |
| Fastjson2 | 2.0.64 | 阿里出品，性能极致 | 含 JSONB 二进制 |

配套说明：

- **JDK**：三库均支持 JDK 8+；Jackson 3 与部分新特性要求 JDK 17+。本系列示例按 JDK 17/21 可编译书写。
- **Spring Boot 对应**：Jackson 是 Boot 官方默认，Boot 3 系列自带 `spring-boot-starter-json`；Gson 有 Boot 官方自动配置；Fastjson2 为非官方，需第三方扩展。

> 版本更新较快，下表以「整理时间 2026-08」为准；后续如需升级请以 Maven 中央仓库实时版本复核。

## 2. 前置知识

读本篇前建议已具备：

- **Java 反射**：理解 `Class`、`Field`、`Method`，因为三库（尤其 Gson）序列化本质是反射遍历对象字段。
- **泛型与类型擦除**：理解 `List<User>` 在运行期 `getClass()` 拿不到 `User`，是反序列化泛型丢类型的根源（详见 Gson/Jackson 的 `TypeToken`/`TypeReference`）。
- **POJO 概念**：getter/setter + 无参构造的普通 JavaBean，是 JSON 序列化的主流目标。
- **序列化概念**：对象 ↔ 字节/文本 的互转；JSON 是文本格式，JSONB 是二进制格式。

进阶前置（通用）链接：

- **00-序列化与数据格式总览**（见知识库）（位于 `01-学习/通用技术/序列化与数据格式/`）——序列化与数据格式的通用总览，先看它能建立整体框架。

## 3. 文档导航

本系列 9 篇索引：

| 编号 | 文件 | 内容 | 优先级 |
|---|---|---|---|
| 00 | 00-JSON序列化与反序列化总览 | 导航、对比、选型、安全总纲（本篇） | 必读 |
| 01 | 01-Gson基础详解 | Gson 从零到精：TypeToken、字段控制、自定义适配器 | 按需 |
| 02 | 02-Fastjson2基础详解 | Fastjson2 日常 JSON 核心：静态类、JSONField、Feature | 按需 |
| 03 | 03-Fastjson2高级·JSONB与JSONPath详解 | JSONB 二进制、JSONPath 提取、JSON Schema | 进阶 |
| 04 | 04-Fastjson2安全与升级详解 | AutoType、SafeMode、1.x 升级、未修复 RCE | **强烈建议** |
| 05 | 05-Jackson核心与ObjectMapper详解 | Jackson 基础：ObjectMapper、JsonNode、TypeReference | 必读 |
| 06 | 06-Jackson注解与高级定制详解 | 注解全家、多态、自定义序列化 | 必读 |
| 07 | 07-Jackson与SpringBoot集成详解 | spring.jackson.*、自定义 Bean、Jackson 3 | 必读 |
| 99 | 99-JSON序列化踩坑记录 | 踩坑库：#1配置/#2性能/#3安全/#4行为/#5泛型/#6Boot | 参考 |

## 4. 学习目标

学完本系列你应该能：

1. 说出三大库各自定位、默认行为与适用场景，会做选型取舍。
2. 用 Gson 完成含泛型、字段改名、自定义适配器的序列化/反序列化。
3. 用 Fastjson2 的 JSON/JSONObject/JSONArray 处理日常 CRUD JSON，并了解 JSONB。
4. 说清 Fastjson 1.x AutoType 漏洞根源与 Fastjson2 未修复 RCE 的触发条件与缓解。
5. 用 Jackson ObjectMapper 做树模型、泛型、多态、日期序列化。
6. 在 Spring Boot 中通过 `spring.jackson.*` 或自定义 Bean 配置全局 JSON 行为。
7. 会判断一条 JSON 处理链路是否存在反序列化安全风险。

## 5. 最佳学习路径

推荐顺序（以业务最常用的 Jackson 为默认重点）：

1. **先读本篇（00）**：建立对比与安全心智。
2. **→ Jackson（05→06→07）**：Boot 默认、生态最强，主力。
3. **→ Gson（01）**：轻量场景补充。
4. **→ Fastjson2（02→03→04）**：性能与高级能力，**务必先看 04 安全篇**再决定是否使用。

> 安全红线优先：无论用哪个库，先看 8·安全风险 与 04 篇，再谈功能。

## 6. 三大 JSON 库对比

核心对比表：

| 维度 | Jackson | Gson | Fastjson2 |
|---|---|---|---|
| 提供方 | FasterXML | Google | 阿里巴巴 |
| 定位 | 生态最全、Boot 默认 | 轻量、反射驱动、零依赖 | 性能极致、含二进制 |
| 性能（阿里官方 JMH） | 中等（排序：Fastjson2 > Jackson > Gson） | 相对较慢 | 最快 |
| 生态 | 极强：模块多（jsr310、modules）、社区大 | 一般 | 阿里系 + 第三方扩展 |
| 泛型支持 | `TypeReference<T>` | `TypeToken<T>` | `TypeReference<T>` |
| 树模型 | `JsonNode`/`ObjectNode` | `JsonElement`/`JsonObject` | `JSONObject`/`JSONArray` |
| 二进制 | ⊘（无原生）| ⊘ | **JSONB**（独有） |
| JSONPath | 无原生 | 无原生 | **内置 JSONPath** |
| JSON Schema | 有（`jackson-module-jsonSchema`） | ⊘ | **内置高性能 Schema 校验** |
| Boot 集成方式 | 官方自动装配 `MappingJackson2HttpMessageConverter` + `spring.jackson.*` | 官方自动配置（`@ConditionalOnClass`）注册 `GsonHttpMessageConverter` + `spring.gson.*` | 非官方，需 `fastjson2-extension-spring5/6` 第三方扩展 |

**Boot 支持力度对比**（选型关键）：

- **Jackson** = 官方自动装配 `MappingJackson2HttpMessageConverter`，`spring.jackson.*` 全套配置项，Boot 默认，功能最全、可定制性最高。
- **Gson** = Boot 官方自动配置（`@ConditionalOnClass` 触发），自动注册 `GsonHttpMessageConverter`，提供 `spring.gson.*` 配置项，但**配置项远少于 Jackson，WebFlux 不友好**。
- **Fastjson2** = 非官方，Boot 不自动识别，需引入 `fastjson2-extension-spring5/6` 扩展并自行注册 `FastJsonHttpMessageConverter`，Boot 官方只声明 Jackson/Gson 为默认选项。

## 7. 选型建议

综合结论（按业务场景）：

- **默认首选 Jackson**：Boot 内置、生态最强、安全可控（主动避免 `enableDefaultTyping` 即较安全）。90% 的常规 Web/后端场景选它。
- **轻量 / Android / 简单 POJO → Gson**：零外部依赖、API 极简、Android 官方生态友好，适合小型或移动端项目。
- **极端性能且接受关闭 autoType → Fastjson2**：若你的场景对序列化吞吐有极致要求（Kafka 高吞吐、高频内部调用），又愿意承担安全心智（不开启 autoType），可考虑 Fastjson2。JSONB 是其独特加分项。
- 不支持自定义树模型/JSONPath/JSON Schema 需求的，Fastjson2 单一即可；需要最广生态面则 Jackson。

决策逻辑（伪代码）：

```
if (Boot 项目)          → Jackson（默认, 安全省心）
else if (Android/轻量)  → Gson
else if (极致性能+关自动类型) → Fastjson2
else                    → Jackson（生态兜底）
```

> 性能取舍提示：Fastjson2 的性能优势在多分支/大数据场景明显；中小型业务 JSON 差异可忽略，不要因性能冲动引入安全风险。

## 8. 安全风险

> 安全风险调研时间：2026-08-14（联网已查证）

⚠️ **反序列化安全是三大库的共同红线**：默认行为安全性不同，但「开启自动类型识别」是所有 RCE 的共性根源。下面先给安全姿态表，再给明细与专题。

### 8.1 安全姿态总表

| 危险版本区 | 相对安全线 | 姿态 | 备注 |
|---|---|---|---|
| Fastjson 1.x：大量 RCE，`1.2.68~1.2.83` 默认可触发 RCE | `1.2.84`（已停维护） | 🔴 高危不推荐 | AutoType 是根源 |
| Fastjson2：显式开 autoType 有未修复 RCE | 关闭 autoType 时 `2.0.64+` | 🟡 有条件暂时安全 | 一旦开 autoType，当前无已修复版本，见 04 篇 |
| Jackson：多分支 CVE（如 CVE-2026-59889 影响 2.18.0-2.18.9 / 2.21.0-2.21.5 / 2.22.0-2.22.1） | `2.18.9+` / `2.21.5+` / `2.22.1+` / `3.1.5+` / `3.2.1+` | 🟡 暂时安全 | 需禁用 `enableDefaultTyping` |
| Gson：`<2.8.9`（CVE-2022-25647 反序列化 DoS） | `2.8.9+` 修复主要；`2.14.0+` 无已知漏洞（2026-04-23 发布） | 🟡 暂时安全 | 历史漏洞少且轻 |

### 8.2 Fastjson 1.x CVE 明细表

| CVE | 严重度 | 影响版本 | 描述 | 修复版本 |
|---|---|---|---|---|
| CVE-2026-16723 | 严重 CVSS 9.0 | 1.2.68 - 1.2.83 | 默认配置可 RCE，利用 `@JSONType` 注解作为信任信号，零补丁级 | 1.2.84 |
| CVE-2022-25845 | High 8.1 | <1.2.83 | AutoType 绕过 RCE | 1.2.83 |
| 其余历史 CVE | - | - | CVE-2017-18349 / CVE-2019-20330 / CVE-2020-10673 等，均为 AutoType 系列绕过 | 见各公告 |

> **结论**：Fastjson 1.x 已停止维护（1.2.84 为终点），AutoType 白名单机制在多轮绕过后仍不安全，**任何新项目都不应选 1.x**。

### 8.3 🚨 Fastjson2 未修复 RCE 专题警示（本次调研重大发现）

- **披露**：2026-07 长亭科技披露 fastjson2 autoType 反序列化路径存在安全风险。
- **官方确认**：官方 issue **#7702** 确认当前**所有已发布版本（含 2.0.64）均不含修复**，修复 PR **#7695 未合并**。
- **触发条件**：必须**显式开启** `SupportAutoType` 才有风险；**默认关闭**不受影响。
- **缓解**：`-Dfastjson2.parser.safeMode=true`；或使用 `autoTypeFilter` 精确白名单。
- **策略**：非必要不开 autoType；公网暴露场景**禁用** autoType。

> 深入见 [04-Fastjson2安全与升级详解](04-Fastjson2安全与升级详解.md)。

## 9. 核心知识点与演进

三大库核心理念一句话：

- **Jackson**：对象绑定（POJO↔JSON），默认全字段自动检测（`AutoDetect`），生态模块最全。
- **Gson**：反射零配置，`new Gson()` 开箱即用，极简 API。
- **Fastjson2**：性能极致 + 二进制（JSONB）+ 内置 JSONPath，Feature 默认全关更安全。

演进方向：

- **Jackson 3**：包名迁移到 `tools.jackson`，核心类 `ObjectMapper` → `JsonMapper`；`jackson-databind` 2.x 仍是当前 Boot 默认，3.x 面向未来迁移。
- **Fastjson 1.x → 2.x**：包名 `com.alibaba.fastjson` → `fastjson2`，groupId 变化，AutoType 默认开 → 关，智能匹配默认开 → 关，**不能 100% 兼容必须测试**（见 04 篇迁移表）。

## 相关笔记

- 上游总览：**00-序列化与数据格式总览**（见知识库）
- 分解篇：01 Gson / 02 Fastjson2 / 03 JSONB与JSONPath / 04 Fastjson2安全 / 05 Jackson核心 / 06 Jackson注解 / 07 Jackson集成 / 踩坑 99

## 参考资料

- 安全调研与文库检索：查询日期 2026-08-14（Gson 2.14.0 安全公告、Fastjson2 issue #7702、Jackson CVE bulletin）。
- 性能数据来源：阿里官方 JMH 基准（query 日期 2026-08-14，数据维度见各库使用报告，据官方文档请复核）。
