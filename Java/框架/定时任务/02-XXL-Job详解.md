---
tags: [定时任务, XXL-Job, 任务调度, 分布式, 调度中心, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/定时任务）
归属: 01-学习/Java/框架/定时任务
---

# 02-XXL-Job详解

> 版本基线：XXL-Job 2.5.x（2025.1 发布 v2.5.0，许雪里个人开源，国内中小企业最主流的分布式调度平台）
> 受众：Java 后端开发，微服务多实例部署，需要一个带界面、可管理、可告警的分布式定时任务方案。默认你懂 Spring Boot 和 cron。
> 关联笔记：[00-定时任务框架选型总览](00-定时任务框架选型总览.md)、[03-Elastic-Job详解](03-Elastic-Job详解.md)、[04-PowerJob详解](04-PowerJob详解.md)

## 📋 总纲

- 1. XXL-Job 是什么：定位与架构
- 2. 核心概念：调度中心 / 执行器 / 任务
- 3. 快速上手：部署调度中心 + 集成执行器
- 4. 任务类型与路由策略
- 5. 分片广播与动态分片参数
- 6. 调度与执行流程
- 7. 高可用设计
- 8. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 XXL-Job 的调度中心/执行器分离架构
2. 独立部署调度中心并集成 Spring Boot 执行器
3. 配置任务（cron、路由策略、失败重试）并理解各选项含义
4. 用分片广播实现大数据量任务的水平切分
5. 说清 XXL-Job 如何保证不重复执行与高可用
6. 指出 XXL-Job 的局限（高并发瓶颈、无工作流编排）

## 前置知识

- [00-定时任务框架选型总览](00-定时任务框架选型总览.md)——XXL-Job 在四大框架中的定位
- [01-Quartz详解](01-Quartz详解.md)——调度基础概念（cron/Trigger）对比
- 需掌握：Spring Boot 项目创建、cron 表达式

---

## 1. XXL-Job 是什么：定位与架构

**一句话记忆**：XXL-Job 是**中心化架构的分布式调度平台**——一个独立的"调度中心"网页管理所有任务，业务应用嵌入"执行器"接收指令干活。

```
┌─────────────────────────┐
│  调度中心 (xxl-job-admin) │  独立部署,网页管理任务
│  - 任务管理/日志/告警     │
└────────────┬────────────┘
             │ HTTP 下发任务
      ┌──────┴──────┐
      ▼             ▼
┌─────────┐    ┌─────────┐
│ 执行器A   │    │ 执行器B   │  业务应用内嵌,注册到中心
└─────────┘    └─────────┘
```

**为什么流行**：

- 开箱即用：调度中心打包成 jar 直接跑，执行器加依赖+注解即可
- 界面完善：任务 CRUD、日志查看、告警配置全有
- 轻量：不依赖 ZooKeeper 等外部组件，只依赖 MySQL
- 社区活跃：资料多、踩坑记录多

---

## 2. 核心概念

| 概念 | 说明 |
|---|---|
| **调度中心（Admin）** | 独立服务，管理任务、触发调度、存日志 |
| **执行器（Executor）** | 嵌入业务应用的组件，向中心注册，接收任务执行 |
| **任务（Job）** | 一个定时任务：cron + 执行器 + 处理逻辑 |
| **路由策略** | 多执行器时选哪个执行（轮询/随机/一致性哈希...） |
| **调度日志** | 每次触发/执行的完整记录 |

---

## 3. 快速上手

### 3.1 部署调度中心

```bash
# 1. 下载 xxl-job 源码, 执行 doc/db/tables_xxl_job.sql 建库
# 2. 修改 xxl-job-admin 配置(数据库连接)
# 3. 打包运行
mvn package
java -jar xxl-job-admin/target/xxl-job-admin-2.5.0.jar
# 访问 http://localhost:8080/xxl-job-admin  (默认 admin/123456)
```

### 3.2 集成执行器（Spring Boot）

```xml
<dependency>
    <groupId>com.xuxueli</groupId>
    <artifactId>xxl-job-core</artifactId>
    <version>2.5.0</version>
</dependency>
```

```java
// 配置类
@Configuration
public class XxlJobConfig {

    @Bean
    public XxlJobSpringExecutor xxlJobExecutor() {
        XxlJobSpringExecutor executor = new XxlJobSpringExecutor();
        executor.setAdminAddresses("http://localhost:8080/xxl-job-admin");
        executor.setAppname("demo-executor");        // 执行器名(与调度中心注册一致)
        executor.setPort(9999);                       // 执行器端口
        executor.setLogPath("/data/applogs/xxl-job/");
        return executor;
    }
}

// 任务处理器:方法上 @XxlJob 注解
@Component
public class DemoTask {

    @XxlJob("demoJobHandler")
    public void demoJobHandler() throws Exception {
        XxlJobHelper.log("任务执行中...");
        System.out.println("定时任务执行: " + System.currentTimeMillis());
        XxlJobHelper.handleSuccess("执行成功");
    }
}
```

**流程**：执行器启动 → 自动注册到调度中心 → 在调度中心"执行器管理"看到在线 → 新建任务选择该执行器 → 配置 cron → 启动任务。

---

## 4. 任务类型与路由策略

### 4.1 调度类型

| 类型 | 说明 |
|---|---|
| **Cron** | cron 表达式定时触发（最常用） |
| **固定速度** | 每 N 秒一次（不重叠执行） |
| **固定延迟** | 上次执行完后延迟 N 秒再执行 |
| **API 触发** | 通过接口手动/代码触发（配合工作流） |

### 4.2 路由策略（多执行器选型）

| 策略 | 行为 | 适用 |
|---|---|---|
| **第一个/最后一个** | 固定选一个 | 简单场景 |
| **轮询** | 依次轮流 | 负载均衡 |
| **随机** | 随机选 | 负载均衡 |
| **一致性哈希** | 按 JobId 哈希选固定节点 | 保证同一任务固定机器（利于本地缓存） |
| **故障转移** | 失败自动换下一个 | 高可用 |
| **分片广播** | 所有执行器都执行，各拿分片号 | 大数据量任务（见下） |

---

## 5. 分片广播与动态分片参数 ★

大数据量任务（如全量同步 1000 万数据），单台机器慢且危险 → 分片广播：

```java
@XxlJob("shardingJobHandler")
public void shardingJobHandler() {
    // 当前执行器分片信息
    int shardIndex = XxlJobHelper.getShardIndex();   // 当前分片号(0开始)
    int shardTotal = XxlJobHelper.getShardTotal();   // 总分片数(=执行器数量)

    // 示例:按 ID 取模分片处理 1..10000 的数据
    for (int i = 1; i <= 10000; i++) {
        if (i % shardTotal == shardIndex) {
            processData(i);   // 只处理属于自己的数据
        }
    }
}
```

**原理**：调度中心把任务广播给所有执行器，每个执行器拿到自己的 `shardIndex/shardTotal`，各自处理一部分数据。

> 💡 **记忆锚点**：**分片广播 = 任务复制 N 份，每份只处理 1/N**。数据按 `id % N == index` 划分，天然不重复不遗漏。

---

## 6. 调度与执行流程

```
1. 调度线程(Quartz)按 cron 触发 → 生成调度日志
2. 按路由策略选择执行器
3. HTTP 请求发送到执行器(嵌入业务应用)
4. 执行器线程池执行任务方法
5. 结果回传调度中心 → 更新日志/触发告警
```

**关键设计**：

- **调度与执行分离**：调度中心只负责"到点发指令"，执行在业务应用内 → 业务上下文（Spring Bean）可直接注入
- **线程池隔离**：每个执行器任务队列独立，任务阻塞不影响其他任务（可配置阻塞处理策略：单机串行/丢弃后续/覆盖之前）
- **失败重试**：可配置重试次数，失败后自动重试
- **超时控制**：可配置任务超时时间，超时标记失败

---

## 7. 高可用设计

| 层 | 方案 |
|---|---|
| **调度中心** | 多实例部署 + 共享 MySQL，Quartz 集群模式（数据库锁） |
| **执行器** | 多实例自动注册，路由策略选型 |
| **数据库** | MySQL 主从/高可用 |
| **任务幂等** | 调度中心每次触发生成唯一调度日志，执行器按 JobId+TriggerId 幂等处理 |

> ⚠️ **局限（实事求是）**：调度中心基于 Quartz + 数据库锁，**任务量大时调度有瓶颈**（万级任务/高频率调度会吃力）；**无原生工作流编排**（任务 A 完成后触发任务 B 需要自己实现或用 API 触发）。这两个场景看 [04-PowerJob详解](04-PowerJob详解.md)。

---

## 8. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #X1 | 执行器未注册 | 调度中心看不到执行器 | 检查 appname 一致、端口可达、admin 地址 |
| #X2 | 任务执行超时被标记失败 | 长任务被砍 | 调大超时时间或用异步任务 |
| #X3 | 阻塞策略理解错 | 任务堆积/丢失 | 按需选"单机串行/丢弃后续/覆盖之前" |
| #X4 | 分片任务没按 shard 处理 | 每台都全量处理 | 必须用 shardIndex/shardTotal 切分数据 |
| #X5 | 调度中心单点 | 中心挂了全停 | 中心多实例 + MySQL 高可用 |
| #X6 | 路由策略选了轮询但有状态任务 | 任务跑到不同机器状态丢失 | 用一致性哈希保证固定节点 |

## 小结

- XXL-Job = 中心化调度平台：调度中心(管理) + 执行器(业务内嵌)
- 部署简单：jar 跑中心 + 依赖注解集成执行器，界面全功能
- 路由策略 9 种，分片广播处理大数据量任务
- 高可用靠中心集群 + 执行器多实例 + 数据库
- 局限：调度中心基于 Quartz 数据库锁，高并发瓶颈；无工作流编排

## 下一篇

[03-Elastic-Job详解](03-Elastic-Job详解.md)——去中心化分片调度方案

## 参考资料

- [XXL-Job 官方文档](https://www.xuxueli.com/xxl-job/)，查询日期：2026-08-09
- [XXL-Job GitHub](https://github.com/xuxueli/xxl-job)，查询日期：2026-08-09
