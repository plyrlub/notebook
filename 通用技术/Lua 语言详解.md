---
tags: [Lua, 脚本语言, 通用技术, 元表, 协程, 编程语言]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/通用技术）
归属: 01-学习/通用技术
---

# Lua 语言详解

> **版本基线**：Lua 5.4（`_G._VERSION` 实测输出 Lua 5.4），macOS 环境实测
> **受众声明**：面向已掌握任意一门编程语言（Java/Python/JS 均可）的开发者；假设你懂变量、函数、循环、面向对象等通用概念，本篇只讲 Lua 的独特之处（table 万能数据结构、元表、协程、环境隔离）
> **关联笔记**：[23-Lua执行阶段详解](Nginx/07-OpenResty与Lua插件/23-Lua执行阶段详解.md)（OpenResty 各阶段钩子）、[26-Lua插件实战](Nginx/07-OpenResty与Lua插件/26-Lua插件实战.md)（Nginx 场景的 Lua 实战）、Redis Lua 脚本（分布式锁/限流场景）

## 📋 总纲


1. 简介
2. 编程规范
3. 基本数据类型
4. 运算符
5. 流程控制
6. API
7. function
8. 可变参数
9. 元表 metatable 和元方法 metamethod
10. 面向对象
11. 协程Coroutines
12. 文件操作
13. 包管理
14. 操作三方资源
15. 环境变量和隔离


## 学习目标

学完这篇笔记，你能：

1. 独立安装 Lua 并用命令行/VSCode 跑通第一个脚本
2. 说出 Lua 8 种基本数据类型，以及「只有 nil/false 为假」的真值规则
3. 熟练使用 table 的 Map / 数组 / 组合三种形式，知道 pairs 与 ipairs 的遍历差异
4. 写出 Lua 的条件、循环（while/repeat/for）和 goto 跳转，避开死循环与作用域陷阱
5. 调用 table / string 标准库 API 完成拼接、排序、查找、替换
6. 理解并写出闭包、匿名函数、table 内嵌函数等灵活的 function 用法
7. 用 select / table.pack / table.unpack / {...} 处理可变参数
8. 用元表实现运算符重载、__index 继承、__newindex 代理、tostring/call 定制
9. 用元表 + self 冒号语法实现面向对象（继承/重写/私有化）
10. 用协程实现分段执行与主动让出，写出 fibonacci 协程
11. 用 io 库读写文件、用 require + package.path 做包管理、用 LuaRocks 装三方库（MySQL/Redis）
12. 用 _G / _ENV / load 做沙箱环境隔离，安全执行不可信代码

## 前置知识

- 本篇无前置，但建议先掌握任意一门编程语言的基础语法
- 关联阅读：[23-Lua执行阶段详解](Nginx/07-OpenResty与Lua插件/23-Lua执行阶段详解.md)（Lua 在 Nginx 网关的实战）

---



## 一、简介

> 📌 原笔记书签链接已丢失

### 1.1 介绍

Lua是一种轻量级的脚本语言，通常用于嵌入式系统和游戏开发中。它具有简单易学、高效快速、动态类型、轻量级、支持面向对象编程等特点。Lua语言由Yves Behar在1989年发明，并在1997年发布了第一个公开版本。

Lua是一种解释性语言，不需要编译，可以直接在程序运行时执行。它支持基本的数据类型如字符串、整数、浮点数、布尔值等，也支持列表、数组、字典等数据结构。Lua语言还支持函数定义和调用，以及条件语句、循环语句等基本控制结构。

Lua的主要特点包括：

- 轻量级：Lua的文件大小通常不到10KB，可以快速加载和执行。

- 动态类型：Lua的变量类型可以动态地改变，可以省去声明变量类型的时间。

- 解释性：Lua可以在程序运行时动态地解释和执行代码。

- 函数式编程：Lua支持函数作为参数和返回值，以及高阶函数。

- 嵌入式系统：Lua常用于嵌入式系统和游戏开发中，可以方便地嵌入到C或C++程序中。

总的来说，Lua是一种简单易学、高效快速、动态类型、轻量级、支持函数式编程的脚本语言，非常适合嵌入式系统和游戏开发。

### 1.2 应用场景

- 游戏开发

- 独立软件

- web开发、中间件

- 数据库操作脚本

- 缓存操作脚本

- 等

### 1.3 安装

> 📌 原笔记书签链接已丢失

然后检查

```
lua -v

lua 
> print("hello world")
> os.exit()
```

### 1.4 VSCode 配置开发环境

> 📌 原笔记书签链接已丢失

### 1.5 简单命令行

```
lua 简单命令行
```

## 二、编程规范

### 2.1 单行注释

```
-- 单行注释
```

### 2.2 多行注释

```
--**
  ......
**（见知识库）--
```

### 2.3 变量名命名

- 弱语言类型，定义变量名的时候不需要类型修饰
- 变量类型随时可修改，即赋值

- 每行代码后，有没有分号都可以

- 由数字、字母、下划线组成
- 不可以数字开头

- 不可以保留字

- 不可以特殊符号

- 不建议 下划线开头+字母大写

- 区分大小写

```
a = 124;
b = 123

a1 = 123
_a = 123
```

### 2.4 变量类型

- 全局变量
    ```
    a = 1
    ```

- 局部变量
    ```
    do
      local b = 1
    end
    ```

- 表字段

### 2.5 转义

和其他语言一样，

转义和原始输出案例：

```
local b = "a\rb\rc\td\te f\t **aa**（见知识库）";
print(b)

输出：
a
b
c       d               e f
c       d       e f      **aa**（见知识库）

local c = [=[a\rb\rc\td\te f\t **aa**（见知识库）]=];
print(c)

输出：
a\rb\rc\td\te f\t **aa**（见知识库）
```

即，需要原始输出需要使用

```
[=[

]=]
```

## 三、基本数据类型

There are eight basic types in Lua: nil, boolean, number, string, function, userdata, thread, and table.

库函数type() 返回一个描述给定值类型的字符串

- 其中 nil 类型只有一个值：nil

- string 类型，不管是单引号还是双引号，或者单字节或多字节

- userdata 是自定义数据格式

- thread 是协程

```
type(print)
> function

type({})
> table
```

> [!note] 在lua中，只有nil 和 false 才表示假，其他都直接表示真，包括0 或者 空串 也表示真

```
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

```
真
真
```

### 3.1 function

```
function的基本定义形式
```

```
结果
```

### 3.2 table 表

不是指数据库中的表，而是一种数据类型

#### 3.2.x Map 形式

类似于 Map，用k-v的方式来表现

理论上除了nil之外，其他类型都可以成为k

格式：

```
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

```
print(info.name)

for k, v in pairs(info) do
    print(k,'-->',v)
end
```

```
luo
name    -->     luo
sex     -->     man
age     -->     23
```

增加字段

```
info.id = 1;
info['country'] = 'china'
```

删除字段

```
info.id = nil
info['sex'] = nil
```

#### 3.2.x 数组形式

```
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

```
print(info[1])

for k, v in pairs(info) do
    print(k,'-->',v)
end
```

```
结果
```

- 增加
    ```
    -- 增加
    info[4] = "mm"
    ```

- 删除
    ```
    -- 删除
    info[4] = nil
    ```

- 修改
    ```
    -- 修改
    info[1] = "ll"
    ```

#### 3.2.x 组合形式

```
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

```
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

## 四、运算符

### 4.1 基础运算符

- 赋值 =
    ```
    a,b,c = 1,2,3
    ```
    交换
    ```
    a,b = 1,2
    print(a,b)
    a,b = b,a
    print(a,b)
    ```

- 算数运算符
- 加+

- 减-

- 乘*

- 除/

- 取模%

- 指数^

- 关系运算符
- 等于==

- 不等于~=

- 大于>

- 小于<

- 大于等于≥

- 小于等于≤

    引用类型比较，会比较引用地址，比如table 类型比较

- 其他符号
- 长度 #

    ```
    a = "abc"
    b = {1,2,3, cc=44, 55}
    
    print(#a)
    print(#b)
    
    > 3
    > 4
    ```
- 获取字符串长度

- 获取table中数组元素个数

### 4.2 逻辑运算符

在其他语言中，逻辑运算结果是bool类型，而lua中，返回值是参与计算的参数之一。

> Lua中逻辑运算符，有短路运算效果

- 与and
    ```
    a,b = 1,2
    print(a and b)
    
    b = false
    print(a and b)
    
    -- 并不是一定返回后面的值，只是有短路运算
    b = 3
    a = nil
    print(a and b)
    ```
    ```
    2
    false
    nil
    ```

- 或 or
    ```
    c,d = 1,nil
    print(c or d)  -- 1
    -- 因为 c 已经是true了，后续就没计算
    
    
    c,d = false, 2
    print(c or d)  -- 2
    -- 因为 c 是 逻辑假，会继续计算后续，2 为逻辑真，所以返回 2
    ```

- 非not
    ```
    e, f = nil, 1
    print(not e)  -- true
    
    print(not f)  -- false
    ```

简单案例，实现三目运算

```
local d,e,f = 1,2,3
local g = d < e and e or f  -- 2
local g = d > e and e or f  -- 3

print(g)
```

## 五、流程控制

### 5.1 if

```
if 条件 then
   计算
end
```

```
if 条件 then
   计算
else
   其他计算
end
```

```
if 条件 then
   计算
elseif 条件 then
   计算
else
   其他计算
end
```

### 5.2 while

```
while 条件 do
  计算
end
```

```
while 条件 do
  计算
  if 条件 then
    break
  end
end
```

> Lua中存在break，意思也是跳出一次循环。
> 但是没有continue.

### 5.3 repeat

```
repeat
  计算
until 条件
```

### 5.4 for

- 数值循环
    ```
    for i=1,10 do
      io.write(i, " ")
    end
    
    print()
    
    -- 倒序
    for i=10,1,-1 do
      io.write(i, " ")
    end
    
    print()
    -- 步进 为 2
    for i = 1, 10, 2 do
        io.write(i, " ")
    end
    ```
    ```
    结果
    ```

- 泛型循环
    ```
    for k,v in pairs(table) do
    
    end
    ```
- 迭代函数pairs

    ```
    local t1 = {1,2,0,a=4,5,b=nil,6,7,nil,8,9}
    
    for k, v in pairs(t1) do
        print(k,v)
    end
    ```
- 遇到元素值为nil，跳过继续下一个元素，但会占用下标位置。

- 混搭table，会优先输出数组元素

    ```
    1       1
    2       2
    3       0
    4       5
    5       6
    6       7
    8       8
    9       9
    a       4
    ```
- 迭代函数ipairs

    ```
    ipairs
    ```
- 遇到非数字 k，跳过

- 遇到第一个数组元素nil，直接终止，不是遇到值为nil

    ```
    1       1
    2       2
    3       0
    4       5
    5       6
    6       7
    ```
    观察所得，a=4跳过了，第一个b=nil那里没有终止，第二个nil的数组元素出现后终止

```
九九乘法表
```

### 5.5 break,goto

Lua 中循环中是存在break打断语句的，和其他语言一致，也是打断一层循环，进行跳出。

goto，跳转到指定标记除，也可以用于跳出循环。

```
while 条件 do
  计算
  if 条件 then
    break
  end
  
  if 条件 then
    goto FLAG;
  end
end

::FLAG::
```

```
一定要避免死循环
```

- goto 不能从代码块外部跳转到代码块内的标记位。

- goto不能在从外部跳入函数内，也不能从函数内直接跳出函数外

- goto不能跳转到 Local局部变量作用域内
    ```
    do
      a = 1
      :: flag::
      print(a)
      
      goto flag2  -- 这里不能直接跳转到后面局部变量作用域内
      local b = 2
      print(b)
      ::flag2::
    end
    ```

## 六、API

### 6.1 table API

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

```
排序
```

```
move复制
```

### 6.2 String API

> 📌 原笔记书签链接已丢失

- string.upper(str)

- string.lower(str)

- string.len(str)
- 中文按照UTF-8默认计算

- string.reverse(str)
翻转

- .. 字符串拼接
    ```
    local a = "123"
    print(a)
    local b = "123"..a
    print(b)
    local c = "123"..123 ..a.."abc"
    print(c)
    ```
- 正常左侧是字符串或变量，直接使用..进行连接即可拼接

- 左侧是数字，那么就需要空格+..进行连接即可拼接

local a = "123"
print(a)
local b = "123"..a
print(b)
local c = "123"..123 ..a.."abc"
print(c)

- string.sub(str,s)
- 位置数字可以是负数

- string.find(str, pattern, init, plain)
在字符串中查询pattern
- 如果找到了，就返回第一次出现的位置和结束位置。

- 默认返回匹配的开始和结束位置

- 如果正则内部有()分组，第三个结果是分组的结果

- 如果找不到，就返回nil

- init 从什么位置开始找，可以是正数，可以是负数

- plain
是否原始匹配

- 默认是false，即开始pattern的正则匹配，

- 如果是true，即原始匹配，直接匹配pattern的字符串，而不是正则

- string.gsub 替换

- string.char(0-255)码表字符，

- string.byte('abc', 1, 3) 字符转码

## 七、function

function的形式很灵活多样。

常见的就略。下面列一些不常见的。

```
函数作为参数直接传入--匿名函数
```

```
将函数直接作为整体对象返回
```

```
直接返回函数对象--闭包
```

```
闭包
```

### 7.1 table 中的function

```
t1 = {
    a1 = function(a, b)
      print(a, b)
    end
}

t1.a1(1, 2)
```

> 这里演示了table中内置function，以此来看；可以在table外添加字段的方式给table动态添加function.

```
t1 = {
    a = 20,
    b = 10,
    res = 0,
    add = function()
      t1.res = t1.a + t1.b
      return t1
    end,
    sub = function()
        t1.res = t1.a - t1.b
        return t1
    end,
    mult = function()
        t1.res = t1.a * t1.b
        return t1
    end,
    div = function()
        t1.res = t1.a / t1.b
        return t1
    end,
    p = function()
        print(t1.res)
    end
}

t1.add().p()
t1.sub().p()
t1.mult().p()
t1.div().p()
```

```
30
10
200
2.0
```

## 八、可变参数

```
function func(...)
end
```

### 8.1 select 函数

选取一个集合中元素列表。

可以用于不定长度的参数选择。

> [!note] select 函数返回值并不是table类型，而是应该返回的第一个元素的当前元素类型

```
function func(...)
    -- 获取参数个数
    print(select("#",...))
    -- 获取第一个参数以及后续参数
    print(select(1,...))
    -- 获取第5个参数以及后续参数
    print(select(5,...))

    print("----------------")
    -- 获取第5个参数的类型  -- 这里返回的是该不定参数位置的元素的元素类型，而不是table
    print(type(select(5,...)))
    -- 获取第5个参数  -- 注意这里的括号不能省略，多一个括号，即可提取select返回的该元素类型的第一个数据
    print((select(5,...)))
    -- 遍历所有参数 -- 利用select 加 括号 的特性
    for i=1,select("#",...) do
        local l = (select(i,...))
        print(l)
    end
    print("===================")
end

func(1,2,3,4,5,6,7,8,9,10)
func("a","b","c","d","e","f")
func(1,2,3, "a","b","c","d","e")
```

```
10
1       2       3       4       5       6       7       8       9       10
5       6       7       8       9       10
----------------
number
5
遍历部分略
===================
6
a       b       c       d       e       f
e       f
----------------
string
e
遍历部分略
===================
8
1       2       3       a       b       c       d       e
b       c       d       e
----------------
string
b
遍历部分略
===================
```

### 8.2 pack 处理可变参数

打包函数，将可变参数直接打包成为table使用，并在table内部增加一个n=len的参数表示可变参数的个数。

```
function func(...)
    local t0 = table.pack(...)
    -- 打印table
    print(t0)
    --  打印参数的个数
    print(t0.n)
    --  打印第一个参数
    print(t0[1])

    -- 打印pack函数打包后的所有打包参数，不包含新增的 n=len 参数
    io.write("{")
    for k, v in pairs(t0) do
        if k~="n" then
            io.write(k, ": ", v, ", ")
        else
            io.write(k, ": ", v, "")
        end
    end
    io.write("}")

    print()
    local sum = 0
    for i = 1, t0.n do
        sum = sum + t0[i]
    end
    print(sum)
end

func(1, 2, 3, 4, 5)
```

下面截图可观察到打包后的table内部。

> 📌 原笔记图片已丢失（wolai 源侧损坏）

```
table: 0x7fcf841073c0
5
1
{1: 1, 2: 2, 3: 3, 4: 4, 5: 5, n: 5}
15
```

### 8.3 unpack

pack是打包，unpack是解包。

table.unpack(list, i, j)

- 默认传入list即可，即将列表中所有元素解包返回。

- i 解包起始位置

- j 解包结束位置，不是解包元素数量。

其他略，活学活用

### 8.4 {...}

使用table括号直接打包，这样打包只包含可变数据，不会像table.pack一样增加n的元素。

```
function f(...) 
  t1 = {...}
end

-- t1打包后是： {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
```

## 九、元表 metatable 和元方法 metamethod

元表并不是一个普通的表，而是一套自定义的计算规则

而这些规则，可以实现表与表之间的运算

而这些规则，都已函数的形式，写在元表中，这些规则又称元方法

元表和元方法的表现可以理解为其他语言的重写(Override)。

> 📌 原笔记书签链接已丢失

### 9.1 运算符重写

> 比如：
> table与 table 之间没有 加法+ 操作，但是可以通过重新定义元方法 __add 来实现表与表之间的加法。
> 
> 其他类型元方法参考此方法和文档即可。

```
local t1 = {1,2,3,4,5,6,7,8,9}
local t2 = {11,22,33,44,55,66,77}

local meta_table = {}

setmetatable(t1, meta_table)
setmetatable(t2, meta_table)

meta_table.__add = function(a, b)
    local res = {}
    local aLen = #a
    local bLen = #b
    -- 取最大长度
    local maxLen = aLen > bLen and aLen or bLen

    for i = 1, maxLen do
        -- 相加, 不够用0补齐
        res[i] = (a[i] or 0) + (b[i] or 0)
    end
    return res
end

local t3 = t1 + t2
for i = 1, #t3 do
    io.write(t3[i], " ")
end

> 12 24 36 48 60 72 84 8 9
```

> 字符串和数字组合加法案例演示

```
local t1 = {1,2,3,4,5,6,7,8,9}
local t2 = {11,22,33,44,55,66,77, "a"}

local meta_table = {}

setmetatable(t1, meta_table)
setmetatable(t2, meta_table)

-- 判断元素中是否存在string类型的元素
local function containStr(t)
    for i = 1, #t do
        if type(t[i]) == "string" then
            return true
        end
    end
    return false
end

--  重载加法操作符
meta_table.__add = function(a, b)
    local res = {}
    local aLen = #a
    local bLen = #b
    -- 判断元素中是否存在string类型的元素设置标识
    local isString = containStr(a) or containStr(b)
    -- 取最大长度
    local maxLen = aLen > bLen and aLen or bLen

    for i = 1, maxLen do
        if isString then
            -- 拼接字符串, 不够用空字符串补齐
            res[i] = (a[i] and tostring(a[i]) or "")..(b[i] and tostring(b[i]) or "")
        else
            -- 相加, 不够用0补齐
            res[i] = (a[i] or 0) + (b[i] or 0)
        end
    end
    return res
end

local t3 = t1 + t2
for i = 1, #t3 do
    io.write(t3[i], " ")
end

> 111 222 333 444 555 666 777 8a 9
```

### 9.2 __index

```
local t1 = {id=1, name='zs'}

local meta_table = {}

-- 重载新索引操作符3  其实和第二种是一样的
-- local meta_table = { 
--    __index = {age=18}
--}

setmetatable(t1, meta_table)

--  重载索引操作符1
meta_table.__index = function(t, k)
    if k == "phone" then
        return 1234567890
    end
end

--  重载新索引操作符2
-- meta_table.__index = {age=18}

print(t1.id)
print(t1.name)
print("-----")
print(t1.age)
print(t1.phone)
print(t1['phone'])

> 1
> zs
> -----
> nil
> 1234567890
> 1234567890
```

- 重写索引的方法有两种，同时只能使用一种。

- 查询索引的顺序：
    查询表中索引字段
- 有key，返回值，

- 没有key，查询是否存在索引重写

- 没有重写，返回nil

- 有重写

- 如果重写的是一个表，查询是否存在对应key（例子中方式 2，3）

- 没有对应，则返回nil

- 有，则返回对应值

- 如果重写的是一个function，则调用，看是否存在对应key处理步骤（例子中方式 1）

- 没有对应，则最终返回nil

- 有对应，则按照步骤处理返回

#### 9.2.x 自索引

- 实现继承

```
local t1 = {id=1, name='zs'}
local t2 = {id=2}

-- 给t1 添加 self 方法
function t1:getName()
    print(self.name)
end

-- 添加自索引， 这样
t1.__index = t1
-- 将t2的元表设置为t1 -- 实现继承
setmetatable(t2, t1)

-- 这样就可以实现继承形式。即t2调用t1的方法了, 当然访问属性肯定可以
print(t2:getName())
```

> 经典的使用场景就是实现继承

- 实现链式继承

```
local grandfather = {id=1, name='zs'}

-- 这是一组代码， 实现了继承
grandfather.__index = grandfather
local father = {name='ls'}
setmetatable(father, grandfather)

-- 这是一组代码，实现了多重继承
father.__index = father
local son = {name='ww'}
setmetatable(son, father)

print(grandfather.id, father.id, son.id)
print(grandfather.name, father.name, son.name)

----
1       1       1
zs      ls      ww
```

```
多继承在方法上直接实现，方便后续调用
```

### 9.3 __newindex

#### 9.3.x 表类型

相当于两个表中间建立单向的增、删、改关系；具体看案例

```
local t1 = {id=1, name='zs'}
local t2 = {country='china'}

local meta_table = {}
setmetatable(t1, meta_table)

print(t1.phone)  -- nil
t1.phone = 1234567890
-- 重载newindex
-- t1本表已经存在的键值对，不会影响，但是不存在的键值对，后续操作，都会影响t2
meta_table.__newindex = t2
-- 重写newindex之后，再给t1中键值对修改，不会影响t1,t2
t1.name = 'ls'  -- 只修改t1的name

-- 重写newindex之后，再给t1增加键值对，会将新键值对，添加到t2中, 
-- 此时，t1中没有age这个键值对, 但是t2中存在age这个键值对
t1.age = 18

t1.age = 19  -- 修改t1, 其实会修改t2的age
print(t1.age)  -- 通过t1查询age, 查询不到，返回nil
print(t2.age)  -- 通过t2可以查询age
t2.age = 20  -- 通过t2可以修改age
-- t1.age = nil  -- 可以通过t1, 删除t2的age
-- t2.age = nil  -- 当然也可以通过t2, 删除t2的age

-- 遍历t1
print("--t1--")
for k, v in pairs(t1) do
    print(k, v)
end
-- 遍历t2
print("--t2--")
for k, v in pairs(t2) do
    print(k, v)
end
```

```
nil
nil
19
--t1--
id      1
name    ls
phone   1234567890
--t2--
country china
age     20
```

可以看到，当__newindex建立之前的t1表内已经存在的键值对，无论如何操作，都会只影响t1本身内部原来旧的键值对。不会影响t2

但是当__newindex建立之后，再对t1进行增加新的键值对，对被赋值到t2里面

- 通过t2可以完全控制该新的键值对

- 通过t1只能进行修改、删除该键值对操作，来影响t2内的该新键值对，不能进行查询操作。

> 元表 t2 就相当于是t1的副表
> 一个场景：当给t1进行修改属性操作的时候，不清楚哪些属性是以前存在的，哪些是后来增加的，就可以使用该方法
> 这样原来存在的属性直接修改，新的属性放到副表中查询，比对等操作。

#### 9.3.x function类型

```
local t1 = {id=1, name='zs'}

local meta_table = {}
setmetatable(t1, meta_table)

meta_table.__newindex = function (t, k, v)
    print("将原始操作的table直接传入: ", t==t1)
    print("进行了".. k.. " = ".. v.. "的操作, 但是没有进行赋值操作, 即表中到此没有这个键值对的添加")
    -- t[k] = v  -- 死循环， 该操作会触发调用newindex function
    rawset(t, k, v)  -- 调用原生方法，不会在内部第二次触发newindex function
end
-- 修改原有的键值对，不会触发newindex function
t1.name = 'ls'
-- 删除原有的键值对，不会触发newindex function
t1.id = nil
-- 给t1中添加新的键值对，会触发newindex function
t1.age = 18

-- 遍历t1
print("--t1--")
for k, v in pairs(t1) do
    print(k, v)
end
```

```
将原始操作的table直接传入:      true
进行了age = 18的操作, 但是没有进行赋值操作, 即表中到此没有这个键值对的添加
--t1--
name    ls
age     18
```

可以看到，当newindex的是一个function的时候，只会在赋值新键值对的时候触发，并传入三个参数：

- 本table

- 新的 key

- 新的value

> [!note] 这里注意，触发function并不代表添加键值对成功了，需要在function内部手动添加。但是不能使用传统的t[k]=v的形式添加，因为使用该操作，又会触发newindex function，这样就死循环了，会导致oom；所以需要使用rawset(t,k,v)，使用原生操作进行添加，这样就不会死循环了。

### 9.4 tostring

```
local t1 = {id=1, name='zs'}
local meta_table = {}
setmetatable(t1, meta_table)

-- 重写tostring方法
meta_table.__tostring = function (t)
    local str = ""
    for k, v in pairs(t) do
        str = str.. k.. " = ".. v.. ", "
    end
    return str
end

print(t1)

> phone = 1234567890, name = zs, id = 1,
```

### 9.5 call

类似增加构造函数

```
local t1 = {id=1, name='zs'}
local meta_table = {}
setmetatable(t1, meta_table)

-- 重写call方法
meta_table.__call = function (t,...)
    print("call方法被调用了")
    for k, v in pairs({...}) do
        t[k] = v
    end
end
-- 类似增加构造函数
t1(1,2,3,4,5)
print(t1)
```

### 9.6 rawget

取原始表中键值对，不走index

```
local t1 = {id=1, name='zs'}
local meta_table = {}
setmetatable(t1, meta_table)

print(t1.name)
print(t1.phone)

-- 重写index
meta_table.__index = function (t, k)
    if k == "phone" then
        return 1234567890
    end
end
print(t1.phone)

-- 取原始表的键值对，不触发index
print(rawget(t1, "phone"))
```

```
zs
nil
1234567890
nil
```

### 9.7 rawset

给原始表设置字段

案例

- 比如newindex表类型，使用该函数增加字段，就不会将新键值对添加到副本表中了。

- 比如newindex的function类型，就使用了该方法防止死循环

Lua-newindex-function

## 十、面向对象

### 10.1 self

```
local t1 = {id=1, name='zs'}

local t2 = t1

t1.getId = function()
    return t1.id
end

print(t1.getId())
print(t2.getId())

-- 使用self，使用冒号的方法，默认自动传入第一个参数为self，即调用者对象
function t1:getId2()
    return self.id
end

t1 = nil
-- 这里获取不到，因为t1已经为nil了，无法获取到id
-- print(t2.getId())

-- 使用self之后，就可以获取到id了
print(t2:getId2())
```

### 10.2 继承

详见

﻿自索引﻿

### 10.3 重写

子类内没有的属性会继承自父类，子类也可以自定义属性。

即子类可以有自己的属性值，或者自己的私有化属性

详见

﻿Lua代码块

### 10.4 成员私有化

之前的实例都是table，成员私有化最好使用function

```
成员私有化
```

## 十一、协程Coroutines

协程不是进程和线程，其执行过程更类似于子例程，或者说不带返回值的函数调用

多个线程相对独立，有自己的上下文，切换受系统控制

协程也是相对独立，也有自己的上下文，但是切换由自己控制

> [!note] 当前协程切换成其他协程由当前协程来控制

协程方法

> 📌 原笔记书签链接已丢失

- coroutine.close
关闭协程，返回bool

- coroutine.create
创建协程，传入一个 function，返回一个协程句柄

- coroutine.isyieldable
判断协程是否是yield状态

- coroutine.resume
将挂起态的协程重新唤醒

- coroutine.running
获取正在运行的协程

- coroutine.status
获取协程的状态
- suspended
挂起

- running
执行中

- dead
结束

- coroutine.wrap
用 function创建一个新的协程

- coroutine.yield
挂起当前协程，即主动让出当前协程执行权
- 可以理解为当前程序执行到这里被挂起。即将一段程序一分为二

- 当第一段程序执行结束之后，遇到这里，并将需要返回的值当参数传入，外部就会接受一阶段程序运行的结果

- 当外部再次唤醒程序后，该function，不会从头执行，只会从此处继续执行。

- 当再次唤醒传入的参数，会被该方法返回给二阶段程序接收使用

```
local function f(aa, bb)
    print('一阶段程序执行中...',aa, bb, os.time())
    -- 挂起协程, 将一阶段计算结果当做返回值传入作为参数，外部接收到的一阶段返回值就是括号内的参数
    -- 一阶段程序执行完成，等待被重新唤醒
    local x, y, z = coroutine.yield(aa*2, bb*3, os.time())
    -- x, y, z 是二阶段协程被唤醒后传入的参数
    print('二阶段程序执行中...', x, y, z)
    return 100, 200
end

-- 创建协程句柄
local co = coroutine.create(f)
print(1, coroutine.status(co))
-- 启动协程 -- 可以给方法传递参数
-- 返回值 1 表示是否执行成功， 2 3 4 5 6 表示返回值
local res, aa, bb, cc = coroutine.resume(co, 10, 20)
print('一阶段跳出: ', res, aa, bb, cc, coroutine.status(co))
-- 恢复协程执行
coroutine.resume(co, 'abc', 'cba', '二阶段')

-- 查询协程状态
print(3, coroutine.status(co))
```

```
1       suspended
一阶段程序执行中...     10      20      1733536960
一阶段跳出:     true    20      60      1733536960      suspended
二阶段程序执行中...     abc     cba     二阶段
3       dead
```

```
-- coroutine fibonacci
local function fibonacci(n)
    local a, b = 0, 1
    for i = 1, n do
        a, b = b, a + b
        io.write(a, ' ')
    end
    print()
    coroutine.yield(a)
end

local co = coroutine.create(fibonacci)
-- 启动协程
local status, res = coroutine.resume(co, 10)
print(status, res)

----
1 1 2 3 5 8 13 21 34 55 
true    55
```

## 十二、文件操作

> 📌 原笔记书签链接已丢失

- io.open(filename, mode)
- r
只读，文件必须存在

- w
只写，文件存在会清空内容，文件不存在则创建

- a
追加，文件存在则在最后添加数据，文件不存在则创建

- r+
读写，文件必须存在

- w+
读写，文件存在删除内容，文件不存在则创建

- a+
与a类似，但文件可读可写

- b
二进制

- +
修饰符，表示对文件既可以读，也可以写

- io.read()
- *n
读取一个数字

- *a
读取所有内容

- *l
默认值，读取下一行

- 123..
当前位置开始，读取几个字符

- file:read()
    ```
    ---| "n"  # 读取一个数字，根据 Lua 的转换文法返回浮点数或整数。
    ---| "a"  # 从当前位置开始读取整个文件。
    ---|>"l"  # 读取一行并忽略行结束标记。
    ---| "L"  # 读取一行并保留行结束标记。
    ```

- file:seek()
- 参数seekwhence

    ```
    ---@alias seekwhence
    ---| "set" # 基点为 0 （文件开头）。
    ---|>"cur" # 基点为当前位置。
    ---| "end" # 基点为文件尾。
    ```
- 参数offset
偏移量

```
local f1 = io.open('test001.txt', 'r')
local f2 = io.open('test002.txt', 'r')

print(f1 and f1:read() or "文件不存在")
print(f2 and f2:read() or "文件不存在")

if f1 then
    f1:seek('set')
    print(2, "-->"..f1:read())
end
```

## 十三、包管理

tools.lua

```
-- 模拟包管理器

helper = {}
helper.getIp = function()
    return "127.0.0.1";
end

utils = {
    getOs = function()
        return os.getenv("OS");
    end
}
```

其他lua

```
-- 引入tools 工具

require("tools")

-- 使用工具
print(helper.getIp())

-- 使用工具
print(utils.getOs())
```

> 如果其他 Lua 文件中有相同的方法会被覆盖。
> 所以可以使用下列方法其别名

```
local helper = {}
helper.getIp = function()
    return "127.0.0.1";
end

local utils = {
    getOs = function()
        return 'MacOS';
    end
}

-- 返回模块方法
return {helper=helper, utils=utils}
```

```
-- 返回包返回的内容，和包名
local tools, packageName = require("tools")

-- 使用工具
print(tools.helper.getIp())

-- 使用工具
print(tools.utils.getOs())

print(packageName)
```

> [!note] 还有一点，如果包在工作路径之外，需要使用package.path来指定寻找路径

```
package.path = package.path..";/temp/?.lua;"
package.path = package.path..";/temp/?.lua;"
```

## 十四、操作三方资源

这里设计三方库

> 📌 原笔记书签链接已丢失

LuaRocks is the package manager for Lua modules.

1. 安装rocks工具
    ```
    brew install luarocks
    -- 其他系统自行查询
    ```

1. 使用工具安装三方库
    ```
    luarocks install luasql-mysql
    ```

### 14.1 操作 MySQL

luasql

安装的时候可能会提示， 需要先安装mysql，并指定路径

```
You may have to install MYSQL in your system and/or pass MYSQL_DIR or MYSQL_INCDIR to the luarocks command.
Example: luarocks install luasql-mysql MYSQL_DIR=/usr/local
```

> [!note] 安装此三方库需要对应数据库

安装后就可以编写代码了

```
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

### 14.2 操作 Redis

需要先安装luasocket

然后将redis-lua源码下载下来，将src中的lua文件拿出来使用即可

```
local redis = require("redis")

local config = {host="127.0.0.1", port=6379}

local client = redis.connect(config)

-- info = client.info()
client:get("key")
client:del("key")
```

#### 14.2.x Redis内部跑lua

这是比较常见的一个场景，比如分布式锁，限流等场景

## 十五、环境变量和隔离

比如有一个str接收到前端传入，直接执行。

```
str = "print(123);os.remove('a.txt');"
```

前端传入的代码是不可信的，非常危险。

所以在执行之前，需要将代码放入沙箱执行。而沙箱内部的设置（比如移除部分标准库的执行，或者指定只能执行哪些操作）不能影响外部的代码使用。这里涉及到全局环境变量。

### 15.1 全局环境变量

在标准库中，_G是所有可见的鼻祖表，即所有的标准库默认存放在该表中，如果对该表进行操作，会影响后续整个代码运行。

看看_G中有哪些东西。

```
-- 全局环境变量
for k,v in pairs(_G) do
    print(k, '-->', v)
end
```

```
rawequal  -->  function: 0x10fdb1931
tonumber  -->  function: 0x10fdb1baa
rawset  -->  function: 0x10fdb1a19
load  -->  function: 0x10fdb158d
string  -->  table: 0x60000292c640
rawget  -->  function: 0x10fdb19ce
package  -->  table: 0x60000292c3c0
tostring  -->  function: 0x10fdb1dc0
coroutine  -->  table: 0x60000292c4c0
xpcall  -->  function: 0x10fdb1e40
setmetatable  -->  function: 0x10fdb1b11
io  -->  table: 0x60000292c540
error  -->  function: 0x10fdb1418
arg  -->  table: 0x60000292c7c0
getmetatable  -->  function: 0x10fdb1489
ipairs  -->  function: 0x10fdb14d7
assert  -->  function: 0x10fdb1145
dofile  -->  function: 0x10fdb13ac
select  -->  function: 0x10fdb1a71
warn  -->  function: 0x10fdb1885
collectgarbage  -->  function: 0x10fdb11c0
next  -->  function: 0x10fdb1679
os  -->  table: 0x60000292c600
print  -->  function: 0x10fdb17bb
require  -->  function: 0x60000322c480
loadfile  -->  function: 0x10fdb151e
rawlen  -->  function: 0x10fdb1979
pcall  -->  function: 0x10fdb1753
math  -->  table: 0x60000292c6c0
type  -->  function: 0x10fdb1dee
utf8  -->  table: 0x60000292c740
debug  -->  table: 0x60000292c780
pairs  -->  function: 0x10fdb16cc
_G  -->  table: 0x60000292c240
_VERSION  -->  Lua 5.4
table  -->  table: 0x60000292c500
```

如果直接对_G操作会导致影响其他后续操作。

```
print(os.time())
_G.os = nil
print(os.time())
```

```
1734323227
/usr/local/bin/lua: base031.lua:10: attempt to index a nil value (global 'os')
stack traceback: base031.lua:10: in main chunk [C]: in ?
```

### 15.2 环境隔离

使用预加载函数内部限制，或者规则变量_ENV来在函数内进行设置，使得函数内设置之后的操作受影响，而不会影响前面和函数外；从而达到环境隔离的效果。

```
str = "print('hello world');os.remove('a.txt')"

-- 环境隔离
function func1(code)
    -- 将传入的代码编译成函数, 即预加载
    -- 第一个参数是代码, 第二个参数是代码有误返回的 msg, 第三个参数是编译模式(二进制或文本), 第四个参数是环境变量(这里指定只能使用 print 函数)
    local res, msg = load(code, "传入代码有误", "bt", { print = print })
    if res then
        return pcall(res)
    else
        return msg
    end
end

function func2(code)
    print(os.time())
    -- 直接通过_ENV 来限制函数内部后续处理的环境变量， 5.4 版本使用
    --  setfenv(1, {os=nil}) 5.1 使用，现在已经废弃
    local _ENV = {print = _G.print, load = _G.load, pcall = _G.pcall}
    local res, msg = load(code, "传入代码有误", "bt")
    if res then
        return pcall(res)
    else
        return msg
    end
end

-- func1(str)
-- func2(str)
```

> [!note] 可以看到，这里最新的限制，都使用了白名单方式，而不是黑名单方式。
> 白名单限制会更加严格



---

## 最佳实践

1. **变量默认全局，慎用**：Lua 里 `a = 1` 是全局变量，函数内赋值前一定要 `local`，否则污染 _G 且难以排查
2. **table 是唯一复合结构**：数组/Map/对象都用 table，记住「数组部分 + Map 部分」混搭时的遍历顺序（先数组后 Map）
3. **遍历优先 pairs**：ipairs 遇到第一个 nil 就停，混搭 table 会漏 Map 部分；需要数字下标顺序遍历时用 `for i=1,#t`
4. **`#` 长度运算符只对数组部分可靠**：`#{1,2,3,cc=44,55}` 返回 4（只数数组元素），不要对 Map 用 `#`
5. **字符串拼接用 `..`**：左侧是数字时必须加空格（`"123"..123`），Lua 没有 `+` 拼接
6. **元表运算小心死循环**：`__newindex` 函数内用 `rawset(t,k,v)` 而不是 `t[k]=v`，否则无限递归 OOM
7. **执行不可信代码必须沙箱**：用 `load(code, ..., {白名单})` + `_ENV` 限制，永远用白名单而非黑名单
8. **协程是协作式**：切换由当前协程主动 yield 控制，不是抢占式，别当线程用

## 常见踩坑

- `for i=1,10` 的步进默认 1，倒序必须写 `-1`（`for i=10,1,-1`）
- `table.unpack` 的第三个参数是结束位置（下标），不是解包元素数量
- `select(5,...)` 返回的是「第 5 个参数及其后所有参数」，想取单个值要加括号 `(select(5,...))`
- `string.sub` 位置可以是负数；`string.len` 中文按 UTF-8 字节数算
- `goto` 不能跳进局部变量作用域、不能从外部跳进代码块/函数
- `package.path` 拼接用 `..`（`package.path = package.path..";/temp/?.lua;"`），不是 `+`
- `io.open` 的 `r` 模式文件必须存在，`w` 会清空内容
- Lua 5.1 的 `setfenv` 已废弃，5.4 用 `_ENV` 做环境隔离

## 小结

Lua 是一门轻量级嵌入式脚本语言（核心解释器 < 10KB），用**一个 table 打天下**：数组、Map、对象、模块都是它。它的进阶精髓在三块——**元表**（运算符重载与继承）、**协程**（协作式分段执行）、**环境隔离**（沙箱安全执行）。掌握这三块 + table/string 标准库，就掌握了 Lua 的 80%。

## 下一篇

- [23-Lua执行阶段详解](Nginx/07-OpenResty与Lua插件/23-Lua执行阶段详解.md)：OpenResty 各阶段钩子（init/rewrite/access/content/log_by_lua）
- [26-Lua插件实战](Nginx/07-OpenResty与Lua插件/26-Lua插件实战.md)：Lua 在 Nginx 网关的实战（限流、鉴权、动态路由）
