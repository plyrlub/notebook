---
tags: [Java, Spring, SpringMVC, 整合, 实践, web.xml]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring与SpringMVC整合实践

> 版本基线：Spring 5.x + SpringMVC 传统 Servlet 容器整合（web.xml 双容器）。先读 [05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md)。
> 前置：[05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md)；本篇给"一个完整的 XML web 项目怎么搭起来"。

## 📋 总纲

1. 为什么要"整合"：双容器
2. 两个配置文件（root 容器 + MVC 容器）
3. web.xml 完整清单
4. 父子容器与扫描切分
5. 注意点与踩坑

## 1. 为什么整合与双容器

SpringMVC 挂到 Spring 上，`web.xml` 里要配**两个容器**，各自加载不同 bean：
- **root 容器**（`ContextLoaderListener`）：service/dao/数据源/事务/安全等"非 web" Bean
- **MVC 容器**（`DispatcherServlet`）：@Controller、视图解析、拦截器（web 层）

**父子关系**：MVC 容器是 root 容器的**子容器**，能看见父(service/dao)，父看不见子(@Controller)。所以要**按职责切分扫描**，别两个都扫重复。

## 2. 两个配置文件

`applicationContext.xml`（root 容器，服务层）：

```xml
<beans ... xmlns:context="...">
    <!-- 只扫 service/dao/repository，圈住业务层，别扫到 controller -->
    <context:component-scan base-package="com.example.service,com.example.dao"/>

    <!-- 数据源 / 事务管理器（非 web） -->
    <bean id="dataSource" class="com.zaxxer.hikari.HikariDataSource">...</bean>
    <bean id="txManager" class="org.springframework.jdbc.datasource.DataSourceTransactionManager">
        <property name="dataSource" ref="dataSource"/>
    </bean>
</beans>
```

`spring-mvc.xml`（MVC 容器，web 层）：

```xml
<beans ... xmlns:mvc="..." xmlns:context="...">
    <!-- 只扫 controller -->
    <context:component-scan base-package="com.example.controller"/>
    <mvc:annotation-driven/>
    <!-- 视图解析 / 拦截器 / 静态资源 见 [[04-SpringMVC执行流程实践]] -->
</beans>
```

## 3. web.xml 完整清单（两个容器怎么装）

```xml
<web-app>
    <!-- ① root 容器：加载业务层 -->
    <context-param>
        <param-name>contextConfigLocation</param-name>
        <param-value>classpath:applicationContext.xml</param-value>
    </context-param>
    <listener>
        <listener-class>org.springframework.web.context.ContextLoaderListener</listener-class>
    </listener>

    <!-- ② MVC 容器：DispatcherServlet 加载 web 层 -->
    <servlet>
        <servlet-name>dispatcher</servlet-name>
        <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
        <init-param>
            <param-name>contextConfigLocation</param-name>
            <param-value>classpath:spring-mvc.xml</param-value>
        </init-param>
        <load-on-startup>1</load-on-startup>
    </servlet>
    <servlet-mapping>
        <servlet-name>dispatcher</servlet-name>
        <url-pattern>/</url-pattern>
    </servlet-mapping>
</web-app>
```

**contextConfigLocation 两个位置**（很易混）：
- `<context-param>`（root）→ `ContextLoaderListener` 用它加载业务层
- `<init-param>`（servlet）→ `DispatcherServlet` 用它加载 MVC 层
**忘了给 DispatcherServlet 配 init-param**，它默认找 `/WEB-INF/dispatcher-servlet.xml`（按 servlet 名），找不到会启动失败。

## 4. 父子容器扫描切分（金点子）

| 层 | 谁管 | 扫描包 | 该有的 | 不该有的 |
| --- | --- | --- | --- | --- |
| root | ContextLoaderListener | service/dao/数据源/事务 | `@Service @Repository`、事务、数据源 | `@Controller` |
| mvc | DispatcherServlet | controller | `@Controller`、拦截器、视图 | `@Service @Dao`、数据源（会被子孙各建一份）|

**如果不切分**：两个容器都 `base-package="com.example"` → 业务层被 root 和 mvc **各建一份**，出现"两个事务管理器/两个 service 实例"，@Transactional 可能失效（事务切面在 root，控制器引的是 mvc 那份）。

> Spring Boot 已内置这套整合（单容器 + 自动装配），传统 XML 只用于老项目/ Servlet 容器部署。

## 5. 注意点与踩坑

- **重复扫描**＝重复 Bean：两个容器扫同一个包，业务 bean 存在两份。
- **@Transactional 失效（经典）**：事务切面扫描在 root，而 controller 引用的 service 来自 mvc 容器 → 两个实例，事务管理器的切面没贴着被用的那份 → `@Transactional` 静默失效。排查看**事务管理器与 service 是否同一容器同一实例**。
- **Controller 调 service 拿到 null/两份**：多半是两个根因的重复扫描。
- **`/` vs `/*`**：`/` 会有静态资源被拦截问题，配合 `<mvc:resources>`；`/*` 让视图 JSP 不渲染。
- 参考踩坑：web 层整合类坑集中在"双容器扫描切分"这一条。

## 6. 关联

- 详解：[05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md)
- 上一篇（详解）：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md) 与 [04-SpringMVC执行流程实践](04-SpringMVC执行流程实践.md)
- 下一篇：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)
