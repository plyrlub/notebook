---
tags: [Lua, LuaJIT, FFI, 性能, 其他语言]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/其他语言/Lua）
归属: 01-学习/其他语言/Lua
---

# LuaJIT 与性能优化

> 上一篇：[13-Lua 5.4 新特性](13-Lua 5.4 新特性.md)

---

## 18.1 LuaJIT 是什么

LuaJIT 是 Lua 的 **JIT（Just-In-Time）编译器**实现：解释执行 + 热点代码编译为机器码，性能比标准 Lua 解释器高 **10~50 倍**（接近 C 的 1/2~1/3）。**OpenResty 1.5.8.1 起默认启用 LuaJIT**——你写 Nginx Lua 跑的就是 LuaJIT，不是标准 Lua！

| 对比 | 标准 Lua 5.4 | LuaJIT 2.1 |
|---|---|---|
| 执行方式 | 纯解释执行 | 解释 + JIT 编译机器码 |
| 性能 | 基准 | 快 10~50 倍 |
| 版本基线 | 5.4 | **5.1 语法** + 部分 5.2/5.3 扩展 |
| 内存限制 | 无（分代 GC） | GC64 模式前 2GB（OpenResty 已默认 GC64） |
| 典型场景 | 嵌入式/通用 | OpenResty、游戏（性能敏感） |

**陷阱**：LuaJIT 是 5.1 语法！5.4 的 `<const>`、`//` 整除、位运算 `&|~` 在 LuaJIT 里**都没有**（位运算 LuaJIT 有自己的 `bit` 库：`bit.band`/`bit.bor`）。OpenResty 写代码要按 5.1 规范，别用 5.4 语法。

## 18.2 FFI：零开销调用 C

FFI（Foreign Function Interface）是 LuaJIT 的王牌：**直接在 Lua 里声明并调用 C 函数/结构体**，无 C 绑定层，性能接近原生 C：

```lua
local ffi = require("ffi")
ffi.cdef[[
    int getpid(void);
    double sqrt(double x);
]]
print(ffi.C.getpid())       -- 进程号（直接调 libc）
print(ffi.C.sqrt(16))       -- 4.0
```

- 相比标准 Lua 的 LuaJIT `ffi` 是内置模块（标准 Lua 需要 C API 扩展才能调 C）
- OpenResty 的 `lua-resty-core` 就是 FFI 封装 Nginx C API（`ngx.re`/`ngx.ctx`），性能比纯 Lua 实现高
- **注意**：FFI 与 JIT 配合最好，纯解释模式下降级为 C 函数调用开销

## 18.3 GC 与性能优化建议

**GC 控制**：

```lua
collectgarbage("collect")        -- 手动触发完整 GC
collectgarbage("count")          -- 返回当前内存(KB)
collectgarbage("setpause", 200)  -- 调整 GC 节奏
collectgarbage("generational")   -- 5.4: 切分代 GC
```

**性能优化清单**（OpenResty/游戏场景）：

1. **local 化一切**：全局变量访问是 `_G` 表查找，local 是寄存器访问，快 10 倍以上；热循环里把 `math.floor` 等存 local
2. **字符串拼接用 table.concat**：`s = s .. "x"` 每次创建新串 O(n²)，`table.concat` 线性
3. **避免创建临时 table**：循环里 `{}` 触发 GC 压力，复用 table 或值类型
4. **热点函数别用 pcall**：有开销，边界保护用 `assert` 或前置判断
5. **数值用整数**：Lua 数字是 double，整数在 JIT 下更快；大数运算注意精度
6. **表预分配**：`table.new(n, m)`（LuaJIT 扩展）预分配避免 rehash
7. **避开 JIT 黑洞**：`string.gsub` 复杂 pattern、`load` 动态编译、`setmetatable` 某些场景会触发解释执行（NYI），热点路径避免

---
