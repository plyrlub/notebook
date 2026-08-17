---
tags: [Java, SpringBoot, 异步, 线程池, 实践, Async, ThreadPoolTaskExecutor, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot异步与线程池实战

> 版本基线：Spring Boot 3.x
> 受众：先读 [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)（@Async 原理/AOP 代理/失效场景），本篇给"能直接抄"的线程池配置与 @Async 用法。有代码即看本篇。
> 前置：[07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)。

## 📋 总纲

1. 大坑警示：不要裸用 @Async
2. 自定义线程池配置类（推荐可上生产）★
3. 多线程池：按业务拆分 email/sms/export
4. @Async 用法与指定线程池
5. 返回值 CompletableFuture 用法
6. 拒绝策略选型
7. 监控线程池
8. 踩坑速查（含必须避开的失效场景）

## 1. 大坑警示：不要裸用 @EnableAsync

> **裸 @EnableAsync 会让异步失控**：Boot 在没自定义 `TaskExecutor` Bean 时，默认用 `SimpleAsyncTaskExecutor`——它**每次调用都 new 一个线程、不复用、无界**。低并发没感觉，生产一爆流量就疯狂建线程 → `OutOfMemoryError: Java heap space`（堆是被线程栈撑爆的，不是 Xmx 小）。看到"OOM + @Async"，第一反应别调 -Xmx，查线程池。

所以：**正经项目第一个配置类就是自定义执行器**。

## 2. 自定义线程池配置类（★ 推荐抄")

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import java.util.concurrent.*;

@Configuration
@EnableAsync
public class ThreadPoolConfig {

    @Bean(name = "taskExecutor")
    public ThreadPoolTaskExecutor taskExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(8);                // 核心线程数
        e.setMaxPoolSize(32);                // 最大线程数
        e.setQueueCapacity(200);             // 有界队列容量
        e.setKeepAliveSeconds(60);           // 非核心线程空闲存活
        e.setThreadNamePrefix("biz-async-"); // 线程名前缀（排查日志/监控用）
        e.setWaitForTasksToCompleteOnShutdown(true); // 优雅停机：等已提交任务跑完
        e.setAwaitTerminationSeconds(30);    // 停机最多等 30s
        e.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        e.initialize();
        return e;
    }
}
```

> **关键点**：
> - **有界队列**（`setQueueCapacity(200)`）：裸用无界队列 `LinkedBlockingQueue` 在高负载下照旧 OOM。有界队列让"队列满则触发拒绝策略"，可控。
> - **CallerRunsPolicy**：队列满 + 线程满时，任务回退调用线程同步执行（牺牲一点吞吐，保命不丢任务不爆内存），生产常用兜底。
> - `setWaitForTasksToCompleteOnShutdown(true)` 优雅停机，避免"流量回滚时异步任务被突突杀掉"。
> - 用 `ThreadPoolTaskExecutor`（Spring 封装）而非裸 `ThreadPoolExecutor`，它自动接入 Spring 生命周期回调（`@PreDestroy` 关闭），配合上面两个停机参数更稳。

## 3. 多线程池：按业务拆分

单一池所有业务混用易互相拖累（发邮件占满池，导出任务饿死）。按业务拆：

```java
@Configuration
@EnableAsync
public class MultiThreadPoolConfig {

    @Bean("emailExecutor")
    public ThreadPoolTaskExecutor emailExecutor() {
        return build("email-", 5, 10, 50);
    }

    @Bean("exportExecutor")
    public ThreadPoolTaskExecutor exportExecutor() {
        return build("export-", 8, 16, 100);
    }

    private ThreadPoolTaskExecutor build(String prefix, int core, int max, int queue) {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(core);
        e.setMaxPoolSize(max);
        e.setQueueCapacity(queue);
        e.setThreadNamePrefix(prefix);
        e.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        e.initialize();
        return e;
    }
}
```

## 4. @Async 用法与指定线程池

```java
@Service
public class NotificationService {

    /** 用默认 taskExecutor 池 */
    @Async
    public void sendSms(Phone p) {
        // 耗时：短信第三方调用
    }

    /** 指定 emailExecutor 池 */
    @Async("emailExecutor")
    public CompletableFuture<Void> sendEmail(Email e) {
        // ...
        return CompletableFuture.completedFuture(null);
    }
}
```

> **指定方法**：`@Async("beanName")` 绑定指定的 ThreadPoolTaskExecutor Bean。

## 5. 返回值：CompletableFuture

需要拿异步结果：

```java
@Service
public class DataService {

    @Async("exportExecutor")
    public CompletableFuture<String> export(UserQuery q) {
        String jobId = doExport(q);
        return CompletableFuture.completedFuture(jobId);
    }
}

// 调用方
CompletableFuture<String> f = dataService.export(q);
String jobId = f.get(10, TimeUnit.SECONDS);  // 阻塞等结果，超时保护
```

> 注意：返回类型必须是 CompletableFuture（或 Future），否则不能走异步逻辑；void 方法天然适配"跑完就完"。

## 6. 拒绝策略选型

| 策略 | 行为 | 适用 |
| --- | --- | --- |
| `AbortPolicy`（默认） | 直接抛 RejectedExecutionException | 宁可报错也不丢 |
| `CallerRunsPolicy`（推荐） | 回退调用线程同步执行 | 不丢任务、保吞吐，可降级 |
| `DiscardPolicy` | 静默丢弃 | 可丢弃的统计/日志类 |
| `DiscardOldestPolicy` | 丢弃队列最旧任务 | 时效性场景 |

生产兜底：`CallerRunsPolicy` 最稳（不丢任务不爆内存，代价是调用线程被拖慢）。

## 7. 监控线程池

接入指标（配合 Actuator/Prometheus，见 [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md) / [12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md)）：

```java
@Configuration
public class ThreadPoolMonitor {
    @Bean
    public MeterBinder threadPoolMetrics(ThreadPoolTaskExecutor executor) {
        return registry -> Gauge.builder("biz.async.pool.active", executor, e -> e.getActiveCount())
                .description("活动线程数").register(registry);
    }
}
```

> 至少盯：`activeCount` / `queueSize` / 拒绝次数（加个计数器）。队列长期接近满 + active 近 max = 该扩池或重估并发模型了。

## 8. 踩坑速查（▲ 失效场景务必躲")

- **@Async 不生效**：① 没 `@EnableAsync`；② 同 Class 内部自调用（`this.asyncMethod()`），代理不拦截——必须从外部 Bean 调用，或改用 `ApplicationContext.getBean` 拿到代理；③ 方法 `final`/`private`（CGLIB 代理不了）。
- **裸用默认池 OOM**：见第 1 节，必须自定义有界队列执行器。
- **无界队列**：`LinkedBlockingQueue` 不设容量=无限入队，照样爆内存；用 `setQueueCapacity` 有界。
- **返回类型不是 Future**：返回普通对象时异步不生效（代理期望 Future 类型签名）。
- **事务 + 异步**：`@Async` 与 `@Transactional` 一起时注意——异步方法在新线程执行，事务传播/ThreadLocal（如登录态）在线程间不共享。见解析详解篇。
- **停机丢任务**：没设 `waitForTasksToCompleteOnShutdown`，容器关闭瞬间把排队任务干掉。
- **线程名前缀没设**：日志里看不出是异步线程，排查困难。

## 9. 小结

- 先自定义有界队列执行器，再谈 @Async——这是防 OOM 的第一道闸。
- 多业务多池隔离；`@Async("beanName")` 指定池。
- 拒绝策略优先 `CallerRunsPolicy`（保命不丢任务）。
- 最易踩的三个失效：没 EnableAsync / 类内自调用 / 返回类型非 Future。
- 监控队列与活跃线程，指标比调参更早发现问题。

## 10. 关联笔记

- 理论篇：[07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)
- [11-SpringBoot Actuator监控详解](11-SpringBoot Actuator监控详解.md)：线程池指标暴露
- [12-SpringBoot Actuator监控实践](12-SpringBoot Actuator监控实践.md)：Prometheus 对接实例
- [03-SpringBoot配置体系与外部化配置实践](03-SpringBoot配置体系与外部化配置实践.md)：池参数可用 @ConfigurationProperties 外部化

## 11. 参考资料

- [Baeldung 中文：Spring 中的 @Async 使用指南](https://www.baeldung-cn.com/spring-async)，查询日期 2026-08-15
- [ByteZoneX：Spring Boot @Async OOM？实战解决线程池失控问题](https://www.bytezonex.com/archives/spring-boot-async-oom-thread-pool-fix.html)，查询日期 2026-08-15
- [geekcoder.org：Spring Boot 的异步线程池：原理、配置与最佳实践](https://www.geekcoder.org/blog/springboot-de-yi-bu-xian-cheng-chi/)，查询日期 2026-08-15
