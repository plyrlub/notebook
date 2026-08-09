---
tags: [分布式, ZooKeeper, 协调服务, 一致性, 总览]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/分布式/Zookeeper）
归属: 01-学习/分布式/Zookeeper
来源: wolai 笔记转存 + 网络查证补充
---

# ZooKeeper 总览

> 本文是 **ZooKeeper 系列** 的总览与入口。ZooKeeper 是分布式协调服务的经典基石（Kafka/HBase/Dubbo 的底层依赖），本系列按「基础 → 机制 → 协议 → 客户端 → 运维」组织，共 9 篇。
> 前置知识：[00-分布式基础总览](../00-分布式基础总览.md)
> 关联笔记：[03-分布式锁原理详解](../03-分布式锁原理详解.md)（Redis 锁对照）、**04-Apache Dubbo详解**（见知识库）、**02-XXL-Job详解**（见知识库）（注册中心）

## 版本基线

- 当前稳定版 **3.8.6**，最新发布 **3.9.5**（2026-08 查证）
- 客户端兼容性：3.5+ 客户端与 3.8.x 服务器完全兼容；3.8.x 客户端兼容 3.5/3.6/3.7 服务器
- 本文示例以 3.6+（Watch 持久监听、动态 reconfig、多网络端口）为主

## 受众声明

面向已了解分布式基础（[00-分布式基础总览](../00-分布式基础总览.md)）、了解 Linux/Java 的读者。假设已懂：TCP/IP、Java、集群概念。以下术语必须讲清：znode、Session、Watch、Quorum（过半）、Leader/Follower/Observer。

## 学习目标

学完本系列你能：
1. 说清 **ZooKeeper 是什么**、解决什么问题、适合存什么数据
2. 独立**安装部署**单机与 Docker Compose 集群，看懂 zoo.cfg 核心配置
3. 说清 **znode 四种类型、Session、Watch** 三大基础机制
4. 理解**集群角色与 Leader 选举、ZAB 协议**如何保证数据一致性
5. 掌握 **Java API 与 Curator** 客户端，能实现分布式锁/选举等协同场景
6. 配置 **ACL 权限**、四字命令监控、日志清理等运维技能
7. 知道 **ZooKeeper 与 etcd/Consul/Nacos** 的选型差异

## 前置知识

- [00-分布式基础总览](../00-分布式基础总览.md)——一致性、CAP 等分布式基础
- [03-分布式锁原理详解](../03-分布式锁原理详解.md)——分布式锁对照（ZooKeeper 锁 vs Redis 锁）
- 需掌握：Java 基础、Linux 基础命令

---

## 📋 总览

| 篇目 | 内容 | 说明 |
|---|---|---|
| 00 | 本页（总览） | 定位、安装部署、配置、选型、学习路线 |
| 01 | [01-数据模型与节点详解](01-数据模型与节点详解.md) | znode 类型/版本/属性、data tree、常用 shell 命令 |
| 02 | [02-会话与Watch机制](02-会话与Watch机制.md) | Session 状态机、Watch 原理与持久监听 ★ |
| 03 | [03-集群与Leader选举](03-集群与Leader选举.md) | 角色分工、选举算法、数据同步、启动原理 ★ |
| 04 | [04-ZAB协议与一致性](04-ZAB协议与一致性.md) | ZAB 崩溃恢复/原子广播、Paxos/Raft/2PC 对比 ★ |
| 05 | [05-ACL权限控制](05-ACL权限控制.md) | scheme/权限位、命令行与代码配置 |
| 06 | [06-Java客户端API详解](06-Java客户端API详解.md) | ZooKeeper API、Watcher、示例代码 |
| 07 | [07-Curator详解](07-Curator详解.md) | 高级客户端、分布式锁/选举/缓存 ★ |
| 08 | [08-运维与监控专题](08-运维与监控专题.md) | 四字命令、日志清理、动态配置、Jute、zkClient/Python |
| 09 | [09-应用场景与分布式协同](09-应用场景与分布式协同.md) | Master 选举、服务发现、分布式锁、ID 生成器、负载均衡 |

## 1. ZooKeeper 是什么

**一句话记忆**：ZooKeeper 是一个开源的**分布式协同服务系统**，把"复杂且易出错的分布式协同"封装成**高效可靠的原语集**，以简单接口暴露给用户。

**生活类比**：动物园管理员（ZooKeeper）——大象（应用）之间需要互相同步信息（谁是老大、谁在哪个笼子），管理员负责登记和广播，动物们不用自己喊话。

**为什么需要它**：分布式系统的协调本质是"让每个节点的信息同步和共享"，这依赖服务进程间通信，方式只有两种：
1. **通过网络进行信息共享**
2. **通过共享存储**（ZooKeeper 走的就是这条——大家读写同一棵数据树）

**典型应用场景**：配置管理、DNS 服务、组成员管理（集群管理）、各种分布式锁、Leader 选举。

> 💡 **关键定位**：ZooKeeper 适合存储**存储和协同相关的关键数据**（几百 MB 级），**不适合大数据量存储**——所有数据常驻内存。

## 2. 总体架构

```
应用（客户端）
   │  zk 客户端库（会话、心跳、Watcher）
   ▼
ZooKeeper 集群
   ├── standalone 模式：单节点
   └── quorum 模式：多节点（Leader/Follower/Observer）
```

- 应用通过 **zk 客户端库** 与集群交互
- 客户端与集群中某个节点创建 **Session**，可主动关闭；节点在 timeout 内没收到客户端消息也会关闭会话
- 客户端库发现连接的节点出错，**自动与其他节点建立连接**（会话仍有效，见 [02-会话与Watch机制](02-会话与Watch机制.md)）

## 3. 安装部署

### 3.1 目录结构

![ZK目录结构](00-assets/ZK目录结构.png)

### 3.2 核心配置（zoo.cfg）

```properties
# 基本配置（必须）
tickTime=2000        # 心跳间隔 ms（client-server / server-server 之间）
initLimit=10         # Follower 启动连 Leader 最多容忍心跳数（同步超时 = initLimit×tickTime）
syncLimit=5          # Follower 与 Leader 请求/应答容忍心跳数（数据同步延迟超限会被剔除）
dataDir=/tmp/zookeeper   # 快照目录 + myid 文件（不要用 /tmp 生产）
clientPort=2181      # 客户端端口（SSL 用 2281）

# 集群配置（quorum 模式）
server.1=host1:2888:3888   # id=myid；2888 集群通信端口；3888 选举端口
server.2=host2:2888:3888
server.3=host3:2888:3888

# 自动清理
autopurge.snapRetainCount=3    # 保留快照数（默认3，最小3）
autopurge.purgeInterval=0      # 清理频率（小时），0 表示不开启

# 运维
dataLogDir=/tmp/dataLog    # 事务日志目录——必须与 dataDir 分盘（独立 SSD）
globalOutstandingLimit=1000  # 客户端最大请求队列（限流防 OOM）
maxClientCnxns=60          # 同一客户端 IP 最大并发连接（防 DDoS）
maxSessionTimeout / minSessionTimeout  # 会话超时上下限
snapCount=100000           # 每写多少次事务日志做一次快照
```

> ⚠️ 3.6.0+ 只能使用 FastLeaderElection，升级时 `electionAlg` 要么指定为 3、要么注释掉（旧的 UDP 算法 1/2 已废弃）。

### 3.3 Docker Compose 集群（3.5+ 镜像）

```yaml
version: '3.6'
services:
    zk1:
        image: zookeeper:3.6
        restart: always
        hostname: zk1
        container_name: zk1
        ports: ["2181:2181"]
        environment:
         ZOO_MY_ID: 1
         ZOO_SERVERS: server.1=0.0.0.0:2888:3888;2181 server.2=zk2:2888:3888;2181 server.3=zk3:2888:3888;2181
    zk2:
        image: zookeeper:3.6
        restart: always
        hostname: zk2
        container_name: zk2
        ports: ["2182:2181"]
        environment:
         ZOO_MY_ID: 2
         ZOO_SERVERS: server.1=zk1:2888:3888;2181 server.2=0.0.0.0:2888:3888;2181 server.3=zk3:2888:3888;2181
    zk3:
        image: zookeeper:3.6
        restart: always
        hostname: zk3
        container_name: zk3
        ports: ["2183:2181"]
        environment:
         ZOO_MY_ID: 3
         ZOO_SERVERS: server.1=zk1:2888:3888;2181 server.2=zk2:2888:3888;2181 server.3=0.0.0.0:2888:3888;2181
```

- `ZOO_MY_ID`：1-255 整数，集群唯一（写入 dataDir/myid）
- 启动：`docker-compose up`；访问：`zkCli.sh -server localhost:2181,localhost:2182,localhost:2183`

## 4. 生产环境建议

1. **独占服务器**：给 ZK 分配独立机器，事务日志要独立存储设备
2. **内存**：data tree 常驻内存，一般场景 8G 足够
3. **CPU**：ZK 对 CPU 消耗不高，独占一个双核 CPU 即可
4. **存储**：写延迟直接影响事务提交效率，`dataLogDir` 建议独占 **SSD**；事务日志目录与数据目录分盘
5. **日志**：`$ZK_HOME/conf/log4j.properties`

## 5. ZooKeeper vs etcd vs Consul vs Nacos ★选型

> 网络查证补充（2026-08）。ZooKeeper 是协调领域经典基石，但**云原生时代选型已分化**——不是所有场景都该用 ZK。

| 维度 | ZooKeeper | etcd | Consul | Nacos |
|---|---|---|---|---|
| 一致性算法 | ZAB | Raft | Raft | Raft（AP 模式 Distro） |
| 数据模型 | 树形 znode | KV（MVCC） | KV | KV + 配置 |
| 语言 | Java | Go | Go | Java |
| 存储 | 全内存（几百 MB 级） | bbolt 磁盘（几 GB 级） | 内存+磁盘 | 内存+磁盘 |
| 生态代表 | Kafka/HBase/Dubbo | **Kubernetes** | 服务网格/网络治理 | Spring Cloud Alibaba |
| 动态配置 | reconfig 3.5+ | 天然支持 | 天然支持 | 一体化 |
| 云原生契合度 | 低（重客户端、运维重） | ★★★★ | ★★★ | ★★★ |

**选型结论**：
- 云原生/K8s 场景 → **etcd**（K8s 标配，无需自建）
- 微服务注册配置一体化 → **Nacos**（国内 Spring Cloud 生态主流）
- 服务网格/多数据中心 → **Consul**
- Hadoop 系（Kafka/HBase）或存量 Dubbo → **ZooKeeper** 仍是事实标准，**值得学但不一定值得新项目选**

## 6. 学习路线建议

1. 先读 [01-数据模型与节点详解](01-数据模型与节点详解.md)（最基础：znode + 命令）
2. 再读 [02-会话与Watch机制](02-会话与Watch机制.md) + [03-集群与Leader选举](03-集群与Leader选举.md)（机制层）
3. 再读 [04-ZAB协议与一致性](04-ZAB协议与一致性.md)（原理层，面试重点）
4. 最后按需读客户端篇（[06-Java客户端API详解](06-Java客户端API详解.md) / [07-Curator详解](07-Curator详解.md)）与运维篇（[08-运维与监控专题](08-运维与监控专题.md)）
5. 场景理解看 [09-应用场景与分布式协同](09-应用场景与分布式协同.md)（可作导读，先看"能干什么"再学机制）

## 最佳实践

1. 生产环境 **dataLogDir 与 dataDir 必须分盘**，事务日志落盘是提交瓶颈
2. 集群节点数**奇数**（3/5），过半可用即可服务，容忍 N/2-1 台故障
3. 客户端务必设置**合理的 Session 超时**并用 Curator 这类带重连的客户端
4. ZK 数据**常驻内存**，只存协调数据（配置、元数据），不存业务大数据
5. 开启 `autopurge` 自动清理，避免快照/日志撑爆磁盘

## 常见踩坑

- **myid 缺失/不唯一**：集群启动抛异常，日志可见详情
- **dataDir 用 /tmp**：重启丢数据（配置注释里官方都提醒了）
- **事务日志与数据目录同盘**：写延迟互相拖累，提交变慢
- **节点数偶数**：如 2 台，故障 1 台就失去过半，集群不可用
- **旧配置 electionAlg=1/2**：3.6+ 启动失败，必须改 3 或注释

## 小结

1. ZooKeeper = 分布式**协同服务**，把复杂协同封装成原语集，数据常驻内存，适合协调数据不适合大数据
2. 架构：客户端库 + standalone/quorum 集群；Session 会话 + Watch 通知是两大核心机制
3. 部署要点：zoo.cfg 核心 4 项 + 集群 server.N 配置 + Docker Compose 一键起
4. 生产铁律：事务日志独立 SSD、奇数节点、自动清理
5. 选型：**K8s 用 etcd、微服务用 Nacos、Hadoop 系用 ZK**——ZK 值得深学但新项目未必首选

## 下一篇

- 下一篇：[01-数据模型与节点详解](01-数据模型与节点详解.md)

---
*创建于 2026-08-09（wolai 笔记转存 + 网络查证补充）*
