---
tags: [Java, Spring, 错误码, 配置中心, Nacos, Apollo, Maven, 插件, 代码生成, ErrorCode]
创建日期: 2026-08-15
状态: ✅ 已归档（01-学习/Java/框架/spring）
归属: 01-学习/Java/框架/spring
---

# 错误码配置中心 · Nacos 生成插件

> **本篇定位**：`[[17-全局异常与国际化详解]]` §3.2 讲到的「错误码配置中心 + 生成式同步」的可落地实现。17 里是**思路**，本篇是**能跑的代码**。
> **机制**：编译期调 Nacos/配置中心 openAPI 拉错误码 → 生成 `ErrorCode.java` 进 `generated-sources` → 本地开发/CI 都可用。
> **版本基线**：Maven 3.6+、JDK 17、Spring Boot（业务侧）任意版本均适用；本文件代码独立可运行。

## 📋 总纲

1. 目标与边界：**只读+生成**，不碰上传/权限
2. Nacos 侧准备：dataId 约定 + `code=描述` 格式 + `Locale` 语言变体
3. 插件工程：Maven plugin + 拉取 + 模板生成（完整代码）
4. **双产物**：`ErrorCode` enum（兜底）+ 多语言 `messages*.properties`（运行期展示，打包进 jar）
5. 业务侧用法：本地顺序 + `.gitignore` + CI 再拉
6. Apollo 对比：结构同、仅地址/认证/客户端不同

---

## 一、目标与边界

- **要解决的**：错误码真源在配置中心，业务代码编译期要有 `ErrorCode` 类型可引用。
- **做法**：Maven 构建时调 Nacos openAPI 拉「本业务段 + 公共码」→ 生成 `ErrorCode.java` → 进 `target/generated-sources` → 编译。
- **边界（重要）**：本工具**只读取、只生成，不做任何写入**。新增码走配置中心后台（开发环境任何人可新增自己的码段；公共/领域段改删需权限）。这样既保快速迭代，又守住"公共码只加不改删"的契约。
- **文件归属**：生成的 `ErrorCode.java` 属 build 产物，不手工维护、不入 git，每次构建重新生成。

## 二、Nacos 侧准备

新建一个配置（约定 dataId + group 即可）：

- **dataId**：`error-code.properties`（可命名空间区分环境）
- **group**：`ERROR_CODE`
- **格式**：`code=描述`，一行一个，注释用 `#`：

```properties
# 公共码（人人可见）
0=成功
1001=用户不存在
3002=token已过期

# --- 本业务私有码 ---
42001=订单已取消
42002=订单已删除
```

> 备注：数字码天然作唯一 key，公共/业务合并到一个文件也不会撞（码段隔离）。多语言可再加 `error-code_zh/en` 或单独 namespace，本插件先按单语言生成，多语言扩展点在模板内。

## 三、插件工程（完整可用代码）

一个最小 Maven 插件：`获取配置 → 解析 → 生成 enum 源文件`。三步都极简，生成一个枚举的模板几十行即可。

### 3.1 插件工程结构

```
errorcode-generator-plugin/          # 插件本身（一次写好，全公司复用）
├── pom.xml
└── src/main/java/com/company/errorcode/
    └── ErrorCodeGeneratorMojo.java
```

**插件 pom.xml**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.company</groupId>
  <artifactId>errorcode-generator-plugin</artifactId>
  <version>1.0.0</version>
  <packaging>maven-plugin</packaging>

  <dependencies>
    <!-- 插件注解：@Mojo @Parameter @Execute -->
    <dependency>
      <groupId>org.apache.maven.plugin-tools</groupId>
      <artifactId>maven-plugin-annotations</artifactId>
      <version>3.11.0</version>
      <scope>provided</scope>
    </dependency>
    <!-- 仅用于解析 openAPI 返回，可用任何 JSON 库 -->
    <dependency>
      <groupId>com.google.code.gson</groupId>
      <artifactId>gson</artifactId>
      <version>2.10.1</version>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <!-- 自动生成 plugin.xml 描述符 -->
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-plugin-plugin</artifactId>
        <version>3.11.0</version>
      </plugin>
    </plugins>
  </build>
</project>
```

### 3.2 插件实现（Mojo）

```java
package com.company.errorcode;

import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 编译期从 Nacos 拉错误码，生成 ErrorCode.java。
 * 用法见业务侧 pom（绑到 generate 阶段，先于 compile）。
 */
@Mojo(name = "generate-errorcode", defaultPhase = LifecyclePhase.GENERATE_SOURCES)
public class ErrorCodeGeneratorMojo extends AbstractMojo {

    /** Nacos 服务地址，如 http://nacos.yourcorp.com:8848 */
    @Parameter(property = "nacos.serverAddr", required = true)
    private String serverAddr;

    /** 命名空间 ID（可对应环境：dev/test/prod） */
    @Parameter(property = "nacos.namespace", defaultValue = "public")
    private String namespace;

    /** dataId，默认 error-code */
    @Parameter(property = "nacos.dataId", defaultValue = "error-code.properties")
    private String dataId;

    /** group */
    @Parameter(property = "nacos.group", defaultValue = "ERROR_CODE")
    private String group;

    /** 生成的包名 */
    @Parameter(property = "errorcode.packageName", defaultValue = "com.company.common.api")
    private String packageName;

    @Override
    public void execute() throws MojoExecutionException {
        try {
            // 1) 从 Nacos 拿配置原文（只读，无写权限）
            String raw = fetchFromNacos(serverAddr, namespace, dataId, group);
            // 2) 解析 code=描述
            Map<Integer, String> codes = parse(raw);
            // 3) 生成 ErrorCode.java 到 generated-sources
            Path outDir = Paths.get(projectBuildDir(), "generated-sources", "errorcode");
            Path outFile = outDir.resolve("ErrorCode.java");
            Files.createDirectories(outDir);
            Files.writeString(outFile, render(codes, packageName));
            getLog().info("生成 ErrorCode.java，共 " + codes.size() + " 个错误码 -> " + outFile);

            // 可选：添加到编译源根（部分构建工具场景需要）
            // project.addCompileSourceRoot(outDir.toString());
        } catch (Exception e) {
            throw new MojoExecutionException("拉取/生成错误码失败: " + e.getMessage(), e);
        }
    }

    /** Nacos 2.x openAPI 读取配置：GET /nacos/v1/cs/configs */
    private String fetchFromNacos(String addr, String namespace, String dataId, String group) throws Exception {
        String uid = java.net.URLEncoder.encode(namespace, "UTF-8");
        String did = java.net.URLEncoder.encode(dataId, "UTF-8");
        String gid = java.net.URLEncoder.encode(group, "UTF-8");
        String url = addr + "/nacos/v1/cs/configs?dataId=" + did
                + "&group=" + gid + "&tenant=" + uid;
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(5000);
        int code = conn.getResponseCode();
        if (code == 404) {
            throw new IllegalStateException("Nacos 配置不存在: dataId=" + dataId + " group=" + group);
        }
        BufferedReader br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), java.nio.charset.StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line).append('\n');
        return sb.toString();
    }

    /** 解析 code=描述，`#` 开头为注释 */
    private Map<Integer, String> parse(String raw) {
        Map<Integer, String> codes = new LinkedHashMap<>();
        for (String line : raw.split("\n")) {
            String t = line.trim();
            if (t.isEmpty() || t.startsWith("#") || !t.contains("=")) continue;
            int eq = t.indexOf('=');
            try {
                int code = Integer.parseInt(t.substring(0, eq).trim());
                codes.put(code, t.substring(eq + 1).trim());
            } catch (NumberFormatException ignore) {
                // 非数字 key（语义码场景）可跳过或另行处理
            }
        }
        return codes;
    }

    /** 用模板渲染出 enum 源码 */
    private String render(Map<Integer, String> codes, String pkg) {
        StringBuilder sb = new StringBuilder();
        sb.append("// 本文件由 errorcode-generator-plugin 生成，禁止手工修改\n")
          .append("package ").append(pkg).append(";\n\n")
          .append("public enum ErrorCode {\n\n")
          .append("    SUCCESS(0, \"success\"),\n");
        for (Map.Entry<Integer, String> e : codes.entrySet()) {
            if (e.getKey() == 0) continue; // SUCCESS 已在上面
            // 常数名：用户不存在 -> USER_NOT_FOUND（可自定义，这里做简单示意）
            String name = toConst(e.getValue());
            sb.append("    ").append(name).append('(').append(e.getKey())
              .append(", \"").append(escape(e.getValue())).append("\"),\n");
        }
        sb.setLength(sb.length() - 2); // 去掉末行逗号
        sb.append(";\n\n")
          .append("    private final int code;\n")
          .append("    private final String defaultMsg;\n\n")
          .append("    ErrorCode(int code, String defaultMsg) { this.code = code; this.defaultMsg = defaultMsg; }\n")
          .append("    public int code() { return code; }\n")
          .append("    public String defaultMsg() { return defaultMsg; }\n")
          .append("}\n");
        return sb.toString();
    }

    private String toConst(String msg) {
        String s = msg.replaceAll("[^\\u4e00-\\u9fa5A-Za-z0-9]", " ");
        StringBuilder sb = new StringBuilder();
        String[] parts = s.trim().split("\\s+");
        for (String p : parts) {
            if (p.matches("\\d+")) continue;   // 数字可跳过或按需处理
            if (p.matches("[\\u4e00-\\u9fa5]+")) {
                // 中文没法直接作常量名，取"关键动作"，这里用拼音占位示例
                sb.append("ERR");
            } else {
                sb.append(p.toUpperCase(Locale.ROOT).replace("-", "_"));
            }
        }
        return sb.length() == 0 ? "ERR_" + Math.abs(msg.hashCode()) : sb.toString();
    }

    private String escape(String v) {
        return v.replace("\"", "\\\"");
    }

    private String projectBuildDir() {
        // 简化：依赖项目 build 目录。完整插件应通过 MavenProject 注入
        return System.getProperty("project.build.directory", "target");
    }
}
```

> 说明：上面 `projectBuildDir()` 用了属性占位，实际生产插件应注入 `MavenProject` 拿 `getBuild().getDirectory()`；`toConst` 的中文→常量名需接团队拼音/语义规则（示意见意），可改为从配置中心带英文 key，更稳。

**安装插件**（公司公共基建，各业务依赖）：
```bash
cd errorcode-generator-plugin && mvn clean install
```

### 3.3 多语言 messages 拉取与存储（不止 enum）

`ErrorCode` enum 只是**兜底/defaultMsg**（编译期引用 + 默认文案）。真正按用户 Locale 展示的文案在**多语言 messages 资源文件**里——构建时也要把配置中心里**各语言的文案**一起拉下来、打包进 jar，运行时由 `MessageSource` 按 Locale 查。

**两组产物分工**：

| 产物                     | 形态             | 作用                                 |
| ---------------------- | -------------- | ---------------------------------- |
| `ErrorCode.java`       | 编译期 enum       | switch/throw 引用，`defaultMsg()` 做兜底 |
| `messages*.properties` | 运行时资源文件 ➔ 打jar | `MessageSource` 按 Locale 取多语言文案    |

**Nacos 多语言存储约定**（一个 dataId 一种语言，或同 dataId 用 `Locale` 后缀）：

```properties
# error-code-zh_CN.properties
1001=用户不存在
42002=订单已删除

# error-code_en.properties
1001=User not found
42002=Order deleted
```

**插件在 `3.2` 基础上，再加一个 goal 拉多语言**（复用 openAPI，只是把每个语言的文件写成 `messages_<locale>.properties`）：

```java
// 新 goal generate-messages
@Mojo(name = "generate-messages", defaultPhase = LifecyclePhase.GENERATE_RESOURCES)
public class MessageGeneratorMojo extends AbstractMojo {
    // 复用 fetchFromNacos，循环拉取 zh_CN / en / ja 等语言
    // 每个语言生成一份：target/generated-resources/errorcode/messages_<locale>.properties
    // 写入占位：本段示意，生产插件解析各 dataId 后写对应语言文件
}
```

**重点**：这些 `messages*.properties` 进 `generated-resources`（resources 源根），**build 时打包进 jar 的 `WEB-INF/classes` 或 classpath**，运行时 `spring.messages.basename=messages` 即可按 Locale 取出（机制见 [17-全局异常与国际化详解](17-全局异常与国际化详解.md) §4）。

> 与 enum 同理：生成的 messages 文件**不入 git**，每次构建重新生成，真源永远在配置中心。

## 四、业务侧用法

### 4.1 业务 pom 绑定（关键顺序：generate 先于 compile）

```xml
<build>
  <plugin>
    <groupId>com.company</groupId>
    <artifactId>errorcode-generator-plugin</artifactId>
    <version>1.0.0</version>
    <executions>
      <execution>
        <goals><goal>generate-errorcode</goal></goals>
      </execution>
    </executions>
    <configuration>
      <nacos.serverAddr>http://nacos.yourcorp.com:8848</nacos.serverAddr>
      <nacos.namespace>dev</nacos.namespace>
      <nacos.dataId>error-code.properties</nacos.dataId>
      <nacos.group>ERROR_CODE</nacos.group>
      <errorcode.packageName>com.example.order.api</errorcode.packageName>
      <!-- 环境变量注入，避免写死：${NACOS_ADDR} ${NAMESPACE} -->
    </configuration>
  </plugin>
</build>
```

### 4.2 本地开发顺序（核心防坑）

**先有类型、再写引用**：

1. 在配置中心新增/确认错误码 → `mvn compile`（或 IDE 触发）先生成 `ErrorCode.java`
2. 正常写代码：`throw new BusinessException(ErrorCode.ORDER_CANCEL);`
3. `.gitignore` 排除生成目录（不入库）：
   ```
   target/generated-sources/errorcode/
   ```

### 4.3 CI/CD

push 后构建，插件**再拉一次最新真源**重新生成再编译打包。本地那份只是开发副本，**真源永远以 CI 拉到的为准**。顺序守「先中心新增 → 再生成 → 再写引用」，否则会出现"本地有、线上报不存在的码"。

## 五、Apollo 对比（Nacos vs Apollo）

两者机制一样：**配置中心存 `code=描述` → 插件 openAPI 拉 → 生成 enum**。仅接入细节不同：

| 项 | Nacos | Apollo |
| --- | --- | --- |
| 读取配置接口 | `GET /nacos/v1/cs/configs?dataId&group&tenant` | `GET /configfiles/json/{appId}/{cluster}/{namespace}` |
| 名称 | dataId / group / tenant（namespace） | appId / cluster / namespace |
| 唯一 key | 数字码（码段隔离） | 同左 |
| 认证 | 可开鉴权(accessToken) | 需配置 portal 地址 + token/元数据 |
| 权限 | 需在 Nacos 控制台配 | Apollo 自带完备 RBAC/发布审批流程 |

> Apollo 优势：**运维/权限/发布审核更开箱即用**，适合"公共码改删要审批"的场景；Nacos 更轻、更常与 Spring Cloud Alibaba 配套。**切 Apollo 只需改插件里的 `fetchFromNacos` 为 `fetchFromApollo`（换 URL + 认证），解析/模板部分完全复用。**

---

> 上一篇：[17-全局异常与国际化详解](17-全局异常与国际化详解.md)（错误码治理升级路径 §3.2 的思路出处，本篇为落地扩展）
> 关联：[00-构建工具总览·Maven & Gradle选型对比](../../构建工具/00-构建工具总览·Maven & Gradle选型对比.md)（插件生命周期 / Mojo 概念）
