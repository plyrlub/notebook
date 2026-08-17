---
tags: [Java, Spring, IoC, 实践, XML, 注解, JavaConfig]
创建日期: 2026-08-14
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# Spring核心·IoC与Bean生命周期实践

> 版本基线：Spring 5.x/6.x，传统 XML + 注解 + JavaConfig 三套写法覆盖
> 受众：先读 [01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)（概念/原理），本篇只管"怎么配置、怎么写代码"。
> 前置：[01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)；有代码即看本篇，概念不清回详解。

## 📋 总纲

1. XML 装配：最完整的传统写法
2. XML 里的属性/标签含义清单（一个配置值 = 一个行为）
3. 注解式装配（@Component/@Autowired）
4. JavaConfig 装配（@Configuration/@Bean）
5. 三种方式混用与区别
6. 注意点与踩坑

## 1. XML 装配（传统，完整可运行）

> 伪代码示例，跑通即可，类体只留关键字段。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="
           http://www.springframework.org/schema/beans
           http://www.springframework.org/schema/beans/spring-beans.xsd">

    <!-- 基础 bean：无依赖 -->
    <bean id="userDao" class="com.example.dao.UserDao"/>

    <!-- 构造器注入：orderService 依赖 userDao -->
    <bean id="orderService" class="com.example.service.OrderService">
        <constructor-arg ref="userDao"/>      <!-- 或 index="0" -->
    </bean>

    <!-- setter 注入：按属性名 -->
    <bean id="orderService2" class="com.example.service.OrderService">
        <property name="userDao" ref="userDao"/>
    </bean>

    <!-- 作用域 & 懒加载 & 初始化/销毁 -->
    <bean id="taskRunner" class="com.example.task.TaskRunner"
          scope="prototype"
          lazy-init="true"
          init-method="init"
          destroy-method="cleanup">
        <property name="size" value="100"/>   <!-- 基本类型/字符串，用 value -->
    </bean>
</beans>
```

## 2. XML 属性/配置值含义清单（重点看这里）

> 每个配置项 = 一个确切行为，逐条理解比背代码更重要。

| 属性 | 取值示例 | 含义 / 影响 |
| --- | --- | --- |
| `id` | `userDao` | bean 唯一标识，ioc.getBean("userDao") 用 |
| `class` | `com.example.dao.UserDao` | 全限定类名，容器反射 new 出来 |
| `scope` | `singleton`(默认)/`prototype` | singleton=整个容器一份；prototype=每次 getBean 新实例 |
| `lazy-init` | `true/false`(默认) | singleton 下延迟到首次用时才实例化（prototype 本就是 lazy） |
| `init-method` | `init` | 初始化回调（实例化+注入后调）；等价于 `@Bean(initMethod)` |
| `destroy-method` | `cleanup` | 容器关闭时销毁回调（仅 singleton 有效） |
| `abstract` | `true` | 抽象 bean，仅作继承模板不实例化（配合 `parent`） |
| `parent` | 其它 bean id | 继承父 bean 的配置（XML 继承，非 Java 继承） |
| `primary` | `true` | 多实现时该 bean 为默认首选（等价 @Primary） |
| `depends-on` | `a,b` | 强制 A/B 先于本 bean 创建（无引用依赖时的顺序控制） |
| `autowire` | `byName/byType` | 自动注入策略，XML 时代少用（现在注解为主） |

**property vs constructor-arg**：
- `property name=` → **setter 注入**（按属性名，须有 setter）
- `constructor-arg` → **构造器注入**（按参数顺序/index/type）

**ref vs value**：
- `ref="beanId"` → 引用**另一个 bean**（注入对象）
- `value="100"` / `value="abc"` → 注入**字面量**（基本类型/字符串，容器自动转类型）

## 3. 注解式装配（混合 XML 扫描）

```xml
<!-- 开启组件扫描：扫 @Component/@Service/@Repository/@Controller -->
<context:component-scan base-package="com.example"/>
<!-- 或只要扫描不用过滤器：base-package 指定起始包，容器递归扫子包 -->
```

```java
@Service
public class OrderService {
    // 字段注入（推荐构造器注入，见下）
    @Autowired private UserDao userDao;
}
```

**注解三件套**：`@Component`(标注类) + `@ComponentScan`(扫描位置) + `@Autowired`(注入) 缺一不可——只有前两者没注入 = 不自动 `new`。

> 最佳实践：字段注入简洁但难测试；**推荐 final 字段 + 构造器注入**（不可变、显式依赖、防循环依赖误用）。

## 4. JavaConfig 装配（主流）

```java
@Configuration
public class AppConfig {
    @Bean
    public DataSource dataSource() {           // 方法名=bean id，返回值=类型
        return new HikariDataSource();
    }

    @Bean
    public OrderService orderService(UserDao userDao) {  // 参数=自动注入
        return new OrderService(userDao);
    }
}
```

**@Bean vs @Component**：
- `@Bean` 用在 `@Configuration` 类的方法上，返回对象注册为 bean——适合**第三方库/无源码类/条件复杂构造**
- `@Component` 标在**自研类**上，容器扫描后反射注册

> ⚠️ **Bean 方法返回类型不能写太泛**：`@Bean Object foo()` 容器不知道具体类型，无法按类型注入到 `@Autowired Xxx`。必须返回具体类型。

## 5. 三种方式对比

| 方式 | 入口 | 适用 | 装配粒度 |
| --- | --- | --- | --- |
| XML | `<bean>` | 老项目/第三方 bean/无源码 | 全部属性手动列 |
| 注解 | `@ComponentScan` | 自研类，主流 | 扫描即用 |
| JavaConfig | `@Configuration`+`@Bean` | 第三方/条件装配/多步初始 | 方法级控制 |

## 6. 注意点与踩坑

- **构造器注入遇到循环依赖直接报错**：A 构造需 B、B 构造需 A，谁也先 new 不出 → `BeanCurrentlyInCreationException`。字段/setter 注入才有三级缓存兜底（见详解 3.7）。
- **@Bean 方法里手动 new 的对象不被容器管**：生命周期回调、AOP 都不生效，须作为 bean 声明。
- **单例注入 prototype 失效**：单例 bean 里注入的 prototype bean 是启动时固定的同一实例，每次不会新造——要用 `ObjectProvider` 或 `@Scope(proxyMode=...)`。
- **同名 bean**：同类型多个实现，`@Autowired` byType 报 `NoUniqueBeanDefinitionException` → 用 `@Primary`（默认）/ `@Qualifier`（精确）。
- **XML 里 value 转类型**：`value="2026-08-01"` 注入 Date 需配 `CustomEditor`/`@DateTimeFormat`，纯 XML 不自带。
- 参考踩坑：详见知识库踩坑记录（配置类 #1）

## 7. 关联

- 详解（上一知识点）：[01-Spring核心·IoC与Bean生命周期详解](01-Spring核心·IoC与Bean生命周期详解.md)（本篇所有配置对应的生命周期阶段）
- 下一篇：[03-SpringMVC执行流程详解](03-SpringMVC执行流程详解.md)（下一个知识点，紧邻）
