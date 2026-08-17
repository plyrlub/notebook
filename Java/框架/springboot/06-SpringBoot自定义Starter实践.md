---
tags: [Java, SpringBoot, Starter, 实践, 自动配置, 双模块, 条件注解, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot自定义Starter实战

> 版本基线：Spring Boot 3.x（Boot2 差异在文中标注）
> 受众：先读 [05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md)（双模块拆分/命名/原理），本篇一步步写一个**能跑的自定义 Starter**：基于 AOP + 线程池 的"耗时日志 Starter"。概念不清回详解。
> 前置：[05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md)；[01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)；Maven 多模块。

## 📋 总纲

1. 目标与成品：耗时日志 Starter（@CostLog）
2. 项目结构：三模块（autoconfigure / starter / 测试 app）
3. autoconfigure 模块：注解 + 切面 + 自动配置类
4. 配置属性绑定：@CostLogProperties
5. 注册：META-INF/spring/...AutoConfiguration.imports ★
6. starter 空模块：依赖聚合
7. 在业务工程里引入并验证
8. 踩坑速查

## 1. 目标与成品

做一个 `method-cost-spring-boot-starter`：给任意 `@Service` 方法加 `@CostLog` 注解，自动打印该方法的耗时（用 AOP 环绕通知 + 线程池异步上报）。验证点：
- 引入 starter 后自动装配生效（无需手动 @Bean）
- 配置 `cost.costlog.enabled` 可开关
- 属性经 `application.yml` 绑定，不生效字段有默认值

## 2. 项目结构（三模块标准）

```text
method-cost/
├── pom.xml                          # 父 pom（聚合三模块）
├── method-cost-spring-boot-autoconfigure/   # 核心：注解/切面/自动配置
└── method-cost-spring-boot-starter/         # 空模块，只聚合依赖
```

> 命名规范（官方）：`xxx-spring-boot-starter` + `xxx-spring-boot-autoconfigure`。可合并成两模块：`autoconfigure` 里放太多东西、`starter` 只做依赖中继。

**父 pom**（聚合）：

```xml
<modules>
    <module>method-cost-spring-boot-autoconfigure</module>
    <module>method-cost-spring-boot-starter</module>
</modules>
```

## 3. autoconfigure 模块

### 3.1 注解

```java
package com.example.costlog;

import java.lang.annotation.*;

/** 标注在方法上，统计执行耗时并上报 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface CostLog {
    String bizName() default "";   // 业务名，空则取方法名
}
```

### 3.2 配置属性（record + prefix）

```java
package com.example.costlog;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "cost.costlog")
public record CostProperties(boolean enabled, int thresholdMs) {
    public CostProperties {
        if (thresholdMs < 0) thresholdMs = 0;
    }
}
```

> `enabled` 默认 false？不——**record 默认字段是 0/false**，但业务期望"默认开"。解决：自动配置类里用 `@ConditionalOnProperty` 控制是否装配切面（见 3.4），默认 `havingValue` 不设即"有值即生效"，配合缺省默认更清晰。

### 3.3 切面（AOP 环绕）

```java
package com.example.costlog;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Aspect
public class CostLogAspect {
    private static final Logger log = LoggerFactory.getLogger(CostLogAspect.class);
    private final CostProperties props;
    private final AsyncReporter reporter;

    public CostLogAspect(CostProperties props, AsyncReporter reporter) {
        this.props = props; this.reporter = reporter;
    }

    @Around("@annotation(costLog)")
    public Object around(ProceedingJoinPoint pjp, CostLog costLog) throws Throwable {
        long start = System.nanoTime();
        try {
            return pjp.proceed();
        } finally {
            long costMs = (System.nanoTime() - start) / 1_000_000;
            reporter.report(costLog.bizName(), pjp.getSignature().toString(), costMs);
            if (costMs >= props.thresholdMs()) {
                log.warn("[CostLog] {} 耗时 {}ms 超过阈值 {}ms", costLog.bizName(), costMs, props.thresholdMs());
            }
        }
    }
}
```

### 3.4 异步上报器 + 自动配置类

```java
package com.example.costlog;

public class AsyncReporter {
    public void report(String bizName, String method, long costMs) {
        // 简化：这里异步/打印。真正可接日志/监控/MQ
        System.out.println("[CostLog] " + bizName + " " + method + " = " + costMs + "ms");
    }
}
```

**自动配置类**——灵魂：把上面所有 Bean 按条件装配，用户无感依赖就是好 Starter。

```java
package com.example.costlog;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

@AutoConfiguration           // Boot3 用 @AutoConfiguration，不是 @Configuration
@EnableConfigurationProperties(CostProperties.class)
@ConditionalOnProperty(prefix = "cost.costlog", name = "enabled", havingValue = "true", matchIfMissing = true)
                                    // 默认启动；配 enabled: false 即关闭整个切面
public class CostAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean       // 用户可自备覆盖
    public AsyncReporter asyncReporter() {
        return new AsyncReporter();
    }

    @Bean
    @ConditionalOnMissingBean
    public CostLogAspect costLogAspect(CostProperties props, AsyncReporter reporter) {
        return new CostLogAspect(props, reporter);
    }
}
```

> Boot2 用 `@Configuration`；Boot3 必须 `@AutoConfiguration`（否则不参与 .imports 扫描）。见 [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md) 变化。

## 4. 注册文件（★ 最容易漏的一步）

Boot3 在 `autoconfigure` 模块的 `src/main/resources/META-INF/spring/` 下建：

```text
# 文件：src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.example.costlog.CostAutoConfiguration
```

> Boot2 则是 `META-INF/spring.factories`，键 `org.springframework.boot.autoconfigure.EnableAutoConfiguration`。**放错路径/目录 = 自动装配静默失败**（不报错但 Bean 全没有——最隐蔽的坑）。

## 5. starter 空模块（依赖聚合）

`method-cost-spring-boot-starter` 里**不写业务代码**，pom 只聚合 autoconfigure + 依赖：

```xml
<artifactId>method-cost-spring-boot-starter</artifactId>

<dependencies>
    <dependency>
        <groupId>com.example</groupId>
        <artifactId>method-cost-spring-boot-autoconfigure</artifactId>
    </dependency>
    <!-- 关键：把用户不需要自己 import 的第三方依赖收进来 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-aop</artifactId>
    </dependency>
</dependencies>
```

> 作用：用户只需引 `method-cost-spring-boot-starter` 一个依赖，AOP 等全部到位。若 autoconfigure 依赖了可选的第三方，用 `<optional>true</optional>` 防止强制传递。

## 6. 在业务工程里引入并验证

业务工程 `pom.xml`：

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>method-cost-spring-boot-starter</artifactId>
    <version>0.0.1-SNAPSHOT</version>
</dependency>
```

`application.yml`（可选覆盖）：

```yaml
cost:
  costlog:
    enabled: true
    threshold-ms: 500
```

业务代码：

```java
@Service
public class OrderService {

    @CostLog(bizName = "createOrder")          // 加注解即生效，无需其他配置
    public Order createOrder(Order req) {
        // 业务逻辑...
        return req;
    }
}
```

**验证清单**（对"/先验证是否生效"）：
- 启动无报错，且日志能看到切面打出的耗时 → 自动装配成功
- 把 `enabled: false`，重启后 @CostLog 不打印 → 条件装配开关生效
- 不写 `threshold-ms`，看默认值兜底 → 属性绑定默认值生效

## 7. 踩坑速查

- **.imports 路径错**：Boot3 必须 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`；一个都不生效排查第一位。
- **用 @Configuration 而非 @AutoConfiguration**：Boot3 不注册。
- **属性全 null**：`prefix` 拼错 / record 参数名与 yml key 松散绑定不上。
- **切面不生效**：缺 `spring-boot-starter-aop`；@Around 参数 `@annotation(xxx)` 类型/参数名不匹配条件注解。
- **版本冲突**：starter 传递依赖与主项目相撞，用 dependencyManagement 仲裁或排除。
- **重复 Bean**：`@ConditionalOnMissingBean` 没加，用户也想自定义时冲突。
- **autoconfigure 依赖了业务不需要的大库**：务必标 optional，避免污染用户依赖树。

## 8. 小结

- 三步走：`autoconfigure`（注解+切面+自动配置类）→ `.imports` 注册 → `starter` 空模块聚合。
- `@AutoConfiguration`(Boot3) + `@ConfigurationProperties` + `@ConditionalOnXxx` 是骨架。
- `@ConditionalOnMissingBean` 让用户可覆盖；`@ConditionalOnProperty` 提供开关。
- 用户侧体验 = "引依赖 + 加注解 + 配可选 yml"，这才是好 Starter。

## 9. 关联笔记

- 前面（理论）篇：[05-SpringBoot自定义Starter详解](05-SpringBoot自定义Starter详解.md)
- [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)：@EnableAutoConfiguration/.imports 机制原理
- [04-SpringBoot模块化详解](04-SpringBoot模块化详解.md)：Boot4 对 starter/.imports 的演进
- [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)：@ConfigurationProperties 绑定
- [07-SpringBoot异步与线程池详解](07-SpringBoot异步与线程池详解.md)：本例 AsyncReporter 可用线程池增强

## 10. 参考资料

- [Spring Boot 官方：Developing Auto-configuration](https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html)，查询日期 2026-08-15
- [Spring Boot 官方：Creating Your Own Auto-configuration](https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html#features.developing-auto-configuration.creating-an-auto-configuration)，查询日期 2026-08-15
- [深入理解 Spring Boot 自定义 Starter：从原理到实战（腾讯云）](https://cloud.tencent.com/developer/article/2560722)，查询日期 2026-08-15
