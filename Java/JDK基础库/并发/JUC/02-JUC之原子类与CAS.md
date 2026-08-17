---
tags: [JUC, 原子类, CAS, AtomicInteger, LongAdder, 无锁, 并发, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JDK基础库/并发/JUC）
归属: 01-学习/Java/JDK基础库/并发/JUC
---

# 02-JUC之原子类与CAS

> 版本基线：JDK 5 引入原子类，JDK 8 新增 LongAdder/LongAccumulator
> 受众：Java 后端开发，已懂 synchronized（[01-多线程基础详解](../01-多线程基础详解.md)）和 volatile（[Java volatile详解](../Java volatile详解.md)），要掌握无锁原子操作。默认你懂线程、内存模型。
> 关联笔记：[00-JUC总览](00-JUC总览.md)、[01-JUC之锁与AQS](01-JUC之锁与AQS.md)、[JMM内存模型详解](../../../JVM/JMM内存模型详解.md)

## 📋 总纲

- 1. 为什么需要原子类
- 2. CAS 原理（核心）★
- 3. CAS 的三大问题
- 4. 原子类分类
- 5. 常用原子类详解
- 6. LongAdder 与 AtomicLong 对比
- 7. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清原子类解决的问题（volatile 不保证原子性）
2. **讲透 CAS 原理**：比较-交换，无锁实现原子操作
3. 说出 CAS 三大问题（ABA/自旋开销/只能单变量）
4. 分类使用原子类（基本类型/引用/数组/字段更新器/累加器）
5. 对比 LongAdder vs AtomicLong 并正确选型
6. 避免原子类的误用（复合操作不适用）

## 前置知识

- [JMM内存模型详解](../../../JVM/JMM内存模型详解.md)——可见性/原子性概念
- [01-多线程基础详解](../01-多线程基础详解.md)——synchronized 局限
- 需掌握：volatile、线程安全概念

---

## 1. 为什么需要原子类

**痛点**：`i++` 不是原子操作（读-改-写三步），volatile 只保证可见性不保证原子性：

```java
volatile int count = 0;
count++;   // ❌ 三步操作, 多线程下会丢更新
```

**synchronized 太重**：加锁有线程阻塞/唤醒开销。

**原子类方案**：AtomicInteger 等用 **CAS（无锁）** 实现原子操作，性能更好：

```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();   // ✅ 原子自增, 无锁
```

---

## 2. CAS 原理（核心）★

**一句话记忆**：CAS（Compare And Swap）是**比较并交换**——先比较内存值是否等于期望值，相等才更新为新值，全程原子（CPU 指令级别），不相等则重试。

```java
// 伪代码: CAS 语义
boolean compareAndSwap(int expect, int update) {
    if (memoryValue == expect) {     // 比较: 内存值是否还是预期值
        memoryValue = update;        // 交换: 是则更新
        return true;
    }
    return false;                    // 否: 已被别人改过, 返回失败
}
```

**硬件支持**：CAS 由 CPU 指令保证原子性（如 x86 的 `CMPXCHG`），Java 通过 Unsafe 调用。

### 自旋重试

```java
// AtomicInteger.incrementAndGet 内部逻辑(简化)
int current;
do {
    current = get();                     // 读当前值
} while (!compareAndSet(current, current + 1));  // CAS 失败就重读重试(自旋)
return current + 1;
```

> 💡 **记忆锚点**：**CAS = "我先看一眼，没变才动手"**——乐观锁思想，不加锁、不阻塞，靠失败重试保证正确。

---

## 3. CAS 的三大问题

| 问题 | 说明 | 解决方案 |
|---|---|---|
| **ABA 问题** | A→B→A，CAS 认为没变（实际变过） | AtomicStampedReference（版本号） |
| **自旋开销** | 高竞争下 CAS 反复失败空转，耗 CPU | LongAdder（分段累加）/ 退避策略 |
| **只能保证单变量** | CAS 只能操作一个变量 | 用锁；或 AtomicReference 包对象 |

### ABA 问题详解

```java
// 场景: 线程1读A, 线程2改A→B→A, 线程1 CAS 成功(但数据已被改过)
AtomicInteger ai = new AtomicInteger(1);
// 解决: 带版本号
AtomicStampedReference<Integer> ref = new AtomicStampedReference<>(1, 0);
ref.compareAndSet(1, 2, 0, 1);   // 值 + 版本号都匹配才更新
```

---

## 4. 原子类分类

| 分类 | 代表类 |
|---|---|
| **基本类型** | AtomicInteger / AtomicLong / AtomicBoolean |
| **引用类型** | AtomicReference / AtomicStampedReference / AtomicMarkableReference |
| **数组** | AtomicIntegerArray / AtomicLongArray / AtomicReferenceArray |
| **字段更新器** | AtomicIntegerFieldUpdater / AtomicLongFieldUpdater / AtomicReferenceFieldUpdater |
| **累加器**（JDK8） | LongAdder / LongAccumulator / DoubleAdder |

---

## 5. 常用原子类详解

### 5.1 AtomicInteger（最常用）

```java
AtomicInteger ai = new AtomicInteger(10);

ai.get();                    // 读取: 10
ai.set(20);                  // 写入: 20
ai.incrementAndGet();        // ++i: 21 (原子)
ai.getAndIncrement();        // i++: 返回20, 值21
ai.addAndGet(5);             // += 5: 26
ai.compareAndSet(26, 100);   // CAS: 期望26, 是则改100 → true
```

| 方法 | 说明 |
|---|---|
| `get()/set()` | 读取/写入（volatile 语义） |
| `incrementAndGet()/getAndIncrement()` | 自增（前置/后置） |
| `addAndGet()/getAndAdd()` | 加指定值 |
| `compareAndSet(expect, update)` | CAS 核心 |
| `getAndUpdate(IntUnaryOperator)` | 函数式更新（JDK8+） |

### 5.2 AtomicReference（对象引用）

```java
// 原子更新对象引用(如无锁栈/队列节点)
AtomicReference<Node> head = new AtomicReference<>(null);

// 无锁入栈
Node newNode = new Node(value);
Node oldHead;
do {
    oldHead = head.get();
    newNode.next = oldHead;
} while (!head.compareAndSet(oldHead, newNode));   // 自旋
```

### 5.3 AtomicIntegerFieldUpdater（字段更新器）

**场景**：不想把整个对象包成 AtomicReference，只想原子更新某个字段（字段必须 volatile）：

```java
// 字段必须 volatile!
class Counter { volatile int count; }

AtomicIntegerFieldUpdater<Counter> updater =
        AtomicIntegerFieldUpdater.newUpdater(Counter.class, "count");

Counter c = new Counter();
updater.incrementAndGet(c);   // 原子更新 c.count
```

---

## 6. LongAdder 与 AtomicLong 对比 ★

| 维度 | AtomicLong | LongAdder |
|---|---|---|
| 原理 | 单值 + CAS 自旋 | **分段累加**（Cell 数组，各线程累加到自己的 Cell） |
| 高竞争性能 | CAS 自旋损耗大 | ✅ 明显更好（分段分散竞争） |
| 读取 | 实时精确 | sum() 遍历 Cell 求和（略慢但准确） |
| 适用 | 竞争低/需要精确返回值 | **超高并发累加**（计数器/统计） |

```java
// 高并发计数: LongAdder 更优
LongAdder counter = new LongAdder();
counter.increment();
counter.increment();
long total = counter.sum();   // 2

// 对比: AtomicLong 适合需要单个精确值且竞争不激烈的场景
```

> 💡 **记忆锚点**：**AtomicLong 是"单窗口排队"，LongAdder 是"多个窗口同时收"**——LongAdder 牺牲一点读取精确性（sum 遍历），换超高并发下的写入性能。

---

## 7. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #A1 | 原子类做复合操作 | 检查-再操作（如 if(get()>0) then decrement）竞态 | 用 getAndUpdate 原子函数/锁 |
| #A2 | 高竞争用 AtomicLong | 性能瓶颈（自旋） | 换 LongAdder |
| #A3 | 忽略 ABA | 数据被改过但 CAS 成功 | AtomicStampedReference |
| #A4 | 字段更新器字段非 volatile | 更新不生效/异常 | 字段必须 volatile |
| #A5 | 以为 CAS 无代价 | 高竞争 CPU 飙高 | 合理选择：低竞争 CAS / 高竞争分段或锁 |
| #A6 | AtomicBoolean 当锁用 | 不可重入/无超时 | 需要重入/超时用 ReentrantLock（[01-JUC之锁与AQS](01-JUC之锁与AQS.md)） |

## 小结

- 原子类解决 volatile 不保证原子性的痛点，无锁实现原子操作
- **CAS 核心**：比较-交换，CPU 指令级原子，失败自旋重试
- 三大问题：ABA（版本号）/自旋开销（LongAdder）/单变量（AtomicReference/锁）
- 分类：基本类型/引用/数组/字段更新器/累加器
- 高并发计数用 LongAdder，精确单值用 AtomicLong

## 下一篇

[03-JUC之并发容器](03-JUC之并发容器.md)——线程安全的容器家族

## 参考资料

- [JavaGuide: 原子类](https://javaguide.cn/java/concurrent/atomic-classes.html)，查询日期：2026-08-09
- [java.util.concurrent.atomic 官方文档](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/atomic/package-summary.html)，查询日期：2026-08-09
