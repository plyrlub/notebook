---
tags: [Java, SpringBoot, Actuator, 监控, 实践, Prometheus, Grafana, Micrometer, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot监控实践

> 版本基线：Spring Boot 3.x，默认 Micrometer
> 受众：先读 [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)（端点/指标原理），本篇给"能让 Prometheus + Grafana 真正看到图"的配置与自定义指标代码。
> 前置：[11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)。

## 📋 总纲

1. 三步通：启 Actuator → 暴露端点 → 接入 Prometheus
2. 生产安全：端点暴露最小化 + 认证 ★
3. 接入 Prometheus（config + 拉取）
4. Grafana 面板可视化
5. 自定义业务指标（Counter/Timer）★
6. 健康检查自定义
7. 踩坑速查

## 1. 三步通：让 /actuator 说话

### ① 加依赖

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

### ② 配置暴露端点

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus   # 白名单暴露
  endpoint:
    health:
      show-details: always      # 健康详情（有组件就别 always，见安全节）
```

### ③ 验证

```bash
curl localhost:8080/actuator/health    # {"status":"UP"}
curl localhost:8080/actuator/prometheus  # Prometheus 文本指标格式（被 grafana/采集器拉取）
```

> 注：Spring Boot 3 里 `/metrics` 是综合页，Prometheus 采集走 `/actuator/prometheus`。

## 2. 生产安全：暴露最小化 + 认证（★ 别裸奔)

开发时 `include: *` 图爽快，生产**绝不**全暴露（暴露 `/actuator/env`、`/heapdump`、`/configprops` 会泄漏配置/内存快照/密钥）：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus   # 只留这三个
  endpoint:
    health:
      show-details: never                  # 生产不显示组件细节，避免泄露依赖信息
```

Prometheus 的 `/actuator/prometheus` 也可再加访问控制。落地到 `/env /heapdump` 等敏感端点在生产**默认就要关闭**，不写进 include 即不可访问。

## 3. 接入 Prometheus

`prometheus.yml` 配置抓取（与 Spring Boot 同机或 K8s Service 都行）：

```yaml
scrape_configs:
  - job_name: 'springboot-app'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['localhost:8080']
```

启动 Prometheus 后，`{{prometheus}}/targets` 能看到 target UP，`/graph` 里能查内置指标（如 `http_server_requests_seconds`、`process_cpu_usage`、`jvm_memory_used_bytes`）。

## 4. Grafana 面板可视化

- 数据源 HTTP URL 指到 Prometheus（如 `http://prometheus:9090`）
- 常见告警/图表查询示例：

```promql
# 接口 QPS（按 path 分）——Actuator 自动打了 http_server_requests_* 指标
sum(rate(http_server_requests_seconds_count[1m])) by (uri)

# JVM 堆使用率
sum(jvm_memory_used_bytes{area="heap"}) / sum(jvm_memory_max_bytes{area="heap"})

# 线程池活跃度（配合异步实践篇自定义指标）
biz_async_pool_active
```

> 社区已有现成 JSON 面板，导入后选 Prometheus 数据源即可出 JVM/HTTP/GC 概览。

## 5. 自定义业务指标（Counter / Timer）

不满足于内置，自己埋点统计业务量（如订单数、接口耗时分位）：

```java
import io.micrometer.core.annotation.Timed;
import io.micrometer.core.instrument.*;

@RestController
public class OrderController {
    private final Counter orderCreated;
    private final Timer createTimer;

    public OrderController(MeterRegistry registry) {
        orderCreated = Counter.builder("order.created").description("新建订单数").register(registry);
        createTimer = Timer.builder("order.create.time")
                .publishPercentiles(0.5, 0.9, 0.99)   // 发布 P50/P90/P99
                .publishPercentileHistogram()          // 直方图给 PromQL 做分位
                .register(registry);
    }

    @PostMapping("/orders")
    public Order create(@RequestBody Order req) {
        return createTimer.record(() -> {
            Order o = doCreate(req);
            orderCreated.increment();
            return o;
        });
    }
}
```

> PromQL 查分位：`histogram_quantile(0.99, sum(rate(order_create_time_seconds_bucket[5m])) by (le))`。命中率/错误率同理用 `Counter` + 比值。

## 6. 自定义健康检查

告诉探针"服务依赖的某中间件是否可用"（如自研缓存、外部 API）:

```java
import org.springframework.boot.actuate.health.*;

@Component
public class MyServiceHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        boolean ok = checkExternalApi();
        return ok
            ? Health.up().withDetail("api", "reachable").build()
            : Health.down().withDetail("api", "unreachable").build();
    }
}
```

> 结合 `show-details` 控制是否暴露详情。K8s 里把 `/actuator/health` 配成 liveness/readiness 探针即可做自动重启。

## 7. 踩坑速查

- **生产全量暴露**：泄漏 `/env` 密钥、`/heapdump` 堆快照——白名单只留 `health,info,prometheus`。
- **Prometheus 拉不到**：依赖没加 `micrometer-registry-prometheus`，或 `scrape_configs` 的 `metrics_path` 忘写 `/actuator/prometheus`。
- **`show-details: always` 上生产**：暴露组件细节/地址，压测或安全审计是红线。改 never。
- **自定义指标没出现在 metrics**：`MeterRegistry` 注入错（用了注入而不是构造器），或没在自动注册类里。
- **P99 拉平**：单实例日志/官方默认分位粒度，取不到 P99 时检查 `publishHistogram` 是否开。
- **健康检查误报 UP**：业务组件没实现 `HealthIndicator`，探针探不到依赖真实状态。

## 8. 小结

- 三件套：`actuator` 依赖 + `include` 白名单 + `micrometer-registry-prometheus`。
- 生产只暴露 `health,info,prometheus`，`show-details: never`。
- Prometheus 拉 `/actuator/prometheus`，Grafana 建数据源看图。
- Counter 记数、Timer 记时（含分位），配 prometheus 直方图即可出 P90/P99。
- 自定义 HealthIndicator 让探针反映真实依赖。

## 9. 关联笔记

- 理论篇：[11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)
- [08-SpringBoot异步与线程池实践](08-SpringBoot异步与线程池实践.md)：线程池指标自定义（MeterBinder）
- [10-SpringBoot日志配置实践](10-SpringBoot日志配置实践.md)：日志与监控的告警互补
- orm 域 [07-Spring Boot集成与配置详解](../数据访问层/07-Spring Boot集成与配置详解.md)：数据源健康检查

## 10. 参考资料

- [Spring Boot 官方：Actuator（Production-ready Features）](https://docs.spring.io/spring-boot/reference/actuator/index.html)，查询日期 2026-08-15
- [Micrometer 官方：Prometheus 注册表](https://micrometer.io/docs/registry/prometheus)，查询日期 2026-08-15
- [Prometheus 官方：Configuring scrape](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)，查询日期 2026-08-15
