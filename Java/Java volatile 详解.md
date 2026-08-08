---
tags: [Java, 并发, volatile, JMM, 面试]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/并发）
归属: 01-学习/Java/并发
---

# Java volatile 详解

## 📋 总纲

1. 基本概念：volatile 是什么、教学比喻与真实语义、快速上手
2. 使用场景：状态标志、安全发布、轻量级共享、选型对比
3. JMM 语义：可见性、有序性、传递性、原子性边界
4. 写读操作流程：从 Java 到硬件的完整链路
5. 底层原理（补充知识）：MESI、内存屏障、内存模型差异、性能代价
6. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 volatile 是什么

volatile 是 Java 的**轻量级同步关键字**，用于多线程共享变量的可见性与有序性控制。

**三特性总览**

    可见性 ✓   一个线程写 volatile，其他线程读必然看到最新值
    有序性 ✓   volatile 读写不会被编译器/CPU 重排序（有边界限制）
    原子性 ✗   不保证复合操作的原子性（i++ 该错还是错）

**定位**：比 synchronized 轻（无锁、无阻塞），比 Atomic 弱（只解决可见性+有序性，不解决复合原子性）。

### 1.2 「刷回主内存」只是教学比喻

网上最常见的说法：*「写 volatile 变量会立即刷回主内存，读会从主内存重新加载」* —— 这是**教学比喻**，不是 JMM 规范字句。

真实语义是 **happens-before 规则**：

    volatile 写 happens-before 后续对同一 volatile 的读

即：一个线程写 volatile 之后，另一个线程读到该 volatile 值时，**必然能看到写之前的所有操作结果**。中间没有字面意义上的「主内存同步」动作，实际靠内存屏障 + 缓存一致性协议完成（见第 4、5 章）。

### 1.3 快速上手（可运行 Demo ★）

```java
public class VolatileDemo {
    // 不加 volatile：主线程的修改可能永远不被工作线程看到
    private static volatile boolean running = true;

    public static void main(String[] args) throws InterruptedException {
        Thread worker = new Thread(() -> {
            long count = 0;
            while (running) {          // volatile 读
                count++;
            }
            System.out.println("工作线程停止，共执行: " + count);
        });
        worker.start();

        Thread.sleep(1000);
        running = false;               // volatile 写
        System.out.println("主线程已置 running=false");
    }
}
```

**验证**：把 `volatile` 去掉再跑 —— 工作线程大概率**永不停止**（JIT 优化 + 缓存导致读不到新值）；加上 volatile 后必停。这是可见性问题最直观的演示。

---

## 2. 使用场景

### 2.1 状态标志（最常用）

```java
public class TaskRunner {
    private volatile boolean stop = false;   // 开关/停止标志

    public void stop() { stop = true; }
    public void run() {
        while (!stop) { /* 干活 */ }
    }
}
```
- 适用：一个线程写、其他线程读的**开关类变量**
- 不需要原子性（布尔赋值本身就是原子的），volatile 正好够用

### 2.2 安全发布 / DCL 单例（发布语义）

```java
public class Singleton {
    private static volatile Singleton instance;   // ← 必须 volatile

    public static Singleton get() {
        if (instance == null) {                   // volatile 读（快速路径）
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();   // volatile 写
                }
            }
        }
        return instance;
    }
}
```

**为什么必须 volatile**：`new Singleton()` 三步可能重排序（分配内存 → 构造 → 引用赋值）。若步骤 2、3 重排，其他线程可能读到「非 null 但未构造完」的对象。volatile 保证：**引用赋值（volatile 写）之前的构造动作对读线程可见**（见 3.3 传递性）。

### 2.3 轻量级共享（读多写少）

```java
public class ConfigHolder {
    private volatile String configVersion = "v1";   // 配置版本号
    private volatile int maxRetry = 3;              // 配置项
}
```
- 适用：配置、指标、水位等**读频率远高于写**的共享数据
- volatile 读在 x86 上几乎免费（普通 load），多读场景无感

### 2.4 不适合的场景

**① 计数器 / 复合操作**

```java
private volatile int count = 0;
count++;        // ❌ 不是原子的：读-改-写三步，可能丢更新
```
- 需要原子性 → `AtomicInteger`

**② 多线程写同一个变量**

```java
private volatile long total = 0;   // 多线程各自 total += x
```
- volatile 只保证单次读写可见，不保证「基于旧值计算」的复合操作正确
- 需要 `AtomicLong` + `addAndGet` 或 LongAdder（高并发累加）

### 2.5 三兄弟选型

    场景                       选择
    布尔开关/状态标志          volatile
    单例发布 / 安全发布         volatile（配 synchronized）
    计数器/累加                 AtomicInteger / LongAdder
    复合操作需要原子性           Atomic*（CAS）
    需要互斥/临界区             synchronized / Lock
    读多写少共享值               volatile（读免费，写有代价）

**一句话**：只要「可见性+有序性」就 volatile；要「原子性」就 Atomic；要「互斥」就 synchronized/Lock。

---

## 3. JMM 语义（规范层）

### 3.1 可见性：happens-before 规则

JMM 的 happens-before 规则之一：

    对一个 volatile 变量的写，happens-before 后续对该变量的任意读

含义：
- 写线程写完 volatile，读线程读到后，**写之前的所有操作对读线程可见**
- 这不止作用于 volatile 变量本身（见 3.3）

### 3.2 有序性：重排序限制

JMM 针对 volatile 读写与普通读写，定义了 8 种组合的重排序规则：

| 第一个操作 | 第二个操作 | 能否重排序 |
|-----------|-----------|-----------|
| 普通读 | 普通读 | 可以 |
| 普通读 | 普通写 | 可以 |
| 普通写 | 普通读 | 可以 |
| 普通写 | 普通写 | 可以 |
| **volatile 读** | 任意操作 | **禁止** |
| **volatile 写** | 任意操作 | **禁止** |
| 任意操作 | **volatile 读** | **禁止** |
| 任意操作 | **volatile 写** | **禁止** |

即：**volatile 读写是双向屏障** —— 编译器/JIT/CPU 都不能让任何操作跨越 volatile 读写重排。

### 3.3 传递性：volatile 的「连坐」发布 ★

**volatile 写之前的所有普通变量写入，会随这次 volatile 写一起对其他线程可见**：

```java
// 线程 A                              // 线程 B
config = loadConfig();   // 普通写     while (!ready) { }   // volatile 读
ready = true;            // volatile写  use(config);         // 普通读
```

happens-before 链：`config 写 → ready 写 → ready 读 → config 读`，传递得到 `config 写 happens-before config 读` → B 必然看到完整 config。

**这就是 DCL 单例的理论基础**：instance 的 volatile 写「发布」了构造函数里的所有普通字段赋值。volatile 不只是让自己可见，它是**安全发布点**。

### 3.4 原子性边界与 long/double 特例

- volatile **不保证复合操作原子**（i++、x += 1）
- 但 JMM 规定：**volatile 的 long/double 读写是原子的**（JSR-133）
- 为什么强调：普通 long/double 在 32 位 JVM 上可能非原子（高 32 位、低 32 位分两次写，中间可能被其他线程读到撕裂值）→ 共享的 long/double 建议 volatile 修饰

---

## 4. 写读操作流程（硬件层）

> 先立认知：volatile 保证的是**顺序语义**（写已提交则读必然看见），不是**时间语义**（不是"写后立即广播到所有线程"）。

### 4.1 volatile 写流程

```java
x = 1;              // ① 普通写
flag = true;        // ② volatile 写
y = 2;              // ③ 普通写
```

**软件层（编译器/JIT）**

    ① JMM 要求：volatile 写 = 普通 store + 内存屏障
       写前插 StoreStore 屏障 → 阻止 ① 跑到 ② 后（x=1 先落定）
       写后插 StoreLoad 屏障 → 阻止 ③/后续读跑到 ② 前
    ② 编译器/JIT 不得把 volatile 写与任何操作重排序（见 3.2 表）

**硬件层（x86 视角）**

    ③ store 指令进入本核心的 store buffer（写缓冲）
    ④ 处理器发现 flag 缓存行不在「独占/修改」态
       → 发 RFO（Read For Ownership）+ 广播 invalidate
    ⑤ 其他核心收到 invalidate → 把自己的 flag 行标记 Invalid
    ⑥ StoreLoad 屏障（x86 上是 mfence / lock 前缀）冲刷 store buffer，
       让前面的写真正对外可见

**关键**：第 ④⑤ 步是「让其他线程第一时间知道」的机制 —— 靠**缓存一致性协议**广播失效，不是"刷主存"。

### 4.2 volatile 读流程

```java
while (!flag) { }   // volatile 读
int r = x;          // 普通读
```

**软件层**

    ① JMM 要求：volatile 读 = load + LoadLoad + LoadStore 屏障
       读后插 LoadLoad  → 阻止后续普通读跑到读前
       读后插 LoadStore → 阻止后续普通写跑到读前

**硬件层**

    ② 执行 load flag
    ③ 检查本核心 L1 缓存里 flag 行的状态：
       - S/E 态 → 直接读（有最新值）
       - I 态（Invalid）→ cache miss！
         总线嗅探/目录 → 从持有最新值的核心（cache-to-cache）或主存拿数据
    ④ 拿到后本核缓存行变 S，读返回最新值

**关键**：写方已 invalidate 你的缓存行，所以你读时**必然 miss、必然重取** —— 不可能读到旧值。这就是「第一时间发现」的答案。

### 4.3 完整时间线（A 写 / B 读）

```
线程 A                          线程 B
① 写 x=1（普通写）              
② 写 flag（volatile）
   → RFO + invalidate 广播       
                               ③ flag 缓存行被置 Invalid（此刻 B 无感知）
                               ④ 读 flag → 自检发现 Invalid
                                  → miss → 从 A（M 态）cache-to-cache 拿 true
                               ⑤ 读 x → LoadLoad 屏障保证不早于④
                                  → 必然看到 1
```

第 ⑤ 步是「连坐」的硬件化：屏障锁死读取顺序 + 缓存一致性保证数据来源，合起来得到「flag 可见 ⇒ x 也可见」。

### 4.4 三个细节修正 ★

**① 广播发生在「写之前」，不是「写之后」**

    A 要写 flag → 先发 RFO + invalidate（获取独占权的准备动作）
               → 拿到独占权后，才真正执行写
    广播是写的「入场券」，B 的失效通知在 A 落笔前就到达了

**② 是「核心的缓存」，不是「线程的缓存」**

MESI 是**核心级**协议，Java 线程是 OS 线程、随时可能被调度到别的核心。准确说法：B miss 后从「持有该缓存行 M 态的那个核心」cache-to-cache 拿数据。

**③ 「等待」确实存在，但等的是硬件事务**

如果 B 的读请求撞上 A 正在写同一缓存行，B 的读会 stall —— 在总线/目录层面排队，等该缓存行事务完成再拿数据。这个等待由硬件仲裁，纳秒级，但确实存在。

---

## 5. 底层原理（补充知识）

### 5.1 MESI 缓存一致性协议

每个核心有私有 L1/L2，共享 L3 + 主存。缓存行四种状态：

    M Modified    本核心独占修改，主存是旧的
    E Exclusive   本核心独占，与主存一致
    S Shared      多核心共享，与主存一致
    I Invalid     已失效，读必须重新获取

**写流程状态转换**

    A 写 flag → 状态不是 M/E → 发 RFO + invalidate 广播
    B/C 的 flag 行 → I
    A 获得独占 → 写入 → M

**读流程状态转换**

    B 读 flag → 状态是 I → cache miss
    → 嗅探总线：谁有最新（M 态核心）→ cache-to-cache 获取
    → B 状态变 S → 读到最新值

**一句话**：写方靠 MESI 广播失效，读方靠缓存行自检 miss，中间靠屏障锁死顺序 —— 三者配合才是「第一时间发现」的真相。

### 5.2 四种内存屏障

    屏障           语义                                  代价
    LoadLoad      Load1; LL; Load2 → Load2 前 Load1 读完   低
    StoreStore    Store1; SS; Store2 → Store2 前 Store1 对其他核可见  低
    LoadStore     Load1; LS; Store2 → Store2 刷出前 Load1 读完  中
    StoreLoad     Store1; SL; Load2 → Load2 前 Store1 对所有处理器可见  最高（万能屏障）

- **StoreLoad 是最贵的**：兼具其他三种功能，x86 上实现为 mfence / lock 前缀
- 这就是 volatile **写**比普通写贵 10~100 倍、**读**在 x86 上几乎免费的原因
- **final 字段也有屏障语义**（JSR-133）：`x.finalField = v; StoreStore; sharedRef = x;` —— 保证 final 字段在对象发布前完成初始化（final 的「构造安全」保证）

### 5.3 x86 vs ARM 内存模型

    x86 / x64    TSO（强内存模型）
                load 天然较强；只需在写后插 StoreLoad
                volatile 读 ≈ 普通 load（免费）
    ARM / POWER  弱内存模型
                读写都要屏障，编译器/JIT 插入更多屏障
    Java 层面    无需关心 —— JVM 已按 JMM 规范插好屏障，
                同一份 Java 代码跨平台语义一致

### 5.4 性能代价与假共享

**① volatile 写贵**：StoreLoad 屏障（mfence）开销大；高频写 volatile 会显著变慢（用 AtomicLong 的 lazySet / Unsafe.putOrderedLong 可绕过）。

**② 假共享（False Sharing）**：多个核心高频写**同一缓存行**（哪怕不同字段），每次写都要 RFO + invalidate 对方 → 缓存行在两核间 ping-pong → 总线拥塞、吞吐暴跌。

```java
// 反例：a 和 b 不同线程各写，但可能落在同一 64 字节缓存行
class Counter {
    volatile long a;   // 线程 1 写
    volatile long b;   // 线程 2 写 —— 互相拖垮！
}
```

**③ 解法**：`@Contended` 注解（Java 8+，需 -XX:-RestrictContended）或手动 padding 把字段拆到不同缓存行。

---

## 6. 面试追问清单（带答案）

### 6.1 volatile 的三个特性？

A：可见性（写对后续读可见）、有序性（禁止重排序，双向屏障）、**不保证原子性**。它是轻量级同步：比 synchronized 轻（无锁），比 Atomic 弱（不解决复合原子性）。

### 6.2 volatile 能保证原子性吗？i++ 问题？

A：不能。volatile 只保证单次读写的可见性，i++ 是读-改-写三步，可能丢更新。计数器用 AtomicInteger / LongAdder。

### 6.3 DCL 单例为什么必须 volatile？

A：new Singleton() 三步（分配→构造→引用赋值）可能重排序，不加 volatile 时其他线程可能读到「非 null 但未构造完」的对象。volatile 保证引用赋值（volatile 写）之前的构造动作对读线程可见（happens-before 传递）。

### 6.4 volatile 和 synchronized 的区别？

A：① volatile 无锁、无阻塞、不能做互斥；synchronized 可做临界区。② volatile 只能修饰变量；synchronized 修饰方法/代码块。③ volatile 保证可见性+有序性；synchronized 额外保证原子性（互斥）。④ volatile 写比 synchronized 快，但解决不了复合操作。

### 6.5 volatile 和 Atomic 的区别？

A：volatile 只解决可见性/有序性；Atomic 用 CAS 解决原子性（并含 volatile 的可见性）。原子性要求用 Atomic，纯开关用 volatile 更轻。

### 6.6 volatile 写为什么比普通写慢？

A：写后要插 StoreLoad 屏障（x86 上 mfence/lock 前缀），它是四种屏障中最贵的万能屏障，还要冲刷 store buffer + 广播 invalidate。volatile 读在 x86 上几乎免费（普通 load）。

### 6.7 假共享是什么？怎么解决？

A：多个核心高频写同一缓存行（哪怕不同字段）→ 每次写都 RFO + invalidate 对方 → 缓存行 ping-pong、总线拥塞、性能暴跌。解决：@Contended 注解或字段 padding 拆行。

### 6.8 happens-before 传递性怎么理解？

A：A 写普通变量 → A 写 volatile（发布）→ B 读 volatile → B 读普通变量，链式传递得到「普通写 happens-before 普通读」。volatile 写之前的普通写会随 volatile 写一起对读线程可见 —— 这是 DCL 和「安全发布」的理论基础。

### 6.9 volatile long/double 有什么特殊？

A：JMM 规定 volatile 的 long/double 读写是原子的。普通 long/double 在 32 位 JVM 上可能非原子（高 32 位/低 32 位分两次写，可能读到撕裂值）。共享的 long/double 建议 volatile 修饰。

### 6.10 「volatile 会立即刷回主内存」对吗？

A：是教学比喻，不精确。JMM 没有「立即刷回主内存」的字面保证；真实语义是 happens-before + 内存屏障 + 缓存一致性协议（MESI）。volatile 保证顺序语义（写已提交则读必然看见），不是时间语义（不是实时广播）。

---
*来源：Hermes 会话整理（2026-08-06，含 JMM/硬件层完整链路、MESI、四种屏障、假共享，网络资料补充 long/double 与 final 屏障语义）*
