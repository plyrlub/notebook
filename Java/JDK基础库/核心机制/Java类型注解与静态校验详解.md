---
tags: [Java, 占位, 类型注解, TYPE_USE, 静态校验]
创建日期: 2026-08-08
状态: 📌 占位（待总结）
归属: 01-学习/Java/JDK基础库/核心机制
---

# Java类型注解与静态校验详解

> 📌 占位文档：由 [Java注解机制详解](Java注解机制详解.md) 引用，待总结时充实。

## 待总结内容

- 类型注解：TYPE_USE / TYPE_PARAMETER（JDK 8 引入）
- List<@NonNull String> 的注解语义：注解在类型使用处而非声明处
- Checker Framework：基于类型注解的编译期静态校验（空安全/污点分析）
- 运行时读取类型注解：AnnotatedType 反射 API（getAnnotatedReturnType 等）

## 触发场景

- [Java注解机制详解](Java注解机制详解.md) 中 @Target(TYPE_USE) 与类型注解的面试追问
