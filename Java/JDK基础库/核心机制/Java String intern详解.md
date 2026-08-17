---
tags: [Java, String, intern, StringTable, JVM, 面试]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/JDK基础库/核心机制）
归属: 01-学习/Java/JDK基础库/核心机制
---

# Java String intern详解

## 📋 总纲

1. 基本概念：intern 是什么、与字面量的关系、== 比较
2. 常量池位置演进：JDK6 PermGen → JDK7 堆 → JDK8+ Metaspace
3. StringTable 实现原理：哈希表、查找流程、扩容、GC 回收
4. 大量 intern 反而 OOM 的根因
5. 使用场景与性能调优
6. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 intern 是什么

`String.intern()` 是 **native 方法**，语义：

    若常量池中已有「内容相同」的字符串 → 返回池中引用
    否则 → 把当前字符串加入常量池，返回池中引用

```java
String s1 = "abc";               // 字面量：编译期入池
String s2 = new String("abc");   // 堆上新对象
s1 == s2                         // false（引用不同）
s2.intern() == s1                // true（intern 返回池中引用）
```

**目的**：复用相同内容的字符串，省内存 + 支持 `==` 快速比较。

### 1.2 字面量与 intern 的关系

- 代码里的**字面量**（`"abc"`）在类加载时自动入池，等价于隐式 intern
- `new String("abc")`：会创建**两个对象** —— 字面量"abc"（池中）+ new 出来的堆对象
- `new String("abc").intern()`：返回池中那个，堆上 new 的对象变成垃圾

### 1.3 intern 后 == 比较

```java
// 经典优化模式：intern 后可以用 == 代替 equals
if (a.intern() == b.intern()) { ... }   // 性能优化，但见 5.2 的坑
```

**注意**：`==` 比较的是引用，只有两侧都是池中对象才成立 —— 一侧没 intern 就翻车。

---

## 2. 常量池位置演进（OOM 问题的根源）

| JDK 版本 | 字符串常量池位置 | 特点 | 典型 OOM |
|---------|----------------|------|---------|
| JDK 6 及以前 | **PermGen**（永久代） | 空间固定、很小、基本不回收 | PermGen space |
| JDK 7 | **Java 堆** | 池中字符串是普通堆对象，GC 可回收 | Java heap space |
| JDK 8+ | **Java 堆**（PermGen 被 Metaspace 取代） | 池仍在堆，Metaspace 管类元数据 | Java heap space |

**关键变化**（JDK 7 是分水岭）：

    ① JDK6：intern 的字符串「拷贝」进 PermGen，永久存活，空间还小
              → 大量 intern 直接 PermGen OOM（当年著名的内存炸弹）
    ② JDK7+：intern 的是堆对象引用，且无外部引用时可被 GC 回收
              → 池不再是「无底洞」，但仍有 OOM 风险（见第 4 章）

---

## 3. StringTable 实现原理

### 3.1 数据结构：哈希表

- 字符串常量池的底层是 **StringTable**：一个固定大小的 **Hashtable**（哈希桶数组 + 链表）
- 默认桶数：JDK 6 为 **1009**，JDK 7+ 为 **60013**（`-XX:StringTableSize` 可调）
- 元素：哈希桶里的条目持有 String 引用

### 3.2 intern 流程（HotSpot 的 StringTable::intern）

    ① 计算字符串 hashCode
    ② 定位哈希桶
    ③ 遍历桶内链表，逐个 equals 比较
    ④ 命中 → 返回池中引用（新对象变垃圾）
    ⑤ 未命中 → 插入桶中，返回池中引用

- 平均 O(1)；**桶数太小 + 大量字符串 → 链表变长 → 退化为 O(n)**（调 StringTableSize 的原因）

### 3.3 GC 与回收（重要澄清 ★）

    JDK7+ 池在堆中，但 StringTable 持有强引用 —— 那还能回收吗？

    能。GC 时有 StringTable unlink 机制：
    如果池中的字符串「只有 StringTable 引用、无外部引用」，
    GC 会把它从表中移除 → 可回收

    结论：JDK7+ 中「intern 后没人持有」的字符串不会被永久钉在池里；
          但「intern 后业务代码还持有引用」的字符串 → 永不可回收。

### 3.4 与运行时常量池的关系

    类文件常量池 → 类加载后进入「运行时常量池」（方法区/Metaspace）
    字符串字面量/intern 的字符串 → StringTable（JDK7+ 在堆）
    两者不同：StringTable 存字符串实例，运行时常量池存符号引用等

---

## 4. 大量 intern 反而 OOM 的根因

### 4.1 JDK6 时代：PermGen 爆炸

    intern 字符串进 PermGen：空间固定且极小（默认几十 MB）
    → 大量 intern 必然 java.lang.OutOfMemoryError: PermGen space
    这是 intern 被称为「内存炸弹」的历史原因

### 4.2 JDK7+ 时代：堆被吃光

**原因①：动态唯一字符串 = 池化无复用价值**

```java
// 反例：intern 动态生成的唯一字符串
for (每条记录) {
    String key = id + "_" + timestamp;   // 每条都独一无二
    key.intern();                        // 池里全是唯一条目，永远复用不上
}
```

    intern 的本质是「内容重复才省钱」：
    内容有限重复 → 池化是复利（省内存）
    内容全唯一   → 池化是纯负债（只进不出的内存占用）

**原因②：外部持有引用 → 永不可回收**

    intern 后存进 Map/List/缓存 → 字符串永远可达
    → GC 的 unlink 机制失效 → 越积越多 → 堆爆

### 4.3 本质总结

    大量 intern OOM = 池化语义被用错场景：
    ① 池强引用（或外部持有）→ 只增不减
    ② 唯一字符串 → 存了还复用不上，纯占空间
    ③ JDK6 额外叠加 PermGen 空间瓶颈

**经典案例**：某系统用 intern 做 `==` 比较优化，对业务动态字符串 intern，上线后堆 OOM —— 内存从"减少"变成"加速耗尽"。

---

## 5. 使用场景与性能调优

### 5.1 适合用 intern 的场景

    ① 有限集合的常量（枚举名、状态码、固定字典）
    ② 明确知道内容会大量重复的字符串
    ③ 需要 == 快速比较且生命周期受控

### 5.2 不适合的场景

    ① 动态拼接字符串（时间戳、ID、随机数）
    ② 无限增长的唯一业务字段
    ③ 大字符串（intern 省不了多少，反而哈希/比较开销大）

### 5.3 JVM 调优参数

    -XX:StringTableSize=100000   // 调大桶数，减少哈希冲突（默认 60013）
    适用：确定会有大量 intern 且内容重复的场景
    注意：调大 = 内存换性能；无脑调大反而多占内存

### 5.4 替代方案

    业务去重 → HashMap/ConcurrentHashMap（生命周期可控、可清理）
    对象复用 → Flyweight 模式（享元）
    == 优化   → 一般场景 equals 足够，别为微优化引入 intern

### 5.5 JDK9+ Compact Strings

    JDK9 起 String 内部从 char[] 改为 byte[]（Latin-1 单字节存储）
    → 纯 ASCII 字符串内存减半，intern 的字符串也受益
    → 但 intern 的核心语义和 OOM 风险不变

---

## 6. 面试追问清单（带答案）

### 6.1 String.intern() 的原理？

A：native 方法，操作 StringTable（哈希表）。流程：算 hash → 定位桶 → 链表 equals → 命中返回池中引用，未命中插入并返回。JDK7+ 池在堆中，JDK6 在 PermGen。

### 6.2 为什么大量 intern 反而 OOM？

A：① JDK6 池在 PermGen，空间固定且小 → PermGen OOM；② JDK7+ 池在堆，若 intern 动态唯一字符串（无复用价值，只进不出）或被外部持有引用（GC unlink 失效）→ 堆 OOM。本质：池化只对内容重复的字符串省内存，唯一字符串池化是纯负债。

### 6.3 intern 的字符串能被 GC 回收吗？

A：JDK7+ 可以 —— 若字符串只有 StringTable 引用、无外部引用，GC 的 unlink 机制会把它从表中移除。JDK6 基本不行（PermGen 不回收）。有外部引用则永不可回收。

### 6.4 用 == 比较 intern 后的字符串安全吗？

A：只有两侧都保证是池中对象才安全（都经过 intern 或都是字面量）。一侧是 new 出来的对象就翻车。实践中优先 equals，== 比较是优化手段不是默认。

### 6.5 new String("abc") 创建几个对象？intern 之后呢？

A：字面量"abc"进池（1 个）+ new 出堆对象（1 个）= 2 个。intern 后返回池中那个，堆对象变垃圾（若无人持有）。若池中已有"abc"，new String("abc") 只新增 1 个堆对象。

### 6.6 StringTable 怎么调优？

A：-XX:StringTableSize 调大桶数减少哈希冲突（JDK7+ 默认 60013）。适用大量 intern 且内容重复的场景；调大是内存换性能，别无脑调。

### 6.7 什么场景适合 intern？

A：内容有限且高度重复的字符串（枚举名、状态码、固定字典）、受控生命周期的 == 比较优化。动态唯一字符串、无限增长字段、大字符串都不适合。

### 6.8 JDK9+ Compact Strings 对 intern 有影响吗？

A：JDK9 起 String 内部改 byte[] 存储，ASCII 字符串内存减半，intern 同样受益；但 intern 的语义、StringTable 机制和 OOM 风险不变。

### 6.9 字符串常量池和运行时常量池的区别？

A：运行时常量池在方法区（Metaspace），存类加载后的常量/符号引用；字符串常量池（StringTable）JDK7+ 在堆，存 intern 的字符串实例。两者是不同结构，常被混淆。
> 参考：美团《深入解析 String#intern》、StringTable 源码分析
