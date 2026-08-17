---
tags:
  - Java
  - JSON
  - Fastjson2
  - Fastjson
  - 安全
  - AutoType
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/三方库/JSON序列化）
归属: 01-学习/Java/三方库/JSON序列化
---

# Fastjson2 安全与升级详解

## 📋 总纲

本篇是本系列**安全红线的核心篇**。读完你会：说清 AutoType 是什么、1.x vs 2.x 本质差异、Fastjson2 **未修复 RCE** 的触发条件与缓解、SafeMode 配置、AutoType 安全实践，以及从 Fastjson 1.x 升级到 2.x 的完整迁移清单。

> 前置：[00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)；基础用法：[02-Fastjson2基础详解](02-Fastjson2基础详解.md)；防御性选择见 [07-Jackson与SpringBoot集成详解](07-Jackson与SpringBoot集成详解.md)（Jackson 是 Boot 默认更稳的选择）。

> 🚨 本篇安全信息调研时间：**2026-08-14（联网已查证）**。

## 1. AutoType 是什么

AutoType 让序列化**携带类型信息**，反序列化**自动识别具体类型**——这是 Java 反序列化 RCE 的共性机制来源。

- **序列化**：`JSONWriter.Feature.WriteClassName` 在输出里写入类型名（如 `{"@type":"com.x.User",...}`）。
- **反序列化**：`JSONReader.Feature.SupportAutoType` 允许"看到 `@type` 就按该类型实例化"。

```java
// 序列化带类型（危险方向，谨慎）
String json = JSON.toJSONString(user, JSONWriter.Feature.WriteClassName);

// 反序列化自动类型（危险方向，如开启则必须配白名单）
User u = JSON.parseObject(json, User.class, JSONReader.Feature.SupportAutoType);
```

**说明**：`@type` 字段可被攻击者操控。若允许任意 `com.*` 反序列化，配合可利用的 gadget 类（数据源/代理链等）即可触发 RCE。**本质是「信任了不可信的类型名 + 存在可利用类」**。

## 2. 1.x vs 2.x AutoType 对比（★）

| 维度 | Fastjson 1.x | Fastjson2 |
|---|---|---|
| 包名 | `com.alibaba.fastjson` | `com.alibaba.fastjson2` |
| groupId | `com.alibaba:fastjson` | `com.alibaba.fastjson2:fastjson2` |
| AutoType 默认 | **开**（白名单） | **关** |
| 白名单机制 | 内置黑/白名单，可被绕过 | 无隐式白名单，需 `autoTypeFilter` |
| 循环引用检测 | 默认开 | 默认关 |
| 智能匹配 | 默认开 | 默认关 |
| 所有 Feature 默认 | 混合（部分开） | **全部关** |
| SafeMode | — | 支持（`-Dfastjson2.parser.safeMode=true`） |

> **变化总表**：Fastjson2 从 1.x 继承教训，把**所有高危/影响行为的 Feature 默认关闭**，需要显式开启。这是相对 1.x 最大的安全改进——默认行为安全了。

- **1.x 白名单默认开启 = 漏洞根源**：默认允许一部分类型反序列化，但黑白名单模型在多轮绕过（1.2.25→1.2.80+）后仍不安全，最终 1.2.84 停维护。
- **2.x 无隐式白名单/全关/黑名单过滤/SafeMode**：默认不信任类型名，风险大幅收敛。

## 3. 🚨 AutoType 安全现状与未修复 RCE（2026）（★）

> 本次调研重大发现，本系列安全红线核心。

- **披露**：2026-07 **长亭科技**披露 fastjson2 **autoType 反序列化路径**存在安全风险。
- **官方确认**：官方 issue **#7702** 确认当前**所有已发布版本（含 2.0.64）均不含修复**，修复 PR **#7695 未合并**。
- **触发条件**：必须**显式开启** `SupportAutoType` 才有风险；**默认关闭不受影响**。
- **缓解措施**：
  - JVM 参数：`-Dfastjson2.parser.safeMode=true`
  - 非必要不开 autoType，确需则用 `JSONReader.autoTypeFilter(AutoTypeBeforeHandler)` 精确白名单
  - **公网暴露场景禁用 autoType**。
- **姿态**：默认/关闭时 **🟡 有条件暂时安全**；一旦开启 autoType，当前**没有已修复版本**。

```java
// 安全策略：能不开就不开
// 必须开时，用 autoTypeFilter 收紧到精确白名单
JSONReader.autoTypeFilter((className, type, features) ->
    className.startsWith("com.your.pkg.model.")  // 白名单前缀
);
```

**说明**：这是「少数开启者的风险精准定位」——只要你没显式开 `SupportAutoType`，默认就是关闭的，攻击面不展开。但**任何团队都不能因为"在用 2.x"就放松**，一旦有人为了兼容 1.x 迁入代码开了 autoType 且用了可达攻击面 URL，就可能中招。

> 深度表述一句话：**Fastjson2 的安全依赖"你不开 autoType"这条自律**，而非依赖官方补丁——因为后者当前不存在。

## 4. SafeMode 配置

SafeMode 从**总闸**角度彻底关闭类型识别：

```java
// JVM 参数（最彻底，全进程生效）
-Dfastjson2.parser.safeMode=true
```

- 开启后，任何 `SupportAutoType`/`WriteClassName` 都被忽略，等效禁 autoType。
- 程序内也可用 `JSONReader.autoTypeFilter(AutoTypeBeforeHandler)` 做程序化白名单。
- ⚠️ **注意**：**自 2.0.63 起，accept 前缀不覆盖黑名单类型**，例如 `DruidDataSource` 等黑名单类**必须写全类名**才能放行。

```java
// 黑名单类写全类名才生效（非前缀匹配）
JSONReader.autoTypeFilter((className, type, features) ->
    className.equals("com.alibaba.druid.pool.DruidDataSource")   // 精确，非 prefix
);
```

**说明**：SafeMode 是"总保险丝"，autoTypeFilter 是"精确允许列表"。两者配合：默认 SafeMode 兜底，个别可信类型用全类名白名单放行。

## 5. 从 Fastjson 1.x 升级指南（★）

> ⚠️ **不能 100% 兼容，必须测试**。v1 兼容模块（`com.alibaba:fastjson:2.0.64`）只缓解包名迁移，行为（Feature 默认、AutoType、异常类型）仍有差异。

### 5.1 迁移总表

| 关注点 | 1.x | 2.x 变化 |
|---|---|---|
| 包名 | `com.alibaba.fastjson.JSON` | `com.alibaba.fastjson2.JSON` |
| groupId | `com.alibaba:fastjson` | `com.alibaba.fastjson2:fastjson2` |
| AutoType | 默认开 | 默认关 → 需显式开 + 白名单 |
| 循环引用 | 默认开 | 默认关 |
| 智能匹配 | 默认开 | 默认关 |
| Feature 默认 | 部分开 | 全部关 |
| 无参构造 | 需 | 需（可 `@JSONCreator`） |
| 日期格式 | 特定 | `yyyy-MM-dd HH:mm:ss`（与 Jackson 不同，见踩坑 [99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)） |

### 5.2 升级步骤

1. 替换依赖坐标到 `com.alibaba.fastjson2:fastjson2`。
2. 全局替换 import（`com.alibaba.fastjson` → `com.alibaba.fastjson2`）。
3. 逐个检查依赖 AutoType / 智能匹配 / 循环引用等依赖"默认开启"的代码，**显式补齐对应的 2.x Feature**。
4. 对每个对外接口做**序列化结果 diff 测试**（字段顺序、null、日期格式、类型）。
5. 上线前用 SafeMode + autoTypeFilter 白名单关闭非必要 autoType。

**说明**：迁移不是"换坐标"这么简单——**默认行为 flip** 会导致漏字段/格式变化/反序列化失败。单测与黄金对比文件（golden files）是标配。

## 6. Fastjson 1.x CVE 历史回顾

- 涉及 CVE：CVE-2017-18349、CVE-2019-20330、CVE-2020-10673、CVE-2022-25845、CVE-2026-16723 等，均集中于 AutoType。
- 决定性版本：
  - 1.2.68~1.2.83：**默认可 RCE**（可被 `@JSONType` 注解等信号触发，CVE-2026-16723, CVSS 9.0）。
  - 1.2.84：**已停维护**的最后版本。
- 结论与总览一致：**新项目绝不选 1.x**。明细表见 [00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)。

## 7. 安全最佳实践清单

1. **首选 Jackson**（Boot 默认、生态强、默认不开类型识别），可规避本库全部 AutoType 心智负担。
2. 若必须用 Fastjson2：**保持 autoType 默认关闭**，这是安全第一原则。
3. 非开不可时：`SafeMode` 兜底 + `autoTypeFilter` 精确全类名白名单 + 拒绝黑名单类。
4. **公网直接暴露反序列化入口**的场景：禁用 autoType，用 DTO + 显式类型。
5. 升级任何 Fastjson2 版本前：检查官方 issue/安全公告（2026-08 时 #7702 未修复）。
6. 定时升级到最新补丁版本，本项目基线 2.0.64 为调研时无更安全版本，**上线前复核是否有新补丁**。

## 小结

- AutoType 是 Fastjson 系 RCE 的根源；1.x 白话名单+默认开 = 无穷绕过；2.x 默认全关 = 安全改进。
- **Fastjson2 当前（2026-08）开启 autoType 有未修复 RCE（长亭披露 / #7702 / PR #7695 未合并）**，唯一缓解是"不开 + SafeMode + autoTypeFilter 精确白名单"。
- SafeMode 是总闸；2.0.63 起黑名单类必须写全类名。
- 1.x→2.x 不能 100% 兼容，默认行为 flip 必须测。
- 安全红线统一措辞：默认/关时 **🟡 有条件暂时安全**，开启则危。

## 相关笔记

- 总览安全节：[00-JSON序列化与反序列化总览](00-JSON序列化与反序列化总览.md)
- 踩坑新增：[99-JSON序列化踩坑记录](99-JSON序列化踩坑记录.md)
