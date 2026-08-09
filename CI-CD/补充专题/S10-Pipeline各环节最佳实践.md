---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S10. Pipeline 各环节最佳实践合集

> **专题编号：S10**。被引用章节：第 04、05、06 章。

---

## 一、介绍：从概念到操作的桥梁

**要解决的核心问题**：原路径有各环节的概念，但缺少"每个环节具体怎么做才是业界最佳"的操作性指导。本专题把每个环节的"做法 + 原因 + 反模式"写清。

---

## 二、代码拉取（Checkout / Clone）

**表 10-1：代码拉取最佳实践**

| 要点 | 做法 | 为什么 |
| ---- | ---- | ------ |
| fetch 深度 | 默认 `--depth=1`（浅克隆），需要 Tag 历史时再加深 | 90% 的 pipeline 不需要全历史，浅克隆省时间和网络 |
| Git LFS | 需要时显式拉取 `lfs: true`，否则跳过 | LFS 对象拉取慢，不需要就关掉 |
| Submodule | 默认 `submodules: false`，需要时递归 `recursive: true` | 嵌套 submodule 深 clone 很慢 |
| 代码所有权 | 用 Deploy Key（只读）或 GitHub App 身份，不用个人 Token | 个人 Token 绑定到人，离职即失效 |
| Checkout 后校验 | 关键 pipeline 校验 commit GPG 签名 / 提交者身份 | 防代码篡改 |
| Runner 工作目录清理 | 每个 Job 执行前 `git clean -ffdx` 或用临时 Runner | 防上一个 Job 的残留文件污染 |

**GitHub Actions 配置**：
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 1                  # 浅克隆
    fetch-tags: false               # 不拉 Tag，加速
    lfs: false                      # 不用 LFS 就关
    submodules: false               # 不用 submodule 就关
    persist-credentials: false      # 不留 Token 在 .git/config
```

**GitLab CI 配置**：
```yaml
variables:
  GIT_DEPTH: 1
  GIT_STRATEGY: fetch               # 增量 fetch 比 clone 快
  GIT_SUBMODULE_STRATEGY: none
  GIT_LFS_SKIP_SMUDGE: 1            # 不自动拉 LFS
```

---

## 三、缓存（Cache）

**表 10-2：缓存对象 × 键策略 × 失效策略对照**

| 缓存对象 | 键（Key）策略 | 失效策略 | 注意事项 |
| -------- | ------------- | -------- | -------- |
| pip/poetry 依赖 | `python-${os}-${hash(lockfile)}` | lockfile 变了自动失效 | 别缓存 `.venv` 整个目录，体积太大 |
| Maven/Gradle 依赖 | `maven-${os}-${hash(pom.xml)}` / `gradle-${os}-${hash(build.gradle)}` | 同上 | 注意不要缓存本地安装的临时制品 |
| npm/yarn/pnpm 依赖 | `node-${os}-${hash(pnpm-lock.yaml)}` | 同上 | pnpm 缓存命中率最高 |
| Docker layer cache | `--cache-from` 指向上一次成功构建的镜像 | 镜像被清理就失效 | BuildKit + 缓存仓（Registry/Action Cache） |
| 编译中间产物（.o / target/） | `build-${os}-${compilerVer}-${hash(src)}` | 源码 hash 变了就失效 | 体积太大反而不如重新编译快 |

**缓存总原则**：小而准（只缓存会复用的东西）、可观测（记录命中率）、有上限（单个缓存不要超过 500MB，大了走制品仓）。

---

## 四、制品保存（Artifact / Package）

### 4.1 制品命名规范

格式：`${appName}-${version}-${buildNumber}-${gitSHA短号}`
- 版本号来源：Git Tag（正式发版）或 `main-YYYYMMDD-N`（每日构建）
- 绝不使用 `latest` / `lastest-snapshot` 这类可变标签做追溯

### 4.2 制品与 Git Commit 的映射

```dockerfile
# Dockerfile 中嵌入元数据
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.source="https://github.com/myorg/myrepo"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.created="${BUILD_TIME}"
```

```bash
# Maven 制品元数据
mvn deploy -Drevision=${VERSION} -Dsha1=${GIT_SHA} -Dchangelist=${BUILD_NUMBER}
```

### 4.3 保留策略（Retention）

**表 10-3：制品保留策略**

| 制品类型 | 保留时长 | 说明 |
| -------- | -------- | ---- |
| PR 构建产物 | 7~14 天 | 量最大，必须定期清 |
| main/主干 nightly | 30~90 天 | 中等 |
| 正式 Tag 发版制品 | 永久保留 | 按合规要求 N 年 |
| 制品仓存储配额 | 触发告警 80% | 防磁盘撑爆 |

### 4.4 跨 Stage / 跨 Job 传递制品

**同一 Pipeline 内**：用工具原生 Artifact 机制
```yaml
# GitHub Actions
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: target/*.jar
    retention-days: 7

# 下游 Job
- uses: actions/download-artifact@v4
  with:
    name: build-output
```

```yaml
# GitLab CI
build:
  artifacts:
    paths:
      - target/*.jar
    expire_in: 1 week

deploy:
  needs: [build]
  script: deploy target/*.jar
```

**跨 Pipeline / 跨项目**：走制品仓（Nexus / Harbor / Artifactory），给下游明确的版本号依赖。

---

## 五、镜像推送（Image Push）

### 5.1 标签策略（2026 最佳实践）

必推三个标签：
- `${版本号}`（精确，如 `v1.2.0`）
- `${gitSHA短号}`（可追溯，如 `sha-abc1234`）
- `${major}.${minor}`（浮动引用，如 `v1.2`，自动指向该 minor 的最新 patch）

**慎用 `latest`**：只在 dev 环境图方便时用，prod 绝不引用 `latest`。

**预发版用预发布标签**：`v1.2.0-rc.3`、`v1.2.0-beta.1`。

### 5.2 推送前三道闸

```
构建完成
    ↓
Trivy 扫描（CRITICAL/HIGH 发现 → 终止）
    ↓
Cosign 签名（或 Notation，OCI 1.1 后二选一）
    ↓
SBOM 产物（CycloneDX）与镜像一同推送
    ↓
推送
```

### 5.3 多架构推送

2026 标配：`linux/amd64 + linux/arm64` 双架构（ARM 服务器/云实例越来越多）。

```bash
# 方式 1：buildx 一次性构建多架构
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:v1.2.0 \
  --push .

# 方式 2：分别 build → 分别 push → manifest create（跨 Runner 并行时更快）
docker build --platform linux/amd64 -t myapp:v1.2.0-amd64 .
docker build --platform linux/arm64 -t myapp:v1.2.0-arm64 .
docker push myapp:v1.2.0-amd64
docker push myapp:v1.2.0-arm64
docker manifest create myapp:v1.2.0 \
  myapp:v1.2.0-amd64 \
  myapp:v1.2.0-arm64
docker manifest push myapp:v1.2.0
```

### 5.4 重推保护

制品仓开启"不可变标签"（immutable tags）：同一个 tag 不允许覆盖，只能推新版本号。

```
# Harbor 配置：项目设置 → 部署 → Immutable Tag Rule
# Pattern：v* → 不可变
# 防止有人手动覆盖 prod 镜像、导致"线上跑的是什么说不清"
```

---

## 六、测试分层在 Pipeline 中的执行策略

**表 10-4：5 层测试在 Pipeline 中的精确位置**

| 测试层级 | 放哪个 Stage | 触发条件 | 并行策略 | 失败后 | 报告上传 |
| -------- | ------------ | -------- | -------- | ------ | -------- |
| 单元测试（Unit） | **Test Stage 第一批** | 每个 PR + 每次 push | **全并行**（按包/模块切 Job，矩阵并发） | **立即阻断**（单元不过不往下走） | 覆盖率报告 → SonarQube / 覆盖率门禁 |
| 集成测试（Integration） | **Test Stage 第二批**（单元全过后） | 每个 PR；对 main 必跑 | 按服务/模块切并行，有顺序依赖的串行 | 阻断合并（但允许 `/ok-to-test` 先跑小范围验证） | JUnit XML → PR 评论展示失败用例 |
| 契约测试（Contract） | Test Stage 与集成测试并行 | 消费者/生产者 PR | 消费者侧并行，生产者侧按契约文件切 | 阻断合并 | Pact/CDC 报告发契约中心 |
| E2E / UI | **Post-Deploy Stage**（部署到类生产环境后） | main push + 发版 Tag；PR 用 `/e2e` 手动触发 | 按场景切并行，有会话状态的串行 | 发告警 + 阻断发版窗口（不阻断当前 PR 合并） | Selenium/Cypress 视频/截图存档 |
| 性能/压测 | **独立 Schedule Pipeline**（非每次 PR 跑） | 每日 main nightly / 每周 / 发版前 | 独立压测集群，不在共享 Runner 上跑 | 不阻断合并，压测报告对比基线发告警 | 压测报告入库 + 趋势图 |

### 6.1 测试总原则

- **70-20-10 法则**：70% 单元、20% 集成、10% E2E（金字塔）
- **Flaky Test 处理**：连续 2 次相同失败判定为真失败；flaky 自动重跑最多 2 次；累计 flaky 率 >5% 的用例必须修或隔离
- **失败快停**（Fail Fast）：单元测试发现失败立即取消后续 Stage，节省 CI 时间和成本

### 6.2 GitHub Actions 失败快停配置

```yaml
jobs:
  unit-test:
    strategy:
      fail-fast: true         # 矩阵中任一失败立即取消其他
      matrix:
        module: [auth, payment, search]
    steps:
      - run: pytest tests/${{ matrix.module }}/

  integration:
    needs: unit-test          # 必须等单测全过
    if: ${{ success() }}
    runs-on: ubuntu-latest
    steps: ...
```

---

## 七、与主章节的关联

- 第 04 章（工具配置）：Checkout/缓存/制品/镜像推送的各工具具体语法
- 第 05 章（构建测试）：测试分层执行策略 + Sonar 覆盖率门控
- 第 06 章（容器制品）：镜像三道闸 + 多架构 + 不可变标签
