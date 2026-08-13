---
tags: [Java, Spring, 事件, 实践, 监听器, ApplicationEvent]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring事件驱动机制实践

> 版本基线：Spring 5.x。先读 [13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md)；本篇给事件/监听器/发布三件怎么配、怎么用。
> 前置：[13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md)（观察者模式）。

## 📋 总纲

1. 三个角色（事件/监听器/发布）
2. 发布-订阅最小可用示例
3. 监听方式三种写法
4. 事务事件 & 异步
5. 注意点与踩坑

## 1. 三个角色

Spring 事件 = 观察者模式在容器里的落地：
- **事件**（`ApplicationEvent` 子类）：携带数据
- **监听器**（`@EventListener`/`ApplicationListener`）：订阅响应
- **发布器**（`ApplicationEventPublisher`）：触发

## 2. 最小可用示例

```java
// ① 事件对象（volatile 数据容器）
public class OrderCreatedEvent extends ApplicationEvent {
    public final Long orderId;
    public OrderCreatedEvent(Object source, Long orderId) {
        super(source); this.orderId = orderId;
    }
}

// ② 监听器（订阅）
@Component
public class OrderEventListener {
    @EventListener
    public void onOrder(OrderCreatedEvent e) {
        System.out.println("订单已创建 id=" + e.orderId);   // 业务：发通知/日志/扣库存
    }
}

// ③ 发布（业务处触发）
@Service
public class OrderService {
    @Autowired private ApplicationEventPublisher publisher;
    public void createOrder(Long id) {
        // ...保存订单
        publisher.publishEvent(new OrderCreatedEvent(this, id));   // 同步广播给所有监听器
    }
}
```

## 3. 监听方式的三种写法（择一）

| 方式 | 写法 | 说明 |
| --- | --- | --- |
| 注解（推荐） | `@EventListener` 标注方法，参数=监听的事件类型 | 现代、免实现接口 |
| 实现接口 | `implements ApplicationListener<OrderCreatedEvent>` | 传统 |
| 泛型事件 | `@EventListener(condition="#e.orderId > 0")` | 按 SpEL 条件过滤 |

## 4. 事务事件 & 异步

```java
@EventListener
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)  // 事务提交后才响应
public void afterTx(OrderCreatedEvent e) { ... }
```
- **`AFTER_COMMIT`**：事务提交成功后才触发，避免"事件先发但事务没提交"。失败不触发。
- **`BEFORE_COMMIT` / `AFTER_ROLLBACK`** 等 phase 见详解。

```java
@Async            // 异步执行监听器（需开 @EnableAsync）
@EventListener
public void async(OrderCreatedEvent e) { ... }   // 不阻塞发布线程
```

## 5. 注意点与踩坑（事件机制经典坑）

- **同步默认**：`publisher.publishEvent` 默认**同步阻塞**调用监听器；要异步须 `@Async`+`@EnableAsync`，否则耗时监听拖垮主流程。
- **一个事件多个监听器**：全部都会执行（广播）；顺序靠 `@Order`（小先）。
- **监听器异常会传导**：同步监听器抛异常会往上抛给发布处 → 可能让业务方法失败。要隔离用 `@Async` 或 try-catch。
- **事务内发事件但没提交**：普通 `@EventListener` 在事务提交前就触发，读不到已提交数据 → 用 `@TransactionalEventListener(AFTER_COMMIT)`。
- **方法参数是接口/父类**：事件类型匹配按参数实际类型，父类事件会被父类监听器接住（注意命中）。
- **死循环**：监听器里又 publishEvent 同一类事件会无限递归，注意。

## 6. 关联

- 详解：[13-Spring事件驱动机制详解](13-Spring事件驱动机制详解.md)
- 上一篇：[12-SpEL表达式实践](12-SpEL表达式实践.md)
- 下一篇（可选）：springboot 域 [05-SpringBoot异步与线程池详解](../springboot/05-SpringBoot异步与线程池详解.md)（@Async 与线程池）
