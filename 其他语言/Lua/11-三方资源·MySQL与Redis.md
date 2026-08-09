---
tags: [Lua, MySQL, Redis, Lua脚本, 其他语言]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/其他语言/Lua）
归属: 01-学习/其他语言/Lua
---

# Lua 三方资源·MySQL与Redis

> 上一篇：[10-文件与包管理](10-文件与包管理.md)
> 下一篇：[12-环境隔离与沙箱](12-环境隔离与沙箱.md)

---

这里设计三方库

> 📌 原笔记书签链接已丢失

LuaRocks is the package manager for Lua modules.

1. 安装rocks工具
    
```bash
brew install luarocks
    -- 其他系统自行查询
```

1. 使用工具安装三方库
    
```lua
luarocks install luasql-mysql
```

## 1. 操作 MySQL

luasql

安装的时候可能会提示， 需要先安装mysql，并指定路径

```bash
You may have to install MYSQL in your system and/or pass MYSQL_DIR or MYSQL_INCDIR to the luarocks command.
Example: luarocks install luasql-mysql MYSQL_DIR=/usr/local
```

> [!note] 安装此三方库需要对应数据库

安装后就可以编写代码了

```lua
local luasql = require("luasql.mysql")

client = luasql.mysql()

-- 创建链接
conn = client:connect("dbName","dbUser","dbPwd","127.0.0.1",3306)

rs = conn:execute("sql 语句")
-- 增删改都是返回影响行数

-- rs.fetch({}, "a")  -- 查询的时候需要对结果进行处理

-- 后续收尾操作
conn:close()
client:close()
```

## 2. 操作 Redis

需要先安装luasocket

然后将redis-lua源码下载下来，将src中的lua文件拿出来使用即可

```lua
local redis = require("redis")

local config = {host="127.0.0.1", port=6379}

local client = redis.connect(config)

-- info = client.info()
client:get("key")
client:del("key")
```

### 2.1 Redis 内部跑 Lua

这是比较常见的一个场景，比如分布式锁，限流等场景（详见 14.3）。

## 3. Redis Lua 脚本实战（分布式锁 / 限流）★

> **为什么用 Lua**：Redis 执行 Lua 脚本是**原子**的（脚本整体作为一个操作执行，期间不会有其他命令插入），这是「读-判-写」三步操作安全的根本保证——也是分布式锁、限流、计数器的核心原理。Java 端通过 `DefaultRedisScript<T>` + `redisTemplate.execute(script, keys, args)` 调用。

**执行方式**：

| 命令 | 说明 |
|---|---|
| `EVAL script numkeys key... arg...` | 直接执行脚本 |
| `SCRIPT LOAD script` | 预编译脚本，返回 SHA1 |
| `EVALSHA sha1 numkeys key... arg...` | 用 SHA1 执行（避免每次传脚本） |
| `SCRIPT EXISTS sha1` | 检查脚本是否已缓存 |

**Redis 里的 Lua 环境**：
- 内置 `redis.call(cmd, ...)` / `redis.pcall(cmd, ...)` 调 Redis 命令（pcall 出错返回 err 表而不抛异常）
- 内置 `KEYS[i]`（key 参数）和 `ARGV[i]`（arg 参数），**访问 key 必须通过 KEYS 传**（集群分片依赖 key 声明）
- 返回：Lua 值自动转 Redis 类型（table→数组，nil→false，number→整数）
- **注意版本**：Redis 内置 Lua 5.1——**没有** `goto`、`//` 整除、位运算符（5.3+ 才有 bit 库）、`<const>` 等 5.4 新特性！

**分布式锁（解锁必须用 Lua 保证原子性）**：

```lua
-- 加锁：SET key value NX PX 30000 已由 Redis 命令原子完成
-- 解锁：先比较 value（防止删掉别人的锁），再 DEL —— 两步必须 Lua 原子
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
```

```java
// Spring Data Redis 使用示例
DefaultRedisScript<Long> unlockScript = new DefaultRedisScript<>();
unlockScript.setScriptText(
    "if redis.call('get', KEYS[1]) == ARGV[1] then " +
    "return redis.call('del', KEYS[1]) else return 0 end");
unlockScript.setResultType(Long.class);
redisTemplate.execute(unlockScript, Collections.singletonList("lock:order:1001"), requestId);
```

> 加锁必须带唯一标识 value（如 UUID + 线程号）：否则 A 持锁超时后 B 加锁，A 释放时会把 B 的锁删掉（经典误删）。

**固定窗口限流（Lua 原子 读-判-写）**：

```lua
-- KEYS[1]=限流 key, ARGV[1]=窗口毫秒, ARGV[2]=阈值
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])  -- 第一次设置窗口过期
end
return current <= tonumber(ARGV[2])
```

**令牌桶限流（滑动窗口版）**：

```lua
-- KEYS[1]=令牌桶key, ARGV[1]=容量, ARGV[2]=速率(每秒), ARGV[3]=当前时间ms, ARGV[4]=请求token数
local tokenKey, timeKey = KEYS[1], KEYS[1] .. ':time'
local capacity, rate = tonumber(ARGV[1]), tonumber(ARGV[2])
local now, need = tonumber(ARGV[3]), tonumber(ARGV[4])

local tokens = tonumber(redis.call('GET', tokenKey) or capacity)
local lastTime = tonumber(redis.call('GET', timeKey) or now)
-- 按时间差补令牌
local delta = math.max(0, (now - lastTime) / 1000)
tokens = math.min(capacity, tokens + delta * rate)
redis.call('SET', tokenKey, tokens)
redis.call('SET', timeKey, now)

if tokens >= need then
    redis.call('SET', tokenKey, tokens - need)
    return 1
else
    return 0
end
```

**易错点**：
- 脚本内**不能**用全局变量（5.1 环境隔离，直接报错），所有中间值必须 `local`
- `redis.call` 出错会抛异常中断脚本，用 `redis.pcall` 可捕获返回 `{err=...}` 表
- 不要在脚本里 `KEYS[1]` 拼接字符串做 key（`KEYS[1]..':time'` 可以，但 `KEYS[1]` 必须是**调用方传入**的，不能从 ARGV 拼——集群模式下 key 无法预声明会报 CROSSSLOT）
