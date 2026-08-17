---
tags: [Java, 三方库, MapStruct, APT, 代码生成, 对象映射, DTO]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/三方库）
归属: 01-学习/Java/三方库
---

# MapStruct详解

> 适用版本：1.6.3（2024 年稳定版）
> 实测环境：mapstruct 1.6.3 + mapstruct-processor 1.6.3 + JDK 17.0.12（实测数据标注于各节）
> 关联笔记：[Java注解机制详解](../JDK基础库/核心机制/Java注解机制详解.md)（APT 处理方式）、[Lombok详解](Lombok详解.md)（同为注解处理器但路线不同）、[Java参数校验详解](../框架/通用实践/Java参数校验详解.md)（同属 DTO/实体转换场景）

## 📋 总纲

1. MapStruct 是什么：编译期 Bean 映射代码生成器
2. 原理：APT（JSR 269）生成实现类（实测生成源码全文）
3. 快速开始：依赖、@Mapper、INSTANCE 单例
4. 核心注解：@Mapper / @Mapping / @Mappings / @Named / @ValueMapping
5. 映射场景逐个拆解：同名自动映射 / 异名 / 嵌套平铺 / 集合 / 常量（全实测）
6. 与 BeanUtils 对比：性能、类型安全、编译期检查
7. 高级特性：自定义转换、枚举、Ignore、Spring 集成
8. 易错点与常见问题

## 一、MapStruct 是什么

MapStruct 是一个 **Java 注解处理器**，在**编译时**自动生成类型安全的对象映射代码。你只需要定义一个 Mapper 接口声明映射方法，编译时 MapStruct 生成实现类——典型场景：Entity ↔ DTO ↔ VO 转换。

| 维度 | 说明 |
| --- | --- |
| 本质 | 代码生成器（不是运行时框架） |
| 原理 | JSR 269 可插拔注解处理（APT），编译期生成 `XxxMapperImpl` |
| 运行时开销 | **零**（生成的是普通方法调用，无反射） |
| 类型安全 | 编译期检查字段类型，不匹配直接编译失败 |
| 版本 | 当前 1.6.x（1.6.3），要求 Java 8+ |

一句话：**写接口，编译期自动生成实现**——把"手写 getter/setter 赋值"这种样板代码交给编译器。

## 二、原理：APT 生成实现类（实测）

MapStruct 基于 JSR 269：javac 编译时扫描 `@Mapper` 注解，由 `org.mapstruct.ap.MappingProcessor` 生成实现类源码并参与编译。**标准 APT 只能生成新文件**（这与 [Lombok详解](Lombok详解.md) 直接改 AST 的黑科技路线不同）。

实测（mapstruct 1.6.3 + JDK 17.0.12）：对下面的 Mapper 接口——

```java
@Mapper
public interface UserMapper {
    UserMapper INSTANCE = Mappers.getMapper(UserMapper.class);

    @Mappings({
        @Mapping(source = "name", target = "userName"),          // 字段名不同
        @Mapping(source = "address.city", target = "city"),      // 嵌套对象平铺
        @Mapping(source = "address.street", target = "street"),
        @Mapping(target = "remark", constant = "from-mapstruct") // 目标独有字段用常量
    })
    UserDTO toDTO(UserEntity entity);

    List<UserDTO> toDTOList(List<UserEntity> entities);          // 集合映射
}
```

javac 编译时（`-processorpath` 指向 mapstruct-processor）生成的 `UserMapperImpl.java`（真实生成源码）：

```java
@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-08-08T07:01:03+0800",
    comments = "version: 1.6.3, compiler: javac, environment: Java 17.0.12 (Oracle Corporation)"
)
public class UserMapperImpl implements UserMapper {

    @Override
    public UserDTO toDTO(UserEntity entity) {
        if ( entity == null ) {
            return null;                       // ← 自动 null 安全
        }
        UserDTO userDTO = new UserDTO();
        userDTO.setUserName( entity.getName() );               // 异名映射
        userDTO.setCity( entityAddressCity( entity ) );        // 嵌套 → 私有方法
        userDTO.setStreet( entityAddressStreet( entity ) );
        userDTO.setId( entity.getId() );                       // 同名自动映射
        userDTO.setEmail( entity.getEmail() );
        userDTO.setAge( entity.getAge() );
        userDTO.setRemark( "from-mapstruct" );                 // 常量直接赋值
        return userDTO;
    }

    @Override
    public List<UserDTO> toDTOList(List<UserEntity> entities) {
        if ( entities == null ) { return null; }
        List<UserDTO> list = new ArrayList<UserDTO>( entities.size() );
        for ( UserEntity userEntity : entities ) {
            list.add( toDTO( userEntity ) );
        }
        return list;                           // ← 集合映射 = 循环调用单对象映射
    }

    private String entityAddressCity(UserEntity userEntity) {
        AddressEntity address = userEntity.getAddress();
        if ( address == null ) { return null; }                // ← 嵌套 null 安全
        return address.getCity();
    }
    // entityAddressStreet 同理
}
```

实测运行输出：

```
id=100, userName=robin, email=robin@example.com, city=Shanghai, street=Nanjing Rd, remark=from-mapstruct
list size=2
null -> null
```

关键认知（从生成代码反推设计）：

- 生成的是**普通 Java 代码**（setter 调用），无反射 → 性能等同手写。
- **自动 null 安全**：入参 null 返回 null；嵌套对象 null 返回 null（不会 NPE）。
- **嵌套平铺**：`address.city` 展开成私有辅助方法，内部逐层判空。
- **集合映射**：循环 + 复用单对象映射方法，天然支持 List/Set/Map。
- **@Generated 标注**：生成代码带版本与环境信息，便于排查。

## 三、快速开始

```xml
<!-- Maven -->
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>1.6.3</version>
</dependency>

<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.13.0</version>
    <configuration>
        <annotationProcessorPaths>
            <path>
                <groupId>org.mapstruct</groupId>
                <artifactId>mapstruct-processor</artifactId>
                <version>1.6.3</version>
            </path>
            <!-- 与 Lombok 同用需加 binding（见第七节） -->
        </annotationProcessorPaths>
    </configuration>
</plugin>
```

```java
@Mapper
public interface UserMapper {
    UserMapper INSTANCE = Mappers.getMapper(UserMapper.class);   // 推荐单例
    UserDTO toDTO(UserEntity entity);
}
// 使用：UserMapper.INSTANCE.toDTO(entity)
```

要点：`Mappers.getMapper` 返回生成的实现类单例（约定俗成命名 `INSTANCE`）；也可 `componentModel = "spring"` 让 Spring 管理（见第七节）。

## 四、核心注解

| 注解 | 作用 | 关键属性 |
| --- | --- | --- |
| @Mapper | 标注映射器接口 | componentModel（default/spring/jsr330）、uses（引用其他转换器） |
| @Mapping | 定义单个字段映射 | source / target / constant / expression / ignore / defaultValue |
| @Mappings | 多个 @Mapping 容器 | - |
| @Named | 给自定义转换方法命名 | 配合 qualifiedByName 指定用哪个 |
| @ValueMapping | 枚举/值映射 | source / target |

@Mapping 属性逐个：

| 属性 | 说明 | 示例 |
| --- | --- | --- |
| source / target | 源字段/目标字段（支持 `a.b.c` 点路径） | `@Mapping(source="address.city", target="city")` |
| constant | 目标字段用固定常量 | `@Mapping(target="remark", constant="from-mapstruct")` |
| expression | 目标字段用表达式（慎用，编译期拼进代码） | `@Mapping(target="time", expression="java(new Date())")` |
| ignore | 忽略该字段（不映射） | `@Mapping(target="id", ignore=true)` |
| defaultValue | 源为 null 时给默认值 | `@Mapping(source="age", target="age", defaultValue="0")` |

## 五、映射场景逐个拆解（全实测）

### ① 同名字段：零配置自动映射

类型相同、名字相同的字段自动赋值（实测 id/email/age 全部自动映射，无需 @Mapping）。

### ② 字段名不同：@Mapping

`@Mapping(source = "name", target = "userName")` —— 生成代码 `userDTO.setUserName(entity.getName())`（实测）。

### ③ 嵌套对象平铺

`@Mapping(source = "address.city", target = "city")` —— 生成私有辅助方法逐层判空（实测生成源码）。

### ④ 集合映射：自动支持

声明 `List<UserDTO> toDTOList(List<UserEntity>)` 即可，生成循环 + 复用 toDTO（实测）。

### ⑤ 目标独有字段：constant / defaultValue / ignore

```java
@Mapping(target = "remark", constant = "from-mapstruct")  // 常量
@Mapping(source = "age", target = "age", defaultValue = "0")  // 源 null 时默认值
@Mapping(target = "secret", ignore = true)                // 忽略不映射
```

注意：目标有而源没有的字段，**不配置就会编译失败**（unmapped target 警告可配 unmappedTargetPolicy 控制）。

### ⑥ 反向映射：inverse

```java
@Mapper
public interface UserMapper {
    UserDTO toDTO(UserEntity entity);
    @InheritInverseConfiguration           // 复用 toDTO 的映射规则反向
    UserEntity toEntity(UserDTO dto);
}
```

## 六、与 BeanUtils 对比

| 维度 | MapStruct | Spring BeanUtils / Apache BeanUtils |
| --- | --- | --- |
| 时机 | 编译期生成代码 | 运行时反射 |
| 性能 | **约 7~8 倍于 BeanUtils**（零反射） | 反射开销 |
| 类型安全 | 编译期检查（类型不匹配编译失败） | 运行时才暴露 |
| 字段名不同 | @Mapping 显式配置 | 不映射（静默丢失） |
| 嵌套/集合 | 原生支持 | 需手写或丢失 |
| 编译期检查 | 未映射字段可报错 | 无 |
| 使用成本 | 需加依赖 + 注解处理器 | 开箱即用 |

结论：**新项目 DTO 转换首选 MapStruct**；BeanUtils 的"便利"以类型不安全为代价（字段名拼错静默丢失，线上才暴露）。

## 七、高级特性

### 自定义转换方法

```java
@Mapper
public interface OrderMapper {
    @Mapping(target = "statusDesc", source = "status", qualifiedByName = "statusDesc")
    OrderDTO toDTO(OrderEntity entity);

    @Named("statusDesc")
    default String toDesc(String status) {
        return "ACTIVE".equals(status) ? "生效" : "失效";
    }
}
```

`uses` 属性可引用外部转换器类（如日期格式化工具），自动用于嵌套转换。

### 枚举转换

```java
@Mapper
public interface EnumMapper {
    // 同名枚举自动映射；异名用 @ValueMapping
    @ValueMapping(source = "ACTIVE", target = "ENABLED")
    @ValueMapping(source = MappingConstants.NULL, target = "UNKNOWN")
    TargetStatus map(SourceStatus status);
}
```

### Spring 集成

```java
@Mapper(componentModel = "spring")        // 生成 @Component 实现类
public interface UserMapper {
    UserDTO toDTO(UserEntity entity);
}
// 使用时 @Autowired 注入 UserMapper 即可
```

### 与 Lombok 共存（重点坑）

Lombok 和 MapStruct 都是注解处理器，**编译顺序问题**会导致"找不到 getter/setter"。解法：

```xml
<!-- maven-compiler-plugin 里加 lombok-mapstruct-binding -->
<path>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok-mapstruct-binding</artifactId>
    <version>0.2.0</version>
</path>
```

binding 插件保证 Lombok 先生成 getter/setter，MapStruct 后读取（Lombok 与 MapStruct 的协作原理见 [Lombok详解](Lombok详解.md)）。

## 八、易错点与常见问题

- **目标字段未映射**：源没有对应字段且未配 ignore/constant → 编译警告/失败（`unmappedTargetPolicy = ReportingPolicy.ERROR` 可强制失败）。
- **忽略 Lombok 共存**：实体用 @Data 时忘了 binding 依赖 → "Unknown property" 编译错误。
- **expression 滥用**：表达式拼进生成代码，编译期才检查，写错难排查，优先用自定义方法（@Named）。
- **循环引用映射**：A→B→A 的嵌套映射会无限递归（生成代码也是），需 @Mapping(ignore) 打断。
- **泛型映射**：复杂泛型（如 Map<String, List<T>>）需自定义转换方法辅助。
- **修改源模型后**：重新编译即可，生成代码自动更新（不要手改 UserMapperImpl——下次编译被覆盖）。

## 参考资料

- [MapStruct 官方文档](https://mapstruct.org/documentation/stable/reference/html/)，查询日期：2026-08-08
- [Commons BeanUtils 与 MapStruct 性能对比分析（OSCHINA）](https://my.oschina.net/emacs_7986973/blog/19211188)，查询日期：2026-08-08
- [MapStruct 使用教程 2024 高级版（阿里云）](https://developer.aliyun.com/article/1551640)，查询日期：2026-08-08
- 实测数据：mapstruct 1.6.3 + JDK 17.0.12 本机编译运行（demo 在 /tmp/mapstruct-demo，生成源码见 UserMapperImpl.java）
