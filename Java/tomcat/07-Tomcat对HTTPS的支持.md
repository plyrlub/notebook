---
tags: [Java, Tomcat, HTTPS, SSL, TLS, keytool, 证书]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
---

# Tomcat对HTTPS的支持

> 本文是 Tomcat 学习笔记第 6 章。讲解 HTTPS 原理、浏览器握手流程，以及 Tomcat 配置 HTTPS 的具体步骤。
> 关联笔记：[00-Tomcat总览](00-Tomcat总览.md)、[02-Tomcat服务器核心配置详解](02-Tomcat服务器核心配置详解.md)、[08-Tomcat性能优化策略](08-Tomcat性能优化策略.md)

## 📋 总纲

1. HTTPS 简介
2. HTTPS 与 HTTP 的主要区别
3. HTTPS 浏览器连接（握手）流程
4. Tomcat 配置 HTTPS 支持（keytool 演示）

---

## 1. HTTPS 简介

参考：https://zh.wikipedia.org/wiki/超文本传输安全协议

**超文本传输安全协议**（HyperText Transfer Protocol Secure，缩写 HTTPS；常称为 HTTP over TLS、HTTP over SSL 或 HTTP Secure）是一种**通过计算机网络进行安全通信的传输协议**。HTTPS 经由 HTTP 进行通信，但利用 **SSL/TLS 来加密数据包**。

- HTTPS 开发的主要目的：提供对**网站服务器的身份认证**，保护交换资料的**隐私与完整性**
- 由网景公司（Netscape）在 **1994 年首次提出**，随后扩展到互联网上
- 历史上，HTTPS 连接经常用于**万维网上的交易支付**和企业信息系统中敏感信息的传输
- 2000 年代末至 2010 年代初，HTTPS 开始广泛使用，以确保各类型的网页真实，保护账户和保持用户通信、身份和网络浏览的私密性
- 另外还有一种**安全超文本传输协议（S-HTTP）** 的 HTTP 安全传输实现，但 HTTPS 的广泛应用使其成为事实上的 HTTP 安全传输实现，S-HTTP 并没有得到广泛支持

### 1.1 主要作用

HTTPS 的主要作用是在不安全的网络上**创建一个安全信道**，并可在使用适当的加密包和服务器证书可被验证且可被信任时，对**窃听和中间人攻击**提供合理的防护。

HTTPS 的信任基于预先安装在操作系统中的**证书颁发机构（CA）**。因此，与一个网站之间的 HTTPS 连线仅在这些情况下可被信任：

1. 浏览器正确地实现了 HTTPS 且操作系统中安装了正确且受信任的证书颁发机构
2. 证书颁发机构仅信任合法的网站
3. 被访问的网站提供了一个**有效的证书**（由操作系统信任的证书颁发机构签发，大部分浏览器会对无效的证书发出警告）
4. 该证书正确地验证了被访问的网站（例如访问 https://example.com 时收到签发给 example.com 而不是其它域名的证书）
5. 此协议的加密层（SSL/TLS）能够有效地提供认证和高强度的加密

> HTTPS 不应与在 RFC 2660 中定义的安全超文本传输协议（S-HTTP）相混淆。

### 1.2 HTTPS 和 HTTP 的主要区别

| 对比项 | HTTP | HTTPS |
|---|---|---|
| 证书 | 不需要 | 需要到电子商务认证授权机构 CA 申请 SSL 证书 |
| 默认端口 | **8080**（Tomcat 默认；标准为 80） | **443**（Tomcat 默认演示 8443） |
| 加密 | 明文传输，不安全 | SSL/TLS 加密传输，安全性高 |
| 本质 | 无状态、不安全的协议 | SSL+HTTP 构建，可加密传输、身份认证 |
| 连接 | 直接 TCP | 先 TCP 再 TLS 握手 |

### 1.3 HTTPS 浏览器连接（握手）流程

```
① 浏览器将自己支持的一套加密规则（加密套件列表）发送给网站
② 网站从中选择出一组加密算法，并将自己的身份信息以证书的形式发回给浏览器
   （证书中包含网站地址、加密公钥、证书的颁发机构等信息）
③ 浏览器获得网站证书之后要验证证书合法性：
   - 证书结构是否合法
   - 证书中包含的网站地址是否与正在访问的地址一致等
   - 若证书受信任，浏览器栏显示 🔐；否则给出证书不可信提示
④ 如果证书受信任（或用户接受不受信的证书），浏览器生成一串随机数密码，
   并用证书中提供的公钥加密
⑤ 使用公钥加密后的随机数密码加密握手信息，之后发给网站
⑥ 网站接受浏览器发来的数据做如下操作：
   - 使用私钥解密出密码
   - 使用密码解密握手信息
   - 使用密码再加密一段握手信息，发给浏览器
⑦ 浏览器解密并计算握手信息的 Hash，如果与服务器端发送来的 Hash 一致，握手结束
⑧ 之后所有的通信数据由之前浏览器生成的随机密码并利用对称加密算法进行加密
```

**握手本质总结**：

- **非对称加密（公钥/私钥）**：只用于安全地交换"随机密码"（会话密钥），解决密钥分发问题
- **对称加密**：握手成功后，实际数据传输用会话密钥 + 对称加密算法（快）
- **证书**：用于身份认证，防止中间人冒充服务器

---

## 2. Tomcat 配置 HTTPS 支持

### 2.1 使用 JDK 免费工具演示

**① 使用 JDK 中 Keytool 工具生成免费的密钥库文件**

```bash
keytool -genkeypair -alias tomcat -keyalg RSA -keysize 2048 \
        -validity 3650 -keystore /path/to/tomcat.keystore \
        -storepass changeit -dname "CN=localhost, OU=dev, O=dev, L=city, ST=state, C=CN"
```

- `-genkeypair`：生成密钥对（公钥+私钥）
- `-keyalg RSA -keysize 2048`：RSA 算法，2048 位
- `-validity 3650`：有效期 10 年（演示用）
- `-storepass`：密钥库口令
- `-dname`：证书主体信息（CN 要和服务域名一致）

**② 配置 conf/server.xml**

在 server.xml 中为 HTTPS 连接器添加 `SSLEnabled` 配置：

```xml
<Connector port="8443"
           protocol="org.apache.coyote.http11.Http11NioProtocol"
           maxThreads="150"
           SSLEnabled="true"
           scheme="https"
           secure="true"
           clientAuth="false"
           sslProtocol="TLS"
           keystoreFile="/path/to/tomcat.keystore"
           keystorePass="changeit" />
```

关键属性：

| 属性 | 说明 |
|---|---|
| `SSLEnabled="true"` | 开启 SSL |
| `scheme="https" secure="true"` | 标记为 HTTPS 安全连接 |
| `sslProtocol="TLS"` | 使用 TLS 协议 |
| `keystoreFile` | 密钥库文件路径 |
| `keystorePass` | 密钥库口令（与 keytool 的 -storepass 一致） |
| `clientAuth="false"` | 不要求客户端证书（单向认证） |

**③ 访问对应端口**

```
https://localhost:8443/
```

浏览器访问时因为是自签名证书（非 CA 签发），会提示证书不可信——**演示环境点继续访问即可**；生产环境必须使用 CA 签发的正式证书。

---

## 面试追问 Q&A

### Q1：HTTPS 握手为什么先用非对称加密再转对称加密？

答：非对称加密（RSA/ECC）安全但慢，适合少量数据；对称加密（AES）快但需要双方共享密钥。方案：用非对称加密安全地交换"随机会话密钥"，之后用对称加密传输实际数据——兼顾安全与性能。

### Q2：自签名证书和 CA 证书的区别？

答：自签名证书自己签自己，浏览器不认识签发机构 → 提示不可信；CA 证书由浏览器内置信任的机构签发 → 自动受信。演示/内网可用自签名，公网必须 CA 证书。

### Q3：Tomcat 配置 HTTPS 的关键步骤？

答：① keytool 生成密钥库；② server.xml 添加 SSLEnabled 的 Connector（指定 keystoreFile/keystorePass）；③ 访问 https 端口验证。生产还需用 CA 证书替换自签名。

---

> 参考：官方文档（keytool/server.xml 命令细节）
