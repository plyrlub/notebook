---
tags: [Java, Guava, 三方库, io, math, primitives, BaseEncoding, IntMath]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava io / math / primitives详解

> 实测环境：guava 33.6.0-jre + JDK 17.0.12（实测数据标注于各节）
> 系列导航：[00-Guava概览与模块化辨析](00-Guava概览与模块化辨析.md)
> 包域：com.google.common.io / math / primitives

## 📋 总纲

1. io：流抽象 ByteSource / CharSource
2. io：Files 与 MoreFiles、ByteStreams / CharStreams
3. io：BaseEncoding 编码（实测）
4. math：IntMath / LongMath（实测）
5. math：Stats 与 Quantiles
6. primitives：Ints / Longs 等工具（实测）
7. primitives：Unsigned 无符号类型
8. 易错点汇总

## 一、io：流抽象 ByteSource / CharSource

Guava io 的核心抽象：把"数据源"和"对数据的操作"分离，替代手工 try-with-resources 样板。

### 抽象体系

| 抽象 | 代表字节流 | 代表字符流 |
| --- | --- | --- |
| 只读源 | ByteSource（可 copyTo） | CharSource（可 copyTo / read） |
| 可写目标 | ByteSink | CharSink |

```java
// 文件 → 字符串（一行样板）
String content = Files.asCharSource(new File("a.txt"), Charsets.UTF_8).read();

// 字符串 → 文件
Files.asCharSink(new File("b.txt"), Charsets.UTF_8).write("hello");
```

| 常用方法 | 说明 |
| --- | --- |
| `read()` / `readLines()` | 全量读 / 逐行读 |
| `copyTo(sink)` / `copyTo(OutputStream)` | 复制到目标 |
| `size()` | 大小（尽量不加载全部） |
| `isEmpty()` | 判空 |
| `slice(offset, len)` / `concat(sources)` | 切片 / 拼接数据源 |

易错点：Charsets.UTF_8 是 Guava 常量，JDK 7+ 用 `StandardCharsets.UTF_8`（Java 标准，新代码优先 JDK 版）。


**JDK 替代对照（JDK 11 起 Files 已覆盖主要场景）**

| Guava | JDK 替代 |
| --- | --- |
| Files.asCharSource(f).read() | `Files.readString(Path)`（JDK 11） |
| Files.asCharSink(f).write(s) | `Files.writeString(Path, s)`（JDK 11） |
| Files.readLines | `Files.readAllLines` / `BufferedReader.lines()` |

```java
// JDK 11 等价写法：等价 asCharSource(file, UTF_8).read()
String content = java.nio.file.Files.readString(Path.of("a.txt"));
```

结论：文件读写 JDK 11+ 直接用 java.nio.file.Files；Charsets.UTF_8 换成 StandardCharsets。

## 二、io：Files / MoreFiles / ByteStreams / CharStreams

| 工具 | 常用方法 | 33.x 状态 |
| --- | --- | --- |
| Files | asCharSource / asByteSource / readLines / toByteArray / write | 大部分 **deprecated**（官方引导迁移 java.nio.file.Files） |
| MoreFiles | asByteSource(Path) / asCharSource(Path) / deleteRecursively | 推荐的新版（Path 版） |
| ByteStreams | toByteArray(InputStream) / copy(InputStream, OutputStream) | 保留 |
| CharStreams | toString(Readable) / copy(Readable, Appendable) | 保留 |

选型：新代码用 `MoreFiles`（Path API）+ java.nio.file.Files；Guava Files 仅存量维护。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| ByteStreams.toByteArray(in) | `InputStream.readAllBytes()`（JDK 9） |
| ByteStreams.copy(in, out) | `InputStream.transferTo(out)`（JDK 9） |
| CharStreams.toString(Readable) | `Reader.transferTo(StringWriter)`（JDK 10）或 Files.readString |
| Guava Files（大部分已废弃） | `java.nio.file.Files` + `MoreFiles`（Path 版） |

结论：流复制/读取 JDK 9+ 已内置，新代码不再需要 Guava 流工具。

## 三、io：BaseEncoding（实测）

纯 JDK 编码（Base64.getEncoder）之外的扩展：base32、hex、大小写控制、可自定义 alphabet。

| 方法 | 说明 |
| --- | --- |
| `base64()` | 标准 Base64（无 padding 用 `base64().omitPadding()`） |
| `base32()` | Base32（长度翻倍，URL 安全场景） |
| `base16()` / `hex()` | 十六进制 |
| `encode(byte[])` / `decode(String)` | 编解码 |
| `withSeparator(",", n)` | 每 n 个字符加分隔符（如 UUID 格式） |
| `lowerCase()` / `upperCase()` | 大小写 |

实测输出：

```
base64('hello'): aGVsbG8=
```

易错点：

- decode 遇非法字符默认抛 IllegalArgumentException（可 `withPadChar` / 自定义 alphabet 调整）。
- 与 JDK 对比：简单 Base64 用 JDK 即可；需要 hex/base32/自定义字母表/分隔符时用 Guava。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| base64() | `java.util.Base64`（JDK 8）：`Base64.getEncoder().encodeToString(bytes)` |
| base16() / hex() | `HexFormat.of().formatHex(bytes)`（**JDK 17**） |
| base32 / withSeparator / 自定义字母表 | 无 |

```java
// JDK 等价写法
String b64 = Base64.getEncoder().encodeToString("hello".getBytes());  // aGVsbG8=
String hex = HexFormat.of().formatHex("hello".getBytes());            // JDK 17
```

结论：常规 base64 / hex 用 JDK；base32 与自定义格式才需要 Guava。

## 四、math：IntMath / LongMath（实测）

| 方法 | 说明 |
| --- | --- |
| `checkedAdd / checkedSubtract / checkedMultiply / checkedPow` | 溢出抛 ArithmeticException（实测见下） |
| `saturatedAdd / saturatedMultiply` | 溢出饱和到最大/最小值 |
| `pow(b, k)` | 快速幂（非 checked，可能溢出） |
| `gcd(a, b)` | 最大公约数 |
| `mod(a, m)` | 正模（结果恒非负，与 % 不同！） |
| `isPowerOfTwo` / `log2` / `ceilingPowerOfTwo` | 位运算友好函数 |
| `divide(a, b, RoundingMode)` | 带舍入模式的除法（含负数向零/向下取整差异） |

实测输出（guava 33.6.0-jre）：

```
IntMath.checkedAdd: 300
checkedAdd overflow -> ArithmeticException
```

易错点：

- `mod` 与 Java `%` 对负数行为不同：`-7 % 3 = -1`，`IntMath.mod(-7, 3) = 2`（恒非负）——循环索引、哈希取模场景正确性关键。
- `divide` 必须显式给 RoundingMode，防静默截断（JDK `/` 向零取整是经典坑）。


**JDK 替代对照（JDK 8 已覆盖大部分）**

| Guava | JDK 替代 |
| --- | --- |
| checkedAdd / Subtract / Multiply | `Math.addExact` / `subtractExact` / `multiplyExact`（JDK 8，溢出抛 ArithmeticException，同语义） |
| mod(a, m) | `Math.floorMod(a, m)`（JDK 8，结果非负，同语义） |
| pow / gcd / isPowerOfTwo / log2 | 部分无：pow 用 Math.pow(double) 注意精度；gcd 用 BigInteger.gcd；位运算手写 |
| saturatedAdd | 无；手写 clamp |

```java
// JDK 8 等价写法：等价 IntMath.checkedAdd / IntMath.mod
Math.addExact(100, 200);        // 300
Math.floorMod(-7, 3);           // 2（同 IntMath.mod，与 % 不同）
```

结论：checked 系列与 floorMod 用 JDK；gcd / 位运算便捷方法仍 Guava 方便。

## 五、math：Stats 与 Quantiles

### Stats / StatsAccumulator

流式统计（可增量喂数据）：

| API | 说明 |
| --- | --- |
| `Stats.of(...)` / `StatsAccumulator.add(...)` | 构造/增量 |
| `mean()` / `populationVariance()` / `sampleVariance()` | 均值/总体方差/样本方差 |
| `min()` / `max()` / `sum()` / `count()` | 基本量 |
| `toStats()` | 累积器转快照 |

```java
StatsAccumulator acc = new StatsAccumulator();
acc.addAll(ImmutableList.of(1.0, 2.0, 3.0, 4.0));
double mean = acc.snapshot().mean();    // 2.5
```

### Quantiles

分位数计算：`Quantiles.percentiles().index(99).compute(data)` 得 P99；支持 `quartiles()`、自定义刻度。

典型场景：接口耗时分布统计（TP99）——**替代手写排序取分位**，且是流式可增量。注意 Guava 的 Quantiles 需要全量数据（非流式），大样本注意内存。


**JDK 替代**：`DoubleSummaryStatistics`（JDK 8）只有 count / sum / min / max / average，**无方差、无分位数**。需要 TP99 等分位统计 → Guava Quantiles 或自实现。结论：基础统计用 JDK；分位数场景 Guava 无替代。

## 六、primitives：Ints / Longs 等工具（实测）

每个原始类型一个工具类：Ints、Longs、Shorts、Bytes、Booleans、Chars、Floats、Doubles。

| 方法 | 说明 |
| --- | --- |
| `tryParse(String)` | 安全解析，失败返回 **null**（不抛 NumberFormatException） |
| `asList(int...)` | 数组转固定长 List（**视图**，无装箱复制） |
| `concat(a, b)` | 拼接数组 |
| `contains(arr, v)` / `indexOf` | 线性查找 |
| `compare(a, b)` | 无溢出比较（比 a-b 安全） |
| `toArray(Collection)` | 包装类型集合转原始数组 |
| `min / max` | 最值 |
| `stringConverter()` | 与字符串互转的 Converter |

实测输出：

```
Ints.tryParse('42'): 42, tryParse('x'): null
```

易错点：

- `asList` 是数组的固定长视图：**不能 add/remove**（抛 UnsupportedOperationException），但可 set（直接改数组）。
- `tryParse` 返回 null 而非异常——调用方要判空，别解引用。
- 与 JDK 对比：JDK 8 后 Integer.parseInt 仍抛异常；`Integer.compare` 已覆盖 compare 需求；asList/concat 仍是 Guava 独有优势。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| tryParse(s) | 无；`Integer.parseInt` try-catch 包 Optional，或正则预检 |
| compare(a, b) | `Integer.compare` / `Long.compare`（JDK 7） |
| asList(int[]) | 无（`Arrays.asList` 是包装类型数组）；`IntStream.of(arr).boxed().toList()`（JDK 16） |
| concat(a, b) | 无；`IntStream.concat` 或 `System.arraycopy` |
| toArray(Collection) | `collection.stream().mapToInt(Integer::intValue).toArray()` |

```java
// JDK 等价写法
Integer.compare(1, 2);                          // -1，等价 Ints.compare
try { int v = Integer.parseInt(s); } catch (NumberFormatException e) { /* tryParse 返回 null 的分支 */ }
```

结论：compare 用 JDK；数组便捷操作（asList / concat）仍 Guava 方便。

## 七、primitives：Unsigned 无符号类型

| 类型 | 说明 |
| --- | --- |
| UnsignedInteger / UnsignedLong | 无符号包装（把 int/long 的最高位当数值位） |
| UnsignedInts / UnsignedLongs | 无符号运算工具（compare/divide/remainder/toString） |

```java
UnsignedInteger u = UnsignedInteger.fromIntBits(-1);   // 视为 4294967295
u.longValue();                                          // 4294967295
```

典型场景：C 协议解析、二进制协议字段、把"负数位模式"当大数用。日常业务极少用，了解即可。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| UnsignedInts.compare | `Integer.compareUnsigned`（JDK 8） |
| UnsignedLongs.divide / remainder | `Long.divideUnsigned` / `remainderUnsigned`（JDK 8） |
| UnsignedInteger 对象语义 | 无；`Integer.toUnsignedLong`（JDK 8） |

结论：无符号**运算**用 JDK 静态方法；需要对象包装语义（集合存储等）才用 Guava 包装类。

## 八、易错点汇总

- Charsets.UTF_8 → 新代码用 StandardCharsets（JDK 7+）。
- Guava Files 大量 deprecated → 用 MoreFiles + java.nio.file。
- IntMath.mod 与 % 负数行为不同。
- Ints.tryParse 返回 null 需判空。
- Ints.asList 是固定长视图，不能增删。
- 简单 Base64 用 JDK 的，复杂编码需求才上 Guava。

## 参考资料

- [Guava io javadoc（com.google.common.io）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/io/package-summary.html)，查询日期：2026-08-08
- [Guava math javadoc（com.google.common.math）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/math/package-summary.html)，查询日期：2026-08-08
- [Guava primitives javadoc（com.google.common.primitives）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/primitives/package-summary.html)，查询日期：2026-08-08
- 实测数据：guava 33.6.0-jre + JDK 17.0.12 本机运行
