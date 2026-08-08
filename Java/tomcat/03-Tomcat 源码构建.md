---
tags: [Java, Tomcat, 源码, 构建, IDE, Bootstrap]
创建日期: 2026-08-08
状态: ✅ 已归档（01-学习/Java/框架/tomcat）
归属: 01-学习/Java/框架/tomcat
来源: wolai 笔记转存（https://www.wolai.com/plyr/wq9uk2MQqaTtbaJMX3H6YA）
---

# Tomcat 源码构建

> 本文是 Tomcat 学习笔记第 3 章（wolai 转存整理）。记录从源码下载到 IDE 运行 Tomcat 的全过程，便于后续源码级学习。
> 关联笔记：[[00-Tomcat 学习笔记（总览）]]、[[04-Tomcat 核心流程剖析]]、[[01-Tomcat 系统架构与原理剖析]]

## 📋 总纲

1. 下载源码
2. 源码导入 IDE 之前的准备工作
3. 导入源码到 IDE 并配置
4. 运行验证

---

## 1. 下载源码

**略**——从 Apache 官网（https://tomcat.apache.org/download-8.0.cgi 或 GitHub 仓库）下载对应版本源码包，解压到本地。

---

## 2. 源码导入 IDE 之前的准备工作

**① 源码主目录下新建 pom.xml**

Tomcat 源码本身是 Ant 构建，为了方便用 Maven 导入 IDE，需要在源码根目录创建 pom.xml：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>org.apache.tomcat</groupId>
    <artifactId>Tomcat8.5</artifactId>
    <name>Tomcat8.5</name>
    <version>8.5</version>
    <dependencies>
        <dependency>
            <groupId>org.apache.ant</groupId>
            <artifactId>ant</artifactId>
            <version>1.9.9</version>
        </dependency>
        <dependency>
            <groupId>org.apache.ant</groupId>
            <artifactId>ant-apache-log4j</artifactId>
            <version>1.9.9</version>
        </dependency>
    </dependencies>
</project>
```

**② 在主目录下创建 source 文件夹**

**③ 将 conf、webapps 目录移动到刚刚创建的 source 文件夹中**

> 目的：保持源码目录干净，把**运行所需的配置文件（conf）和默认应用（webapps）**集中到 source 下，模拟 Tomcat 安装目录结构。

```
tomcat-src/
├── pom.xml
├── source/
│   ├── conf/       ← 配置文件（server.xml 等）
│   └── webapps/    ← 默认 Web 应用
├── java/           ← 源码
└── ...
```

---

## 3. 导入源码到 IDE 并配置

**① 将源码工程导入 IDE**（IDEA：File → Open 选择源码目录，Maven 会自动识别 pom.xml）

**② 给 Tomcat 源码程序启动类 Bootstrap 配置 JVM 参数**

因为 Tomcat 启动的时候也需要加载配置文件等，需要设置 `catalina.home` 指向 source 目录：

```
# IDEA Run Configuration → VM options
-Dcatalina.home=/path/to/tomcat-src/source
-Dcatalina.base=/path/to/tomcat-src/source
```

![[assets/ch3_00.png]]

---

## 4. 运行验证

**③ 此时运行成功；浏览器访问会提示：**

![[assets/ch3_01.png]]

**④ 手动加载**

![[assets/ch3_02.png]]

此时访问 `http://localhost:8080/`，可以正常看见 Tomcat 默认页面，表示 **Tomcat 源代码环境正常构建完成**。

---

## 面试追问 Q&A

### Q1：为什么源码运行要设置 catalina.home？

答：Tomcat 启动时需要加载 conf/server.xml 等配置文件，`catalina.home`/`catalina.base` 告诉它去哪找这些文件。源码目录本身没有 conf/webapps，所以要指定到 source 目录。

### Q2：为什么用 Maven 而源码用 Ant？

答：Tomcat 官方用 Ant 构建，但 IDE 对 Maven 支持更友好（依赖管理自动下载）。新建 pom.xml 只是为了**方便 IDE 导入和依赖解析**，编译运行核心逻辑不变。

### Q3：源码运行和成品 Tomcat 有什么区别？

答：源码运行用 IDE 里的 Bootstrap main 方法直接启动，方便断点调试；成品 Tomcat 通过 startup.sh 启动。两者加载的配置、类路径本质相同，源码运行更适合学习源码流程（见 [[04-Tomcat 核心流程剖析]]）。

---

*来源：wolai 笔记转存（Apache Tomcat 学习笔记第 3 章），2026-08-08 整理*
