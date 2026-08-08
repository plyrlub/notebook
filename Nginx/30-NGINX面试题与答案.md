---
tags: [Nginx, 面试]
创建日期: 2026-08-05
状态: ✅ 已归档（01-学习/服务器/Nginx）
归属: 01-学习/服务器/Nginx
---

# 30 - NGINX 面试题与答案

> **版本基线**：Nginx 1.30.4 (stable) | 创建日期：2026-08-05
> **受众**：后端开发熟手（熟悉 Python/Java/Lua），准备 Nginx 相关面试或系统复习 Nginx 知识体系。

---

## 目录

- [说明](#说明)
- [一、基础概念（10题）](#一基础概念10题)
- [二、配置相关（10题）](#二配置相关10题)
- [三、HTTPS/安全（8题）](#三https安全8题)
- [四、性能优化（8题）](#四性能优化8题)
- [五、OpenResty/Lua（8题）](#五openrestylua8题)
- [六、实战场景（6题）](#六实战场景6题)
- [小结](#小结)

---

## 说明

本文档精选 50 道 Nginx 面试题，按难度和主题分为六大类。每道题都给出**详细答案**（不是简单一两句话），关键题目配有**代码示例**和**踩坑提醒**。

题目覆盖范围：

- **基础概念**：架构原理、进程模型、代理概念、配置结构
- **配置相关**：location 匹配、root/alias、proxy_pass、rewrite、if、try_files、限流
- **HTTPS/安全**：TLS 握手、证书链、HSTS、OCSP、版本隐藏、目录穿越、HTTP/2&3、SNI
- **性能优化**：调优手段、reuseport、upstream keepalive、连接数计算、sendfile、缓存、502/504 排查
- **OpenResty/Lua**：架构关系、执行阶段、cosocket、shared.DICT vs ctx、限流、balancer_by_lua、Kong vs APISIX、lua_code_cache
- **实战场景**：灰度发布、WebSocket、限流方案、配置不生效排查、reload 失败、零停机更新

> **使用建议**：先尝试自己回答，再对照答案。重点关注**踩坑提醒**部分，这些是面试官最想听到的加分项。相关知识点可参考本系列其他文档深入学习。

---

## 一、基础概念（10题）

### Q1. Nginx 是什么？它的主要用途有哪些？

**答案要点**：

Nginx（读作 "engine-x"）是一款开源的高性能 HTTP 服务器和反向代理服务器，由俄罗斯工程师 Igor Sysoev 于 2002 年开发，2004 年首次发布。它采用 BSD 许可证，核心设计哲学是**事件驱动 + 异步非阻塞 IO**，以极少的进程和内存处理海量并发连接。

Nginx 的主要用途包括四大类：

**1. 静态 Web 服务器**：直接返回 HTML、图片、CSS、JS 等静态文件。Nginx 处理静态文件的效率远高于 Tomcat、Node.js 等应用服务器，因为它使用 sendfile 零拷贝技术，数据直接从磁盘到网络套接字，不经过用户空间。

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    location / {
        try_files $uri $uri/ =404;
    }
}
```

**2. 反向代理服务器**：接收客户端请求，转发给后端应用服务器（如 Java/Python/Node.js），再把后端的响应返回给客户端。这是 Nginx 最常见的用途。

```nginx
location /api/ {
    proxy_pass http://backend:8080;
}
```

**3. 负载均衡器**：将请求分发到多台后端服务器，支持轮询、加权轮询、IP Hash、最少连接等算法。

```nginx
upstream backend {
    server 192.168.1.1:8080 weight=3;
    server 192.168.1.2:8080 weight=2;
    server 192.168.1.3:8080;
}
```

**4. API 网关**：通过 Nginx + Lua（OpenResty）可以实现认证、限流、熔断、动态路由等网关功能。Kong、APISIX 等开源网关都基于 OpenResty。

> **面试加分点**：提到 Nginx 还可以做事层（TCP/UDP）代理（`stream` 模块），以及 mail 代理（`mail` 模块），展示你了解 Nginx 的完整能力边界。

---

### Q2. Nginx 和 Apache 的主要区别是什么？

**答案要点**：

| 维度 | Nginx | Apache |
|------|-------|--------|
| **并发模型** | 事件驱动（epoll/kqueue），少量 worker 进程，每个 worker 处理大量连接 | 默认一个连接一个线程/进程（prefork/worker MPM），event MPM 才接近事件驱动 |
| **内存占用** | 极低，万级并发只需几十 MB | 高，每连接/线程占数 MB 栈空间 |
| **静态文件** | 极快（sendfile 零拷贝） | 快，但不如 Nginx |
| **动态内容** | 需反向代理给后端（PHP-FPM、uWSGI 等） | 可直接嵌入 mod_php、mod_wsgi 等模块处理 |
| **配置风格** | 声明式，location 匹配规则复杂 | 声明式，`.htaccess` 支持目录级配置 |
| **模块加载** | 静态编译（1.9.11+ 支持动态模块） | 支持运行时动态加载模块（DSO） |
| **适用场景** | 高并发、反向代理、负载均衡、静态资源 | 传统 Web 应用、需要 .htaccess、需要嵌入式动态处理 |

**核心区别在于并发模型**：

- Apache 传统模型（prefork MPM）：每个连接分配一个进程。10000 个并发连接需要 10000 个进程，每个进程至少几 MB 内存，内存和上下文切换开销巨大。这就是著名的 C10K 问题。
- Nginx 事件驱动模型：一个 worker 进程通过 epoll 同时管理数千个连接。worker 大部分时间在 IO 多路复用上等待事件，哪个连接有数据可读/可写就处理哪个，不阻塞在任何单个连接上。

**为什么 Apache 没有"死"**：Apache 在动态内容处理上有历史优势（mod_php 直接嵌入 PHP 解释器，不需要额外进程间通信），且 `.htaccess` 提供了目录级配置能力（Nginx 不支持），在某些场景下仍然有市场。但现代架构中，Nginx 做前端反向代理 + 后端应用服务器（PHP-FPM/Gunicorn/Node.js）已经成为主流。

> **踩坑提醒**：面试时不要说"Nginx 比 Apache 好"这种笼统的话。要具体到并发模型、内存占用、适用场景的差异，展示你理解的是"为什么"而不仅是"是什么"。

---

### Q3. 解释 Nginx 的事件驱动模型

**答案要点**：

Nginx 的事件驱动模型是其高性能的核心。要理解它，需要从三个层面讲清楚：

**1. 为什么需要事件驱动——传统模型的问题**

传统服务器（如 Apache prefork）采用"一连接一线程/进程"模型：每来一个连接，就派一个线程专门伺候它，直到连接关闭。问题是线程绝大部分时间在**等**——等客户端发数据、等磁盘读文件、等后端返回响应。等待期间线程占着内存不释放，CPU 还要在大量线程间做上下文切换，真正处理请求的时间反而很少。

**2. 事件驱动怎么工作**

Nginx 的做法：一个 worker 进程通过操作系统提供的 **IO 多路复用**机制（Linux 上的 epoll，BSD 上的 kqueue）同时监控数千个连接的状态。哪个连接有数据可读、哪个连接可以写入，epoll 会通知 worker，worker 就去处理那个连接的事件。处理完立刻回到 epoll 等下一个事件，不在任何一个连接上阻塞。

用餐厅类比：

> 传统模型 = 一个服务员盯一桌客人，客人在看菜单时服务员干站着。
> 事件驱动 = 一个服务员同时照看 1000 桌，谁按铃（有事件）就去谁那桌，处理完立刻回来等下一个铃。

**3. 具体流程**

```
worker 进程启动
  → 调用 epoll_create() 创建 epoll 实例
  → 将监听套接字（listen socket）加入 epoll 监听
  → 进入事件循环：
      epoll_wait()  ← 阻塞等待事件（不会忙等，CPU 占用极低）
      |
      ├─ 如果是监听套接字可读 → 有新连接来了 → accept() 接受连接
      |    → 将新连接的套接字加入 epoll 监听
      |
      ├─ 如果是已连接套接字可读 → 客户端发了数据 → 读取请求
      |    → 解析请求 → 如果是静态文件，读文件并返回
      |    → 如果是反向代理，连接后端，转发请求（非阻塞）
      |
      ├─ 如果是后端连接可读 → 后端返回了响应 → 读响应并转发给客户端
      |
      └─ 如果是套接字可写 → 写入响应数据 → 写完后可能继续保持连接（keepalive）
```

**4. 非阻塞 IO 的配合**

事件驱动必须配合**非阻塞 IO**。当 worker 调用 `read()` 读取套接字时，如果数据还没到，`read()` 立刻返回 `EAGAIN` 错误（而不是阻塞等待）。worker 知道"这个连接暂时没数据"，就回去等 epoll 的下一个事件。如果用阻塞 IO，worker 在等一个连接的数据时就被卡住了，其他几千个连接都得不到处理。

**5. 事件驱动模型的局限**

- **CPU 密集型任务不适合**：事件驱动擅长 IO 密集型场景（等网络、等磁盘），如果请求需要大量 CPU 计算（如视频转码），会卡住整个 worker 的事件循环。所以 Nginx 把动态请求代理给后端处理，自己只做 IO 转发。
- **单 worker 不能利用多核**：一个 worker 是单线程的，只能用一个 CPU 核。所以 Nginx 启动多个 worker 进程（通常等于 CPU 核数），每个 worker 独立运行事件循环。

> **面试加分点**：提到 epoll 相比 select/poll 的优势——epoll 使用红黑树管理监听的 fd，`epoll_wait` 只返回有事件的 fd（O(活跃连接数)），而 select/poll 每次要遍历所有监听的 fd（O(总连接数)）。这就是为什么 epoll 能高效处理万级并发。

---

### Q4. master 进程和 worker 进程的区别？

**答案要点**：

Nginx 采用 **master-worker** 多进程架构。它们分工明确：

**master 进程**：

- **角色**：管理者，不处理具体请求。
- **运行用户**：通常是 root（需要绑定 80/443 特权端口）。
- **职责**：
  1. 读取并验证配置文件。
  2. 创建、管理 worker 进程（fork 出来）。
  3. 绑定监听端口（listen socket）。
  4. 接收外部信号（如 `kill -HUP` 触发 reload），并转发给 worker。
  5. 监控 worker 状态，如果 worker 异常退出，自动重新 fork 一个新的。
  6. 管理日志文件（响应 USR1 信号重新打开日志）。
  7. 热升级（USR2 信号启动新 master，WINCH 信号让旧 worker 退出）。

**worker 进程**：

- **角色**：实际干活的，处理客户端请求。
- **运行用户**：通常是 `nginx` 或 `www-data` 等非特权用户（安全考虑）。
- **职责**：
  1. 从 master 继承监听套接字。
  2. 运行事件循环（epoll），接受连接、处理请求。
  3. 所有 worker 共享同一组监听套接字，通过 `accept_mutex`（互斥锁）或 `reuseport` 避免惊群问题。
- **数量**：通常设置为 CPU 核数（`worker_processes auto;`），每个 worker 独立运行，利用多核。

**请求处理流程**：

```
客户端连接 → 操作系统 → master 创建的 listen socket
                            ↓
                   多个 worker 竞争 accept（或 reuseport 各自accept）
                            ↓
                   某个 worker accept 成功 → 处理这个连接
                            ↓
                   worker 通过事件循环处理请求 → 返回响应
```

**为什么 master 不处理请求**：分离关注点。master 专注管理（配置加载、进程管理、信号处理），worker 专注请求处理。如果 worker 崩溃了，master 会立即 fork 一个新的，服务不中断。如果 master 和请求处理混在一起，一个 bug 就可能导致整个服务挂掉。

**reload 时发生什么**：

```
1. master 收到 HUP 信号
2. master 重新读取配置文件
3. master fork 出新的 worker 进程（使用新配置）
4. master 向旧 worker 发送 QUIT 信号
5. 旧 worker 处理完手中请求后优雅退出
6. 新 worker 接管所有新连接
```

> **踩坑提醒**：面试官可能会追问"worker 之间如何共享监听端口"。答案是：所有 worker 进程从 master 继承了同一个 listen socket 的文件描述符。多个进程同时 `accept` 同一个 socket 会导致"惊群"问题（一个连接到来，所有 worker 被唤醒，但只有一个能 accept 成功，其他白跑一趟）。Nginx 用 `accept_mutex` 锁来避免：同一时刻只有一个 worker 在 accept。Linux 3.9+ 可以用 `reuseport` 让每个 worker 有独立的 listen socket，完全避免惊群。

---

### Q5. Nginx 为什么能处理高并发？

**答案要点**：

Nginx 能处理高并发是多个设计决策共同作用的结果，不能只回答"事件驱动"一个点：

**1. 事件驱动 + 非阻塞 IO（核心）**

如 Q3 所述，一个 worker 通过 epoll 同时管理数千个连接，不在任何单个连接上阻塞。万级并发只需少量 worker 进程（通常等于 CPU 核数），内存占用极低。

**2. 内存复用——连接不独占线程**

传统模型每个连接独占一个线程，每个线程默认 8MB 栈空间，10000 连接需要 80GB 内存。Nginx 每个连接只占几 KB（连接结构体 + 读写缓冲区），10000 连接只需几十 MB。

**3. master-worker 架构**

master 负责管理，worker 负责干活。worker 崩溃了 master 自动重建，保证高可用。多 worker 利用多核 CPU。

**4. 内存池（memory pool）**

Nginx 为每个请求分配一个内存池，请求处理完毕后整个内存池一次性释放，避免了频繁的 malloc/free 调用和内存碎片。

**5. sendfile 零拷贝**

处理静态文件时，Nginx 使用 `sendfile()` 系统调用，数据从磁盘直接到网络套接字，不需要经过用户空间拷贝，大幅减少 CPU 和内存开销。

```nginx
# 开启 sendfile
sendfile on;
# 配合 tcp_nopush 减少网络包数量
tcp_nopush on;
```

**6. 长连接复用**

客户端 keepalive：一个 TCP 连接可以处理多个 HTTP 请求，避免反复 TCP 握手。
upstream keepalive：Nginx 到后端的连接也复用，避免每次请求都新建 TCP 连接。

**7. 轻量级**

Nginx 本身没有嵌入重量级的运行时（如 JVM、PHP 解释器），二进制只有几 MB，启动极快。

**量化对比**：

| 指标 | 传统模型（Apache prefork） | Nginx |
|------|---------------------------|-------|
| 10000 并发连接的内存 | 数十 GB（每线程 8MB 栈） | 数十 MB（每连接约 2KB） |
| 10000 并发连接的 CPU | 大量消耗在上下文切换 | 主要消耗在 IO 等待 |
| 理论并发上限 | 受线程数限制（通常数千） | 受文件描述符限制（可达数十万） |

> **面试加分点**：提到 Nginx 的并发上限最终受限于**系统文件描述符数量**（`ulimit -n`），而不是 Nginx 本身。生产环境需要调大 `worker_rlimit_nofile` 和系统的 `fs.file-max`。

---

### Q6. 正向代理和反向代理的区别？

**答案要点**：

这是面试高频题，关键在于理解"代理"代理的是谁。

**正向代理（Forward Proxy）**：

- **代理的是客户端**。客户端知道要访问的目标服务器，但不直接访问，而是先发给正向代理服务器，由代理服务器代为请求。
- **客户端感知代理的存在**，需要配置代理地址。
- **服务器不知道真实客户端是谁**，只看到代理服务器的 IP。
- **典型用途**：翻墙（VPN/代理）、公司内网上外网、缓存加速。
- **Nginx 正向代理配置**：Nginx 本身不太适合做正向代理（不支持 CONNECT 方法的 HTTPS 代理），通常用 Squid、V2Ray 等专业工具。

```
客户端 → 正向代理 → 目标服务器
         (客户端配置代理)
```

**反向代理（Reverse Proxy）**：

- **代理的是服务端**。客户端直接访问代理服务器（以为它就是目标服务器），代理服务器将请求转发给后端真实服务器。
- **客户端不感知代理的存在**，以为代理服务器就是目标服务器。
- **后端服务器不知道真实客户端是谁**（除非代理传递了 `X-Forwarded-For`）。
- **典型用途**：负载均衡、SSL 终止、静态缓存、隐藏后端服务器 IP。
- **Nginx 反向代理配置**：这是 Nginx 最核心的用途。

```
客户端 → 反向代理（Nginx） → 后端服务器1
                          → 后端服务器2
                          → 后端服务器3
         (客户端以为Nginx就是目标)
```

**对比表**：

| 维度 | 正向代理 | 反向代理 |
|------|---------|---------|
| 代理谁 | 客户端 | 服务端 |
| 谁配置 | 客户端配置代理地址 | 服务端部署代理 |
| 客户端是否感知 | 是 | 否 |
| 目标服务器是否感知 | 只看到代理 IP | 通常只看到代理 IP |
| 典型用途 | 翻墙、内网出网、缓存 | 负载均衡、SSL终止、安全隔离 |
| Nginx 是否擅长 | 不擅长（HTTPS 需 CONNECT） | 非常擅长（核心功能） |

**一句话记忆**：正向代理代理的是客户端（帮客户端发请求），反向代理代理的是服务端（帮服务端收请求）。

> **踩坑提醒**：Nginx 做反向代理时，默认不会传递客户端真实 IP。后端看到的是 Nginx 的 IP。需要配置 `proxy_set_header X-Real-IP $remote_addr;` 和 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` 才能让后端拿到真实客户端 IP。详见踩坑记录 `#5.4`。

---

### Q7. Nginx 的配置文件结构是怎样的？

**答案要点**：

Nginx 配置文件采用**嵌套的块结构**，从外到内分为多个层级，每层有各自可用的指令：

```
nginx.conf（主配置文件）
│
├── events {}           ← 事件模块配置（全局，影响 worker 行为）
│
├── http {}             ← HTTP 模块配置（HTTP 相关的所有配置都在这里）
│   ├── upstream {}     ← 负载均衡池定义
│   ├── server {}       ← 虚拟主机（一个 server = 一个站点）
│   │   ├── location {} ← URL 匹配规则（一个 location = 一类请求的处理方式）
│   │   │   ├── proxy_pass / root / rewrite / ...
│   │   │   └── location {}  ← 嵌套 location（较少用）
│   │   └── ...
│   └── server {}       ← 更多虚拟主机
│
├── stream {}           ← TCP/UDP 代理配置（四层代理，与 http 同级）
│   └── server {}
│
└── mail {}             ← 邮件代理配置（较少用）
```

**各层级的职责**：

| 层级 | 作用 | 常见指令 |
|------|------|---------|
| `main`（全局） | 影响 Nginx 全局行为 | `worker_processes`、`error_log`、`pid`、`user` |
| `events` | 影响 worker 的连接处理 | `worker_connections`、`use epoll`、`accept_mutex` |
| `http` | HTTP 服务全局配置 | `sendfile`、`keepalive_timeout`、`include mime.types`、`gzip` |
| `upstream` | 定义后端服务器组 | `server`、`keepalive`、`load balancing method` |
| `server` | 虚拟主机 | `listen`、`server_name`、`ssl_certificate` |
| `location` | URL 路由匹配 | `proxy_pass`、`root`、`alias`、`rewrite`、`try_files` |

**指令继承规则**：

- 子块继承父块的指令（如 `http` 里的 `sendfile on;` 对所有 `server` 和 `location` 生效）。
- 子块可以覆盖父块的指令（如 `location` 里重新定义 `root`）。
- 有些指令只能在特定层级使用（如 `listen` 只能在 `server` 里，`proxy_pass` 只能在 `location` 里）。

**完整示例**：

```nginx
# ===== 全局配置 =====
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

# ===== events 块 =====
events {
    worker_connections 10240;
    use epoll;
}

# ===== http 块 =====
http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    # ===== upstream 定义 =====
    upstream backend {
        server 192.168.1.1:8080;
        server 192.168.1.2:8080;
        keepalive 32;
    }

    # ===== 虚拟主机 1 =====
    server {
        listen 80;
        server_name www.example.com;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # ===== 虚拟主机 2 =====
    server {
        listen 80;
        server_name api.example.com;

        location / {
            proxy_pass http://backend;
        }
    }
}
```

> **最佳实践**：生产环境不要把所有配置堆在 `nginx.conf` 一个文件里。`nginx.conf` 只放全局配置，`http` 块里用 `include /etc/nginx/conf.d/*.conf;` 引入各个站点的独立配置文件。这样每个站点一个文件，方便管理和版本控制。

---

### Q8. worker_processes 应该设置多少？

**答案要点**：

**核心结论**：`worker_processes` 应该设置为 **CPU 核心数**。最简单的方式是用 `auto`：

```nginx
worker_processes auto;
```

**为什么是 CPU 核心数**：

1. Nginx 每个 worker 是单线程的（运行一个事件循环），一个 worker 同一时刻只能用一个 CPU 核。
2. 如果 worker 数少于 CPU 核数，有的 CPU 核会闲置。
3. 如果 worker 数多于 CPU 核数，多个 worker 会争抢同一个 CPU 核，增加上下文切换开销，反而降低性能。
4. 设为 CPU 核数，每个 worker 独占一个核，最大化利用 CPU 且无争抢。

**如何确认 CPU 核数**：

```bash
# 查看 CPU 核数
nproc
# 或
grep -c ^processor /proc/cpuinfo
```

**什么时候需要调整**：

| 场景 | 建议值 | 原因 |
|------|--------|------|
| 正常 Web 服务器 | `auto`（= CPU 核数） | 默认最优 |
| CPU 有超线程 | `auto`（= 逻辑核数） | 超线程核也算 |
| 多核但 IO 等待高 | 可以略多于核数（如核数 × 1.5） | IO 等待时 CPU 空闲，多一个 worker 填补空闲 |
| 运行 OpenResty + CPU 密集型 Lua | `auto`，不要更多 | Lua 代码在 worker 线程执行，多了反而争抢 CPU |
| 混合部署（同机器有其他 CPU 密集型服务） | 减少 worker 数 | 给其他服务留 CPU |

**`auto` 的原理**：Nginx 启动时读取 `/sys/devices/system/cpu/online` 或调用 `sysconf(_SC_NPROCESSORS_ONLN)` 获取在线 CPU 核数，自动设置为该值。

> **踩坑提醒**：
> 1. 修改 `worker_processes` 后需要 **restart**（不是 reload）才能生效。reload 只重新加载配置，不会改变 worker 数量——要改变 worker 数量必须重启 Nginx 进程。
> 2. `auto` 在某些容器环境（如 Docker 限制 CPU 的场景）可能不准确。如果 Docker 用 `--cpus=2` 限制了 CPU，但宿主机有 32 核，`auto` 可能拿到 32 而不是 2。这时需要手动指定。

---

### Q9. 什么是 upstream？

**答案要点**：

`upstream` 是 Nginx 中定义**后端服务器组**的指令，用于反向代理和负载均衡。它把一组后端服务器打包成一个逻辑名称，`proxy_pass` 直接引用这个名称即可，不需要写死具体 IP。

**基本语法**：

```nginx
http {
    upstream backend {
        server 192.168.1.1:8080;
        server 192.168.1.2:8080;
        server 192.168.1.3:8080;
    }

    server {
        location /api/ {
            proxy_pass http://backend;  # 引用 upstream 名称
        }
    }
}
```

**upstream 的作用**：

1. **负载均衡**：多个后端服务器分担请求压力。
2. **故障转移**：某台后端挂了，Nginx 自动把请求转发到其他健康的服务器。
3. **解耦**：`proxy_pass` 引用 upstream 名称，后端服务器 IP 变化时只需改 upstream 配置，不用改每个 location。
4. **健康检查**：通过 `max_fails` 和 `fail_timeout` 做被动健康检查（开源版）。

**upstream 中的 server 参数**：

```nginx
upstream backend {
    # 基本格式：server address [parameters];
    server 192.168.1.1:8080 weight=3 max_fails=3 fail_timeout=30s;
    server 192.168.1.2:8080 weight=2;
    server 192.168.1.3:8080 backup;       # 备用服务器，正常时不参与，其他都挂了才启用
    server 192.168.1.4:8080 down;         # 标记为下线，不参与负载
    keepalive 32;                          # 到后端的长连接池大小
}
```

| 参数 | 说明 |
|------|------|
| `weight=N` | 权重，默认 1。权重越高，分配到的请求越多 |
| `max_fails=N` | 在 `fail_timeout` 时间内失败 N 次，标记为不可用 |
| `fail_timeout=T` | 失败统计时间窗口（默认 10s） |
| `backup` | 备用服务器，正常时不接收请求，其他服务器都不可用时才启用 |
| `down` | 永久标记为不可用 |
| `max_conns=N` | 最大并发连接数（1.11.5+），超过则不分配新请求 |
| `resolve` | 动态解析域名（配合 `resolver` 使用），后端 IP 变化时自动更新 |
| `slow_start=T` | 服务恢复后 gradually 增加权重（商业版功能） |

> **踩坑提醒**：
> 1. `upstream` 只能定义在 `http` 块中，不能放在 `server` 或 `location` 里。
> 2. 开源版 Nginx 只支持**被动健康检查**——请求失败才标记不可用。如果你需要**主动健康检查**（定期发健康探测请求），需要用 Nginx Plus（商业版）或第三方模块（如 `nginx_upstream_check_module`）或 OpenResty 的 `lua-resty-upstream-healthcheck`。
> 3. 单台后端时 `max_fails`/`fail_timeout` **不生效**——因为只有一台，标记为不可用后没有其他服务器可以接管。详见踩坑记录 `#5.2`。

---

### Q10. Nginx 支持哪些负载均衡算法？

**答案要点**：

Nginx 内置 4 种负载均衡算法，还可以通过第三方模块扩展：

**1. 轮询（Round Robin）——默认**

```nginx
upstream backend {
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
    server 192.168.1.3:8080;
}
```

请求按顺序轮流分配给每台服务器。不需要显式指定，这是默认行为。

**2. 加权轮询（Weighted Round Robin）**

```nginx
upstream backend {
    server 192.168.1.1:8080 weight=3;  # 30% 的请求
    server 192.168.1.2:8080 weight=2;  # 20% 的请求
    server 192.168.1.3:8080 weight=5;  # 50% 的请求
}
```

按权重比例分配请求。服务器性能不均时，给高性能服务器更高权重。

**3. IP Hash**

```nginx
upstream backend {
    ip_hash;
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}
```

根据客户端 IP 的哈希值决定转发到哪台后端。**同一个客户端 IP 的请求始终转发到同一台后端**（除非该后端不可用）。

适用场景：后端有 Session 状态（如 Tomcat 的 session sticky），需要同一个用户始终访问同一台后端。

> **踩坑提醒**：`ip_hash` 基于 IPv4 前 3 段或 IPv6 完整地址做哈希。如果大量用户在同一个 NAT 出口（如公司网络、校园网），他们的前 3 段 IP 相同，会被哈希到同一台后端，导致负载不均。更好的方案是用 `hash $cookie_xxx` 基于 cookie 做一致性哈希，或在应用层用 JWT 无状态设计。

**4. 最少连接（Least Connections）**

```nginx
upstream backend {
    least_conn;
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}
```

把请求转发给当前活跃连接数最少的服务器。适合请求处理时间差异较大的场景（有的请求快，有的慢）。

**5. 通用 Hash（一致性哈希）**

```nginx
upstream backend {
    hash $request_uri consistent;
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}
```

根据指定变量（如 `$request_uri`、`$cookie_xxx`）做哈希。加 `consistent` 参数启用一致性哈希——当后端服务器增减时，只有部分请求需要重新映射，而不是全部重新洗牌。

**6. 随机（Random）——1.15.1+**

```nginx
upstream backend {
    random;
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}

# 随机 + 最少连接（选 2 台中连接少的）
upstream backend {
    random two least_conn;
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}
```

随机选择后端。适用于多 Nginx 实例场景（避免每个实例都做相同的最少连接计算导致负载集中）。

**算法选择建议**：

| 场景 | 推荐算法 | 原因 |
|------|---------|------|
| 后端性能一致 | 轮询（默认） | 简单有效 |
| 后端性能不一致 | 加权轮询 | 按能力分配 |
| 后端有 Session 状态 | IP Hash 或一致性 Hash | 保持会话粘性 |
| 请求处理时间差异大 | 最少连接 | 避免慢请求堆积在某台 |
| 需要缓存命中率 | `hash $request_uri consistent` | 同 URL 始终到同一台，提高缓存命中 |
| 多 Nginx 实例 | random | 避免负载集中 |

> **面试加分点**：提到一致性哈希解决了"增减节点时大量请求重新映射"的问题。普通哈希增减一台后端，几乎所有请求的目标都会变；一致性哈希只有约 1/N 的请求受影响（N 为后端总数）。Nginx 的 `hash ... consistent` 使用 Ketama 算法实现。

---

## 二、配置相关（10题）

### Q11. location 匹配的优先级是什么？

**答案要点**：

location 匹配优先级是 Nginx 面试**必考题**。Nginx 的 location 匹配不是"按配置顺序从上到下"的，而是有固定的优先级规则。

**四种 location 修饰符**：

| 修饰符 | 含义 | 示例 |
|--------|------|------|
| `=` | 精确匹配 | `location = /favicon.ico` |
| `^~` | 前缀匹配（不继续正则） | `location ^~ /static/` |
| `~` | 区分大小写的正则匹配 | `location ~ \.php$` |
| `~*` | 不区分大小写的正则匹配 | `location ~* \.(jpg\|png)$` |
| 无修饰符 | 普通前缀匹配 | `location /api/` |

**匹配优先级（从高到低）**：

```
1. =    精确匹配（最高优先级，匹配到就停止）
       ↓ 如果没匹配到
2. ^~  前缀匹配（匹配到就停止，不再检查正则）
       ↓ 如果没匹配到
3. ~ / ~*  正则匹配（按配置文件中的顺序，第一个匹配的生效）
       ↓ 如果没有正则匹配到
4. 无修饰符  普通前缀匹配（最长前缀匹配，记住最长的那个）
```

**完整匹配流程**：

```
1. 先检查所有 = 精确匹配，如果命中，立即使用该 location，停止搜索。
2. 检查所有 ^~ 和无修饰符的前缀匹配，找到最长前缀匹配的那个。
3. 如果最长前缀匹配是 ^~，立即使用该 location，停止搜索（不检查正则）。
4. 如果最长前缀匹配是无修饰符的，记住它，继续检查正则。
5. 按配置文件中的顺序依次检查正则 location（~ 和 ~*），第一个匹配的生效。
6. 如果有正则匹配到，使用该正则 location。
7. 如果没有正则匹配到，使用第 4 步记住的那个最长前缀匹配。
```

**示例**：

```nginx
server {
    location = / {
        # ① 精确匹配 / → 只有请求 / 时命中
        # 优先级最高
    }

    location / {
        # ④ 所有请求的兜底
        # 优先级最低
    }

    location ^~ /static/ {
        # ② 前缀匹配 /static/ → 不再检查正则
        # /static/a.js 命中这里
    }

    location ~* \.(gif|jpg|jpeg|png)$ {
        # ③ 正则匹配图片后缀
        # /images/a.jpg 命中这里（如果前面没有 ^~ 拦截）
    }

    location ~ \.php$ {
        # ③ 正则匹配 .php 后缀
        # /api/test.php 命中这里
    }
}
```

**测试请求的匹配结果**：

| 请求 URI | 命中的 location | 原因 |
|----------|----------------|------|
| `/` | `location = /` | 精确匹配，最高优先级 |
| `/static/a.js` | `location ^~ /static/` | `^~` 前缀匹配，不再检查正则 |
| `/images/a.jpg` | `location ~* \.(gif\|jpg...)$` | 没有精确和 `^~` 匹配，正则匹配到 |
| `/api/test.php` | `location ~ \.php$` | 正则匹配到 |
| `/api/users` | `location /` | 无精确、无 `^~`、无正则匹配，用最长前缀 `/` |

> **踩坑提醒**：
> 1. 正则 location 之间是**按配置文件顺序**匹配的，第一个匹配的生效。如果有两个正则都能匹配同一个 URI，写在前面的生效。这在排查"为什么我的 location 没匹配到"时非常重要。
> 2. `^~` 的作用是"前缀匹配优先于正则"。如果你想让 `/static/` 下的请求不被正则 location 拦截（比如不被 `~ \.php$` 匹配到），就用 `^~`。
> 3. `location` 后面的 URI 是否带尾斜杠有区别：`location /api/` 只匹配 `/api/xxx`，不匹配 `/api`；`location /api` 同时匹配 `/api` 和 `/api/xxx`。

---

### Q12. root 和 alias 的区别？

**答案要点**：

`root` 和 `alias` 都用于指定静态文件的根目录，但它们拼接文件路径的方式不同。

**root——将 URI 完整拼接到 root 路径后面**：

```nginx
location /static/ {
    root /var/www;
}
# 请求 /static/img/a.jpg → 文件路径 /var/www/static/img/a.jpg
# root 路径 + 完整 URI
```

**alias——将 location 匹配的部分替换为 alias 路径**：

```nginx
location /static/ {
    alias /var/www/;
}
# 请求 /static/img/a.jpg → 文件路径 /var/www/img/a.jpg
# alias 路径 + (URI - location匹配部分)
```

**对比表**：

| 维度 | root | alias |
|------|------|-------|
| 路径拼接 | `root路径 + 完整URI` | `alias路径 + (URI - location匹配部分)` |
| 尾斜杠 | 不影响 | **影响**（alias 必须与 location 的尾斜杠一致） |
| 可用位置 | http、server、location | 仅 location |
| 是否替换 URI | 否（URI 保留） | 是（location 匹配部分被替换） |

**尾斜杠陷阱**（alias 最常见的坑）：

```nginx
# 正确：location 和 alias 都带尾斜杠
location /static/ {
    alias /var/www/;   # /static/a.jpg → /var/www/a.jpg ✓
}

# 错误：location 带斜杠，alias 不带
location /static/ {
    alias /var/www;    # /static/a.jpg → /var/wwwwa.jpg ✗ (拼接错误!)
}

# 正确：location 和 alias 都不带尾斜杠
location /static {
    alias /var/www;    # /static/a.jpg → /var/www/a.jpg ✓
}
```

> **踩坑提醒**：
> 1. **alias 的尾斜杠必须和 location 的尾斜杠一致**。这是最常见的配置错误，会导致文件路径拼接错误，返回 404。
> 2. **alias 有安全风险**：如果 `alias` 指向的路径是通过变量拼接的（如 `alias $some_path;`），可能导致目录穿越漏洞。详见踩坑记录 `#3.7`。
> 3. 一般建议：如果 root 和 alias 都能用，**优先用 root**，不容易出错。alias 主要用于"URI 路径和文件系统路径不一致"的场景。

---

### Q13. proxy_pass 带尾斜杠和不带尾斜杠有什么区别？

**答案要点**：

这是 Nginx 配置中**最容易踩坑**的问题之一。`proxy_pass` 的 URL 是否带尾斜杠（以及是否带 URI 路径），直接决定了转发给后端的请求 URI 是什么。

**规则总结**：

- `proxy_pass` **不带 URI**（只有 `host:port`）→ **保留原始 URI**，原样转发。
- `proxy_pass` **带 URI**（哪怕只是一个 `/`）→ **替换 location 匹配的部分**。

**四种情况对比**：

```nginx
# 情况1：proxy_pass 不带 URI（只有 host:port）
location /api/ {
    proxy_pass http://backend;     # 不带尾斜杠，不带路径
}
# 请求 /api/users → 后端收到 /api/users（原始 URI 保留）

# 情况2：proxy_pass 带尾斜杠（URI 为 /）
location /api/ {
    proxy_pass http://backend/;    # 带尾斜杠
}
# 请求 /api/users → 后端收到 /users（location 匹配的 /api/ 被替换为 /）

# 情况3：proxy_pass 带路径
location /api/ {
    proxy_pass http://backend/v1/; # 带路径
}
# 请求 /api/users → 后端收到 /v1/users（location 匹配的 /api/ 被替换为 /v1/）

# 情况4：proxy_pass 带路径但不带尾斜杠
location /api/ {
    proxy_pass http://backend/v1;  # 带路径，不带尾斜杠
}
# 请求 /api/users → 后端收到 /v1users（注意！没有斜杠分隔，通常不是你想要的）
```

**完整对比表**：

| location | proxy_pass | 请求 URI | 后端收到 | 说明 |
|----------|-----------|---------|---------|------|
| `/api/` | `http://backend` | `/api/users` | `/api/users` | 不带 URI，保留原始 |
| `/api/` | `http://backend/` | `/api/users` | `/users` | 带尾斜杠，替换 `/api/` |
| `/api/` | `http://backend/v1/` | `/api/users` | `/v1/users` | 带路径，替换 `/api/` 为 `/v1/` |
| `/api/` | `http://backend/v1` | `/api/users` | `/v1users` | 路径不带尾斜杠，拼接异常 |

**使用正则 location 时的限制**：

如果 location 使用了正则匹配（`~`、`~*`）或命名 location（`@name`），`proxy_pass` **不能带 URI**：

```nginx
# 正则 location → proxy_pass 不能带路径
location ~ \.php$ {
    proxy_pass http://backend;     # ✓ 只能写 host:port
    # proxy_pass http://backend/;  # ✗ 报错！正则 location 不允许带 URI
}
```

> **踩坑提醒**：这是面试高频题，也是生产环境最常见的 404 原因。后端框架（如 Spring Boot、Django）通常期望收到的是 `/users` 而不是 `/api/users`，所以如果用情况 2（带尾斜杠）去掉 `/api/` 前缀，后端路由才能正确匹配。如果后端需要保留 `/api/` 前缀，用情况 1（不带 URI）。详见踩坑记录 `#1.4`。

---

### Q14. rewrite 的 last 和 break 有什么区别？

**答案要点**：

`rewrite` 指令用于修改请求 URI。它有两个 flag：`last` 和 `break`，行为区别在于 rewrite 之后**是否继续执行后续的 rewrite 规则**以及**是否重新进行 location 匹配**。

**last**：

- 停止当前 location 中的 rewrite 规则处理。
- **重新发起 location 匹配**（用新的 URI 去走一遍 location 匹配流程）。
- 如果新 URI 匹配到了另一个 location，会在新 location 中继续处理。

**break**：

- 停止当前 location 中的 rewrite 规则处理。
- **不重新发起 location 匹配**，继续在当前 location 中执行后续指令（如 `proxy_pass`）。

**对比表**：

| flag | 停止 rewrite 规则 | 重新 location 匹配 | 继续当前 location 执行 |
|------|------------------|-------------------|----------------------|
| `last` | 是 | **是** | 否（跳到新 location） |
| `break` | 是 | **否** | 是 |

**示例说明**：

```nginx
server {
    # rewrite 链
    location /old/ {
        rewrite ^/old/(.*)$ /new/$1 last;
        # last → 停止当前 location，用 /new/xxx 重新匹配 location
        # 下面的 proxy_pass 不会执行
        proxy_pass http://backend;
    }

    location /new/ {
        # /old/xxx 被 rewrite 为 /new/xxx 后，匹配到这里
        proxy_pass http://backend;
    }
}
```

```nginx
server {
    location /api/ {
        rewrite ^/api/(.*)$ /$1 break;
        # break → 停止 rewrite，不重新匹配 location
        # 继续在当前 location 执行下面的 proxy_pass
        # 后端收到的是 /xxx（去掉了 /api/ 前缀）
        proxy_pass http://backend;
    }
}
```

**其他 flag**：

- `redirect`：返回 302 临时重定向（URL 会变，客户端可见）。
- `permanent`：返回 301 永久重定向（URL 会变，客户端可见，浏览器会缓存）。

```nginx
# 永久重定向到新域名
server {
    listen 80;
    server_name old.com;
    rewrite ^/(.*)$ https://new.com/$1 permanent;
}
```

**使用场景**：

| 场景 | 推荐 flag | 原因 |
|------|----------|------|
| 内部 URI 改写，需要走不同的 location | `last` | 改写后重新匹配 location |
| 内部 URI 改写，在当前 location 继续处理 | `break` | 改写后直接 proxy_pass |
| 需要客户端浏览器跳转 | `redirect` / `permanent` | 返回 3xx 状态码 |

> **踩坑提醒**：
> 1. `last` 可能导致**死循环**：如果 rewrite 后的新 URI 又匹配到同一个 location，且该 location 又有 rewrite 规则，会无限循环。Nginx 内部有保护机制，循环 10 次后返回 500 错误。
> 2. `rewrite` 在 `server` 块中执行时，如果 flag 是 `last`，会重新做 location 匹配；如果是 `break`，会跳过后续 server 级的 rewrite，直接进入 location 匹配。
> 3. 详见踩坑记录 `#1.5`。

---

### Q15. 为什么说 "if is evil"？应该怎么替代？

**答案要点**：

Nginx 官方文档明确指出 **"if is evil"**（if 是邪恶的），因为 `if` 指令在 `location` 块中的行为经常**不符合直觉**，容易导致意外结果。

**if 的问题**：

**1. if 不创建作用域**

你以为 `if` 块像编程语言中的 if 一样是一个作用域，但实际上 Nginx 的 `if` 不是。在 `if` 内部写的指令和外面的指令是在同一个 location 上下文中执行的，只是有条件地执行。

```nginx
# 有问题的配置
location / {
    set $do_proxy 0;
    if ($request_method = POST) {
        set $do_proxy 1;
    }
    if ($do_proxy = 1) {
        proxy_pass http://backend;
    }
    # 如果 $do_proxy 不等于 1，这里没有 proxy_pass
    # Nginx 会尝试作为静态文件处理，可能不是你想要的
}
```

**2. if 中某些指令行为异常**

`if` 块中只能安全地使用 `return` 和 `rewrite` 指令。其他指令（如 `proxy_pass`、`try_files`）在 `if` 中的行为可能不符合预期。

```nginx
# 危险！if 中的 proxy_pass 行为可能不符合预期
location / {
    if ($http_x_custom = "special") {
        proxy_pass http://special_backend;  # 可能不按你想的来
    }
    proxy_pass http://default_backend;
}
```

**3. 嵌套 if 不支持**

Nginx 不支持嵌套 `if`，也不支持 `if` 中的 `&&`、`||` 逻辑运算。

**正确替代方案**：

**方案1：用 `return` 替代（最安全）**

```nginx
# 安全：if 中只用 return
location / {
    if ($request_method != GET) {
        return 405;  # 只允许 GET 请求
    }
    # 继续正常处理
}
```

**方案2：用 `try_files` 替代文件存在性判断**

```nginx
# 错误：用 if 判断文件是否存在
location / {
    if (-f $request_filename) {
        # 有问题
    }
}

# 正确：用 try_files
location / {
    try_files $uri $uri/ /index.php?$query_string;
}
```

**方案3：用 `map` 替代复杂条件判断**

```nginx
# 用 map 做条件映射
map $http_host $backend {
    default    http://default_backend;
    "api.com"  http://api_backend;
    "www.com"  http://www_backend;
}

server {
    location / {
        proxy_pass $backend;  # 直接用 map 的结果
    }
}
```

**方案4：用多个 location 替代**

```nginx
# 错误：用 if 区分静态和动态
location / {
    if ($uri ~* \.(jpg|png|css|js)$) {
        root /var/www/static;
    }
    if ($uri ~* \.php$) {
        proxy_pass http://php_backend;
    }
}

# 正确：用多个 location
location ~* \.(jpg|png|css|js)$ {
    root /var/www/static;
}
location ~* \.php$ {
    proxy_pass http://php_backend;
}
```

**if 的安全使用场景**（这些是安全的）：

```nginx
# 1. if + return（安全）
if ($http_user_agent ~* "bot") {
    return 403;
}

# 2. if + rewrite ... last/break（安全）
if ($host = "old.com") {
    rewrite ^ https://new.com$request_uri permanent;
}

# 3. if + set（安全）
if ($request_method = POST) {
    set $do_proxy 1;
}
```

> **面试加分点**：引用 Nginx 官方的话——"The only 100% safe things which may be done inside if in a location context are: return ... and rewrite ... last."（在 location 的 if 中，唯一 100% 安全的操作是 return 和 rewrite last/break）。详见踩坑记录 `#1.7`。

---

### Q16. try_files 的作用是什么？

**答案要点**：

`try_files` 指令按顺序尝试多个文件/URI，返回第一个找到的。如果都找不到，使用最后一个参数（通常是 fallback URI 或状态码）。

**语法**：

```nginx
try_files file1 [file2 ...] (uri|=code);
```

**典型用途**：

**1. 单页应用（SPA）的 fallback**

```nginx
location / {
    root /var/www/html;
    try_files $uri $uri/ /index.html;
    # 1. 先尝试 $uri 对应的文件（如 /about → /var/www/html/about）
    # 2. 再尝试 $uri/ 目录（如 /css/ → /var/www/html/css/）
    # 3. 都找不到就返回 /index.html（Vue/React 等前端路由的入口）
}
```

这是最经典的用途。Vue/React 等单页应用的路由是前端处理的，`/about`、`/users` 等路径在服务器上没有对应的文件，需要 fallback 到 `index.html` 让前端路由处理。

**2. 前端控制器模式（PHP/框架入口）**

```nginx
location / {
    try_files $uri $uri/ /index.php?$query_string;
    # 找不到文件就交给 index.php 处理（Laravel/Symfony 等框架的入口）
}
```

**3. 静态文件优先，动态请求代理**

```nginx
location / {
    root /var/www;
    try_files $uri @backend;  # 找不到文件就走 @backend
}

location @backend {
    proxy_pass http://backend;
}
```

**4. 返回特定错误码**

```nginx
location / {
    try_files $uri =404;  # 找不到文件就返回 404
}
```

**关键点**：

- 最后一个参数**必须是**一个 URI（内部跳转）或 `=code`（返回状态码），不能是文件路径。
- `try_files` 是**内部跳转**，客户端的 URL 不会变（不像 rewrite 那样返回 3xx 重定向）。
- `$uri/` 表示尝试作为目录访问（会查找该目录下的 `index` 指令指定的文件）。

**为什么用 try_files 而不用 if**：

```nginx
# 错误：用 if 判断文件是否存在
if (-f $request_filename) {
    root /var/www;
}
if (!-f $request_filename) {
    proxy_pass http://backend;
}

# 正确：用 try_files
try_files $uri @backend;
```

`try_files` 是原生的文件检查机制，比 `if (-f ...)` 更高效、更安全。详见 Q15。

> **踩坑提醒**：`try_files` 中的内部跳转（如 `/index.html`）会**重新进行 location 匹配**。如果 `/index.html` 匹配到了另一个 location，会在新 location 中处理。这可能导致意外的循环或行为。确保 fallback URI 不会匹配到同一个 location 的 `try_files`。

---

### Q17. 如何配置 HTTP 跳转 HTTPS？

**答案要点**：

有两种常见方式：

**方式1：return 301（推荐，最简洁）**

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    # 所有 HTTP 请求永久跳转到 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com www.example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # HTTPS 配置...
}
```

**方式2：rewrite（传统方式）**

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    rewrite ^ https://$host$request_uri permanent;
}
```

**为什么推荐 `return 301` 而不是 `rewrite`**：

1. `return` 比 `rewrite` 更高效——`return` 直接返回 301 响应，不经过 rewrite 引擎的规则匹配。
2. `return` 语义更清晰——明确表示"返回一个重定向"。
3. `rewrite` 会先执行 rewrite 引擎的规则匹配，虽然结果一样，但多了一步开销。

**`$host` vs `$server_name`**：

```nginx
# 用 $host：保留客户端实际访问的域名（推荐）
return 301 https://$host$request_uri;

# 用 $server_name：固定使用配置中的 server_name
return 301 https://$server_name$request_uri;
```

- `$host`：客户端请求的 Host 头中的域名。更灵活，支持泛域名。
- `$server_name`：配置文件中 `server_name` 指令的值。固定值。
- 推荐用 `$host`，这样无论用户访问 `example.com` 还是 `www.example.com`，都能正确跳转。

**HSTS——更安全的跳转方案**：

单纯 HTTP→HTTPS 跳转存在中间人攻击风险（首次 HTTP 请求可能被劫持）。HSTS（HTTP Strict Transport Security）通过响应头告诉浏览器"以后只用 HTTPS 访问这个域名"：

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # 启用 HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    # max-age=31536000：一年内浏览器自动用 HTTPS
    # includeSubDomains：包含子域名
}
```

> **踩坑提醒**：
> 1. HSTS 一旦生效，浏览器在 `max-age` 时间内**强制**使用 HTTPS，无法回退到 HTTP。测试环境不要轻易启用 HSTS，或者用较短的 `max-age`（如 300 秒）。
> 2. `return 301` 必须放在 80 端口的 server 块中。如果放在 443 端口会导致无限重定向。

---

### Q18. 如何限制某个 IP 的访问？

**答案要点**：

Nginx 提供了 `allow` 和 `deny` 指令来基于 IP 控制访问：

**基本用法**：

```nginx
# 只允许特定 IP 访问
location /admin/ {
    allow 192.168.1.0/24;    # 允许内网
    allow 10.0.0.0/8;        # 允许 VPN 网段
    deny all;                # 拒绝其他所有 IP
    proxy_pass http://backend;
}

# 拒绝特定 IP，允许其他
location / {
    deny 123.45.67.89;       # 拒绝恶意 IP
    deny 123.45.67.0/24;     # 拒绝恶意 IP 段
    allow all;               # 允许其他所有 IP
    proxy_pass http://backend;
}
```

**规则**：

- `allow` 和 `deny` 按从上到下的顺序匹配，**第一个匹配的规则生效**，后面的不再检查。
- 支持 IP 地址和 CIDR 网段。
- `allow all` / `deny all` 表示允许/拒绝所有。

**匹配流程**：

```
请求进来 → 检查客户端 IP
  → 匹配 allow 192.168.1.0/24？
     → 是：允许访问，停止检查
     → 否：继续
  → 匹配 allow 10.0.0.0/8？
     → 是：允许访问，停止检查
     → 否：继续
  → 匹配 deny all？
     → 是：拒绝访问（返回 403），停止检查
```

**作用域**：`allow`/`deny` 可以用在 `http`、`server`、`location`、`limit_except` 块中。子块继承父块的规则。

**结合 limit_except 限制 HTTP 方法**：

```nginx
location /api/ {
    # 只允许 POST 请求来自内网
    limit_except GET {
        allow 192.168.1.0/24;
        deny all;
    }
    proxy_pass http://backend;
}
```

**用 map 实现动态 IP 白名单**：

如果 IP 列表经常变化，用 `geo` 指令更灵活：

```nginx
http {
    geo $allowed_ip {
        default        0;    # 默认不允许
        192.168.1.0/24 1;    # 允许内网
        10.0.0.0/8     1;    # 允许 VPN
    }

    server {
        location /admin/ {
            if ($allowed_ip = 0) {
                return 403;
            }
            proxy_pass http://backend;
        }
    }
}
```

> **踩坑提醒**：
> 1. 如果 Nginx 在反向代理后面（如前面有 CDN 或负载均衡器），`$remote_addr` 拿到的是代理的 IP，不是真实客户端 IP。需要配置 `set_real_ip_from` + `real_ip_header` 才能拿到真实 IP。详见踩坑记录 `#5.4`。
> 2. `allow`/`deny` 只能做简单的 IP 过滤，如果需要更复杂的访问控制（如基于时间、基于请求频率），需要结合 `limit_req` 或 OpenResty Lua。

---

### Q19. limit_req 的 burst 和 nodelay 是什么意思？

**答案要点**：

`limit_req` 用于请求限流（基于令牌桶算法）。`burst` 和 `nodelay` 控制突发流量的处理行为。

**基本配置**：

```nginx
http {
    # 定义限流规则：每个 IP 每秒最多 1 个请求
    limit_req_zone $binary_remote_addr zone=mylimit:10m rate=1r/s;

    server {
        location /api/ {
            limit_req zone=mylimit burst=5 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

**参数解释**：

| 参数 | 含义 |
|------|------|
| `rate=1r/s` | 平均速率：每秒 1 个请求（令牌桶每秒生成 1 个令牌） |
| `burst=5` | 突发容量：允许排队的最大请求数为 5 |
| `nodelay` | 突发请求不延迟，立即处理（默认突发请求会延迟处理） |

**三种场景对比**：

**场景1：只有 rate，没有 burst**

```nginx
limit_req zone=mylimit;
# rate=1r/s, burst=0
```

每秒只允许 1 个请求通过，第 2 个请求立刻返回 503。非常严格，不适合真实场景。

**场景2：有 burst，没有 nodelay**

```nginx
limit_req zone=mylimit burst=5;
# rate=1r/s, burst=5
```

令牌桶容量为 5。突发请求可以排队，但会**延迟处理**：

- 第 1 秒来了 6 个请求：第 1 个立即处理，第 2~6 个排队。
- 第 2 秒：处理排队的第 2 个请求。
- 第 3 秒：处理排队的第 3 个请求。
- ...以此类推，每秒处理 1 个。

问题是排队的请求会被**延迟**，用户感受到的是响应变慢。

**场景3：有 burst + nodelay（推荐）**

```nginx
limit_req zone=mylimit burst=5 nodelay;
# rate=1r/s, burst=5, nodelay
```

令牌桶容量为 5，但突发请求**不延迟**，立即处理：

- 第 1 秒来了 6 个请求：前 6 个（1 个 rate + 5 个 burst）**立即处理**。
- 第 7 个请求：令牌用完了，立刻返回 503。
- 第 2 秒：令牌桶恢复了 1 个令牌，可以处理 1 个新请求。

`nodelay` 的效果：突发请求立即处理（不延迟），但总量受 `rate + burst` 限制。这是最接近"限流但不影响用户体验"的配置。

**图示理解**：

```
没有 burst:     |█|█|█|█|█|  → 第2个开始就503
                   503 503 503 503

burst=5:        |█|█|█|█|█|█|  → 前6个排队，每秒处理1个（延迟）
                立即 排队等待...

burst=5 nodelay: |█|█|█|█|█|█|  → 前6个立即处理，第7个503
                 立即 立即 立即 立即 立即 503
```

> **踩坑提醒**：
> 1. `limit_req` 的 `rate` 是**每秒**或**每分钟**的速率，不是瞬时并发数。如果你想限制"同时最多 100 个并发连接"，应该用 `limit_conn`，不是 `limit_req`。
> 2. `burst` 不要设太大——burst 越大，突发流量越大，后端压力越大。通常 burst 设为 rate 的 2~5 倍。
> 3. `limit_req_zone` 中的 `zone=mylimit:10m` 分配 10MB 共享内存，大约能存 16 万个 IP 的状态。如果 IP 数量超过这个值，会有精度问题。

---

### Q20. proxy_set_header Host $host 和 $proxy_host 的区别？

**答案要点**：

反向代理时，Nginx 默认会把发给后端的 `Host` 头改为 upstream 中定义的地址。通过 `proxy_set_header` 可以控制这个行为。

**两个变量的区别**：

| 变量 | 值 | 示例 |
|------|-----|------|
| `$host` | 客户端请求的 Host 头（原始域名） | `example.com` |
| `$proxy_host` | upstream 中定义的 `host:port` | `backend:8080` |

**对比示例**：

```nginx
upstream backend {
    server 192.168.1.1:8080;
}

server {
    listen 80;
    server_name example.com;

    location /api/ {
        proxy_pass http://backend;

        # 情况1：不设置 proxy_set_header Host
        # → 后端收到的 Host: 192.168.1.1:8080（默认行为，= $proxy_host）

        # 情况2：传递原始域名
        proxy_set_header Host $host;
        # → 后端收到的 Host: example.com

        # 情况3：传递 upstream 名称
        proxy_set_header Host $proxy_host;
        # → 后端收到的 Host: 192.168.1.1:8080
    }
}
```

**什么时候用哪个**：

**用 `$host`（传递原始域名）——大多数场景**：

```nginx
proxy_set_header Host $host;
```

后端需要知道客户端访问的是哪个域名时使用。典型场景：

- 后端基于 Host 做虚拟主机路由（如 Tomcat、Spring Boot 的多域名配置）。
- 后端生成绝对 URL（如重定向 URL、静态资源 URL）需要用到正确域名。
- 后端日志需要记录客户端访问的域名。

**用 `$proxy_host`（传递 upstream 地址）——少数场景**：

```nginx
proxy_set_header Host $proxy_host;  # 或不设置（这是默认行为）
```

后端只认自己配置的地址时使用。典型场景：

- 后端是 PHP-FPM，通过 fastcgi 通信，Host 头不重要。
- 后端配置了基于 IP 的虚拟主机，只认 `192.168.1.1:8080`。

**完整的代理头设置（推荐配置）**：

```nginx
location /api/ {
    proxy_pass http://backend;

    # 传递原始 Host
    proxy_set_header Host $host;

    # 传递真实客户端 IP
    proxy_set_header X-Real-IP $remote_addr;

    # 传递 X-Forwarded-For 链
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # 传递原始协议（http 或 https）
    proxy_set_header X-Forwarded-Proto $scheme;

    # 传递原始 Host（有些后端框架认这个头）
    proxy_set_header X-Forwarded-Host $host;
}
```

> **踩坑提醒**：
> 1. 如果不设置 `proxy_set_header Host $host`，后端拿到的 Host 是 upstream 的 IP:port，可能导致后端生成的 URL 错误（如重定向到 `http://192.168.1.1:8080/users` 而不是 `http://example.com/users`）。
> 2. `$http_host` 和 `$host` 有细微区别：`$http_host` 是原始 Host 头的值（始终带端口号，如 `example.com:8080`），`$host` 会去掉默认端口且做了小写处理。大多数情况下用 `$host` 更好。
> 3. 详见踩坑记录 `#3.5`。

---

## 三、HTTPS/安全（8题）

### Q21. HTTPS 握手过程简述

**答案要点**：

HTTPS = HTTP + TLS。TLS 握手建立加密通道后，HTTP 通信在这个加密通道上进行。以 TLS 1.2 为例：

**TLS 1.2 握手流程**：

```
客户端                                          服务器
  |                                               |
  | 1. ClientHello                                |
  |   (TLS版本, 支持的加密套件, 客户端随机数)        |
  | ────────────────────────────────────────────→ |
  |                                               |
  | 2. ServerHello                                |
  |   (选定的加密套件, 服务器随机数)                 |
  |   Certificate (服务器证书)                     |
  |   ServerKeyExchange (如果需要)                 |
  |   ServerHelloDone                             |
  | ←──────────────────────────────────────────── |
  |                                               |
  | [客户端验证证书:                                |
  |  - 检查证书链是否可信(到根CA)                    |
  |  - 检查域名是否匹配                             |
  |  - 检查证书是否过期                             |
  |  - 检查证书是否被吊销(CRL/OCSP)]                |
  |                                               |
  | 3. ClientKeyExchange                          |
  |   (生成 Pre-Master Secret, 用服务器公钥加密)     |
  |   ChangeCipherSpec                            |
  |   Finished (加密握手摘要)                      |
  | ────────────────────────────────────────────→ |
  |                                               |
  | [双方根据:                                      |
  |  客户端随机数 + 服务器随机数 + Pre-Master Secret |
  |  计算出相同的 Master Secret → 会话密钥]          |
  |                                               |
  | 4. ChangeCipherSpec                           |
  |   Finished (加密握手摘要)                      |
  | ←──────────────────────────────────────────── |
  |                                               |
  | ========= 加密通道建立完成, 开始 HTTP 通信 ========= |
```

**核心步骤总结**：

1. **ClientHello**：客户端发送支持的 TLS 版本、加密套件列表、客户端随机数。
2. **ServerHello + Certificate**：服务器选定加密套件、发送服务器随机数和证书。
3. **客户端验证证书**：检查证书链、域名、有效期、吊销状态。
4. **密钥交换**：客户端生成 Pre-Master Secret，用服务器公钥加密发送。
5. **双方计算会话密钥**：用客户端随机数 + 服务器随机数 + Pre-Master Secret 计算出对称加密密钥。
6. **Finished**：双方发送加密的握手摘要，确认握手没有被篡改。
7. **加密通信**：之后用对称密钥加密 HTTP 数据。

**TLS 1.3 的简化**（Nginx 1.25+ 默认支持）：

TLS 1.3 将握手从 2-RTT 减少到 1-RTT（甚至支持 0-RTT 恢复），流程更简洁：

```
1. ClientHello + KeyShare (客户端直接发送密钥交换材料)
2. ServerHello + KeyShare + Certificate + Finished (服务器一次性返回所有内容)
3. Client Finished
→ 1-RTT 完成握手
```

**Nginx 中的 TLS 配置**：

```nginx
server {
    listen 443 ssl;
    http2 on;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # 推荐：只允许 TLS 1.2 和 1.3
    ssl_protocols TLSv1.2 TLSv1.3;

    # 推荐的加密套件
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;  # TLS 1.3 中由客户端选择，TLS 1.2 中建议 on

    # 会话恢复（减少握手开销）
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;  # 出于安全考虑，建议关闭 session tickets
}
```

> **面试加分点**：提到 TLS 握手中用了两种加密——**非对称加密**（RSA/ECDHE）用于安全交换密钥，**对称加密**（AES）用于后续数据传输。非对称加密计算开销大，不适合大量数据；对称加密速度快但需要双方先安全协商出密钥。TLS 握手就是用非对称加密安全地协商出对称密钥。

---

### Q22. 证书链不完整会有什么问题？

**答案要点**：

**什么是证书链**：

HTTPS 证书不是单独一张证书，而是一条链：

```
根证书 (Root CA)  ← 操作系统/浏览器内置，自签名
   ↓ 签发
中间证书 (Intermediate CA)
   ↓ 签发
终端证书 (你的域名证书)  ← 你从 CA 申请到的证书
```

浏览器验证证书时，需要从终端证书追溯到根证书。如果服务器只返回终端证书，没有返回中间证书，浏览器就无法构建完整的信任链。

**证书链不完整的问题**：

1. **部分客户端报错**：Android、Java、curl（不带 `-k`）、部分旧浏览器会报"证书不可信"或"unable to find valid certification path"。因为它们没有内置中间证书，无法验证终端证书。
2. **桌面浏览器可能正常**：Chrome、Firefox 会自动从 CA 服务器下载中间证书（AIA fetching），所以桌面浏览器可能不报错——但这增加了延迟，且不是所有客户端都支持 AIA fetching。
3. **安全风险**：AIA fetching 过程可能被中间人攻击利用。

**如何检查证书链是否完整**：

```bash
# 用 openssl 检查
openssl s_client -connect example.com:443 -showcerts

# 如果输出中只有一个 Certificate（终端证书），说明中间证书缺失
# 如果有两个或更多 Certificate（终端 + 中间），说明链完整

# 在线工具：https://www.ssllabs.com/ssltest/
# 如果评级不是 A，检查 "Chain issues" 是否有 "Incomplete"
```

**如何修复**：

将终端证书和中间证书合并为一个文件：

```bash
# cat 终端证书 + 中间证书 → fullchain.pem
cat cert.pem chain.pem > fullchain.pem

# Nginx 配置中使用 fullchain.pem
# ssl_certificate /etc/nginx/ssl/fullchain.pem;  ← 正确
# ssl_certificate /etc/nginx/ssl/cert.pem;       ← 错误！只有终端证书
```

**Let's Encrypt 的处理**：

```bash
# certbot 生成的文件
cert.pem        # 终端证书
chain.pem       # 中间证书
fullchain.pem   # 终端 + 中间（Nginx 用这个）
privkey.pem     # 私钥
```

```nginx
ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;  # 正确
ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
```

> **踩坑提醒**：
> 1. 证书链不完整是最常见的 HTTPS 配置错误。桌面浏览器能正常访问不代表所有客户端都正常——一定要用 SSL Labs 测试或用 curl/openssl 从其他机器验证。
> 2. 证书顺序很重要：fullchain.pem 中终端证书必须在**最前面**，中间证书在后面。如果顺序反了，部分客户端会报错。
> 3. 详见踩坑记录 `#4.1`。

---

### Q23. 什么是 HSTS？什么时候启用？

**答案要点**：

**HSTS（HTTP Strict Transport Security）** 是一个 HTTP 响应头，告诉浏览器："在指定时间内，只能用 HTTPS 访问这个域名，即使用户手动输入 http:// 也要自动跳转到 https://"。

**为什么需要 HSTS**：

没有 HSTS 时，用户输入 `http://example.com` → 服务器返回 301 跳转到 `https://example.com`。但这个**首次 HTTP 请求**可能被中间人劫持——中间人可以返回一个假的页面，用户在不知情的情况下泄露信息。

HSTS 解决这个问题：浏览器第一次收到 HSTS 头后，在 `max-age` 时间内，**浏览器自身**会阻止 HTTP 访问，直接在本地转为 HTTPS，不需要发 HTTP 请求到服务器。

**配置方法**：

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # 启用 HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

| 参数 | 含义 |
|------|------|
| `max-age=31536000` | HSTS 有效期，31536000 秒 = 1 年 |
| `includeSubDomains` | HSTS 也应用于所有子域名 |
| `preload` | 申请加入浏览器内置的 HSTS 预加载列表（见下文） |

**什么时候启用 HSTS**：

**前提条件**（必须全部满足）：

1. 网站已经**全站 HTTPS**——所有页面、所有资源（图片、CSS、JS、API）都通过 HTTPS 提供。
2. 没有**混合内容**（Mixed Content）——HTTPS 页面中没有引用 HTTP 资源。
3. 所有子域名也支持 HTTPS（如果用了 `includeSubDomains`）。
4. SSL 证书有效且不会很快过期。

**启用步骤**：

1. 先用较短的 `max-age`（如 300 秒 = 5 分钟）测试，确认没有问题。
2. 逐步增加 `max-age`：1 天 → 1 周 → 1 个月 → 1 年。
3. 确认无误后，考虑申请 HSTS preload。

**HSTS Preload**：

浏览器维护一个内置的 HSTS 域名列表（https://hstspreload.org）。加入这个列表后，即使用户**从未访问过**你的网站，浏览器也会强制使用 HTTPS。这解决了"首次访问仍可能被劫持"的问题。

```nginx
# 申请 preload 需要加 preload 参数
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

> **踩坑提醒**：
> 1. HSTS 是**不可逆**的——一旦浏览器记录了 HSTS，在 `max-age` 时间内无法回退到 HTTP。如果网站还需要支持 HTTP 访问（如某些旧客户端），不要启用 HSTS。
> 2. `includeSubDomains` 要非常谨慎——如果某个子域名还不支持 HTTPS，加了 `includeSubDomains` 会导致该子域名完全无法访问。
> 3. HSTS 头只在 HTTPS 响应中有效——HTTP 响应中的 HSTS 头会被浏览器忽略（防止中间人注入虚假 HSTS 头）。
> 4. 详见踩坑记录 `#4.2`。

---

### Q24. 什么是 OCSP Stapling？

**答案要点**：

**OCSP（Online Certificate Status Protocol）** 是一个用于检查证书是否被吊销的协议。浏览器在 TLS 握手时可以额外向 CA 发送 OCSP 请求，确认服务器证书是否仍然有效。

**OCSP 的问题**：

1. **隐私泄露**：浏览器向 CA 查询证书状态时，CA 知道了用户正在访问哪个网站。
2. **性能开销**：浏览器需要额外发一个 HTTP 请求到 CA 的 OCSP 服务器，增加页面加载延迟。
3. **可用性问题**：如果 CA 的 OCSP 服务器挂了或响应慢，浏览器要么等待（超时），要么跳过验证（安全隐患）。

**OCSP Stapling（OCSP 装订）的解决方案**：

由**服务器**（Nginx）定期去 CA 获取 OCSP 响应，在 TLS 握手时直接把 OCSP 响应"装订"在证书后面发给客户端。客户端不需要自己去查 CA。

```
没有 Stapling:
  浏览器 → 服务器 (获取证书)
  浏览器 → CA 的 OCSP 服务器 (查询证书是否被吊销)  ← 额外请求，慢，泄露隐私

有 Stapling:
  Nginx → CA 的 OCSP 服务器 (定期获取 OCSP 响应，缓存)
  浏览器 → 服务器 (获取证书 + OCSP 响应)  ← 一次搞定，快，保护隐私
```

**Nginx 配置 OCSP Stapling**：

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;  # 必须包含中间证书
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # 开启 OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # 指定信任的 CA 证书（用于验证 OCSP 响应）
    ssl_trusted_certificate /etc/nginx/ssl/chain.pem;

    # 指定 DNS 解析器（OCSP 请求需要解析 CA 的域名）
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

**验证 OCSP Stapling 是否生效**：

```bash
# 用 openssl 检查
openssl s_client -connect example.com:443 -status

# 如果看到 "OCSP Response Status: successful" 说明 Stapling 生效
# 如果看到 "OCSP response: no response sent" 说明未生效
```

> **踩坑提醒**：
> 1. `ssl_stapling` 需要 `fullchain.pem`（包含中间证书），否则 Nginx 无法获取 OCSP 响应——因为 OCSP 响应是对终端证书的，但验证需要中间证书。
> 2. Nginx 启动后不会立刻有 OCSP 缓存，需要等几秒钟才会去 CA 获取。如果刚 reload 就测试，可能看到"no response sent"，等一会儿再测。
> 3. `resolver` 是必须的——Nginx 需要解析 CA 的 OCSP 服务器域名。如果 Nginx 运行在容器中且没有配置 DNS，OCSP Stapling 会失败。
> 4. 详见踩坑记录 `#4.4`。

---

### Q25. 如何隐藏 Nginx 版本号？

**答案要点**：

默认情况下，Nginx 会在响应头和错误页中暴露版本号：

```
Server: nginx/1.30.4
```

暴露版本号的安全风险：攻击者可以根据版本号查找该版本已知的漏洞进行针对性攻击。

**隐藏版本号**：

```nginx
http {
    server_tokens off;  # 隐藏版本号
}
```

效果：`Server: nginx`（不显示版本号）。

**完全隐藏 Server 头**：

`server_tokens off` 只隐藏版本号，仍然显示 `Server: nginx`。要完全去掉或修改 `Server` 头，需要：

**方案1：用 `more_clear_headers` 模块（第三方模块，推荐）**

```nginx
# 需要安装 headers-more-nginx-module
more_clear_headers 'Server';
more_clear_headers 'X-Powered-By';
```

**方案2：重新编译 Nginx，修改源码**

修改 `src/http/ngx_http_header_filter_module.c` 中的版本字符串，重新编译。

**方案3：用 OpenResty 的 header_filter_by_lua**

```nginx
header_filter_by_lua_block {
    ngx.header["Server"] = nil  -- 删除 Server 头
    -- 或伪装成其他服务器
    -- ngx.header["Server"] = "Microsoft-IIS/10.0"
}
```

**隐藏错误页中的版本号**：

```nginx
http {
    server_tokens off;

    # 自定义错误页，不暴露 Nginx 信息
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;

    location = /404.html {
        root /usr/share/nginx/html;
        internal;
    }
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
```

> **踩坑提醒**：
> 1. 隐藏版本号是**安全加固**的一部分，但不能替代真正的安全措施（如及时升级、WAF 等）。"安全通过隐蔽"（Security through obscurity）不是可靠的防御手段。
> 2. `server_tokens off` 也会影响错误页（404、500 等页面底部的 `nginx/1.30.4` 字样会变成 `nginx`）。
> 3. 详见踩坑记录 `#3.1`。

---

### Q26. Nginx 如何防止目录穿越？

**答案要点**：

目录穿越（Directory Traversal）是指攻击者通过构造特殊 URL（如 `../../../etc/passwd`）访问到 Web 根目录之外的文件。

**Nginx 的防护机制**：

Nginx 在内部会对 URI 做规范化处理，自动处理 `..` 和重复的 `/`：

- `/../etc/passwd` → Nginx 会规范化为 `/etc/passwd`，然后尝试在 root 目录下查找。
- 如果 root 是 `/var/www`，最终查找的路径是 `/var/www/etc/passwd`，不会穿越到 `/etc/passwd`。

**危险的配置——alias + 正则导致目录穿越**：

```nginx
# 危险配置！
location /files {
    alias /var/www/data/;  # location 不带尾斜杠，alias 带尾斜杠
}
# 请求 /files../etc/passwd
# Nginx 会将 /files 替换为 /var/www/data/
# 结果路径：/var/www/data/../etc/passwd → /var/etc/passwd ← 穿越成功！
```

**修复方法**：

```nginx
# 正确：location 和 alias 都带尾斜杠
location /files/ {
    alias /var/www/data/;
}
# 请求 /files/../etc/passwd → /var/www/data/../etc/passwd
# Nginx 规范化后 → /var/etc/passwd ← 仍然可能穿越？
# 不，Nginx 会在 alias 替换后再次规范化路径

# 更安全：用 root 替代 alias
location /files/ {
    root /var/www/data;  # /files/a.txt → /var/www/data/files/a.txt
}
```

**更危险的配置——变量拼接 root/alias**：

```nginx
# 极度危险！用户可控变量直接拼接到文件路径
location /download/ {
    alias /var/www/files/$arg_name;  # $arg_name 是查询参数
}
# 请求 /download/?name=../../../etc/passwd → /var/www/files/../../../etc/passwd
```

**防护建议**：

1. **优先用 `root` 而不是 `alias`**——root 不会替换 URI，不容易出错。
2. **alias 的尾斜杠必须和 location 一致**——详见 Q12。
3. **不要用用户可控变量拼接文件路径**——如果必须用变量，要校验或过滤 `..`。
4. **用 `internal` 指令防止直接访问内部 location**。

```nginx
# internal 标记的 location 只能通过内部跳转访问，不能从外部直接访问
location /protected/ {
    internal;
    root /var/www/protected;
}
```

> **踩坑提醒**：Nginx 本身对基本的 `..` 穿越是有防护的（会在 URL 解析阶段规范化路径），但 `alias` 配置不当或变量拼接可能绕过这个防护。定期用安全扫描工具检查 Nginx 配置。详见踩坑记录 `#3.2` 和 `#3.7`。

---

### Q27. HTTP/2 和 HTTP/3 的区别？Nginx 如何配置？

**答案要点**：

**HTTP/2 的核心特性**：

- **多路复用**：一个 TCP 连接上可以同时传输多个请求/响应，不需要像 HTTP/1.1 那样排队（队头阻塞）。
- **头部压缩**：用 HPACK 算法压缩 HTTP 头部，减少开销。
- **二进制分帧**：HTTP/1.1 是文本协议，HTTP/2 是二进制协议，解析更快。
- **服务器推送**：服务器可以主动推送资源（如 CSS、JS）到客户端。

**HTTP/2 的问题**：底层仍然是 TCP，TCP 层有队头阻塞——如果某个 TCP 包丢失，所有在这个连接上的 HTTP/2 流都会被阻塞，直到丢包重传完成。

**HTTP/3 的核心改进**：

- **基于 QUIC（UDP）**：不使用 TCP，使用基于 UDP 的 QUIC 协议。
- **解决了 TCP 队头阻塞**：QUIC 在传输层实现多路复用，一个流丢包不影响其他流。
- **更快的连接建立**：QUIC 将传输层握手和 TLS 握手合并，1-RTT 甚至 0-RTT 建立连接（TCP + TLS 1.3 需要至少 2-RTT）。
- **连接迁移**：客户端 IP 变化（如从 WiFi 切到 4G）时，QUIC 连接不断开（基于 Connection ID 而非 IP）。

**对比表**：

| 特性 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------|----------|--------|--------|
| 传输层 | TCP | TCP | QUIC (UDP) |
| 多路复用 | 不支持 | 支持（应用层） | 支持（传输层） |
| 队头阻塞 | 有（应用层） | 有（TCP 层） | 无 |
| 头部压缩 | 不支持 | HPACK | QPACK |
| 连接建立 RTT | 1-3 RTT | 1-3 RTT | 0-1 RTT |
| 加密 | 可选 | 必须（实践中） | 必须（内置 TLS） |

**Nginx 配置 HTTP/2**（Nginx 1.25.1+ 的新语法）：

```nginx
# Nginx 1.25.1+ 推荐写法（http2 作为独立指令）
server {
    listen 443 ssl;
    http2 on;              # 开启 HTTP/2

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
}

# 旧写法（1.25.1 之前，仍然兼容但不推荐）
server {
    listen 443 ssl http2;  # 在 listen 指令上加 http2
    ...
}
```

**Nginx 配置 HTTP/3**（Nginx 1.25.0+，需要编译时加 `--with-http_v3_module`）：

```nginx
server {
    # 同时监听 TCP 和 UDP
    listen 443 ssl;
    listen 443 quic reuseport;   # HTTP/3 over QUIC (UDP)
    http2 on;
    http3 on;                     # 开启 HTTP/3

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.3;       # HTTP/3 需要 TLS 1.3

    # 告诉客户端支持 HTTP/3（浏览器会优先尝试 HTTP/3）
    add_header Alt-Svc 'h3=":443"; ma=86400' always;
}
```

**Alt-Svc 头的作用**：

浏览器第一次用 HTTP/2 连接，收到 `Alt-Svc: h3=":443"` 头后，知道服务器支持 HTTP/3。下次访问时浏览器会尝试用 HTTP/3（UDP 443），如果成功就用 HTTP/3，失败则回退到 HTTP/2。

> **踩坑提醒**：
> 1. HTTP/3 需要 UDP 443 端口。很多云厂商的负载均衡器/防火墙默认只放行 TCP，需要额外放行 UDP。
> 2. Nginx 的 `listen 443 quic reuseport;` 中 `reuseport` 是推荐的——让多个 worker 各自有 UDP socket，避免惊群问题。
> 3. HTTP/3 目前还在早期阶段，客户端支持不完善。建议同时提供 HTTP/2 和 HTTP/3，用 `Alt-Svc` 让客户端自行选择。详见踩坑记录 `#4.6`。

---

### Q28. 什么是 SNI？

**答案要点**：

**SNI（Server Name Indication）** 是 TLS 协议的一个扩展，允许客户端在 TLS 握手**开始时**就告诉服务器它要访问的域名。服务器根据这个域名返回对应的证书。

**为什么需要 SNI**：

在 TLS 握手过程中，证书是在 ServerHello 阶段发送的，此时 HTTP 请求还没有开始（HTTP 的 Host 头还没有发送）。如果一个 IP 上有多个域名（虚拟主机），每个域名有不同的证书，服务器不知道该返回哪个证书。

没有 SNI 的情况：

```
客户端 → 服务器：ClientHello (没有域名信息)
服务器 → 客户端：Certificate (返回哪个证书？服务器不知道客户端要访问哪个域名)
```

结果：服务器只能返回**默认**证书。如果客户端访问的不是默认域名的站点，证书的域名不匹配，浏览器报错。

有 SNI 的情况：

```
客户端 → 服务器：ClientHello + SNI (域名: example.com)
服务器 → 客户端：Certificate (返回 example.com 的证书)  ← 正确！
```

**Nginx 中的 SNI**：

Nginx 天然支持 SNI——每个 `server` 块配置自己的证书，Nginx 根据 TLS 握手中的 SNI 选择对应的 server 块：

```nginx
# 一个 IP 上两个域名，各自有独立证书
server {
    listen 443 ssl;
    server_name a.com;
    ssl_certificate     /etc/nginx/ssl/a.com.pem;
    ssl_certificate_key /etc/nginx/ssl/a.com.key;
    # ...
}

server {
    listen 443 ssl;
    server_name b.com;
    ssl_certificate     /etc/nginx/ssl/b.com.pem;
    ssl_certificate_key /etc/nginx/ssl/b.com.key;
    # ...
}
```

Nginx 根据 TLS ClientHello 中的 SNI 值匹配 `server_name`，返回对应的证书。

**SNI 的限制——同一个 IP 多域名共用 443 端口时的证书选择**：

如果不支持 SNI（极少数旧客户端），Nginx 会使用**第一个**（默认）server 块的证书。

**默认 server 的指定**：

```nginx
# 指定默认的 HTTPS server（SNI 不匹配时使用）
server {
    listen 443 ssl default_server;
    server_name _;
    ssl_certificate     /etc/nginx/ssl/default.pem;
    ssl_certificate_key /etc/nginx/ssl/default.key;
    return 444;  # 拒绝未匹配的请求
}
```

**测试 SNI**：

```bash
# 用 openssl 测试，-servername 指定 SNI
openssl s_client -connect 192.168.1.1:443 -servername a.com
# 应该返回 a.com 的证书

openssl s_client -connect 192.168.1.1:443 -servername b.com
# 应该返回 b.com 的证书

# 用 curl 测试
curl -v --resolve a.com:443:192.168.1.1 https://a.com/
curl -v --resolve b.com:443:192.168.1.1 https://b.com/
```

> **面试加分点**：提到 **ESNI（Encrypted SNI）/ ECH（Encrypted Client Hello）**——SNI 本身是明文传输的，中间人可以看到客户端要访问的域名。ESNI/ECH 是 TLS 1.3 的扩展，加密 SNI 信息，保护用户隐私。不过目前部署率还很低。

---

## 四、性能优化（8题）

### Q29. Nginx 性能调优的常见手段有哪些？

**答案要点**：

Nginx 性能调优可以从以下几个层面进行：

**1. 进程与连接配置**

```nginx
# worker 进程数 = CPU 核数
worker_processes auto;

# 每个 worker 的最大连接数
worker_connections 10240;

# worker 进程的最大文件描述符
worker_rlimit_nofile 65535;
```

同时需要调整系统级限制：

```bash
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535

# /etc/sysctl.conf
fs.file-max = 1000000
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
```

**2. 事件模型优化**

```nginx
events {
    use epoll;           # Linux 用 epoll
    worker_connections 10240;
    multi_accept on;     # 一次接受所有新连接（而不是一次一个）
}
```

**3. 网络优化**

```nginx
http {
    sendfile on;          # 零拷贝，传输静态文件
    tcp_nopush on;        # 配合 sendfile，等数据包攒够再发
    tcp_nodelay on;       # 禁用 Nagle 算法，小数据立即发送

    keepalive_timeout 65;        # 客户端长连接超时
    keepalive_requests 1000;     # 一个长连接最多处理多少请求

    # 缓冲区优化
    client_body_buffer_size 16k;
    client_max_body_size 50m;
    client_header_buffer_size 4k;
    large_client_header_buffers 4 16k;
}
```

**4. Gzip 压缩**

```nginx
http {
    gzip on;
    gzip_min_length 1024;          # 小于 1KB 不压缩
    gzip_comp_level 4;             # 压缩级别 1-9，4 是性能和压缩比的平衡
    gzip_types text/plain text/css application/json application/javascript;
    gzip_vary on;                  # 添加 Vary: Accept-Encoding 头
}
```

**5. upstream 长连接复用**

```nginx
upstream backend {
    server 192.168.1.1:8080;
    keepalive 32;  # 到后端的长连接池
}

server {
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;                    # 必须 1.1 才能复用
        proxy_set_header Connection "";            # 清除 Connection 头，启用长连接
    }
}
```

**6. 静态资源缓存**

```nginx
# 浏览器缓存
location ~* \.(jpg|png|gif|css|js)$ {
    expires 30d;                    # 浏览器缓存 30 天
    add_header Cache-Control "public, immutable";
}

# Nginx 代理缓存
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 10m;     # 200 响应缓存 10 分钟
    proxy_cache_valid 404 1m;      # 404 缓存 1 分钟
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    proxy_pass http://backend;
}
```

**7. SSL 优化**

```nginx
server {
    listen 443 ssl;
    ssl_session_cache shared:SSL:10m;   # SSL 会话缓存
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_buffer_size 4k;                  # TLS 记录大小，小值降低首字节延迟
}
```

**8. 日志优化**

```nginx
http {
    # 高并发时可以关闭 access_log 减少磁盘 IO
    # access_log off;

    # 或使用缓冲写入
    access_log /var/log/nginx/access.log combined buffer=32k flush=5s;

    # 只记录错误，不记录正常访问
    # location /health {
    #     access_log off;
    # }
}
```

**调优检查清单**：

| 层面 | 调优项 | 效果 |
|------|--------|------|
| 进程 | `worker_processes auto` | 充分利用多核 |
| 连接 | `worker_connections 10240+` | 提高并发上限 |
| 文件描述符 | `worker_rlimit_nofile 65535` | 避免连接耗尽 |
| IO | `sendfile on` + `tcp_nopush on` | 零拷贝，减少 CPU 开销 |
| 网络 | `keepalive_timeout` + `keepalive_requests` | 减少连接建立开销 |
| 压缩 | `gzip on` | 减少带宽，加速传输 |
| 后端连接 | `upstream keepalive` | 减少到后端的 TCP 开销 |
| 缓存 | `proxy_cache` | 减少后端压力 |
| SSL | `ssl_session_cache` | 减少握手开销 |
| 日志 | `access_log buffer` | 减少磁盘 IO |

> **面试加分点**：提到调优要有**测量**支撑——先压测（ab/wrk）找到瓶颈，针对性优化，而不是盲目调参数。每次只改一个参数，对比效果。

---

### Q30. 什么是 reuseport？有什么好处？

**答案要点**：

`reuseport` 是 Linux 3.9+ 引入的 `SO_REUSEPORT` socket 选项，允许多个进程/线程绑定**同一个 IP + 端口**，由内核做负载均衡。

**没有 reuseport 的情况**：

```
所有 worker 共享同一个 listen socket
  → 新连接到来 → 所有 worker 被 epoll 唤醒（惊群问题）
  → 但只有一个 worker 能 accept 成功
  → 其他 worker 白跑一趟

Nginx 用 accept_mutex 解决：同一时刻只让一个 worker accept
  → 但 accept_mutex 本身有锁竞争开销
  → 在极高并发下，accept_mutex 成为瓶颈
```

**有 reuseport 的情况**：

```
每个 worker 有自己独立的 listen socket（同一 IP:端口）
  → 新连接到来 → 内核直接分发给某个 worker
  → 被选中的 worker 独自 accept，没有惊群
  → 内核层面做负载均衡，效率极高
```

**Nginx 配置 reuseport**：

```nginx
# 方式1：在 listen 指令上加 reuseport
server {
    listen 80 reuseport;       # 每个 worker 有独立的 socket
    # listen 443 ssl reuseport;
}

# 方式2：配合 worker_processes
worker_processes auto;         # 8 核 → 8 个 worker
# 每个 worker 独立 bind 80 端口（通过 reuseport）
```

**reuseport 的好处**：

1. **消除惊群问题**：内核直接把连接分发给某个 worker，不需要所有 worker 竞争 accept。
2. **更好的多核扩展性**：没有 accept_mutex 锁竞争，每个 worker 独立处理自己的连接，性能随 CPU 核数线性扩展。
3. **更均匀的负载分配**：内核的 hash 算法将连接均匀分配给各 worker。

**reuseport 的性能提升**：

根据 Nginx 官方博客的测试，在高并发场景下（如数万并发连接），reuseport 可以带来 **2~3 倍**的性能提升，尤其是在多核服务器上。

**注意事项**：

1. **只在一个 server 上设置 reuseport**：如果有多个 server 监听同一端口，只在一个上设 `reuseport` 即可。
2. **worker 数量固定**：reuseport 的 socket 数量等于 worker 数。如果 reload 时 worker 数量变化，Nginx 会正确处理。
3. **不是所有场景都适合**：如果并发量不高（如几百并发），accept_mutex 足够，reuseport 的提升不明显。

**对比 accept_mutex 和 reuseport**：

| 特性 | accept_mutex | reuseport |
|------|-------------|-----------|
| 工作方式 | 锁竞争，一次一个 worker accept | 每个 worker 独立 socket，内核分配 |
| 惊群 | 有（用锁避免） | 无 |
| 多核扩展性 | 一般（锁竞争随核数增加） | 好（无锁） |
| Linux 版本要求 | 无 | 3.9+ |
| 适用场景 | 中低并发 | 高并发 |

> **踩坑提醒**：reuseport 和 `accept_mutex off` 通常一起使用。如果开了 reuseport，建议关掉 `accept_mutex`：
> ```nginx
> events {
>     accept_mutex off;  # 配合 reuseport 使用
> }
> ```

---

### Q31. upstream keepalive 的作用？如何配置？

**答案要点**：

**作用**：默认情况下，Nginx 每次向后端发请求都会新建一个 TCP 连接，请求完成后关闭。这在高并发场景下会导致大量 TCP 连接建立/关闭的开销（三次握手 + 四次挥手），还可能产生大量 TIME_WAIT 状态的连接。

`upstream keepalive` 让 Nginx 到后端保持**长连接池**，复用 TCP 连接处理多个请求，避免反复建连。

**性能影响**：

- 减少 TCP 三次握手开销（每个连接约 1 RTT）。
- 减少 TIME_WAIT 连接数量。
- 降低后端服务器的连接压力。
- 对于 HTTPS 后端，还减少 TLS 握手开销。

**配置方法**：

```nginx
http {
    upstream backend {
        server 192.168.1.1:8080;
        server 192.168.1.2:8080;

        keepalive 32;  # 保持 32 个空闲长连接
        # keepalive 32 表示连接池中最多保留 32 个空闲连接
        # 超过 32 个空闲连接时，多余的会被关闭
    }

    server {
        location /api/ {
            proxy_pass http://backend;

            # 以下三行是必须的配置！
            proxy_http_version 1.1;        # HTTP/1.1 才支持 keepalive
            proxy_set_header Connection ""; # 清除 Connection: close 头
            # 这样 Nginx 不会在请求头中发 Connection: close
            # 后端也不会在响应后关闭连接
        }
    }
}
```

**关键配置解释**：

| 配置 | 作用 |
|------|------|
| `keepalive 32` | 连接池大小，保留 32 个空闲连接 |
| `proxy_http_version 1.1` | 必须用 HTTP/1.1（HTTP/1.0 默认不支持 keepalive） |
| `proxy_set_header Connection ""` | 清除 Connection 头，默认 Nginx 会发 `Connection: close`，必须清除才能复用 |

**缺少哪一行会怎样**：

- 没有 `keepalive 32`：不会维护连接池，每次都新建连接。
- 没有 `proxy_http_version 1.1`：默认用 HTTP/1.0，不支持 keepalive。
- 没有 `proxy_set_header Connection ""`：Nginx 默认发 `Connection: close`，后端收到后会在响应后关闭连接，无法复用。

**keepalive 数量如何设置**：

- `keepalive` 的值应该略大于 QPS × 后端响应时间（秒）。
- 例如：QPS = 1000，后端平均响应时间 50ms = 0.05s → 连接数 ≈ 1000 × 0.05 = 50，设为 `keepalive 64`。
- 不是越大越好——连接太多占用后端资源，太少起不到复用效果。

**验证 keepalive 是否生效**：

```bash
# 查看 Nginx 到后端的连接数
ss -tnp | grep :8080 | grep -c ESTAB

# 如果连接数稳定在 keepalive 值附近，说明复用生效
# 如果连接数不断波动（频繁建立/关闭），说明配置有问题

# 查看后端的 TIME_WAIT 数量
ss -tn | grep :8080 | grep -c TIME-WAIT
# 开启 keepalive 后 TIME_WAIT 应大幅减少
```

> **踩坑提醒**：
> 1. `keepalive 32` 不是"最大并发数"，而是"空闲连接池大小"。高峰期可以超过这个数（新建临时连接），空闲时保留这么多。
> 2. 如果后端也配置了 keepalive 超时（如 Tomcat 的 `keepAliveTimeout`），确保后端的超时 > Nginx 的超时，否则后端先关闭连接会导致 Nginx 报错。
> 3. 详见踩坑记录 `#2.3`。

---

### Q32. worker_connections 如何计算最大连接数？

**答案要点**：

Nginx 的最大并发连接数由 `worker_processes` × `worker_connections` 决定，但实际可用连接数还要考虑连接类型。

**计算公式**：

```
最大连接数 = worker_processes × worker_connections
```

但这个总数需要分配给不同类型的连接：

**作为反向代理时**：

每个客户端请求会占用**两个**连接：

1. 客户端 → Nginx 的连接
2. Nginx → 后端服务器的连接

所以：

```
最大并发请求数 = worker_processes × worker_connections / 2
```

**作为静态 Web 服务器时**：

每个请求只占**一个**连接（客户端 → Nginx）：

```
最大并发请求数 = worker_processes × worker_connections
```

**具体计算**：

```nginx
worker_processes auto;        # 假设 4 核 CPU → 4 个 worker
worker_connections 10240;     # 每个 worker 10240 连接
```

- 作为静态服务器：最大连接 = 4 × 10240 = 40960
- 作为反向代理：最大请求 = 4 × 10240 / 2 = 20480

**系统级限制检查**：

`worker_connections` 不能超过系统级的文件描述符限制。每个连接占用一个文件描述符：

```bash
# 查看当前用户的文件描述符限制
ulimit -n

# 查看系统级最大文件描述符
cat /proc/sys/fs/file-max
```

如果 `worker_connections 10240` 但 `ulimit -n` 只有 1024，Nginx 会报错 `socket() failed (24: Too many open files)`。

**解决方法**：

```nginx
# nginx.conf 中调大 worker 的文件描述符限制
worker_rlimit_nofile 65535;

events {
    worker_connections 10240;
}
```

```bash
# 系统级调大（/etc/security/limits.conf）
* soft nofile 65535
* hard nofile 65535

# 或在 systemd 服务文件中设置
# /usr/lib/systemd/system/nginx.service
[Service]
LimitNOFILE=65535
```

**计算示例**：

假设需要支持 10000 并发请求（反向代理场景）：

```
需要连接数 = 10000 × 2 = 20000
需要 worker_connections = 20000 / worker_processes

如果 worker_processes = 4:
  worker_connections = 20000 / 4 = 5000
  设置为 10240（留余量）

如果 worker_processes = 8:
  worker_connections = 20000 / 8 = 2500
  设置为 5120（留余量）
```

> **踩坑提醒**：
> 1. `worker_connections` 是**每个 worker** 的连接数，不是总连接数。总连接数 = worker_processes × worker_connections。
> 2. 反向代理场景要除以 2（一个请求占两个连接），这是面试常考的"陷阱"。
> 3. 修改 `worker_connections` 需要 restart 才能生效（不是 reload）。
> 4. 详见踩坑记录 `#2.2`。

---

### Q33. sendfile 的工作原理？什么是零拷贝？

**答案要点**：

**传统文件传输（不用 sendfile）**：

当 Nginx 要把一个静态文件发送给客户端时，传统方式需要 4 次上下文切换 + 4 次数据拷贝：

```
1. Nginx 调用 read() → 用户态→内核态切换
   → DMA 从磁盘读取文件到内核缓冲区
   → CPU 将数据从内核缓冲区拷贝到用户空间缓冲区
   → 内核态→用户态切换（返回到 Nginx）

2. Nginx 调用 write() → 用户态→内核态切换
   → CPU 将数据从用户空间缓冲区拷贝到 socket 缓冲区
   → DMA 将数据从 socket 缓冲区拷贝到网卡
   → 内核态→用户态切换（返回到 Nginx）
```

数据流：磁盘 → 内核缓冲区 → 用户空间 → socket 缓冲区 → 网卡

问题：数据从内核空间拷贝到用户空间再拷贝回内核空间（socket 缓冲区），这两次拷贝是多余的——Nginx 只是转发数据，不需要在用户空间处理数据内容。

**sendfile 零拷贝**：

`sendfile()` 系统调用让数据**直接从内核缓冲区到 socket 缓冲区**，不经过用户空间：

```
1. Nginx 调用 sendfile() → 用户态→内核态切换
   → DMA 从磁盘读取文件到内核缓冲区
   → 内核直接将文件描述符和偏移信息写入 socket 缓冲区
   → DMA 将数据从内核缓冲区直接拷贝到网卡
   → 内核态→用户态切换（返回到 Nginx）
```

数据流：磁盘 → 内核缓冲区 → 网卡

**对比**：

| 维度 | 传统方式 | sendfile |
|------|---------|----------|
| 上下文切换 | 4 次 | 2 次 |
| 数据拷贝 | 4 次（2 次 DMA + 2 次 CPU） | 3 次（2 次 DMA + 1 次 CPU）或更少 |
| 用户空间参与 | 是（数据经过用户空间） | 否（数据不经过用户空间） |
| CPU 开销 | 高（CPU 参与拷贝） | 低（DMA 直接拷贝） |

**零拷贝的含义**：

"零拷贝"不是说完全没有数据拷贝（DMA 拷贝仍然存在），而是**CPU 不参与数据拷贝**（零次 CPU 拷贝），数据搬运全部由 DMA（Direct Memory Access）硬件完成，CPU 只负责发指令。

**Nginx 配置**：

```nginx
http {
    sendfile on;       # 开启 sendfile 零拷贝
    tcp_nopush on;     # 配合 sendfile，等数据攒够一个完整包再发
}
```

`tcp_nopush` 的作用：开启后，Nginx 会等响应头和响应体凑够一定大小后一次性发送，减少网络包数量。对于大文件传输特别有效。

**sendfile 的适用场景**：

- **静态文件传输**：Nginx 直接从磁盘读文件发给客户端。sendfile 的最大受益场景。
- **不适用于反向代理**：反向代理的响应来自后端（已经通过网络读到了用户空间），不需要 sendfile。

> **面试加分点**：提到 Linux 2.4+ 的 sendfile 支持 **SG-DMA（Scatter-Gather DMA）**，数据甚至不需要从内核缓冲区拷贝到 socket 缓冲区——内核只把文件描述符和长度信息传给 socket，DMA 直接从内核缓冲区读数据发到网卡。这就是真正的"零拷贝"。

---

### Q34. proxy_cache 如何配置缓存？

**答案要点**：

`proxy_cache` 让 Nginx 缓存后端的响应，后续相同的请求直接从 Nginx 缓存返回，不需要转发到后端。这大幅减少后端压力和响应延迟。

**完整配置**：

```nginx
http {
    # 1. 定义缓存路径和参数
    proxy_cache_path /var/cache/nginx
        levels=1:2              # 目录层级，1:2 表示两级目录（如 /var/cache/nginx/a/bc/...）
        keys_zone=api_cache:10m # 共享内存区域名和大小（10m 约 16 万个 key）
        max_size=1g             # 缓存最大磁盘占用
        inactive=60m            # 60 分钟未被访问的缓存自动清除
        use_temp_path=off;      # 临时文件直接写在缓存目录中（减少一次文件拷贝）

    server {
        location /api/ {
            proxy_pass http://backend;

            # 2. 启用缓存
            proxy_cache api_cache;

            # 3. 定义缓存 key（默认是 $scheme$proxy_host$request_uri）
            proxy_cache_key "$scheme$request_method$host$request_uri";

            # 4. 定义缓存有效期
            proxy_cache_valid 200 10m;    # 200 响应缓存 10 分钟
            proxy_cache_valid 301 1h;     # 301 缓存 1 小时
            proxy_cache_valid 404 1m;     # 404 缓存 1 分钟（防止缓存穿透）
            proxy_cache_valid any 1m;     # 其他响应缓存 1 分钟

            # 5. 缓存降级：后端异常时使用旧缓存
            proxy_cache_use_stale error timeout invalid_header updating
                                 http_500 http_502 http_503 http_504;

            # 6. 后端挂了时，用旧缓存响应（不返回错误）
            proxy_cache_background_update on;
            proxy_cache_lock on;          # 同一请求同时只有一个去后端取数据

            # 7. 添加响应头显示缓存命中情况
            add_header X-Cache-Status $upstream_cache_status;
        }
    }
}
```

**`$upstream_cache_status` 的值**：

| 值 | 含义 |
|----|------|
| `MISS` | 缓存未命中，请求转发到后端 |
| `HIT` | 缓存命中，直接返回缓存 |
| `EXPIRED` | 缓存已过期，请求转发到后端 |
| `STALE` | 后端异常，返回旧缓存 |
| `UPDATING` | 缓存正在更新，返回旧缓存 |
| `REVALIDATED` | 缓存通过条件请求验证仍有效 |
| `BYPASS` | 绕过缓存（配置了 `proxy_cache_bypass`） |

**绕过缓存的条件**：

```nginx
location /api/ {
    proxy_cache api_cache;

    # 以下情况绕过缓存，直接请求后端
    proxy_cache_bypass $http_cache_control $arg_nocache;

    # 以下情况不写入缓存
    proxy_no_cache $http_authorization;

    proxy_pass http://backend;
}
```

**手动清除缓存**：

```nginx
# 方式1：删除缓存目录中的文件
rm -rf /var/cache/nginx/*

# 方式2：用第三方模块 ngx_cache_purge
location /purge/ {
    allow 127.0.0.1;
    deny all;
    proxy_cache_purge api_cache $scheme$proxy_host$request_uri;
}

# 方式3：用 Lua 实现（OpenResty）
# 通过 lua_shared_dict 存缓存元数据，灵活控制
```

> **踩坑提醒**：
> 1. 默认情况下，带 `Set-Cookie` 响应头的请求不会被缓存（安全考虑）。如果你确定要缓存，需要用 `proxy_ignore_headers Set-Cookie;` 忽略。
> 2. `proxy_cache_valid` 也可以由后端通过 `Cache-Control` 头控制——如果后端返回 `Cache-Control: max-age=300`，Nginx 会用后端的值。用 `proxy_ignore_headers Cache-Control Expires;` 可以忽略后端的缓存指令。
> 3. 缓存 key 的设计很关键——如果 key 太粗（如只用 `$request_uri`），可能缓存了不应该缓存的内容（如带认证的请求）；如果太细（如加上 `$http_authorization`），缓存命中率会很低。

---

### Q35. 如何排查 502 错误？

**答案要点**：

**502 Bad Gateway** 的含义：Nginx 作为反向代理，无法从后端服务器获得有效响应。通常意味着后端服务挂了或不可达。

**排查步骤**：

**第一步：确认后端服务是否存活**

```bash
# 检查后端进程是否在运行
ps aux | grep backend

# 检查后端端口是否在监听
ss -tlnp | grep 8080

# 直接请求后端（绕过 Nginx）
curl -v http://192.168.1.1:8080/api/test
```

如果后端进程不存在或端口没监听 → 后端服务挂了，重启后端。

**第二步：检查 Nginx 错误日志**

```bash
# 查看 error.log 中的 502 相关错误
sudo tail -50 /var/log/nginx/error.log
```

常见错误信息：

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `connect() failed (111: Connection refused)` | 后端端口没监听 | 重启后端服务 |
| `connect() failed (113: No route to host)` | 网络不通/防火墙 | 检查网络和防火墙 |
| `upstream timed out` | 后端响应太慢 | 调大 `proxy_read_timeout` |
| `upstream sent invalid header` | 后端返回了非法 HTTP 响应 | 检查后端日志 |
| `no live upstreams` | 所有后端都被标记为不可用 | 检查 `max_fails`/`fail_timeout` 配置 |

**第三步：检查后端服务日志**

```bash
# 看后端是否有崩溃、OOM 等
journalctl -u backend -n 50

# 看后端应用日志
tail -50 /var/log/backend/app.log

# 检查系统是否 OOM killed
dmesg | grep -i oom
```

**第四步：检查网络连通性**

```bash
# 从 Nginx 服务器 ping 后端
ping 192.168.1.1

# 从 Nginx 服务器 telnet 后端端口
telnet 192.168.1.1 8080

# 检查防火墙规则
iptables -L -n | grep 8080
```

**第五步：检查 Nginx 配置**

```nginx
# 常见配置问题导致 502：

# 1. upstream 地址写错了
upstream backend {
    server 192.168.1.1:8080;  # 确认 IP 和端口正确
}

# 2. 后端只监听了 127.0.0.1，Nginx 用外部 IP 连不上
# 后端需要监听 0.0.0.0:8080 而不是 127.0.0.1:8080

# 3. proxy_pass 超时太短
location /api/ {
    proxy_connect_timeout 5s;    # 连接超时
    proxy_read_timeout 60s;      # 读取超时
    proxy_send_timeout 60s;      # 发送超时
    proxy_pass http://backend;
}

# 4. 后端是 HTTPS 但 Nginx 用 HTTP 连
location /api/ {
    proxy_pass https://backend;  # 确认协议正确
}
```

**第六步：检查后端资源是否耗尽**

```bash
# 后端服务器文件描述符是否耗尽
ss -s  # 查看连接数

# 后端服务器内存是否耗尽
free -m

# 后端服务器 CPU 是否 100%
top
```

**常见 502 原因总结**：

| 原因 | 占比 | 排查方法 |
|------|------|---------|
| 后端服务挂了 | 50% | `ps` + `ss` 检查进程和端口 |
| 后端 OOM | 15% | `dmesg \| grep oom` |
| 网络不通/防火墙 | 15% | `ping` + `telnet` |
| 后端监听地址不对 | 10% | 检查后端 `bind` 地址 |
| Nginx 配置错误 | 5% | 检查 `proxy_pass` 地址和协议 |
| 后端响应超时 | 5% | 调大 `proxy_read_timeout` |

> **踩坑提醒**：
> 1. Docker 网络中，后端容器和 Nginx 容器必须在同一个 Docker 网络中才能通信。用 `docker network inspect` 确认。
> 2. 如果后端偶尔 502（不是持续），可能是后端在高负载时来不及处理新连接。检查后端的 `backlog` 设置和 `max_connections` 配置。

---

### Q36. 如何排查 504 错误？

**答案要点**：

**504 Gateway Timeout** 的含义：Nginx 作为反向代理，在指定时间内没有收到后端的响应。后端服务存活（连接建立了），但处理太慢。

**502 vs 504 的区别**：

| 错误 | 含义 | 原因 |
|------|------|------|
| 502 | 无法连接后端或后端返回无效响应 | 后端挂了、端口没监听、网络不通 |
| 504 | 连上了后端但响应超时 | 后端太慢、数据库查询慢、死锁 |

**排查步骤**：

**第一步：确认是哪个超时**

Nginx 有三个超时配置：

```nginx
location /api/ {
    proxy_connect_timeout 5s;    # 连接后端的超时（连不上 → 502）
    proxy_send_timeout 60s;      # 发送请求给后端的超时
    proxy_read_timeout 60s;      # 等待后端响应的超时（超时 → 504）
    proxy_pass http://backend;
}
```

504 通常是 `proxy_read_timeout` 超时——Nginx 连上了后端，发了请求，但在 `proxy_read_timeout` 时间内没收到响应。

**第二步：检查 Nginx 错误日志**

```bash
sudo tail -50 /var/log/nginx/error.log
```

504 相关的错误信息：

```
upstream timed out (110: Connection timed out) while reading response header from upstream
```

这条日志明确说：在等待后端响应头时超时了。

**第三步：检查后端为什么慢**

```bash
# 1. 看后端日志，确认请求是否到达后端
tail -f /var/log/backend/app.log

# 2. 如果请求到达了后端，但处理很慢，可能是：
#    - 数据库查询慢
#    - 调用外部 API 慢
#    - CPU/内存耗尽
#    - 线程池满

# 3. 检查后端资源
top          # CPU 和内存
ss -tnp      # 连接数
# 如果是 Java 应用
jstack <pid> # 看线程在干什么
# 如果是 Python 应用
# 检查 GIL 是否被占住、有没有死循环
```

**第四步：直接请求后端，测量响应时间**

```bash
# 直接请求后端（绕过 Nginx），看响应时间
time curl -v http://192.168.1.1:8080/api/slow-endpoint

# 如果后端响应也慢 → 问题在后端
# 如果后端响应快但 Nginx 504 → 问题在 Nginx 配置或网络
```

**第五步：调整超时配置**

如果后端确实需要较长时间处理（如大文件上传、复杂计算），可以适当调大超时：

```nginx
location /api/upload {
    proxy_read_timeout 300s;     # 5 分钟
    proxy_send_timeout 300s;
    proxy_pass http://backend;
}

# 或者对特定慢接口单独设置
location /api/report/generate {
    proxy_read_timeout 600s;     # 10 分钟（报表生成很慢）
    proxy_pass http://backend;
}
```

**第六步：检查后端的 keepalive 超时冲突**

```nginx
# Nginx 配置了 upstream keepalive
upstream backend {
    server 192.168.1.1:8080;
    keepalive 32;
}

# 如果后端的 keepalive 超时（如 Tomcat keepAliveTimeout=20s）
# 比 Nginx 的空闲连接检查更短
# 后端可能先关闭连接，Nginx 尝试复用时连接已失效 → 504
```

解决方法：确保后端的 keepalive 超时 > Nginx 的 `keepalive_timeout`。

**常见 504 原因总结**：

| 原因 | 排查方法 |
|------|---------|
| 后端处理慢（数据库慢查询） | 看后端慢查询日志 |
| 后端线程池满 | 看后端线程池状态 |
| 后端调用外部 API 超时 | 看后端日志中的外部调用 |
| proxy_read_timeout 太短 | 检查 Nginx 配置 |
| keepalive 超时冲突 | 对比 Nginx 和后端的超时配置 |
| 后端 OOM 导致 GC 频繁 | `jstat`/`top` 检查 GC 和内存 |
| 网络延迟高 | `ping` 和 `traceroute` |

> **踩坑提醒**：
> 1. 调大 `proxy_read_timeout` 只是"治标"——让用户等更久而不是直接 504。**治本**是优化后端性能。如果只是临时缓解，要确保有进度提示或异步处理机制。
> 2. 如果频繁 504，考虑将慢接口改为异步处理：Nginx 立即返回 202 Accepted，后端异步处理，客户端轮询或 WebSocket 获取结果。
> 3. 可以用 `proxy_next_upstream timeout` 配置：某个后端超时后，自动尝试下一个后端（前提是有多个后端）。

---

## 五、OpenResty/Lua（8题）

### Q37. OpenResty 和 Nginx 的关系？

**答案要点**：

**OpenResty 是一个基于 Nginx 的 Web 平台**，由中国人章亦春（agentzh）发起，核心是在 Nginx 中嵌入 LuaJIT（Lua 的即时编译器），让开发者可以用 Lua 脚本扩展 Nginx 的功能。

**关系图**：

```
OpenResty = Nginx + LuaJIT + 一系列 lua-resty-* 库

┌─────────────────────────────────┐
│         OpenResty               │
│  ┌───────────────────────────┐  │
│  │     Nginx (核心)          │  │  ← 标准 Nginx 的所有功能
│  │  ┌─────────────────────┐  │  │
│  │  │  ngx_http_lua_module│  │  │  ← 在 Nginx 中嵌入 Lua 引擎
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │     LuaJIT (Lua 引擎)    │  │  ← 高性能 Lua 即时编译器
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  lua-resty-* 库生态       │  │  ← redis/mysql/http 客户端等
│  │  (resty.redis, resty.http │  │
│  │   resty.core, etc.)       │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**关键区别**：

| 维度 | Nginx | OpenResty |
|------|-------|-----------|
| 核心 | Nginx 官方源码 | Nginx + 第三方模块（主要是 ngx_lua） |
| 配置 | 纯声明式配置 | 配置 + Lua 脚本 |
| 扩展性 | C 模块（需重新编译） | Lua 脚本（无需重新编译） |
| 动态能力 | 弱（配置变更需 reload） | 强（Lua 可在运行时动态处理） |
| 性能 | 极高（纯 C） | 极高（LuaJIT 接近 C 的性能） |
| 适用场景 | 反向代理、负载均衡、静态服务 | API 网关、WAF、动态路由、业务逻辑 |

**OpenResty 能做什么 Nginx 做不了的事**：

1. **动态路由**：根据请求内容（header、body、cookie）动态决定转发到哪个后端。
2. **认证鉴权**：在 Nginx 层做 JWT 验证、OAuth 校验，不需要转发到后端。
3. **限流**：比 `limit_req` 更灵活的限流（如基于用户 ID、基于 API 路径）。
4. **WAF**：在 Nginx 层做 Web 应用防火墙（SQL 注入检测、XSS 防护）。
5. **动态负载均衡**：根据后端健康状态动态调整权重。
6. **缓存**：用 `lua_shared_dict` 做内存缓存，比 `proxy_cache` 更灵活。
7. **API 聚合**：一个请求并行调用多个后端 API，合并结果返回。

**OpenResty 示例**：

```nginx
# 在 Nginx 配置中直接写 Lua 代码
location /hello {
    content_by_lua_block {
        ngx.say("Hello, OpenResty!")
        ngx.say("Your IP is: ", ngx.var.remote_addr)
    }
}

# 访问 Redis 做缓存
location /api/user {
    access_by_lua_block {
        local redis = require "resty.redis"
        local red = redis:new()
        red:set_timeout(1000)
        local ok, err = red:connect("127.0.0.1", 6379)
        if not ok then
            ngx.log(ngx.ERR, "failed to connect to redis: ", err)
            return
        end
        local res, err = red:get("user:" .. ngx.var.arg_id)
        if res and res ~= ngx.null then
            ngx.say(res)
            return ngx.exit(200)
        end
        -- 缓存未命中，继续转发到后端
    }
    proxy_pass http://backend;
}
```

> **面试加分点**：提到 OpenResty 的核心设计理念是**"在 Nginx 的事件循环中执行 Lua"**——Lua 代码运行在 Nginx worker 进程中，通过 cosocket（协程套接字）实现非阻塞 IO，不会阻塞 worker 的事件循环。这就是为什么 OpenResty 能保持 Nginx 级别的性能。

---

### Q38. Lua 在 Nginx 中有哪些执行阶段？

**答案要点**：

Nginx 处理请求有 11 个阶段（phase），OpenResty 的 Lua 代码可以挂载到其中大部分阶段执行。每个阶段有不同的用途和限制。

**Nginx 的 11 个处理阶段**：

```
1. post-read         → 读取请求头后
2. server-rewrite     → server 级 rewrite
3. find-config        → location 匹配
4. rewrite            → location 级 rewrite
5. post-rewrite       → rewrite 后处理
6. preaccess          → 访问前准备（如 limit_req）
7. access             → 访问控制（allow/deny）
8. post-access        → 访问控制后
9. precontent         → 内容生成前（try_files）
10. content           → 内容生成（proxy_pass/root）
11. log               → 日志记录
```

**OpenResty 的 Lua 执行阶段指令**：

| 指令 | 对应 Nginx 阶段 | 用途 | 能否输出响应 | 能否 proxy_pass |
|------|----------------|------|-------------|----------------|
| `init_by_lua` | Nginx 启动时 | 初始化全局变量、预加载模块 | 否 | 否 |
| `init_worker_by_lua` | worker 启动时 | 初始化 worker 级数据、定时任务 | 否 | 否 |
| `ssl_certificate_by_lua` | TLS 握手时 | 动态选择证书 | 否 | 否 |
| `set_by_lua` | rewrite | 设置变量 | 否 | 否 |
| `rewrite_by_lua` | rewrite | URL 重写 | 否 | 否 |
| `access_by_lua` | access | 访问控制、认证 | 可以（ngx.exit） | 可以（改 proxy_pass） |
| `content_by_lua` | content | 生成响应内容 | 是 | 否（自己生成内容） |
| `header_filter_by_lua` | 响应头过滤 | 修改/删除响应头 | 否 | 否 |
| `body_filter_by_lua` | 响应体过滤 | 修改响应体 | 否 | 否 |
| `log_by_lua` | log | 记录日志、上报指标 | 否 | 否 |
| `balancer_by_lua` | 负载均衡 | 动态选择后端 | 否 | 否 |

**常用阶段详解**：

**1. access_by_lua（最常用）**：认证、限流、访问控制

```nginx
location /api/ {
    access_by_lua_block {
        -- 检查 JWT
        local auth_header = ngx.var.http_authorization
        if not auth_header then
            ngx.exit(401)
        end
        -- 验证 JWT...
    }
    proxy_pass http://backend;
}
```

**2. content_by_lua**：直接生成响应（不转发给后端）

```nginx
location /time {
    content_by_lua_block {
        ngx.say('{"time": "', os.time(), '"}')
        ngx.header["Content-Type"] = "application/json"
    }
}
```

**3. header_filter_by_lua**：修改响应头

```nginx
header_filter_by_lua_block {
    ngx.header["Server"] = nil           -- 删除 Server 头
    ngx.header["X-Custom"] = "value"     -- 添加自定义头
}
```

**4. log_by_lua**：记录请求日志、上报指标

```nginx
log_by_lua_block {
    local metrics = require "metrics"
    metrics.record({
        uri = ngx.var.uri,
        status = ngx.status,
        request_time = ngx.var.request_time,
    })
}
```

**5. balancer_by_lua**：动态负载均衡

```nginx
upstream backend {
    server 0.0.0.0;  -- 占位，实际的 peer 由 Lua 决定
    balancer_by_lua_block {
        local balancer = require "ngx.balancer"
        -- 动态选择后端地址
        balancer.set_current_peer("192.168.1." .. math.random(1,3), 8080)
    }
}
```

**阶段执行顺序**：

```
请求进来
  → post-read
  → rewrite（set_by_lua, rewrite_by_lua）
  → access（access_by_lua）
  → content（content_by_lua 或 proxy_pass）
  → header_filter（header_filter_by_lua）
  → body_filter（body_filter_by_lua）
  → log（log_by_lua）
```

> **踩坑提醒**：
> 1. `content_by_lua` 和 `proxy_pass` 不能在同一个 location 中同时使用——`content_by_lua` 自己生成内容，不会再转发给后端。如果你既要认证又要代理，用 `access_by_lua`（做认证）+ `proxy_pass`（做代理）。
> 2. `init_by_lua` 在 master 进程中执行，只执行一次，适合加载全局配置和模块。`init_worker_by_lua` 在每个 worker 中执行，适合初始化 worker 级数据和启动定时任务。
> 3. `body_filter_by_lua` 可能被调用多次（响应体分块传输），要注意累加处理。

---

### Q39. cosocket 是什么？有什么限制？

**答案要点**：

**cosocket（Coroutine Socket）** 是 OpenResty 提供的非阻塞套接字 API，允许 Lua 代码进行网络 IO 操作（TCP/UDP）而不阻塞 Nginx worker 的事件循环。

**为什么需要 cosocket**：

标准 Lua 的 `socket` 库是阻塞的——调用 `socket:receive()` 会阻塞整个线程直到数据到达。如果 Nginx worker 在处理某个请求时阻塞了，这个 worker 上所有其他连接都得不到处理。

cosocket 基于 Nginx 的事件循环和 Lua 协程（coroutine）实现：

```
Lua 代码调用 cosocket:receive()
  → Lua 协程 yield（挂起），控制权回到 Nginx 事件循环
  → Nginx 继续处理其他连接
  → 当数据到达时，Nginx 事件循环 resume（恢复）Lua 协程
  → Lua 代码继续执行
```

**使用示例**：

```lua
local http = require "resty.http"
local httpc = http.new()
-- 这个请求是非阻塞的，不会卡住 Nginx
local res, err = httpc:request_uri("http://backend/api/data", {
    method = "GET",
    timeout = 5000,
})
```

**cosocket 的限制**：

1. **只能在某些阶段使用**：cosocket 不能在 `init_by_lua`、`init_worker_by_lua`、`set_by_lua`、`log_by_lua`、`header_filter_by_lua`、`body_filter_by_lua` 中使用。只能在 `access_by_lua`、`rewrite_by_lua`、`content_by_lua` 中使用。

   | 阶段 | 能否用 cosocket |
   |------|----------------|
   | `access_by_lua` | 能 |
   | `rewrite_by_lua` | 能 |
   | `content_by_lua` | 能 |
   | `init_by_lua` | 不能 |
   | `init_worker_by_lua` | 不能 |
   | `header_filter_by_lua` | 不能 |
   | `body_filter_by_lua` | 不能 |
   | `log_by_lua` | 不能 |
   | `balancer_by_lua` | 不能 |

2. **`log_by_lua` 的替代方案**：如果需要在 `log_by_lua` 中发送网络请求（如上报指标），用 `ngx.timer.at` 创建一个定时器，在定时器中使用 cosocket：

```lua
log_by_lua_block {
    ngx.timer.at(0, function()
        local http = require "resty.http"
        -- 在 timer 中可以用 cosocket
        local httpc = http.new()
        httpc:request_uri("http://metrics-server/report", {...})
    end)
}
```

3. **协程数量限制**：每个请求中创建的 cosocket 数量受 `lua_max_pending_timers` 和 `lua_max_running_timers` 限制。

4. **不能跨阶段使用**：在一个阶段创建的 cosocket 连接不能在另一个阶段继续使用（因为 Lua 协程的生命周期绑定到请求处理的阶段）。

> **面试加分点**：提到 cosocket 是 OpenResty 的核心创新——它让 Lua 开发者可以用同步的代码风格写异步 IO，不需要像 Node.js 那样写回调或 Promise。代码可读性极高，同时保持非阻塞的高性能。

---

### Q40. ngx.shared.DICT 和 ngx.ctx 的区别？

**答案要点**：

`ngx.shared.DICT` 和 `ngx.ctx` 是 OpenResty 中两个常用的数据存储机制，用途完全不同。

**ngx.shared.DICT——共享内存字典**：

- **作用域**：所有 worker 进程共享（跨 worker、跨请求）。
- **生命周期**：Nginx 运行期间一直存在（直到 Nginx 关闭）。
- **存储位置**：Nginx 共享内存（shm）。
- **线程安全**：是，内部有锁机制。
- **典型用途**：全局缓存、限流计数器、配置数据共享、健康检查状态。

```nginx
http {
    # 声明共享内存区域
    lua_shared_dict my_cache 10m;

    server {
        location /api/ {
            access_by_lua_block {
                local cache = ngx.shared.my_cache
                -- 写入缓存（所有 worker 可见）
                cache:set("key", "value", 60)  -- TTL 60 秒
                -- 读取缓存
                local val = cache:get("key")
            }
        }
    }
}
```

**ngx.ctx——请求上下文**：

- **作用域**：单个请求（同一个请求的各个 Lua 阶段之间共享）。
- **生命周期**：请求结束即销毁。
- **存储位置**：Lua 协程的内存（用户空间）。
- **线程安全**：不需要（每个请求独立）。
- **典型用途**：在同一个请求的不同阶段之间传递数据（如 access_by_lua 设置的数据在 content_by_lua 中读取）。

```nginx
location /api/ {
    access_by_lua_block {
        -- 在 access 阶段设置
        ngx.ctx.user_id = "12345"
        ngx.ctx.user_role = "admin"
    }

    header_filter_by_lua_block {
        -- 在 header_filter 阶段读取
        ngx.header["X-User-ID"] = ngx.ctx.user_id
    }

    log_by_lua_block {
        -- 在 log 阶段读取
        ngx.log(ngx.INFO, "request by user: " .. (ngx.ctx.user_id or "unknown"))
    }
}
```

**对比表**：

| 维度 | ngx.shared.DICT | ngx.ctx |
|------|----------------|---------|
| 作用域 | 所有 worker 共享 | 单个请求 |
| 生命周期 | Nginx 运行期间 | 请求结束即销毁 |
| 存储位置 | 共享内存（shm） | Lua 协程内存 |
| 大小限制 | 声明时指定（如 10m） | 无显式限制（受 worker 内存限制） |
| 线程安全 | 是（内部有锁） | 不需要（每请求独立） |
| 性能 | 略低（锁 + 内存拷贝） | 极高（直接内存访问） |
| 典型用途 | 全局缓存、限流计数 | 请求内数据传递 |

**使用场景选择**：

- 需要跨请求/跨 worker 共享数据 → `ngx.shared.DICT`
- 只在单个请求内传递数据 → `ngx.ctx`
- 需要持久化（Nginx 重启后还在） → 都不行，用 Redis/数据库

> **踩坑提醒**：
> 1. `ngx.ctx` 在**内部重定向**（`ngx.exec`）后会丢失——因为内部重定向会创建新的请求上下文。
> 2. `ngx.shared.DICT` 的 value 大小有限制（默认单个 value 不超过 `lua_shared_dict` 总大小减去元数据开销）。大对象建议序列化为 JSON 后存储。
> 3. `ngx.shared.DICT` 的 `set` 操作是原子的，但"读-改-写"不是原子的。需要原子操作时用 `incr` 或 `add`。

---

### Q41. 如何用 OpenResty 实现限流？

**答案要点**：

OpenResty 实现限流比 Nginx 原生 `limit_req` 更灵活，可以基于任意维度（用户 ID、API 路径、IP 等）做限流，且限流策略可以动态调整。

**方案1：基于令牌桶的请求限流（lua-resty-limit-traffic）**

```nginx
http {
    lua_shared_dict limit_req_store 10m;

    server {
        location /api/ {
            access_by_lua_block {
                local limit_req = require "resty.limit.req"

                -- 速率：每秒 10 个请求，突发容量 20
                local lim, err = limit_req.new("limit_req_store", 10, 20)
                if not lim then
                    ngx.log(ngx.ERR, "failed to instantiate limit_req: ", err)
                    return ngx.exit(500)
                end

                -- 基于客户端 IP 限流（也可以换成用户 ID、API 路径等）
                local key = ngx.var.binary_remote_addr
                local delay, err = lim:incoming(key, true)

                if not delay then
                    if err == "rejected" then
                        -- 超过限流，返回 429
                        ngx.header["Retry-After"] = "1"
                        return ngx.exit(429)
                    end
                    ngx.log(ngx.ERR, "limit_req error: ", err)
                    return ngx.exit(500)
                end

                -- delay > 0 表示需要延迟处理（突发请求排队）
                if delay >= 0.001 then
                    ngx.sleep(delay)
                end
            }
            proxy_pass http://backend;
        }
    }
}
```

**方案2：基于用户 ID 限流（需要先解析认证信息）**

```lua
access_by_lua_block {
    local limit_req = require "resty.limit.req"
    local lim = limit_req.new("limit_req_store", 100, 50)

    -- 从 JWT 中解析用户 ID
    local auth = ngx.var.http_authorization
    local user_id = parse_jwt(auth)  -- 自定义函数
    if not user_id then
        return ngx.exit(401)
    end

    -- 基于用户 ID 限流（每个用户独立计数）
    local key = "user:" .. user_id
    local delay, err = lim:incoming(key, true)
    if not delay then
        if err == "rejected" then
            ngx.header["X-RateLimit-Remaining"] = "0"
            return ngx.exit(429)
        end
    end
}
```

**方案3：并发连接数限流**

```lua
local limit_conn = require "resty.limit.conn"
-- 最多 100 并发连接，每秒 50 个请求的速率
local lim = limit_conn.new("limit_conn_store", 100, 50)

local key = ngx.var.binary_remote_addr
local delay, err = lim:incoming(key, true)
if not delay then
    if err == "rejected" then
        return ngx.exit(429)
    end
end

-- 请求结束后减少并发计数
local ok, err = lim:leaving(key, 1)
```

**方案4：滑动窗口限流（自定义实现）**

```lua
-- 用 ngx.shared.DICT 实现滑动窗口
local function sliding_window_limit(key, max_requests, window_sec)
    local dict = ngx.shared.rate_limit
    local now = ngx.time()
    local window_start = now - window_sec

    -- 获取当前窗口内的请求记录
    local count = dict:incr(key .. ":" .. now, 1, 0, window_sec)
    if count > max_requests then
        return false
    end
    return true
end
```

> **踩坑提醒**：
> 1. `lua_shared_dict` 的大小要足够存储所有限流 key 的计数。10MB 约能存 16 万个 key。如果用户量大，需要调大。
> 2. 限流 key 的设计很关键——用 `$binary_remote_addr` 比 `$remote_addr` 省内存（4 字节 vs 7~15 字节）。
> 3. 分布式环境下（多个 Nginx 实例），`ngx.shared.DICT` 是单机共享，不能跨实例。需要用 Redis 做分布式限流（`lua-resty-redis` + 原子操作）。

---

### Q42. balancer_by_lua 的作用？

**答案要点**：

`balancer_by_lua` 允许在 Lua 代码中**动态选择后端服务器**，替代 Nginx 原生的静态负载均衡算法（轮询、IP Hash 等）。

**Nginx 原生负载均衡的局限**：

- 算法在配置文件中固定，修改需要 reload。
- 健康检查是被动式的（请求失败才标记不可用）。
- 无法根据请求内容动态路由（如根据用户 ID 路由到特定后端）。

**balancer_by_lua 的能力**：

```nginx
upstream backend {
    server 0.0.0.1;  -- 占位符，实际的 peer 由 Lua 决定

    balancer_by_lua_block {
        local balancer = require "ngx.balancer"
        local host, port

        -- 根据请求头动态选择后端
        local channel = ngx.var.http_x_channel
        if channel == "canary" then
            host, port = "192.168.1.10", 8080  -- 灰度服务器
        else
            host, port = "192.168.1.1", 8080   -- 生产服务器
        end

        local ok, err = balancer.set_current_peer(host, port)
        if not ok then
            ngx.log(ngx.ERR, "failed to set peer: ", err)
            return ngx.exit(500)
        end
    }
}
```

**典型应用场景**：

**1. 动态灰度发布**：根据请求头/Cookie/用户 ID 决定路由到灰度服务器还是生产服务器。

**2. 主动健康检查**：配合 `lua-resty-upstream-healthcheck` 库，定期探测后端健康状态，动态剔除不健康的节点。

```lua
-- 健康检查库会维护一个后端健康状态的共享字典
balancer_by_lua_block {
    local healthcheck = require "resty.upstream.healthcheck"
    local ok, err = healthcheck.spawn_checker({
        shm = "healthcheck",
        upstream = "backend",
        type = "http",
        http_req = "GET /health HTTP/1.0\r\n\r\n",
        interval = 2,       -- 每 2 秒检查一次
        fall = 3,           -- 连续失败 3 次标记为 down
        rise = 2,           -- 连续成功 2 次标记为 up
    })

    -- 从健康的后端中选择一个
    local balancer = require "ngx.balancer"
    local healthy_peers = get_healthy_peers()  -- 自定义函数
    local peer = healthy_peers[math.random(#healthy_peers)]
    balancer.set_current_peer(peer.host, peer.port)
}
```

**3. 一致性哈希**：在 Lua 中实现一致性哈希算法，比 Nginx 原生的 `hash` 更灵活。

**4. 权重动态调整**：根据后端服务器的负载情况（如 CPU、内存、响应时间）动态调整权重。

**balancer_by_lua 的限制**：

- 只能在 `upstream` 块中使用。
- 不能使用 cosocket（因为此时还没有建立到后端的连接）。
- `set_current_peer` 只能设置一个 peer，不支持一次设置多个（不支持 backup peer）。

> **踩坑提醒**：`balancer_by_lua` 中不能用 `ngx.var` 的大部分变量（因为此时还在 upstream 选择阶段，请求还没转发）。但可以用 `ngx.ctx` 中之前阶段（如 `access_by_lua`）存储的数据。

---

### Q43. Kong 和 APISIX 的区别？

**答案要点**：

Kong 和 APISIX 都是基于 OpenResty 的 API 网关，但设计理念和技术架构有显著区别。

**共同点**：

- 都基于 OpenResty（Nginx + LuaJIT）。
- 都是开源 API 网关，提供路由、认证、限流、监控等功能。
- 都支持插件扩展。

**核心区别**：

| 维度 | Kong | APISIX |
|------|------|--------|
| **开发语言** | Lua（OpenResty）+ 少量 Go | Lua（OpenResty）|
| **配置存储** | PostgreSQL / Cassandra | etcd |
| **配置生效** | 通过 Admin API 写数据库，轮询同步到 Nginx | 通过 etcd watch 实时推送 |
| **动态路由** | 支持，但依赖数据库轮询 | 支持，基于 etcd 实时变更 |
| **插件机制** | Lua 插件 / Go 插件 / JS 插件 | Lua 插件 / Java 插件 / Go 插件 |
| **配置延迟** | 秒级（轮询间隔） | 毫秒级（etcd watch） |
| **架构复杂度** | 较高（需数据库） | 较低（只需 etcd） |
| **社区** | 早期发起，社区成熟 | 后来者，国内社区活跃 |
| **性能** | 高 | 略高于 Kong（配置同步更快） |

**配置同步机制对比**：

```
Kong:
  Admin API → 写 PostgreSQL → Kong 节点轮询数据库 → 更新 Nginx 配置
  延迟：取决于轮询间隔（通常 1~5 秒）

APISIX:
  Admin API → 写 etcd → etcd watch 推送到 APISIX 节点 → 更新 Nginx 配置
  延迟：毫秒级（etcd watch 是推模式，实时通知）
```

**选型建议**：

| 场景 | 推荐 | 原因 |
|------|------|------|
| 已有 PostgreSQL/Cassandra | Kong | 复用现有基础设施 |
| 需要极低的配置生效延迟 | APISIX | etcd watch 毫秒级 |
| 需要丰富的插件生态 | Kong | 社区更成熟，插件更多 |
| 国内团队，需要中文支持 | APISIX | 国内开源项目，文档和社区中文友好 |
| 云原生/K8s 环境 | APISIX | 与 etcd/K8s 集成更自然 |
| 简单 API 网关需求 | 两者皆可 | 功能都足够 |

> **面试加分点**：提到两者最核心的区别是**配置存储和同步机制**——Kong 用数据库轮询（pull 模式），APISIX 用 etcd watch（push 模式）。这导致 APISIX 的配置变更延迟更低，但引入了 etcd 依赖。选择取决于你的基础设施和延迟需求。

---

### Q44. lua_code_cache 为什么生产环境必须开启？

**答案要点**：

`lua_code_cache` 控制 Lua 代码是否被缓存（编译后的字节码）。默认是 `on`（开启缓存）。

```nginx
http {
    lua_code_cache on;   # 生产环境必须开启（默认值）
    # lua_code_cache off; # 开发环境可以关闭
}
```

**开启时（lua_code_cache on）**：

- Lua 文件第一次被加载时，LuaJIT 会编译成字节码并**缓存**在内存中。
- 后续请求直接使用缓存的字节码，不再重新读取文件和编译。
- 性能极高——字节码执行速度接近 C 代码。
- **修改 Lua 文件后需要 reload Nginx** 才能生效（因为缓存了旧代码）。

**关闭时（lua_code_cache off）**：

- 每次请求都会重新读取 Lua 文件、重新编译。
- 修改 Lua 文件后**立即生效**，不需要 reload。
- 性能极差——每次请求都有文件 IO + 编译开销。
- 会禁用 LuaJIT 的 JIT 编译（退化为解释执行）。

**为什么生产环境必须开启**：

1. **性能**：关闭缓存后，每个请求都要重新编译 Lua 代码，QPS 可能下降 **10~100 倍**。
2. **JIT 失效**：`lua_code_cache off` 会禁用 LuaJIT 的 JIT 编译器，所有代码退化为解释执行，性能急剧下降。
3. **文件 IO 压力**：高并发时大量请求同时读取 Lua 文件，磁盘 IO 成为瓶颈。
4. **稳定性**：如果 Lua 文件正在被修改（如部署时），关闭缓存可能导致请求读到半个文件，产生语法错误。

**开发环境关闭的好处**：

开发时频繁修改 Lua 代码，关闭缓存可以**免 reload 立即看到修改效果**，提高开发效率。

**生产环境的替代方案——平滑更新**：

如果需要在不停机的情况下更新 Lua 代码：

```bash
# 1. 更新 Lua 文件
cp /path/to/new_script.lua /path/to/script.lua

# 2. reload Nginx（优雅重载，不中断服务）
nginx -s reload
```

reload 会让新 worker 使用新代码，旧 worker 处理完手中请求后退出。整个过程不中断服务。

> **踩坑提醒**：
> 1. 如果用 `require` 加载的模块，即使 `lua_code_cache off`，模块代码也**不会被重新加载**（因为 Lua 的 `package.loaded` 机制缓存了模块）。要真正实现热更新，需要清除 `package.loaded` 中的缓存或用 OpenResty 的 `resty` 命令行工具。
> 2. `lua_code_cache off` 只对 `content_by_lua_file`、`access_by_lua_file` 等 `_file` 后缀的指令有效。`_block` 后缀的指令（内联代码）始终被缓存。
> 3. 线上误关 `lua_code_cache` 是常见性能事故——如果发现 OpenResty 性能突然下降，第一时间检查这个配置。

---

## 六、实战场景（6题）

### Q45. 如何用 Nginx 实现灰度发布？

**答案要点**：

灰度发布（Canary Release）是指让一部分用户访问新版本，其他用户仍然访问旧版本，逐步扩大新版本的流量比例。

**方案1：基于 Cookie/Header 的灰度（Nginx 原生）**

```nginx
upstream production {
    server 192.168.1.1:8080;
    server 192.168.1.2:8080;
}

upstream canary {
    server 192.168.1.10:8080;
}

server {
    listen 80;

    location / {
        # 通过 Cookie 判断是否灰度用户
        if ($cookie_canary = "true") {
            proxy_pass http://canary;
        }
        # 通过 Header 判断
        if ($http_x_canary = "true") {
            proxy_pass http://canary;
        }
        # 默认走生产
        proxy_pass http://production;
    }
}
```

> 注意：这里用了 `if`，虽然 "if is evil"，但 `if + proxy_pass` 在这种简单场景下可以工作。更可靠的方式见方案3。

**方案2：基于 IP 的灰度**

```nginx
geo $is_canary {
    default       0;
    192.168.1.100 1;    # 测试人员 IP
    10.0.0.0/8    1;    # 内网全部灰度
}

server {
    location / {
        if ($is_canary) {
            proxy_pass http://canary;
        }
        proxy_pass http://production;
    }
}
```

**方案3：基于 split_clients 按比例灰度（推荐）**

```nginx
# split_clients 按哈希值分配比例
split_clients "${remote_addr}${http_user_agent}" $upstream_group {
    10%  canary;      # 10% 流量走灰度
    *    production;  # 90% 流量走生产
}

upstream production {
    server 192.168.1.1:8080;
}
upstream canary {
    server 192.168.1.10:8080;
}

server {
    location / {
        proxy_pass http://$upstream_group;
    }
}
```

`split_clients` 根据客户端 IP + User-Agent 的哈希值，将 10% 的流量分配到 canary。同一个用户的请求始终走同一个上游（哈希稳定）。

**方案4：基于 OpenResty Lua 的动态灰度（最灵活）**

```nginx
upstream backend {
    server 0.0.0.1;
    balancer_by_lua_block {
        local balancer = require "ngx.balancer"

        -- 读取灰度配置（可以存在 Redis 中，动态调整）
        local config = ngx.shared.config:get("canary_ratio") or 0
        local ratio = tonumber(config)

        -- 根据用户 ID 哈希决定是否灰度
        local user_id = ngx.ctx.user_id or ngx.var.remote_addr
        local hash = ngx.crc32_long(user_id)
        local mod = hash % 100

        if mod < ratio * 100 then
            balancer.set_current_peer("192.168.1.10", 8080)  -- 灰度
        else
            balancer.set_current_peer("192.168.1.1", 8080)   -- 生产
        end
    }
}
```

**灰度发布流程**：

```
1. 部署新版本到灰度服务器
2. 设置灰度比例 1%（只让内部测试用户访问）
3. 观察灰度服务器的错误率、性能指标
4. 逐步提高比例：1% → 5% → 10% → 50% → 100%
5. 全量后下线旧版本
```

> **踩坑提醒**：
> 1. 灰度发布要确保**有状态请求**（如 Session）的一致性——同一个用户的请求应该始终走同一个版本，不要一会儿新版本一会儿旧版本。用基于用户 ID 的哈希可以保证。
> 2. 数据库变更要**向前兼容**——灰度期间新旧版本同时运行，新版本不能使用旧版本不认识的数据库字段。
> 3. 灰度比例可以存在 Redis/etcd 中，通过管理后台动态调整，不需要 reload Nginx。

---

### Q46. Nginx 代理 WebSocket 需要什么配置？

**答案要点**：

WebSocket 协议基于 HTTP 升级机制——客户端先发一个 HTTP 请求，通过 `Upgrade: websocket` 头要求升级到 WebSocket 协议。Nginx 默认会在一定时间后关闭空闲连接，需要特殊配置。

**完整 WebSocket 代理配置**：

```nginx
upstream ws_backend {
    server 192.168.1.1:8080;
}

server {
    listen 80;
    server_name ws.example.com;

    location /ws {
        proxy_pass http://ws_backend;

        # 关键配置1：升级协议头
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 关键配置2：传递标准代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 关键配置3：超时设置（WebSocket 连接是长连接，需要调大超时）
        proxy_read_timeout 3600s;    # 1 小时
        proxy_send_timeout 3600s;

        # 关键配置4：禁用缓冲（WebSocket 需要实时传输）
        proxy_buffering off;
    }
}
```

**逐项解释**：

| 配置 | 作用 | 不设置的后果 |
|------|------|-------------|
| `proxy_http_version 1.1` | 使用 HTTP/1.1（HTTP/1.0 不支持 Upgrade） | 升级失败 |
| `proxy_set_header Upgrade $http_upgrade` | 传递客户端的 Upgrade 头 | 服务器不知道要升级 |
| `proxy_set_header Connection "upgrade"` | 设置 Connection 头为 upgrade | 连接不会被升级 |
| `proxy_read_timeout 3600s` | 读超时设为 1 小时 | 默认 60 秒后空闲连接被关闭 |
| `proxy_buffering off` | 禁用响应缓冲 | WebSocket 消息被缓冲，延迟增大 |

**Map 变量优化（推荐写法）**：

如果同一个 server 同时代理 HTTP 和 WebSocket，用 `map` 变量更优雅：

```nginx
# 根据 Upgrade 头自动设置 Connection 头
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    # HTTP API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Connection "";  # 普通 HTTP，用长连接
    }

    # WebSocket
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;  # 自动判断
        proxy_read_timeout 3600s;
    }
}
```

**WSS（WebSocket over TLS）配置**：

```nginx
server {
    listen 443 ssl;
    server_name ws.example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location /ws {
        proxy_pass http://ws_backend;   # 后端用 HTTP（Nginx 做 TLS 终止）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

> **踩坑提醒**：
> 1. `proxy_read_timeout` 是最常见的 WebSocket 问题——默认 60 秒，如果 60 秒内没有消息传输，Nginx 会关闭连接。WebSocket 应用通常会发心跳包保活，但如果心跳间隔 > 60 秒，需要调大超时。
> 2. 详见踩坑记录 `#5.3`。

---

### Q47. 如何防止后端被刷（限流方案）？

**答案要点**：

防止后端被刷需要多层限流策略，不同层面的限流有不同的粒度和效果。

**第一层：Nginx 原生限流（limit_req + limit_conn）**

```nginx
http {
    # 按 IP 限流：每秒 10 个请求
    limit_req_zone $binary_remote_addr zone=ip_limit:10m rate=10r/s;

    # 按 IP 限连接：最多 50 个并发连接
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # 按 URI 限流：保护慢接口
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=1r/s;

    server {
        # 全局连接限制
        limit_conn conn_limit 50;

        location / {
            limit_req zone=ip_limit burst=20 nodelay;
            proxy_pass http://backend;
        }

        # 慢接口更严格的限流
        location /api/report/ {
            limit_req zone=api_limit burst=5 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

**第二层：多维度限流（limit_req 组合）**

```nginx
http {
    # 按 IP 限流
    limit_req_zone $binary_remote_addr zone=per_ip:10m rate=10r/s;

    # 按用户 ID 限流（需要先解析认证信息）
    limit_req_zone $http_x_user_id zone=per_user:10m rate=5r/s;

    # 全局限流（所有请求总和）
    limit_req_zone $server_name zone=global:10m rate=1000r/s;

    server {
        location /api/ {
            # 同时应用三个限流规则（取最严格的）
            limit_req zone=per_ip burst=20 nodelay;
            limit_req zone=per_user burst=10 nodelay;
            limit_req zone=global burst=100 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

**第三层：OpenResty Lua 限流（最灵活）**

```lua
access_by_lua_block {
    local limit_req = require "resty.limit.req"

    -- 基于 API 路径 + 用户 ID 的组合限流
    local lim = limit_req.new("limit_store", 10, 20)
    local user_id = ngx.var.http_x_user_id or ngx.var.remote_addr
    local api_path = ngx.var.uri

    -- key = 用户ID + API路径，实现对"每个用户每个API"的限流
    local key = user_id .. ":" .. api_path
    local delay, err = lim:incoming(key, true)
    if not delay then
        if err == "rejected" then
            ngx.header["Retry-After"] = "1"
            return ngx.exit(429)
        end
    end
}
```

**第四层：Redis 分布式限流（多 Nginx 实例）**

```lua
access_by_lua_block {
    local redis = require "resty.redis"
    local red = redis:new()
    red:connect("redis-host", 6379)

    local key = "rate:" .. ngx.var.remote_addr
    -- 原子操作：INCR + EXPIRE
    local count = red:incr(key)
    if count == 1 then
        red:expire(key, 1)  -- 1 秒窗口
    end
    if count > 10 then
        return ngx.exit(429)
    end
}
```

**限流后的响应**：

```nginx
# 自定义限流响应
limit_req_status 429;  # 返回 429 而不是默认的 503
limit_conn_status 429;

# 添加 Retry-After 头
error_page 429 = @rate_limited;
location @rate_limited {
    add_header Retry-After "1" always;
    add_header Content-Type "application/json" always;
    return 429 '{"error": "rate_limit_exceeded", "message": "Too many requests"}';
}
```

**完整防护策略总结**：

| 层面 | 工具 | 限流维度 | 效果 |
|------|------|---------|------|
| Nginx limit_req | 原生 | IP / URI | 防 CC 攻击 |
| Nginx limit_conn | 原生 | IP 并发连接数 | 防慢连接攻击 |
| OpenResty Lua | Lua | 用户ID / API路径 | 精确限流 |
| Redis 分布式 | Lua + Redis | 跨实例 | 多节点统一限流 |
| 后端应用 | 应用代码 | 业务逻辑 | 最终兜底 |

> **踩坑提醒**：
> 1. 限流要分层——不要只在一个层面限流。Nginx 限流挡住大部分恶意流量，后端应用做业务级限流兜底。
> 2. `429 Too Many Requests` 比 `503 Service Unavailable` 更合适——429 明确告诉客户端"你被限流了"，503 让客户端以为服务器挂了。
> 3. 限流 key 的选择要考虑 NAT 问题——大量用户在同一个 NAT 出口，用 IP 限流会误伤正常用户。优先用用户 ID 限流，IP 限流作为补充。

---

### Q48. 如何排查 Nginx 配置不生效的问题？

**答案要点**：

配置不生效是 Nginx 运维中最常见的问题之一。排查步骤如下：

**第一步：确认配置是否通过语法检查**

```bash
sudo nginx -t
```

如果报错，说明配置语法有问题，修改后重试。如果通过，继续下一步。

**第二步：确认是否 reload 了**

```bash
# 修改配置后必须 reload
sudo nginx -s reload

# 或
sudo systemctl reload nginx
```

很多人改了配置但忘了 reload。检查 reload 是否成功：

```bash
# 查看 Nginx 状态
sudo systemctl status nginx

# 查看最近的重载时间
sudo journalctl -u nginx --since "10 minutes ago"
```

**第三步：用 nginx -T 确认最终生效的配置**

```bash
# 打印所有已生效的配置
sudo nginx -T | grep "你要检查的指令"

# 例如检查 server_name
sudo nginx -T | grep server_name

# 例如检查某个 location
sudo nginx -T | grep -A 10 "location /api/"
```

`nginx -T` 打印的是**解析后展开的完整配置**，包括所有 include 进来的文件。如果 `nginx -T` 的输出和你预期的不一样，说明配置文件没有被正确加载。

**第四步：检查 include 路径**

```bash
# nginx.conf 中 include 的路径
grep include /etc/nginx/nginx.conf

# 常见的 include 路径
ls -la /etc/nginx/conf.d/
ls -la /etc/nginx/sites-enabled/

# 确认你的配置文件在这些目录中
ls -la /etc/nginx/conf.d/my-site.conf
```

常见问题：
- 配置文件放在了 `/etc/nginx/sites-available/` 但没有创建到 `sites-enabled/` 的软链接。
- 配置文件后缀不是 `.conf`（如果 include 的是 `*.conf`，非 `.conf` 文件不会被加载）。

**第五步：检查 location 匹配优先级**

配置写了但没匹配到，可能是 location 优先级问题（详见 Q11）。用 `curl -v` 测试：

```bash
# 查看请求实际命中了哪个 location
curl -v http://localhost/api/test

# 对比不同 URI 的行为
curl -v http://localhost/api/test/
curl -v http://localhost/api/test.php
```

**第六步：检查浏览器缓存**

如果是 HTTP→HTTPS 跳转或 HSTS 不生效，可能是浏览器缓存了 301：

```bash
# 用 curl 测试（绕过浏览器缓存）
curl -I http://example.com/

# 浏览器无痕模式测试
# 或清除浏览器缓存
```

**第七步：检查SELinux/AppArmor**

```bash
# CentOS 检查 SELinux
getenforce
# 如果是 Enforcing，可能阻止了 Nginx 读取某些文件
# 临时关闭测试
sudo setenforce 0

# 查看 SELinux 审计日志
sudo ausearch -m avc -ts recent | grep nginx
```

**排查清单**：

| 检查项 | 命令 | 常见问题 |
|--------|------|---------|
| 语法检查 | `nginx -t` | 语法错误 |
| 是否 reload | `systemctl status nginx` | 忘了 reload |
| 生效配置 | `nginx -T` | include 路径不对 |
| 配置文件存在 | `ls /etc/nginx/conf.d/` | 文件放错目录 |
| 文件后缀 | `ls *.conf` | 后缀不是 .conf |
| location 匹配 | `curl -v` | 优先级问题 |
| 浏览器缓存 | `curl -I` | 301 被缓存 |
| SELinux | `getenforce` | 权限被限制 |

> **踩坑提醒**：最常见的"配置不生效"原因是：(1) 改了配置但没 reload；(2) 配置文件不在 include 的目录中；(3) location 优先级导致请求匹配到了另一个 location。按照上述步骤逐一排查，90% 的问题在前三步就能定位。

---

### Q49. Nginx reload 失败怎么办？

**答案要点**：

`nginx -s reload` 失败通常有以下几种原因和对应的解决方案。

**原因1：配置语法错误（最常见）**

```bash
$ sudo nginx -s reload
nginx: [emerg] unknown directive "proxy_pas" in /etc/nginx/conf.d/default.conf:5
nginx: configuration file /etc/nginx/nginx.conf test failed
```

**解决**：reload 前先 `nginx -t` 检查语法。reload 内部会先做语法检查，如果失败不会影响正在运行的 Nginx（旧配置仍然生效）。

```bash
# 最佳实践：先测试再 reload
sudo nginx -t && sudo nginx -s reload
```

**原因2：端口被占用**

```bash
$ sudo nginx -s reload
nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
```

**解决**：找出占用端口的进程并处理：

```bash
# 查看谁占用了端口
sudo lsof -i :80
# 或
sudo ss -tlnp | grep :80

# 如果是另一个 Nginx 实例，先停掉
sudo kill $(cat /var/run/nginx.pid)

# 如果是其他程序（如 Apache），停掉它
sudo systemctl stop httpd
```

**原因3：权限不足**

```bash
$ nginx -s reload
nginx: [alert] could not open error log file: open() "/var/log/nginx/error.log" failed (13: Permission denied)
```

**解决**：用 `sudo` 执行，或确保运行用户有权限读写日志文件和 PID 文件。

```bash
sudo nginx -s reload

# 如果是 systemd 服务
sudo systemctl reload nginx
```

**原因4：PID 文件不存在或不正确**

```bash
$ sudo nginx -s reload
nginx: [error] open() "/var/run/nginx.pid" failed (2: No such file or directory)
```

**解决**：PID 文件记录了 master 进程的 PID。如果文件不存在（如被手动删除），Nginx 找不到 master 进程发信号。

```bash
# 方法1：手动找到 master PID 并发送 HUP 信号
ps -ef | grep "nginx: master" | grep -v grep
# 假设 PID 是 12345
sudo kill -HUP 12345

# 方法2：重新创建 PID 文件
echo 12345 | sudo tee /var/run/nginx.pid
sudo nginx -s reload

# 方法3：重启 Nginx（最后手段，会短暂中断）
sudo systemctl restart nginx
```

**原因5：磁盘空间不足**

```bash
$ sudo nginx -s reload
nginx: [emerg] open() "/var/log/nginx/error.log" failed (28: No space left on device)
```

**解决**：清理磁盘空间，特别是日志文件：

```bash
# 检查磁盘空间
df -h

# 清理大日志文件
sudo truncate -s 0 /var/log/nginx/access.log
# 或用 logrotate 轮转
sudo logrotate -f /etc/logrotate.d/nginx
```

**reload 失败时的重要保障**：

Nginx 的 reload 机制设计为**安全的**——如果新配置有问题，Nginx 不会应用新配置，**旧的配置继续运行**。这意味着即使 reload 失败，线上服务不会中断（只是用的还是旧配置）。

```
reload 流程：
1. master 进程收到 HUP 信号
2. master 重新读取配置文件
3. 如果配置有错误 → 记录错误日志，保持旧配置运行，reload 失败
4. 如果配置正确 → fork 新 worker（用新配置），向旧 worker 发 QUIT
5. 旧 worker 处理完手中请求后退出
```

> **踩坑提醒**：
> 1. reload 失败时 Nginx **不会中断**——旧配置继续运行。这是 Nginx 的安全设计。但要及时修复配置问题，否则你的修改永远不会生效。
> 2. 如果 reload 似乎成功了但行为没变，检查是否有**多个 Nginx 实例**在运行（`ps -ef | grep nginx`），你可能 reload 的是错误的实例。

---

### Q50. 如何实现 Nginx 的零停机更新？

**答案要点**：

零停机更新（Zero Downtime Upgrade）分为两种场景：更新 Nginx 配置和更新 Nginx 二进制。

**场景1：更新配置（reload）**

```bash
# reload 本身就是零停机的
sudo nginx -t && sudo nginx -s reload
```

reload 过程中，旧 worker 处理完手中请求后优雅退出，新 worker 用新配置启动。整个过程不中断服务。

**场景2：更新 Nginx 二进制（热升级）**

当需要升级 Nginx 版本（如从 1.28 升到 1.30）时，不能用 reload（reload 只重新加载配置，不加载新二进制）。需要用 **USR2 + WINCH 信号**实现热升级：

**热升级流程**：

```bash
# 步骤1：备份旧二进制
sudo cp /usr/sbin/nginx /usr/sbin/nginx.old

# 步骤2：安装新二进制
sudo cp /path/to/new/nginx /usr/sbin/nginx

# 步骤3：向旧 master 发送 USR2 信号
# → 旧 master 会用新二进制 fork 一个新 master
# → 新 master 用新二进制运行，接管监听端口
sudo kill -USR2 $(cat /var/run/nginx.pid)

# 步骤4：向旧 master 发送 WINCH 信号
# → 旧 master 的 worker 优雅退出（处理完手中请求）
# → 新 master 的 worker 接管所有新连接
sudo kill -WINCH $(cat /var/run/nginx.pid)

# 步骤5：确认新版本正常工作
curl -I http://localhost/
nginx -v  # 确认新版本

# 步骤6（可选）：如果新版本正常，向旧 master 发送 QUIT 信号
sudo kill -QUIT $(cat /var/run/nginx.pid.oldbin)
# 注意：此时旧 master 的 PID 在 nginx.pid.oldbin 文件中

# 步骤7（回退）：如果新版本有问题，回退到旧版本
# 向新 master 发送 QUIT（让新 master 和其 worker 退出）
sudo kill -QUIT $(cat /var/run/nginx.pid)
# 旧 master 会重新 fork worker，接管所有连接
# 然后恢复旧二进制文件
sudo cp /usr/sbin/nginx.old /usr/sbin/nginx
```

**热升级过程中的进程状态**：

```
初始状态：
  master (旧二进制, PID 在 nginx.pid)
    └─ worker (旧)
    └─ worker (旧)

USR2 后：
  master (旧二进制, PID 在 nginx.pid.oldbin)
    └─ worker (旧)        ← 还在处理旧请求
  master (新二进制, PID 在 nginx.pid)  ← 新 master 启动
    └─ worker (新)

WINCH 后：
  master (旧二进制, PID 在 nginx.pid.oldbin)
    (旧 worker 已退出)
  master (新二进制, PID 在 nginx.pid)
    └─ worker (新)        ← 接管所有连接

QUIT (旧 master) 后：
  master (新二进制, PID 在 nginx.pid)
    └─ worker (新)        ← 完成升级
```

**Docker 环境的零停机更新**：

Docker 中更常见的做法是用蓝绿部署或滚动更新：

```yaml
# docker-compose.yml 蓝绿部署
services:
  nginx-blue:
    image: nginx:1.28
    # ... 配置

  nginx-green:
    image: nginx:1.30
    # ... 配置
    # 启动 green，确认正常后停止 blue
```

或用 Kubernetes 的滚动更新（自动零停机）：

```yaml
# K8s Deployment 滚动更新
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0      # 不允许减少 pod
      maxSurge: 1            # 最多多一个 pod
```

> **踩坑提醒**：
> 1. 热升级前务必用 `nginx -t` 测试新二进制能否正确解析现有配置。
> 2. 新旧 Nginx 的模块要兼容——如果旧版本编译了某个模块但新版本没有，热升级后该模块的指令会失效。
> 3. 热升级后不要急着退出旧 master——先观察一段时间（如 30 分钟），确认新版本没有问题后再发 QUIT 信号退出旧 master。如果新版本出问题，可以用旧 master 回退。
> 4. PID 文件管理是热升级的关键——USR2 后会有两个 PID 文件：`nginx.pid`（新 master）和 `nginx.pid.oldbin`（旧 master）。回退时要注意用正确的 PID 文件。

---

## 小结

本文档精选了 50 道 Nginx 面试题，覆盖从基础概念到实战场景的完整知识体系。回顾各部分重点：

| 分类 | 题数 | 核心知识点 |
|------|------|-----------|
| 基础概念 | 10 | 事件驱动、master/worker、高并发原理、正向/反向代理、配置结构、upstream、负载均衡算法 |
| 配置相关 | 10 | location 匹配优先级、root/alias、proxy_pass 尾斜杠、rewrite last/break、if is evil、try_files、HTTP跳HTTPS、IP 限制、limit_req burst/nodelay、proxy_set_header |
| HTTPS/安全 | 8 | TLS 握手、证书链、HSTS、OCSP Stapling、隐藏版本号、目录穿越、HTTP/2&3、SNI |
| 性能优化 | 8 | 调优手段、reuseport、upstream keepalive、连接数计算、sendfile 零拷贝、proxy_cache、502/504 排查 |
| OpenResty/Lua | 8 | OpenResty 架构、Lua 执行阶段、cosocket、shared.DICT vs ctx、限流实现、balancer_by_lua、Kong vs APISIX、lua_code_cache |
| 实战场景 | 6 | 灰度发布、WebSocket 代理、限流方案、配置不生效排查、reload 失败处理、零停机更新 |

**面试策略建议**：

1. **基础概念题**要能讲清"为什么"——不要只说"Nginx 用事件驱动"，要能解释事件驱动比传统模型好在哪里、epoll 为什么比 select 快。
2. **配置相关题**要能手写配置——面试官可能让你在白板上写 location 匹配或 proxy_pass 配置。
3. **踩坑提醒是加分项**——面试官不只看你能不能答对，更看你有没有实战经验。提到"proxy_pass 尾斜杠导致 404"、"if is evil"、"证书链不完整"等踩坑经历，比标准答案更有说服力。
4. **性能优化题要有数据支撑**——说"开了 reuseport 性能提升 2 倍"比"reuseport 能提升性能"更有说服力。
5. **实战场景题要讲思路**——不只是给出配置，要讲排查思路和决策过程。

> **扩展阅读**：本文档中的每个知识点在本系列其他文档中都有更深入的讲解。建议结合 [01-Nginx概述与架构原理](./01-基础认知/01-Nginx概述与架构原理.md) 到 [27-网关生态Kong与APISIX](./07-OpenResty与Lua插件/27-网关生态Kong与APISIX.md) 系统学习，配合 [29-常用命令速查表](./29-常用命令速查表.md) 和 [99-踩坑记录与解决方案](./99-踩坑记录与解决方案.md) 巩固实战经验。