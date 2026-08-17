---
tags: [Java, Guava, 三方库, base, Preconditions, Joiner, Splitter, CharMatcher, 字符串]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava base与字符串处理详解

> 实测环境：guava 33.6.0-jre + JDK 17.0.12（实测数据标注于各节）
> 系列导航：[00-Guava概览与模块化辨析](00-Guava概览与模块化辨析.md)
> 包域：com.google.common.base

## 📋 总纲

1. Preconditions：参数校验五件套
2. MoreObjects：toStringHelper 与 firstNonNull
3. Optional：Guava 版与 JDK 版对比
4. Strings：空值/补位/重复工具
5. Joiner：拼接（实测）
6. Splitter：拆分（实测）
7. CharMatcher：字符匹配器（23.1 API 重构说明）
8. CaseFormat：命名风格互转
9. Throwables：异常工具（33.x 废弃说明）
10. Enums：枚举工具

## 一、Preconditions：参数校验

方法逐个详解（全部失败时抛异常，消息支持 %s 占位符）：

| 方法 | 校验 | 失败异常 | 说明 |
| --- | --- | --- | --- |
| `checkArgument(boolean)` | 参数条件 | IllegalArgumentException | 最常用，校验业务参数 |
| `checkNotNull(T)` | 非空 | NullPointerException | 返回原值，可链式赋值 |
| `checkState(boolean)` | 对象状态 | IllegalStateException | 校验状态而非参数 |
| `checkElementIndex(int, int)` | 索引合法 | IndexOutOfBoundsException | 数组/列表下标校验 |
| `checkPositionIndex(int, int)` | 位置合法（可等于 size） | IndexOutOfBoundsException | 插入位置校验 |

消息占位符：`checkArgument(1 > 2, "must be %s > %s", 1, 2)` 输出 `must be 1 > 2`——**只在失败时才拼接消息**，避免了字符串拼接的性能开销（这是相对手写 if + 拼接的核心优势）。

实测输出（guava 33.6.0-jre）：

```
checkArgument msg: must be 1 > 2
checkNotNull msg: null value at field
```

与 JDK 对比：

| 场景 | JDK 写法 | Guava 写法 |
| --- | --- | --- |
| 非空校验 | Objects.requireNonNull(x, "msg") | Preconditions.checkNotNull(x, "msg") |
| 参数条件 | 手写 if + throw | checkArgument |
| 索引校验 | 手写边界判断 | checkElementIndex |

易错点：checkArgument 的 boolean 参数是"条件为真才通过"，写反条件（传了非法时的值）是最高频错误。


**JDK 替代对照**

| Guava | JDK 替代 | 写法要点 |
| --- | --- | --- |
| checkNotNull(x, msg) | `Objects.requireNonNull(x, msg)` | 同语义，JDK 7+ |
| checkArgument / checkState | 无直接替代 | 手写 `if (!cond) throw new IllegalArgumentException(...)` |
| checkElementIndex(i, n) | `Objects.checkIndex(i, n)` | JDK 9+，抛 IndexOutOfBoundsException |
| checkPositionIndex(i, n) | 无直接替代 | Objects.checkFromToIndex 部分场景可用 |

结论：非空/索引校验可用 JDK；参数条件校验 JDK 无替代，Guava 仍是最简写法（且只在失败时拼接消息，无字符串开销）。

## 二、MoreObjects

| 方法 | 说明 |
| --- | --- |
| `toStringHelper(obj)` | 流式拼接 toString：`MoreObjects.toStringHelper(this).add("id", id).toString()` |
| `firstNonNull(a, b)` | 返回第一个非 null（**33.x 已废弃**，改用 JDK `Objects.requireNonNullElse`） |
| `Objects.equals/hashCode` | 与 JDK Objects 功能重复，直接用 JDK 版即可 |


**JDK 替代对照**

| Guava | JDK 替代 | 写法要点 |
| --- | --- | --- |
| toStringHelper | 无（用 Lombok `@ToString`） | 或手写 StringBuilder |
| firstNonNull(a, b) | `Objects.requireNonNullElse(a, b)` | JDK 9+，同语义 |
| Objects.equals / hashCode | `java.util.Objects` 同名方法 | 直接用 JDK 版即可 |

## 三、Optional：Guava 版 vs JDK 版

Guava Optional 是 JDK 8 java.util.Optional 的"原型"，JDK 版出现后 Guava 官方建议**新代码用 java.util.Optional**（Guava 版未删除但不再推荐，且与 JDK 版有语义差异）。

关键差异：

| 维度 | Guava Optional | java.util.Optional |
| --- | --- | --- |
| 可空包装 | 不支持 null 值 | 支持（ofNullable） |
| 作为字段/参数 | 官方曾建议 | JDK 官方不建议作字段 |
| 序列化 | 实现 Serializable | 否 |

结论：新项目直接 `java.util.Optional`，Guava Optional 仅历史代码维护需要了解。


**JDK 替代**：`java.util.Optional` 完全替代（Guava 官方推荐迁移）。注意 JDK 版支持 `ofNullable`（Guava 版不支持 null 值），语义差异见上文表格；新代码一律用 JDK 版。

## 四、Strings：字符串工具

| 方法 | 说明 | 示例（实测） |
| --- | --- | --- |
| `padEnd(s, minLen, padChar)` | 尾部补位 | `padEnd("ab", 5, '*')` → `ab***` |
| `padStart(s, minLen, padChar)` | 头部补位 | 数字对齐场景常用 |
| `repeat(s, count)` | 重复拼接 | `repeat("ab", 3)` → `ababab` |
| `commonPrefix(a, b)` | 最长公共前缀 | 路径/字符串比较 |
| `commonSuffix(a, b)` | 最长公共后缀 | |
| `nullToEmpty(s)` | null → "" | |
| `emptyToNull(s)` | "" → null | `emptyToNull("")` → `null` |
| `isNullOrEmpty(s)` | 判空（含 null） | `isNullOrEmpty("")` → `true` |

实测输出：

```
padEnd: [ab***]
repeat: ababab
emptyToNull: null
isNullOrEmpty(''): true
```

注意：Guava 没有 isBlank/trim 类方法（JDK 11 String.isBlank 已覆盖）。


**JDK 替代对照**

| Guava | JDK 替代 | 写法要点 |
| --- | --- | --- |
| padEnd / padStart | 无直接替代 | `String.format("%-5s", s)` 部分场景可用，但中文宽度处理不友好 |
| repeat | `String.repeat(n)` | **JDK 11+** 直接替代 |
| commonPrefix / commonSuffix | 无 | 手写循环比较 |
| nullToEmpty | `Objects.toString(s, "")` | JDK 7+ |
| emptyToNull | 无 | 手写 `s.isEmpty() ? null : s` |
| isNullOrEmpty | 无 | `s == null \|\| s.isEmpty()`；注意 JDK 11 `isBlank()` 语义不同（含空白） |

## 五、Joiner：拼接（实测）

把集合/迭代器拼成字符串，解决 `String.join` 和 `Collectors.joining` 处理 null 的痛点。

| 方法 | 说明 |
| --- | --- |
| `on(separator)` | 指定分隔符（String 或 char） |
| `skipNulls()` | 跳过 null 元素 |
| `useForNull(replacement)` | null 替换为占位字符串（与 skipNulls 互斥） |
| `withKeyValueSeparator("=")` | 拼接 Map 为 key=value 形式 |
| `join(Iterable/array)` | 执行拼接 |

实测输出：

```
join skipNulls: a, b        # Joiner.on(", ").skipNulls().join(["a", null, "b"])
```

易错点：

- `skipNulls` 与 `useForNull` 二选一，同时调用抛 IllegalStateException。
- null 元素**不处理会 NPE**——`String.join` 遇 null 会拼出 "null" 字符串，Guava 则直接抛 NPE，行为更严格。
- 拼接 Map 时 key 或 value 为 null 同样需 skipNulls/useForNull。


**JDK 替代对照**

| Guava | JDK 替代 | 写法要点 |
| --- | --- | --- |
| `Joiner.on(",").join(list)` | `String.join(",", list)` | JDK 8+；但遇 null 会拼出字面 "null"（Guava 是 NPE 或跳过） |
| skipNulls / useForNull | `list.stream().filter(Objects::nonNull).collect(Collectors.joining(","))` | Stream 版，可读性稍差 |
| withKeyValueSeparator | 无 | 手写 entrySet 循环拼接 |

```java
// JDK 8+ 等价写法
String joined = list.stream()
        .filter(Objects::nonNull)
        .collect(Collectors.joining(", "));   // 等价 Joiner.on(", ").skipNulls().join(list)
```

## 六、Splitter：拆分（实测）

比 `String.split` 更安全可控的拆分工具（String.split 的 regex 语义与空串保留策略是经典坑）。

| 方法 | 说明 |
| --- | --- |
| `on(separator)` | 分隔符（String/char/Pattern） |
| `trimResults()` | 去除每段首尾空白 |
| `omitEmptyStrings()` | 丢弃空段 |
| `limit(n)` | 限制拆分段数 |
| `splitToList(s)` | 返回不可变 List（**推荐**） |
| `split(s)` | 返回 Iterable（惰性，过大的串有 OOM 风险） |

实测输出：

```
splitToList: [a, b, c]       # Splitter.on(',').trimResults().omitEmptyStrings().splitToList(" a, b, ,c ")
```

与 String.split 对比（核心差异）：

| 场景 | String.split | Splitter |
| --- | --- | --- |
| "a,b," 尾部空串 | 默认丢弃（limit<0 才保留） | omitEmptyStrings 控制，默认**保留** |
| 正则 | 总是正则（`.` 要转义） | on() 默认字面量，需要正则才用 on(Pattern) |
| 空串 "a,,b" | 保留空段 | 保留空段（可 omitEmptyStrings 丢弃） |
| 结果 | String[] | 不可变 List |

易错点：`split()` 返回惰性 Iterable，对超大输入用 `splitToList` 更安全；`String.split(".")` 全拆成空数组的经典坑在 Splitter.on('.') 不存在（字面量语义）。


**JDK 替代**：`String.split`（注意其 regex 语义与尾部空串默认丢弃的差异，见上表）；JDK 无 trimResults + omitEmptyStrings 的组合，`split("\\s*,\\s*")` 正则可近似但易错。结论：简单分隔用 split，健壮拆分场景仍推荐 Splitter。

## 七、CharMatcher：字符匹配器

字符集合的声明式工具，**23.1 版本经历 API 重构**：静态常量（如 `CharMatcher.WHITESPACE`）改为静态方法（`CharMatcher.whitespace()`），旧写法编译失败。

| 静态工厂 | 说明 |
| --- | --- |
| `whitespace()` | 空白字符 |
| `anyOf("aeiou")` | 指定字符集合 |
| `is(char)` / `isNot(char)` | 单字符匹配 |
| `inRange(a, b)` | 字符区间（如 inRange('a','z')） |
| `digit()` / `javaLetter()` / `javaDigit()` | 数字/字母 |
| `none()` / `any()` | 空集/全集 |

| 实例方法 | 说明 |
| --- | --- |
| `removeFrom(s)` | 移除匹配字符 |
| `retainFrom(s)` | 保留匹配字符（移除其他） |
| `trimFrom(s)` / `trimLeadingFrom` / `trimTrailingFrom` | 去首尾匹配字符 |
| `replaceFrom(s, ch)` | 替换匹配字符 |
| `countIn(s)` | 统计匹配数量 |
| `matchesAllOf/matchesAnyOf` | 全匹配/存在匹配 |
| 组合：`or` / `and` / `negate` | 集合运算 |

示例：

```java
String digits = CharMatcher.inRange('0', '9').retainFrom("abc123def");  // "123"
String trimmed = CharMatcher.whitespace().trimFrom("  hi  ");           // "hi"
```

易错点：23.1 前的 `CharMatcher.WHITESPACE` 字段写法已失效，老代码迁移需改方法调用。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| whitespace() | `Character.isWhitespace(c)` + 手写循环；JDK 11 `String.isBlank()` |
| inRange / is / anyOf | `Character.isDigit` / `isLetter` 部分覆盖；无声明式字符集合 |
| removeFrom / retainFrom | `String.replaceAll("正则", "")` 或手写循环 |
| trimFrom | `String.trim()` / `strip()`（JDK 11，Unicode 感知） |

结论：单字符判断用 Character；字符串清洗 JDK 无完整替代，复杂规则仍用 CharMatcher。

## 八、CaseFormat：命名风格互转

枚举表示命名风格，`to(targetFormat, str)` 互转：

| 常量 | 风格 | 示例 |
| --- | --- | --- |
| LOWER_CAMEL | 小驼峰 | `orderId` |
| UPPER_CAMEL | 大驼峰 | `OrderId` |
| LOWER_UNDERSCORE | 下划线小写 | `order_id` |
| UPPER_UNDERSCORE | 下划线大写 | `ORDER_ID` |
| LOWER_HYPHEN | 连字符小写 | `order-id` |

```java
CaseFormat.LOWER_CAMEL.to(CaseFormat.LOWER_UNDERSCORE, "orderId");  // "order_id"
```

典型场景：数据库列名 ↔ Java 字段名、JSON 命名风格转换。


**JDK 替代**：无。需自行正则处理或依赖框架内置工具（如 MyBatis 的驼峰↔下划线自动映射、Jackson 的命名策略）。命名风格互转场景 Guava 仍是最简方案。

## 九、Throwables：异常工具

| 方法 | 说明 | 33.x 状态 |
| --- | --- | --- |
| `getStackTraceAsString(Throwable)` | 异常转字符串（日志友好） | 保留 |
| `throwIfInstanceOf(t, X.class)` | 类型匹配则原样抛出 | 保留 |
| `throwIfUnchecked(t)` | RuntimeException/Error 原样抛，checked 包装 | 保留 |
| `propagate(t)` | 包装抛 RuntimeException | **已废弃**（用 throwIfUnchecked） |
| `getRootCause(t)` | 根因提取 | **已废弃**（JDK 9+ 无直接替代，手写遍历） |

实测输出：

```
stack starts: java.lang.RuntimeException: boom
```

易错点：33.x 起 Throwables 部分方法进入废弃，新版代码用 throwIfUnchecked 替代 propagate；getRootCause 废弃后需自行 while 遍历 getCause。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| getStackTraceAsString | 手写：`StringWriter w = new StringWriter(); e.printStackTrace(new PrintWriter(w));` |
| throwIfInstanceOf(t, X.class) | 手写：`if (t instanceof X) throw (X) t;` |
| throwIfUnchecked(t) | 手写：`if (t instanceof RuntimeException) throw (RuntimeException) t;` |
| getRootCause（已废弃） | 手写 while 循环遍历 getCause() 至 null |

## 十、Enums：枚举工具

| 方法 | 说明 |
| --- | --- |
| `getField(enumValue)` | 返回枚举值对应的字段（反射，可用作常量引用） |
| `getIfPresent(Class, name)` | 按名取值，不存在返回 Optional（**不抛异常**，比 valueOf 友好） |
| `stringConverter(Class)` | 名字 ↔ 枚举的 Converter |

```java
Optional<Color> c = Enums.getIfPresent(Color.class, "RED");  // 存在则 Optional.of
```


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| getIfPresent(cls, name) | 手写 try-catch：`try { return Optional.of(Enum.valueOf(cls, name)); } catch (IllegalArgumentException e) { return Optional.empty(); }` |
| getField | 反射手写；通常直接用枚举常量引用即可，无需反射 |
| stringConverter | 无；`Enum.valueOf` 双向手写 |

## 易错点汇总

- checkArgument 条件写反。
- Joiner 的 skipNulls 与 useForNull 互斥。
- 误以为 Splitter.on 是正则（默认字面量）。
- CharMatcher 用 23.1 前的字段写法（WHITESPACE）编译失败。
- Throwables.propagate 已废弃，新代码用 throwIfUnchecked。

## 参考资料

- [Guava base javadoc（com.google.common.base）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/base/package-summary.html)，查询日期：2026-08-08
- [Guava Strings 教学 wiki](https://github.com/google/guava/wiki/StringsExplained)，查询日期：2026-08-08
- 实测数据：guava 33.6.0-jre + JDK 17.0.12 本机运行
