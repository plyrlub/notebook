---
tags: [Java, SpringBoot, 日志, 实践, Logback, 滚动, MDC, 链路追踪, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot日志配置实战

> 版本基线：Spring Boot 3.x，默认 SLF4J + Logback
> 受众：先读 [09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md)（门面/实现/logback-spring.xml 原理），本篇给能直接抄的生产级配置与 MDC 链路用法。
> 前置：[09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md)。

## 📋 总纲

1. 快速起步：application.yml 行内配置
2. 生产推荐：logback-spring.xml 完整模板 ★
3. 滚动策略（按天+大小）配置
4. profile 区分：开发/生产不同级别
5. MDC 链路追踪实战 ★
6. 异步日志（性能优化）
7. 常见踩坑

## 1. 快速起步：application.yml 行内配置

不写 xml 也能配最简单的：

```yaml
logging:
  level:
    root: info
    com.example.order: debug        # 指定包降级打印
  file:
    name: logs/app.log
  pattern:
    console: "%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n"
```

> 适合小项目/调试。要滚动/多环境/异步，上 logback-spring.xml（第 2 节）。

## 2. 生产推荐：logback-spring.xml 完整模板"★ 可直接抄

放在 `src/main/resources/logback-spring.xml`（注意是 `logback-spring.xml` 不是 `logback.xml`，见理论篇：要能读 spring profile 必须用前者）。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <!-- 统一属性：日志目录 & 级别（可用 SPRING_PROFILES_ACTIVE 配合 profile 覆盖） -->
    <property name="LOG_DIR" value="${LOG_PATH:-logs}"/>

    <!-- 控制台输出 -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} [%X{traceId}] - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- 滚动文件：按天 + 大小 -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>${LOG_DIR}/app.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>${LOG_DIR}/app.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>100MB</maxFileSize>       <!-- 单文件阈值，达到即滚 -->
            <maxHistory>30</maxHistory>            <!-- 保留 30 天 -->
            <totalSizeCap>10GB</totalSizeCap>      <!-- 全量上限，防磁盘爆 -->
        </rollingPolicy>
        <encoder><pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} [%X{traceId}] - %msg%n</pattern></encoder>
    </appender>

    <!-- 根级别：控制台 + 文件 -->
    <root level="info">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="FILE"/>
    </root>
</configuration>
```

> 要点：
> - **文件名用 `.gz`**：滚动后自动压缩，省磁盘。
> - **`maxHistory` + `totalSizeCap` 双上限**：前者按天，后者兜底总量，防止"单体撑爆磁盘"。
> - **`LOG_PATH` 环境变量占位**：`${LOG_PATH:-logs}` 无环境变量时落到 `logs/` 目录，方便部署接管日志目录。

## 3. 滚动策略对照

| 策略类 | 文件名样式 | 触发条件 | 适用 |
| --- | --- | --- | --- |
| `TimeBasedRollingPolicy` | `app.%d{yyyy-MM-dd}.log` | 按时间（日/时） | 量大按时间归档 |
| `SizeBasedTriggeringPolicy` | 需配 size | 按文件大小 | 配合时间粒度 |
| `SizeAndTimeBasedRollingPolicy`（推荐） | `%d`+`.%i` | 时间+大小双触发 | **生产首选**：日切 + 超阈值再切 |

## 4. profile 区分：开发/生产不同级别

`logback-spring.xml` 里用 springProfile 按环境分支，开发 full、生产只看 warn：

```xml
<!-- 开发/本地：打印 debug 到控制台即可 -->
<springProfile name="dev">
    <root level="debug">
        <appender-ref ref="CONSOLE"/>
    </root>
</springProfile>

<!-- 生产：warn 起 + 滚动文件 -->
<springProfile name="prod">
    <root level="warn">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="FILE"/>
    </root>
</springProfile>
```

> 依赖 `logback-spring.xml`（非 `.xml`）才能读 spring profile；同时若用 `application-{profile}.yml` 的 `logging.level` 也能覆盖，二选一避免打架。

## 5. MDC 链路追踪实战（★ 排查神器)

给一次请求的所有日志带同一个 `traceId`，用 Filter 借 SLF4J MDC 实现：

```java
import org.slf4j.MDC;
import jakarta.servlet.*;
import java.io.IOException;
import java.util.UUID;

/** 请求入口生成 traceId 塞入 MDC；日志 pattern 里 %X{traceId} 输出 */
@Component
public class TraceIdFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        MDC.put("traceId", UUID.randomUUID().toString().replace("-", "").substring(0, 16));
        try {
            chain.doFilter(req, res);
        } finally {
            MDC.remove("traceId");      // 必须清理，避免线程池复用串号
        }
    }
}
```

logback 加 `[%X{traceId}]`（第 2 节模板已含）。效果：同一次 HTTP 请求的所有同步日志共享 traceId，`grep traceId` 即可串起整条链路。

> **异步线程串号**：MDC 靠 ThreadLocal，`@Async` 新线程不继承。要跨线程传 traceId，需用增强的 TaskDecorator（异步篇可补充）——否则从线程池出来的日志没有/错 traceId。

## 6. 异步日志（性能优化）

高并发下 IO 是瓶颈，文件输出改异步 appender：

```xml
<appender name="ASYNC" class="ch.qos.logback.classic.AsyncAppender">
    <queueSize>1024</queueSize>               <!-- 缓冲队列 -->
    <discardingThreshold>0</discardingThreshold> <!-- 永不丢弃（重要：不静默丢日志） -->
    <appender-ref ref="FILE"/>
    <appender-ref ref="CONSOLE"/>
</appender>
```

> `AsyncAppender` 把写盘交给独立线程，业务线程只需入队，显著降延迟。`discardingThreshold=0` 意在不因队列满丢弃日志。

## 7. 常见踩坑

- **用 logback.xml 却想读 profile**：读不了。要么 `logback-spring.xml`（推荐），要么配置里硬编码。
- **滚动文件权限被占**：Linux 下文件被 Inotify/别进程占用时滚动失败，检查 `file` 路径与归档目录权限。
- **磁盘打爆**：没设 `totalSizeCap`/`maxHistory`，`logs/` 无限膨胀（最隐蔽的生产事故）。
- **MDC 残留串号**：finally 里忘 `MDC.remove`，线程池复用后下一个任务带上上个 traceId。
- **异步线程 traceId 丢失**：没做 TaskDecorator 传递。
- **多 appender 重复打印**：文件 appender 里误加多个 ref，或 root 与 logger 叠加输出。

## 8. 小结

- 小项目 application.yml 够用；生产上 `logback-spring.xml`（滚动 + profile + 异步）。
- 滚动选 `SizeAndTimeBasedRollingPolicy`，`.gz` 压缩 + 双上限防爆盘。
- MDC + `%X{traceId}` Filter 是串链路的主手段，记得 finally 清理。
- 异步 appender 提吞吐，`discardingThreshold=0` 保日志不丢。

## 9. 关联笔记

- 理论篇：[09-SpringBoot日志配置详解](09-SpringBoot日志配置详解.md)
- [08-SpringBoot异步与线程池实践](08-SpringBoot异步与线程池实践.md)：MDC 跨线程传 traceId 的 TaskDecorator 实践
- [03-SpringBoot配置体系与外部化配置实践](03-SpringBoot配置体系与外部化配置实践.md)：LOG_PATH 走环境变量接管

## 10. 参考资料

- [Logback 官方：Configuration](https://logback.qos.ch/manual/configuration.html)，查询日期 2026-08-15
- [《Spring Boot 3.x 日志最佳实践》——Baeldung](https://www.baeldung-cn.com/spring-boot-logging)，查询日期 2026-08-15
- [Logback 官方：RollingPolicy / AsyncAppender](https://logback.qos.ch/manual/appenders.html)，查询日期 2026-08-15
