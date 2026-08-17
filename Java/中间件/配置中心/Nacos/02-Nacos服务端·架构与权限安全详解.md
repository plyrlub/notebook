---
tags: [Java, 中间件, 配置中心, Nacos, 服务端, 权限, 安全, 集群, 学习笔记]
创建日期: 2026-08-16
状态: ✅ 已归档（01-学习/Java/中间件/配置中心/Nacos）
归属: 01-学习/Java/中间件/配置中心/Nacos
---

# Nacos 服务端 · 架构与权限安全详解

> 配套 Nacos 配置热加载（客户端篇 [01-Nacos配置·动态热加载详解](01-Nacos配置·动态热加载详解.md)）。本篇站在**服务端**视角：Nacos 整体架构、**2.x vs 3.x**、**权限控制（⭐）、安全**、**部署与集群**、命名空间/分组/DataID 组织模型。
> 声明：本机满足受控实操条件有限，本篇按官方文档 + 权威资料详细整理（**不可作强鉴权/公网部署的直接依据**，生产务必再核官方文档）。

## 📋 总纲

1. Nacos 是什么：三大能力 + 版本演进
2. 整体架构（Server 内部模块 + 端口）
3. **2.x vs 3.x 关键差异**（⭐）
4. 配置组织模型：命名空间 / 分组 / DataID（⭐使用）
5. **权限控制与鉴权**（⭐安全重心）
6. **安全最佳实践**（⭐）
7. 部署：单机 / 集群 / 持久化
8. 与 Apollo 对比（衔接）
9. 面试高频 Q&A
10. 参考

---

## 1. Nacos 是什么：三大能力 + 版本演进

**一句话**：Nacos = **服务注册与发现 + 配置管理 + 动态DNS（命名服务）** 三合一的开源基础设施，源于阿里,经双十一百万实例锤炼。

| 能力 | 解决什么 |
|---|---|
| 服务发现/注册中心 | 服务注册、健康检查、订阅通知（CP/AP 权衡）|
| 配置管理 | 集中管理配置、动态下发、历史版本、灰度 |
| 动态 DNS | 域名/命名服务（3.x 增强为 AI Registry）|

**版本演进**：
- **1.x**：HTTP 短连接、内置 Derby/MySQL。
- **2.x**：**gRPC 长连接**重构，性能/推送大幅提升；配置管理、容量、鉴权增强。
- **3.0（2025-04 GA）**：定位升级为 **AI Registry（AI Agent 应用注册中心）**；支持 **MCP（Model Content Protocol）**；按模块鉴权、控制台鉴权策略更严。

> 💡 记忆：**2.x 是"性能代"（gRPC），3.x 是"AI 代"（Registry + MCP + 强鉴权）**。

---

## 2. 整体架构（Server 内部模块 + 端口）

```
客户端 SDK / Console ---HTTP/gRPC--> Nacos Server(集群)
                                        │ 一致性协议(JRaft/Raft)
                                        │ 通信模块(HTTP+gRPC)
                                        │ 各插件(Auth/Persistence/Capacity...)
                                        ▼
                                   内置 Derby(单机) 或 外置 MySQL(集群)
```

**Nacos Server 内部基础模块**：一致性协议（JRaft）、通信模块（HTTP/gRPC 双栈）、配置管理、服务管理、命名空间、权限、容量/流量管理、缓存/容灾目录。

**关键端口**（部署必知）：

| 端口 | 偏移 | 用途 |
|---|---|---|
| **8848** | 0 | 主端口，控制台 + HTTP/OpenAPI |
| **9848** | +1000 | 客户端 gRPC（SDK 连这个）|
| **9849** | +1001 | 服务端间 gRPC 同步 |
| **7848** | -1000 | JRaft 请求（服务端间）|

> ⚠️ VIP/负载均衡：客户端走 HTTP 太慢，**gRPC 端更优**；VIP 要 TCP 转发（不能 http2 转发否则被断开）。9849/7848 是服务端间端口，**勿暴露公网**。

---

## 3. 2.x vs 3.x 关键差异（⭐）

| 维度 | 2.x | 3.x |
|---|---|---|
| 定位 | "云原生应用动态服务发现/配置/服务管理" | **"AI Agent 应用"注册中心**（升级）|
| 通信 | gRPC 长连接（对 1.x HTTP 是革命） | 延续 gRPC，**协议增强** |
| 新能力 | — | **MCP（Model Content Protocol）**、AI 服务管理 |
| 鉴权 | 简单 RBAC（弱鉴权）| **按 API 模块分类默认鉴权策略**、控制台鉴权更强 |
| 一致性 | JRaft（Raft 演进）| 延续，**可支撑 AI/百万规模** |
| 适用 | 生产主力 | 新项目/要 AI-Rregistry + 更强控制台 |

> 💡 **2.3/2.5 仍是很多生产主力**，3.x 追求 AI 场景 + 更严安全。选型：要 AI Registry/MCP → 3.x；常规微服务 → 2.5 或 3.x 均可（3.x 更前瞻）。

---

## 4. 配置组织模型：命名空间 / 分组 / DataID（⭐使用）

配置的**三级唯一标识**，权限和隔离都基于它：

```
namespaceId(命名空间) + groupName(分组) + dataId(配置集ID)
         租户隔离              分组                具体配置
```

| 维度 | 作用 | 例子 |
|---|---|---|
| **命名空间 Namespace** | **租户级隔离**（环境隔离 dev/test/prod、租户隔离）| `dev`/`prod`、`租户A` |
| **分组 Group** | 同一命名空间内再分组，区分相同 DataID | `DEFAULT_GROUP`、`BUY_GROUP` |
| **DataID 配置集ID** | 具体某份配置的唯一标识（类 Java 包命名）| `application.yaml`、`mysql.yaml` |

**DataID 命名惯例（推荐）**：
```yaml
# 常见: 应用名-环境.扩展名 or 应用名-模块.扩展名
application-dev.yaml     # 环境
user-service-datasource.yaml
log-level.properties
```
> DataID 只允许英文字母/数字和 `_.:-`，≤256 字节；group 仅 `_.:-` ≤128；namespaceId ≤64 用 `[\w-]`。

> 💡 **为什么三个维度**：不同环境（namespace）即便 DataID 相同也隔离；同一应用不同模块用分组区分；DataID 是最细粒度。权限可精确到某一 `namespace:group:dataId`。

---

## 5. 权限控制与鉴权（⭐ 安全重心）

### 5.1 定位：弱鉴权，不是强防护

> ⚠️ 官方原话要点：**Nacos 是内部组件，须在可信内网运行，不可暴露公网**。它提供**防止业务错用的弱鉴权**，**不是防止恶意攻击的强鉴权**。强鉴权诉求需自定义鉴权插件。

### 5.2 鉴权插件体系（3.2）

Nacos 鉴权由**插件**提供，3.2 内置三种，用同一套开关、但身份来源和权限模型不同：

| 模式 | 配置值 | 身份来源 | 权限模型 | 适用 |
|---|---|---|---|---|
| **默认 Nacos 鉴权** | `nacos` | 本地用户/角色/权限/token | Nacos 内 RBAC | 小部署、内网基础 |
| **LDAP 鉴权** | `ldap` | 企业 LDAP 用户目录 | LDAP 认证 + Nacos 管角色权限 | 已有 LDAP |
| **OIDC/OAuth2 鉴权** | `oidc` | 企业 SSO、统一身份、MFA | OIDC 认证 + Nacos 授权 | 企业 SSO |

### 5.3 开启鉴权 + RBAC（默认 nacos 模式）

```properties
# application.properties (服务端)
nacos.core.auth.enabled=true                 # 开启鉴权
nacos.core.auth.system.type=nacos            # 鉴权插件类型(默认)
# ★ 必须改强密钥! 2.2.0.1后无默认token密钥, 不设=安全风险
nacos.core.auth.plugin.nacos.token.secret.key=<生成强密钥Base64>
nacos.core.auth.plugin.nacos.token.expire.seconds=18000
# 控制台用户名密码(初始化即改)
# 控制台 → 权限控制 → 用户管理 创建用户/角色; 给角色配权限
```

**RBAC 三步**（控制台「权限控制」菜单）：
1. **用户管理**：创建用户，设密码。
2. **角色管理**：把用户绑到角色。
3. **权限管理**：给角色授权（**资源维度** = 命名空间/分组/配置/服务）。

**资源授权格式**：
```
{namespaceId}:{group}:{signType}/{resourceName}     # signType 如 config/service
例: public:DEFAULT_GROUP:config/example.properties    # 精确到某配置
    public:DEFAULT_GROUP:config/*                     # 该分组全部配置
```

### 5.4 客户端/OpenAPI 鉴权

开启鉴权后，所有访问都要带身份：
```bash
# OpenAPI 登录拿 token
curl -X POST '127.0.0.1:8848/nacos/v3/auth/user/login' \
  -d 'username=nacos&password=xxx'
# 拿到 accessToken, 之后每次请求 URL 带 accessToken=xxx 或在 header
```
```properties
# 客户端 SDK(Java): 配置加认证信息
username=nacos
password=xxx
```
> 🔥 **生产必配**：`token.secret.key` 改强随机值（默认值/弱值=可被伪造 token 的漏洞）；**控制台默认账号 nacos/nacos 必改**；开启鉴权后业务零依赖的 OpenAPI 会 403，需同步客户端。

---

## 6. 安全最佳实践（⭐）

| 措施 | 说明 |
|---|---|
| **内网隔离，不暴露公网** | Nacos 必须在可信内网，公网暴露=极大风险（官方红线）|
| **强密钥** | `token.secret.key` 用强随机 Base64，禁用默认值 |
| **改默认账号密码** | 控制台 `nacos/nacos`、用户密码初始化改掉 |
| **开启鉴权** | `auth.enabled=true` + RBAC 按最小权限授权 |
| **按环境分 namespace** | dev/test/prod 用不同命名空间 + 独立权限 |
| **只开必要端口** | 对外只 8848；9849/7848 服务端间端口不暴露 |
| **数据库隔离** | 数据库只允许 Nacos Server 访问，不外连 |
| **升级** | 用近期 patch（2.3.x/3.x 修复了历史 CVE）|
| **使用有治理** | 结合容量管理+流量管理防配置写爆 |

> 🔑 一句话：**Nacos 弱鉴权 + 内网隔离 + 强密钥 + 最小权限**，缺一不可；强安全性需求再自定义鉴权插件或前置网关。

---

## 7. 部署：单机 / 集群 / 持久化

### 7.1 单机（开发/演示）
```bash
# 单机模式(内嵌 Derby)
sh startup.sh -m standalone
# 或用 MySQL
# 1) 建库 + 导入 conf/mysql-schema.sql
# 2) application.properties 配 MySQL
spring.datasource.platform=mysql
```
> ⚠️ 单机默认 Derby 不支持集群、数据仅本机，**生产必须集群 + MySQL**。

### 7.2 集群（生产）
```bash
# 1. cluster.conf: 每行一个节点 IP:port
vi conf/cluster.conf
# 172.16.0.1:8848
# 172.16.0.2:8848
# 172.16.0.3:8848

# 2. 持久化到 MySQL(所有节点共用库)
spring.datasource.platform=mysql
spring.datasource.url=jdbc:mysql://dbhost:3306/nacos_config?...
spring.datasource.username=...
spring.datasource.password=...

# 3. 各节点改端口(可选)
server.port=8848
# 4. 推荐挂 VIP/域名, 各节点统一入口
```

**流量走向**（OpenAPI域名+SLB 内网模式）：
```
客户端/Console → VIP/SLB(内网) → Nacos 集群节点(8848/9848)
                             └→ 外置 MySQL(集群统一存储)
```
> 💡 集群节点都放一个 **VIP + 域名**下，换 IP 方便、客户端只配域名。数据库务必**外置共享**（集群用同一 MySQL 才一致）。

### 7.3 三种部署模式小结
| 模式 | 存储 | 高可用 | 适用 |
|---|---|---|---|
| 单机 | Derby/MySQL | 无 | 开发演示 |
| 集群 | 外置 MySQL | ✅ 多节点 | **生产主流** |
| 异地多活 | 多集群 | ✅✅ | 超大规模 |

---

## 8. 与 Apollo 对比（衔接）

| 维度 | Nacos | Apollo |
|---|---|---|
| 定位 | 配置 + 注册 + 动态DNS 三合一 | **纯配置中心**（专注治理）|
| 权限治理 | RBAC（弱鉴权,新建完善）| **成熟项目/环境/操作级权限**（编辑/发布分离、审计）|
| 灰度/回滚 | 支持(3.x增强) | **灰度发布、发布回滚**非常完善 |
| 部署 | 单/集群 + MySQL | Config/Admin/Portal 多组件 + 多环境 |
| 客户刷新 | gRPC 长连接快 | 长轮询(1s) |
| 适用 | 想一套搞定注册+配置 | 配置治理/多环境/权限审计诉求重 |

> 详见 [01-Apollo配置中心详解](../Apollo/01-Apollo配置中心详解.md)。

---

## 9. 面试高频 Q&A

- **Nacos 2.x 和 3.x 最大区别？** 2.x=gRPC长连接性能代；3.x=AI Registry+MCP+更强鉴权，定位升级。
- **Nacos 权限怎么做？** 开 `auth.enabled` + 默认 RBAC（用户/角色/权限，资源精确到 namespace:group:dataId），或用 LDAP/OIDC 插件。
- **为什么 Nacos 不能暴露公网？** 弱鉴权体系防业务错用，不防恶意攻击；必须内网 + 强密钥 + 最小权限。
- **命名空间/分组/DataID？** namespace租户隔离(环境)、group分组、dataId 具体配置；三级唯一标识。
- **开启鉴权要注意啥？** 改强 token.secret.key、改默认账号密码、客户端/OpenAPI 同步配身份，否则 403。
- **Nacos 集群怎么持久化？** cluster.conf + 外置共享 MySQL(导入 schema)；节点挂 VIP+域名。
- **端口？** 8848主/9848客户端gRPC/9849服务端同步/7848 Jraft。

---

## 10. 参考

- [Nacos 3.0 架构全景（官网 blog）](https://nacos.io/blog/nacos-gvr7dx_awbbpb_gzlzyehxberthsng/)
- [Nacos 权限校验（鉴权插件 RBAC）](https://nacos.io/docs/latest/manual/admin/auth/)
- [Nacos 鉴权插件（默认/LDAP/OIDC）](https://nacos.io/docs/latest/plugin/auth-plugin/)
- [Nacos 集群模式部署](https://nacos.io/docs/latest/manual/admin/deployment/deployment-cluster/)
- [Nacos 部署最佳实践（安全）](https://nacos.io/docs/latest/manual/admin/deployment/deployment-best-practices/)
- [Nacos 概念（namespace/group/dataId）](https://nacos.io/docs/latest/concepts/)
- [Nacos CLIENTS 配置鉴权信息](https://nacos.io/docs/latest/guide/user/auth/)
- 查证 2026-08：Nacos 2.5 / 3.0 / 3.2
- 关联：[01-Nacos配置·动态热加载详解](01-Nacos配置·动态热加载详解.md)、[01-Apollo配置中心详解](../Apollo/01-Apollo配置中心详解.md)、[00-中间件总览](../../00-中间件总览.md)
