---
tags: [Java, Arthas, 诊断, 调优, 在线排查]
创建日期: 2026-08-07
状态: ✅ 已归档（01-学习/Java/JVM）
归属: 01-学习/Java/JVM
---

# Arthas在线诊断（安装 / 核心命令 / 实战场景）

## 📋 总纲

1. Arthas 是什么：与 JDK 自带工具的本质区别
2. 安装与启动（本机已装 4.3.2，附实测 attach 方式、文件清单、服务器离线部署最小集、agent 生命周期、标准操作流程）
3. 核心命令逐个讲：dashboard / thread / trace / watch / jad / sc / memory / jvm / sysprop / stack / monitor / ognl / redefine（含本机实测输出）
4. Web 控制台（tunnel-server）：浏览器里用 Arthas + 端口排查
5. 典型场景实战：CPU 高、方法慢、看实现、查参数
6. 与 jstack / jstat 等 JDK 工具对比
7. 易错点清单
8. 面试追问 Q&A
9. 📌 原理篇：[Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)（插帧/插桩原理）
10. 附录：FastDemo 高频调用测试靶子

---

## 1. Arthas 是什么

**Arthas（阿尔萨斯）**：阿里巴巴开源的 **Java 在线诊断工具**——不重启应用，直接 attach 到运行中的 JVM 上做"活体解剖"。

### 1.1 与 JDK 自带工具的本质区别

| 维度 | JDK 工具（jstack/jmap/jstat） | Arthas |
|---|---|---|
| 方式 | **快照式**：dump 下来离线看 | **活体式**：attach 上去实时观测 |
| 反编译 | ❌ | ✅ jad 直接看线上类源码 |
| 方法级追踪 | ❌ 只能看线程栈 | ✅ trace 看方法内部每行耗时 |
| 参数观测 | ❌ | ✅ watch 看入参/返回值/异常 |
| 热更新 | ❌ | ✅ redefine 运行时替换 class |
| 对进程影响 | jmap -dump 会 STW | attach 后按命令开销，用完 stop |

### 1.2 核心能力一句话

a. **看**：dashboard 总览、jad 反编译、sc 搜类
b. **查**：thread 线程、trace 调用链、watch 参数
c. **改**：redefine 热更新（慎用）

---

## 2. 安装与启动

### 2.1 本机已装（2026-08-07 实测）

```bash
# 本地文件位置：
#   /Users/lub/Desktop/本地环境/tools/arthas-bin/          ← arthas 4.3.2 完整发行版
#   /Users/lub/Desktop/本地环境/tools/arthas-tunnel-server-4.3.2-fatjar.jar  ← Web 控制台（tunnel server）
```

- 版本：**4.3.2**（`unzip -p arthas-boot.jar META-INF/MANIFEST.MF` 可查 Implementation-Version）
- 若还没下载，联网装法：

```bash
# 方式一：官方（国内可访问）
curl -O https://arthas.aliyun.com/arthas-boot.jar
java -jar arthas-boot.jar

# 方式二：gitee 镜像（更快）
curl -O https://gitee.com/arthas/arthas-boot/raw/master/arthas-boot.jar
java -jar arthas-boot.jar
```

### 2.2 启动并 attach 目标进程（本机实测）

```bash
# 交互式选择 PID（列出所有 Java 进程，输入序号）
java -jar arthas-boot.jar

# 直接指定 PID 进入交互式命令行
java -jar arthas-boot.jar 32039

# 非交互模式：-c 直接执行一条命令后退出（批量脚本/自动化友好）
java -jar arthas-boot.jar -c 'dashboard -n 1' 32039        # 只刷一帧 dashboard
java -jar arthas-boot.jar -c 'thread -n 3; sysprop user.home' 32039   # 分号连多条
java -jar arthas-boot.jar --width 180 -c 'memory' 32039    # 加宽终端防输出截断
```

> ⚠️ **macOS 实测坑**：`as.sh` 脚本依赖 `telnet`（macOS 默认没装，会报 `telnet is not installed`），本机直接用 `java -jar arthas-boot.jar` 即可，走的是 TCP 通道，不需要 telnet 命令。

> ⚠️ **attach 会注入 agent**：首次 attach 会在目标 JVM 里注入 arthas agent（本机 IDEA 32039 注入后 `jcmd 32039 Thread.print` 里能看到 100+ 个 arthas 相关线程，正常现象）。**同一进程重复 attach 是复用已有 agent 实例，不会重复注入**（实测连续多次 `-c` 执行，IDEA 里只有一个 agent）。

### 2.3 文件清单（每个文件干什么，实测确认）

本机发行版 `/Users/lub/Desktop/本地环境/tools/arthas-bin/` 各文件角色：

| 文件 | 大小 | 作用 | 服务器必带？ |
|---|---|---|---|
| **arthas-boot.jar** | 147KB | 启动器：attach 目标 JVM + 拉起客户端，日常入口 | ✅ 必需 |
| **arthas-core.jar** | 17MB | 核心引擎：注入目标 JVM 的 agent 本体（体积大头） | ✅ 必需 |
| **arthas-agent.jar** | 8.5KB | agent 引导：attach 时注入的入口 | ✅ 必需 |
| **arthas-spy.jar** | 5.8KB | 字节码增强埋点（watch/trace 的探针） | ✅ 必需 |
| **arthas-client.jar** | 437KB | 客户端 TelnetConsole（-c 非交互模式就是它） | ✅ 必需 |
| lib/libArthasJniLibrary-*.so/dylib/dll | ~45-105KB | **vmtool 命令专用**的 JNI 原生库（实例枚举/算大小/强制 GC） | ⭕ 按平台选 1 个 |
| async-profiler/ | ~600KB×3 | **profiler 命令专用**（火焰图），分 mac/linux-x64/linux-arm64 | ⭕ 要用火焰图才带 |
| arthas.properties | 791B | agent 默认配置（telnet/http 端口、session 超时等） | ⭕ 推荐带 |
| logback.xml | 2KB | 日志配置 | ⭕ 推荐带 |
| as.sh | 34KB | Linux/macOS 启动脚本（**依赖 telnet/curl/unzip**） | ⭕ 有 telnet 才用 |
| as.bat / as-service.bat | — | Windows 启动脚本 | ❌ 服务器不用 |
| install-local.sh | 635B | 把 jar 拷到 ~/.arthas 的本地安装脚本 | ⭕ 可选 |
| math-game.jar | 4.4KB | 官方演示程序（实测靶子） | ❌ 不需要 |

> **实测结论**：最小可运行集 = 5 个 jar（boot/core/agent/spy/client）+ 对应平台的 JNI 库 + arthas.properties + logback.xml。**完全离线可用，不会联网下载**——前提是 attach 时用 `--arthas-home` 指到本地目录（见 2.4）。

### 2.4 上传服务器部署（离线最小集，实测验证）

```bash
# 服务器是 Linux x64 的话，只需拷这些（约 18MB）：
#   arthas-boot.jar  arthas-core.jar  arthas-agent.jar  arthas-spy.jar  arthas-client.jar
#   arthas.properties  logback.xml
#   lib/libArthasJniLibrary-x64.so        ← Linux x64 选这个
#   （Windows 选 -x64.dll，macOS 选 .dylib，ARM Linux 选 -aarch64.so，32位ARM选 -arm.so）

# 服务器上用法一：--arthas-home 指到解压目录（离线关键！）
java -jar arthas-boot.jar --arthas-home /opt/arthas <pid>

# 用法二：交互式选择进程
java -jar arthas-boot.jar --arthas-home /opt/arthas

# 用法三：非交互批量（脚本化）
java -jar arthas-boot.jar --arthas-home /opt/arthas -c 'thread -n 3; memory' <pid>
```

> ⚠️ **实测踩坑**：
> - **`--arthas-home` 必须指定**：不指定时 boot 会去 `~/.arthas/lib/` 找缓存，找不到就**联网下载**——服务器离线直接卡死/失败。拷过去的目录必须带完整的 5 个 jar，缺 arthas-client.jar 会报 `ClassNotFoundException: com.taobao.arthas.client.TelnetConsole`（实测）
> - **JNI 库按平台选**：拷错平台（如 mac 的 .dylib 拿到 Linux）vmtool 报 `no ArthasJniLibrary in java.library.path`；但 **thread/trace/watch/monitor/sc/jad/ognl 等主要命令不需要 JNI 库**，只有 vmtool 要（实测去掉 JNI 库后 thread/trace 照常工作）
> - **profiler 命令要 async-profiler 目录**：没带报 `AsyncProfiler error: Can not find libasyncProfiler so`（实测）
> - as.sh 在服务器上可用，但依赖 telnet/curl/unzip（Linux 一般自带 telnet，macOS 没有）；不想装依赖就统一用 `java -jar arthas-boot.jar`

### 2.5 as.sh 与 arthas-boot 的加载机制（源码确认）

**as.sh 不是安装器,而是"引导器 + 按需下载器"**。它启动时的定位顺序(源码 main 函数 1060-1077 行):

1. 检查 as.sh **自身所在目录**是否存在 arthas-core.jar + arthas-agent.jar + arthas-spy.jar——三者齐全直接使用本地文件,不发起任何网络请求
2. 本地缺失 → 通过 `curl https://arthas.aliyun.com/api/latest_version` 获取远程最新版本
3. 本地 `~/.arthas/lib/` 无该版本或版本较旧 → 自动下载 `arthas-<version>-bin.zip` 并解压至 `~/.arthas/lib/<version>/arthas/`

由此导出两种部署方式:
- **仅拷贝 as.sh 单文件**:执行时自动下载完整发行包,适合可联网的一键安装
- **拷贝完整目录**(as.sh + 5 个 jar):全部使用本地文件,零网络请求,适合离线服务器

**as.sh 的依赖约束**:启动时强制检查 curl / grep / awk / telnet / unzip 五个外部命令(源码 188-208 行),任一缺失即报错退出;同时自动探测 JAVA_HOME,JDK 8 及以下还要求存在 tools.jar。因此服务器上若无 telnet,应改用 `java -jar arthas-boot.jar`(不依赖这些外部命令,见 2.4)。

**arthas-boot.jar 与核心的关系**:boot 始终是引导器(147KB),核心逻辑一直位于 arthas-core.jar(17MB),二者从未合并过。旧版单独执行 boot.jar 即可运行,是因为引导器启动时自动从远程仓库下载核心组件;新版新增 `--arthas-home` 参数,可显式指向本地核心目录,实现完全离线运行。变化的只是"壳去哪里找核心":联网、本地缓存、还是同目录。

### 2.6 退出

```bash
quit      # 退出 Arthas（目标 JVM 不受影响，继续正常运行）
stop      # 关闭 Arthas 服务端（完全卸载字节码增强）
```

> 注意：`quit` 只是退出客户端，增强还在；`stop` 才完全还原。生产上用完建议 stop。

### 2.7 agent 生命周期（boot / agent / client 三角色）

**核心铁律：agent 注入即驻留，只有两种方式退出——① 目标 JVM 关闭 ② client 执行 stop**。客户端怎么退出都不影响 agent。

| 角色 | 类比 | 生命周期 | 退出方式 |
|---|---|---|---|
| boot（启动器） | 安装师傅 | 注入完就走 | 一次性 |
| agent（代理服务） | 监控摄像头 | 驻留目标 JVM | JVM 关 / client stop |
| client（连接器） | 手机监控 App | 随时连随时断 | 随时 q |

推论：
- `q` / `Ctrl+C` 只退客户端，agent 和字节码增强都还在
- boot 异常退出（终端关闭/被杀）不影响 agent，之后用 client 直接连还能继续用
- 同一进程重复 attach 是复用已有 agent，不是重复注入

### 2.8 标准操作流程（从零开始，照抄即可）

> 完整流程：查进程 → 查 agent 端口 → 连接 → 使用 → 收尾。每步命令可直接复制，替换 `<pid>` 即可。

```bash
# ① 查 Java 进程（拿到目标 PID）
jps -l
# 或 ps aux | grep java

# ② 查目标进程是否已有 agent（关键！避免踩"旧 agent 复用"坑）
lsof -nP -p <pid> | grep LISTEN
# 有输出（3658/8563 或自定义端口）= 已有 agent 驻留
# 无输出 = 干净进程，可直接 attach

# ③ 若有旧 agent 且想重来：停掉它（注意：连 telnet 端口，不是 http）
grep -E "bind telnet|bind http" ~/logs/arthas/arthas.log | tail   # 找 telnet 端口（唯一铁证）
java -jar arthas-client.jar 127.0.0.1 <telnet端口> -c "stop"      # 停旧 agent

# ④ 全新 attach（普通场景）
java -jar arthas-boot.jar <pid>

# ④' 全新 attach（离线/指定 arthas 目录）
java -jar arthas-boot.jar --arthas-home /path/to/arthas <pid>

# ④'' 全新 attach（注册到 Web 控制台 tunnel）
java -jar arthas-boot.jar --tunnel-server 'ws://127.0.0.1:7777/ws' \
     --agent-id my-agent-001 --app-name myapp --attach-only <pid>

# ⑤ 非交互执行单条命令（脚本化/自动化）
java -jar arthas-boot.jar -c 'thread -n 3; memory' <pid>
java -jar arthas-client.jar 127.0.0.1 3658 -c 'dashboard -n 1'   # 已有 agent 时直连

# ⑥ 交互使用（进入命令行后）
#   dashboard / thread -n 3 / trace ... / watch ... / jad ... / sc ...
#   用 q 退出客户端

# ⑦ 收尾（生产必做）：彻底卸载 agent
java -jar arthas-client.jar 127.0.0.1 <telnet端口> -c "stop"
```

> ⚠️ 端口速查：telnet 端口（client 连这个）= 默认 3658；http 端口（浏览器用）= 默认 8563。两者都可能被 `--telnet-port` / `--http-port` 改过，甚至 `-1` 禁用。区分方法见 4.3 节。

---

## 3. 核心命令逐个讲

### 3.1 dashboard（实时总览）

```bash
dashboard                 # 每 5 秒刷新
dashboard -n 1            # 只刷一帧就退出（非交互模式用）
```

**本机实测**（attach IDEA 32039，JBR 25.0.3，Arthas 4.3.2，2026-08-07）：

```
ID NAME                GROUP     PRIORI STATE  %CPU  DELTA_ TIME   INTER DAEMON
-1 C2 CompilerThread0  -         -1     -      0.0   0.000  1:52.1 false true
-1 C1 CompilerThread0  -         -1     -      0.0   0.000  0:23.2 false true
13 DefaultDispatcher-w main      5       TIMED_ 0.0   0.000  0:12.5 false true
68 AWT-EventQueue-0    main      6       WAITIN 0.0   0.000  0:10.8 false false


Memory           used  total max usage GC
heap             549M  645M             gc.g1_young_generat 111
g1_eden_space    262M  322M  -1         ion.count
g1_old_gen       275M  310M             gc.g1_young_generat 1862
                 12M   13M   -1         ion.time(ms)
nonheap          495M  535M  -1         gc.g1_concurrent_gc 74


Runtime
os.name                                 Mac OS X
os.version                              15.7.3
java.version                            25.0.3
```

| 看什么 | 怎么读 |
|---|---|
| CPU 占用 TOP 线程 | 哪个线程吃 CPU 一目了然（替代 top -Hp + jstack 三板斧） |
| 内存区 | heap / non-heap / 各代使用率 |
| GC 次数与耗时 | 快速判断 GC 是否异常（G1 收集器显示 g1_young_generation / g1_concurrent_gc） |

> 实测解读：IDEA 空放时 heap 549M/645M、Metaspace 属于 nonheap（495M）大头，C2/C1 编译线程和 AWT 事件线程都在——IDE 类应用特征。dashboard 输出会自动随终端宽度换行，`--width 180` 可避免换行错位。

### 3.2 thread（线程排查，比 jstack 强）

```bash
thread -n 3              # 按 CPU 占用排序，看最忙的 3 个线程（不用转十六进制！）
thread -b                # 找阻塞线程（死锁检测，等价 jstack 里的 deadlock 段）
thread <id>              # 看指定线程的完整栈
thread --state WAITING   # 按状态过滤
```

**本机实测**（IDEA 空闲态，`thread -n 3`）：

```
"arthas-command-execute" Id=1366 cpuUsage=0.06% deltaTime=2ms time=8ms RUNNABLE
    at sun.management.ThreadImpl.dumpThreads0(Native Method)
    at com.taobao.arthas.core.command.monitor200.ThreadCommand.processTopBusyThreads(ThreadCommand.java:206)
    ...
"DefaultDispatcher-worker-8" Id=41 cpuUsage=0.03% deltaTime=1ms time=8311ms RUNNABLE
    at jdk.internal.misc.Unsafe.park(Native Method)
    at java.util.concurrent.locks.LockSupport.parkNanos(LockSupport.java:408)
    at kotlinx.coroutines.scheduling.CoroutineScheduler$Worker.runWorker(CoroutineScheduler.kt:797)
"DefaultDispatcher-worker-40" Id=197 cpuUsage=0.03% deltaTime=0ms time=8793ms RUNNABLE
    at kotlinx.coroutines.scheduling.CoroutineScheduler$Worker.run(CoroutineScheduler.kt:762)
```

`thread -b` 实测：空闲 JVM 输出 `No most blocking thread found!`（没有死锁，正常）。

> 实测解读：空闲 IDEA 没有忙线程，`-n 3` 排出来的都是 Kotlin 协程调度线程（`DefaultDispatcher-worker-*`）在 park 等待——这是 IDEA 2024+ 内部用协程的痕迹，CPU 都是 0.03% 级别，属正常。排第一的是 Arthas 自己的命令执行线程（正在执行本次 thread 命令），不用管。

**对比 jstack 的优势**：jstack 要 top -Hp 找线程号 → 转十六进制 → grep；Arthas 一个 `thread -n 3` 直接给结果。

### 3.3 trace（方法内部耗时追踪，Arthas 招牌）

```bash
trace demo.MathGame run -n 2        # 追踪方法, -n 2: 只抓 2 次就退出
trace com.example.OrderService createOrder '#cost > 100'   # 只显示耗时 > 100ms 的
```

**本机实测**（官方演示程序 math-game.jar，`trace demo.MathGame run -n 2`）：

```
`---ts=2026-08-07 16:20:45.446;thread_name=main;id=1;is_daemon=false;priority=5
    `---[0.32337ms] demo.MathGame:run()
        +---[13.29% 0.042979ms ] demo.MathGame:primeFactors() #24
        `---[39.55% 0.127882ms ] demo.MathGame:print() #25
```

> 实测解读：输出是**方法内部调用树**——run() 调了 primeFactors()（#24 是源码行号）和 print()（#25），括号里是每层耗时与占比，一眼看出瓶颈在哪一段。**这个命令有探针开销**（在目标方法里插桩），所以用 `-n` 限制抓取次数，测完就停，别挂着刷。对高频方法长期开着会明显拖慢应用。

**用途**：接口慢，一把揪出是 DB / 远程调用 / 本地计算哪一段。

### 3.4 watch（观测方法参数 / 返回值 / 异常）

```bash
watch demo.MathGame primeFactors '{params, returnObj}' -n 2   # -n 2: 抓 2 次退出
watch com.example.OrderService createOrder '{params, returnObj}' -x 2
# params: 入参列表, returnObj: 返回值, -x 2: 展开深度 2 层
watch com.example.OrderService createOrder '{params[0].userId}'   # 只看第一个参数
watch com.example.OrderService createOrder 'throwExp'             # 只看抛的异常
```

**本机实测**（math-game.jar，`watch demo.MathGame primeFactors "{params, returnObj}" -n 2`）：

```
method=demo.MathGame.primeFactors location=AtExit
ts=2026-08-07 16:20:50.501; [cost=0.049311ms] result=@ArrayList[
    @Object[][isEmpty=false;size=1],
    @ArrayList[isEmpty=false;size=8],
]
method=demo.MathGame.primeFactors location=AtExceptionExit
ts=2026-08-07 16:20:51.506; [cost=0.139229ms] result=@ArrayList[
    @Object[][isEmpty=false;size=1],
    null,
]
```

> 实测解读：watch 在**每次调用**时输出——`location=AtExit` 是正常返回（第二个元素是返回值，8 个质因数），`location=AtExceptionExit` 是抛异常路径（返回值是 null）——异常现场也能抓到，不用加日志重新发版。同样建议 `-n` 限次数。

**用途**：线上参数传错、返回值异常、抛了什么异常——不用加日志重新发版。

### 3.5 jad（反编译线上类）

```bash
jad com.example.OrderService          # 反编译整个类
jad --source-only com.example.OrderService   # 只输出源码（不含反编译头）
jad com.example.OrderService createOrder     # 只看某个方法
```

**本机实测**（反编译 IDEA 主类 `com.intellij.idea.Main`，`jad --source-only`）：

```java
/*
 * Decompiled with CFR.
 */
package com.intellij.idea;

import com.intellij.concurrency.IdeaForkJoinWorkerThreadFactory;
import com.intellij.diagnostic.Activity;
...
import java.lang.invoke.MethodHandle;
import java.util.ArrayList;
```

> 实测解读：CFR 反编译，输出就是可读 Java 源码——连 JBR 25 上跑的 IDEA 2026 主类都能完整反编译。注意 `jad` 默认输出带 `/* Decompiled with CFR. */` 头，`--source-only` 仍有包名+import，`--lineNumberFormat` 可自定义行号格式；排查"线上代码和本地不一致"直接对比即可。

### 3.6 sc（搜索类 / 类信息）

```bash
sc com.example.*                      # 按模式搜类
sc -d com.example.OrderService        # 详细：类加载器、注解、方法签名
sc -d com.example.OrderService | head -30
```

**本机实测**（`sc -d com.intellij.idea.Main`）：

```
 class-info        com.intellij.idea.Main
 code-source
 name              com.intellij.idea.Main
 isInterface       false
 ...
 modifier          final,public
 annotation        kotlin.Metadata
 super-class       +-java.lang.Object
 class-loader      +-com.intellij.util.lang.PathClassLoader@24d46ca6
                     +-jdk.internal.loader.ClassLoaders$PlatformClassLoader@6dfa39f0
 classLoaderHash   24d46ca6
Affect(row-cnt:1) cost in 221 ms.
```

> 实测解读：`-d` 输出类加载器链（IDEA 用自研 PathClassLoader 加载主类，父加载器是 PlatformClassLoader）——这就是排查"类从哪个 jar 来、谁加载的"最直接证据。`Affect(row-cnt:1) cost in 221 ms` 是匹配行数与耗时。

### 3.7 memory（内存总览，4.x 替代旧 gc 命令）

```bash
memory     # 堆 + 非堆各区域 used/total/max/usage
```

**本机实测**（IDEA 32039，`memory`）：

```
Memory                used       total      max      usage
heap                  558M       645M       1024M    54.58%
g1_eden_space         271M       322M       -1       84.16%
g1_old_gen            275M       310M       1024M    26.86%
g1_survivor_space     12M        13M        -1       98.91%
nonheap               495M       535M       -1       92.52%
metaspace             407M       414M       -1       98.32%
compressed_class_space 56M       58M        1024M    5.48%
codeheap_'profiled_nmethods'   16M  46M     253M     6.59%
mapped                3429M      3429M      -        100.00%
direct                273M       273M       -        100.00%
```

> ⚠️ **版本差异（4.x 实测）**：`gc` 命令在 Arthas 4.x 已移除，报 `gc: command not found`——看 GC 统计用 `memory`（有 g1_young_generation count/time）。另外 `-Xmx` 在 IDEA 这类 JBR 上有 SoftMaxHeapSize 动态堆机制（详见 [JVM调优实战](JVM调优实战.md)），`max` 列 1024M 与 `jps -v` 的 -Xmx2048m 不一致是正常的。

> 实测解读：IDEA 空放 heap 558M/1024M，Metaspace 407M 占比高（IDE 加载海量类的特征）；mapped 3429M 是 IDEA 的 memory-mapped 缓存（代码索引/文件缓存），direct 273M 是堆外直接内存——IDE 类应用这两个非堆大头都正常。

### 3.8 jvm（JVM 运行时信息）

```bash
jvm     # 运行时/OS/JVM 参数等一大屏
```

**本机实测**（关键行）：

```
 RUNTIME
 MACHINE-NAME     32039@MacBookPro
 VM-NAME          OpenJDK 64-Bit Server VM
 VM-VENDOR        JetBrains s.r.o.
 VM-VERSION       25.0.3+9-b329.124
 INPUT-ARGUMENTS  -Xmx2048m ... -XX:+HeapDumpOnOutOfMemoryError ...
```

> 实测解读：VM-VENDOR 显示 `JetBrains s.r.o.` = IDEA 用的是 JBR（JetBrains Runtime），不是 Oracle/OpenJDK 发行版——`jvm` 一眼确认运行时来源，比 `java -version` 直观。INPUT-ARGUMENTS 列的是启动参数（实际生效值要配合 `jcmd <pid> VM.flags` 看，JBR 有 SoftMaxHeapSize 动态堆，详见 [JVM调优实战](JVM调优实战.md) 4.1）。

### 3.9 sysprop / sysenv（系统属性 / 环境变量）

```bash
sysprop                  # 全部系统属性
sysprop user.home        # 按 key 查
sysenv PATH              # 查环境变量
```

**本机实测**（`sysprop user.home`）：

```
 KEY        VALUE
 user.home  /Users/lub
```

> 比 `System.getProperties()` 方便在不用写代码，线上直接查启动参数里的 -D 属性是否生效。

### 3.10 stack（方法调用路径）

```bash
stack demo.MathGame primeFactors -n 2    # 抓 2 次退出
stack com.example.OrderService createOrder
# 输出：这个方法被哪些调用链调进来的（反向线程栈）
```

**本机实测**（math-game.jar，`stack demo.MathGame primeFactors -n 2`）：

```
ts=2026-08-07 16:21:09.581;thread_name=main;id=1;is_daemon=false;priority=5
    @demo.MathGame.primeFactors()
        at demo.MathGame.run(MathGame.java:24)
        at demo.MathGame.main(null:16)
```

> 实测解读：stack 与 trace 相反——trace 看**这个方法的内部调用链**（向下），stack 看**谁调进来的**（向上）。输出的是调用该方法的完整线程栈，用于反查入口。

### 3.12 monitor（方法调用监控）

```bash
monitor -c 5 com.example.OrderService createOrder
# 每 5 秒统计：调用次数、成功率、平均耗时、失败率
monitor -c 3 demo.MathGame primeFactors -n 2   # 3 秒一统计, 2 次统计后退出
```

**本机实测**（math-game.jar，`monitor -c 3 demo.MathGame primeFactors -n 2`）：

```
 timestamp    class          method        total  success  fail  avg-rt(ms)  fail-rate
 2026-08-07   demo.MathGame  primeFactors  3      1        2     0.22        66.67%
 16:20:58.536
 2026-08-07   demo.MathGame  primeFactors  3      1        2     0.05        66.67%
 16:21:01.550
```

> 实测解读：每个统计周期输出一次——total 调用次数、success/fail 成功失败数、avg-rt 平均耗时、fail-rate 失败率。math-game 故意随机抛异常（number<2 时），所以失败率稳定在 66.67%，正好演示了失败统计。适合挂在方法上看一段时间的健康度。

### 3.13 ognl（表达式执行，万能钥匙）

```bash
ognl '@com.example.Config@MAX_RETRY'                 # 读静态字段
ognl '@demo.MathGame@random.nextInt()'               # 调静态方法/字段上的方法
ognl '#map = new java.util.HashMap(), #map.put("a",1), #map'  # 执行任意表达式
```

**本机实测**（math-game.jar）：

```
$ ognl '@demo.MathGame@random.nextInt()'
@Integer[1091758713]
```

> ⚠️ **JDK 17+ 模块坑（实测踩到）**：ognl 碰 `java.util.Random` 内部字段会报 `InaccessibleObjectException: module java.base does not "opens java.util"`——JDK 9 模块化后，反射访问 java.base 内私有成员被拒。**测业务代码自己的类没问题，碰 JDK 内部类字段就会炸**，这不是 ognl 坏了，是模块封装。想放开得 `--add-opens java.base/java.util=ALL-UNNAMED` 启动目标进程。

> ⚠️ 另外实例字段不能 `@类名@字段` 读（报 `Field xxx is not static`），那是静态访问语法；实例字段要拿对象实例走别的路子（如 threadlocal/watch）。

**⚠️ 危险**：能读也能写，能调任意方法——生产慎用，别用它改线上状态。

### 3.14 redefine / mc（热更新）

```bash
mc /tmp/OrderService.java -d /tmp/classes      # 内存编译
redefine /tmp/classes/com/example/OrderService.class   # 替换运行中的类
```

**本机实测**（math-game.jar 完整跑通热更新）：

```bash
# 1. 改源码：在 print() 里加一行 [REDEFINED] 标记
# 2. mc 内存编译（不需要 javac 命令）
$ mc -d /tmp/arthas-redefine/out /tmp/arthas-redefine/demo/MathGame.java
Memory compiler output:
/tmp/arthas-redefine/out/demo/MathGame.class
Affect(row-cnt:1) cost in 409 ms.

# 3. redefine 热替换
$ redefine /tmp/arthas-redefine/out/demo/MathGame.class
redefine success, size: 1, classes:
demo.MathGame
```

**效果对比**（同一进程输出，未重启）：

```
# redefine 前
91230=2*3*5*3041
99032=2*2*2*12379
# redefine 后（print 里加了标记的新代码立即生效）
[REDEFINED] number=98461
98461 = 11 * 8951
```

> 实测解读：mc 是**内存编译**（用目标 JVM 自己的编译器），不需要本机装 javac；redefine 用 `Instrumentation.redefineClasses` 原地换类。改方法体立竿见影，进程不重启。**但注意这是改线上行为，只适合临时救火，重启即失效**。

**⚠️ 风险**：新类必须与原类**结构完全一致**（不能增删字段/方法，只能改方法体）；重启后失效；生产谨慎。本机测试用 math-game.jar（官方 demo）零风险，别拿业务系统练手。

---

## 4. Web 控制台（tunnel-server，浏览器里用 Arthas）

Arthas 不止有终端客户端，还有 **Web 控制台**：目标 JVM 里的 agent 通过 WebSocket 注册到 tunnel-server，浏览器访问 tunnel-server 的页面即可在网页终端里敲 Arthas 命令——**适合不想 SSH 到机器、或团队共享诊断入口的场景**。

### 4.1 架构一句话

```
目标 JVM(agent) ──ws──▶ tunnel-server(:7777) ──http──▶ 浏览器(:8080)
                      (Arthas Console 页面)
```

### 4.2 启动 tunnel-server（本机实测）

```bash
# 本地文件：/Users/lub/Desktop/本地环境/tools/arthas-tunnel-server-4.3.2-fatjar.jar
java -jar arthas-tunnel-server-4.3.2-fatjar.jar --server.port=8080 --arthas.agent-port=7777
```

- 默认端口：Web 控制台 **8080**、agent 注册 **7777**（可用 `--server.port` / `--arthas.agent-port` 改）
- 启动成功标志：浏览器打开 `http://127.0.0.1:8080/` 显示 **Arthas Console** 页面（实测 HTTP 200，`<title>Arthas Console</title>`）

> ⚠️ **实测坑（端口占用）**：本机之前已经跑着一个 tunnel-server（`lsof -i :7777` 可见），再启动会报 `Address already in use` 直接退出。启动前先 `lsof -i :8080 -i :7777` 确认端口没被占。

### 4.3 attach 时注册到 tunnel（实测）

```bash
java -jar arthas-boot.jar --tunnel-server 'ws://127.0.0.1:7777/ws' \
     --agent-id my-agent-001 --app-name myapp <pid>
```

- `--tunnel-server`：tunnel 地址，格式 `ws://host:7777/ws`
- `--agent-id`：给这个 agent 起唯一 ID（**必须唯一**，重复会互相顶掉）
- `--app-name`：应用名，Web 控制台里按 app 分组
- 注册成功后，浏览器里能看到 agent 出现在列表，点进去就是该 JVM 的 Arthas 终端

> 实测：本机 agent 注册后，tunnel-server 的 API 端点有 `/api/tunnelApps`、`/api/tunnelAgentInfo`（从 fatjar 里反编译 Controller 确认）。Web 前端通过 WebSocket 实时推送 agent 列表，刷新页面即可看到。

> [!note]- 🐛 tunnel 注册失败排查（实测踩坑）
> **症状**：Web 控制台 connect 显示"已连接"但无反应。
> **根因**：目标进程已有**旧 agent 驻留**（无 tunnel 配置），新 attach 被静默复用——tunnel 注册是 agent **注入时**读配置决定的，不是连接时。
> **自查清单**：
> ```bash
> lsof -i :7777          # ① 目标进程有没有连到 tunnel（没有=没注册）
> lsof -nP -p <pid> | grep LISTEN   # ② 目标进程是否有旧 agent 端口
> # 修复：停旧 agent → 重新注入带 tunnel 配置的新 agent
> java -jar arthas-client.jar 127.0.0.1 <telnet端口> -c "stop"
> java -jar arthas-boot.jar --tunnel-server 'ws://127.0.0.1:7777/ws' \
>      --agent-id xxx --app-name xxx --attach-only <pid>
> lsof -i :7777          # ③ 验证：目标进程出现 → 刷新页面
> ```

### 4.4 端口排查（telnet 端口 vs http 端口）

**症状**：attach 报 `Connection refused 127.0.0.1 3658`——目标进程已有 agent，但不在默认端口（曾被 `--telnet-port` 改过）。

**完整排查流程**（不靠猜，每步有实锤）：

```bash
# ① 目标进程所有监听端口
lsof -nP -p <pid> | grep LISTEN
# 例: 127.0.0.1:9995 (LISTEN)   ← 可能的 telnet 端口
#     127.0.0.1:8563 (LISTEN)   ← http 端口(特征!)

# ② 区分哪个是 telnet、哪个是 http —— 日志是唯一铁证
grep -E "bind telnet|bind http" ~/logs/arthas/arthas.log | tail
# → "try to bind telnet server, port: 9995."  ← telnet 端口(client 连这个)
# → "try to bind http server, port: 8563."    ← http 端口(浏览器用)

# ③ 无日志权限时的兜底:client 试连
java -jar arthas-client.jar 127.0.0.1 <端口>   # 出 [arthas@pid]$ = telnet;卡住 = http

# ④ 停旧 agent 后重新注入默认端口
java -jar arthas-client.jar 127.0.0.1 <telnet端口> -c "stop"
java -jar arthas-boot.jar --attach-only <pid>
lsof -nP -p <pid> | grep LISTEN   # 验证:3658/8563 出现
```

**实测结论**：
- `curl` 区分不了两个端口——telnet 端口做了 HTTP 兼容，两个都返回同样的 Arthas Console 页面
- `jcmd VM.system_properties` 查不到端口（agent 不写系统属性）；`ps` 看不到（attach 参数不残留）
- 只有 arthas.log 的 bind 记录是权威，其次 client 试连兜底

**配置优先级**（官方文档）：命令行参数 > System Env > System Properties > arthas.properties

**随机端口防冲突**（官方推荐）：`arthas.telnetPort=0` 随机端口（日志里找）；`arthas.httpPort=-1` 禁用 http——多实例防端口冲突，配合 tunnel 使用。

### 4.5 与终端客户端的区别

| 维度 | 终端 `java -jar arthas-boot.jar <pid>` | Web 控制台 |
|---|---|---|
| 使用位置 | 目标机器本机 | 任意能访问 tunnel-server 的浏览器 |
| 多 agent | 一次连一个 | 列表里随意切换 |
| 典型场景 | 本机/单机排查 | 服务器集群、团队共享诊断、跳板机访问 |

> 生产建议：tunnel-server 部署在跳板机/内网，agent 注册到它，团队成员浏览器访问 Web 控制台排查——不用给每个人开服务器 SSH 权限。

---

## 5. 典型场景实战

### 5.1 场景一：CPU 100% 飙高

```bash
# 老办法（三板斧）：
#   top -Hp <pid> → 线程号转十六进制 → jstack grep nid=0x...
# Arthas 一步到位：
thread -n 3
# 直接看到最忙的 3 个线程正在执行什么代码
```

### 5.2 场景二：接口变慢，定位瓶颈

```bash
trace com.example.OrderService createOrder '#cost > 50'
# 看耗时分布：DB 慢？远程调用慢？还是本地循环慢？
```

### 5.3 场景三：线上报错，但不知道哪个参数导致

```bash
watch com.example.OrderService createOrder '{params, throwExp}' -x 2
# 把每次调用的入参和异常打出来，复现问题时直接抓到
```

### 5.4 场景四：怀疑线上版本不对

```bash
jad --source-only com.example.OrderService | grep "2026-07-01"
# 反编译看线上真实代码，和本地对比
```

### 5.5 场景五：内存里有个对象想看看内容

```bash
# 配合 ognl：从静态字段/Spring 容器里取对象
ognl '@com.example.Cache@INSTANCE.size()'
```

---

## 6. 与 JDK 工具对比（何时用谁）

| 场景 | 首选 | 原因 |
|---|---|---|
| 快速看 GC/内存趋势 | `jstat -gcutil` | 零侵入、轻量 |
| 线程 dump 落盘分析 | `jstack` | 快照可归档对比 |
| OOM 后分析堆 | `jmap -dump` + MAT | 离线深度分析 |
| **线上实时排查** | **Arthas** | 不重启、方法级、能反编译 |
| 长时性能画像 | JFR | 采样开销 <1% |

**原则**：JDK 工具"轻快够用"优先；Arthas 用于"JDK 工具解决不了"的深水区（方法级追踪、看参数、反编译、热更新）。

---

## 7. 易错点清单

1. **quit ≠ stop**：quit 只退客户端，增强还在；要完全还原用 `stop`
2. **watch/trace 有性能开销**：线上挂着高频 trace 会拖慢应用（探针在每个调用上跑），排查完记得 stop
3. **redefine 结构限制**：只能改方法体，不能增删字段/方法/改签名，否则报错；重启失效
4. **ognl 危险**：能改线上状态、能调任意方法，生产别乱玩
5. **attach 可能被拒**：目标 JVM 若开了 `-XX:+DisableAttachMechanism` 无法 attach；容器内要注意权限（非 root 用户可能 attach 不了别人的进程）
6. **Arthas 自身要 JDK 版本匹配**：高版本 JDK（17+）要用新版 Arthas（旧版 3.5.x 对 JDK 17 支持不完整）；Arthas 4 支持 JDK 8+
7. **别在生产裸奔**：用完 stop，别挂着 dashboard 刷一天
8. **4.x 里 `gc` 命令没了**（实测报 `gc: command not found`）：看 GC 统计用 `memory`
9. **as.sh 依赖 telnet**（macOS 默认没装）：直接用 `java -jar arthas-boot.jar`，不需要 telnet
10. **tunnel-server 端口占用**：8080（Web）/ 7777（agent）被占时启动直接报 `Address already in use` 退出，先 `lsof -i :8080 -i :7777` 检查
11. **agent-id 必须唯一**：多个 agent 用同一个 `--agent-id` 注册 tunnel 会互相顶掉
12. **ognl 碰 JDK 内部类会炸（JDK 17+ 实测）**：反射访问 java.base 模块内私有字段报 `InaccessibleObjectException`——业务类随便测，JDK 内部类要 `--add-opens` 才行
13. **同机多进程 attach 端口冲突**：本机已有 agent 占着 3658 时，attach 另一个进程要 `--telnet-port 9998 --http-port -1` 指定新端口（实测报错提示"3658 is used by process X"）
14. **实测演示推荐 math-game.jar**：arthas 发行版自带官方 demo（`java -jar math-game.jar`），方法持续调用、会随机抛异常，trace/watch/monitor/redefine 都能稳定抓到输出，redefine 改它零风险——别拿业务系统练手
15. **agent 生命周期 = 目标 JVM 生命周期**：注入即驻留，`q`/`Ctrl+C` 只退客户端；boot 异常退出后 agent 还在，用 client 直连即可（见 2.7）
16. **旧 agent 复用坑**：目标进程已有 agent 时，新 attach 会静默复用（不注入新配置）——换 tunnel/端口必须**先 stop 再 attach**（见 4.3 排查）
17. **端口不一致坑**：同进程被不同 `--telnet-port` 注入过，client 默认连 3658 会 `Connection refused`——用 `lsof -nP -p <pid> | grep LISTEN` + 日志找实际 telnet 端口（见 4.4）
18. **lsof 端口显示服务名**：macOS 的 lsof 会把 3658 显示成 `ps-ams`、7777 显示成 `cbt`——加 `-nP` 参数才显示数字端口

---

## 8. 面试追问 Q&A

### 8.1 Arthas 和 jstack/jmap 的区别？

答：jstack/jmap 是快照式工具，dump 下来离线看；Arthas 是 attach 到运行中 JVM 的在线诊断工具，能做方法级追踪（trace）、参数观测（watch）、反编译（jad）、热更新（redefine），不需要重启应用。JDK 工具轻快，Arthas 用于深水区排查。

### 8.2 trace 和 watch 的区别？

答：trace 关注**方法内部调用链的耗时分布**，定位"慢在哪一段"；watch 关注**方法的入参/返回值/异常**，定位"数据哪里不对"。一个查性能、一个查数据。

### 8.3 Arthas 为什么不重启就能改代码？

答：底层用 Java Agent 机制（agentmain 运行时 attach）+ Instrumentation 的 retransformClasses 做字节码增强，在方法字节码里插入探针或替换类定义。详见 [Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)。

### 8.4 thread -n 3 为什么比 jstack 方便？

答：jstack 排查 CPU 高需要 top -Hp 找线程号 → 十进制转十六进制 → grep nid=0x...，三步；Arthas 的 thread -n 3 直接按 CPU 占用排序输出最忙线程及当前栈，一步到位。

### 8.5 生产用 Arthas 要注意什么？

答：① 用完 stop（quit 只退客户端，增强还在）；② watch/trace 有探针开销，别长期挂着；③ redefine 只能改方法体且重启失效；④ ognl 能改线上状态，慎用；⑤ 高版本 JDK 要用新版 Arthas。

### 8.6 agent 驻留后怎么退出？boot / agent / client 什么关系？

答：agent 注入后驻留目标 JVM，只有两种退出方式——目标 JVM 关闭、或 client 执行 stop。boot 是启动器（负责 attach 注入，注入完即走），agent 是驻留的代理服务，client 是连接器（随时连随时断）。`quit` 只退客户端，agent 和字节码增强都还在。

### 8.7 attach 报 Connection refused 3658 怎么排查？

答：说明目标进程已有 agent 且不在默认端口。先 `lsof -nP -p <pid> | grep LISTEN` 找实际监听端口，再 `grep "bind telnet" ~/logs/arthas/arthas.log` 确认哪个是 telnet 端口（日志是唯一铁证，curl 区分不了因为两个端口都返回同样页面），最后用 client 连实际 telnet 端口执行 stop 或继续使用。

---

## 9. 📌 原理延伸

Arthas 的底层是 **Java Agent + Instrumentation + 字节码增强（插帧）**——不重启改代码的秘密全在这：

→ 详见 [Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)（01-学习/Java/JDK基础库/核心机制/）

---

## 参考

- Arthas 官方文档：https://arthas.aliyun.com/doc/
- 官方 Properties 文档（端口配置/优先级）：https://arthas.aliyun.com/doc/arthas-properties.html
- 本地文件：`/Users/lub/Desktop/本地环境/tools/arthas-bin/`（4.3.2 发行版）、`arthas-tunnel-server-4.3.2-fatjar.jar`（Web 控制台）
- 关联笔记：[JVM调优实战](JVM调优实战.md)（工具链与场景）、[Java Agent与字节码增强详解](../JDK基础库/核心机制/Java Agent与字节码增强详解.md)（原理）、[Java反射详解](../JDK基础库/核心机制/Java反射详解.md)（运行期动态机制对比）、**Arthas告警自动诊断方案**（见知识库）（监控告警自动触发 Arthas 的落地架构）

---

## 附录：FastDemo 测试靶子（高频调用 demo）

> [!note]- 📦 FastDemo（math-game 调用太慢时的替代靶子）
> **用途**：math-game 每秒才调一次 run()，trace/watch 复现太慢；FastDemo 高频调用 + 真实耗时 + 随机异常，秒出结果。
> **用法**：`javac FastDemo.java && java FastDemo [间隔ms] [耗时ms]`（默认 100ms 间隔 / 50ms 耗时）
> **关键代码**：
> ```java
> public class FastDemo {
>     public static void main(String[] args) throws InterruptedException {
>         long intervalMs = args.length > 0 ? Long.parseLong(args[0]) : 100;
>         long slowMs     = args.length > 1 ? Long.parseLong(args[1]) : 50;
>         while (true) {
>             try {
>                 slowMethod(slowMs);            // 目标方法
>             } catch (Exception e) { /* 偶发异常 */ }
>             TimeUnit.MILLISECONDS.sleep(intervalMs);  // 可调频率
>         }
>     }
>     public static void slowMethod(long sleepMs) throws InterruptedException {
>         TimeUnit.MILLISECONDS.sleep(sleepMs);  // 真实耗时(可调)
>         if (new Random().nextInt(10) < 3) {
>             throw new IllegalArgumentException("random fail");  // 30% 抛异常
>         }
>     }
> }
> ```
> **配套命令**：
> ```bash
> trace FastDemo slowMethod -n 1                          # 秒出耗时分布
> watch FastDemo slowMethod '{params, returnObj}' -n 2    # 能抓到异常路径
> ```
> **测试完记得 stop**：`java -jar arthas-client.jar 127.0.0.1 <telnet端口> -c "stop"`
