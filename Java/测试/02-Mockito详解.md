---
tags: [Mockito, Mock, 单元测试, 测试框架, verify, stub, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/测试）
归属: 01-学习/Java/测试
---

# 02-Mockito详解

> 版本基线：Mockito 5.x（Java 单元测试 Mock 事实标准）
> 受众：Java 后端开发，已会 [01-JUnit 5详解](01-JUnit 5详解.md)，要 mock 外部依赖写隔离的单元测试。默认你懂 JUnit、依赖注入。
> 关联笔记：[00-测试体系总览](00-测试体系总览.md)、[01-JUnit 5详解](01-JUnit 5详解.md)、[04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)

## 📋 总纲

- 1. Mockito 是什么：Mock 框架
- 2. 快速上手
- 3. Stub（打桩）
- 4. Verify（验证交互）
- 5. 注解：@Mock/@Spy/@Captor/@InjectMocks
- 6. ArgumentCaptor（参数捕获）
- 7. Spy 与 doReturn
- 8. Mock final/static（内联 mock）
- 9. 最佳实践与常见踩坑

## 学习目标

学完本篇你能：

1. 说清 Mock 的意义（隔离外部依赖，聚焦被测单元）
2. 用 when/thenReturn 打桩
3. 用 verify 验证交互（调用次数/顺序）
4. 用 @Mock/@InjectMocks/@Spy/@Captor 四注解
5. 用 ArgumentCaptor 捕获参数断言
6. Mock final 类/静态方法
7. 避开 Mockito 常见坑（过度 mock/无效打桩）

## 前置知识

- [01-JUnit 5详解](01-JUnit 5详解.md)——测试框架基础
- 需掌握：依赖注入、接口设计

---

## 1. Mockito 是什么：Mock 框架

**一句话记忆**：Mockito 是 Java 单元测试的 **Mock（模拟）框架**——把外部依赖（DAO/第三方服务/消息队列）替换成"假对象"，让你**只测被测类的逻辑**。

**为什么要 mock**：

```java
// 被测类: UserService 依赖 UserRepository(数据库)
class UserService {
    private final UserRepository repo;
    UserService(UserRepository repo) { this.repo = repo; }

    String getUsername(Long id) {
        return repo.findById(id).getName();
    }
}

// ❌ 不 mock: 测试要连数据库
// ✅ mock: UserRepository 用假实现, 只测 UserService 逻辑
```

```
测试 → UserService(真) → UserRepository(Mock, 假)
                              ↑ 返回预设数据, 不碰数据库
```

> 💡 **记忆锚点**：**Mock = 替身演员**——主角（被测类）是真身，配角（依赖）找替身，替身按剧本（stub）演。

---

## 2. 快速上手

```java
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

class UserServiceTest {

    @Test
    void getUsername_should_return_name() {
        // 1. 创建 mock
        UserRepository repo = mock(UserRepository.class);

        // 2. 打桩: 当 findByid(1) 被调用时返回预设 User
        User user = new User(1L, "Alice");
        when(repo.findById(1L)).thenReturn(user);

        // 3. 被测对象注入 mock
        UserService service = new UserService(repo);

        // 4. 断言
        assertEquals("Alice", service.getUsername(1L));

        // 5. 验证交互
        verify(repo).findById(1L);
    }
}
```

**核心流程**：**mock 创建 → stub 打桩 → 注入 → 断言 → verify 验证**。

---

## 3. Stub（打桩）

**打桩 = 预设 mock 方法的返回值**：

```java
// 基本打桩
when(repo.findById(1L)).thenReturn(user);
when(repo.findAll()).thenReturn(List.of(user1, user2));

// 连续调用返回不同值
when(repo.nextId()).thenReturn(1L, 2L, 3L);

// 抛异常(测试异常分支)
when(repo.findById(999L)).thenThrow(new NotFoundException("不存在"));

// 按参数匹配(any/eq)
when(repo.findByName(anyString())).thenReturn(user);
when(repo.findByName(eq("Alice"))).thenReturn(user);  // 精确匹配

// 无返回值方法
doNothing().when(repo).delete(anyLong());
```

**参数匹配器**：

| 匹配器 | 作用 |
|---|---|
| `any()/anyString()/anyLong()` | 任意值 |
| `eq(value)` | 精确匹配 |
| `contains/startsWith/endsWith` | 字符串匹配 |
| `isNull/isNotNull` | 空判断 |

> ⚠️ **易错**：匹配器不能混用——`when(repo.find(eq("a"), anyLong()))` 里**要么全用匹配器，要么全用具体值**。

---

## 4. Verify（验证交互）

**验证 = 断言"某个方法被调用了几次、以什么参数"**：

```java
// 基本验证: 调用过一次
verify(repo).findById(1L);

// 验证次数
verify(repo, times(3)).findById(1L);
verify(repo, never()).delete(anyLong());
verify(repo, atLeastOnce()).findAll();
verify(repo, atMost(2)).save(any());

// 验证无交互
verifyNoInteractions(repo);

// 验证调用顺序
InOrder inOrder = inOrder(repo);
inOrder.verify(repo).findById(1L);
inOrder.verify(repo).save(any());
```

| 验证模式 | 含义 |
|---|---|
| `times(n)` | 恰好 n 次 |
| `never()` | 0 次 |
| `atLeastOnce()/atLeast(n)` | 至少 |
| `atMost(n)` | 至多 |
| `timeout(ms)` | 超时内完成 |

> 💡 **记忆锚点**：**stub 管"返回什么"，verify 管"调没调"**——前者测数据，后者测行为。

---

## 5. 注解：@Mock/@Spy/@Captor/@InjectMocks ★

```java
@ExtendWith(MockitoExtension.class)   // JUnit5 集成(关键!)
class UserServiceTest {

    @Mock                       // 自动创建 mock
    UserRepository repo;

    @Mock
    MailService mailService;

    @InjectMocks                // 自动把上面的 mock 注入被测对象
    UserService service;

    @Test
    void register_should_save_and_send_mail() {
        service.register(new User("Bob"));

        verify(repo).save(any(User.class));
        verify(mailService).sendWelcomeMail(anyString());
    }
}
```

| 注解 | 作用 |
|---|---|
| `@Mock` | 创建 mock 对象 |
| `@InjectMocks` | 把 @Mock/@Spy 注入被测对象（按构造器/Setter/字段） |
| `@Spy` | 创建 spy（部分 mock，真实对象） |
| `@Captor` | 简化 ArgumentCaptor 创建 |

> ⚠️ **关键**：必须加 `@ExtendWith(MockitoExtension.class)`（JUnit 5）注解才生效。

**@InjectMocks 注入顺序**：构造器注入 → Setter 注入 → 字段注入（按此优先级）。

---

## 6. ArgumentCaptor（参数捕获）

**场景**：需要断言"传给 mock 的参数内容"（而不只是调没调）：

```java
@Captor
ArgumentCaptor<User> userCaptor;

@Test
void register_should_save_user_with_generated_id() {
    service.register(new User("Alice"));

    verify(repo).save(userCaptor.capture());       // 捕获参数
    User saved = userCaptor.getValue();

    assertEquals("Alice", saved.getName());
    assertNotNull(saved.getId());                  // 断言被修改过的参数
}

// 捕获多次调用
verify(repo, times(2)).save(userCaptor.capture());
List<User> all = userCaptor.getAllValues();        // 所有捕获值
```

---

## 7. Spy 与 doReturn

**Spy = 部分 mock**：真实对象上**只 mock 部分方法**，其余走真实逻辑。

```java
List<String> list = new LinkedList<>();
List<String> spy = spy(list);

spy.add("one");
spy.add("two");

verify(spy).add("one");           // 验证真实调用
assertEquals(2, spy.size());      // 真实方法仍执行

// 只 mock size(): 用 doReturn(不能用 when!)
doReturn(100).when(spy).size();   // when(spy.size()) 会先执行真实方法(副作用)
assertEquals(100, spy.size());
```

| 方法 | 适用 |
|---|---|
| `when(mock.method()).thenReturn(x)` | mock 对象（推荐） |
| `doReturn(x).when(spy).method()` | **spy 对象**（避免真实方法副作用） |
| `doThrow/doAnswer/doCallRealMethod` | 异常/自定义/真实执行 |

> ⚠️ **易错**：spy 上用 `when(spy.size())` 会**先调用真实方法**再打桩——有副作用时用 `doReturn`。

---

## 8. Mock final/static（内联 mock）

**Mockito 2+ 默认支持 mock final 类/方法**；**静态方法/构造器 mock 在 Mockito 5.x 已内置（inline mock-maker 为默认，零额外依赖）**：

```java
// mock 静态方法(无需 mockito-inline, 5.x 内置)
try (MockedStatic<Utility> mocked = mockStatic(Utility.class)) {
    mocked.when(() -> Utility.getId()).thenReturn(42L);

    assertEquals(42L, service.getCurrentId());

    mocked.verify(() -> Utility.getId());
}

// mock 构造器(5.x 内置)
try (MockedConstruction<Foo> mocked = mockConstruction(Foo.class)) {
    Foo foo = new Foo();          // 返回 mock
    when(foo.bar()).thenReturn("mocked");
}
```

> 📌 **版本说明（2026-08 复查补充）**：Mockito 5.0 起 inline mock-maker 为默认，静态/构造器 mock **开箱即用**；只有用 Mockito 3.x 老版本才需要额外 `mockito-inline` 依赖。老教程里的 `mockito-inline` 依赖在 5.x 已不需要。

> ⚠️ **谨慎**：静态/构造器 mock 是"最后手段"——过度使用说明设计有问题（应依赖注入）。

---

## 9. 最佳实践与常见踩坑

### 最佳实践

- **只 mock 外部依赖**：不 mock 被测类自身；不过度 mock（简单对象用真实值）
- **一个测试一个行为**：断言聚焦一个场景
- **verify 必要交互**：关键副作用（保存/发送/删除）要 verify
- **参数匹配用 any/eq 谨慎**：太宽泛会掩盖 bug
- **配合 [04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)**：断言更可读

### 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #M1 | 忘 @ExtendWith | @Mock 为 null | 加 MockitoExtension |
| #M2 | 匹配器混用 | InvalidUseOfMatchersException | 全用匹配器或全用具体值 |
| #M3 | spy 用 when | 真实方法副作用 | doReturn().when(spy) |
| #M4 | 无效打桩 | UnnecessaryStubbingException | 打桩的方法没被调用(检查逻辑) |
| #M5 | 过度 mock | 测试脆弱/失焦 | 只 mock 外部依赖 |
| #M6 | mock 静态方法没关 | 影响其他测试 | try-with-resources 自动关闭 |

## 小结

- Mockito 是 Mock 框架：替身依赖，聚焦被测逻辑
- 核心三件套：**stub（when/thenReturn）+ verify（交互断言）+ captor（参数捕获）**
- 注解四件套：@Mock/@InjectMocks/@Spy/@Captor（配 @ExtendWith）
- Spy 部分 mock，doReturn 处理副作用；final/static 用 inline mock
- 最佳实践：只 mock 外部依赖，一个测试一个行为

## 下一篇

[04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)——让断言更可读

## 参考资料

- [Mockito 官方 Javadoc](https://site.mockito.org/javadoc/current/org/mockito/Mockito.html)，查询日期：2026-08-09
- [Baeldung: Mockito Annotations](https://www.baeldung.com/mockito-annotations)，查询日期：2026-08-09
- [Mockito GitHub](https://github.com/mockito/mockito)，查询日期：2026-08-09
