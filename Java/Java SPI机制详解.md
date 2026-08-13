---
tags: [Java, SPI, 机制, Spring, Dubbo]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/核心机制）
归属: 01-学习/Java/核心机制
---

# Java SPI机制详解（JDK / Spring / Dubbo / Servlet）

## 📋 总纲

1. 基本概念：SPI 是什么、与 API 的区别、适用场景
2. JDK SPI：ServiceLoader 机制 + 手写 Demo + 经典实例
3. Spring SPI：spring.factories / AutoConfiguration.imports + Demo
4. Dubbo SPI：ExtensionLoader + @SPI/@Adaptive/@Activate/Wrapper + Demo
5. Servlet 规范 SPI：ServletContainerInitializer（Tomcat 加载）
6. 三大机制对比表 + 常见实例速查
7. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 SPI 是什么

**SPI = Service Provider Interface（服务提供者接口）**：接口由框架定义，实现由第三方提供，框架通过**约定位置**自动发现并加载实现。

```java
// 框架只定义接口，不写实现
public interface Payment { String pay(BigDecimal amount); }

// 第三方各自实现，放进约定的配置目录
// META-INF/services/com.example.spi.Payment
//   com.example.spi.impl.Alipay
//   com.example.spi.impl.WechatPay

// 框架侧：一行代码拿到所有实现，谁接入谁生效
ServiceLoader<Payment> loader = ServiceLoader.load(Payment.class);
```

**核心思想**：控制反转（IoC）的一种 —— 不是「框架依赖具体实现」，而是「第三方实现主动被框架发现」。

### 1.2 SPI vs API

    API：调用方按接口调，实现是固定的 —— 「你用我的」
    SPI：框架定义接口，等第三方实现接入 —— 「我用你的」

    API 演进会破坏调用方；SPI 演进不破坏实现方（只要接口不变）

### 1.3 适用场景

① 框架的可插拔扩展：日志（SLF4J）、数据库驱动（JDBC）、序列化
② 解耦核心与实现：核心框架不依赖任何具体厂商实现
③ 多实现共存按需选择：Dubbo 的协议/负载均衡/注册中心全是 SPI

---

## 2. JDK SPI（ServiceLoader）

### 2.1 机制

**约定目录**：`META-INF/services/<接口全限定名>`

文件内容：每行一个实现类的全限定名（# 开头为注释）

**加载流程**
- `ServiceLoader.load(接口.class)` 拿到 loader（懒加载，不立即实例化）
- 遍历时：`ClassLoader.getResources("META-INF/services/接口名")` 找到**所有 jar** 里的服务文件
- 读取类名 → `Class.forName` → 反射实例化（**必须有 public 无参构造**）

### 2.2 手写 Demo ★

```java
// ① 定义接口
public interface Payment {
    String pay(BigDecimal amount);
}

// ② 实现一
public class Alipay implements Payment {
    @Override public String pay(BigDecimal amount) { return "支付宝支付 " + amount; }
}

// ③ 实现二
public class WechatPay implements Payment {
    @Override public String pay(BigDecimal amount) { return "微信支付 " + amount; }
}

// ④ 配置文件：META-INF/services/com.example.spi.Payment
//    内容：
//    com.example.spi.impl.Alipay
//    com.example.spi.impl.WechatPay

// ⑤ 加载使用
ServiceLoader<Payment> loader = ServiceLoader.load(Payment.class);
for (Payment p : loader) {
    System.out.println(p.pay(new BigDecimal("100")));
}
```

**注意点**
- 文件名**必须等于接口全限定名**，路径、大小写都不能错（错了静默不加载，很坑）
- 文件编码 UTF-8（JDK 9+ 默认 UTF-8 读取）
- 实现类必须有 **public 无参构造**（反射 newInstance）
- 多个 jar 提供同名服务文件：全部加载（会冲突，见 7.9）

### 2.3 经典实例

| 实例 | 服务文件 | 说明 |
|------|---------|------|
| JDBC 驱动 | `META-INF/services/java.sql.Driver` | JDBC 4.0+ DriverManager 自动加载，**不用再 Class.forName** |
| JPA 实现 | `javax.persistence.spi.PersistenceProvider` | Hibernate / EclipseLink 接入 |
| Bean Validation | `jakarta.validation.spi.ValidationProvider` | Hibernate Validator 接入（参数校验那篇聊过） |
| 脚本引擎 | `javax.script.ScriptEngineFactory` | Nashorn/GraalJS |
| 字符集 | `java.nio.charset.spi.CharsetProvider` | 自定义字符集 |
| 文件系统 | `java.nio.file.spi.FileSystemProvider` | NIO.2 自定义文件系统 |

### 2.4 缺点（被诟病的点）

- **平铺加载**：不能按名字拿指定实现，只能全遍历
- **无优先级/排序**：多个实现顺序不可控
- **无 IoC**：实例自己 new，依赖注入要自己处理
- **实例化浪费**：遍历时所有实现全 new（哪怕只用其中一个）
- **异常不友好**：配置错误抛 ServiceConfigurationError，难排查

---

## 3. Spring SPI

### 3.1 是什么

Spring 基于 **SpringFactoriesLoader** 的 SPI 机制，配置放 `META-INF/spring.factories`（properties 格式）。

**演进**（Spring Boot 自动装配的配置文件）

    旧：META-INF/spring.factories
        org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
        com.example.autoconfigure.MyAutoConfiguration

    新（Spring Boot 2.7+/3.x）：META-INF/spring/
        org.springframework.boot.autoconfigure.AutoConfiguration.imports
        com.example.autoconfigure.MyAutoConfiguration

**相比 JDK SPI 的改进**
- **key-value**：一个文件可以配多个接口（一行一个 key，值逗号分隔）
- **有序**：支持 @Order / @AutoConfigureOrder / 配置顺序
- **工厂方法**：loadFactories 可以自定义实例化逻辑

### 3.2 手写 Demo ★

```java
// ① 接口 + 实现
public interface HelloService { String hello(); }
public class HelloServiceImpl implements HelloService {
    @Override public String hello() { return "hello from spring spi"; }
}

// ② 配置文件 META-INF/spring.factories：
//    com.example.spi.HelloService=com.example.spi.impl.HelloServiceImpl

// ③ 加载
List<HelloService> services =
        SpringFactoriesLoader.loadFactories(HelloService.class, null);
// 注意：Spring 6 / Boot 3 中位于 org.springframework.core.io.support 包
```

### 3.3 经典实例

- **Spring Boot 自动装配**：AutoConfiguration.imports（最出名，starter 机制的基础）
- `EnvironmentPostProcessor`：环境后处理（如读取自定义配置源）
- `ApplicationContextInitializer`：容器刷新前回调
- `ApplicationListener` / `SpringApplicationRunListener`：生命周期监听
- 自定义 `HttpMessageConverter`、`PropertySourceLoader` 等扩展点

### 3.4 与 JDK SPI 对比

    JDK SPI                    Spring SPI
    一接口一文件                一文件多接口（key-value）
    无顺序                     支持 Ordered 排序
    ServiceLoader.load          SpringFactoriesLoader.loadFactories
    反射直接 new                工厂方法，可自定义创建逻辑
    无容器支持                  Spring 容器内，可注入依赖

---

## 4. Dubbo SPI

### 4.1 为什么 Dubbo 要自己写一套

JDK SPI 的缺点 Dubbo 全踩：不能按名加载、不能自适应、无 IoC、无 AOP。而 Dubbo 的协议、序列化、负载均衡、注册中心全部需要「配置里写个名字就能切换实现」→ 必须重写一套更强的。

### 4.2 机制

**① @SPI 注解**

```java
@SPI("dubbo")        // 标注接口，可指定默认实现名
public interface Protocol { String speak(String name); }
```

**② 约定目录（优先级从高到低）**

    META-INF/dubbo/              ← 用户自定义扩展（优先）
    META-INF/dubbo/internal/     ← dubbo 内部扩展
    META-INF/services/           ← 兼容 JDK SPI 目录

文件格式是 **key=value**（别名=实现类）：

    dubbo=com.example.spi.impl.DubboProtocol
    http=com.example.spi.impl.HttpProtocol

**③ 按名加载**

```java
ExtensionLoader<Protocol> loader = ExtensionLoader.getExtensionLoader(Protocol.class);
Protocol dubbo = loader.getExtension("dubbo");   // 按别名拿指定实现
Protocol http = loader.getExtension("http");
```

**④ @Adaptive（自适应扩展）**

- 方法级 `@Adaptive`：运行时**动态生成代理类**，根据参数（如 URL 里的协议名）自动选择实现 —— 调用方不用写死用哪个
- 例：`Protocol` 接口的 `getAdaptiveExtension()`，调用时按 URL 的 protocol 字段路由到 dubbo/http

**⑤ @Activate（条件激活）**

- 按条件自动生效的扩展点（如过滤器），支持 order 排序、group 分组过滤
- 例：`Filter` 扩展点按 `@Activate(group = "provider")` 自动激活

**⑥ 扩展点注入（ExtensionLoader 的 IoC）**

- 扩展实现里用 setter 注入其他扩展点（ExtensionLoader 内部自己管理依赖）
- 例：`Protocol` 实现里注入 `ExtensionFactory`

**⑦ Wrapper（包装类）**

- 构造器接收目标扩展的类 = 包装类 → 实现**类似 AOP 的增强**（调前/调后加逻辑）
- 例：`ProtocolFilterWrapper` 包一层过滤器链

### 4.3 手写 Demo ★

```java
// ① 接口
@SPI("dubbo")
public interface Protocol {
    String speak(String name);
}

// ② 实现
public class DubboProtocol implements Protocol {
    @Override public String speak(String name) { return "dubbo: " + name; }
}
public class HttpProtocol implements Protocol {
    @Override public String speak(String name) { return "http: " + name; }
}

// ③ 配置 META-INF/dubbo/com.example.spi.Protocol
//    dubbo=com.example.spi.impl.DubboProtocol
//    http=com.example.spi.impl.HttpProtocol

// ④ 使用
ExtensionLoader<Protocol> loader = ExtensionLoader.getExtensionLoader(Protocol.class);
Protocol dubbo = loader.getExtension("dubbo");    // 按别名拿
Protocol adaptive = loader.getAdaptiveExtension(); // 自适应代理
```

### 4.4 经典实例（全是扩展点）

    协议：dubbo / rmi / http / webservice / rest / grpc
    序列化：hessian2 / java / fastjson / kryo
    负载均衡：random / roundrobin / leastactive / shortestresponse
    注册中心：zookeeper / nacos / redis / eureka
    过滤器：monitor / trace / cache / validation

### 4.5 三大机制对比表

| 维度 | JDK SPI | Spring SPI | Dubbo SPI |
|------|---------|-----------|-----------|
| 加载器 | ServiceLoader | SpringFactoriesLoader | ExtensionLoader |
| 配置文件 | META-INF/services/接口全名 | spring.factories / AutoConfiguration.imports | META-INF/dubbo/ 等 |
| 文件格式 | 每行一个类 | key=类列表 | key=类（别名） |
| 一文件多接口 | ✗ | ✓ | ✓ |
| 按名获取 | ✗ | ✗ | ✓（别名） |
| 排序 | ✗ | ✓（Ordered） | ✓（@Activate order） |
| 自适应 | ✗ | ✗ | ✓（@Adaptive 动态代理） |
| 依赖注入 | ✗ | ✓（Spring 容器） | ✓（ExtensionLoader IoC） |
| 条件激活 | ✗ | ✗ | ✓（@Activate） |
| AOP 包装 | ✗ | ✗ | ✓（Wrapper） |
| 单例缓存 | ✗（每次遍历 new） | 工厂方法 | ✓（缓存扩展实例） |

---

## 5. Servlet 规范 SPI（ServletContainerInitializer）

### 5.1 是什么

**Servlet 3.0+ 规范定义的 SPI**：Web 容器（Tomcat/Jetty）启动时，扫描所有 jar 里 `META-INF/services/javax.servlet.ServletContainerInitializer` 声明的实现，并回调 `onStartup` —— 让框架**不用 web.xml 也能注册 Servlet/Filter/Listener**。

### 5.2 机制流程

    ① 容器启动 → 扫描 META-INF/services/javax.servlet.ServletContainerInitializer
    ② 实例化实现类 → 调用 onStartup(Set<Class<?>> c, ServletContext ctx)
    ③ 配合 @HandlesTypes：容器收集「实现/继承该类型的所有类」传入
    ④ 框架在回调里用编程方式注册组件（Servlet/Filter/Listener）

```java
// 声明感兴趣的类型：容器会收集所有 WebApplicationInitializer 实现类传进来
@HandlesTypes(WebApplicationInitializer.class)
public class SpringServletContainerInitializer
        implements ServletContainerInitializer {
    @Override
    public void onStartup(Set<Class<?>> webAppInitializerClasses, ServletContext ctx) {
        // 反射实例化所有 WebApplicationInitializer，调用 onStartup 注册 DispatcherServlet
    }
}
```

### 5.3 经典实例

- **Spring MVC**：`SpringServletContainerInitializer` + `WebApplicationInitializer`（注册 DispatcherServlet 和 ContextLoaderListener）—— 这就是 Spring Boot 内嵌 Tomcat 无 web.xml 的原理底座
- 其他 Web 框架（Shiro 等）的 Web 集成同样走它

### 5.4 手写（简版）★

```java
@HandlesTypes(MyWebAppInitializer.class)
public class MyServletContainerInitializer implements ServletContainerInitializer {
    @Override
    public void onStartup(Set<Class<?>> classes, ServletContext ctx) {
        for (Class<?> clazz : classes) {
            try {
                MyWebAppInitializer initializer =
                        (MyWebAppInitializer) clazz.getDeclaredConstructor().newInstance();
                initializer.onStartup(ctx);      // 注册 Servlet/Filter
            } catch (Exception e) { ... }
        }
    }
}

// 配置 META-INF/services/javax.servlet.ServletContainerInitializer
// com.example.spi.MyServletContainerInitializer
```

**注意点**
- 需要 Servlet 3.0+ 容器（Tomcat 7+ / Jetty 8+）
- Spring Boot 内嵌容器直接支持；打 war 部署到外部 Tomcat 同样生效
- @HandlesTypes 收集的是「该类型的所有实现/子类」（含抽象类的子类），回调里要过滤非实例化类型

---

## 6. 常见 SPI 实例速查

| 生态 | SPI 点 | 谁加载 | 典型实现 |
|------|--------|--------|---------|
| JDBC | java.sql.Driver | DriverManager | MySQL / PostgreSQL 驱动 |
| JPA | PersistenceProvider | Persistence | Hibernate / EclipseLink |
| Bean Validation | ValidationProvider | ValidatorFactory | Hibernate Validator |
| SLF4J | 绑定实现 | LoggerFactory | Logback / Log4j2 |
| Spring Boot | AutoConfiguration | SpringFactoriesLoader | 各种 starter |
| Dubbo | Protocol/序列化/负载均衡 | ExtensionLoader | dubbo/rmi/http、hessian2 |
| Servlet 容器 | ServletContainerInitializer | Tomcat/Jetty | Spring MVC |

---

## 7. 面试追问清单（带答案）

### 7.1 SPI 是什么？和 API 有什么区别？

A：SPI（Service Provider Interface）是服务提供者接口：框架定义接口、第三方实现、框架按约定位置自动发现加载。API 是「调用方用实现方提供的接口」（你用我的），SPI 是「框架定义接口等实现方接入」（我用你的）。本质是控制反转思想的体现。

### 7.2 JDK SPI 的原理？

A：约定目录 META-INF/services/<接口全限定名>，文件里每行一个实现类全名。ServiceLoader.load 后遍历时通过 ClassLoader.getResources 找所有 jar 的服务文件，Class.forName 反射实例化（要求 public 无参构造）。懒加载，遍历时才真正创建。

### 7.3 JDBC 4.0 为什么不用 Class.forName 了？

A：JDBC 4.0 起驱动通过 SPI 自动注册 —— 驱动 jar 里有 META-INF/services/java.sql.Driver 文件，DriverManager 初始化时用 ServiceLoader 自动加载，所以不再需要手动 Class.forName("com.mysql.jdbc.Driver")。

### 7.4 Spring SPI 和 JDK SPI 的区别？

A：① 配置文件不同（spring.factories 的 key-value 支持一文件多接口 vs 一接口一文件）；② Spring 支持排序（Ordered）；③ 通过工厂方法加载可自定义创建逻辑；④ 有 Spring 容器支持，可注入依赖。

### 7.5 Dubbo 为什么不用 JDK SPI？

A：JDK SPI 只能平铺加载所有实现、不能按名获取、无优先级、无依赖注入、无自适应。Dubbo 需要按配置名切换协议/序列化/负载均衡，还要自适应扩展、条件激活、包装增强 —— 所以重写了 ExtensionLoader。

### 7.6 @SPI / @Adaptive / @Activate 分别干什么？

A：@SPI 标注接口声明它是扩展点（可指定默认实现）；@Adaptive 生成自适应代理，运行时按参数（如 URL）自动选实现；@Activate 按条件自动激活扩展（如过滤器按 group/order 生效）。

### 7.7 Dubbo SPI 的 Wrapper 是什么？

A：构造器接收目标扩展实例的类，ExtensionLoader 加载时自动包装目标扩展，实现类似 AOP 的增强（在调用前后插入逻辑）。典型如 ProtocolFilterWrapper 给协议调用链加过滤器。

### 7.8 ServletContainerInitializer 是干什么的？Spring MVC 怎么用它？

A：Servlet 3.0+ 的 SPI，Web 容器启动时扫描并回调，让框架在无 web.xml 时编程注册组件。Spring MVC 的 SpringServletContainerInitializer 配合 @HandlesTypes(WebApplicationInitializer.class) 收集初始化器，注册 DispatcherServlet —— Spring Boot 内嵌 Tomcat 的原理底座。

### 7.9 SPI 有哪些坑？

A：① 配置文件路径/文件名错 → 静默不加载，难排查；② 多个 jar 提供同名服务 → 实现冲突/顺序不可控；③ 全量加载浪费（JDK SPI 遍历即 new）；④ 实现类必须无参构造；⑤ 版本升级接口变化会炸掉所有实现方（所以 SPI 接口演进要谨慎）。

### 7.10 让你设计一个 SPI 机制，怎么做？

A：① 约定配置目录（如 META-INF/ext/接口名）；② 加载器：ClassLoader.getResources 扫描 + 类名解析 + 反射实例化；③ 按名获取：配置用 key=value 支持别名；④ 缓存单例扩展实例；⑤ 可选：自适应代理（按运行时参数路由）、依赖注入、排序、包装增强 —— 即 Dubbo ExtensionLoader 的简化版。

---
- 关联笔记：[01-代码混淆详解](../通用技术/软件保护/01-代码混淆详解.md)（SPI 的 META-INF/services 写全限定类名，混淆重命名后服务发现失败，实现类需 keep）、[Java反射详解](Java反射详解.md)（SPI 加载本质是反射实例化）、**Java注解机制详解**（见知识库）（APT 与 SPI 的异同）
