---
tags: [Java, Spring, SpringMVC, 拦截器, Interceptor, HandlerInterceptor, 过滤器]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# 拦截器Interceptor详解

> 前置知识：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)（请求分发流程）、[16-拦截器Interceptor详解](16-拦截器Interceptor详解.md) 无
> 关联笔记：[15-Filter过滤器详解与三层对比](15-Filter过滤器详解与三层对比.md)（Filter 对比）、[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（AOP 独立成篇）、springboot 域 [08-Spring WebFlux响应式编程详解](../springboot/08-Spring WebFlux响应式编程详解.md)（响应式无拦截器）
> 定位：拦截器**单独成篇**——因为与本篇对比的 Filter 和 AOP 各自已另有文档，本篇专注 HandlerInterceptor 本身。

## 📋 总纲

1. 拦截器是什么：Spring MVC 框架内的请求钩子
2. 三个核心方法 preHandle / postHandle / afterCompletion
3. 拦截器写法：实现 + 注册（WebMvcConfigurer）
4. 完整示例：登录鉴权 + 多拦截器顺序
5. 拦截器 vs Filter（对比表 + 选型）
6. 拦截器 vs AOP（对比表）
7. 拦截器常见坑
8. 总结

## 一、拦截器是什么

**拦截器 HandlerInterceptor 是 Spring MVC 框架内的组件**，在请求通过 DispatcherServlet 分发、**到达 Controller 方法前后**执行。

- **位置**：Spring MVC 内，比 Filter 靠内，比调用业务方法靠外。
- **关键优势**：能拿到 **HandlerMethod**（即当前 Controller 方法 + 其上注解），这是它与 Filter 的本质区别。
- **范围**：只拦截 Spring MVC 的处理器（Controller），**默认不拦静态资源**（除非手动 `excludePathPatterns` 之外再配）。
- **一句话记忆**：拦截器管"请求到 Controller 通道"上的前置检查和后置清理。

## 二、三个核心方法

| 方法 | 时机 | 返回值/作用 | 典型场景 |
| --- | --- | --- | --- |
| `preHandle` | 进 Controller **之前** | 返回 `true` 放行，`false` 则**拦截（终止后续）** | 登录鉴权、权限校验 |
| `postHandle` | Controller 返回后、**视图渲染前** | 可改 `ModelAndView` | 向模型注入公共数据 |
| `afterCompletion` | 整个请求完成后、**响应已提交** | 无论正常/异常都执行，用于清理 | 记录耗时、释放资源 |

执行顺序：所有 `preHandle` 按注册正序 → 目标方法 → 所有 `postHandle` 逆序 → `afterCompletion` 逆序（只对执行了 preHandle 的拦截器）。

## 三、拦截器写法

### 3.1 实现 HandlerInterceptor

```java
public class LoginInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        // 拿到 Controller 方法信息（关键能力）
        HandlerMethod handlerMethod = (HandlerMethod) handler;
        System.out.println("拦截到：" + handlerMethod.getBean().getClass().getSimpleName()
                + "." + handlerMethod.getMethod().getName());

        Object loginUser = request.getSession().getAttribute("loginUser");
        if (loginUser == null) {
            response.sendRedirect("/login");   // 拦截：返回 false
            return false;
        }
        return true;                            // 放行：进 Controller
    }

    @Override
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler,
                           ModelAndView modelAndView) throws Exception {
        // 返回后、渲染前：可加公共数据
        if (modelAndView != null) {
            modelAndView.addObject("now", System.currentTimeMillis());
        }
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) throws Exception {
        long cost = System.currentTimeMillis() - (long) request.getAttribute("start");
        System.out.println("请求完成耗时: " + cost + "ms");   // 无论成败都会执行
    }
}
```

### 3.2 注册拦截器（WebMvcConfigurer + addInterceptors）

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new LoginInterceptor())
                .addPathPatterns("/**")        // 拦截所有路径
                .excludePathPatterns("/login", "/css/**", "/js/**", "/error");  // 放行路径
    }
}
```

> 注册顺序即执行顺序；也可用 `@Order` 注解微调。

### 3.3 排除静态资源

默认不拦静态资源，但若想拦截 Controller 但放行静态，用 `excludePathPatterns` 显式排除静态目录。

## 四、完整示例：登录鉴权

```java
@Component
public class AuthInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        // 不需要鉴权的接口：用注解标记，这里读出判断
        HandlerMethod hm = (HandlerMethod) handler;
        if (hm.getMethodAnnotation(AllowAnonymous.class) != null) {
            return true;   // 带 @AllowAnonymous 的接口跳过登录校验
        }
        String token = request.getHeader("token");
        if (token == null || !token.equals("valid-token")) {
            response.setStatus(401);
            response.getWriter().write("{\"code\":401}");
            return false;
        }
        return true;
    }
}
```

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new AuthInterceptor())
                .addPathPatterns("/**")
                .excludePathPatterns("/login");
    }
}
```

> 相比 Filter 的突出能力：通过 `HandlerMethod` 检查**方法级注解**（如 `@AllowAnonymous`），这是 Filter 做不到的。

## 五、拦截器 vs Filter

| 维度 | Filter 过滤器 | Interceptor 拦截器 |
| --- | --- | --- |
| 所属规范 | Servlet 规范（容器级） | Spring MVC 框架 |
| 执行层 | 进 Spring 前 | DispatcherServlet 分发后 |
| 拿到什么 | ServletRequest/Response | **HandlerMethod**（方法+注解） |
| 范围 | 所有请求（含静态、非 MVC servlet） | 仅 Spring MVC 处理器 |
| 粒度 | 请求级（urlPatterns） | Controller 方法级 |
| 核心方法 | doFilter + chain | pre/post/after |
| 典型场景 | 编码、CORS、响应包装、底层 | 鉴权、权限、Controller 日志 |

**选型**：要判断"是哪个 Controller 方法 / 有没有某注解" → 用拦截器；要在最外层、覆盖静态资源、包装响应体 → 用 Filter。

## 六、拦截器 vs AOP

| 维度 | 拦截器 | AOP（Spring） |
| --- | --- | --- |
| 层级 | Spring MVC（Web 层） | Spring IoC 容器 |
| 对象 | 只贴 Controller（HandlerMethod） | 任意 Spring Bean 任意方法 |
| 拿到什么 | 请求/响应 + 方法 | Method / JoinPoint / 参数 / 返回值 |
| 机制 | Spring MVC 拦截链 | 动态代理（JDK/CGLIB） |
| 典型场景 | 鉴权、Controller 前置 | 事务、审计、缓存、限流 |

> 目的都是"横切"，但拦截器绑定 Web 请求；AOP 通用到任何 Bean 方法（详见 [07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)）。

## 七、常见坑

1. **preHandle 返回 false 后要自行处理响应**：框架不会默认写 401，需像示例那样设置状态/重定向。
2. **postHandle 在异常时不执行**：但 `afterCompletion` 一定执行（无论成败，用于清理）。
3. **静态资源默认不拦**：需要放行时别忘 `excludePathPatterns`（静态资源本身就不走 HandlerMethod 拦截）。
4. **对象转换**：`handler` 不一定总是 `HandlerMethod`（可能命中 `ResourceHttpRequestHandler`），转型前判类型避免 CCE。
5. **响应式（WebFlux）无拦截器**：`HandlerInterceptor` 是同步 MVC 专属，响应式用 WebFilter（见 [15-Filter过滤器详解与三层对比](15-Filter过滤器详解与三层对比.md) 与 [08-Spring WebFlux响应式编程详解](../springboot/08-Spring WebFlux响应式编程详解.md)）。

## 八、总结

- 拦截器 = **Spring MVC 框架内、Controller 方法级**的请求钩子，靠 HandlerMethod 获得方法级洞察。
- 三个方法分工：`preHandle` 决定放不放行，`postHandle` 结果前补齐，`afterCompletion` 收尾清理。
- 与 Filter / AOP 分工：**Filter 最外层（容器级）→ 拦截器（Controller 通道）→ AOP（业务方法）**，由外到内。

---

> 上一篇：[15-Filter过滤器详解与三层对比](15-Filter过滤器详解与三层对比.md)
> 对比项：[07-Spring核心·AOP详解](07-Spring核心·AOP详解.md)（AOP 独立成篇）
