---
tags: [JUC, ReentrantLock, AQS, 锁, 读写锁, 并发, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/JUC）
归属: 01-学习/Java/JDK基础库/并发/JUC
---

# 01-JUC之锁与AQS

> 版本基线：JDK 8+（AQS 自 JDK 5 引入，Doug Lea 设计）
> 受众：Java 后端开发，已会用 synchronized（[01-多线程基础详解](../01-多线程基础详解.md)），要掌握 JUC 锁体系与 AQS 原理。默认你懂线程状态、CAS 概念。
> 关联笔记：[00-JUC总览](00-JUC总览.md)、[JMM内存模型详解](../../../JVM/JMM内存模型详解.md)、[02-JUC之原子类与CAS](02-JUC之原子类与CAS.md)

## 📋 总纲

- 1. 锁体系全景
- 2. ReentrantLock 详解
- 3. AQS 原理（核心）★
- 4. 公平锁与非公平锁
- 5. ReentrantReadWriteLock
- 6. Lock 与 synchronized 对比
- 7. 常见踩坑

## 学习目标

学完本篇你能：

1. 说出 JUC 锁体系（ReentrantLock/ReadWriteLock/StampedLock）
2. 熟练使用 ReentrantLock（lock/unlock/tryLock/lockInterruptibly）
3. **讲清 AQS 核心原理**：volatile state + CLH 变体队列 + CAS
4. 说清公平锁/非公平锁的实现差异
5. 用 ReentrantReadWriteLock 优化读多写少场景
6. 对比 Lock 与 synchronized 并给出选型

## 前置知识

- [01-多线程基础详解](../01-多线程基础详解.md)——synchronized 原理与使用
- [JMM内存模型详解](../../../JVM/JMM内存模型详解.md)——锁规则 happens-before
- 需掌握：CAS 概念（[02-JUC之原子类与CAS](02-JUC之原子类与CAS.md) 有详解）

---

## 1. 锁体系全景

```
Lock 接口
├── ReentrantLock          可重入独占锁(最常用)
├── ReentrantReadWriteLock 读写锁(读共享/写独占)
│   └── StampedLock        增强版(乐观读,JDK8)
└── 基于 AQS (AbstractQueuedSynchronizer)
```

**AQS 是核心**：以上锁（以及 [04-JUC之工具类](04-JUC之工具类.md) 的 Semaphore/CountDownLatch）都基于 AQS 实现。

---

## 2. ReentrantLock 详解

### 2.1 基本使用

```java
ReentrantLock lock = new ReentrantLock();
try {
    lock.lock();                    // 加锁(阻塞)
    // 临界区代码
} finally {
    lock.unlock();                  // 必须 finally 释放!
}
```

### 2.2 核心方法

| 方法 | 作用 |
|---|---|
| `lock()` | 获取锁（阻塞，不可中断） |
| `unlock()` | 释放锁（必须 finally） |
| `tryLock()` | 尝试获取（立即返回 true/false） |
| `tryLock(timeout, unit)` | 限时尝试（超时返回 false） |
| `lockInterruptibly()` | 可中断获取（响应 interrupt） |
| `isLocked()/isHeldByCurrentThread()` | 状态查询 |
| `newCondition()` | 创建条件变量（多条件等待/通知） |

### 2.3 Condition 多条件（比 wait/notify 强）

```java
ReentrantLock lock = new ReentrantLock();
Condition notFull = lock.newCondition();   // 可多个条件!
Condition notEmpty = lock.newCondition();

// 生产者
lock.lock();
try {
    while (queue.isFull()) notFull.await();   // 队列满则等
    queue.put(data);
    notEmpty.signal();                        // 唤醒消费者
} finally {
    lock.unlock();
}
```

**对比 wait/notify**：synchronized 只有一个等待集，Condition 可以分多个（如"不满"和"不空"独立唤醒），更精细。

---

## 3. AQS 原理（核心）★

### 3.1 核心思想

**一句话记忆**：AQS 用 **volatile int state（同步状态）+ CLH 变体 FIFO 队列 + CAS** 实现锁的获取与释放——抢不到锁的线程包装成 Node 进队等待，前驱释放后唤醒后继。

```
state (volatile int)  ← 同步状态: 0=空闲, >0=被占用(可重入计数)
      │ CAS 修改
      ▼
等待队列 (CLH变体双向链表)
  head → Node(占位) → Node(线程A) → Node(线程B) → tail
```

### 3.2 三个核心要素

| 要素 | 作用 |
|---|---|
| **state** | volatile int 同步状态，CAS 原子修改 |
| **CLH 变体队列** | FIFO 双向链表，存等待线程（虚拟头节点占位） |
| **CAS** | 原子修改 state（compareAndSetState） |

### 3.3 模板方法（子类实现）

AQS 是模板方法模式，子类（如 ReentrantLock）实现钩子方法：

| 方法 | 用途 | 谁实现 |
|---|---|---|
| `tryAcquire(int arg)` | 独占获取（返回是否成功） | ReentrantLock |
| `tryRelease(int arg)` | 独占释放 | ReentrantLock |
| `tryAcquireShared(int arg)` | 共享获取（负数失败/0成功无余/正数成功有余） | Semaphore/CountDownLatch |
| `tryReleaseShared(int arg)` | 共享释放 | Semaphore/CountDownLatch |
| `isHeldExclusively()` | 是否独占 | 用到 Condition 才需要 |

### 3.4 获取锁流程（以 ReentrantLock 为例）

```
lock()
  → acquire(1)
      → tryAcquire(1)   // 子类实现: CAS 改 state, 成功则持有
      → 失败 → 线程封装为 Node 加入等待队列尾部
          → 自旋检查前驱是否 head(可抢锁)
          → 阻塞 (LockSupport.park)
          → 被唤醒后竞争锁
      → 成功 → 持有锁, 执行临界区
```

### 3.5 释放锁流程

```
unlock()
  → release(1)
      → tryRelease(1)   // 子类实现: state 减1, 减到0才真正释放
      → 成功 → 唤醒 head.next 节点线程 (LockSupport.unpark)
```

> 💡 **记忆锚点**：**AQS = 排队机制 + 状态管理**——state 表示锁被谁占了几次，队列管理"谁下一个"，CAS 保证并发安全。ReentrantLock 只关心"独占+重入"，Semaphore 关心"计数"，都是 AQS 这个骨架的不同皮肤。

---

## 4. 公平锁与非公平锁

| 类型 | 原理 | 特点 |
|---|---|---|
| **非公平锁**（默认） | 新线程**先抢一次**（CAS），失败才进队 | 吞吐高，可能"插队"导致饥饿 |
| **公平锁** | 直接进队，FIFO 严格按顺序 | 无饥饿，吞吐略低 |

```java
new ReentrantLock();              // 非公平(默认)
new ReentrantLock(true);          // 公平
```

**非公平为什么快**：线程刚被唤醒时，它的时间片还在，直接抢锁比进队再唤醒更高效（减少上下文切换）。

> ⚠️ **易错点**：非公平锁的"插队"只在**队列为空/刚释放**时发生，不会无限饿死（有队列机制兜底）。

---

## 5. ReentrantReadWriteLock

**场景**：读多写少（如缓存、配置中心）——读读不互斥，读写/写写互斥。

```java
ReentrantReadWriteLock rwLock = new ReentrantReadWriteLock();
Lock readLock = rwLock.readLock();    // 共享锁: 可多个线程同时持有
Lock writeLock = rwLock.writeLock();  // 独占锁: 与其他锁互斥

// 读操作
readLock.lock();
try { /* 多个线程可同时进入 */ } finally { readLock.unlock(); }

// 写操作
writeLock.lock();
try { /* 独占 */ } finally { writeLock.unlock(); }
```

| 特性 | 说明 |
|---|---|
| 读-读 | ✅ 并发（共享） |
| 读-写 | ❌ 互斥 |
| 写-写 | ❌ 互斥 |
| 锁降级 | 写锁可降级为读锁（先写后读） |
| 锁升级 | ❌ 不支持（读锁升级写锁会死锁） |

**锁降级示例**（缓存更新场景）：
```java
writeLock.lock();
try {
    // 更新缓存...
    readLock.lock();      // 降级: 先拿读锁
    writeLock.unlock();   // 释放写锁
    // 此时持有读锁, 可安全读最新值
} finally {
    readLock.unlock();
}
```

---

## 6. Lock 与 synchronized 对比

| 维度 | synchronized | ReentrantLock |
|---|---|---|
| 语法 | 简单（关键字） | 需手动 lock/unlock（finally） |
| 可中断 | ❌ | ✅ lockInterruptibly |
| 超时 | ❌ | ✅ tryLock(timeout) |
| 公平性 | 非公平 | 可配公平/非公平 |
| 多条件 | ❌ 单一等待集 | ✅ 多个 Condition |
| 性能（JDK6+） | 优化后接近 | 相近 |
| 适用 | 简单临界区 | 复杂需求（超时/中断/多条件） |

**选型**：
- 简单同步 → **synchronized**（代码简洁，JVM 优化好）
- 需要超时/中断/公平/多条件 → **ReentrantLock**
- 读多写少 → **ReentrantReadWriteLock**

---

## 7. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #L1 | unlock 不在 finally | 异常时锁不释放→死锁 | 必须 try/finally |
| #L2 | tryLock 忘记判断返回值 | 未拿到锁也进临界区 | `if (lock.tryLock()) { try {...} finally {unlock} }` |
| #L3 | 读写锁升级 | 死锁 | 只降级不升级 |
| #L4 | Condition await 用 if | 虚假唤醒 | while 循环条件 |
| #L5 | 公平锁误用 | 不必要地降低吞吐 | 默认非公平，需要防饥饿才用公平 |
| #L6 | 忘记可重入 | 嵌套调用自己死锁 | 理解可重入性（同一线程可重复获取） |

## 小结

- ReentrantLock：可重入独占锁，支持超时/中断/公平/多条件
- **AQS 核心**：volatile state + CLH 变体 FIFO 队列 + CAS，模板方法模式
- 公平锁直接进队，非公平锁先抢一次（吞吐高）
- ReentrantReadWriteLock：读读共享/读写互斥，锁降级可用、升级禁止
- 选型：简单用 synchronized，复杂用 Lock，读多写少用读写锁

## 下一篇

[02-JUC之原子类与CAS](02-JUC之原子类与CAS.md)——无锁并发编程

## 参考资料

- [JavaGuide: 从 ReentrantLock 实现看 AQS 原理](https://javaguide.cn/java/concurrent/reentrantlock.html)，查询日期：2026-08-09
- [美团技术: 不可不说的 Java 锁事](https://tech.meituan.com/2018/11/15/java-lock.html)，查询日期：2026-08-09
- [AQS 官方 Javadoc](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/locks/AbstractQueuedSynchronizer.html)，查询日期：2026-08-09
