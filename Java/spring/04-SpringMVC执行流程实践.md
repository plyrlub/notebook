---
tags: [Java, SpringMVC, 实践, 控制器, 传参, XML, 拦截器]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# SpringMVC执行流程实践

> 版本基线：Spring MVC 5.x/6.x。先读 [03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)，本篇只给"怎么一步步搭 + 参数怎么传 + 配置值含义"。
> 前置：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)；本篇可运行伪代码为主，坑用⚠️标注。

## 📋 总纲

1. web.xml 配置（传统 XML 时代）
2. 配置 DispatcherServlet 与组件（值含义）
3. 控制器与 4 种参数绑定
4. 返回值与 @ResponseBody
5. 拦截器 vs 过滤器
6. 全局异常 & 静态资源 & CORS
7. 注意点与踩坑

## 1. web.xml 配置（传统 XML 时代）

```xml
<!-- 前端控制器：接收所有请求（前端控制器模式） -->
<servlet>
    <servlet-name>dispatcher</servlet-name>
    <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
    <init-param>
        <param-name>contextConfigLocation</param-name>
        <param-value>/WEB-INF/spring-mvc.xml</param-value>  <!-- MVC 配置文件位置 -->
    </init-param>
    <load-on-startup>1</load-on-startup>                     <!-- 容器启动即初始化 -->
</servlet>
<servlet-mapping>
    <servlet-name>dispatcher</servlet-name>
    <url-pattern>/</url-pattern>                             <!-- 根路径，接管所有请求 -->
</servlet-mapping>
```

## 2. DispatcherServlet 初始化参数含义

| init-param | 值 | 作用 |
| --- | --- | --- |
| `contextConfigLocation` | `classpath:spring-mvc.xml` / `/WEB-INF/xx.xml` | MVC 配置（控制器扫描/视图解析/拦截器）在哪 |
| `load-on-startup` | `1` | 容器启动即建 servlet（>0 数字越小越先加载） |

**`/` vs `/*` 的坑**（最常见）：`/` 匹配所有**除 JSP 外**的请求，会拿不到静态资源（css/js）——要配合 `<mvc:resources>`；`/*` 匹配所有（含 JSP，会让 JSP 视图解析失效，通常不用）。

> **Spring Boot 下不用配 web.xml**：自动装配 `DispatcherServlet` + 约定 `spring.mvc.*` 配置（见 springboot 域），下面 XML 适用于纯 SpringMVC/Servlet 容器项目。

## 3. spring-mvc.xml：组件与配置值含义

```xml
<beans ... xmlns:mvc="http://www.springframework.org/schema/mvc"
        xmlns:context="http://www.springframework.org/schema/context">
    <!-- 扫描 @Controller -->
    <context:component-scan base-package="com.example.controller"/>

    <!-- 开启动态注解驱动：@RequestMapping 等 + 消息转换器(JSON) -->
    <mvc:annotation-driven/>

    <!-- 静态资源放行（否则被 DispatcherServlet 拦截） -->
    <mvc:resources mapping="/static/**" location="/static/"/>

    <!-- 视图解析器 -->
    <bean class="org.springframework.web.servlet.view.InternalResourceViewResolver">
        <property name="prefix" value="/WEB-INF/views/"/>
        <property name="suffix" value=".jsp"/>
    </bean>
</beans>
```

**配置项含义**：
- `mvc:annotation-driven` → 开启注解映射 + 参数绑定 + `@ResponseBody` 的 JSON 转换（Jackson）——**忘了它会 404/走不到方法**。
- `mvc:resources mapping="/static/**"` → 把静态资源从控制器手里捞回来，`location` 是物理路径。`**` 匹配多级目录。
- `view-resolver prefix/suffix` → 控制器返回字符串视图名 `hello` 时拼成 `/WEB-INF/views/hello.jsp`。

## 4. 控制器与 4 种参数绑定

```java
@Controller                       // @Controller = @Component 族，容器管理
public class UserController {
    @RequestMapping("/user/{id}") // 路径参数 { } 占位
    public String detail(@PathVariable("id") Long id) { ... }        // ① 路径变量

    @GetMapping("/list")
    public String list(@RequestParam(name="page", defaultValue="1") int page,
                       @RequestParam(required=false) String kw) {...} // ② 查询参数

    @PostMapping("/create")
    public String create(@ModelAttribute User user) {...}             // ③ 表单→对象

    @PostMapping("/json")
    @ResponseBody
    public Result create(@RequestBody User user) {...}                // ④ JSON body→对象
}
```

**4 种绑定方式（含属性值含义）**：

| 注解 | 来源 | 关键属性（defaultValue/required/name） |
| --- | --- | --- |
| `@PathVariable` | URL 路径 `{}` | 绑路径段，与 `{}` 名对应 |
| `@RequestParam` | 查询串 `?a=1` | `defaultValue` 缺省值、`required` 是否必填、`name` 参数名 |
| `@ModelAttribute` | 表单字段 | 自动把 request 参数映射进对象的同名属性 |
| `@RequestBody` | 请求体(JSON) | 靠 Jackson 反序列化，须有 `<mvc:annotation-driven>` |

> ⚠️ **@RequestParam 几个坑**：缺省传参加 `required=false` 或给 `defaultValue`，否则报 400；参数名与形参名不一致用 `name=`；int → Long 类型不匹配会 400。

## 5. 返回值与 @ResponseBody

- **返回 String** → 走视图解析器，当视图名（`.jsp`）
- **返回对象 + `@ResponseBody`** → 走 Jackson 序列化成 JSON（REST 风格，常用）
- **`@RestController`** = `@Controller` + `@ResponseBody` 合体，方法默认全 JSON

```java
@RestController
public class ApiController {
    @GetMapping("/api/user")
    public User user() { return new User(1L, "robin"); }  // 自动 JSON: {"id":1,"name":"robin"}
}
```

## 6. 拦截器 vs 过滤器（一句话对照）

| | 过滤器 Filter | 拦截器 Interceptor |
| --- | --- | --- |
| 归属 | Servlet 规范 | SpringMVC |
| 配置 | web.xml | XML `<mvc:interceptors>` 或 JavaConfig |
| 能拿到 | HttpServletRequest（servlet 层） | Controller 方法 + Handler（spring 层） |
| 时机 | 请求进 servlet 前 | 请求进 controller 前后（pre/post/afterCompletion） |

```xml
<mvc:interceptors>
    <mvc:interceptor>
        <mvc:mapping path="/api/**"/>           <!-- 只拦这些路径 -->
        <bean class="com.example.interceptor.AuthInterceptor"/>
    </mvc:interceptor>
</mvc:interceptors>
```

**`/api/**` 含义**：`/api/**` 命中 /api 下所有（含子路径）；`/api/*` 只命中单层。

## 7. 全局异常 & 静态资源 & CORS（简）

```java
@ControllerAdvice
public class GlobalHandler {
    @ExceptionHandler(Exception.class)      // 捕获所有异常
    @ResponseBody
    public Result handle(Exception e) { return Result.error(e.getMessage()); }
}
```

- **全局异常**：`@ControllerAdvice` + `@ExceptionHandler(某异常)` 统一兜底，避免每个方法 try-catch。
- **CORS 跨域**：Boot 用 `spring.mvc.cors` 或 `@CrossOrigin`；XML 时代用 `mvc:cors`。
- **静态资源 404**：Boot 用 `spring.web.resources.static-locations` 配静态路径；XML 时代需 `<mvc:resources>`。另一种 404 是拦截器把静态资源拦了（排除路径没写好）。

## 8. 注意点与踩坑

- **404 误区**：不是"没这个页面"，常是 ① 请求被 `/` DispatcherServlet 拦截到静态 ② `mvc:annotation-driven` 未加找不到映射 ③ `@Controller` 没被判作扫描。
- **400 参数错误**：类型不匹配（传 "abc" 给 int）、required 缺参。
- **415 Unsupported Media Type**：`@RequestBody` 但请求没带 JSON Content-Type。
- **拦截器不生效**：没配 `<mvc:interceptors>` 或路径 pattern 写错（`/api/*` vs `/api/**`）。
- **视图逃不掉**：想返回 JSON 却走了 jsp → 忘加 `@ResponseBody` / 没用 `@RestController`。

## 9. 关联

- 详解：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)
- 上一点：[02-Spring核心·IoC与Bean生命周期实践](02-Spring核心·IoC与Bean生命周期实践.md)
- 下一篇：[05-Spring与SpringMVC整合详解](05-Spring与SpringMVC整合详解.md)
