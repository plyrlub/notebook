---
tags: [Lua, 数据类型, table, 其他语言]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/其他语言/Lua）
归属: 01-学习/其他语言/Lua
---

# Lua数据类型与table

> 上一篇：[01-基础语法](01-基础语法.md)
> 下一篇：[03-运算符与流程控制](03-运算符与流程控制.md)

---

There are eight basic types in Lua: nil, boolean, number, string, function, userdata, thread, and table.

库函数type() 返回一个描述给定值类型的字符串

- 其中 nil 类型只有一个值：nil
- string 类型，不管是单引号还是双引号，或者单字节或多字节
- userdata 是自定义数据格式
- thread 是协程
    ```lua
type(print)
> function

type({})
> table
```

> [!note] 在lua中，只有nil 和 false 才表示假，其他都直接表示真，包括0 或者 空串 也表示真

```lua
local a = 0
local b = ''

if a then
    print("真")
else
    print("假")
end

if b then
    print("真")
else
    print("假")
end
```

> 输出：
> 真
> 真

## 1. function

function 是 Lua 的**第一类值**（first-class value）：可以存变量、作参数、作返回值。基础定义形式：

```lua
-- 全局函数（本质是赋给全局变量的匿名函数）
function add(a, b)
    return a + b
end
-- 等价于：add = function(a, b) return a + b end

-- 局部函数
local function sub(a, b)
    return a - b
end

-- 匿名函数直接调用
print((function(x) return x * 2 end)(21))  -- 42

-- 函数作为参数（高阶函数）
local function apply(f, x) return f(x) end
print(apply(function(v) return v + 1 end, 10))  -- 11
```

> 深层玩法（闭包/table 内嵌函数/可变参数）见 [04-函数与闭包](04-函数与闭包.md)。

## 2. table 表

不是指数据库中的表，而是一种数据类型

### 2.1 Map 形式

类似于 Map，用k-v的方式来表现

理论上除了nil之外，其他类型都可以成为k

格式：

```lua
tableName = {
  k=v,
}

local info = {
    name = "luo",
    age = 23,
    sex = "man"
}
```

遍历

```lua
print(info.name)

for k, v in pairs(info) do
    print(k,'-->',v)
end
```

```lua
luo
name    -->     luo
sex     -->     man
age     -->     23
```

增加字段

```lua
info.id = 1;
info['country'] = 'china'
```

删除字段

```lua
info.id = nil
info['sex'] = nil
```

### 2.2 数组形式

```lua
tableName = {
  v1, v2, v3
}

local info = {
    "luo",
    23,
    "man"
}
```

> 其实是有默认的 k 的，从1 开始

```lua
print(info[1])

for k, v in pairs(info) do
    print(k,'-->',v)
end
```

> 输出：
> ```lua
> luo
> 1 --> luo
> 2 --> 23
> 3 --> man
> ```

- 增加
    ```lua
-- 增加
    info[4] = "mm"
```

- 删除
    ```lua
-- 删除
    info[4] = nil
```

- 修改
    ```lua
-- 修改
    info[1] = "ll"
```

### 2.3 组合形式

```lua
Jinfo3 = {
    name = "tom",
    age = 113,
    sex = false,
    111,
    "222",
    { "abc", "def", 789, son_k_1 = "son-key-1" },
    son2 = { son2_k_1 = "son2- key-1", name = "son2", false, "abc-son2", 123456 },
    coutry = "china",
    3333
}

for k1, v1 in pairs(Jinfo3) do
    print(k1, "-->", v1)

    if type(v1) == "table" then
        for k2, v2 in ipairs(v1) do
            print("\t", k2, "-->", v2)
        end
    end
end
```

```lua
1       -->     111
2       -->     222
3       -->     table: 0x7fd9142081d0
                1       -->     abc
                2       -->     def
                3       -->     789
4       -->     3333
sex     -->     false
name    -->     tom
son2    -->     table: 0x7fd914208500
                1       -->     false
                2       -->     abc-son2
                3       -->     123456
age     -->     113
coutry  -->     china
```

> 可以看出先遍历数组形式，后遍历 Map 形式

> [!note] 注意遍历的函数时pairs，而不要轻易使用ipairs(这函数会只遍历数组形式，不会遍历 Map 形式的)


## 3. table API

> 📌 原笔记书签链接已丢失

- table.concat(list,sep,i,j) 
蒋数组中的元素拼接成一个字符串

- table.remove(list, pos)
删除数组中元素，默认删除最后一个

- table.insert(list, pos, value)
向指定位置插入元素，默认插入到最后

- table.sort(list, comp_function)
数组排序，默认从小到大，可自定义排序规则

- table.move(sourceTable, start, end, targetStart, [targetTable])
从sourceTable中复制元素到targetTable
- start从sourceTable的什么位置开始
- end 到sourceTable的什么位置结束
- targetStart 复制结果从targetTable的哪个位置开始赋值或增加

**排序**

**move复制**
