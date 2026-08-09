---
tags: [Gradle, 构建工具, Task, 生命周期, 增量构建, up-to-date, 注解]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/构建工具/Gradle）
归属: 01-学习/Java/构建工具/Gradle
---

# 02-Gradle Task与生命周期详解

> 版本基线：Gradle 8.x 为主线，标注 5.x 差异（本机实测 Gradle 5.1.1 + JDK 8）
> 受众：想深入理解 Gradle 执行模型（Task DAG、三阶段生命周期、增量构建）的后端开发。
> 关联笔记：[01-Gradle核心机制详解](01-Gradle核心机制详解.md)、[03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)

## 📋 总纲

1. 三阶段生命周期（初始化/配置/执行）
2. Task 声明与依赖（DAG）
3. 增量构建（up-to-date）原理 ★
4. Task 高级特性（注解/类型/运行时机）★
5. 常用命令速查
6. 小结

## 学习目标

学完本篇你能：

1. 讲透 Gradle 三阶段生命周期与"配置阶段全量执行"的陷阱
2. 声明 Task 及依赖关系，理解 Task 图（DAG）执行顺序
3. 解释增量构建（UP-TO-DATE）原理，会用 @Input/@Output 注解自定义增量 Task
4. 掌握 Task 高级特性（类型、doFirst/doLast、依赖时机）
5. 用常用命令完成构建、查依赖、看项目结构

## 前置知识

- [01-Gradle核心机制详解](01-Gradle核心机制详解.md)——构建脚本、DSL 基础
- [01-依赖与仓库](../Maven/01-依赖与仓库.md)——理解 Maven 生命周期，便于对照

---

## 1. 三阶段生命周期

Gradle 构建分为三个阶段（与 Maven 的生命周期概念不同）：

| 阶段 | 做什么 | 触发 |
|---|---|---|
| **初始化（Initialization）** | 解析 settings.gradle，确定哪些项目参与构建 | 每次构建 |
| **配置（Configuration）** | 执行所有项目的 build.gradle，构建 Task 图（DAG） | 每次构建（**所有项目都会配置**） |
| **执行（Execution）** | 只执行本次要运行的任务及其依赖 | 按需 |

**关键认知**：配置阶段会**执行所有项目的构建脚本**（即使只构建一个子项目），所以配置逻辑要轻量；执行阶段才按任务图选择性运行。

> 💡 **记忆锚点**：初始化定"哪些项目"，配置建"任务图"，执行跑"任务"——配置阶段全量是设计行为，不是 bug。

---

## 2. Task 声明与依赖（DAG）

```groovy
// 声明任务
tasks.register('hello') {
    doLast {
        println 'Hello Gradle!'
    }
}

// 任务依赖
tasks.register('world') {
    dependsOn 'hello'    // world 执行前先执行 hello
    doLast {
        println 'World!'
    }
}
```

```bash
gradle world
# 输出: Hello Gradle! 然后 World!
```

**Task 图（DAG）**：所有 Task 通过 `dependsOn` 构成**有向无环图**，Gradle 按拓扑排序执行，保证依赖先执行、无循环依赖。

**依赖声明时机**（易错点）：
- `dependsOn` 在**配置阶段**确定（构建 Task 图）
- `doLast`/`doFirst` 的动作在**执行阶段**运行
- 所以 `dependsOn` 不能放在 `doLast` 里动态加（那已过图构建期）

---

## 3. 增量构建（up-to-date）原理 ★

Gradle 的核心性能武器：每个 Task 有**输入（inputs）**和**输出（outputs）**。

- 首次执行：正常运行，记录输入快照
- 再次执行：如果**输入没变**，Task 标记 `UP-TO-DATE` 直接跳过
- 输出还存在且输入未变 → 跳过；输入变了 → 重跑

```bash
> Task :compileJava UP-TO-DATE    # 输入没变,跳过编译
> Task :test UP-TO-DATE           # 同理
```

**实测**（Gradle 5.1.1 + JDK 8，`gradle build` 二次执行）：
```
> Task :processTestResources NO-SOURCE
> Task :testClasses UP-TO-DATE
> Task :test NO-SOURCE
BUILD SUCCESSFUL in 1s
```

自定义任务想支持增量构建，声明 inputs/outputs：
```groovy
tasks.register('myTask') {
    inputs.file('src/data.txt')          // 声明输入
    outputs.file('build/result.txt')     // 声明输出
    doLast {
        // 只有输入变化才执行到这里
    }
}
```

---

## 4. Task 高级特性（注解/类型/运行时机）★

### 4.1 用注解声明输入输出（增量任务标准做法）★

除了 DSL 里 `inputs.file()`，标准做法是**写自定义 Task 类 + 注解**：

```java
import org.gradle.api.DefaultTask;
import org.gradle.api.tasks.*;

public abstract class GenerateTask extends DefaultTask {
    @InputFile                       // 声明输入文件
    public abstract RegularFileProperty getInputFile();

    @OutputFile                      // 声明输出文件
    public abstract RegularFileProperty getOutputFile();

    @TaskAction                      // 任务动作
    public void generate() {
        // 只有输入变化才执行（增量判断交给 Gradle）
    }
}
```

**常用注解**：

| 注解 | 作用 |
|---|---|
| `@InputFile` / `@InputFiles` | 声明输入文件 |
| `@InputDirectory` | 声明输入目录 |
| `@OutputFile` / `@OutputFiles` | 声明输出文件 |
| `@OutputDirectory` | 声明输出目录 |
| `@Input` | 声明普通输入属性（String/int） |
| `@TaskAction` | 标注任务执行动作 |
| `@Incremental` | 增量文件处理（只处理变化的文件） |

### 4.2 Task 的 `doFirst` / `doLast`

```groovy
tasks.register('example') {
    doFirst { println '1. 最先执行' }   // 动作在最前面
    doLast  { println '3. 最后执行' }   // 动作在最后
    println '0. 配置阶段执行'            // 这行在配置阶段就跑
}
```

**关键**：Task 定义体里的顶层代码（非 doFirst/doLast）在**配置阶段**执行；`doFirst`/`doLast` 里的代码在**执行阶段**执行。

### 4.3 常用内置 Task 类型

| 类型 | 用途 |
|---|---|
| `Copy` | 复制文件 |
| `Zip` / `Tar` | 打包压缩 |
| `Delete` | 删除文件 |
| `Exec` | 执行外部命令 |
| `JavaExec` | 运行 Java 程序 |

```groovy
tasks.register('copyDocs', Copy) {
    from 'src/docs'
    into 'build/docs'
}
```

### 4.4 增量任务（Incremental Task）★

`@Incremental` 注解 + `IncrementalTaskInputs`，让任务**只处理变化的输入文件**（不是全量重跑）：

```java
@Incremental
@TaskAction
public void generate(IncrementalTaskInputs inputs) {
    inputs.outOfDate(change -> process(change.file));   // 只处理新增/修改的
    inputs.removed(change -> cleanup(change.file));      // 处理删除的
}
```

---

## 5. 常用命令速查

| 命令 | 作用 |
|---|---|
| `gradle tasks` | 列出所有可用任务 |
| `gradle build` | 完整构建（编译+测试+打包） |
| `gradle clean` | 清理 build/ 目录 |
| `gradle test` | 运行测试 |
| `gradle dependencies` | 查看依赖树 |
| `gradle dependencies --configuration compileClasspath` | 查看指定依赖范围 |
| `gradle projects` | 查看多项目结构 |
| `gradle --parallel build` | 并行构建 |
| `gradle --build-cache build` | 开启构建缓存 |
| `gradle init` | 初始化项目（交互式） |
| `gradle wrapper --gradle-version 8.10.2` | 生成指定版本 wrapper |
| `./gradlew build` | 用 wrapper 构建（团队统一） |

---

## 6. 小结

- 三阶段生命周期：初始化 → 配置（全量）→ 执行（按任务图）
- Task 构成 **DAG**，`dependsOn` 定依赖，`doFirst`/`doLast` 定执行动作
- **增量构建**（UP-TO-DATE）靠声明 input/output，用 `@InputFile`/`@OutputFile` 注解实现
- **@Incremental** 支持只处理变化的文件，更进一步省时间
- 配置阶段全量执行是设计行为，配置逻辑要保持轻量

## 下一篇

[03-Gradle依赖管理详解](03-Gradle依赖管理详解.md)——Configuration 体系、冲突解析、Version Catalog

## 参考资料

- [Gradle 官方：增量构建](https://docs.gradle.org/current/userguide/incremental_build.html)，查询日期：2026-08-09
- [Gradle 官方：高级任务](https://docs.gradle.org/current/userguide/custom_tasks.html)，查询日期：2026-08-09
- [Gradle 用户手册](https://docs.gradle.org/current/userguide/)，查询日期：2026-08-09