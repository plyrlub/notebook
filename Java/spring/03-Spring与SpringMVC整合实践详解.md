---
tags: [Java, Spring, SpringMVC, 整合, web.xml, 双容器, JavaConfig, 框架]
创建日期: 2026-08-11
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring与SpringMVC整合实践详解

> 版本基线：传统 Spring XML/注解整合 + 与 SpringBoot 对比
> 受众：Java 后端开发。假设已懂 [01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md) 与 [02-SpringMVC执行流程详解](02-SpringMVC执行流程详解.md)；本篇解决"Spring 和 SpringMVC 怎么手动整合起来"以及"为什么 Boot 不用配了"。
> 前置知识：[01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)（IoC/装配）、[02-SpringMVC执行流程详解](02-SpringMVC执行流程详解.md)（MVC 流程）
> 关联笔记：springboot 域 [01-SpringBoot启动原理与自动装配详解](springboot/01-SpringBoot启动原理与自动装配详解.md)（Boot 如何省掉这些配置）

## 📋 总纲

1. 为什么需要"整合"：Spring 和 SpringMVC 本是两套容器
2. 传统 XML 整合：web.xml + 双容器（ContextLoaderListener + DispatcherServlet）
3. 双容器职责：父容器 vs 子容器
4. 注解驱动整合（替代 XML）
5. 完整示例：一个可运行的整合项目
6. 对比：XML 时代 → 注解时代 → Boot 时代
7. 为什么 Boot 简化了这一切

## 1. 学习目标

1. 讲清 Spring 与 SpringMVC 是"两套容器"的关系
2. 理解双容器（父/子）的职责边界与坑
3. 手写 web.xml 完成传统整合
4. 用注解驱动替代 XML 整合
5. 对比 Boot 为何免配置

## 2. 前置知识

- [01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)：@Component/@Bean 装配
- [02-SpringMVC执行流程详解](02-SpringMVC执行流程详解.md)：DispatcherServlet 是 MVC 前端控制器

## 3. 核心知识点

### 3.1 为什么需要"整合"

Spring（核心容器）和 SpringMVC（Web 框架）**是两个独立的容器**：Spring 管业务 Bean（Service/Dao），SpringMVC 管 Web 组件（Controller/拦截器）。传统开发要**显式告诉服务器**这两个容器怎么初始化、怎么加载配置文件——这就是"整合"要做的配置。

> 类比：Spring 是"业务车间"，SpringMVC 是"接待前台"。传统方式你要分别给它们下单（配置）、告诉它们物料来源（配置文件）；Boot 时代由系统自动把两者接好。

### 3.2 传统 XML 整合（web.xml）

web.xml 声明两个监听器/组件：

```xml
<!-- web.xml：声明两个上下文加载器 -->
<web-app>
  <!-- ① 父容器：加载 Spring 核心 Bean（Service/Dao/数据源），全局共享 -->
  <listener>
    <listener-class>org.springframework.web.context.ContextLoaderListener</listener-class>
  </listener>
  <context-param>
    <param-name>contextConfigLocation</param-name>
    <param-value>classpath:spring/applicationContext.xml</param-value>
  </context-param>

  <!-- ② 子容器：DispatcherServlet 加载 MVC 组件（Controller/拦截器/视图解析） -->
  <servlet>
    <servlet-name>springmvc</servlet-name>
    <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
    <init-param>
      <param-name>contextConfigLocation</param-name>
      <param-value>classpath:spring/springmvc.xml</param-value>
    </init-param>
    <load-on-startup>1</load-on-startup>
  </servlet>
  <servlet-mapping>
    <servlet-name>springmvc</servlet-name>
    <url-pattern>/</url-pattern>
  </servlet-mapping>
</web-app>
```

### 3.3 双容器职责：父容器 vs 子容器 ★

```
父容器（ContextLoaderListener 创建）
  ├─ 加载 applicationContext.xml：Service / Dao / 数据源 / 事务管理器
  └─ 全局共享：多个 Servlet 可共用

子容器（DispatcherServlet 创建）
  ├─ 加载 springmvc.xml：Controller / 拦截器 / 视图解析器 / 静态资源
  └─ 只服务当前 DispatcherServlet

父子关系：子容器可访问父容器的 Bean，父容器看不到子容器
```

**关键规则（常踩坑）**：
- **子容器可注入父容器 Bean**（Controller 注入 Service ✅）
- **父容器不能反向拿子容器的 Bean**（Service 注入 Controller ❌）
- **重复扫描的坑**：如果父子容器都扫描了 Controller，会导致 Controller 被创建两份（一份在父容器）→ 请求走子容器那份，父容器那份成为孤儿 → 事务/代理失效。**解决**：父容器只扫 Service/Dao，子容器只扫 Controller，互不重叠。

### 3.4 注解驱动整合（替代 XML）

把两个 XML 换成注解扫描 + 组件扫描，但**双容器边界仍需手动指定**：

```xml
<!-- applicationContext.xml（父容器）：只扫 Service/Dao -->
<context:component-scan base-package="com.example.service,com.example.dao"/>
<!-- 加注解驱动：<mvc:annotation-driven/> 属于 MVC 放子容器 -->

<!-- springmvc.xml（子容器）：只扫 Controller -->
<context:component-scan base-package="com.example.controller"/>
<mvc:annotation-driven/>
```

`<mvc:annotation-driven/>` 启用 @RequestMapping 等 MVC 注解支持（HandlerMapping/HandlerAdapter 等默认组件）。

### 3.5 完整示例：可运行整合项目

```
src/main/resources/spring/
├── applicationContext.xml   # 父容器：Service/Dao + 数据源
└── springmvc.xml            # 子容器：Controller + 注解驱动

src/main/java/com/example/
├── controller/UserController.java
├── service/UserService.java
└── dao/UserDao.java
```

```java
// applicationContext.xml（父容器核心）
@Configuration   // 或用 JavaConfig
// 父容器（contextConfigLocation 指定本类）
@ComponentScan("com.example.service")   // 只扫 Service
public class RootConfig {
    @Bean public DataSource dataSource() { return new HikariDataSource(); }
}

// 子容器（DispatcherServlet 指定本类）
@Configuration
@ComponentScan("com.example.controller")   // 只扫 Controller
@EnableWebMvc
public class WebConfig implements WebMvcConfigurer {
    @Override public void configureMessageConverters(...) { /* Jackson */ }
}
```

> 关键：**两个 @Configuration 分别对应父/子容器**，扫描包严格分离（RootConfig 扫 service，WebConfig 扫 controller），避免双份 Bean。启动类用 `AbstractAnnotationConfigDispatcherServletInitializer`（无 web.xml 的 Servlet 3+ 方式）：

```java
public class AppInitializer extends AbstractAnnotationConfigDispatcherServletInitializer {
    @Override protected Class<?>[] getRootConfigClasses() { return new Class[]{RootConfig.class}; }   // 父
    @Override protected Class<?>[] getServletConfigClasses() { return new Class[]{WebConfig.class}; }  // 子
    @Override protected String[] getServletMappings() { return new String[]{"/"}; }
}
```

### 3.6 对比：XML 时代 → 注解时代 → Boot 时代

| 维度 | XML 时代 | 注解驱动时代 | Boot 时代 |
| --- | --- | --- | --- |
| 容器初始化 | web.xml + listener/servlet | Servlet 3 初始化器 | 自动装配 |
| 配置 | 两个 XML 全手写 | XML 简化为扫描 + JavaConfig | 零 XML |
| 双容器 | 手动配 | 手动配（两类） | 默认单容器 |
| 扫描 | 手写包路径 | 手写包路径 | 自动扫启动类所在包 |
| 内嵌容器 | 外部 Tomcat | 外部 Tomcat | 内置 Tomcat |
| 引入库 | 手写一堆 bean | 手写 | starter 自动配 |

### 3.7 为什么 Boot 简化了这一切

SpringBoot 的自动装配做了三件事：
1. `spring-boot-starter-web` 自动引入 SpringMVC + 内嵌 Tomcat
2. 自动注册 DispatcherServlet + 配置 WebMvc 默认组件（不再需要 web.xml/初始化器）
3. 自动创建"父容器"（ApplicationContext）扫描启动类所在包及子包——**统一单容器**，Controller/Service 一个容器管，双容器边界和重复扫描的坑直接消失

> 所以 Boot 项目里你看不到 web.xml、看不到双容器、不用配 DispatcherServlet——这些被 `@SpringBootApplication` + 自动装配吞掉了。详见 springboot 域 [01-SpringBoot启动原理与自动装配详解](springboot/01-SpringBoot启动原理与自动装配详解.md)。

## 4. 最佳实践

- 现代新项目一律用 SpringBoot，勿手写 web.xml 整合
- 若维护老项目：父子容器**扫描包必须分离**（父=Service/Dao，子=Controller）
- 事务注解放 Service 层（父容器），别放 Controller
- 整合事务需父容器配 `DataSourceTransactionManager` + `<tx:annotation-driven>`

## 5. 常见踩坑

- **Controller 双份**：父子容器重复扫描 → 请求路由混乱、代理失效
- **父容器扫了 Controller**：Controller 在父容器成为孤儿，子容器注入不到
- **事务不生效**：事务管理器配在子容器而非父容器（Controller 层代理在父容器拿不到）
- **老项目迁移 Boot**：删 web.xml/初始化器，靠自动装配；自定义 Filter/拦截器改用 @Component 注册

## 6. 小结

- Spring 与 SpringMVC 是父子双容器：父=全局业务 Bean，子=MVC 组件。
- 子容器可注入父 Bean，父容器不可反向拿子 Bean。
- 整合核心坑：扫描包严格分离，避免 Bean 双份。
- Boot 用自动装配统一单容器，免去 web.xml/双容器/DispatcherServlet 手动配置。

## 7. 关联笔记

- 上一篇：[02-SpringMVC执行流程详解](02-SpringMVC执行流程详解.md)
- 下一篇（进入 Boot）：springboot 域 [01-SpringBoot启动原理与自动装配详解](springboot/01-SpringBoot启动原理与自动装配详解.md)
- [04-Spring核心·AOP详解](04-Spring核心·AOP详解.md)：事务切面代理（父容器配置相关）
- [05-Spring事务管理详解](05-Spring事务管理详解.md)：DataSourceTransactionManager

## 8. 参考资料

- [Spring 官方文档：Web MVC 配置](https://docs.spring.io/spring-framework/reference/web/webmvc.html)，查询日期 2026-08-11
- [Spring/SpringMVC 双容器整合详解（社区）]，查询日期 2026-08-11
