---
tags: [定时任务, Elastic-Job, 任务调度, 分布式, ZooKeeper, 分片, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/定时任务）
归属: 01-学习/Java/框架/定时任务
---

# 03-Elastic-Job详解

> 版本基线：ElasticJob 3.x（2020 年捐赠 Apache，成为 ShardingSphere 子项目；2026-08 查证更新放缓，UI 项目冷清）
> 受众：Java 后端开发，有大数据量任务需要分片处理，且已有/可接受 ZooKeeper 基础设施。默认你懂 cron 和分布式协调基本概念。
> 关联笔记：[00-定时任务框架选型总览](00-定时任务框架选型总览.md)、[02-XXL-Job详解](02-XXL-Job详解.md)

## 📋 总纲

- 1. Elastic-Job 是什么：定位与架构
- 2. 核心概念：Job / 分片 / ZooKeeper
- 3. 分片机制（核心特性）★
- 4. 快速上手
- 5. 运维与现状
- 6. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 Elastic-Job 去中心化架构与 ZK 的作用
2. 理解分片模型：分片总数、分片项与节点关系
3. 写出一个分片任务（SimpleJob + 分片参数）
4. 说清 Elastic-Job 的优缺点与当前维护现状
5. 判断项目是否适合用 Elastic-Job

## 前置知识

- [00-定时任务框架选型总览](00-定时任务框架选型总览.md)——Elastic-Job 在四大框架中的定位
- [02-XXL-Job详解](02-XXL-Job详解.md)——对照理解中心化 vs 去中心化差异
- 需掌握：cron 表达式、ZooKeeper 基本概念（节点/选举）

---

## 1. Elastic-Job 是什么：定位与架构

**一句话记忆**：Elastic-Job 是**去中心化的分布式调度框架**——没有独立调度中心，业务应用节点地位平等，通过 ZooKeeper 协调，谁跑哪个任务、数据分几片由 ZK 统一分配。

```
业务应用节点（内嵌 Elastic-Job）
   ┌──────┐   ┌──────┐   ┌──────┐
   │ 节点A │   │ 节点B │   │ 节点C │
   └──┬───┘   └──┬───┘   └──┬───┘
      └─────────┴─────────┘
              │
        ZooKeeper（协调/选举/分片）
```

**核心特点**：

- **去中心化**：无调度中心单点，节点宕机自动摘除、任务转移
- **分片能力强**：分片是设计核心，数据量大时按片切分
- **弹性伸缩**：加节点自动重分片，减节点自动补偿
- **基于 Quartz**：调度内核复用 Quartz（cron 触发）

---

## 2. 核心概念

| 概念 | 说明 |
|---|---|
| **Job** | 任务（SimpleJob / DataflowJob / ScriptJob） |
| **分片（Sharding）** | 把任务数据切成 N 片，各节点处理一片 |
| **分片项（ShardingItem）** | 每片的编号（0, 1, 2...） |
| **ZooKeeper** | 协调中心：节点注册、选举、分片分配、故障转移 |
| **JobRegistry** | 任务注册中心（基于 ZK） |

**Job 类型**：

| 类型 | 适用 |
|---|---|
| **SimpleJob** | 无状态任务，每片执行一次 |
| **DataflowJob** | 流式任务：抓取-处理循环（适合数据流） |
| **ScriptJob** | 执行脚本任务 |

---

## 3. 分片机制（核心特性）★

**分片流程**：

```
1. 配置任务分片总数(如 4 片)
2. 节点启动 → 注册到 ZK → 选举主节点
3. 主节点把 4 片分配给在线节点(2 节点 → 各 2 片)
4. 节点宕机 → ZK 感知 → 剩余节点重新分片(自动补偿)
```

```java
// 分片任务示例
public class MyShardingJob implements SimpleJob {

    @Override
    public void execute(ShardingContext context) {
        int shardingItem = context.getShardingItem();   // 当前分片项(0,1,2...)
        int shardingTotal = context.getShardingTotalCount(); // 总分片数

        // 按分片处理数据(如按订单ID取模)
        processByShard(shardingItem, shardingTotal);
    }
}
```

**分片 vs XXL-Job 广播差异**：

| 维度 | Elastic-Job 分片 | XXL-Job 分片广播 |
|---|---|---|
| 分配方式 | ZK 主节点智能分配（考虑节点负载） | 简单广播，各节点自取分片号 |
| 节点增减 | 自动重分片（弹性） | 需重跑或手动处理 |
| 编排粒度 | 每片独立调度 | 一次广播全部执行 |

> 💡 **记忆锚点**：**Elastic-Job 的分片是"智能管家分配家务"，XXL-Job 是"广播大家自己认领"**——前者适合节点常变的大数据场景，后者简单直接。

---

## 4. 快速上手

```xml
<dependency>
    <groupId>org.apache.shardingsphere.elasticjob</groupId>
    <artifactId>elasticjob-lite-core</artifactId>
    <version>3.0.4</version>
</dependency>
```

```java
// 配置任务(Spring Boot 风格)
@Configuration
public class ElasticJobConfig {

    @Bean
    public JobSimpleListener jobListener() {
        return new JobSimpleListener();  // 自定义监听
    }

    @Bean(initMethod = "init")
    public JobScheduler jobScheduler() {
        // 注册中心(ZK)
        CoordinatorRegistryCenter regCenter = new ZookeeperRegistryCenter(
                new ZookeeperConfiguration("localhost:2181", "elastic-job"));
        regCenter.init();

        // 任务配置:分片 4 片
        JobConfiguration jobConfig = JobConfiguration.newBuilder("myShardingJob", 4)
                .cron("0 0/5 * * * ?")
                .build();

        return new JobScheduler(regCenter, new MyShardingJob(), jobConfig);
    }
}
```

**前置**：需要可用的 ZooKeeper 集群（生产建议 3 节点）。

---

## 5. 运维与现状

### 5.1 运维注意

- **ZK 是必须依赖**：ZK 集群本身要维护（监控、备份、网络）
- **无成熟管理界面**：ElasticJob-UI 项目简陋（GitHub 约 169 star），任务管理主要靠配置和 ZK 观察
- **与框架绑定**：Lite 版嵌入应用；还有 ElasticJob-Cloud 版（Mesos 调度，基本没人在用）

### 5.2 现状（2026-08 查证）

- 2020 年捐赠 Apache ShardingSphere 成为子项目
- **3.x 之后更新明显放缓**，UI/Cloud 部分基本停滞
- 社区主流推荐度下降：新项目多选 XXL-Job 或 PowerJob
- **仍然适合**：已有 ZK 基础设施、强分片需求、追求去中心化的场景

> ⚠️ **实事求是**：Elastic-Job 技术设计优秀（分片模型至今被借鉴），但**生态活跃度是短板**——选它要有"自己维护"的心理准备，新项目除非强分片+已有 ZK，否则优先 XXL-Job/PowerJob。

---

## 6. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #E1 | ZK 未部署/挂掉 | 任务不执行、节点注册失败 | 保证 ZK 集群高可用（3 节点） |
| #E2 | 分片总数改小 | 数据重复处理/遗漏 | 改分片数前评估，改后重跑 |
| #E3 | 任务处理慢于调度 | 任务堆积 | 调大分片数或优化处理逻辑 |
| #E4 | 无界面误以为有 | 找半天管理界面 | 任务管理靠 ZK + 配置，UI 简陋 |
| #E5 | 与 ShardingSphere 混淆 | 以为能分库分表 | Elastic-Job 只管任务分片，ShardingSphere 才管数据分片 |

## 小结

- Elastic-Job = 去中心化调度，ZK 协调，无单点
- **分片是核心**：ZK 智能分配分片，节点弹性伸缩自动重分片
- 三种 Job：SimpleJob / DataflowJob / ScriptJob
- 必须依赖 ZooKeeper，运维成本高
- **现状：已捐 Apache、更新放缓，新项目除非强分片+已有 ZK 否则不优先推荐**

## 下一篇

[04-PowerJob详解](04-PowerJob详解.md)——新一代分布式调度+计算框架

## 参考资料

- [Apache ShardingSphere ElasticJob](https://github.com/apache/shardingsphere-elasticjob)，查询日期：2026-08-09
- [ElasticJob 官方文档](https://shardingsphere.apache.org/elasticjob/)，查询日期：2026-08-09
