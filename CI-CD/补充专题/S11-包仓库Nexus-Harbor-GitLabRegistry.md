---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S11. 包仓库（Nexus / Harbor / GitLab Container Registry）

> **专题编号：S11**。被引用章节：第 02、06 章。

---

## 一、介绍：为什么需要专门的包仓库

**问题**：CI/CD 的 Publish 阶段 = **把制品推到仓库**，Deploy 阶段 = **从仓库拉对应版本的制品**。没有包仓库，CI 跑完产物没地方存。

**包仓库的三大职能**：
1. **存储**：镜像 / jar / wheel / npm 包等制品
2. **代理**：缓存 Maven Central / PyPI / npm 等公共源，加速拉取
3. **治理**：权限控制、保留策略、漏洞扫描、不可变标签

---

## 二、三大工具对比

**表 11-1：Nexus / Harbor / GitLab Container Registry 对比**

| 维度 | Sonatype Nexus 3 | Harbor | GitLab Container Registry |
| ---- | ---------------- | ------ | ------------------------- |
| **核心定位** | 通用制品仓（全能型） | 镜像仓为主（专精型） | GitLab 内置（一体化） |
| **支持类型** | 镜像 / Maven / PyPI / npm / Go / Helm / APT / YUM / NuGet / Conan | 镜像 / Helm Chart / 部分通用制品 | 镜像 / Maven / PyPI / npm / Helm / Conan / Generic |
| **镜像仓能力** | ✅ 基础（push/pull/认证） | ✅ 顶级（CVE 扫描/Cosign 签名/复制/不可变标签/配额） | ✅ 较好（CVE 扫描/不可变标签/与 GitLab 集成） |
| **包仓能力** | ✅ 最全（25+ 格式） | ❌ 有限 | ✅ 主流格式都支持 |
| **代理公共源** | ✅ 强项（Maven/PyPI/npm 都能代理） | ❌ 不支持 | ✅ 支持 |
| **CVE 扫描** | ✅ Nexus IQ（商业版） | ✅ 内置 Trivy / Clair | ✅ 内置 Trivy |
| **镜像签名** | ❌ 不强 | ✅ Cosign / Notary v2 原生支持 | ✅ Cosign 支持 |
| **多地域复制** | ✅ 商业版 | ✅ 原生支持（Pull-based 复制） | ✅ GitLab Geo |
| **权限模型** | 自带用户系统 | 自带用户系统 | 复用 GitLab 用户/组 |
| **2026 状态** | 通用型企业级首选 | 私有镜像仓事实标准 | GitLab 用户零成本 |
| **开源/商业** | 开源 + 商业版 | 开源（CNCF 毕业） | 开源（GitLab CE 含） + 商业版 |

### 2.1 选型决策树

```
是否已经在用 GitLab CI/CD？
├── 是 → GitLab Container Registry（零成本，一体化）
│        └── 但镜像高级安全功能（Cosign/复制）需要补充 Harbor
└── 否 → 是否镜像为主、不需要复杂包仓？
    ├── 是 → Harbor（镜像能力最强）
    └── 否 → 是否需要代理公共源（Maven/PyPI/npm 缓存）？
        ├── 是 → Nexus 3（代理能力强）
        └── 否 → 看预算
            ├── 预算充足 → JFrog Artifactory（最全最强）
            └── 预算有限 → Nexus 3 开源版
```

### 2.2 三种常见组合方案

| 方案 | 镜像仓 | 包仓 | 通用制品 | 适用场景 |
| ---- | ------ | ---- | -------- | -------- |
| **全 Nexus** | Nexus | Nexus（代理+宿主） | Nexus | 中小团队一站式，预算有限 |
| **Harbor + Nexus** | Harbor | Nexus | Nexus | 大团队，镜像安全要求高 |
| **GitLab + Harbor** | GitLab Registry（dev/test）+ Harbor（prod） | GitLab Package Registry | GitLab Generic | 全 GitLab 栈 + prod 镜像强化 |

---

## 三、Nexus 3 基本使用

### 3.1 部署

**Docker Compose 部署**：
```yaml
# docker-compose.yml
version: '3'
services:
  nexus:
    image: sonatype/nexus3:3.70
    ports:
      - "8081:8081"           # Web UI
      - "8082:8082"           # Docker registry（hosted）
      - "8083:8083"           # Docker registry（proxy）
      - "8084:8084"           # Docker registry（group）
    volumes:
      - nexus-data:/nexus-data
    environment:
      - INSTALL4J_ADD_VM_PARAMS=-Xms2703m -Xmx2703m -XX:MaxDirectMemorySize=2703m -Djava.util.prefs.userRoot=/nexus-data/javaprefs
volumes:
  nexus-data:
```

```bash
docker compose up -d
# 等 1~2 分钟，访问 http://localhost:8081
# 初始密码在容器里：
docker exec nexus cat /nexus-data/admin.password
```

### 3.2 创建仓库

Nexus 的仓库分三种类型：
- **Hosted（宿主）**：存自己的制品
- **Proxy（代理）**：代理外部公共源
- **Group（组）**：把多个 hosted + proxy 组合，对外提供统一地址

**典型仓库规划**：

| 仓库 | 类型 | 格式 | 用途 |
| ---- | ---- | ---- | ---- |
| `maven-hosted` | Hosted | Maven | 自家 jar 包 |
| `maven-proxy` | Proxy | Maven | 代理 Maven Central |
| `maven-group` | Group | Maven | 给应用统一拉依赖 |
| `pypi-hosted` | Hosted | PyPI | 自家 wheel 包 |
| `pypi-proxy` | Proxy | PyPI | 代理 pypi.org |
| `pypi-group` | Group | PyPI | 给应用统一拉依赖 |
| `npm-hosted` | Hosted | npm | 自家前端包 |
| `npm-proxy` | Proxy | npm | 代理 registry.npmjs.org |
| `docker-hosted` | Hosted | Docker | 自家镜像（HTTP 端口 8082） |
| `docker-proxy` | Proxy | Docker | 代理 Docker Hub |
| `docker-group` | Group | Docker | 给客户端统一拉镜像 |

**创建 Maven Proxy 仓库**（UI 操作）：
1. 设置 → Repository → Repositories → Create repository
2. 选 `maven2 (proxy)`
3. Name: `maven-proxy`
4. Remote storage: `https://repo1.maven.org/maven2/`
5. 创建

### 3.3 CI 集成

**Maven 项目推送 jar 到 Nexus**（`pom.xml`）：
```xml
<distributionManagement>
  <repository>
    <id>nexus-releases</id>
    <url>http://nexus.example.com/repository/maven-hosted/</url>
  </repository>
  <snapshotRepository>
    <id>nexus-snapshots</id>
    <url>http://nexus.example.com/repository/maven-hosted/</url>
  </snapshotRepository>
</distributionManagement>
```

**`~/.m2/settings.xml`（含认证）**：
```xml
<settings>
  <servers>
    <server>
      <id>nexus-releases</id>
      <username>${env.NEXUS_USER}</username>
      <password>${env.NEXUS_PASS}</password>
    </server>
  </servers>
  <mirrors>
    <mirror>
      <id>nexus-group</id>
      <mirrorOf>*</mirrorOf>
      <url>http://nexus.example.com/repository/maven-group/</url>
    </mirror>
  </mirrors>
</settings>
```

**CI 中推送**：
```bash
mvn deploy -DskipTests
```

**Python 项目推 wheel 到 Nexus PyPI**：
```bash
# 配置 ~/.pypirc
[distutils]
index-servers = nexus

[nexus]
repository = http://nexus.example.com/repository/pypi-hosted/
username = $NEXUS_USER
password = $NEXUS_PASS

# 推送
python -m build
twine upload -r nexus dist/*
```

**拉取时用 Nexus 代理**：
```bash
pip install -i http://nexus.example.com/repository/pypi-group/simple --trusted-host nexus.example.com -r requirements.txt
```

### 3.4 保留策略

Nexus 没有内置"按时间清理"功能，需要用 **Cleanup Policies** + **Scheduled Tasks**：

1. 设置 → Repository → Cleanup Policies
2. 创建策略：保留最近 100 个版本 + 30 天内的
3. 应用到 hosted 仓库
4. 设置 → System → Scheduled Tasks → 创建"Cleanup service"定时任务

---

## 四、Harbor 基本使用

### 4.1 部署

**Docker Compose 部署**（官方推荐）：
```bash
# 下载
curl -sfL https://github.com/goharbor/harbor/releases/download/v2.10.0/harbor-online-installer-v2.10.0.tgz | tar xz
cd harbor

# 复制配置
cp harbor.yml.tmpl harbor.yml

# 编辑 harbor.yml
# hostname: harbor.example.com
# http:
#   port: 80
# harbor_admin_password: Strong-Password

# 安装
./install.sh --with-trivy --with-notary
```

### 4.2 核心功能

**Harbor 比 Nexus 在镜像场景强的功能**：

| 功能 | 说明 | 配置位置 |
| ---- | ---- | -------- |
| **CVE 扫描（Trivy 内置）** | 自动扫每个 push 的镜像 | 项目 → 配置 → 漏洞扫描 |
| **漏洞阻断策略** | 高危漏洞不让 pull | 项目 → 配置 → 部署安全 |
| **不可变标签（Immutable Tag）** | 防止覆盖已推送的 tag | 项目 → 配置 → Immutable Tag |
| **Cosign 签名验证** | 部署前验证签名 | 项目 → 配置 → 签名验证 |
| **配额（Quota）** | 限制项目存储大小 | 项目 → 配置 → 配额 |
| **复制（Replication）** | 跨实例同步镜像 | 复制 → 复制规则 |

### 4.3 配置不可变标签（防覆盖）

1. 项目 → 选择项目 → 配置 → Immutable Tag
2. 添加规则：
   - 匹配模式：`v*`（所有 v 开头的 tag）
   - 操作：禁止覆盖 + 禁止删除

效果：`myapp:v1.2.0` 推送后，再次推同一个 tag 会被拒绝。

### 4.4 配置漏洞阻断

1. 项目 → 配置 → 部署安全
2. 启用"Prevent vulnerable images from running"
3. 阈值：Critical（Critical 漏洞不让部署）
4. 例外：勾选"Allow overwrites for CVEs without fixes"（无修复的允许部署）

### 4.5 跨实例复制（多地域部署）

**场景**：CI 推 dev 实例，prod 实例只允许从 dev 复制来。

1. 目标实例（prod）→ 复制 → 复制规则 → 新建规则
2. 模式：Pull-based（prod 主动拉 dev）
3. 源：dev 实例的 `prod-candidates/*` 项目
4. 触发：实时（dev push 立刻同步）
5. 过滤：仅复制通过签名验证的镜像

### 4.6 CI 集成

```yaml
# GitLab CI 示例：推镜像到 Harbor
build-push:
  stage: publish
  image: docker:24
  services: [docker:24-dind]
  variables:
    HARBOR_URL: harbor.example.com
    IMAGE: $HARBOR_URL/myorg/myapp:$CI_COMMIT_TAG
  before_script:
    - echo $HARBOR_PASS | docker login -u $HARBOR_USER --password-stdin $HARBOR_URL
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
  rules:
    - if: $CI_COMMIT_TAG
```

---

## 五、GitLab Container Registry 基本使用

### 5.1 启用

GitLab 自带，启用方式：
- **GitLab.com**：默认启用
- **自建 GitLab**：在 `gitlab.rb` 配置 `registry_external_url 'https://registry.example.com'`

### 5.2 CI 集成（最简单的方案）

GitLab CI 自带 `CI_REGISTRY` / `CI_REGISTRY_USER` / `CI_REGISTRY_PASSWORD` 变量，**无需手动配置认证**：

```yaml
# .gitlab-ci.yml
build-push:
  stage: publish
  image: docker:24
  services: [docker:24-dind]
  variables:
    IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  before_script:
    # 用 GitLab 自带变量登录，不需要手动配 Token
    - echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
```

### 5.3 推其他类型包到 GitLab Package Registry

**Maven 包**：
```xml
<!-- pom.xml -->
<distributionManagement>
  <repository>
    <id>gitlab-maven</id>
    <url>https://gitlab.example.com/api/v4/projects/${env.CI_PROJECT_ID}/packages/maven</url>
  </repository>
</distributionManagement>
```

```xml
<!-- ~/.m2/settings.xml -->
<settings>
  <servers>
    <server>
      <id>gitlab-maven</id>
      <username>gitlab-ci-token</username>
      <password>${env.CI_JOB_TOKEN}</password>   <!-- GitLab CI 自带 -->
    </server>
  </servers>
</settings>
```

**Python 包**：
```bash
# 不需要 .pypirc，用 CI_JOB_TOKEN
pip install twine
python -m build
twine upload \
  --repository-url "https://gitlab.example.com/api/v4/projects/${CI_PROJECT_ID}/packages/pypi" \
  --username "gitlab-ci-token" \
  --password "${CI_JOB_TOKEN}" \
  dist/*
```

### 5.4 通用制品（Generic Registry）

存任意文件：SBOM、SQL 脚本、前端 dist：

```bash
# 上传
curl --header "JOB-TOKEN: $CI_JOB_TOKEN" \
  --upload-file ./sbom.json \
  "https://gitlab.example.com/api/v4/projects/${CI_PROJECT_ID}/packages/generic/myapp/${CI_COMMIT_TAG}/sbom.json"

# 下载
curl --header "JOB-TOKEN: $CI_JOB_TOKEN" \
  "https://gitlab.example.com/api/v4/projects/${CI_PROJECT_ID}/packages/generic/myapp/${CI_COMMIT_TAG}/sbom.json"
```

### 5.5 清理策略

GitLab 自带 Package Cleanup Policy：
- 项目 → 设置 → Packages & Registries → Cleanup Policies
- 配置：保留 N 个最新版本，删除更老的
- 仅对 Generic / Maven / npm / PyPI 等有效，**镜像仓需要单独配置**

镜像清理：
- 项目 → 设置 → Packages & Registries → Container Registry cleanup rules
- 规则：删除 N 天前的无 tag 镜像、删除未使用的镜像层

---

## 六、三大工具的协同方案（典型企业落地）

### 6.1 协同拓扑

```
                ┌─────────────────────────────────┐
                │       CI/CD 流水线               │
                └────────────┬────────────────────┘
                             │ 推送
                             ▼
       ┌─────────────────────────────────────────┐
       │  Nexus（包仓 + 通用制品）                │
       │  - Maven / PyPI / npm 包                 │
       │  - 代理 Maven Central / PyPI             │
       │  - Generic 制品（SBOM、SQL 脚本）        │
       └─────────────────────────────────────────┘

       ┌─────────────────────────────────────────┐
       │  Harbor（镜像仓，prod 级别安全）          │
       │  - 所有 Docker 镜像                      │
       │  - Trivy 扫描 + Cosign 签名              │
       │  - 不可变标签                            │
       │  - 复制到 prod 实例                      │
       └─────────────────────────────────────────┘

       ┌─────────────────────────────────────────┐
       │  GitLab Container Registry（dev/test）   │
       │  - 临时镜像，CI 测试用                   │
       │  - 与 GitLab CI 零配置集成               │
       └─────────────────────────────────────────┘
```

### 6.2 协同流程

```
1. CI 构建 jar / wheel → 推 Nexus
2. CI 构建镜像 → 推 GitLab Registry（快速验证用）
3. CI 测试通过 → 镜像转推 Harbor（带签名 + 扫描）
4. Harbor 通过验证 → 复制到 prod Harbor
5. 部署系统从 prod Harbor 拉镜像
```

---

## 七、与主章节的关联

- 第 02 章（环境与前置技能）：制品仓库概念引入
- 第 06 章（容器化与制品管理）：Harbor 详解 + 不可变制品原则
