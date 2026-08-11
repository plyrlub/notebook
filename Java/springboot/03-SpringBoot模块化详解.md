---
tags: [Java, SpringBoot, SpringBoot4, 模块化, 框架]
创建日期: 2026-08-07
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# Spring Boot 4模块化详解

## 📋 总纲

1. 背景:为什么模块化(单体 autoconfigure 的问题)
2. 核心变化:一个 jar → 一组模块
3. Starter 变化:改名与新增
4. 收益分析:启动/构建/正确性三层面
5. 与 SB3 对比:判断机制没删,候选集变小
6. 迁移指南:从 SB3 到 SB4
7. 面试追问 Q&A
8. 参考

---

## 1. 背景:为什么模块化

**触发点**:`spring-boot-autoconfigure` 单体 jar 持续膨胀。

| 版本 | autoconfigure jar 大小 | 状态 |
|---|---|---|
| SB 1.0 (2014) | 182 KiB | 支持技术少,很轻 |
| SB 3.5 | **2 MiB** | 支持几十种技术,全塞一个 jar |

**问题**:
- 应用只用了 3 种技术,却要把 2MiB 的 autoconfigure 全拉进 classpath
- IDE 补全提示一堆用不到的类,心智负担大
- 启动时自动装配要扫描全部候选类再逐个判断
- 依赖传递面大,冲突概率高

官方博客《Modularizing Spring Boot》(2025-10-28)宣布:SB4 对自动装配的**打包、交付、消费方式**做根本性改变。

---

## 2. 核心变化:一个 jar → 一组模块

**SB4 不再有单体 `spring-boot-autoconfigure` jar**,拆分为多个小且聚焦的模块:

- 每个技术一个独立模块,如 `spring-boot-webmvc`、`spring-boot-data-jpa`、`spring-boot-jdbc`、`spring-boot-cache`、`spring-boot-webclient`、`spring-boot-flyway`
- 每个模块**包含自己的自动配置代码**
- 包名变更:模块以 `org.springframework.boot.<module>` 开头

**关键机制变化**:

```
SB3: 引 starter-web → 拉进整个 autoconfigure(2MiB)
     → 启动时 @ConditionalOnClass 对全部技术逐个判断 → 筛出匹配的

SB4: 引 starter-webmvc → 只拉 spring-boot-webmvc 模块
     → 其他技术(redis/kafka/flyway...)不在 classpath,无需判断
```

> ⚠️ **精确理解**:`@ConditionalOnXxx` 判断机制**没有删**,变的是**候选集**——从"全部技术"变成"你显式引入的模块"。以前是"从 50 个里挑 3 个",现在是"只有 3 个,不用挑"。

---

## 3. Starter 变化:改名与新增

### 3.1 改名的 Starter

| 旧 Starter (SB3) | 新 Starter (SB4) |
|---|---|
| `spring-boot-starter-web` | `spring-boot-starter-webmvc` |
| `spring-boot-starter-aop` | `spring-boot-starter-aspectj` |
| `spring-boot-starter-web-services` | `spring-boot-starter-webservices` |
| `spring-boot-starter-oauth2-authorization-server` | `spring-boot-starter-security-oauth2-authorization-server` |
| `spring-boot-starter-oauth2-client` | `spring-boot-starter-security-oauth2-client` |
| `spring-boot-starter-oauth2-resource-server` | `spring-boot-starter-security-oauth2-resource-server` |

### 3.2 新增 Starter(以前没有独立 starter 的技术)

| 技术 | Main 依赖 | Test 依赖 |
|---|---|---|
| Spring Web MVC | `spring-boot-starter-webmvc` | `spring-boot-starter-webmvc-test` |
| RestClient / RestTemplate | `spring-boot-starter-restclient` | `spring-boot-starter-restclient-test` |
| Flyway | `spring-boot-starter-flyway` | `spring-boot-starter-flyway-test` |
| Liquibase | `spring-boot-starter-liquibase` | — |
| Kafka | `spring-boot-starter-kafka` | — |
| Jetty | `spring-boot-starter-jetty` | — |

> **SB3 行为**:Flyway 只要 jar 在 classpath 就自动装配;**SB4 行为**:必须显式引 starter 才有对应模块。

### 3.3 测试 Starter(每个主 starter 配套)

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-webmvc-test</artifactId>
  <scope>test</scope>
</dependency>
```

- 每个主 starter 都有对应的 `-test` starter
- 测试自动配置注解(如 `@AutoConfigureDataJdbc`)移到对应模块的 test jar(如 `spring-boot-data-jdbc-test`)

### 3.4 Classic Starter(过渡方案)

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-classic</artifactId>
</dependency>
```

- 保留的"老式聚合包":捆绑所有模块化自动配置(不含传递依赖)
- 用途:升级卡住时先用它跑起来,修好包导入后再迁移到精细模块
- **官方建议只是过渡,最终要迁移到模块化 starter**

---

## 4. 收益分析:三层面

### 4.1 构建/依赖层面

- 依赖解析更少,打包体积变小(部署镜像瘦身)
- **冲突面变小**:starter 连带引入的无关技术减少 → 依赖版本冲突概率下降
- 注意:版本仲裁机制(Maven)本身没变,是"战场变小了"

### 4.2 启动层面

- 自动装配候选集变小 → 扫描成本降低、类加载变少 → 启动更快
- **收益集中在启动和第一次加载过程**

### 4.3 正确性层面(收益最大,最容易被低估)

```
SB3 的坑: 只想用 WebClient,引了 webflux
         → 自动装配把整个 web 服务器启动了
         → 端口占用、内存多耗、行为意外  ← 运行时事故

SB4: 模块独立 → 用 WebClient 就只装 spring-boot-webclient
     → "意外启动"的运行时事故从根上消失
```

- 不再需要 `SpringApplication.setWebApplicationType(WebApplicationType.NONE)` 这种 hack
- 模块边界成为契约,而不是软约定
- 新用例:Micrometer 指标可独立于 Actuator 使用

> **运行时性能收益有限**:JVM 本来就是懒加载,SB3 时代没用到的类也不会被加载,不占运行时内存;自动装配是一次性动作,运行时请求路径不受影响。模块化解决的是"工程卫生"(正确性),不是"运行时效率"。

---

## 5. 与 SB3 对比速查

| 维度 | SB3 | SB4 |
|---|---|---|
| autoconfigure 打包 | 单 jar 2MiB | 每技术独立模块 |
| 自动装配判断 | @ConditionalOnClass 全量候选 | 同机制,候选集=显式引入的模块 |
| starter-web | `spring-boot-starter-web` | `spring-boot-starter-webmvc` |
| Flyway 装配 | jar 在就自动装配 | 必须显式引 starter |
| 意外装配(WebClient 触发 web server) | 会发生 | 不会(模块独立) |
| IDE 补全 | 一堆用不到的类 | 只显示实际引入模块 |
| 测试支持 | 单 test-autoconfigure jar | 每模块独立 -test jar |
| 过渡方案 | — | `spring-boot-starter-classic` |

---

## 6. 迁移指南:从 SB3 到 SB4

### 6.1 步骤

1. **精化主 starter 依赖**:改名(web→webmvc)、给以前没 starter 的技术(Flyway/Kafka 等)补 starter
2. **加 test starter**:每个主 starter 配 `-test` 到 test scope
3. **改手动/自定义配置**:自定义 starter 或直接依赖 autoconfigure 的,换成新模块依赖;包名 `org.springframework.boot.<module>` 前缀变了,import 要改
4. **审查自定义 starter**:不建议同一 artifact 同时支持 SB3 和 SB4(包名重构过)

### 6.2 自动迁移工具

- **OpenRewrite 配方**:`MigrateToModularStarters`(Community Edition)
  - 按代码里的包引用自动检测技术使用情况
  - 自动添加对应的 SB4 starter 依赖
  - 高阶 starter(如 data-jpa)传递包含低阶(如 jdbc),只加最高级

### 6.3 升级踩坑(社区反馈)

- 改了版本后功能"莫名缺失" → 多半是漏引了对应模块 starter(SB3 时 jar 在就自动装配,SB4 必须显式)
- 测试报错找不到 `@AutoConfigureXxx` → 需要加对应 `-test` starter
- 编译报包不存在 → 包名已改为 `org.springframework.boot.<module>` 前缀

---

## 7. 面试追问 Q&A

### 7.1 Spring Boot 4 模块化改了什么?

答:把单体 `spring-boot-autoconfigure` jar(2MiB)拆分为每个技术一个独立模块,每个模块含自己的自动配置代码。每个技术有独立 starter 和配套 test starter。web starter 改名为 webmvc,Flyway 等以前没有 starter 的技术新增了 starter。

### 7.2 模块化后自动装配判断减少了吗?

答:判断机制(@ConditionalOnXxx)没删,变的是候选集。SB3 是所有技术的自动配置类都在 classpath,启动时逐个判断;SB4 只有显式引入的模块在 classpath,没引入的技术连候选都不是。准确说:判断逻辑不变,候选从"全部技术"变成"显式引入的模块"。

### 7.3 模块化最大的收益是什么?

答:分三层——构建层(依赖少、打包小、冲突面小)、启动层(扫描成本低、启动快)、正确性层(消除意外自动装配,如引 WebClient 不再触发整个 web server)。其中正确性收益最大,解决的是运行时事故而非性能。

### 7.4 模块化对运行时性能有提升吗?

答:有限。JVM 懒加载意味着 SB3 时代没用到的类本来就不会被加载;自动装配是一次性启动动作,不影响运行时请求路径。收益集中在构建和启动阶段。

### 7.5 SB3 项目升 SB4 要注意什么?

答:① starter 改名(web→webmvc);② 以前靠"jar 在就自动装配"的技术(Flyway 等)要显式加 starter;③ 每个主 starter 配 -test 测试 starter;④ 自定义 starter 的包名 import 要改;⑤ 可以用 OpenRewrite 自动迁移,或用 starter-classic 过渡。

---

## 8. 参考

- 官方博客:《Modularizing Spring Boot》(2025-10-28): https://spring.io/blog/2025/10/28/modularizing-spring-boot/
- 官方迁移指南: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide
- OpenRewrite 迁移配方: https://docs.openrewrite.org/recipes/java/spring/boot4/migratetomodularstarters-community-edition
- 关联笔记:[01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)(自动装配机制,模块化改的是候选集)、[02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)、[00-SpringBoot体系总览](00-SpringBoot体系总览.md)、**Java Agent与字节码增强详解**（见知识库）(自动装配底层原理)、**JVM调优实战**（见知识库）(启动优化相关)
