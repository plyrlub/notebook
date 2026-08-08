---
tags: [Java, JVM, GC, 垃圾回收, 机制]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/JVM）
归属: 01-学习/Java/JVM
aliases: [Java GC 详解]
---

# Java GC 详解（判活 / 算法 / 收集器演进）

## 📋 总纲

1. 判活算法：引用计数 vs 可达性分析 + 四种引用
2. 回收算法：标记-清除 / 复制 / 标记-整理 / 分代收集
3. 收集器演进（按 JDK 版本）：Serial → Parallel → CMS → G1 → ZGC / Shenandoah
4. 关键机制：三色标记、写屏障、SATB、卡表 / 记忆集
5. 基础代码示例：对象分配晋升、System.gc() 观察、GC 日志解读
6. 对比总表 + 面试追问 Q&A

---

## 1. 判活算法

### 1.1 引用计数（Reference Counting）

- 原理：对象被引用一次计数 +1，引用失效 -1，计数为 0 即可回收
- 缺点：**循环引用无法回收**（A 引用 B、B 引用 A，彼此计数永不为 0）
- 结论：主流 JVM **不用**引用计数，Java 里它只是概念存在

### 1.2 可达性分析（Reachability Analysis）

- 原理：从 **GC Roots** 出发向下搜索，能到达的对象视为"活"，不可达即"死"
- GC Roots 包括：
  a. 虚拟机栈（栈帧本地变量表）中引用的对象
  b. 方法区中静态属性/常量引用的对象
  c. JNI（Native）方法引用的对象
  d. 活跃线程、Class 对象、**同步锁（synchronized）持有的对象**——锁住的对象不会被 GC 回收
- 代码验证循环引用能被回收：

```java
public class ReachabilityDemo {
    static class Node { Node next; }

    public static void main(String[] args) {
        Node a = new Node();
        Node b = new Node();
        a.next = b;
        b.next = a;          // 循环引用
        a = null;
        b = null;
        // 这里两个对象互相引用但都不再可达 → 可被 GC 回收
        System.gc();
        System.out.println("循环引用对象已被回收");
    }
}
```

### 1.3 四种引用（附小代码）

| 引用 | 回收时机 | 用途 |
|---|---|---|
| 强引用（Strong） | 永不回收（除非不可达） | 普通 new 的对象 |
| 软引用（SoftReference） | 内存不足时回收 | 缓存（图片/大对象） |
| 弱引用（WeakReference） | 下次 GC 就回收 | ThreadLocal、WeakHashMap |
| 虚引用（PhantomReference） | 对象回收后通知（配合 ReferenceQueue） | 堆外内存回收、对象生命周期追踪 |

```java
import java.lang.ref.*;

public class ReferenceDemo {
    public static void main(String[] args) throws Exception {
        // 软引用：内存紧张才回收
        SoftReference<byte[]> soft = new SoftReference<>(new byte[10 * 1024 * 1024]);
        System.out.println("软引用: " + soft.get());

        // 弱引用：一次 GC 就没了
        WeakReference<String> weak = new WeakReference<>(new String("weak"));
        System.gc();
        System.out.println("弱引用 GC 后: " + weak.get());   // null

        // 虚引用：get() 永远返回 null，回收后进队列
        ReferenceQueue<Object> queue = new ReferenceQueue<>();
        PhantomReference<Object> phantom = new PhantomReference<>(new Object(), queue);
        System.gc();
        Thread.sleep(100);
        System.out.println("虚引用已入队: " + (queue.poll() != null));
    }
}
```

---

## 2. 回收算法

### 2.1 标记-清除（Mark-Sweep）

- 两步：标记所有存活对象 → 清除未被标记的
- 缺点：① **内存碎片化**（不连续空洞）；② 标记+清除两次扫描，效率随对象数下降
- 用于：老年代（CMS 的基础）

### 2.2 复制（Copying）

- 把内存分成两块，只用一块；GC 时把存活对象复制到另一块，整块清空
- 优点：无碎片、简单高效；缺点：**空间浪费一半**（可用内存减半）
- 实际应用：新生代用"Eden + 两个 Survivor"比例 8:1:1 优化，只浪费 10%

### 2.3 标记-整理（Mark-Compact）

- 标记存活对象后，把它们**向一端移动**，清理边界外的空间
- 优点：无碎片；缺点：移动对象要更新引用，STW 时间长
- 用于：老年代（Parallel 默认）、G1 的混合回收阶段

### 2.4 分代收集（Generational）

- 依据**弱分代假设**：绝大多数对象朝生夕灭（新生代），少数存活很久（老年代）
- 新生代：复制算法（Eden + Survivor），对象熬过 N 次 Minor GC 晋升老年代
- 老年代：标记-清除/标记-整理（对象大、存活率高，复制不划算）
- 三种 GC 类型：
  a. Minor GC（新生代）：频繁、快
  b. Major GC（老年代）：较慢（常与 Full GC 混称）
  c. Full GC（整堆 + 方法区/元空间）：最慢、STW 最长

```java
// 观察对象晋升：-verbose:gc 或 -Xlog:gc 跑下面的代码
public class PromotionDemo {
    public static void main(String[] args) {
        for (int i = 0; i < 100; i++) {
            byte[] b = new byte[1024 * 1024];   // 每次 1MB，触发多次 Minor GC
        }
    }
}
```

**对象进入老年代的四种情况**：

| 情况 | 说明 |
|---|---|
| 年龄达阈值 | 每熬过一次 Minor GC 年龄 +1，默认到 15（`-XX:MaxTenuringThreshold`）晋升 |
| 大对象 | 超过 `-XX:PretenureSizeThreshold` 直接进老年代，避免在 Survivor 间反复复制 |
| 动态年龄 | Survivor 中同龄对象总大小超过一半，取其年龄以上者直接晋升 |
| 分配担保 | Minor GC 后 Survivor 放不下的对象直接进老年代 |

**Minor GC 触发条件**：Eden 区满即触发（Survivor 满不触发 Minor GC，放不下走分配担保）。

---

## 3. 收集器演进（按 JDK 版本）

### 3.1 Serial（串行，JDK 1.3）

- 单线程回收，GC 时必须 STW（Stop The World）
- 适用：单核、客户端（Client 模式默认）、内存极小场景
- 新生代复制 / 老年代标记-整理；`-XX:+UseSerialGC`

### 3.2 Parallel Scavenge（并行，JDK 1.4 / JDK 8 默认）

- 多线程并行回收，**吞吐量优先**（`-XX:MaxGCPauseMillis` / `-XX:GCTimeRatio` 可调目标）
- 与 Serial 一样有 STW，只是多个 GC 线程同时干活
- JDK 8 默认收集器：新生代 Parallel Scavenge + 老年代 Parallel Old（`-XX:+UseParallelGC`）
- 适用：后台计算、批处理等不介意停顿、追求吞吐的场景

### 3.3 CMS（并发标记清除，JDK 1.5 / JDK 9 废弃 / JDK 14 移除）

- 目标：**低延迟**，与用户线程并发执行大部分阶段
- 四阶段：初始标记（STW 短）→ 并发标记 → 重新标记（STW 短）→ 并发清除
- 缺点：
  a. 并发阶段占用 CPU，吞吐下降
  b. **浮动垃圾**（并发时新产生的垃圾本次收不掉，留到下次）
  c. **内存碎片**（标记-清除无整理），碎片过多时退化为 Serial Old 做 Full GC
- 经典坑：CMS 无法处理"并发失败（Concurrent Mode Failure）"→ 提前触发 Full GC

### 3.4 G1（Garbage First，JDK 7 实验 / JDK 9 默认）

- 把堆划分为**多个大小相等的 Region**（1-32MB，`-XX:G1HeapRegionSize`），逻辑上分代（Region 扮演 Eden/Survivor/Old/Humongous）
- **可预测停顿**：`-XX:MaxGCPauseMillis`（默认 200ms），优先回收"垃圾最多"的 Region（Garbage First 得名）
- 混合回收（Mixed GC）：新生代 + 部分老年代 Region 一起收
- 用 **RSet（记忆集）** 记录跨 Region 引用，避免全堆扫描
- 用 **SATB（Snapshot-At-The-Beginning）** 写屏障处理并发标记（见 4.3）
- 大对象（> Region 一半）直接进 Humongous Region
- JDK 9 起默认，JDK 11/17 仍是默认，适合大多数服务端场景

**Mixed GC 与 Full GC 的触发条件（面试高频）**：
- **Mixed GC**：并发标记（Initial Mark → Concurrent Mark → Remark → Cleanup）完成后，优先回收垃圾最多的老年代 Region（Garbage First），新生代 + 部分老年代一起收
- **G1 退化为 Serial Full GC 的时机**：
  a. 晋升失败（to-space exhausted，Eden/Survivor 没空间放不下晋升对象）
  b. 并发标记完成前老年代被填满
  c. Humongous 大对象分配失败
  → 此时 G1 会退化为**单线程 Serial Full GC**（STW 最长），这是 G1 最需要避免的场景
- **大对象与 G1HeapRegionSize**：大对象分配在连续多个 Region 组成的 Humongous 区，不参与复制/整理（移动成本高）；`-XX:G1HeapRegionSize`（1~32MB，默认堆的 1/2048）设太小 → 大对象频繁触发 Humongous 分配失败 → Full GC；设太大 → Region 数量少、回收粒度粗

### 3.5 ZGC（JDK 11 实验 / JDK 15 转正）

- 目标：**亚毫秒级停顿**，且停顿时间不随堆大小增长（支持 TB 级堆）
- 核心技术：
  a. **染色指针（Colored Pointer）**：64 位指针中**低 42 位存对象地址**（最大 4TB 堆），**高位嵌入 4 个状态位**（Finalizable / Remap / Mark0 / Mark1）——标记信息不占对象空间，也不需额外内存
  b. **读屏障（Load Barrier）**：读引用时检查并修正状态，把标记/重定位工作摊到业务线程
  c. 大部分阶段与业务线程并发，STW 极短
- JDK 16 起**并发栈扫描**（此前栈扫描仍需 STW），停顿降至 <1ms 级，且不随堆增大而增长
- 适用：超大堆（几十 GB ~ TB）、对停顿极度敏感（金融/实时推荐）
- 配置：`-XX:+UseZGC -Xmx<大小>`（ZGC 需要预知堆大小，不支持动态调整）

### 3.6 Shenandoah（JDK 12 实验 / JDK 15 转正）

- 与 ZGC 同属低延迟收集器，但思路不同：**连接矩阵（Connection Matrix）** 记录跨 Region 引用（对比 G1 的 RSet），用**读屏障 + 转发指针（Brooks Pointer）** 实现并发移动对象
- Oracle JDK **不含** Shenandoah（Red Hat 主导，Oracle 商业版不集成）
- 适用：同 ZGC——大堆低延迟场景，OpenJDK 系可用

### 3.7 各版本默认收集器速查

| JDK | 变化 / 默认收集器 |
|---|---|
| 8 | 默认 Parallel Scavenge + Parallel Old；**永久代（PermGen）→ 元空间（Metaspace）** |
| 9 | 默认改为 **G1**；CMS 标记废弃 |
| 11 | 引入 ZGC（实验）、**Epsilon（无操作 GC，只测内存分配不回收）** |
| 14 | 移除 CMS |
| 15 | ZGC、Shenandoah 转正为生产可用 |
| 16 | ZGC 并发栈扫描，停顿降至 <1ms |
| 17+ | 默认仍 G1；大堆低延迟可选 ZGC / Shenandoah（需显式开启） |

---

## 4. 关键机制

### 4.1 三色标记（Tri-color Marking）

并发标记时把对象分三色：
- **白色**：未被访问（可能被回收）
- **灰色**：自身被访问，引用的对象还没全查完
- **黑色**：自身及引用都查完了

**漏标问题**：并发标记时若黑色对象新引用了白色对象（且灰色对象到白色对象的路径被切断），白色对象会被误回收 → 必须用写屏障补救。

### 4.2 写屏障（Write Barrier）

- 在引用**写入**时插入的拦截逻辑（不是内存屏障！）
- 两种补救策略：
  a. **增量更新（Incremental Update）**：把"新引用"记下来，重新标记时再扫——**CMS 用这个**
  b. **SATB（Snapshot-At-The-Beginning）**：把"被切断的旧引用"记下来，按快照标记——**G1 用这个**
- 类比：增量更新盯着"新连接"，SATB 盯着"断开的旧连接"

**SATB 写屏障伪代码（G1）**：

```java
// 写屏障：在引用写入前/后执行（JVM 内部机制，开发者不直接写）
// 漏标场景：灰对象 G 删除指向白对象 W 的引用，同时黑对象 B 新增指向 W
// 解决：SATB 记录"被覆盖的旧引用"（快照），本周期把 W 视为存活
// void writeBarrier(Object src, Field f, Object oldVal, Object newVal) {
//     if (isMarkingActive && oldVal 是白色) {
//         markGray(oldVal);          // 快照：本周期不回收它
//         SATB_QUEUE.add(oldVal);    // 重新标记阶段再处理
//     }
//     f = newVal;                    // 真正写入
// }
// 代价：可能多保留一些本已死亡的对象 → 浮动垃圾（G1 并发标记后常见）
```

### 4.3 卡表 / 记忆集（Card Table / RSet）

- 问题：新生代 Minor GC 要扫描老年代，找谁引用了新生代对象——全扫老年代太慢
- 解决：**卡表（Card Table）**，把老年代分成 512 字节的卡，对象引用被写时（写屏障）把卡标记为 dirty；Minor GC 只扫 dirty 卡
- G1 的 **RSet（Remembered Set）** 是卡表的加强版：按 Region 记录"谁引用了本 Region 内的对象"，粒度更细

### 4.4 Stop-The-World（STW）

- GC 某些阶段必须暂停所有业务线程（保证对象图稳定）
- 各收集器 STW 差异：Serial/Parallel 全程 STW；CMS/G1 只部分阶段；ZGC/Shenandoah 极短

### 4.5 SafePoint（安全点）

- GC 不能在任意时刻开始：线程必须运行到**安全点**（SafePoint）才能暂停——安全点一般设置在**方法调用、循环回边、异常跳转**等位置
- 原因：安全点上线程的栈和寄存器状态稳定，GC 才能准确扫描对象引用
- 相关概念：
  a. **安全区（Safe Region）**：线程 sleep / 阻塞时不在执行，视为一直在安全区，无需等待
  b. 长时间不进入安全点（如巨大循环体、`JNI` 调用）会**推迟 GC**，表现为"GC 等待线程"停顿——`jstack` 里能看到 `vm operation` / GC 线程等某个业务线程
  c. `-XX:+PrintSafepointStatistics` 可观察安全点停顿统计

---

## 5. 基础代码示例

### 5.1 观察 Minor GC / Full GC（JDK 9+ 日志语法）

```bash
# JDK 8：-XX:+PrintGCDetails -XX:+PrintGCDateStamps
# JDK 9+：
java -Xlog:gc*:file=gc.log:time,uptime,level GC 示例类

# 实时看
java -Xlog:gc -Xmx64m -Xms64m PromotionDemo
```

典型输出解读：

```
[0.042s][info][gc,start] GC(0) Pause Young (Normal) (G1 Evacuation Pause)
[0.043s][info][gc,heap]   Eden regions: 32->0(32)   // 新生代清空
[0.043s][info][gc,heap]   Survivor regions: 0->4     // 存活晋升/到 Survivor
[0.043s][info][gc] GC(0) Pause Young ... 2.031ms    // 停顿 2ms
```

### 5.2 触发 Full GC 的常见来源（排查定位用）

a. `System.gc()` / `Runtime.getRuntime().gc()`（RMI 每小时一次、NIO 堆外分配、第三方库）
b. 老年代空间不足（对象晋升失败）
c. 元空间（Metaspace）不足
d. CMS 并发模式失败（Concurrent Mode Failure）
e. `jmap -histo:live` 等工具主动触发
f. `-XX:+DisableExplicitGC` 可屏蔽 a 类（但注意堆外内存回收依赖，见调优篇）

---

## 6. 对比总表 + 面试追问

### 6.1 收集器对比总表

| 收集器 | 线程 | 算法 | 目标 | 适用 | 默认 |
|---|---|---|---|---|---|
| Serial | 单 | 复制+标记整理 | 简单 | 单核/客户端 | JDK 8 Client |
| Parallel | 多 | 复制+标记整理 | 吞吐优先 | 批处理/后台 | JDK 8 默认 |
| CMS | 并发 | 标记-清除 | 低延迟 | 老年代/Web（已废弃） | 无 |
| G1 | 并发+并行 | Region 分代 | 可预测停顿 | 服务端通用 | JDK 9+ 默认 |
| ZGC | 并发 | 染色指针 | 亚毫秒停顿 | 超大堆低延迟 | 可选 |
| Shenandoah | 并发 | 连接矩阵+转发指针 | 亚毫秒停顿 | 超大堆低延迟（OpenJDK） | 可选 |

### 6.2 面试追问 Q&A

### 6.2.1 怎么判断对象已死？

答：主流用可达性分析——从 GC Roots（栈帧局部变量、静态引用、JNI 引用、活跃线程等）出发搜索，不可达即死。引用计数有循环引用缺陷，JVM 不用。

### 6.2.2 CMS 和 G1 的区别？

答：CMS 用标记-清除，针对老年代，有碎片和浮动垃圾问题，并发失败会退化为 Full GC；G1 把堆分成 Region 统一管理新生代和老年代，用 RSet 记录跨 Region 引用、SATB 处理并发标记，可预测停顿且默认 JDK 9+。CMS 已在 JDK 14 移除。

### 6.2.3 ZGC 为什么能亚毫秒停顿？

答：染色指针把 GC 状态信息编码进引用本身，读屏障把标记工作摊到业务线程并发执行，配合多阶段并发，STW 只剩极短的初始/最终标记。停顿不随堆大小增长，支持 TB 级堆。

### 6.2.4 什么是三色标记和漏标？怎么解决？

答：并发标记把对象分白（未访问）、灰（访问中）、黑（完成）；漏标是并发中黑色对象新引用了白色对象且旧路径被切断。解决靠写屏障：CMS 用增量更新（记新引用），G1 用 SATB（记被切断的旧引用快照）。

### 6.2.5 卡表/记忆集是干嘛的？

答：避免 Minor GC 时全扫老年代找跨代引用。卡表把老年代按 512B 分卡，写屏障标记 dirty 卡，只扫 dirty 卡；G1 的 RSet 按 Region 记录引用关系，粒度更细、回收更精准。

### 6.2.6 新生代为什么用复制算法？

答：新生代对象 98% 朝生夕灭，复制存活对象成本低；用 Eden+两个 Survivor（8:1:1）只浪费 10% 空间，且无碎片。老年代存活率高，复制不划算，用标记-清除/整理。

### 6.2.7 System.gc() 一定能触发 GC 吗？

答：只是请求，不保证；但默认 JVM 会响应为 Full GC。生产可用 `-XX:+DisableExplicitGC` 屏蔽，或 `-XX:+ExplicitGCInvokesConcurrent` 让它走并发回收（避免 STW），但禁用前要确认没有依赖 System.gc() 回收堆外内存（DirectByteBuffer）。

### 6.2.8 什么情况会触发 Full GC？

答：老年代空间不足/晋升失败、元空间不足、System.gc() 显式调用、CMS 并发模式失败、工具（jmap -histo:live）触发。排查先看 GC 日志定位是哪种。

### 6.2.9 电商交易系统，堆 16G、P99 延迟要求 200ms，怎么选 GC 并调参？

答：选 G1（JDK9+ 默认，兼顾吞吐与可控停顿）：`-XX:MaxGCPauseMillis=200`（软目标）、`-Xms=-Xmx=16G` 避免扩容抖动；配合 GC 日志监控停顿，若出现频繁 Full GC 用 heap dump 排查内存泄漏/大对象，必要时调 `-XX:G1HeapRegionSize` 与晋升阈值。8G 以下小堆且吞吐优先可考虑 Parallel；128G 超大堆且 P99 更严苛再上 ZGC。核心是**先测量后调优**，别一上来堆参数。

### 6.2.10 大对象在 G1 中如何分配？为什么 G1 倾向于避免大对象？

答：超过 Region 一半大小的对象直接进入 Humongous 区（连续多个 Region），不参与复制/整理。G1 避免大对象是因为：大对象移动成本高、会触发 Humongous 分配失败（→ 退化 Full GC）、且易产生碎片。调优上控制 `-XX:G1HeapRegionSize`（1~32MB）平衡：设小则大对象更易触发 Humongous 失败，设大则 Region 粒度粗。

### 6.2.11 JDK 8 → JDK 11 迁移，默认收集器从 Parallel 变 G1，原来的 `-XX:+UseParallelOldGC` 参数怎么办？

答：升级后显式指定 `-XX:+UseParallelGC` 可保持原行为（ParallelOld 在 JDK 9 后已合并/废弃，只需 UseParallelGC），但更建议做回归压测后切到 G1 享受可控停顿；迁移期对比 GC 日志（停顿/吞吐/内存），用数据决定留哪个。

### 6.3 常见误区清单

- **认为引用计数就是 Java 的回收方式**——Java 用可达性分析（引用计数无法解决循环引用）
- **认为 `System.gc()` 会立即回收**——只是"建议"，且默认触发 Full GC（STW），生产应禁用
- **认为对象没有引用就立刻被回收**——要等下次 GC 真正执行才回收
- **把 Major GC 和 Full GC 混为一谈**——Major 指老年代回收，Full 指整堆 + 元空间
- **认为 G1 一定比 CMS/Parallel 快**——要看堆大小与延迟/吞吐目标（小堆/吞吐场景 Parallel 更优）
- **用软/弱引用缓存后忘记 null 检查**——`get()` 可能返回 null（已回收）
- **以为 G1 没有分代**——G1 逻辑上仍有分代，只是物理上 Region 不连续
- **以为 ZGC 只能配超大堆**——ZGC 也适合中等堆但延迟要求极苛刻的场景，只是内存占用略高

---

## 参考

- 《深入理解 Java 虚拟机（第 3 版）》周志明
- Oracle 官方：JDK 9/11/17 垃圾收集器文档（G1 / ZGC / Shenandoah）
- OpenJDK JEP 333（ZGC）、JEP 189（Shenandoah）、JEP 248（G1）
- 关联笔记：**JVM 调优实战**（见知识库）（参数与场景排查）、[java-reflection](java-reflection.md)（JVM 运行机制相关）
