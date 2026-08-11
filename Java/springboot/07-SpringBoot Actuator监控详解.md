---
tags: [Java, SpringBoot, Actuator, 监控, 指标, Micrometer, Prometheus, health, 运维]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot Actuator监控详解

> 版本基线：Spring Boot 2.x/3.x（Actuator + Micrometer）
> 受众：Java 后端开发 / 运维。生产监控是必备能力，本篇讲清 Actuator 端点、健康检查、指标采集与 Prometheus 集成。
> 前置知识：无强制；了解 HTTP/JSON 即可
> 关联笔记：[05-SpringBoot异步与线程池详解](05-SpringBoot异步与线程池详解.md)（线程池指标）、[06-SpringBoot日志配置详解](06-SpringBoot日志配置详解.md)（日志与监控）、[08-Spring WebFlux响应式编程详解](08-Spring WebFlux响应式编程详解.md)（响应式监控）

## 📋 总纲

1. Actuator 是什么：生产监控端点
2. 核心端点速查
3. 端点暴露与安全（默认只开 health）
4. 健康检查 HealthIndicator
5. 指标 Metrics 与 Micrometer
6. 集成 Prometheus / Grafana
7. 常见坑

## 1. 学习目标

1. 引入 Actuator 并暴露所需端点
2. 用 /actuator/health 做健康检查
3. 自定义 HealthIndicator
4. 用 Micrometer 采集指标并导出 Prometheus
5. 安全控制端点暴露

## 2. 前置知识

- 无强制前置；了解 HTTP GET/JSON

## 3. 核心知识点

### 3.1 Actuator 是什么

Actuator 是 Spring Boot 的**生产监控模块**，通过 HTTP/JMX 端点暴露应用内部状态：健康、指标、环境、日志、线程、堆 dump 等。集成 K8s 健康探测、Prometheus 监控的基石。

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### 3.2 核心端点速查

| 端点 | 路径 | 作用 |
| --- | --- | --- |
| health | /actuator/health | 健康检查（默认暴露） |
| info | /actuator/info | 应用信息 |
| metrics | /actuator/metrics | 指标列表/详情 |
| env | /actuator/env | 环境属性 |
| loggers | /actuator/loggers | 查看/动态改日志级别 |
| beans | /actuator/beans | Bean 列表 |
| conditions | /actuator/conditions | 自动配置条件评估 |
| mappings | /actuator/mappings | URL 映射 |
| threaddump | /actuator/threaddump | 线程 dump |
| heapdump | /actuator/heapdump | 堆 dump |
| prometheus | /actuator/prometheus | Prometheus 格式指标 |
| shutdown | /actuator/shutdown | 优雅关闭（默认禁用） |

### 3.3 端点暴露与安全 ★

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus   # 显式暴露
        # include: "*"                             # 暴露全部（生产不建议）
        exclude: shutdown,env                       # 排除敏感
  endpoint:
    health:
      show-details: always        # 显示健康详情（默认 never）
```

**安全关键**：
- **默认只暴露 `health`**，其余需显式配置
- `shutdown` 默认禁用，需显式开启且有安全风险
- `env`/`heapdump`/`threaddump` 敏感，生产结合 Spring Security 或防火墙保护（见安全域 **01-Spring Security核心架构详解**（见知识库））
- K8s 探针可单独暴露 health 的 `liveness/readiness`

### 3.4 健康检查 HealthIndicator

```yaml
management:
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true      # 支持 liveness/readiness（K8s）
```

内置健康指示器：数据库、Redis、磁盘空间、Ping 等（依赖自动装配）。

**自定义健康检查**：

```java
@Component
public class MyServiceHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        if (myService.isUp()) {
            return Health.up().withDetail("msg", "OK").build();
        }
        return Health.down().withDetail("error", "service unavailable").build();
    }
}
```

K8s 集成：`/actuator/health/liveness`（存活）、`/actuator/health/readiness`（就绪）供探针使用。

### 3.5 指标 Metrics 与 Micrometer ★

Actuator 2.x 起集成 **Micrometer**——指标收集的"门面"（监控界 SLF4J），统一 API 对接 Prometheus/Datadog/InfluxDB 等。

```java
@Autowired MeterRegistry registry;

registry.counter("api.requests", "uri", "/orders").increment();
registry.timer("api.duration").record(...);
```

- 自动采集 JVM、HTTP 请求、线程池、数据库连接等 200+ 指标
- 线程池指标：`/actuator/metrics/jvm.threads.*` 等（呼应 [05-SpringBoot异步与线程池详解](05-SpringBoot异步与线程池详解.md)）
- 切换监控系统只改依赖（micrometer-registry-xxx），代码不变

### 3.6 集成 Prometheus / Grafana

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,prometheus
```

**流程**：
```
应用 /actuator/prometheus  →  Prometheus 拉取指标
                                 ↓
                           Grafana 可视化/告警
```

- 加 `micrometer-registry-prometheus` 依赖，Prometheus 自动配置
- `/actuator/prometheus` 输出 Prometheus 格式文本
- Prometheus 配置 scrape 该端点；Grafana 配 Prometheus 数据源 + 仪表盘

### 3.7 常见坑

- **端点没暴露** → 访问 404，需显式 include
- **health 详情不显示** → show-details 未开或权限受限
- **Prometheus 拉不到** → prometheus 端点没暴露 / 依赖缺失 / 端口没对
- **shutdown 误开** → 生产安全隐患
- **敏感端点裸奔** → env/heapdump 未做安全防护

## 4. 最佳实践

- 只暴露必要端点（health/info/metrics/prometheus），敏感端点防护
- health 配置 probes 供 K8s 探针
- 业务指标用 Micrometer 埋点，导 Prometheus + Grafana
- 自定义 HealthIndicator 反映真实依赖状态
- shutdown 走 K8s 优雅终止而非 Actuator shutdown 端点

## 5. 常见踩坑

- 指标命名规范：Prometheus 用 `api_requests_total`，用 Micrometer counter 自动加 `_total`
- 高维度指标（高基数 label）撑爆 Prometheus → 控制 tag 数量
- 生产环境 Actuator 未走网关鉴权 → 暴露内部信息，务必加 Spring Security/网络隔离

## 6. 小结

- Actuator 提供 HTTP 监控端点，默认只暴露 health。
- 端点按需 include，敏感端点防护。
- HealthIndicator 做健康检查，可自定义，可集成 K8s 探针。
- Micrometer 统一指标 API，对接 Prometheus + Grafana。
- 生产只暴露必要端点 + 安全防护。

## 7. 关联笔记

- 上一篇：[06-SpringBoot日志配置详解](06-SpringBoot日志配置详解.md)
- 下一篇：[08-Spring WebFlux响应式编程详解](08-Spring WebFlux响应式编程详解.md)
- [05-SpringBoot异步与线程池详解](05-SpringBoot异步与线程池详解.md)：线程池指标监控
- [06-SpringBoot日志配置详解](06-SpringBoot日志配置详解.md)：日志与监控协同
- 安全域 **01-Spring Security核心架构详解**（见知识库）：Actuator 端点鉴权

## 8. 参考资料

- [Spring Boot 官方：Metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html)，查询日期 2026-08-11
- [Baeldung：Spring Boot Actuator 详解](https://www.baeldung-cn.com/spring-boot-actuators)，查询日期 2026-08-11
