---
tags: [gRPC, Protobuf, RPC, HTTP2, 微服务, 序列化, Java, Spring Boot]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/框架/服务通信）
归属: 01-学习/Java/框架/服务通信
---

# 05-gRPC详解

> 版本基线：gRPC（Google 开源，基于 HTTP/2 + Protobuf）+ proto3；Spring Boot 4.1 起原生支持 gRPC（spring-boot-starter-grpc-server，2026-06 InfoQ 报道）
> 受众：Java 后端开发，微服务间需要高性能 RPC，或想对比 [04-Apache Dubbo详解](04-Apache Dubbo详解.md) 的另一条技术路线。默认你懂 HTTP/2（**04-HTTP2与HTTP3详解**（见知识库））、微服务概念。
> 关联笔记：[00-RPC与远程调用总览](00-RPC与远程调用总览.md)、[04-Apache Dubbo详解](04-Apache Dubbo详解.md)、[06-OpenFeign详解](06-OpenFeign详解.md)

## 📋 总纲

- 1. gRPC 是什么：定位与设计目标
- 2. 核心技术栈：HTTP/2 + Protobuf
- 3. Protobuf 与 .proto 文件
- 4. 四种调用模式
- 5. 与 REST/Dubbo 的对比
- 6. Spring Boot 集成（服务端）
- 7. Spring Boot 集成（客户端）
- 8. 生产实践与踩坑

## 学习目标

学完本篇你能：

1. 说清 gRPC 的定位：高性能 RPC 框架，跨语言、基于 HTTP/2 + Protobuf
2. 写出 .proto 文件并理解 protoc 代码生成流程
3. 说出四种调用模式（Unary/Server streaming/Client streaming/Bidi streaming）
4. 对比 gRPC vs REST vs Dubbo 的适用场景
5. 在 Spring Boot 中实现 gRPC 服务端与客户端
6. 知道 gRPC 的生产实践要点（拦截器/重试/负载均衡/协议转码）

## 前置知识

- **04-HTTP2与HTTP3详解**（见知识库）——HTTP/2 多路复用是 gRPC 的传输基础
- [00-RPC与远程调用总览](00-RPC与远程调用总览.md)——RPC 概念与方案对比
- 需掌握：微服务、序列化、Spring Boot 基础

---

## 1. gRPC 是什么：定位与设计目标

**一句话记忆**：gRPC 是 Google 开源的高性能 RPC 框架——**用 .proto 定义接口，Protobuf 做序列化，HTTP/2 做传输**，目标是"像调用本地方法一样调用远程服务"，且跨语言。

**核心设计目标**（官方）：

| 目标 | 说明 |
|---|---|
| **跨语言** | 客户端/服务端可用不同语言（Java 服务端 ↔ Go/Python 客户端） |
| **高性能** | 二进制序列化（Protobuf）+ HTTP/2 多路复用 |
| **接口先行** | .proto 是唯一契约，自动生成代码，杜绝接口不一致 |
| **流式支持** | 四种调用模式覆盖普通/流式场景 |

> 💡 **记忆锚点**：gRPC = **IDL（.proto 契约）+ 二进制序列化 + HTTP/2 传输**。对比 REST 的"JSON + HTTP 约定"，gRPC 是"强契约 + 高效传输"。

---

## 2. 核心技术栈：HTTP/2 + Protobuf

### 2.1 为什么用 HTTP/2

gRPC 跑在 HTTP/2 上（**04-HTTP2与HTTP3详解**（见知识库）），利用：

| HTTP/2 特性 | gRPC 利用方式 |
|---|---|
| **多路复用** | 一条连接并发多个 RPC 调用 |
| **二进制帧** | 配合 Protobuf 二进制消息，传输高效 |
| **头部压缩（HPACK）** | 减少重复头部开销 |
| **流（Stream）** | 支撑流式调用模式（见第 4 节） |

### 2.2 为什么用 Protobuf

| 对比 | Protobuf（二进制） | JSON（文本） |
|---|---|---|
| 体积 | 小（约 JSON 的 1/3~1/5） | 大 |
| 序列化速度 | 快（无需解析文本） | 慢 |
| 可读性 | 差（二进制） | 好 |
| 类型安全 | 强（schema 生成代码） | 弱 |
| 跨语言 | 官方支持多语言 | 天然支持 |

---

## 3. Protobuf 与 .proto 文件

### 3.1 基本语法（proto3）

```protobuf
syntax = "proto3";                    // 使用 proto3 版本

option java_package = "com.example.grpc.proto";   // Java 包名
option java_multiple_files = true;    // 每个消息生成独立文件

// 定义服务:方法 + 请求/响应类型
service HelloWorld {
    rpc SayHello (HelloRequest) returns (HelloReply) {}
}

// 定义消息(数据结构)
message HelloRequest {
    string name = 1;                  // 字段名 + 类型 + 唯一编号
}

message HelloReply {
    string message = 1;
}
```

**关键规则**：
- 字段必须带唯一编号（1, 2, 3...），编号用于二进制编码标识
- 常用类型：string/int32/bool/bytes/嵌套 message/repeated(数组)
- `option java_package` 控制生成代码的包名

### 3.2 代码生成流程

```
.proto 文件 (src/main/proto/xxx.proto)
      │ protoc + gRPC 插件
      ▼
生成 Java 代码: 消息类 + 服务基类(XXXGrpc)
      │
      ▼
服务端: 继承 XXXGrpc.XXXImplBase 实现方法
客户端: 用 XXXGrpc.newBlockingStub/NewStub 调用
```

**Maven 集成**（Spring Boot 4.x 用 protobuf-maven-plugin，boot parent 自动配好 protoc 版本）：

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.0</version>
</parent>
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-grpc-server</artifactId>
    </dependency>
</dependencies>
<build>
    <plugins>
        <plugin>
            <groupId>io.github.ascopes</groupId>
            <artifactId>protobuf-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
<!-- .proto 放 src/main/proto/ -->
```

---

## 4. 四种调用模式 ★

gRPC 根据 HTTP/2 的流能力，支持四种调用模式：

| 模式 | 请求 | 响应 | 场景 |
|---|---|---|---|
| **Unary（一元）** | 1 个 | 1 个 | 普通请求-响应（最常见） |
| **Server streaming** | 1 个 | 多个流式 | 服务端推送（如订阅通知、下载） |
| **Client streaming** | 多个流式 | 1 个 | 客户端上传（如批量上报、上传） |
| **Bidi streaming（双向）** | 多个流式 | 多个流式 | 实时双向通信（如聊天、实时协作） |

```protobuf
// 四种模式定义示例
service ChatService {
    rpc GetUser (UserRequest) returns (UserReply);                    // Unary
    rpc Subscribe (SubRequest) returns (stream Event);                // Server streaming
    rpc Upload (stream Chunk) returns (UploadReply);                  // Client streaming
    rpc Chat (stream Message) returns (stream Message);               // Bidi streaming
}
```

> 💡 **记忆锚点**：**看"stream"关键字在哪边**——`returns (stream X)` 是服务端流，`(stream X) returns` 是客户端流，两边都有是双向流。

---

## 5. 与 REST/Dubbo 的对比

| 维度 | gRPC | REST (HTTP/JSON) | Dubbo |
|---|---|---|---|
| 协议 | HTTP/2 + Protobuf | HTTP/1.1 + JSON | 自定义 TCP 协议（可配） |
| 序列化 | Protobuf（二进制） | JSON（文本） | Hessian/Kryo/JSON |
| 契约 | .proto 强契约 | OpenAPI（可选） | 接口（Java 绑定） |
| 跨语言 | ✅ 强 | ✅ 天然 | ⚠️ 弱（Java 为主） |
| 流式 | ✅ 四种模式 | ❌ 需 SSE/WebSocket | 有限 |
| 浏览器直调 | ⚠️ 需转码(gRPC-Web) | ✅ 原生 | ❌ |
| 服务治理 | 需外部组件 | 无 | ✅ 内置(注册中心/负载均衡) |
| 生态 | Google/CNCF | 最广 | 阿里/国内 |

**选型建议**：
- **对外 API（浏览器/第三方）** → REST（浏览器原生支持）
- **内部服务间高性能调用** → gRPC（效率高、强契约）或 Dubbo（Java 生态治理好）
- **跨语言微服务** → gRPC 优势明显（Protobuf 天然跨语言）
- **Java 单体微服务、要服务治理** → Dubbo（[04-Apache Dubbo详解](04-Apache Dubbo详解.md)）

---

## 6. Spring Boot 集成（服务端）

### 6.1 依赖 + .proto

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-grpc-server</artifactId>
</dependency>
```

`src/main/proto/hello.proto`（见第 3 节示例）。

### 6.2 实现服务

```java
import io.grpc.stub.StreamObserver;
import org.springframework.grpc.server.service.GrpcService;

@GrpcService                        // 注册为 gRPC 服务
public class MyHelloWorldService extends HelloWorldGrpc.HelloWorldImplBase {

    @Override
    public void sayHello(HelloRequest request, StreamObserver<HelloReply> responseObserver) {
        String message = "Hello '%s'".formatted(request.getName());
        HelloReply reply = HelloReply.newBuilder().setMessage(message).build();
        responseObserver.onNext(reply);      // 发送响应
        responseObserver.onCompleted();      // 完成
    }
}
```

**要点**：
- `@GrpcService` 注解 + 继承生成的 `XXXImplBase` → 自动暴露为 gRPC 服务
- 默认 Netty 实现，监听 **9090 端口**（`spring.grpc.server.port` 可配）
- 响应通过 `StreamObserver` 回调（onNext/onCompleted）

---

## 7. Spring Boot 集成（客户端）

### 7.1 配置 + Stub

```java
// 创建连接(测试用 NettyChannelBuilder)
ManagedChannel channel = NettyChannelBuilder
        .forAddress("localhost", 9090)
        .usePlaintext()                      // 明文(生产用 TLS)
        .build();

// 三种 Stub:
HelloWorldGrpc.HelloWorldBlockingStub blockingStub =   // 同步阻塞
        HelloWorldGrpc.newBlockingStub(channel);
HelloWorldGrpc.HelloWorldFutureStub futureStub =       // Future 异步
        HelloWorldGrpc.newFutureStub(channel);
HelloWorldGrpc.HelloWorldStub asyncStub =              // 异步流式
        HelloWorldGrpc.newStub(channel);
```

### 7.2 调用

```java
// 同步调用
HelloRequest request = HelloRequest.newBuilder().setName("Spring").build();
HelloReply reply = blockingStub.sayHello(request);
System.out.println(reply.getMessage());   // Hello 'Spring'

// 异步(流式)调用:用 StreamObserver 回调
asyncStub.sayHello(request, new StreamObserver<HelloReply>() {
    @Override public void onNext(HelloReply value) { /* 收到响应 */ }
    @Override public void onError(Throwable t) { /* 出错 */ }
    @Override public void onCompleted() { /* 完成 */ }
});
```

**测试**：Spring Boot 提供 `@LocalGrpcServerPort`（随机端口）+ 进程内测试传输，避免连真实服务。

---

## 8. 生产实践与踩坑

### 8.1 生产实践

| 实践 | 说明 |
|---|---|
| **TLS 加密** | 生产必须 TLS（gRPC 默认支持），`usePlaintext` 仅限开发 |
| **拦截器** | 认证/日志/限流用 ServerInterceptor（类似 Spring 拦截器） |
| **重试策略** | gRPC 内置 retry policy（按状态码配置重试次数） |
| **负载均衡** | 客户端 LB（如 xDS/Consul/etcd 集成） |
| **Deadline 超时** | 每个调用设 deadline，避免无限等待 |
| **gRPC-Web 转码** | 浏览器访问用 grpc-web 或 grpc-gateway（REST 转 gRPC） |
| **健康检查** | grpc-health-probe 配合 K8s 探活 |

### 8.2 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #G1 | .proto 字段编号重复 | 解析错乱 | 编号一旦发布不可改（兼容性） |
| #G2 | proto2/proto3 混用 | 兼容问题 | 统一 proto3 |
| #G3 | 忘记 deadline | 调用挂死 | 每个 RPC 设置 deadline |
| #G4 | 生产用 usePlaintext | 数据明文 | 配置 TLS |
| #G5 | 大消息默认限制 4MB | 传输失败 | 调整 maxInboundMessageSize |
| #G6 | 浏览器直连失败 | CORS/协议不支持 | 用 gRPC-Web 或 grpc-gateway 转码 |

## 小结

- gRPC = IDL(.proto) + Protobuf(二进制) + HTTP/2(传输)，跨语言高性能
- 四种调用模式：Unary / Server streaming / Client streaming / Bidi streaming
- 强契约、高效、流式是三大优势；浏览器直调弱是短板
- Spring Boot 4.1 原生支持：@GrpcService 服务端 + 三种 Stub 客户端
- 选型：对外 REST，内部高性能/跨语言 gRPC，Java 治理 Dubbo

## 下一篇

[06-OpenFeign详解](06-OpenFeign详解.md)——Spring 生态声明式 HTTP 客户端

## 参考资料

- [gRPC 官方文档: Introduction](https://grpc.io/docs/what-is-grpc/introduction/)，查询日期：2026-08-09
- [Spring Boot Reference: gRPC](https://docs.spring.io/spring-boot/reference/io/grpc.html)，查询日期：2026-08-09
- [InfoQ: Spring Boot 4.1 Adds gRPC Auto-Configuration](https://www.infoq.com/news/2026/06/spring-boot-4-1/)，查询日期：2026-08-09
- [Protocol Buffers 官方文档](https://protobuf.dev/overview)，查询日期：2026-08-09
