---
tags: [Java, Guava, 三方库, collect, Immutable, Multimap, BiMap, Table, Multiset, 集合]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库/Guava）
归属: 01-学习/Java/三方库/Guava
---

# Guava collect集合增强详解

> 实测环境：guava 33.6.0-jre + JDK 17.0.12（实测数据标注于各节）
> 系列导航：[00-Guava概览与模块化辨析](00-Guava概览与模块化辨析.md)
> 包域：com.google.common.collect

## 📋 总纲

1. 为什么需要：JDK 集合的四个缺失能力
2. Immutable 集合：真不可变集合（实测）
3. Multimap：一键多值（实测）
4. BiMap：双向映射（实测）
5. Table：双键索引（实测）
6. Multiset：计数集合（实测）
7. RangeSet / RangeMap：区间管理
8. ClassToInstanceMap：类型键映射
9. 工具类：Lists / Maps / Sets / Iterables / Streams
10. 易错点汇总

## 一、为什么需要：JDK 集合的四个缺失能力

| JDK 缺失 | Guava 提供 |
| --- | --- |
| 真不可变集合（Collections.unmodifiableList 只是视图包装，原集合改了它也跟着变） | ImmutableList/Set/Map 系列 |
| 一键多值（Map<K, List<V>> 的样板代码与视图问题） | Multimap |
| 双向映射（维护两份 Map 容易不一致） | BiMap |
| 双键索引（Map<R, Map<C, V>> 嵌套） | Table |

Guava collect 是 Guava 的立身之本，上述四类 + Multiset + RangeSet 是核心增量。

## 二、Immutable 集合（实测）

### 类型与构造

| 类型 | 构造方式 | 特点 |
| --- | --- | --- |
| ImmutableList | `of(...)` / `copyOf(...)` / `builder()` | 有序、可 index |
| ImmutableSet | 同上 | 去重、无序（有 ImmutableSortedSet） |
| ImmutableMap | `of(k1,v1,...)` / `copyOf` / `builder()` | 不可变映射（有 ImmutableSortedMap） |
| ImmutableMultimap / ImmutableBiMap | 同上 | 不可变版复合集合 |

### 真不可变 vs unmodifiable 包装（核心区别）

| 维度 | Collections.unmodifiableList | ImmutableList |
| --- | --- | --- |
| 本质 | 原集合的**视图**，原集合可改，视图跟着变 | 复制后的**独立数据**，彻底不可变 |
| 修改操作 | 抛 UnsupportedOperationException | 抛 UnsupportedOperationException |
| 允许 null | 视原集合 | **拒绝 null**（构造即 NPE） |
| 内存 | 无额外复制 | 复制（builder 可复用） |

实测输出：

```
ImmutableList: [a, b, c], reversed: [c, b, a]
ImmutableMap: {k1=1, k2=2}
immutable add -> UnsupportedOperationException
```

易错点：

- ImmutableList **拒绝 null 元素**（`ImmutableList.of(null)` 直接 NPE），JDK List.of 同样拒绝；这是防御性设计。
- `ImmutableList.copyOf(可变List)` 复制快照，之后原 List 变化不影响不可变集合。
- `reverse()` 返回逆序视图不复制（实测 `[c, b, a]`）。
- 与 JDK 9+ `List.of()` 对比：功能重叠，JDK 版无 builder、无 copyOf 快照语义，Guava 版更丰富。


**JDK 替代对照（重点：JDK 9+ 已内置不可变集合）**

| Guava | JDK 替代 | 写法要点 |
| --- | --- | --- |
| ImmutableList.of(...) | `List.of(...)` | JDK 9+，同样拒绝 null |
| ImmutableList.copyOf(coll) | `List.copyOf(coll)` | JDK 10+，快照语义一致 |
| ImmutableMap.of(k,v,...) | `Map.of(k,v,...)` | JDK 9+，最多 10 对（超出用 `Map.ofEntries`） |
| builder() | `stream.collect(Collectors.toUnmodifiableList())` | JDK 10+；toUnmodifiableSet / toUnmodifiableMap 同理 |
| ImmutableSortedSet / SortedMap | 无直接 | `TreeSet` + unmodifiable 包装（注意是视图非拷贝） |
| reverse() 等高级方法 | 无 | JDK 版 API 更少，高级操作需手写 |

```java
// JDK 9+ 等价写法
List<String> list = List.copyOf(source);          // = ImmutableList.copyOf
Map<String, Integer> map = Map.of("k1", 1, "k2", 2);
List<String> built = stream.collect(Collectors.toUnmodifiableList());  // = builder().build()
```

结论：**JDK 9+ 项目直接用 List.of / copyOf**；JDK 8 项目才需要 Guava。

## 三、Multimap：一键多值（实测）

替代 `Map<K, List<V>>` 的手工样板代码。

| 实现 | 值容器 | 特点 |
| --- | --- | --- |
| ArrayListMultimap | List（ArrayList） | 值有序、可重复（实测用） |
| HashMultimap | Set（HashSet） | 值去重、无序 |
| LinkedHashMultimap | LinkedHashSet | 值去重、插入序 |
| TreeMultimap | TreeSet | 键值均有序 |
| ImmutableListMultimap / ImmutableSetMultimap | 不可变 | 配置类数据 |

| 方法 | 说明 |
| --- | --- |
| `put(k, v)` / `putAll(k, iterable)` | 添加 |
| `get(k)` | 返回**视图集合**（可直接 add，影响原 Multimap） |
| `keys()` | 键多集（含重复计数） |
| `keySet()` | 去重键集 |
| `entries()` | 所有键值对 |
| `size()` | **所有值总数**（不是键数！） |
| `asMap()` | 转为 Map<K, Collection<V>> 视图 |

实测输出：

```
get(a): [1, 2], size: 3, keySet: [a, b]
```

易错点：

- `size()` 是值总数（put 了 2+1=3），不是键数——统计键数用 `keySet().size()`。
- `get(k)` 返回的是**活视图**，直接往里 add 会写回 Multimap（与普通 Map.get 返回副本的直觉不同）。
- 与 JDK 对比：JDK 无原生替代（`groupingBy` 是一次性流水线，Multimap 是可变结构）。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| 一次性分组 | `Collectors.groupingBy(k -> ..., Collectors.toList())`（结果不可变 Map） |
| 反复累积（可增删） | `Map<K, List<V>>` + `computeIfAbsent(k, x -> new ArrayList<>()).add(v)`（JDK 8 样板代码） |

```java
// JDK 8 等价写法（一次性分组）
Map<String, List<Integer>> mm = list.stream()
        .collect(Collectors.groupingBy(Item::getKey, Collectors.toList()));
// 反复累积的样板
map.computeIfAbsent("a", k -> new ArrayList<>()).add(1);
```

结论：一次性分组用 Stream；反复累积且要活视图语义（get 直接 add）仍推荐 Guava Multimap。

## 四、BiMap：双向映射（实测）

| 方法 | 说明 |
| --- | --- |
| `put(k, v)` | 值重复时抛 IllegalArgumentException（保证双向唯一） |
| `forcePut(k, v)` | 值冲突时覆盖旧键值对 |
| `inverse()` | 反转视图（**不复制**，原 map 改动反向视图可见） |
| `get(k)` | 正向取值；inverse().get(v) 反向取键 |

实测输出：

```
forward: {one=1, two=2}, inverse.get(2): two
```

易错点：

- `put` 值重复抛异常（实测 HashBiMap 保证值唯一）；需要覆盖语义用 `forcePut`。
- `inverse()` 是视图不是副本——对 inverse 的修改会反映到原 map（双向一致，无需手动同步，这正是替代"两个 Map"方案的价值）。
- 与 JDK 对比：JDK 无 BiMap；手写两个 Map 维护一致性是经典 bug 源。


**JDK 替代**：无原生。手写两个 Map 需手动保证双向一致（经典 bug 源）；或自封装 inverse 视图。结论：双向映射场景 Guava BiMap 无替代，是必用项。

## 五、Table：双键索引（实测）

| 方法 | 说明 |
| --- | --- |
| `put(r, c, v)` / `get(r, c)` | 行列取值 |
| `row(r)` / `column(c)` | 行视图/列视图（Map<C,V>/Map<R,V>） |
| `rowMap()` / `columnMap()` | 嵌套 Map 视图 |
| `cellSet()` | Cell<r,c,v> 集合 |
| `contains(r, c)` / `containsRow` / `containsColumn` | 存在性 |

实现：HashBasedTable（HashMap 嵌套）、TreeBasedTable（有序行键）、ArrayTable（定长二维数组，省内存）。

实测输出：

```
get(row1,colA): 10, rowMap: {row1={colA=10, colB=20}, row2={colA=30}}
```

典型场景：成绩表（学生×科目）、权限矩阵（角色×资源）、报表二维汇总。

易错点：row/column 返回活视图；ArrayTable 构造即固定行列，越界抛 IndexOutOfBoundsException。


**JDK 替代**：无原生。嵌套 `Map<R, Map<C, V>>`（computeIfAbsent 两层样板）或定长二维数组。结论：双键索引场景 Guava Table 无替代。

## 六、Multiset：计数集合（实测）

| 方法 | 说明 |
| --- | --- |
| `count(element)` | 元素出现次数（实测 x 出现 2 次） |
| `add(e)` / `add(e, occurrences)` | 添加/批量添加 |
| `remove(e, occurrences)` | 批量移除 |
| `setCount(e, n)` | 直接设定次数 |
| `elementSet()` | 去重元素集 |
| `entrySet()` | Map.Entry<e, count> 视图（实测 `[x x 2, y]`） |

实现：HashMultiset（HashMap 计数）、TreeMultiset（有序）、LinkedHashMultiset（插入序）。

实测输出：

```
count(x): 2, entrySet: [x x 2, y]
```

典型场景：词频统计、库存计数、IP 访问统计。与 `Map<T, Integer>` 手写相比省去 getOrDefault+put 样板。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| 反复累积计数 | `Map<T, Integer>` + `merge(k, 1, Integer::sum)`（JDK 8） |
| count(e) | `map.getOrDefault(e, 0)` |
| 一次性词频统计 | `Collectors.groupingBy(Function.identity(), Collectors.counting())` |

```java
// JDK 8 等价写法：等价 ms.add(x) 两次
Map<String, Integer> counts = new HashMap<>();
counts.merge("x", 1, Integer::sum);
counts.merge("x", 1, Integer::sum);   // count("x") == 2
```

结论：单次统计用 Stream；反复增删计数用 merge 或 Guava（Multiset 的 setCount 批量语义更省事）。

## 七、RangeSet / RangeMap：区间管理

| API | 说明 |
| --- | --- |
| RangeSet.add(Range) | 加入区间（自动合并相邻/重叠） |
| RangeSet.remove(Range) | 移除区间（自动拆分） |
| RangeSet.span() | 覆盖所有区间的范围 |
| RangeMap.put(Range, V) / asMapOfRanges() | 区间 → 值映射 |

```java
RangeSet<Integer> rs = TreeRangeSet.create();
rs.add(Range.closed(1, 10));
rs.add(Range.closed(5, 15));       // 自动合并为 [1..15]
rs.remove(Range.closed(3, 5));     // 拆成 [1..3) 与 (5..15]
```

典型场景：IP 段管理、优惠券时段、日历冲突检测。Range 本身（closed/open/closedOpen/atLeast/atMost/contains/intersection）见实测：

```
closedOpen(1,10) contains(1): true, contains(10): false
intersection: [5..10)
```


**JDK 替代**：无。手写边界比较或 TreeMap 区间管理；RangeSet 的自动合并/拆分语义无替代。结论：区间管理场景 Guava 无替代。

## 八、ClassToInstanceMap

`Map<Class<? extends T>, T>` 的类型安全版：`getInstance(Class)` / `putInstance(Class, T)` 编译期校验类型匹配。典型场景：异构配置对象注册表（类型 → 实例）。


**JDK 替代**：无。`Map<Class<?>, Object>` + 手写强转（失去编译期类型检查）。结论：异构类型注册表用 Guava 更安全。

## 九、工具类：Lists / Maps / Sets / Iterables / Streams

| 工具 | 常用方法 | 说明 |
| --- | --- | --- |
| Lists | `newArrayList(...)`、`partition(list, n)`、`reverse(list)`、`transform(list, fn)` | partition 分页切片常用 |
| Maps | `newHashMap()`、`uniqueIndex(iterable, keyFn)`、`toMap`、`difference(a, b)` | uniqueIndex 按键提取建 Map |
| Sets | `newHashSet()`、`union/intersection/difference(a, b)`、`powerSet`、`combinations` | 集合运算 |
| Iterables | `filter`、`transform`、`limit`、`getFirst`、`concat` | 惰性迭代（**集合运算不复制**） |
| Streams | `stream(Iterable)`、`concat(s1, s2)`、`stream(Iterator)` | Iterable ↔ Stream 桥接 |

易错点：

- `Iterables.filter/transform` 是**惰性视图**，与原集合共享数据；遍历时原集合并发修改会出问题。
- JDK 8+ 有 Stream 后，Lists.transform 类方法的价值下降，新代码优先 Stream 表达。


**JDK 替代对照**

| Guava | JDK 替代 |
| --- | --- |
| Lists.partition | 无直接；手写 subList 循环 |
| Lists.transform / reverse | Stream map + `Collections.reverse`（JDK 8） |
| Iterables.filter / transform | `Stream.filter` / `map`（注意 Stream 一次性，Guava 视图可反复遍历） |
| Sets.union / intersection | 无；手写 retainAll / removeAll 拷贝 |
| Maps.uniqueIndex | `Collectors.toMap(keyFn, Function.identity())` |
| Streams.stream(iterable) | `StreamSupport.stream(iterable.spliterator(), false)` |

结论：流式处理用 Stream；需要"反复遍历的惰性视图"（Iterables）或分页切片（partition）时 Guava 仍有价值。

## 十、易错点汇总

- Immutable 集合拒绝 null；unmodifiable 包装只是视图。
- Multimap.size() 是值总数不是键数；get(k) 返回活视图。
- BiMap 值唯一，重复 put 抛异常，覆盖用 forcePut。
- Table 的 row/column 是视图。
- 误用 Iterables 惰性视图做快照。

## 参考资料

- [Guava collect javadoc（com.google.common.collect）](https://guava.dev/releases/33.6.0-jre/api/docs/com/google/common/collect/package-summary.html)，查询日期：2026-08-08
- [Guava Collection 教学 wiki](https://github.com/google/guava/wiki/CollectionHelpersExplained)，查询日期：2026-08-08
- 实测数据：guava 33.6.0-jre + JDK 17.0.12 本机运行
