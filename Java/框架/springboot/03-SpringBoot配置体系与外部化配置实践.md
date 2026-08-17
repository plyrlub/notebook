---
tags: [Java, SpringBoot, 配置, 实践, Profile, yml, ConfigurationProperties, 框架]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringBoot外部化配置实战

> 版本基线：Spring Boot 2.x/3.x（3.x 为主）
> 受众：先读 [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)（优先级/原理），本篇只管"项目里到底怎么配、怎么切环境、怎么写代码"。有已归档代码即看本篇，概念不清回详解。
> 前置：[02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)；Spring Boot 项目已能起。

## 📋 总纲

1. 标准目录与文件组织（主配置 + 多环境文件）
2. yml 语法要点与易错点
3. 绑定配置到对象：@ConfigurationProperties 完整示例 ★
4. profile 多环境切换实战（dev/test/prod）
5. 外部化优先级的命令行/环境变量覆盖
6. 测试区配置与随机值
7. 实战组合：一套代码三套环境
8. 敏感配置与密钥管理 ★
9. 踩坑速查

## 1. 标准目录与文件组织

以官方 Initializer 生成的项目为准，配置都放在 `src/main/resources`：

```text
src/main/resources/
├── application.yml            # 主配置：公共项 + 激活环境
├── application-dev.yml        # 开发环境覆盖项
├── application-prod.yml       # 生产环境覆盖项
└── application-test.yml       # 测试环境覆盖项
```

> **命名规范**：环境名用 `dev`/`test`/`prod`（行业通用，别自创 `pro`/`qa1`）。多环境文件是"覆盖"关系——子文件里的值覆盖主文件同 key，未覆盖的沿用主文件。

## 2. yml 语法要点与易错点

| 易错点 | 反例 | 正例 |
| --- | --- | --- |
| 缩进不对 | 同一层缩进不齐 | 统一空 2 格，同一层对齐 |
| 端口当字符串 | `port: 8080`（对，数字） | 端口不写引号即可 |
| 带冒号的字符串 | `key: a:b`（解析错误） | `key: "a:b"` |
| 带 `#` 的字符串 | `key: #注释`（被当注释） | `key: "#值"` |
| 列表格式 | `k: [a,b]` 可用 | 但多行列表更要空格：`- a` |

**port 写字符串的坑**：`server.port: "8080"` 虽然能启动，但配置绑定为字符串，`@ConfigurationProperties` 转 `int` 时可能报类型转换错。默认不加引号即可。

## 3. 绑定配置到对象：@ConfigurationProperties（★ 核心）

**场景**：把一组自定义配置（如 JWT、OSS、短信）绑进一个 POJO，免写一堆 `@Value`。

配置文件 `application.yml`：

```yaml
app:
  jwt:
    secret: my-secret-key-here
    expire-hours: 12
    issuer: order-center
  oss:
    endpoint: https://oss-cn-hangzhou.aliyuncs.com
    bucket: my-bucket
    access-key-id: ${OSS_AK:defaultAk}   # 支持环境变量占位+默认值
```

对应配置类：

```java
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.jwt")
public record JwtProperties(String secret, int expireHours, String issuer) {}
```

```java
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties({JwtProperties.class})
public class JwtConfig {}
```

启用方式二选一（不要同时都用，会重复实例）：
- ① 注册类写法：如上 `@EnableConfigurationProperties(JwtProperties.class)`
- ② 组件扫描写法：在类上加 `@Component`（配合主类 `@ConfigurationPropertiesScan` 更快）

**使用**：

```java
@RestController
@RequestMapping("/auth")
public class AuthController {
    private final JwtProperties props;

    public AuthController(JwtProperties props) { this.props = props; }  // 构造器注入

    @GetMapping("/issuer")
    public String issuer() { return props.issuer() + " / " + props.expireHours(); }
}
```

> ★ 为什么用 record + 构造器注入，不用 `@Autowired` 字段注入：不可变、易于测试、Spring 官方推荐。record 的字段名即配置 key（`expireHours`→`expire-hours` 靠松散绑定自动转）。

### 松散绑定对照

| Java 字段 | yml key（均可） | 说明 |
| --- | --- | --- |
| `expireHours` | `expire-hours` / `expire_hours` / `expirehours` / `EXPIREHOURS` | 环境变量是大写+下划线 |

## 4. profile 多环境切换实战

`application.yml`（公共 + 激活）：

```yaml
spring:
  profiles:
    active: dev            # 默认激活 dev（可被命令行/环境变量覆盖）
server:
  port: 8080               # 公共端口
```

`application-dev.yml`：

```yaml
server:
  port: 8081
logging:
  level:
    com.example: debug
```

`application-prod.yml`：

```yaml
server:
  port: 8080
logging:
  level:
    com.example: warn
```

**优先级规则**：`application-{profile}.yml` **后加载、覆盖** `application.yml`。

**激活方式由弱到强**：

| 方式 | 示例 | 何时生效 |
| --- | --- | --- |
| 文件内 `spring.profiles.active` | `active: dev` | 默认 |
| 启动参数 | `--spring.profiles.active=prod` | 覆盖文件 |
| 环境变量 | `SPRING_PROFILES_ACTIVE=prod` | 覆盖文件 |
| 默认兜底属性文件 default | 见下 | 兜底 |

**多个同时激活**：`active: dev,local`（逗号分隔），后面的优先级更高。

### 默认 profile 兜底

```yaml
spring:
  profiles:
    default: dev    # 当没有任何激活时，才用 dev；一旦外部激活了就失效
```

> 常用于：本机没配任何 profile 时跑 dev，CI/服务器用外部变量显式指定，不会误落到 dev。

## 5. 外部化优先级的命令行/环境变量覆盖

**最高优先级 —— 命令行参数**（构建部署时最常用）：

```bash
# 启动 jar 时覆盖端口 & 激活环境
java -jar app.jar --server.port=9090 --spring.profiles.active=prod
```

**环境变量覆盖**（Docker/K8s 里最常用）：

```bash
export SERVER_PORT=9090
export SPRING_PROFILES_ACTIVE=prod
java -jar app.jar
```

> ★ 环境变量命名规则：把 `.` 换成 `_`，小写转大写（`server.port`→`SERVER_PORT`）。这是 12-factor 应用的核心：同一份 jar，靠外部变量切环境，代码零改动。

## 6. 测试区配置与随机值

`src/test/resources/application.yml`（测试用，覆盖主配置，不污染生产依赖）：

```yaml
server:
  port: 0                      # 0 = 随机端口，避免测试间端口冲突
spring:
  datasource:
    url: jdbc:h2:mem:testdb    # 用内存库当测试库
    driver-class-name: org.h2.Driver
```

随机值注入（常用于 mock 安全配置）：

```yaml
app:
  token: ${random.uuid}        # 每次启动随机 UUID
  retry: ${random.int[1,5]}     # 1~5 随机整数
```

## 7. 实战组合：一套代码三套环境

完整套路，目标是"代码一份、配置分层、外部接管"：

```text
src/main/resources/application.yml        # 只放公共 & 激活开关
src/main/resources/application-dev.yml    # 本地：端口8081、debug日志、本地库
src/main/resources/application-prod.yml   # 生产：生产库、加密密钥、warn日志
```

启动脚本 / 平台配置覆盖敏感项（密码/密钥/地址），绝不写死在 yml：

```bash
# 生产部署示例（K8s env 或 docker run -e）
java -jar app.jar \
  --spring.profiles.active=prod \
  --spring.datasource.password=${DB_PASSWORD} \
  --app.jwt.secret=${JWT_SECRET}
```

> 红线上：**密码、AK/SK、密钥一律不进 git、不进 yml**，用环境变量/配置中心/密钥管理（Vault/云 KMS）。明文落库=事故。

## 8. 敏感配置与密钥管理 ★

> 敏感信息（DB/Redis 密码、第三方 key、证书私钥）绝不落 yml/git 明文。业界按投入与安全等级，从"本地加密"到"独立密钥库"递进：**Jasypt 对称加密 → 配置中心密文托管 → Vault/KMS 密钥托管**。四段讲透：前三段是三档做法，最后一段是串起来的组合最佳实践。

### 8.1 对称加密：Jasypt + 主密码外部化（入门首选）

**原理**：一个主密码（对称）既加密又解密。配置文件里只存 `ENC(密文)`，主密码通过环境变量/启动参数外部注入，Spring 启动时自动解密注入——业务无感知。适合单体/小服务快速去掉明文。

```xml
<!-- pom.xml -->
<dependency>
  <groupId>com.github.ulisesbocchio</groupId>
  <artifactId>jasypt-spring-boot-starter</artifactId>
  <version>3.0.5</version>
</dependency>
```

```yaml
spring:
  datasource:
    password: ENC(2m3pL1kWABrzYW2M3sXHq0o)   # 密文，可提交仓库
jasypt:
  encryptor:
    password: ${JASYPT_PASSWORD}              # 主密码来自环境变量，文件里只有引用
    algorithm: PBEWITHHMACSHA512ANDAES_256
    iv-generator-classname: org.jasypt.iv.RandomIvGenerator
```

生成密文（明文字符串 → ENC 值）：

```bash
java -cp jasypt-1.9.3.jar org.jasypt.intf.cli.JasyptPBEStringEncryptionCLI \
  input="明文密码" password="YourMasterKey" \
  algorithm=PBEWITHHMACSHA512ANDAES_256 \
  ivGeneratorClassName=org.jasypt.iv.RandomIvGenerator
```

启动注入主密码（忌硬编码进文件/代码）：

```bash
export JASYPT_PASSWORD=YourMasterKey          # 环境变量
java -jar app.jar -Djasypt.encryptor.password=YourMasterKey  # 或启动参数
```

> **为什么叫"对称"**：一把主密码同时加/解密，密文放配置、钥匙放环境，**锁钥分离**。但钥匙本身仍是暴露点——这正是往上走到 Vault 的理由。

### 8.2 配置中心密文托管（微服务）

微服务用 Nacos/Apollo/Spring Cloud Config 集中管理配置时，**密码只存密文，不存明文**：用配置中心自身加密（`{cipher}`/KMS）存公钥加密后的密文，或直接存 Jasypt 密文。

**Spring Cloud Config：`{cipher}` + RSA keyStore**

```yaml
spring:
  datasource:
    password: '{cipher}AKCbpjDkjY12J58wEPoDl8qSqDZQPWJZaWKnoOabp0EDZaF2Vf...'
encrypt:
  keyStore:
    location: classpath:server.jks
    password: KeyStorePwd
    alias: mykey
```

```bash
# 加密（公钥），Config Server 存密文、私钥解密后下发客户端
curl -X POST https://config-server/encrypt -d '明文密码'
```

**Nacos + KMS（云）**：密文存 Nacos（`cipher-` 前缀 dataId），`encrypted_data_key` 保护，由云密钥服务 KMS 负责加解密。传输层再开 TLS。

> **定位**：配置中心管"配置"（可公开/可缓存/可同步），不是管"机密"的。即使加密，钥匙仍在配置中心体系内——仅比明文强一档。

### 8.3 Vault 密钥托管（企业级）

Vault 与配置中心**本质不同**：配置中心管理可公开的"配置"，Vault 管理"机密"——加密存储、按需下发、可撤销、动态密钥、全程审计、最小权限。适合银行/支付/大厂、合规要求高的场景。

```yaml
# bootstrap.yml：应用启动从 Vault 拉密钥（spring-cloud-vault-config）
spring:
  cloud:
    vault:
      host: vault.example.com
      port: 8200
      scheme: https
      authentication: TOKEN
      token: ${VAULT_TOKEN}        # token 外部化，勿随配置提交
      kv:
        enabled: true
        backend: secret
        default-context: myapp
```

```bash
# Vault 写入 / 读取 / 生成应用 token
vault kv put secret/myapp spring.datasource.password=YourPwd
vault kv get secret/myapp
vault token create                                      # 应用 token，设置 TTL/权限
```

> **Vault 核心价值**：机密**物理隔离**于配置，应用运行时动态拉取；可动态生成数据库密码（用完即废）、支持轮转与撤销、审计日志可追溯。

### 8.4 组合最佳实践（★ 落地推荐）

**立意**：钥匙（主密码/私钥）永远在"最安全处"——Vault/KMS 独立托管；锁（密文）散落在配置/配置中心，可进仓库。启动时从外部拉钥匙 → 解密密文 → 注入应用。

典型组合（Jasypt 打底 + 配置项外部化 + Vault 收口）：

```yaml
spring:
  datasource:
    password: ENC(BMnQEZkq7w2M3sXHq00Sm89Kf7Lm4pb7VgxY1cWz0E=)  # 配置里只有密文
# 钥匙：${JASYPT_PASSWORD} 由 Vault 拉取，环境变量注入，绝不落文件
```

启动时序（组合串联）：

1. 应用启动 → 连接 Vault/KMS，**拉取 Jasypt 主密码**（或非对称私钥）。
2. Jasypt 用拿到的钥匙解开 `ENC(密文)` → 明文注入 `@ConfigurationProperties`。
3. 密码只在**应用内瞬态存在**，日志/配置/仓库里全程无明文。

> **安全增益**：就算配置文件/仓库泄露，攻击者拿到密文也缺钥匙；钥匙在 Vault 有权限+审计，换钥匙只改 Vault 一处不碰代码。**动态生成公钥私钥**属于更高级形态，暂不展开。

## 9. 踩坑速查

- **Jasypt 主密码丢失**：密文不可逆、全部变废，**无法找回**——主密码必须严格外部托管。
- **老算法弱**：默认 `PBEWithMD5AndDES` 已被攻破风险，改为 `PBEWITHHMACSHA512ANDAES_256` + 随机 IV。
- **钥匙和锁同处一源**：主密码写进配置文件就白干；务必环境变量/独立密钥库。
- **`ENC()` 密文加引号**：yml 里 `ENC(...)` 值某些库要单引号包裹，否则被当 yml 类型处理。
- **Vault token 泄露**：token 别随 yml 提交；给最小权限 + TTL，走环境变量注入。

- **端口/字段被当字符串**：yml 值不该加引号的地方加了，`@ConfigurationProperties` 绑定 `int` 报类型转换。
- **配置类没生效**：既加了 `@Component` 又 `@EnableConfigurationProperties`，或 `prefix` 拼错（不报错但字段全 null）。
- **环境覆盖无效**：细读优先级，确认不是 `application.yml` 里 `active` 写死覆盖了外部参数；`default` 与 `active` 混用。
- **多 profile 覆盖方向反了**：`application-{profile}` 比 `application.yml` 优先级**高**（后者是公共底，前者是覆盖）。
- **record 参数名与 key 对不上**：松散绑定转不了（中文/特殊字符），字段用小写驼峰对齐英文 key。
- **测试吃生产配置**：`test` 目录没建 `application.yml`，测试类扫到 `main` 的 prod 配置导致连生产库。

## 10. 小结

- 一套代码 + 分层配置 + 外部变量接管 = 能上生产的配置体系。
- `@ConfigurationProperties` + record + 构造器注入是绑定自定义配置的正解。
- profile 用 `application-{profile}.yml` 覆盖主文件，激活优先级：命令行 > 环境变量 > 文件内 `active` > `default`。
- 敏感信息绝不落 yml/git；密钥管理见第 8 章（Jasypt/配置中心/Vault 三档 + 组合）。

## 11. 关联笔记

- 上一篇（详解版权威）：[02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)
- [02-SpringBoot配置体系与外部化配置详解](02-SpringBoot配置体系与外部化配置详解.md)：优先级全景/松散绑定/类型转换
- [01-SpringBoot启动原理与自动装配详解](01-SpringBoot启动原理与自动装配详解.md)：@ConfigurationProperties 在自动装配里如何配合条件注解
- orm 域 [07-Spring Boot集成与配置详解](../数据访问层/07-Spring Boot集成与配置详解.md)：数据源配置实战
- 中间件域 [01-Nacos配置·动态热加载详解](../../中间件/配置中心/Nacos/01-Nacos配置·动态热加载详解.md)：配置动态刷新（Nacos/Apollo/@RefreshScope）——springboot 单机配置的上限，微服务进阶

## 12. 参考资料

- [Spring Boot 官方：Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html)，查询日期 2026-08-15
- [Spring Boot 官方：Configuration Properties](https://docs.spring.io/spring-boot/reference/features/external-config.html#features.external-config.typesafe-configuration-properties)，查询日期 2026-08-15
- [Spring Boot 多环境配置与 Profile 实战（阿里云开发者社区）](https://developer.aliyun.com/article/1697844)，查询日期 2026-08-15
- [Jasypt 与 Spring Boot 集成配置加密（Baeldung 中文）](https://www.baeldung-cn.com/spring-boot-jasypt)，查询日期 2026-08-15
- [Spring Boot 保护敏感配置的 4 种方法（Java技术栈）](https://www.javastack.cn/spring-boot-encrypt-four-ways/)，查询日期 2026-08-15
- [Spring Cloud Config 加密与解密（Spring 官方）](https://docs.spring.java.cn/spring-cloud-config/reference/server/encryption-and-decryption.html)，查询日期 2026-08-15
- [Nacos 配置加密插件（Nacos 官网）](https://nacos.io/docs/latest/plugin/config-encryption-plugin/)，查询日期 2026-08-15
- [Spring Cloud Vault（Baeldung 中文）](https://www.baeldung-cn.com/spring-cloud-vault)，查询日期 2026-08-15
