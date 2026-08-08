---
tags: [Java, Tomcat, server.xml, 配置, Connector, Executor, Engine, Host, Context]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
来源: wolai 笔记转存（https://www.wolai.com/plyr/wq9uk2MQqaTtbaJMX3H6YA）
---

# Tomcat 服务器核心配置详解（server.xml）

> 本文是 Tomcat 学习笔记第 2 章（wolai 转存整理）。核心：**Tomcat 的配置主要在 conf/server.xml**，server.xml 中包含 Servlet 容器的相关配置（即 Catalina 的配置），本质是 **XML 标签的使用**。
> 官方参考：https://tomcat.apache.org/tomcat-8.5-doc/config/ （8.5.100）
> 关联笔记：[[00-Tomcat 学习笔记（总览）]]、[[01-Tomcat 系统架构与原理剖析]]

## 📋 总纲

1. server.xml 标签结构总览
2. Server 与 Service 标签
3. Executor 标签（共享线程池）
4. Connector 标签（连接器）
5. Engine 标签（Servlet 引擎）
6. Host 标签（虚拟主机）
7. Valve 标签（阀）
8. Context 标签（Web 应用）
9. 完整配置示例与易错点

---

## 1. server.xml 标签结构总览

**要点**：

- Tomcat 作为服务器的配置，主要是 **server.xml** 文件的配置
- server.xml 中包含了 Servlet 容器的相关配置，即 **Catalina 的配置**
- XML 中主要是**标签**的使用

**两大问题**：去哪配置？怎么配置？

**主要标签结构**（层级关系）：

```
Server（服务器）
 └── Service（服务）
      ├── Listener   （生命周期监听器）
      ├── Executor   （共享线程池）
      ├── Connector  （连接器，可多个）
      └── Engine     （Servlet 引擎）
           ├── Host  （虚拟主机，可多个）
           │    └── Context（Web 应用，可多个）
           │         └── Wrapper（Servlet）
           └── Valve （阀）
```

---

## 2. Server 与 Service 标签

### 2.1 Server 标签

**Server 代表整个 Catalina Servlet 容器**。负责启动/关闭 Tomcat，监听关闭命令端口（默认 8005）。

```xml
<Server port="8005" shutdown="SHUTDOWN">
  ...
</Server>
```

| 属性 | 说明 |
|---|---|
| `port` | 监听**关闭命令**的端口。收到 `shutdown` 属性值（默认 SHUTDOWN）时关闭 Tomcat |
| `shutdown` | 关闭命令字符串。⚠️ 生产环境建议修改默认值（防止外部直接发 SHUTDOWN 关闭服务） |

### 2.2 Service 标签

**Service 用于创建 Service 实例**，默认使用 `org.apache.catalina.core.StandardService`。

- 一个 Server 中支持配置**多个 Service**，不过大部分情况下都配置一个
- 默认情况下，Tomcat 仅指定了 Service 的名称，值为 **"Catalina"**

```xml
<Service name="Catalina">
  ...
</Service>
```

**Service 子标签**：

| 子标签 | 作用 |
|---|---|
| `Listener` | 为 Service 添加生命周期监听器 |
| `Executor` | 配置 Service 共享线程池 |
| `Connector` | 配置 Service 包含的连接器 |
| `Engine` | 配置 Service 中连接器对应的 Servlet 容器引擎 |

---

## 3. Executor 标签（共享线程池）

**默认情况下，Service 并未添加共享线程池配置**。想添加一个线程池，可以在 `<Service>` 下添加：

```xml
<Service name="Catalina">
  <Executor name="tomcatThreadPool"
            namePrefix="catalina-exec-"
            maxThreads="200"
            minSpareThreads="20"
            maxIdleTime="60000"
            prestartminSpareThreads="false"
            threadPriority="5"
            className="org.apache.catalina.core.StandardThreadExecutor"/>
  ...
</Service>
```

**属性详解**：

| 属性 | 说明 |
|---|---|
| `name` | 线程池名称，用于 Connector 中指定（`executor` 属性引用） |
| `namePrefix` | 所创建的每个线程的名称前缀，一个单独的线程名称为 `namePrefix + threadNumber` |
| `maxThreads` | 池中**最大线程数** |
| `minSpareThreads` | **活跃线程数（核心池线程数）**，这些线程不会被销毁，会一直存在 |
| `maxIdleTime` | 线程空闲时间，超过该时间后空闲线程会被销毁。⚠️ 默认值 6000 毫秒 = 1 分钟 |
| `maxQueueSize` | 被执行前最大线程排队数目，默认为 `Integer.MAX_VALUE`（广义无限）。除非特殊情况，这个值不需要更改，否则会有请求不被处理的情况发生 |
| `prestartminSpareThreads` | 启动线程池时是否启动 minSpareThreads 部分线程。默认 false，即不启动 |
| `threadPriority` | 线程池中线程优先级，默认 5，取值范围 1~10 |
| `className` | 线程池实现类，未指定时默认 `org.apache.catalina.core.StandardThreadExecutor`。想使用自定义线程池需要实现 `org.apache.catalina.Executor` 接口 |

> **注意**：若 Connector 配置了 `executor="xxx"` 引用共享线程池，则 Connector 上其他线程属性（maxThreads 等）**会被忽略**。

---

## 4. Connector 标签（连接器）

**Connector 标签用于创建连接器实例**。默认情况下 server.xml 配置了两个连接器：一个支持 **HTTP 协议**，一个支持 **AJP 协议**。

```xml
<Connector port="8080" protocol="HTTP/1.1"
           connectionTimeout="20000"
           redirectPort="8443" />

<Connector port="8009" protocol="AJP/1.3" redirectPort="8443" />
```

大部分情况下**不需要新增连接器配置**，只根据需要对已有连接器进行优化。

**属性详解**：

| 属性 | 说明 |
|---|---|
| `port` | **端口号**。Connector 用于创建服务端 Socket 并进行监听，以等待客户端请求连接。如果该属性设置为 0，Tomcat 将随机选择一个可用的端口号给当前 Connector 使用 |
| `protocol` | 当前 Connector 支持的访问协议。默认为 `HTTP/1.1`，并采用**自动切换机制**：根据本地是否含有 Tomcat 本地库（APR），选择基于 Java NIO 的连接器或基于本地 APR 的连接器 |
| `connectionTimeout` | Connector 接收连接后的**等待超时时间**，单位毫秒。**-1 表示不超时**。官方默认 60000（60 秒），但 Tomcat 自带 server.xml 中默认设为 **20000（20 秒）** |
| `redirectPort` | 当前 Connector 不支持 SSL 请求，收到符合 security-constraint 约束（需要 SSL 传输）的请求时，Catalina 自动将请求**重定向到指定端口**。默认 8443 |
| `executor` | 指定共享线程池的名称。也可以通过 `maxThreads`、`minSpareThreads` 等属性配置**内部线程池** |
| `URIEncoding` | 指定编码 URI 的字符编码。**Tomcat 8.x 默认 UTF-8**，Tomcat 7.x 默认 ISO-8859-1 |
| `compression` | 是否开启压缩（on/off/force） |
| `compressionMinSize` | 如果开启压缩，最小压缩大小（字节） |
| `maxThreads` | 内部线程池最大线程数（未引用共享 Executor 时生效） |
| `minSpareThreads` | 内部线程池最小空闲线程数 |
| `acceptCount` | 等待队列长度（见性能优化笔记） |
| `maxConnections` | 最大连接数（见性能优化笔记） |

**使用共享线程池的配置示例**：

```xml
<Service name="Catalina">
  <Executor name="tomcatThreadPool" namePrefix="catalina-exec-" maxThreads="200" minSpareThreads="20"/>
  <Connector port="8080" protocol="HTTP/1.1" executor="tomcatThreadPool" connectionTimeout="20000" redirectPort="8443"/>
</Service>
```

---

## 5. Engine 标签（Servlet 引擎）

**Engine 表示 Servlet 引擎**，管理多个虚拟站点（Host）。

```xml
<Engine name="Catalina" defaultHost="localhost">
  ...
</Engine>
```

| 属性 | 说明 |
|---|---|
| `name` | 指定 Engine 的名称，默认为 **Catalina** |
| `defaultHost` | 默认使用的虚拟主机名称。当客户端请求指向的主机无效时，将交由默认的虚拟主机处理，默认为 **localhost** |

---

## 6. Host 标签（虚拟主机）

**Host 用于配置一个虚拟主机**（一个站点）。

```xml
<Host name="localhost" appBase="webapps" unpackWARs="true" autoDeploy="true">
  ...
</Host>
```

| 属性 | 说明 |
|---|---|
| `name` | 虚拟主机名称 |
| `appBase` | 该虚拟主机的应用文件放在哪个目录下。**相对路径，相对 Tomcat 主目录** |
| `unpackWARs` | 是否自动解压 war 包 |
| `autoDeploy` | 资源有一定变更时，是否自动发布（热部署） |

---

## 7. Valve 标签（阀）

**Valve = 阀**，是请求处理管道中的拦截器（类似过滤器）。

```xml
<Valve className="org.apache.catalina.valves.AccessLogValve"
       directory="logs"
       prefix="localhost_access_log"
       suffix=".txt"
       pattern="%h %l %u %t &quot;%r&quot; %s %b" />
```

- 该标签**一般不怎么修改**
- 以上配置是请求过来产生的**访问日志**：存放地点（logs 目录）、名称（localhost_access_log.txt）、格式（pattern）等
- 常用 Valve：`AccessLogValve`（访问日志）、`RemoteAddrValve`（IP 过滤）等

---

## 8. Context 标签（Web 应用）

**Context 用于配置一个 Web 应用**。

```xml
<Context docBase="web_demo" path="/web_demo" reloadable="true"/>
```

| 属性 | 说明 |
|---|---|
| `docBase` | Web 应用目录或者 War 包的部署路径。可以是**绝对路径**，也可以是**相对于 Host appBase 的相对路径** |
| `path` | Web 应用的 Context 路径。如果 Host 名为 localhost，该值为 `web_demo`，则该 Web 应用访问的根路径为 `http://localhost:8080/web_demo` |
| `reloadable` | 是否监听 WEB-INF/classes 和 WEB-INF/lib 变化自动重载（开发用 true，生产建议 false） |

> 现代部署方式更多用 **war 包自动部署**（放到 appBase 目录即可），Context 标签在 server.xml 中手写较少（也可以放在 conf/Catalina/localhost/ 下单独文件配置）。

---

## 9. 完整配置示例与易错点

### 9.1 一份精简的完整 server.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Server port="8005" shutdown="SHUTDOWN">
  <Listener className="org.apache.catalina.startup.VersionLoggerListener"/>
  <Service name="Catalina">
    <Executor name="tomcatThreadPool" namePrefix="catalina-exec-"
              maxThreads="200" minSpareThreads="20"/>
    <Connector port="8080" protocol="HTTP/1.1"
               executor="tomcatThreadPool"
               connectionTimeout="20000"
               redirectPort="8443"
               URIEncoding="UTF-8"/>
    <Engine name="Catalina" defaultHost="localhost">
      <Host name="localhost" appBase="webapps" unpackWARs="true" autoDeploy="true">
        <Context docBase="web_demo" path="/web_demo" reloadable="true"/>
        <Valve className="org.apache.catalina.valves.AccessLogValve"
               directory="logs" prefix="localhost_access_log" suffix=".txt"
               pattern="%h %l %u %t &quot;%r&quot; %s %b"/>
      </Host>
    </Engine>
  </Service>
</Server>
```

### 9.2 易错点

1. **executor 与 maxThreads 二选一**：Connector 配置了 `executor` 后，`maxThreads`/`minSpareThreads` 等线程属性被忽略
2. **URIEncoding 默认值分版本**：Tomcat 8.x 默认 UTF-8，7.x 默认 ISO-8859-1（中文 URL 参数乱码排查点）
3. **shutdown 命令暴露风险**：8005 端口默认 SHUTDOWN 字符串，生产建议修改或关闭
4. **maxIdleTime 单位是毫秒**：默认 6000 = 1 分钟，不是 6000 秒
5. **port=0 随机端口**：Connector port 设为 0 会随机选端口（用于测试/集群动态分配）
6. **Context path 为空字符串**：`path=""` 表示根路径应用（`http://localhost:8080/` 直接访问）

---

## 面试追问 Q&A

### Q1：server.xml 中各组件层级关系？

答：Server → Service（可多个）→ {Listener, Executor, Connector×N, Engine} → Engine → Host×N → Context×N → Wrapper。Connector 与 Engine 通过 Service 绑定：Connector 负责接收，Engine 负责处理。

### Q2：Executor 和 Connector 的 maxThreads 什么关系？

答：Executor 是 Service 级共享线程池，Connector 可通过 `executor` 属性引用；引用后 Connector 自身的 maxThreads 等线程属性失效。不引用时 Connector 使用内部私有线程池。

### Q3：redirectPort 干什么用？

答：Connector 收到需要 SSL 传输的请求（符合 security-constraint 约束）时，将请求重定向到指定 HTTPS 端口（默认 8443）。是 HTTP→HTTPS 自动跳转的底层机制。

### Q4：Host 和 Context 的区别？

答：Host 是虚拟主机（一个站点，如 www.a.com），Context 是 Host 下的 Web 应用（一个应用，如 /web_demo）。一个 Host 可挂多个 Context，通过 path 区分。

---

*来源：wolai 笔记转存（Apache Tomcat 学习笔记第 2 章），参考 Apache Tomcat 8.5 官方配置文档补充，2026-08-08 整理*
