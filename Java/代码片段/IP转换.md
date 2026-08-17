---
tags: [Java, 代码片段, IP, 工具类, IPv4, IPv6]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/代码片段）
归属: 01-学习/Java/代码片段
---

# IP转换（IPv4 ↔ long / IPv6 ↔ BigInteger）

> 代码片段库：直接复制使用的工具方法
> 实测环境：JDK 17.0.12 本机运行（实测输出标注于各节）

## 📋 总纲

1. 适用场景：什么时候需要 IP 数值化
2. IPv4 ↔ long：MySQL INT UNSIGNED 存取（实测）
3. IPv6 ↔ BigInteger：InetAddress 通用方案（实测）
4. 注意点汇总

## 一、适用场景

| 场景 | 说明 |
| --- | --- |
| MySQL 存 IP | `INT UNSIGNED` 存取（4 字节 vs 字符串 15 字节，可建索引范围查询） |
| 日志分析 | IP 转数值排序/聚合/区间判断 |
| GeoIP | 数值区间映射地理位置 |

## 二、IPv4 ↔ long

```java
/** IPv4 字符串 → long（位移拼接用 |，语义清晰） */
public static long ip2Long(String ipStr) {
    String[] ip = ipStr.split("\\.");
    return (Long.parseLong(ip[0]) << 24)
            | (Long.parseLong(ip[1]) << 16)
            | (Long.parseLong(ip[2]) << 8)
            | Long.parseLong(ip[3]);
}

/** long → IPv4 字符串（>>> 无符号右移） */
public static String long2Ip(long ipLong) {
    return (ipLong >>> 24) + "." + ((ipLong >>> 16) & 0xFF) + "."
            + ((ipLong >>> 8) & 0xFF) + "." + (ipLong & 0xFF);
}
```

实测输出（JDK 17.0.12）：

```
ip2Long(192.168.0.1)      = 3232235521
long2Ip(3232235521L)      = 192.168.0.1
ip2Long(0.0.0.0)          = 0
ip2Long(255.255.255.255)  = 4294967295
long2Ip(4294967295L)      = 255.255.255.255
roundtrip(10.20.30.40)    = 10.20.30.40
```

注意点：

- **必须用 long**：192.168.0.1 → 3232235521 超过 int 上限（int 最大 2147483647）。
- MySQL 对应 `INT UNSIGNED`（0 ~ 4294967295），与 long 值域一致。
- 每段位移 8 位后无重叠，`+` 与 `|` 结果相同；`|` 更能表达位拼接语义。
- `long2Ip` 用 `>>>` 无符号右移，避免最高位为 1 时符号扩展。
- **IPv4-only**：IPv6 见下节。

## 三、IPv6 ↔ BigInteger

```java
/** IP 字符串（IPv4/IPv6 通用）→ BigInteger */
public static BigInteger ipToBigInteger(String ip) throws Exception {
    return new BigInteger(1, InetAddress.getByName(ip).getAddress());
}

/** BigInteger → IPv6 字符串（固定 16 字节右侧对齐） */
public static String bigIntegerToIp(BigInteger value) throws Exception {
    byte[] raw = value.toByteArray();
    byte[] bytes = new byte[16];
    int src = raw.length, dst = 16;
    while (src > 0 && dst > 0) bytes[--dst] = raw[--src];   // 低位右对齐补零
    return InetAddress.getByAddress(bytes).getHostAddress();
}
```

实测输出（JDK 17.0.12）：

```
ipToBigInteger(2001:db8::1) = 42540766411282592856903984951653826561
  -> bigIntegerToIp = 2001:db8:0:0:0:0:0:1
ipToBigInteger(::1) = 1  ->  bigIntegerToIp = 0:0:0:0:0:0:0:1
ipToBigInteger(fe80::1) = 338288524927261089654018896841347694593
  -> bigIntegerToIp = fe80:0:0:0:0:0:0:1
ipToBigInteger(::ffff:192.168.0.1) = 3232235521  ->  bigIntegerToIp = 0:0:0:0:0:0:c0a8:1
bigIntegerToIp(1) = 0:0:0:0:0:0:0:1
```

注意点（实测发现的真实行为）：

- **getHostAddress 返回非压缩格式**：`2001:db8::1` 还原成 `2001:db8:0:0:0:0:0:1`（不带 `::` 压缩）。需要压缩格式得自行处理（或接受此形式用于存储/比较）。
- **IPv4-mapped 地址陷阱**：`::ffff:192.168.0.1` 会被 `getByName` 解析成 **Inet4Address**（getAddress 只有 4 字节），BigInteger 值 = IPv4 的 long 值 3232235521——判断 IPv4/IPv6 时要注意这个等价关系。
- `new BigInteger(1, bytes)` 的 `1` 是 signum（正数），避免符号位。
- `toByteArray()` 可能带前导 0 符号位（>16 字节），右侧对齐补零到 16 字节解决。
- IPv4 场景优先用 long 方案（更简单高效），IPv6 才用 BigInteger。

## 四、注意点汇总

- IP 数值化后**不可逆回原始字符串格式**（如 IPv6 压缩形式），存储/展示前定好规范。
- MySQL 存 IPv6 建议 `BINARY(16)` / `VARBINARY(16)`（BigInteger 转 16 字节数组），或字符串存储。
- 涉及网络输入（用户 IP）时用 `InetAddress.getByName` 前先校验格式（防止 DNS 解析：纯 IP 字面量不会触发 DNS，但带主机名的输入会）。

## 参考资料

- [java.net.InetAddress 文档](https://docs.oracle.com/javase/8/docs/api/java/net/InetAddress.html)，查询日期：2026-08-08
- 实测数据：JDK 17.0.12 本机运行（demo 已清理，输出如实标注）
