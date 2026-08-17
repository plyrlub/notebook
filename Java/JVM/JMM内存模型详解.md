---
tags: [JMM, Java内存模型, 可见性, 有序性, happens-before, JVM, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/JVM）
归属: 01-学习/Java/JVM
---

# JMM内存模型详解

> 版本基线：JSR-133（Java 内存模型规范），JDK 5+ 全面生效
> 受众：Java 后端开发，已懂 [01-多线程基础详解](../JDK基础库/并发/01-多线程基础详解.md) 的并发三要素，要理解可见性/有序性的底层原理。默认你懂线程、CPU 缓存基本概念。
> 关联笔记：[00-并发编程总览](../JDK基础库/并发/00-并发编程总览.md)、[01-多线程基础详解](../JDK基础库/并发/01-多线程基础详解.md)、[Java volatile详解](../JDK基础库/并发/Java volatile详解.md)、[01-JUC之锁与AQS](../JDK基础库/并发/JUC/01-JUC之锁与AQS.md)

## 📋 总纲

- 1. JMM 是什么：规范而非实现
- 2. 主内存与工作内存
- 3. 内存交互八大操作
- 4. 三大特性与 JMM 的关系
- 5. happens-before 规则
- 6. 与 volatile 的关系
- 7. 常见踩坑

## 学习目标

学完本篇你能：

1. 说清 JMM 是"规范"（抽象内存模型）而非 JVM 实际内存结构
2. 画出主内存/工作内存模型并解释可见性问题根源
3. 说出内存交互八大操作（lock/unlock/read/load/use/assign/store/write）
4. 讲清 happens-before 规则（重点：程序次序/volatile/锁/传递性）
5. 理解 volatile 如何保证可见性+有序性（不保证原子性）
6. 与 [Java volatile详解](../JDK基础库/并发/Java volatile详解.md) 衔接，理解 JMM 与锁的关系

## 前置知识

- [01-多线程基础详解](../JDK基础库/并发/01-多线程基础详解.md)——并发三要素、线程状态
- [Java volatile详解](../JDK基础库/并发/Java volatile详解.md)——volatile 的实战与原理（本篇理论衔接）
- 需掌握：CPU 缓存、指令重排序基本概念

---

## 1. JMM 是什么：规范而非实现

**一句话记忆**：JMM（Java Memory Model）是一套**规范**，定义了多线程读写共享变量的**内存可见性规则**，屏蔽不同硬件/操作系统差异，让 Java 程序"一次编写到处并发正确"。

**关键认知**：JMM 不是 JVM 的实际内存布局（堆/栈/方法区是运行时结构），而是一个**抽象模型**——用"主内存 + 工作内存"的概念描述线程间如何共享数据。

```
线程A ──工作内存(副本)──┐
                        ├── 主内存(共享变量)  ← 所有线程共享
线程B ──工作内存(副本)──┘
```

> 💡 **记忆锚点**：**JMM 是"交通规则"，JVM 内存结构是"道路"**——规则规定变量怎么在线程间可见，道路怎么铺是 JVM 的事。

---

## 2. 主内存与工作内存

| 内存 | 含义 | 类比 |
|---|---|---|
| **主内存** | 所有线程共享，存储共享变量 | 公司公告栏 |
| **工作内存** | 每个线程私有，存变量副本 | 个人记事本 |

**规则**：
- 线程对变量的所有操作（读/写）都必须在**工作内存**中进行
- 不能直接读写主内存变量
- 不同线程无法直接访问对方工作内存
- 变量传递必须通过主内存完成

**可见性问题根源**：线程 A 改了工作内存的副本，没同步回主内存 → 线程 B 读主内存还是旧值 → 这就是 [01-多线程基础详解](../JDK基础库/并发/01-多线程基础详解.md) 说的"可见性"问题的由来。

---

## 3. 内存交互八大操作

JMM 定义了 8 种操作，规定了主内存与工作内存之间的交互：

| 操作 | 作用 | 涉及内存 |
|---|---|---|
| **lock** | 锁定主内存变量（独占） | 主内存 |
| **unlock** | 解锁主内存变量 | 主内存 |
| **read** | 从主内存读取变量到工作内存 | 主内存→工作内存 |
| **load** | 把 read 的值放入工作内存副本 | 工作内存 |
| **use** | 把工作内存值传给执行引擎 | 工作内存 |
| **assign** | 把执行引擎赋值写回工作内存 | 工作内存 |
| **store** | 把工作内存值传回主内存 | 工作内存→主内存 |
| **write** | 把 store 的值写入主内存变量 | 主内存 |

**约束规则**（关键几条）：
- read 和 load、store 和 write 必须**成对出现**
- 不允许一个线程**丢弃**最近的 assign 操作（改了必须同步）
- 不允许线程**无原因**地把数据从工作内存同步回主内存
- 变量在 lock 前必须先清空工作内存副本（保证读最新）

---

## 4. 三大特性与 JMM 的关系

| 特性 | JMM 保证方式 |
|---|---|
| **原子性** | lock/unlock + synchronized（monitorenter/monitorexit）；基本类型读写（除 long/double 非 volatile 外）有原子性保证 |
| **可见性** | volatile（写后立即同步主内存、读前强制刷新）+ synchronized（解锁前同步）+ final（初始化后可见） |
| **有序性** | volatile（禁止重排序）+ synchronized（同一锁串行）+ happens-before 规则 |

> ⚠️ **易错点**：**原子性 ≠ 可见性**——`i++` 是"读-改-写"三步，volatile 只保证可见性不保证原子性（这是 [02-JUC之原子类与CAS](../JDK基础库/并发/JUC/02-JUC之原子类与CAS.md) 存在的意义）。

---

## 5. happens-before 规则 ★

**happens-before**（先行发生）：如果操作 A happens-before 操作 B，则 A 的结果对 B **可见**，且 A 的执行顺序在 B 之前。是 JMM 判断数据是否竞争的依据。

**核心规则**：

| 规则 | 说明 |
|---|---|
| **程序次序规则** | 单线程内，代码顺序即执行顺序（按书写先后） |
| **volatile 规则** | volatile 变量的**写** happens-before 后续对该变量的**读** |
| **锁规则** | unlock happens-before 后续对同一锁的 lock |
| **传递性** | A happens-before B，B happens-before C → A happens-before C |
| **线程启动** | start() happens-before 线程内的任何操作 |
| **线程终止** | 线程所有操作 happens-before 其他线程检测到它终止（join 返回） |
| **中断** | interrupt() happens-before 被中断线程检测到中断 |

**实战意义**：
- 不用 happens-before 规则保证的操作，顺序不可预测（可能被重排序）
- 合理利用规则：**共享变量先写后 volatile 读，或先 unlock 后 lock**，就能安全传递

```mermaid
flowchart LR
    A["写操作(先执行)"] -->|"程序次序/volatile/锁 等规则"| B["读操作(后执行)"]
    B -->|"保证"| C["结果可见 + 顺序确定"]
```

```java
// 例:volatile 规则保证可见性
volatile boolean ready = false;
// 线程A: data = 42; ready = true;      ← data 写 happens-before ready 写
// 线程B: if (ready) { 读 data }        ← ready 读 happens-before 后续, 且传递性保证 data 可见
```

---

## 6. 与 volatile 的关系

| 能力 | volatile | synchronized |
|---|---|---|
| 可见性 | ✅ 写后同步、读前刷新 | ✅ 解锁同步 |
| 有序性 | ✅ 禁止重排序 | ✅ 串行化 |
| 原子性 | ❌ 不保证 | ✅ 保证 |
| 适用 | 状态标志、单写多读 | 复合操作、临界区 |

**volatile 适用场景**：
- 状态标志（如 `volatile boolean running`）
- 单线程写、多线程读（发布不可变状态）
- 与锁配合：先 volatile 写后读实现安全发布

**详细原理见 [Java volatile详解](../JDK基础库/并发/Java volatile详解.md)**（本机实测：可见性 Demo 复现、MESI 时序图、happens-before 链）。

---

## 7. 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #M1 | 以为 volatile 保证原子性 | i++ 结果错误 | 复合操作用原子类/锁 |
| #M2 | 非 volatile 的 long/double | 64 位拆分读写，可能读到"半个值" | volatile 修饰或加锁 |
| #M3 | 忽略 happens-before 传递性 | 以为两个 volatile 之间无关联 | 善用规则链传递可见性 |
| #M4 | 把 JMM 当 JVM 内存结构 | 概念混淆 | JMM 是抽象规范，不是堆/栈 |
| #M5 | 重排序理解成"代码乱序执行" | 误解语义 | 重排序只影响可见性/时序，单线程语义不变 |

## 小结

- JMM = 抽象规范（主内存 + 工作内存），屏蔽硬件差异，定义可见性规则
- 可见性问题根源：工作内存副本不同步
- 八大操作 + 约束规则定义内存交互
- happens-before 规则是判断数据竞争的核心工具（volatile/锁/传递性最常用）
- volatile 保证可见性+有序性，不保证原子性；原子性交给 synchronized/原子类

## 下一篇

[Java GC详解](Java GC详解.md)——垃圾回收与内存管理（JVM 系列继续）

## 参考资料

- [JavaGuide: JMM 详解](https://javaguide.cn/java/concurrent/jmm.html)，查询日期：2026-08-09
- [JSR-133: Java Memory Model](https://jcp.org/en/jsr/detail?id=133)，查询日期：2026-08-09
