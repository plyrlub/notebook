---
tags: [Java, SpringBoot, 参数校验, BeanValidation]
创建日期: 2026-08-06
状态: ✅ 已归档（01-学习/Java/框架/通用实践）
归属: 01-学习/Java/框架/通用实践
---

# Java参数校验详解（Bean Validation）

## 📋 总纲

1. 基本概念：Bean Validation 规范、Hibernate Validator、快速上手
2. 常用校验注解：逐个说明 + 高频混淆点
3. Spring Boot 集成：Controller 校验、方法级校验、嵌套/分组校验
4. 自定义校验注解
5. 校验异常处理与消息国际化
6. 框架使用注意点与坑
7. 原理（补充知识）
8. 面试追问清单（带答案）

---

## 1. 基本概念

### 1.1 是什么

**Bean Validation** 是 Java 官方的声明式参数校验规范（JSR 303 → 349 → **JSR 380**，即 jakarta.validation），用注解描述约束，框架自动校验，不用手写一堆 if：

```java
public class CreateUserRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(max = 20, message = "用户名最长 20 字")
    private String name;

    @Min(value = 1, message = "年龄最小 1")
    @Max(value = 150, message = "年龄最大 150")
    private Integer age;
}
```

**生态关系**
- 规范：jakarta.validation（Bean Validation 2.0 / 3.0）
- 默认实现：**Hibernate Validator**（最主流）
- Spring Boot：`spring-boot-starter-validation` 内置 Hibernate Validator，开箱即用

### 1.2 快速上手（Spring Boot）

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

```java
@RestController
public class UserController {
    @PostMapping("/users")
    public User create(@Valid @RequestBody CreateUserRequest req) {
        // 校验不通过根本走不到这里，被异常处理器拦截
        return userService.create(req);
    }
}
```

---

## 2. 常用校验注解

### 2.1 空值三兄弟（最高频混淆点）

| 注解 | 适用类型 | 校验内容 | null 时 |
|------|---------|---------|--------|
| `@NotNull` | 任意 | 非 null | 失败 |
| `@NotEmpty` | 字符串/集合/数组/Map | 非 null 且非空 | 失败 |
| `@NotBlank` | 仅字符串 | 非 null 且去空格后非空 | 失败 |

```java
@NotBlank String name;      // " " 空格 → 失败；"robin" → 通过
@NotEmpty List<String> tags; // [] → 失败；[a] → 通过
@NotNull Integer age;        // 0 → 通过（非 null 即可）
```
- **规则**：String 用 @NotBlank（会去空格）；集合用 @NotEmpty；纯 null 检查用 @NotNull
- 常见错误：String 上用 @NotNull 导致 " " 空格字符串通过校验

### 2.2 数值与范围

```java
@Min(1) @Max(150) int age;                  // 数值边界（long 系列）
@DecimalMin("0.00") @DecimalMax("9999.99") BigDecimal amount;  // 高精度，字符串比较
@Positive int x;        // > 0
@PositiveOrZero int y;  // >= 0
@Negative int z;        // < 0
@Size(min = 2, max = 10) List<String> tags;  // 集合/字符串长度
```

### 2.3 格式类

```java
@Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确") String phone;
@Email String email;              // 简单格式校验（不完全符合 RFC，够用）
@Past LocalDate birthday;         // 过去时间
@Future LocalDate expireDate;     // 未来时间
@PastOrPresent / @FutureOrPresent  // 含当天的版本
```

### 2.4 布尔与跨字段

```java
@AssertTrue boolean agree;    // 必须 true（勾选协议）
@AssertFalse boolean blocked; // 必须 false
```
- 跨字段校验：@AssertTrue 配一个返回 boolean 的 getter 方法实现复杂逻辑（见 4.2）

---

## 3. Spring Boot 集成

### 3.1 @RequestBody + @Valid

```java
@PostMapping("/users")
public User create(@Valid @RequestBody CreateUserRequest req) { ... }
// 校验失败 → MethodArgumentNotValidException
```

### 3.2 表单绑定（非 JSON）

```java
@PostMapping("/form")
public String form(@Valid UserForm form) { ... }
// 校验失败 → BindException
```

### 3.3 方法参数校验（@RequestParam / @PathVariable）

```java
@Validated          // ← Controller 类上必须加 @Validated！
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public User get(@PathVariable @Min(1) Long id,
                    @RequestParam @NotBlank String name) { ... }
}
// 校验失败 → ConstraintViolationException
```
- **注意点**：方法参数上的校验注解（@Min/@NotBlank）必须类上加 `@Validated` 才生效；`@Valid` 在这里不管用

### 3.4 嵌套对象校验（级联）

```java
public class CreateOrderRequest {
    @Valid                    // ← 必须加 @Valid，否则内部不校验！
    @NotNull
    private Address address;
}
```
- **注意点**：嵌套对象字段上忘了 @Valid 是最高频的漏校验原因 —— 只校验外层，内层静默跳过

### 3.5 分组校验（Create / Update 不同约束）

```java
public interface CreateGroup {}
public interface UpdateGroup {}

public class UserDTO {
    @Null(groups = CreateGroup.class)          // 创建时 id 必须为空
    @NotNull(groups = UpdateGroup.class)       // 更新时 id 必填
    private Long id;

    @NotBlank(groups = {CreateGroup.class, UpdateGroup.class})
    private String name;
}

// 使用：指定激活哪组
@PostMapping("/users")
public User create(@Validated(CreateGroup.class) @RequestBody UserDTO dto) { ... }

@PutMapping("/users/{id}")
public User update(@Validated(UpdateGroup.class) @RequestBody UserDTO dto) { ... }
```
- **注意点**：不指定 groups 的注解属于 **Default 组**；一旦指定了组，Default 组的约束**不会**被校验 —— 这是分组最常见的坑（约束「消失」了）

### 3.6 方法级校验（Service 层）

```java
@Validated                  // 类上加
@Service
public class UserService {
    public User getById(@NotNull Long id) { ... }           // 参数校验
    public @NotNull User find() { ... }                     // 返回值校验
}
```
- 适用：Controller 之外的入口（RPC、MQ 消费者）同样防脏数据
- 注意点：Spring 代理生效，同类内部调用 this.xxx() 不校验（与 @Cacheable 同款坑）

### 3.7 程序化校验（手动触发）

```java
ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
Validator validator = factory.getValidator();
Set<ConstraintViolation<UserDTO>> violations = validator.validate(dto);
for (ConstraintViolation<UserDTO> v : violations) {
    log.warn("{}: {}", v.getPropertyPath(), v.getMessage());
}
```
- 适用：非 Spring 环境、批量导入数据校验、规则引擎场景

---

## 4. 自定义校验注解

### 4.1 完整示例：@Phone

```java
// ① 定义注解
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = PhoneValidator.class)   // 关联校验器
public @interface Phone {
    String message() default "手机号格式不正确";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

// ② 实现校验器
public class PhoneValidator implements ConstraintValidator<Phone, String> {
    private static final Pattern P = Pattern.compile("^1[3-9]\\d{9}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        return value == null || P.matcher(value).isValid();  // null 交给 @NotNull 管
    }
}

// ③ 使用
public class UserDTO {
    @Phone
    private String phone;
}
```

**注意点**
- 三个默认方法（message/groups/payload）**一个都不能少**（规范要求）
- isValid 返回 true 表示通过；**null 值一般返回 true**（null 归 @NotNull 管，避免重复职责）
- 需要自定义错误消息时用 `context.disableDefaultConstraintViolation()` + `buildConstraintViolationWithTemplate(...)`

### 4.2 跨字段校验（类级别注解）

```java
// 校验 start < end 的经典例子
@StartBeforeEnd
public class DateRangeRequest {
    private LocalDate start;
    private LocalDate end;
}
```
- 实现要点：注解标在**类**上，ConstraintValidator<A, DateRangeRequest> 里拿到整个对象比较字段
- 或者偷懒方案：类里加 `@AssertTrue public boolean isValid() { return start.isBefore(end); }`

---

## 5. 校验异常处理与消息

### 5.1 三类异常

    异常类型                             触发场景
    MethodArgumentNotValidException    @RequestBody + @Valid 失败
    BindException                      表单绑定校验失败
    ConstraintViolationException       方法参数/方法级校验失败（@Validated）

### 5.2 统一异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<?> handleValid(MethodArgumentNotValidException e) {
        Map<String, String> errors = new LinkedHashMap<>();
        for (FieldError fe : e.getBindingResult().getFieldErrors()) {
            errors.put(fe.getField(), fe.getDefaultMessage());  // 字段 → 错误消息
        }
        return ResponseEntity.badRequest().body(errors);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<?> handleConstraint(ConstraintViolationException e) {
        // e.getConstraintViolations() 遍历取 propertyPath + message
        ...
    }
}
```

### 5.3 消息国际化

```properties
# ValidationMessages.properties（classpath 根目录，自动加载）
user.name.required=用户名不能为空

# 注解里引用
@NotBlank(message = "{user.name.required}")
private String name;
```
- 语言版本：`ValidationMessages_zh_CN.properties` 按 Locale 自动切换
- 注意点：**不支持 Spring MessageSource 的占位符自动注入**（Bean Validation 用自己的 ResourceBundle）；要接 Spring 国际化需自定义 MessageInterpolator

> 关联：业务异常（错误码+多语言 `BusinessException`+`@ControllerAdvice`+`MessageSource`）与 Spring 国际化 MessageSource 机制的完整方案见 [全局异常与国际化详解](../spring/17-全局异常与国际化详解.md)

---

## 6. 框架使用注意点与坑

### 6.1 @Valid vs @Validated

    @Valid（JSR 标准）       @Validated（Spring 扩展）
    级联校验 ✓              级联校验 ✓
    分组校验 ✗               分组校验 ✓（value 指定组）
    方法参数校验 ✗           方法参数/返回值校验 ✓
    Controller 类上无效       类上加它才触发方法级校验

- **规则**：嵌套对象用 @Valid；分组/方法级校验用 @Validated；两者经常同时出现

### 6.2 校验失败的 failFast（立即返回 vs 收集全部）

- 默认：**收集所有违规**（一个请求返回全部字段错误）
- 想快速失败：配置 Hibernate Validator failFast

```yaml
spring:
  jackson:
    # 无此配置！Bean Validation 的 failFast 要这样配：
```
```java
@Bean
public Validator validator() {
    return Validation.byProvider(HibernateValidator.class)
            .configure()
            .failFast(true)          // 第一个错误就停
            .buildValidatorFactory()
            .getValidator();
}
```
- 注意点：一旦自定义 Validator Bean，Spring 的自动配置会被覆盖（其他配置也要在里面补）

### 6.3 校验分层：DTO 校验，别在实体堆注解

- 实体上的校验注解会和多个接口的约束互相打架（创建时必填、更新时必填？）
- **实践**：入参 DTO 上校验（每接口一套），实体保持纯净；跨接口复用用分组

### 6.4 性能注意

- 校验在每次调用时执行，热点路径别上重正则（@Pattern 预编译）
- 大对象校验用 @Valid 级联时注意深度（限制嵌套层级）
- 批量导入用程序化校验（3.7）一次收集所有错误，别逐条抛异常

### 6.5 Jackson 反序列化与 getter 校验

- Controller 的 @RequestBody 校验发生在**反序列化完成后**（构造/设值后）
- 想要「反序列化时就拦截」，可以用 @JsonCreator + compact 逻辑，或用 Jackson 的 `@JsonSetter(nulls=...)` —— 但一般 @Valid 在 Controller 层已足够

### 6.6 校验注解在 JPA 实体上的特殊行为

- @Column(nullable=false) 是 DDL 约束；@NotNull 是 Bean Validation —— 两者不同层，别混
- 实体校验默认在 `prePersist/preUpdate` 触发（Hibernate 集成），可能抛在 DAO 层而不是 Controller —— 分层校验可避免这种意外

---

## 7. 原理（补充知识）

### 7.1 校验管线

    ① 启动时：ValidatorFactory 扫描所有约束注解，构建 ConstraintDescriptor 元数据
    ② 校验时：Validator.validate(obj) 遍历对象属性 → 查找属性上的约束 → 实例化对应 ConstraintValidator（缓存复用）
    ③ 每个 validator 的 isValid 返回结果 → 失败收集为 ConstraintViolation（含 propertyPath + message + 被校验值）
    ④ 返回 Set<ConstraintViolation>，由框架（Spring）转成异常

### 7.2 ConstraintValidator 生命周期

- 单例缓存（每个约束类型一个），**线程安全**，isValid 会被并发调用 → 校验器里别存状态
- initialize(annotation) 只调一次，可预编译 Pattern 等重活

### 7.3 Spring 集成点

- Spring 用 `MethodValidationPostProcessor` 把 @Validated 方法级校验织入 AOP 代理
- Controller 参数校验走 `ModelAttributeMethodProcessor` / `RequestResponseBodyMethodProcessor`（HandlerMethodArgumentResolver 层）
- 两级校验体系：参数解析器（@RequestBody/@ModelAttribute）+ AOP（方法级）→ 所以异常类型不同

---

## 8. 面试追问清单（带答案）

### 8.1 @Valid 和 @Validated 的区别？

A：@Valid 是 JSR 标准注解，支持级联校验；@Validated 是 Spring 扩展，额外支持分组校验和方法级（参数/返回值）校验。嵌套对象用 @Valid，分组/方法级用 @Validated，Controller 方法参数校验必须在类上加 @Validated。

### 8.2 @NotNull / @NotEmpty / @NotBlank 区别？

A：@NotNull 只查 null；@NotEmpty 查 null 或空集合/字符串（" " 空格算非空）；@NotBlank 查 null 或去空格后为空（" " 失败）。String 用 @NotBlank，集合用 @NotEmpty，纯 null 检查用 @NotNull。

### 8.3 嵌套对象校验为什么经常漏？

A：嵌套对象的字段上必须显式加 @Valid 才会级联校验。只给外层对象加 @Valid 时，内层对象的约束被静默跳过 —— 这是最常见的漏校验原因。

### 8.4 分组校验怎么用？不指定组会怎样？

A：注解上写 groups = XxxGroup.class，调用处 @Validated(XxxGroup.class) 激活。不指定组的约束属于 Default 组；一旦显式指定了组，Default 组的约束不会被校验 —— 所以分组后要检查每个约束都归了组。

### 8.5 自定义校验注解怎么做？

A：三步：① @interface 定义注解，加 @Constraint(validatedBy=...) + message/groups/payload 三个默认方法；② 实现 ConstraintValidator<A,T>，isValid 返回是否通过（null 一般返回 true）；③ 使用。校验器是单例缓存、线程安全，重活（正则预编译）放 initialize。

### 8.6 校验异常有哪几种？怎么统一处理？

A：MethodArgumentNotValidException（@RequestBody）、BindException（表单绑定）、ConstraintViolationException（方法参数/方法级）。用 @RestControllerAdvice + @ExceptionHandler 分别处理，遍历 FieldError/ConstraintViolation 拼字段错误信息返回。

### 8.7 Controller 方法参数校验为什么要加 @Validated？

A：@RequestParam/@PathVariable 上的 @Min/@NotBlank 属于方法级校验，由 Spring 的 MethodValidationPostProcessor 通过 AOP 织入，而它只对 @Validated 标注的类生效。@Valid 只处理对象绑定，不触发方法参数校验。

### 8.8 校验失败想立即返回还是收集全部？怎么配？

A：默认收集全部违规（一次返回所有字段错误，前端体验好）。想快速失败（如安全敏感、避免无效计算）：自定义 Validator Bean，HibernateValidator configure().failFast(true)。注意自定义后会覆盖 Spring 自动配置。