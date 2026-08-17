---
tags: [Java, SpringBoot, SpringDoc, OpenAPI, 实践, JWT, GroupedOpenApi, 框架]
创建日期: 2026-08-17
状态: ✅ 已归档（01-学习/Java/框架/springboot）
归属: 01-学习/Java/框架/springboot
---

# SpringDoc与OpenAPI集成实践

> 版本基线：Spring Boot 3.x + SpringDoc 2.x（`springdoc-openapi-starter-webmvc-ui`）。用一段**可运行**的 MVC 工程演示：依赖、配置、注解、分组、JWT 全局认证。
> 受众：先读 [16-SpringDoc与OpenAPI集成详解](16-SpringDoc与OpenAPI集成详解.md)（原理/性能/安全），本篇照着抄即跑。默认懂 SpringBoot 工程骨架。
> 前置：[16-SpringDoc与OpenAPI集成详解](16-SpringDoc与OpenAPI集成详解.md)；Java 17+（Boot 3 最低 Java 17）；Maven。

## 📋 总纲

1. 成品目标与验证点
2. pom：唯一依赖 starter
3. application.yml：springdoc 配置
4. OpenApi 配置类（@OpenAPIDefinition + @SecurityScheme + 分组 bean）
5. Controller 注解示例
6. 安全参考：生产关闭 / Security 鉴权
7. 实测状态与踩坑

## 1. 成品目标与验证点

做一个最小 MVC 工程 `demo-api`：
- 引 `springdoc-openapi-starter-webmvc-ui`，启动即有 `/v3/api-docs` + `/swagger-ui`
- `@OpenAPIDefinition` 设文档信息，`@SecurityScheme` 全局声明 JWT
- `GroupedOpenApi` 按 `/api/user/**` 拆一个 `user` 分组
- Controller 方法带 `@Operation/@ApiResponse/@Parameter`
- yml 演示 packages-to-scan、缓存、生产关闭开关

验证点：
- 启动后访问 `/v3/api-docs` 返回 OpenAPI JSON（含 paths/components/securitySchemes）
- 访问 `/swagger-ui/index.html` 有 UI，且带 `Authorize` 按钮
- `/v3/api-docs/user` 只有 user 分组接口

## 2. pom（唯一关键依赖）

```xml
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>3.3.0</version>           <!-- Boot 3.x -->
  <relativePath/>
</parent>
<dependencies>
  <dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
  </dependency>
  <!-- ★ SpringDoc：webmvc + 自带 swagger-ui（Boot3 用 2.x，jakarta 包） -->
  <dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.6.0</version>
  </dependency>
</dependencies>
```

> 说明：只要这一个 starter 就同时给你 `/v3/api-docs` 暴露 JSON **和** `/swagger-ui` 前端。如果你想只要 JSON 不要 UI，换 `springdoc-openapi-starter-webmvc`（不含 `-ui`）。

## 3. application.yml（springdoc + 安全开关）

```yaml
server:
  port: 8080

springdoc:
  # 只扫描这个包，收窄扫描面（性能/减少暴露）
  packages-to-scan: com.example.demo.web
  # 只暴露匹配路径的接口
  paths-to-match: /api/**
  # 是否缓存文档：默认不强制缓存；生产想避免重复构建可显式开
  # cache:
  #   disabled: false   # false=用缓存（复用已构建文档）

# 安全红线：生产 profile 把下面两行打开=彻底关闭文档
# ---
# spring:
#   config:
#     activate:
#       on-profile: prod
# springdoc:
#   api-docs:
#     enabled: false    # 关闭 /v3/api-docs
#   swagger-ui:
#     enabled: false    # 关闭 /swagger-ui
# ---
```

> 说明：上面前 4 项在 dev 生效；最后注释块是"生产 profile 关闭"示例——用 `on-profile: prod` 让生产不留文档。

## 4. OpenApi 配置类

```java
package com.example.demo.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

  // 1) 文档顶层信息 + 全局声明需要 JWT
  @Bean
  OpenAPI customOpenAPI() {
    return new OpenAPI()
        .info(new Info()
            .title("商城 API")
            .version("v1.0.0")
            .description("SpringDoc 实践示例接口")
            .contact(new Contact().email("dev@example.com")))
        .addSecurityItem(new SecurityRequirement().addList("bearerAuth"))
        .components(new io.swagger.v3.oas.models.Components()
            .addSecuritySchemes("bearerAuth", new SecurityScheme()
                .type(SecurityScheme.Type.HTTP)
                .scheme("bearer")
                .bearerFormat("JWT")));
  }

  // 2) 按路径拆一个 user 分组 → /v3/api-docs/user
  @Bean
  GroupedOpenApi userApi() {
    return GroupedOpenApi.builder()
        .group("user")
        .pathsToMatch("/api/user/**")      // 只收 /api/user/**
        .build();
  }
}
```

> 说明：`addSecurityItem(...)` 等价于给所有 operation 声明"默认需要 bearerAuth"；`components().addSecuritySchemes` 生成 `components/securitySchemes/bearerAuth`。这两步就是 §详解里 `@OpenAPIDefinition` + `@SecurityScheme` 注解的编程化等价写法（二选一即可；用注解更简洁，用 Bean 对象更灵活可编程）。

## 5. Controller 注解示例

```java
package com.example.demo.web.user;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "用户接口", description = "商城用户管理")     // 分组标签
@RestController
@RequestMapping("/api/user")
public class UserController {

  @Operation(summary = "用户列表", description = "分页返回用户")
  @ApiResponses({
      @ApiResponse(responseCode = "200", description = "成功"),
      @ApiResponse(responseCode = "401", description = "未认证")})
  @GetMapping
  public List<User> list(
      @Parameter(description = "页码,从1开始", example = "1") @RequestParam(defaultValue = "1") int page) {
    return List.of(new User(1L, "alice"));
  }

  @Operation(summary = "单个用户", security = @SecurityRequirement(name = "bearerAuth"))
  @GetMapping("/{id}")
  public User get(@PathVariable Long id) {
    return new User(id, "alice");
  }

  @Hidden          // 不进文档，防泄漏（import io.swagger.v3.oas.annotations.Hidden）
  @PostMapping("/internal")
  public Map<String, Object> internal() {
    return Map.of("ok", true);
  }
}
```

```java
// 独立内部隐藏 Controller：@Hidden 整个不进文档
import io.swagger.v3.oas.annotations.Hidden;

@Hidden
@RestController
@RequestMapping("/api/debug")
class DebugController {
  @GetMapping
  public String debug() {
    return "debug-info";
  }
}
```

```java
// DTO：@Schema 描述字段 + 示例（record）
import io.swagger.v3.oas.annotations.media.Schema;

public record User(
    @Schema(description = "用户ID", example = "1", required = true) Long id,
    @Schema(description = "用户名", example = "alice") String name) {
}
```

> 说明：
> - `@Hidden`（或字段 `@Schema(hidden=true)`）能让接口/字段不进文档，是收窄暴露的关键手法。
> - `@Operation(security = @SecurityRequirement(name = ""))` 可给个别接口声明"无需认证"（空串覆盖全局要求）。

## 6. 生产关闭参考

若需"生产保留文档但要求登录"，用 Spring Security 让 `/v3/api-docs/**` 与 `/swagger-ui/**` 需要认证，**不要**放白名单：

```java
@Configuration
@EnableWebSecurity
class SecurityConfig {
  SecurityFilterChain chain(HttpSecurity http) throws Exception {
    http.authorizeHttpRequests(a -> a
        .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html")
        .authenticated()          // 未登录看不到文档
        .anyRequest().permitAll());
    return http.build();
  }
}
```

> 最理想是生产直接关闭（§3 注释块），安全需求高时再采用"认证后才可见"方案。

## 7. 实测状态与踩坑

- 本工程示例结构为 Boot3 + SpringDoc 2.6.0，结论与 2026-08 官方文档一致。✅ 实测路径：`/v3/api-docs`、`/swagger-ui/index.html`、`/v3/api-docs/user`（分组）。
- **踩坑**：光关 `springdoc.api-docs.enabled=false` 但 `springdoc.swagger-ui.enabled` 没关 → UI 仍可访问；两者一起关。
- **踩坑**：注解用了 `io.swagger.annotations.*`（SpringFox 的 Swagger2 包）不生效 → 换 `io.swagger.v3.oas.annotations.*`。
- **踩坑**：Boot 3 + SpringFox → 起不来（javax/jakarta 冲突）→ 升级到 SpringDoc 2.x。
- **踩坑**：`/v3/api-docs` 首次访问很慢是正常的（惰性构建），配缓存可缓解。

## 8. 小结

- pom 引 `springdoc-openapi-starter-webmvc-ui`（2.x，作用 Boot 3 / jakarta）即自动有 `/v3/api-docs` 与 `/swagger-ui`。
- yml 用 `packages-to-scan` / `paths-to-match` 收窄；生产 profile 关掉 `api-docs`/`swagger-ui`。
- 配置类用 `OpenAPI` Bean（info + 全局 JWT securityScheme）+ `GroupedOpenApi` 分组。
- Controller 用 `@Tag/@Operation/@ApiResponse/@Parameter/@Schema/@Hidden` 表达文档与收敛。

下一篇：[18-Knife4j增强与网关聚合详解](18-Knife4j增强与网关聚合详解.md)（更美观的增强 UI + 网关聚合两模式）。
