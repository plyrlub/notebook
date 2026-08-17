---
tags: [定时任务, Quartz, 任务调度, cron, Java, Spring]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/定时任务）
归属: 01-学习/Java/框架/定时任务
---

# 01-Quartz详解

> 版本基线：Quartz 2.3.x（Java 最老牌的调度库，2009 年起稳定）
> 受众：Java 后端开发，想理解 Spring @Scheduled 的底层（Spring 内置调度就是基于 Quartz 思路），或在单应用内做复杂调度。默认你懂 cron 表达式和 Spring 基本用法。
> 关联笔记：[00-定时任务框架选型总览](00-定时任务框架选型总览.md)、[02-XXL-Job详解](02-XXL-Job详解.md)

## 📋 总纲

- 1. Quartz 是什么：定位与核心概念
- 2. 三大核心组件：Scheduler / Job / Trigger
- 3. 两种 Trigger：CronTrigger 与 SimpleTrigger
- 4. JobStore：内存 vs JDBC
- 5. 与 Spring 集成
- 6. 集群模式与局限
- 7. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 Quartz 的四大核心概念（Scheduler/Job/Trigger/JobDetail）
2. 用 CronTrigger 和 SimpleTrigger 声明任务
3. 区分 RAMJobStore 与 JDBCJobStore 的适用场景
4. 在 Spring Boot 中集成 Quartz 并动态管理任务
5. 说清 Quartz 集群方案的问题，知道何时该换框架

## 前置知识

- [00-定时任务框架选型总览](00-定时任务框架选型总览.md)——Quartz 在四大框架中的定位
- 需掌握：cron 表达式、Spring Boot 基础

---

## 1. Quartz 是什么：定位与核心概念

**一句话记忆**：Quartz 是一个**嵌入应用内部的 Java 调度库**，把"到什么时间干什么事"拆成 Job（干什么）和 Trigger（什么时间），由 Scheduler（调度器）统一执行。

| 概念 | 作用 | 类比 |
|---|---|---|
| **Scheduler** | 调度器：管理所有任务，是 Quartz 的门面 | 闹钟管理员 |
| **Job** | 任务逻辑：要执行的业务代码 | 闹钟响后做的事 |
| **JobDetail** | 任务描述：Job 的"简历"（绑定哪个类、传什么参数） | 工作描述 |
| **Trigger** | 触发器：什么时候执行、执行几次 | 闹钟设置 |
| **JobStore** | 任务存储：任务和触发器存在哪 | 备忘录 |

> 💡 **记忆锚点**：**Scheduler 拿着 JobDetail（简历）和 Trigger（闹钟设置），到点调用 Job（干活）**。

---

## 2. 三大核心组件

### 2.1 Job 与 JobDetail

```java
// 1. 实现 Job 接口
public class MyJob implements Job {
    @Override
    public void execute(JobExecutionContext context) {
        String param = context.getMergedJobDataMap().getString("param");
        System.out.println("执行任务: " + param);
    }
}

// 2. 创建 JobDetail(绑定 Job 类 + 参数)
JobDetail job = JobBuilder.newJob(MyJob.class)
        .withIdentity("myJob", "group1")
        .usingJobData("param", "hello")
        .build();
```

**关键**：`Job` 实例由 Quartz 每次执行时**重新创建**（new 一个），所以 Job 类内部**不能持有状态**，状态要通过 `JobDataMap` 传。

### 2.2 Scheduler 与 Trigger

```java
// 3. 创建调度器
Scheduler scheduler = StdSchedulerFactory.getDefaultScheduler();
scheduler.start();

// 4. 创建触发器
Trigger trigger = TriggerBuilder.newTrigger()
        .withIdentity("myTrigger", "group1")
        .withSchedule(CronScheduleBuilder.cronSchedule("0 0/5 * * * ?"))  // 每5分钟
        .build();

// 5. 绑定并启动
scheduler.scheduleJob(job, trigger);
```

**JobKey 身份**：任务用 `(name, group)` 唯一标识，group 用于逻辑分组。

---

## 3. 两种 Trigger

### 3.1 CronTrigger（cron 表达式）

适合"固定时间点"的调度（每天几点、每周几）：

```java
CronScheduleBuilder.cronSchedule("0 0 2 * * ?")      // 每天凌晨2点
CronScheduleBuilder.cronSchedule("0 0 9-18 * * MON-FRI")  // 工作日9-18点每小时
```

Quartz cron 与 Linux cron 差异：Quartz 是 **7 位**（秒 分 时 日 月 周 年[可选]），比 Linux 的 5 位多"秒"位，且 `?` 表示不指定（日和周互斥）。

| 位置 | 含义 | 允许值 |
|---|---|---|
| 1 | 秒 | 0-59 |
| 2 | 分 | 0-59 |
| 3 | 时 | 0-23 |
| 4 | 日 | 1-31 |
| 5 | 月 | 1-12 |
| 6 | 周 | 1-7 或 SUN-SAT |
| 7 | 年 | 可选 |

### 3.2 SimpleTrigger（固定间隔）

适合"固定频率"（每 N 毫秒/秒执行一次）：

```java
Trigger trigger = TriggerBuilder.newTrigger()
        .startNow()
        .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                .withIntervalInSeconds(10)    // 每10秒
                .repeatForever())             // 无限重复
        .build();
```

| 维度 | CronTrigger | SimpleTrigger |
|---|---|---|
| 适用 | 固定时间点（每天2点） | 固定间隔（每10秒） |
| 表达能力 | 强（cron 全场景） | 弱（仅间隔） |
| 错过补偿 | 不补（错过就错过） | 可配置 misfire 策略 |

---

## 4. JobStore：内存 vs JDBC

| 维度 | RAMJobStore | JDBCJobStore |
|---|---|---|
| 存储位置 | JVM 内存 | 数据库表 |
| 持久化 | ❌ 重启丢失 | ✅ 重启恢复 |
| 适用 | 单机、可丢任务 | 需要持久化/集群 |
| 性能 | 快 | 较慢（DB 读写） |
| 依赖 | 无 | 数据库 + 建表脚本 |

**JDBCJobStore 配置**：

```properties
org.quartz.jobStore.class=org.quartz.impl.jdbcjobstore.JobStoreTX
org.quartz.jobStore.driverDelegateClass=org.quartz.impl.jdbcjobstore.StdJDBCDelegate
org.quartz.jobStore.dataSource=qzDS
org.quartz.jobStore.tablePrefix=QRTZ_
```

数据库需要执行 Quartz 提供的 `tables_xxx.sql` 建表脚本（11 张表：QRTZ_JOB_DETAILS、QRTZ_TRIGGERS、QRTZ_CRON_TRIGGERS 等）。

---

## 5. 与 Spring 集成

Spring Boot 集成 Quartz（`spring-boot-starter-quartz`）：

```java
// 配置类:定义 JobDetail 和 Trigger Bean
@Configuration
public class QuartzConfig {

    @Bean
    public JobDetail jobDetail() {
        return JobBuilder.newJob(MyJob.class)
                .withIdentity("myJob")
                .storeDurably()   // 无触发器也能存
                .build();
    }

    @Bean
    public Trigger trigger(JobDetail jobDetail) {
        return TriggerBuilder.newTrigger()
                .forJob(jobDetail)
                .withSchedule(CronScheduleBuilder.cronSchedule("0 0/5 * * * ?"))
                .build();
    }
}
```

> ⚠️ **注意**：Spring Boot 默认 `spring.quartz.auto-startup=true`；多数据源/集群场景需配置 `spring.quartz.job-store-type=jdbc`。Spring 的 `@Scheduled` 是简化版（只有 cron 思路，无 JobDetail/Trigger 概念），复杂调度（动态改时间、暂停恢复）必须上 Quartz。

---

## 6. 集群模式与局限

### 6.1 集群原理

多实例共享同一个数据库（JDBCJobStore），Quartz 通过**数据库锁**（QRTZ_LOCKS 表，`SELECT ... FOR UPDATE`）保证同一时刻只有一个节点执行任务。

### 6.2 集群的痛点

| 问题 | 说明 |
|---|---|
| **锁竞争** | 任务多时数据库锁成为瓶颈，调度延迟增大 |
| **重复执行风险** | 节点时钟不同步/网络抖动可能重复触发（Quartz 2.x 已知问题） |
| **无管理界面** | 改任务要改代码或数据库，运维不友好 |
| **无失败重试/告警** | 任务失败只记日志，没有通知机制 |

**结论**：Quartz 集群适合**少量任务**的持久化场景；任务量大、要界面管理、要告警 → 换 XXL-Job/PowerJob（见 [00-定时任务框架选型总览](00-定时任务框架选型总览.md)）。

---

## 7. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #Q1 | Job 类里持有成员变量状态 | 每次执行新实例，状态丢失 | 状态放 JobDataMap 或外部存储 |
| #Q2 | 集群节点时钟不一致 | 任务重复执行 | NTP 同步时钟；或换调度框架 |
| #Q3 | 任务错过调度时间 | misfire 不处理，任务丢失 | 配置 misfire 策略（withMisfireHandlingInstructionIgnoreMisfires） |
| #Q4 | 用 @Scheduled 以为支持动态管理 | 无法暂停/改时间 | 复杂调度用 Quartz API |
| #Q5 | JDBCJobStore 没建表 | 启动报错找不到表 | 执行 tables_xxx.sql |
| #Q6 | 任务执行时间 > 间隔 | 下次触发被阻塞/重叠 | 用 @DisallowConcurrentExecution 注解 |

## 小结

- Quartz = 嵌入应用的调度库，Scheduler + Job + Trigger 三大概念
- CronTrigger（固定时间点）vs SimpleTrigger（固定间隔）
- RAMJobStore 内存快、JDBCJobStore 可持久化可集群
- 集群靠数据库锁，任务多时性能差 → 换平台型框架
- Spring @Scheduled 是简化版，动态管理要上 Quartz

## 下一篇

[02-XXL-Job详解](02-XXL-Job详解.md)——分布式调度平台，中小企业主流方案

## 参考资料

- [Quartz 官方文档](http://www.quartz-scheduler.org/documentation/)，查询日期：2026-08-09
- [Spring Boot Quartz 集成文档](https://docs.spring.io/spring-boot/reference/io/quartz.html)，查询日期：2026-08-09
