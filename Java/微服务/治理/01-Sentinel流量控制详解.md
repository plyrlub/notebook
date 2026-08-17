---
tags: [Java, 微服务, Sentinel, 限流, 熔断, 降级, 流量治理, 高可用, 学习笔记]
创建日期: 2026-08-16
状态: ✅ 已归档（01-学习/Java/微服务/治理）
归属: 01-学习/Java/微服务/治理
---

# Sentinel 流量控制详解

> 阿里开源的**流量治理**组件（微服务架构「容错/流量防防护」核心）。不止熔断——还含**限流、流量整形、熔断降级、热点参数限流、系统自适应保护、授权黑白名单、集群流控**。
> 本文讲透：sentinel 核心概念与原理（滑动窗口/责任链）、**六大规则的使用**（⭐）、Dashboard 与规则持久化、Spring 集成、生产最佳实践。
> 前置：微服务架构基础（[00-微服务总览](../00-微服务总览.md)）、高可用理念（[00-分布式基础总览](../../../分布式/00-分布式基础总览.md)）。

## 📋 总纲

1. Sentinel 是什么：全链路流量治理
2. 核心概念：资源/规则/上下文
3. **核心原理（⭐）**：滑动窗口 + 责任链 SlotChain
4. **六大规则使用（⭐）**：流控/熔断/热点/系统/授权/集群
5. 流量整形：预热 / 匀速排队
6. **控制台 Dashboard + 规则持久化（⭐）**
7. Spring Cloud 集成实战
8. 生产最佳实践
9. 与 Hystrix / Resilience4j 对比选型
10. 面试高频 Q&A
11. 参考

---

## 1. Sentinel 是什么：全链路流量治理

**一句话**：Sentinel 是抗雪崩的**流量防护**组件——用「**资源**」维度统一管理，从**接口级**到**调用关系级**/参数级做限流熔断降级，达到"保护自己、不让故障扩散"。

**为什么需要**：微服务调用链路长，下游一慢/一挂会**线程堆积 → 耗尽本地线程池 → 服务不可用 → 层层放大成雪崩**。Sentinel 在客户端（调用方）做熔断限流，暂切断不稳定调用。

**Sentinel vs Hystrix 定位**：Sentinel 不止熔断，而是**全链路流量治理**（限流+熔断+系统保护+热点+授权+集群），Hystrix 只有熔断+少量限流。

```
应用请求 → ① FlowSlot限流 → ② DegradeSlot熔断 → ③ SystemSlot系统保护 → ④ 授权
            ↓ 命中规则被拦截 ↓
           自定义降级(Fallback): 返回默认值/缓存/提示
```
> Sentinel 通过**责任链**把这些功能串起来，见 §3。

---

## 2. 核心概念：资源 / 规则 / 上下文

| 概念 | 含义 | 例子 |
|---|---|---|
| **资源 Resource** | 被保护的业务入口（方法/接口/代码块）| `com.xxx.orderService.getOrder` |
| **规则 Rule** | 对资源施加的流量策略 | 限流规则/熔断规则… |
| **上下文 Context** | 调用链上下文，区分调用来源/链路 | `@SentinelResource` |
| **Entry** | 进入资源的一个句柄（进入才被统计）| `SphU.entry("getOrder")` |

```java
// 代码埋点: 对资源做保护
try (Entry entry = SphU.entry("getOrder")) {      // 进入资源(会被统计/限流)
    // 业务逻辑
} catch (BlockException ex) {                       // 被限流/熔断时触发
    // 降级处理
}
```

> 🔑 记忆：**资源 = 你保护的代码；规则 = 怎么保护；Entry = 保护点**。

---

## 3. 核心原理（⭐）：滑动窗口 + 责任链 SlotChain

### 3.1 实时统计：滑动窗口（LeapArray）

要限流，先要知道当前 QPS/错误率。Sentinel 用**滑动窗口**实时统计：

```
时间轴(秒级/分钟级) 分成 N 个小桶(sampleCount)
[ 桶1 ][ 桶2 ][ 桶3 ]...   → 每次滑动,过期桶滚出,新桶滚入
每个桶 MetricBucket 记录: 通过数/阻塞数/异常数/成功数/RT
```

| 核心类 | 作用 |
|---|---|
| `Metric / ArrayMetric` | 报告接口，定义滑动窗口统计（成功/异常/阻塞/RT）|
| `LeapArray` | 滑动窗口顶层结构，含一串 `WindowWrap` |
| `WindowWrap` | 单桶包装 |
| `MetricBucket` | 指标桶（通过/阻塞/异常/成功/RT 计数）|
| `MetricEvent` | 指标事件类型 |

> 💡 滑动窗口解决"统计精度 vs 内存"权衡：比固定窗口平滑、比全量计数省内存。**QPS、熔断比例、异常统计都基于它**。

### 3.2 责任链 SlotChain（各功能串联）

Sentinel 把不同功能做成 **Slot**，按责任链串联执行（每资源一条 chain）：

```
chain:  NodeSelectorSlot → ClusterBuilderSlot → FlowSlot(限流) → DegradeSlot(熔断)
        → SystemSlot(系统保护) → AuthoritySlot(授权) → StatisticSlot(统计)
```

| Slot | 职责 |
|---|---|
| NodeSelectorSlot / ClusterBuilderSlot | 构建调用链节点 / 全局集群节点（统计用）|
| **FlowSlot** | 流控（限流）判断 |
| **DegradeSlot** | 熔断降级判断 |
| **SystemSlot** | 系统保护（load/CPU/入口QPS）|
| **AuthoritySlot** | 授权（黑白名单）|
| StatisticSlot | 最终统计写回滑动窗口 |

> 🔑 面试点：**Sentinel = 滑动窗口统计 + 责任链规则判断**。统计用 LeapArray，判断按 Node→Flow→Degrade→System→Authority 链式执行，命中即 Block。

### 3.3 关键统计节点

- `DefaultNode`：链路节点（某资源在**某条调用链**上的数据）。
- `ClusterNode`：簇点（某资源**全局**数据，不分链路）。
- `EntranceNode`：入口节点（全局入口，系统保护用）。

---

## 4. 六大规则使用（⭐）

### 4.1 流控规则（限流）

**核心维度**：QPS（每秒请求数）/ 并发线程数；**应对资源**：直接 / 关联 / 链路。

```yaml
# 流控规则 (FlowRule)
resource: getOrder          # 资源
grade: 1                    # 1=QPS 0=并发线程数
count: 100                  # 阈值: QPS 100
limitApp: default           # 调用来源(可用 default=全部)
strategy: 0                 # 0=直接 1=关联 2=链路
controlBehavior: 0          # 控制行为(直接拒绝/预热/匀速排队) 见§5
```

```java
FlowRuleManager.loadRules(() -> {
    FlowRule r = new FlowRule();
    r.setResource("getOrder");
    r.setGrade(RuleConstant.FLOW_GRADE_QPS);
    r.setCount(100);          // QPS≤100
    r.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_DEFAULT); // 直接拒绝
    return Arrays.asList(r);
});
```

> 说明：`limitApp` 可做**调用来源限流**（如某来源配额）；`strategy=关联` 限流关联资源（保护主入口）。

### 4.2 熔断降级规则（DegradeRule）

**三大熔断策略**（1.8+）：

| 策略 | `grade` | 触发条件 | 关键字段 |
|---|---|---|---|
| **慢调用比例** | `SLOW_REQUEST_RATIO` | 慢请求(>RT阈值)比例超阈值 | `count`(RT阈值ms)、`slowRatioThreshold`(慢比例)、`statIntervalMs` |
| **异常比例** | `EXCEPTION_RATIO` | 异常数/总数 比例超阈值 | `count`(比例)、`statIntervalMs` |
| **异常数** | `EXCEPTION_COUNT` | 统计区间内异常数超阈值 | `count`(数量)、`statIntervalMs` |

通用字段：`timeWindow`（熔断后**时间窗口**，期内请求直接降级）、`minRequestAmount`（最少请求数，防冷启动误判）。

```yaml
resource: rpcPay
grade: 0                     # 0=慢调用比例
count: 1000                  # 平均RT>1000ms 记为慢
slowRatioThreshold: 0.5      # 慢调用占比>50%
timeWindow: 10               # 熔断10秒
minRequestAmount: 5          # 统计区间内最少5个请求才判断
statIntervalMs: 1000         # 统计窗口1s
```

> 🔑 **熔断后状态机**：进入 `open` 状态，`timeWindow` 内请求直接拒绝降级 → 窗口过转 `half-open`（放少量试探）→ 恢复则 `closed`。**这区别于限流（瞬时超限）**：熔断是"持续故障主动切断"。

### 4.3 热点参数限流（Hot Param）

对**某个参数值**（如 uid=热点用户）单独限流，LRU 统计 + 令牌桶：

```
资源 getOrder 的参数 uid
规则: 总 QPS>100 限流; 例外: uid=1 单独阈值为 3
```

```java
ParamFlowRule r = new ParamFlowRule();
r.setResource("getOrder");
r.setParamIdx(0);          // 参数下标0(uid)
r.setCount(100);           // 参数级总阈值
// 例外项: 热点uid=1 只允许3
ParamFlowItem item = new ParamFlowItem("1", 3, null);
r.setParamFlowItemList(Arrays.asList(item));
```

> ⚠️ 用 `SphU.entry(res, args)` 传参；`exit` 也要带参数，否则统计错。`@SentinelResource` 注解方法参数会自动作为入参。

### 4.4 系统自适应保护规则（SystemRule）

**应用级**（非资源级）入口保护，借鉴 **TCP BBR** 思想——按"系统处理能力"而非固定 load 限流：

| 维度 | 字段 | 说明 |
|---|---|---|
| load1 | 系统1分钟load | 仅 Linux；**load 作为启动因子**，实际允许流量由 RT+并发决定 |
| CPU 使用率 | | CPU 超过阈值拒绝对新的入口 |
| 平均 RT | | 入口平均 RT 阈值 |
| 入口 QPS | | 全局入口 QPS |
| 并发线程数 | | 入口并发数 |

> 💡 **BBR 精髓**：不按"load 超了就禁"（治果），而是用 load1 做启动信号 + 按处理能力（RT/并发）决定放行流量，让系统跑在最大吞吐又稳定。**只能保护入口流量**。

### 4.5 授权规则（黑白名单 / AuthorityRule）

按**调用来源（origin）**控制 是否放行：

| 策略 | 配置 | 效果 |
|---|---|---|
| 白名单 | limitApp=来源A | **只有**来自A通过 |
| 黑名单 | limitApp=来源A | **来自A的**拒绝 |

```java
AuthorityRule r = new AuthorityRule();
r.setResource("getOrder");
r.setStrategy(RuleConstant.AUTHORITY_WHITE); // 白名单
r.setLimitApp("internal-service");           // 只准 internal-service 调用
```

> 使用场景：管理员接口只允许网关来源、内部接口禁外部直连等。

**设置调用来源（origin）**：授权规则判断的 `origin` 由 `RequestOriginParser` 解析（默认从 `origin` 请求头取）：

```java
// 自定义来源解析器: 从请求头/参数取调用来源
@Component
public class CustomOriginParser implements RequestOriginParser {
    @Override
    public String parseOrigin(HttpServletRequest request) {
        return request.getHeader("X-Source");   // 取 X-Source 头作来源
    }
}
```

> 说明：来源可来自网关透传的头（`X-Source`）或自定义参数，这样授权规则能识别"来自网关/来自内部"。配合网关透传身份（见 [01-Spring Cloud Gateway详解](../网关/01-Spring Cloud Gateway详解.md) §7）。

### 4.6 集群流控（Token Client / Server）

单机限流解决不了"集群总量"（100台各限10 QPS，某个机器被热点打满失真）。Sentinel 集群流控：

```
TokenClient(每实例) ←—Netty—→ TokenServer(一个/内嵌)
                              ↓ 汇总统计集群总量判断
```
| 模式 | 说明 |
|---|---|
| **集群总体模式** | 整个集群某资源总 QPS ≤ 阈值 |
| **单机均摊模式** | 阈值=单机限额，server 按连接数算总量（n×单机）|

> 适用：要给"**某个用户调某API 总量≤50**"（不限单机）、流量不均场景。TokenServer 独立部署或内嵌某实例。

---

## 5. 流量整形（controlBehavior）

流控规则可通过 `controlBehavior` 选择"超限怎么处理"：

| 控制行为 | 说明 | 场景 |
|---|---|---|
| **直接拒绝**（默认）| 超限立刻 Block | 大部分 |
| **预热 Warm Up** | 阈值从 1/3 逐步升到满（冷启动保护）| 应用刚启动、缓存未热的接口 |
| **匀速排队** | 超限请求进队列匀速处理（拒绝超过排队时长）| 削峰填谷、MQ 式平滑 |

```yaml
controlBehavior: 1     # 预热
warmUpPeriodSec: 10    # 预热10秒
```
```yaml
controlBehavior: 2     # 匀速排队
maxQueueingTimeMs: 400 # 最多排队400ms
```

> 💡 **冷启动**：预热让刚重启的缓存/连接池有时间初始化，避免瞬间压爆。**匀速排队**适合消息下发、积分等可容忍延迟的场景。

---

## 6. 控制台 Dashboard + 规则持久化（⭐）

### 6.1 控制台

Sentinel 提供**开箱即用控制台**：机器发现、配置规则（流控/熔断/热点/系统/授权）、秒级监控。

```bash
# 启动控制台(独立进程)
java -Dserver.port=8080 -Dcsp.sentinel.dashboard.server=localhost:8080 \
     -Dproject.name=sentinel-dashboard -jar sentinel-dashboard.jar
```
```properties
# 客户端接入: 告诉它控制台地址 + 项目名
spring.cloud.sentinel.transport.dashboard=localhost:8080
spring.cloud.sentinel.transport.port=8719
```
客户端上报并连控制台，控制台**发现机器→展示监控→下发规则**。

### 6.2 规则持久化（关键！）

⚠️ **Sentinel 默认规则在客户端内存 + Dashboard 保存不了规则**——**重启即丢**。生产必须对接规则中心持久化。

三种模式：

| 模式 | 机制 | 优缺点 | 生产? |
|---|---|---|---|
| **原始模式** | API 直接推客户端内存 | 简单无依赖，**重启丢、不保证一致** | ❌ 禁用 |
| **Pull 模式** | 客户端轮询规则中心(DB/文件/VCS)拉取 | 实现简单，实时性差 | ⚠️ 少用 |
| **Push 模式** | 规则中心(Nacos/Apollo/ZK)**推送**，客户端监听 | **实时、一致、官方推荐** | ✅ 推荐 |

**Push 模式（Nacos 为例）**：

```
Dashboard改造 → 规则写入 Nacos(配置中心)
        ↘ 客户端 ReadableDataSource 监听 Nacos → 实时更新本地规则
```

```java
// 客户端: 对接 Nacos 数据源(推模式)
ReadableDataSource<String, List<FlowRule>> ds =
    new NacosDataSource<>(NacosConfigUtil.getServerAddr(), "",
        NacosConfigUtil.getGroup(), NacosConfigUtil.getFlowDataId(postfix),
        source -> JSON.parseObject(source, new TypeReference<List<FlowRule>>() {}));
FlowRuleManager.register2Property(ds.getProperty());
```

> 🔥 **生产铁律**：Dashboard 默认**不持久化规则**（1.8 后部分版本加了 Nacos 支持），要**改造 Dashboard 或直接配 Push 数据源**，否则重启规则全丢。规则最好控制台集中管理 + 推配置中心。

---

## 7. Spring Cloud 集成实战

```xml
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-sentinel</artifactId>
</dependency>
```
```yaml
spring:
  cloud:
    sentinel:
      transport:
        dashboard: localhost:8080   # 控制台
        port: 8719                  # 客户端端口
      eager: true                   # 启动即sentinel初始化(否则懒加载)
      datasource:                   # 规则数据源(推模式持久化)
        flow:
          nacos:
            server-addr: 127.0.0.1:8848
            data-id: ${spring.application.name}-flow-rules
            rule-type: flow
```

```java
@SentinelResource("getOrder")            // 注解定义资源
public Order getOrder(String uid) {
    return orderService.query(uid);
}
// 降级/兜底:
@SentinelResource(value = "getOrder", blockHandler = "orderBlock", fallback = "orderFallback")
Order orderBlock(String uid, BlockException ex) { return Order.empty(); }     // 被限流
Order orderFallback(String uid) { return Order.empty(); }                     // 业务异常
```
> 说明：`blockHandler` 处理**被规则拦截**(BlockException)；`fallback` 处理**业务异常**。两个兜底区分开。

**@SentinelResource 注解全属性**（高频使用，建议掌握）：

| 属性 | 作用 | 说明 |
|---|---|---|
| `value` | 资源名 | 默认方法名+"()"，限流/熔断规则绑它 |
| `blockHandler` | 被规则拦截的兜底方法 | 同类名方法，参数须含 `BlockException` |
| `blockHandlerClass` | blockHandler 所在类 | 放独立类时指定，方法须 `static` |
| `fallback` | **业务异常**兜底方法 | 非 BlockException（含业务异常/RT），返回默认 |
| `fallbackClass` | fallback 所在类 | 放独立类时指定，须 `static` |
| `defaultFallback` | 默认兜底(通用) | 不考虑参数(2 个以内版本/同签)，兜底所有 |
| `exceptionsToIgnore` | **忽略不兜底的异常** | 被忽略的异常原样抛出，不 trigger fallback |

```java
@SentinelResource(
    value = "placeOrder",
    blockHandler = "blocked",               // 被限流/熔断
    fallback = "fb",                        // 业务异常
    exceptionsToIgnore = {IllegalStateException.class}  // 这类异常不兜底,直接抛
)
public Order placeOrder(long uid) {
    return Order.of(uid);
}
// 兜底方法签名: 参数与主方法一致(可放多余) + 结尾一个 Throwable/BlockException
public Order blocked(long uid, BlockException e) { return Order.empty(); }
public Order fb(long uid, Throwable t) { return Order.empty(); }
```

> 🔥 注意签名规则：兜底方法**返回类型需与主方法一致**，参数在主方法参数后追加 `BlockException`（blockHandler）或 `Throwable`（fallback）。`exceptionsToIgnore` 里列出的异常**不会触发降级**（如参数校验异常应直接提示）——这是很容易忽略但生产很实用的点。

> 适配：Sentinel 有 servlet / spring-cloud / dubbo / gRPC 等适配器，自动埋点常见框架。

---

## 8. 生产最佳实践

- **规则持久化用 Push(Nacos/ZK)**，别靠 Dashboard 内存规则。
- **熔断降级兜底必配** `fallback`：返回默认值/缓存/提示，别让异常抛给上游。
- **冷启动/热点**：刚重启接口用预热；热点商品/用户用热点参数限流。
- **系统保护做兜底**：入口级 load/CPU 保护防整体雪崩。
- **授权白名单**控敏感接口来源。
- **区分限流 vs 熔断**：限流控瞬时超量，熔断控持续故障；都用。
- **监控告警**：配合监控对 Block 数/熔断事件告警。
- 权限/凭证：客户端 token 等配好，防未授权机器上报控制台（`project.name`+transport 权限）。

---

## 9. 与 Hystrix / Resilience4j 对比选型

| 维度 | Sentinel | Resilience4j | Hystrix(已停更) |
|---|---|---|---|
| 隔离策略 | 信号量(并发线程) | 信号量 | 线程池/信号量 |
| 熔断策略 | 慢调用/异常比例/异常数 | 异常比例/RT | 异常比例 |
| 实时统计 | 滑动窗口(LeapArray) | Ring Bit Buffer | 滑动窗口(RxJava) |
| **限流** | ✅ QPS+调用关系 | RateLimiter | 有限 |
| **流量整形** | ✅ 预热/匀速 | 简单 | ❌ |
| **集群流控** | ✅ | ❌ | ❌ |
| **系统自适应** | ✅ | ❌ | ❌ |
| 控制台 | ✅ 开箱即用+监控 | ❌ | 不完善 |
| 注解/适配 | Spring/Dubbo/gRPC | 函数式/轻量 | Spring Cloud Netflix |
| 生态 | **Spring Cloud Alibaba** | Spring Cloud / 官方轻量 | 弃用 |
| 选型 | **国内微服务主流** | **轻量/函数式/架构无入侵** | ❌ 不选 |

> 💡 选型一句话：**要全链路流量治理+控制台+国内生态 → Sentinel**（默认）；要轻量函数式、库体积小、不想依赖 Alibaba → **Resilience4j**；Hystrix **已停更不可选**（迁移到上面两）。

---

## 10. 面试高频 Q&A

- **Sentinel 和 Hystrix 区别？** Sentinel 全链路治理(限流+热点+系统+集群+控制台)；Hystrix 只有熔断+线程池隔离，已停更。
- **Sentinel 限流原理？** 滑动窗口(LeapArray)统计 + 责任链 SlotChain 判断；FlowSlot 按 QPS/并发。
- **熔断三种策略？** 慢调用比例/异常比例/异常数；timeWindow 熔断后窗口 + minRequestAmount 防误判。
- **限流 vs 熔断？** 限流=瞬时超量拒；熔断=持续故障开门状态切（open/half-open/closed）。
- **规则持久化怎么做？** 生产用 Push(Nacos/ZK) 数据源，别用内存原始模式(重启丢)；Dashboard 默认不持久化需处理。
- **热点参数限流？** 对参数值(uid)单独限流,LRU+令牌桶,例外项；需传参 entry。
- **系统保护规则？** 应用级 load/CPU/RT/QPS 入口保护,借鉴 BBR。
- **集群流控？** TokenClient/Server(Netty) 控制集群总量,总体/单机均摊。
- **fallback vs blockHandler？** blockHandler=被规则拦截, fallback=业务异常。

---

## 11. 参考

- [Sentinel 熔断降级（Wiki）](https://github.com/alibaba/Sentinel/wiki/%E7%86%94%E6%96%AD%E9%99%8D%E7%BA%A7)
- [Sentinel 热点参数限流（Wiki）](https://github.com/alibaba/Sentinel/wiki/%E7%83%AD%E7%82%B9%E5%8F%82%E6%95%B0%E9%99%90%E6%B5%81)
- [Sentinel 系统自适应限流（Wiki）](https://github.com/alibaba/Sentinel/wiki/%E7%B3%BB%E7%BB%9F%E8%87%AA%E9%80%82%E5%BA%94%E9%99%90%E6%B5%81)
- [Sentinel 集群流控（Wiki）](https://github.com/alibaba/Sentinel/wiki/%E9%9B%86%E7%BE%A4%E6%B5%81%E6%8E%A7)
- [Sentinel 动态规则扩展（数据源持久化 Push/Pull）](https://sentinelguard.io/zh-cn/docs/dynamic-rule-configuration.html)
- [Sentinel 在生产环境中使用（规则持久化三种模式）](https://github.com/alibaba/Sentinel/wiki/%E5%9C%A8%E7%94%9F%E4%BA%A7%E7%8E%AF%E5%A2%83%E4%B8%AD%E4%BD%BF%E7%94%A8-Sentinel)
- [Slide 窗口实现原理（阿里云）](https://developer.aliyun.com/article/939609)
- [常用限流降级组件对比（Sentinel/Hystrix/Resilience4j）](https://github.com/alibaba/Sentinel/wiki/%E5%B8%B8%E7%94%A8%E9%99%90%E6%B5%81%E9%99%8D%E7%BA%A7%E7%BB%84%E4%BB%B6%E5%AF%B9%E6%AF%94)
- 查证 2026-08：Sentinel 1.8.x
- 关联：[00-微服务总览](../00-微服务总览.md)、[02-熔断限流降级·原理与组件选型](02-熔断限流降级·原理与组件选型.md)（本篇姊妹篇）、[00-中间件总览](../../中间件/00-中间件总览.md)
