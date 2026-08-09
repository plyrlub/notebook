---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S12. CI/CD 开源设施部署指南

> **专题编号：S12**。被引用章节：第 02、04、06、08、09 章。
> **定位**：S1~S11 大多讲"是什么 + 怎么用"，本专题补齐"**怎么部署安装**"。
> **范围**：15 套免费开源 CI/CD 设施的 docker-compose / 二进制部署，含完整可运行 yaml、GitLab CI 集成、验证排障、生产建议。
> **前置假设**：Docker / Docker Compose / Kubernetes 自身的安装在 02 / 07 章已覆盖，本专题不再重复。
> **版本约定**：所有镜像版本均为 2024-2026 稳定版（已通过官方文档与 GitHub Releases 确认，截至 2026-08 主流可用）。
> **语言约束**：所有脚本示例仅使用 Bash / Python / YAML，禁止 TypeScript。

---

## 总览：15 套设施清单与端口规划

为避免附录 A 一键启动时端口冲突，本专题提前做端口规划。生产环境建议通过反向代理（Nginx/Traefik）暴露 80/443，下表为容器直接暴露端口。

| 编号 | 设施 | 镜像/版本 | 主端口 | 用途 |
| ---- | ---- | --------- | ------ | ---- |
| D1 | GitLab CE + Runner | `gitlab/gitlab-ce:17.6.1-ce.0` | 8080 / 8022 / 8023 | 代码仓 + CI |
| D2 | Harbor | `goharbor/harbor-*:v2.12.2` | 8081 / 8443 | 镜像私仓 + 漏扫 |
| D3 | SonarQube | `sonarqube:25.1.0.102705-community` | 9000 | 静态分析 + 质量门 |
| D4 | Trivy | `aquasec/trivy:0.58.2` | 8082（server） | 镜像/FS 漏扫 |
| D5 | Dependency-Track | `dependencytrack/apiserver:4.12.5` | 8081（与 Harbor 复用需错开）→ 改 8083 | SBOM 监控 |
| D6 | Renovate | `renovate/renovate:39.20.5` | 无常驻端口 | 依赖更新 |
| D7 | OWASP ZAP | `softwaresecurityproject/zap2docker-stable:2.15.0` | 8090（代理） | DAST |
| D8 | Bandit / Semgrep | `pybandit/bandit:1.7.10` / `returntocorp/semgrep:1.96` | 无 | Python SAST |
| D9 | Gitleaks | `zricethezav/gitleaks:v8.21.2` | 无 | 密钥扫描 |
| D10 | Prometheus + Grafana + Loki + Promtail | `prom/prometheus:v3.1.0` 等 | 9090 / 3000 / 3100 / 9080 | 监控 + 日志 |
| D11 | Pushgateway | `prom/pushgateway:v1.10.0` | 9091 | 短任务指标 |
| D12 | OTel Collector + Tempo | `otel/opentelemetry-collector-contrib:0.116.1` / `grafana/tempo:2.6.0` | 4317 / 3200 | 链路追踪 |
| D13 | Alertmanager + Unleash | `prom/alertmanager:v0.27.0` / `unleash/unleash:5.16.0` | 9093 / 4242 | 告警 + Feature Flag |
| D14 | Cosign + Rekor | 二进制 `cosign v2.4.1` / `rekor-server v1.3.7` | 3000（Rekor） | 签名 + 透明日志 |
| D15 | Vault + External Secrets | `hashicorp/vault:1.18.3` | 8200 | Secret 管理 |

> **端口冲突提示**：D5 Dependency-Track 默认 8081 与 Harbor Portal 冲突，本专题统一改 D5 为 8083。

---

## D1. GitLab CE + Runner

### D1.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB SSD | 50 GB SSD |
| 说明 | 低于 4GB 无法启动；SSD 显著影响 git clone 性能 |

### D1.2 docker-compose.yml

```yaml
# /opt/cicd/gitlab/docker-compose.yml
version: "3.9"

services:
  gitlab:
    image: gitlab/gitlab-ce:17.6.1-ce.0
    container_name: gitlab
    restart: unless-stopped
    hostname: gitlab.example.com
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://gitlab.example.com:8080'
        gitlab_rails['initial_root_password'] = 'ChangeMe!2026'
        gitlab_rails['gitlab_shell_ssh_port'] = 8022
        # 关闭 Gravatar 外联（内网环境）
        gravatar['enabled'] = false
        # 备份保留 7 天
        gitlab_rails['backup_keep_time'] = 604800
        # 与 SonarQube / Harbor 联动 webhook 不在此配置，运行时配置
    ports:
      - "8080:8080"   # Web
      - "8022:22"     # SSH（容器内 22 → 主机 8022）
      - "8023:8050"   # Pages / Registry 内部代理
    volumes:
      - gitlab-config:/etc/gitlab
      - gitlab-logs:/var/log/gitlab
      - gitlab-data:/var/opt/gitlab
    shm_size: "256m"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/-/health"]
      interval: 60s
      timeout: 10s
      retries: 5
      start_period: 300s
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 6G

  gitlab-runner:
    image: gitlab/gitlab-runner:ubuntu-v17.6.1
    container_name: gitlab-runner
    restart: unless-stopped
    depends_on:
      gitlab:
        condition: service_healthy
    volumes:
      - runner-config:/etc/gitlab-runner
      - /var/run/docker.sock:/var/run/docker.sock   # 让 Runner 能起 docker 建镜像
      - runner-cache:/cache
    environment:
      - CI_SERVER_URL=http://gitlab:8080/
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G

volumes:
  gitlab-config:
  gitlab-logs:
  gitlab-data:
  runner-config:
  runner-cache:
```

### D1.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `external_url` | ✅ | 必须为外部可访问地址，影响 clone URL / webhook |
| `gitlab_rails['initial_root_password']` | ✅ | 首次启动 root 密码，至少 12 位；改完建议删除该行重启 |
| `gitlab_shell_ssh_port` | ✅ | 影响 `git@clone` 时的 SSH 端口 |
| `shm_size` | ⚠️ | 默认 64MB 不够，Sidekiq / Prometheus Exporter 会 OOM |
| `volumes /var/run/docker.sock` | ⚠️ | Runner Docker executor 才能起兄弟容器，安全敏感，生产用 dind 隔离 |

### D1.4 与 CI/CD 集成

注册 Runner（容器内执行）：
```bash
docker exec -it gitlab-runner gitlab-runner register \
  --url http://gitlab:8080/ \
  --registration-token glrt-xxxxxxxxxx \
  --executor docker \
  --docker-image "alpine:3.20" \
  --docker-privileged \
  --description "shared-docker-runner" \
  --tag-list "docker,linux" \
  --run-untagged=true
```

GitLab CI 中调用其它设施示例（`.gitlab-ci.yml`）：
```yaml
stages:
  - scan

sonarqube:
  stage: scan
  image: sonarsource/sonar-scanner-cli:5.0.1
  variables:
    SONAR_HOST_URL: "http://sonarqube:9000"
    SONAR_TOKEN: "$SONAR_TOKEN"      # 在 GitLab CI/CD Variables 中配置，masked
  script:
    - sonar-scanner -Dsonar.projectKey=$CI_PROJECT_NAME
```

凭据管理：所有第三方 Token（SonarQube / Harbor / Renovate 等）放 GitLab 项目的 **Settings → CI/CD → Variables**，勾选 `Masked` + `Protected`，运行时注入为环境变量。

### D1.5 验证与排障

```bash
# 验证 GitLab 健康
curl -s http://localhost:8080/-/health | jq .
docker exec gitlab gitlab-ctl status
# 验证 Runner 在线
docker exec gitlab-runner gitlab-runner verify
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| 502 持续 | 启动 5 分钟仍 502 | 查 `gitlab-ctl status`，多为内存不足，调高 `shm_size` 与 memory limit |
| SSH clone 失败 | `port 22 connection refused` | `gitlab_shell_ssh_port` 与 ports 映射不一致；防火墙未放 8022 |
| Runner `docker: not found` | job 报 docker 命令不存在 | Runner 未挂 `docker.sock` 或未加 `--docker-privileged` |
| `initial_root_password` 无效 | 登录失败 | 该变量仅首次启动生效，已初始化后需 `gitlab-rake "gitlab:password:reset"` |
| 备份失败 | backup 文件为空 | 磁盘满，检查 `df -h` |

### D1.6 生产建议

- **备份**：`gitlab-backup create` + `gitlab-ctl backup-etc`（配置），cron 每日 02:00，配合附录 C。
- **升级**：`gitlab/gitlab-ce:17.6.1 → 17.7.x` 需先看 `UPDATE.md`，**禁止跨大版本跳跃**（17.x → 18.x 要走 17.11 中转）。升级前必须备份。
- **告警打通**：GitLab 自带 Prometheus exporter，被 D10 Prometheus scrape（`- targets: ['gitlab:9168']`）。
- **HA**：CE 不支持原生 HA，需 PostgreSQL + Redis + Gitaly Cluster，超过 500 人团队建议上 EE。

---

## D2. Harbor

### D2.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 40 GB（镜像） | 200 GB SSD |

### D2.2 docker-compose.yml

Harbor 官方推荐离线安装包生成 compose，但也可手动拆镜像。下面提供简化版（核心组件齐全）：

```yaml
# /opt/cicd/harbor/docker-compose.yml
version: "3.9"

services:
  harbor-db:
    image: goharbor/harbor-db:v2.12.2
    container_name: harbor-db
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: harbor_db_change_me
      POSTGRES_USER: postgres
      POSTGRES_DB: registry
    volumes:
      - harbor-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  redis:
    image: goharbor/redis-photon:v2.12.2
    container_name: harbor-redis
    restart: unless-stopped
    volumes:
      - harbor-redis:/var/lib/redis
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  harbor-core:
    image: goharbor/harbor-core:v2.12.2
    container_name: harbor-core
    restart: unless-stopped
    depends_on:
      harbor-db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      CONFIG_PATH: /etc/harbor/app.conf
      POSTGRESQL_HOST: harbor-db
      POSTGRESQL_PORT: "5432"
      POSTGRESQL_USERNAME: postgres
      POSTGRESQL_PASSWORD: harbor_db_change_me
      POSTGRESQL_DATABASE: registry
      REDIS_HOST: redis
      REDIS_PORT: "6379"
      HARBOR_ADMIN_PASSWORD: HarborAdmin123!
      SELF_REGISTRATION: "off"
      AUTH_MODE: db_auth
    ports:
      - "8081:8080"   # HTTP
      - "8443:8443"   # HTTPS（需挂证书）
    volumes:
      - harbor-data:/data
      - harbor-config:/etc/harbor
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v2.0/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  harbor-jobservice:
    image: goharbor/harbor-jobservice:v2.12.2
    container_name: harbor-jobservice
    restart: unless-stopped
    depends_on:
      harbor-core:
        condition: service_healthy
    environment:
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  harbor-registryctl:
    image: goharbor/harbor-registryctl:v2.12.2
    container_name: harbor-registryctl
    restart: unless-stopped
    depends_on:
      harbor-core:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  registry:
    image: goharbor/registry-photon:v2.12.2
    container_name: harbor-registry
    restart: unless-stopped
    depends_on:
      harbor-core:
        condition: service_healthy
    volumes:
      - harbor-data:/data
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  trivy-adapter:
    image: goharbor/trivy-adapter-photon:v2.12.2
    container_name: harbor-trivy
    restart: unless-stopped
    depends_on:
      harbor-core:
        condition: service_healthy
    environment:
      TRIVY_OFFLINE_SCAN: "false"
      TRIVY_SKIP_UPDATE: "false"
    volumes:
      - harbor-trivy-cache:/root/.cache/trivy
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  harbor-db:
  harbor-redis:
  harbor-data:
  harbor-config:
  harbor-trivy-cache:
```

### D2.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `HARBOR_ADMIN_PASSWORD` | ✅ | admin 默认密码，首次登录后改 |
| `POSTGRESQL_PASSWORD` | ✅ | 数据库密码 |
| `AUTH_MODE` | ⚠️ | 生产用 `ldap_auth` 与企业目录打通 |
| `SELF_REGISTRATION` | ⚠️ | 生产关闭，避免任何人能注册推镜像 |
| `trivy-adapter` 卷 | ⚠️ | 漏扫 DB 缓存，离线环境要持久化避免重复下载 |

### D2.4 与 CI/CD 集成

GitLab CI 推镜像示例：
```yaml
build-and-push:
  stage: build
  image: docker:24.0.7
  services:
    - docker:24.0.7-dind
  variables:
    HARBOR_REGISTRY: "harbor.example.com:8081"
    IMAGE: "$HARBOR_REGISTRY/myteam/$CI_PROJECT_NAME:$CI_COMMIT_SHORT_SHA"
  before_script:
    - echo "$HARBOR_TOKEN" | docker login $HARBOR_REGISTRY -u $HARBOR_USER --password-stdin
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
  after_script:
    - docker logout $HARBOR_REGISTRY
```

凭据：在 GitLab 配 `HARBOR_USER` / `HARBOR_TOKEN` 两个 CI 变量，Harbor 端为该用户配机器人账号限定 push 命名空间。

### D2.5 验证与排障

```bash
curl -s -u admin:HarborAdmin123! http://localhost:8081/api/v2.0/health
# 推镜像验证
docker login localhost:8081
docker pull alpine:3.20
docker tag alpine:3.20 localhost:8081/test/alpine:3.20
docker push localhost:8081/test/alpine:3.20
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| push `400` unknown project | 项目不存在 | Harbor UI 先建 project，或用 API `POST /api/v2.0/projects` |
| scan 一直 pending | Trivy 不工作 | 检查 `harbor-trivy` 日志，多为外网拉 vuln db 超时 |
| `http: server gave HTTP response to HTTPS client` | docker push 报错 | insecure-registries 未配，编辑 `/etc/docker/daemon.json` 重启 docker |
| login 401 反复 | 账号正常但登录失败 | DB 密码不一致，重置 `HARBOR_ADMIN_PASSWORD` 需重置 core 容器 |

### D2.6 生产建议

- **HTTPS 必上**：用 `nginx` 或 Traefik 终结 TLS，证书挂到 harbor-core。
- **备份**：`pg_dump registry > harbor.sql` + 镜像数据卷快照，每日。
- **保留策略**：每个 project 配 `Tag Retention`：保留最近 10 个 tag + `latest`。
- **复制**：多机房用 Harbor Replication（pull-based）做灾备。
- **升级**：v2.12 → v2.13 直接换 tag；v2.x → v3.x 看 migration guide。

---

## D3. SonarQube

### D3.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB（含 ES） | 8 GB |
| 磁盘 | 20 GB | 100 GB（历史扫描数据） |
| 内核参数 | `vm.max_map_count=262144` | 必须，否则 Elasticsearch 起不来 |

宿主机执行：
```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
```

### D3.2 docker-compose.yml

```yaml
# /opt/cicd/sonar/docker-compose.yml
version: "3.9"

services:
  sonar-db:
    image: postgres:16-alpine
    container_name: sonar-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: sonar_db_change_me
      POSTGRES_DB: sonar
    volumes:
      - sonar-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sonar"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  sonarqube:
    image: sonarqube:25.1.0.102705-community
    container_name: sonarqube
    restart: unless-stopped
    depends_on:
      sonar-db:
        condition: service_healthy
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://sonar-db:5432/sonar
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: sonar_db_change_me
      SONAR_WEB_HOST: 0.0.0.0
      SONAR_WEB_PORT: "9000"
      SONAR_WEB_CONTEXT: /
      # 不再硬编码登录密码，用 token
    ports:
      - "9000:9000"
    volumes:
      - sonar-data:/opt/sonarqube/data
      - sonar-logs:/opt/sonarqube/logs
      - sonar-extensions:/opt/sonarqube/extensions
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/system/status"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 180s
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G

volumes:
  sonar-db:
  sonar-data:
  sonar-logs:
  sonar-extensions:
```

### D3.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `vm.max_map_count` | ✅ | 宿主机内核参数，不调 ES 启动失败 |
| `SONAR_JDBC_*` | ✅ | 强烈建议用外部 PG，内置 H2 仅限演示 |
| `SONAR_WEB_PORT` | ⚠️ | 改端口需与 ports 映射一致 |
| `sonar-extensions` 卷 | ⚠️ | 持久化插件，避免升级丢插件 |
| Quality Gate | ⚠️ | UI 内配置 `Sonar way` 自定义阈值 |

### D3.4 与 CI/CD 集成

GitLab CI：
```yaml
sonar-scan:
  stage: scan
  image: sonarsource/sonar-scanner-cli:5.0.1
  variables:
    SONAR_HOST_URL: "http://sonarqube.example.com:9000"
    SONAR_TOKEN: "$SONAR_TOKEN"
    SONAR_PROJECT_KEY: "myteam-$CI_PROJECT_NAME"
  script:
    - sonar-scanner
        -Dsonar.projectKey=$SONAR_PROJECT_KEY
        -Dsonar.sources=.
        -Dsonar.python.coverage.reportPaths=coverage.xml
        -Dsonar.qualitygate.wait=true
  allow_failure: false   # 质量门不通过则阻断流水线
```

凭据：`SONAR_TOKEN` 为用户级 token（UI → My Account → Security → Generate Tokens），配 GitLab CI 变量 masked。

### D3.5 验证与排障

```bash
curl -s http://localhost:9000/api/system/status | jq .
# 默认登录 admin / admin，首次强制改密
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| ES 启动失败 | `max virtual memory areas` | 宿主机未调 `vm.max_map_count` |
| 扫描卡住 | `qualitygate.wait` 一直转 | 大项目首次扫描慢，加 `-Dsonar.scanner.scanAnalysis` 调超时 |
| Python 规则不全 | 看不到 `bandit` 风险 | 装 Python 插件 + 配 `sonar.python.bandit.reportPaths` |
| 数据库连不上 | `connection refused` | `depends_on: condition: service_healthy` 未生效 |
| 升级后规则消失 | Profile 空白 | 数据库未迁移；旧版数据卷需 import |

### D3.6 生产建议

- **备份**：`pg_dump sonar` + `data` 卷（含 ES 索引），每日。
- **升级**：LTS 才能跨大版本（9.9 LTS → 2025.1 LTS）。非 LTS 版本不能跨，必须按顺序升。
- **告警**：Webhook 把 Quality Gate 失败推到飞书/钉钉。
- **清理**：定期删旧分析数据，UI → Administration → Housekeeping。

---

## D4. Trivy（CLI + Server）

### D4.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.5 核 | 1 核 |
| 内存 | 512 MB | 1 GB（含 vuln db 缓存） |
| 磁盘 | 5 GB（vuln db） | 10 GB |
| 网络 | 拉取 vuln db 需外网 | 离线场景用 `--skip-update` + 离线 db 包 |

### D4.2 docker-compose.yml（Server 模式）

CLI 模式无需常驻容器，只需 `pip install` 或下载二进制。Server 模式用于多 Runner 共享 vuln db。

```yaml
# /opt/cicd/trivy/docker-compose.yml
version: "3.9"

services:
  trivy-server:
    image: aquasec/trivy:0.58.2
    container_name: trivy-server
    restart: unless-stopped
    command: ["server", "--listen", "0.0.0.0:8082"]
    ports:
      - "8082:8082"
    volumes:
      - trivy-cache:/root/.cache/trivy
    healthcheck:
      test: ["CMD", "trivy", "server", "--help"]
      interval: 60s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  trivy-cache:
```

### D4.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `--listen 0.0.0.0:8082` | ✅ | 默认只监听 localhost |
| `trivy-cache` 卷 | ⚠️ | vuln db 缓存，重启不重下 |
| `--token` | ⚠️ | 生产加 token 防止匿名调用 |
| 离线模式 | ⚠️ | `--skip-update` + 手动导入 airgap db |

### D4.4 与 CI/CD 集成

GitLab CI（直接 CLI 模式）：
```yaml
trivy-image:
  stage: scan
  image: aquasec/trivy:0.58.2
  variables:
    TRIVY_NO_PROGRESS: "true"
    TRIVY_CACHE_DIR: ".trivycache/"
  script:
    - trivy image --exit-code 1 --severity HIGH,CRITICAL
        --ignore-unfixed
        --format json -o trivy-report.json
        $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  artifacts:
    when: always
    reports:
      dependency_scanning: trivy-report.json
  cache:
    paths:
      - .trivycache/
```

Server 模式：加 `--server http://trivy-server:8082` 即可。

### D4.5 验证与排障

```bash
# CLI 验证
trivy fs --severity HIGH,CRITICAL .
trivy image --format json -o r.json alpine:3.20
# Server 验证
trivy --server http://localhost:8082 image alpine:3.20
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| `database update failed` | 拉不下 vuln db | 网络问题，配置镜像 `TRIVY_DB_REPOSITORY=public.ecr.aws/aquasecurity/trivy-db` |
| `--ignore-unfixed` 漏报 | CVE 没显示 | 该参数只显示有 fix 的，排查时去掉 |
| Server 首次慢 | 客户端 5 分钟无响应 | Server 首次同步 db，预热后再接 CI |
| 报告 artifacts 不显示 | MR 上看不到 | 需配 `dependency_scanning` report 类型 |

### D4.6 生产建议

- **私有镜像源**：用 `public.ecr.aws/aquasecurity/trivy-db` 镜像源避免 GitHub 限流。
- **离线**：air-gap 环境用 `trivy --skip-db-update --db-repository file:///path/to/db`。
- **告警**：在 CI 中加 webhook，CRITICAL 漏洞超阈值时推飞书。
- **与 Harbor**：Harbor 自带 Trivy adapter，独立部署 Server 仅用于扫描非 Harbor 镜像。

---

## D5. Dependency-Track

### D5.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB |

### D5.2 docker-compose.yml

```yaml
# /opt/cicd/dtrack/docker-compose.yml
version: "3.9"

services:
  dtrack-db:
    image: postgres:16-alpine
    container_name: dtrack-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: dtrack
      POSTGRES_PASSWORD: dtrack_db_change_me
      POSTGRES_DB: dtrack
    volumes:
      - dtrack-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dtrack"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  dtrack-apiserver:
    image: dependencytrack/apiserver:4.12.5
    container_name: dtrack-apiserver
    restart: unless-stopped
    depends_on:
      dtrack-db:
        condition: service_healthy
    environment:
      ALPINE_DATABASE_MODE: external
      ALPINE_DATABASE_URL: jdbc:postgresql://dtrack-db:5432/dtrack
      ALPINE_DATABASE_DRIVER: org.postgresql.Driver
      ALPINE_DATABASE_USERNAME: dtrack
      ALPINE_DATABASE_PASSWORD: dtrack_db_change_me
      ALPINE_DATABASE_POOL_MAX_SIZE: "20"
    ports:
      - "8083:8080"   # 错开 Harbor 的 8081
    volumes:
      - dtrack-data:/data
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/api/v1/version"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G

  dtrack-frontend:
    image: dependencytrack/frontend:4.12.5
    container_name: dtrack-frontend
    restart: unless-stopped
    depends_on:
      dtrack-apiserver:
        condition: service_healthy
    environment:
      API_URL: http://localhost:8083
    ports:
      - "8084:8080"
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M

volumes:
  dtrack-db:
  dtrack-data:
```

### D5.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `ALPINE_DATABASE_*` | ✅ | 强制用外部 PG，内置 H2 不可生产 |
| `API_URL` | ✅ | 前端访问后端地址，写外部可达地址 |
| `ALPINE_DATABASE_POOL_MAX_SIZE` | ⚠️ | 默认 10，并发扫描量大调到 20-30 |
| 端口 8083 | ⚠️ | 避开 Harbor 8081 |

### D5.4 与 CI/CD 集成

GitLab CI 推送 SBOM（CycloneDX）：
```yaml
sbom-and-upload:
  stage: scan
  image: cyclonedx/cyclonedx-cli:0.26.0
  variables:
    DTRACK_URL: "http://dtrack.example.com:8083"
    DTRACK_API_KEY: "$DTRACK_API_KEY"
    PROJECT_ID: "$DTRACK_PROJECT_ID"
  script:
    # Python 项目用 cyclonedx-bom 生成
    - pip install cyclonedx-bom==5.1.2
    - cyclonedx-py environment -o bom.xml
    # 上传到 Dependency-Track
    - |
      curl -X POST "$DTRACK_URL/api/v1/bom" \
        -H "X-Api-Key: $DTRACK_API_KEY" \
        -H "Content-Type: multipart/form-data" \
        -F "project=$PROJECT_ID" \
        -F "bom=@bom.xml"
```

凭据：`DTRACK_API_KEY` 在 DTrack UI 创建 Automation 时生成，配 GitLab masked 变量。

### D5.5 验证与排障

```bash
curl -s http://localhost:8083/api/v1/version
# UI 访问 http://localhost:8084，默认 admin/admin
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| 上传 SBOM 后无数据 | project 显示空 | project 不存在自动创建需开 API 权限；建议先建 project |
| vuln 同步慢 | 30 分钟无 CVE | 后台 mirror 各生态库，看日志 `apiserver` 是否在拉 |
| `OOMKilled` | apiserver 重启循环 | 内存不足，调高 memory limit；DB pool 调小 |
| frontend 加载白屏 | 控制台 CORS 错 | `API_URL` 写错，必须前端浏览器可达 |

### D5.6 生产建议

- **备份**：`pg_dump dtrack` + `data` 卷（含已下载 vuln db）。
- **告警**：UI → Project → Notification Rules → Webhook 推飞书。
- **清理**：删除 90 天无活动的旧 project，避免 DB 膨胀。
- **镜像源加速**：vuln 镜像源可切 OSMU 镜像。

---

## D6. Renovate / Renovate Bot

### D6.1 资源需求

Renovate 无常驻服务，由 GitLab CI 定时触发，资源按需。

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.5 核（单次任务） | 1 核 |
| 内存 | 512 MB | 1 GB |
| 磁盘 | 无持久化 | 无 |

### D6.2 docker-compose.yml（self-hosted runner 模式）

Renovate 推荐用 GitLab CI Pipeline Schedule 触发，不需要 compose。但若要常驻 Webhook 模式，可用下面：

```yaml
# /opt/cicd/renovate/docker-compose.yml
version: "3.9"

services:
  renovate:
    image: renovate/renovate:39.20.5-full
    container_name: renovate
    restart: "no"   # 由 cron 触发，不常驻
    environment:
      LOG_LEVEL: info
      RENOVATE_PLATFORM: gitlab
      RENOVATE_ENDPOINT: http://gitlab:8080/api/v4
      RENOVATE_TOKEN: ${RENOVATE_TOKEN}
      RENOVATE_REPOSITORIES: "myteam/service-a,myteam/service-b"
      RENOVATE_ONBOARDING_CONFIG_FILE_NAME: renovate.json
      RENOVATE_EXTEND_CONFIG: "config:recommended"
    volumes:
      - renovate-cache:/tmp/renovate
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  renovate-cache:
```

### D6.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `RENOVATE_TOKEN` | ✅ | GitLab project access token，需 `api` + `write_repository` 权限 |
| `RENOVATE_REPOSITORIES` | ✅ | 逗号分隔，或留空走 `autodiscover` |
| `RENOVATE_EXTEND_CONFIG` | ⚠️ | `config:recommended` 默认策略；改 `config:base` 兼容旧 |
| `RENOVATE_AUTODISCOVER` | ⚠️ | `true` 则扫所有可见仓，注意权限 |

### D6.4 与 CI/CD 集成（推荐方式）

GitLab Pipeline Schedule 模式：
```yaml
# .gitlab-ci.yml 在专门的 renovate-runner 仓库
renovate:
  image: renovate/renovate:39.20.5-full
  stage: deploy
  variables:
    RENOVATE_PLATFORM: gitlab
    RENOVATE_ENDPOINT: http://gitlab:8080/api/v4
    RENOVATE_TOKEN: $RENOVATE_TOKEN
    RENOVATE_REPOSITORIES: $CI_PROJECT_PATH
  script:
    - renovate
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
```

在 GitLab UI 配 Schedule（每日 02:00 cron `0 2 * * *`）。

### D6.5 验证与排障

```bash
docker run --rm renovate/renovate:39.20.5-full --version
# 手动跑一次看日志
docker-compose run --rm renovate
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| `platform unauthorized` | 401 | token 过期或权限不足，需 `api` scope |
| `onboarding PR` 不出现 | 仓库无 MR | 检查 token 是否有该 repo 写权限 |
| 拉 npm/pypi 慢 | 任务超时 | 配 `hostRules` 用内网镜像 |
| `auto-merge` 不生效 | MR 走到 merge 卡住 | GitLab project settings → Merge requests → 启用 auto-merge |

### D6.6 生产建议

- **限速**：大仓库多时设 `RENOVATE_HOST_RULES` 防撞 GitHub API 限流。
- **告警**：renovate 失败时 MR 创建失败，用 GitLab Pipeline notification 推飞书。
- **审计**：开 `dryRun: true` 先看变更不合并，确认策略再正式跑。

---

## D7. OWASP ZAP

### D7.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 1 GB | 5 GB（报告） |
| 目标应用 | 需运行中 | DAST 需要可访问的目标 URL |

### D7.2 docker-compose.yml

```yaml
# /opt/cicd/zap/docker-compose.yml
version: "3.9"

services:
  zap-baseline:
    image: softwaresecurityproject/zap2docker-stable:2.15.0
    container_name: zap-runner
    restart: "no"
    # 一般不在 compose 常驻，CI 调用为主；下面配置保留容器
    volumes:
      - zap-reports:/zap/wrk
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G

volumes:
  zap-reports:
```

### D7.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `-t target_url` | ✅ | 必须能从容器内访问 |
| `-config` 配置文件 | ⚠️ | 自定义扫描规则、认证上下文 |
| `zap-reports` 卷 | ⚠️ | 报告持久化 |

### D7.4 与 CI/CD 集成

GitLab CI baseline scan：
```yaml
zap-baseline:
  stage: scan
  image: softwaresecurityproject/zap2docker-stable:2.15.0
  variables:
    TARGET_URL: "https://staging.example.com"
  script:
    - mkdir -p zap-out
    - zap-baseline.py -t $TARGET_URL -J zap-out/report.json -x zap-out/report.xml
      -c config/zap-rules.conf
  artifacts:
    when: always
    paths:
      - zap-out/
    reports:
      dast: zap-out/report.xml
  allow_failure: false
```

凭据：被测应用需登录态时，用 ZAP Context + 自定义脚本注入 cookie，凭据配 GitLab 变量。

### D7.5 验证与排障

```bash
docker run --rm softwaresecurityproject/zap2docker-stable:2.15.0 \
  zap-baseline.py -t https://example.com -J report.json
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| `X-Frame-Options` 误报 | 警告一堆 | 加 `-config` rules 文件 ignore id 10020 |
| 认证站点扫描不全 | 只扫到登录页 | 用 Context + recorded auth script |
| 超时 | 扫描 30 分钟未结束 | 加 `-m 10` 限制分钟数 |
| 报告中文乱码 | xml 中字符损坏 | 用 `-x report.xml` 而非 `-w` 默认 html |

### D7.6 生产建议

- **目标**：只在 staging 跑，**禁止** 对生产做 active scan。
- **限速**：`-config network.rate=10` 避免压垮被测系统。
- **告警**：HIGH 阈值超 N 个时 fail pipeline。
- **报告归档**：每周归档到对象存储。

---

## D8. Bandit / Semgrep

### D8.1 资源需求

纯 CLI 工具，按 CI job 临时拉起。

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.5 核 | 1 核 |
| 内存 | 256 MB | 512 MB |
| 磁盘 | 100 MB | 200 MB |

### D8.2 docker-compose.yml（pre-commit 本地用）

通常直接用 `pip install`，无需 compose。若 CI 镜像统一管理：

```yaml
# /opt/cicd/sast/docker-compose.yml
version: "3.9"

services:
  bandit:
    image: returntocorp/semgrep:1.96.0
    container_name: sast-runner
    restart: "no"
    volumes:
      - ../:/src
    working_dir: /src
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

Bandit 直接 pip：
```bash
python -m venv .venv && source .venv/bin/activate
pip install bandit==1.7.10 semgrep==1.96.0
bandit -r app/ -f json -o bandit-report.json
semgrep scan --config p/python --config p/owasp-top-ten --json -o semgrep-report.json
```

### D8.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `.bandit` 文件 | ⚠️ | 项目级 ignore 列表 |
| `semgrep` ruleset | ✅ | `p/python` `p/owasp-top-ten` 等组合 |
| `.pre-commit-config.yaml` | ⚠️ | 本地提交前自动跑 |

### D8.4 与 CI/CD 集成

```yaml
# .gitlab-ci.yml
bandit:
  stage: scan
  image: python:3.12-slim
  script:
    - pip install bandit==1.7.10
    - bandit -r app/ -f json -o bandit-report.json || true
  artifacts:
    reports:
      sast: bandit-report.json

semgrep:
  stage: scan
  image: returntocorp/semgrep:1.96.0
  script:
    - semgrep scan --config p/python --config p/owasp-top-ten
        --json -o semgrep-report.json
  artifacts:
    reports:
      sast: semgrep-report.json
  allow_failure: false
```

pre-commit 配置（提交前拦截）：
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.10
    hooks:
      - id: bandit
        args: ["-r", "app/", "-ll"]
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.96.0
    hooks:
      - id: semgrep
        args: ["--config", "p/python"]
```

### D8.5 验证与排障

```bash
bandit -r app/ -f txt
semgrep scan --config p/python --dryrun .
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| Bandit 误报一堆 assert | 全是 B101 | `# nosec B101` 注释或加 `-ll` 只报中高 |
| semgrep ruleset 拉不下 | `failed to fetch rules` | 网络问题，用 `--config auto` 或预下载到本地 |
| pre-commit 慢 | 提交卡 30s | bandit 改成 `-r app/` 范围收窄 |
| GitLab 报告不显示 | sast 报告为空 | artifacts `reports.sast` 格式必须符合 GitLab schema |

### D8.6 生产建议

- **基线**：先开 `allow_failure: true` 跑一周摸底，再转 `false` 阻断。
- **规则自定义**：用 `--config .semgrep.yml` 加团队规则。
- **与 SonarQube 互补**：Sonar 看代码味道/重复，Semgrep 看安全规则，互不替代。

---

## D9. Gitleaks

### D9.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.2 核 | 0.5 核 |
| 内存 | 128 MB | 256 MB |
| 磁盘 | 50 MB | 100 MB |

### D9.2 docker-compose.yml / 二进制

二进制安装（推荐，最快）：
```bash
# 下载到 /usr/local/bin
curl -sSL https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz \
  | sudo tar -xz -C /usr/local/bin gitleaks
sudo chmod +x /usr/local/bin/gitleaks
gitleaks version
```

Docker 方式：
```yaml
# /opt/cicd/gitleaks/docker-compose.yml
version: "3.9"
services:
  gitleaks:
    image: zricethezav/gitleaks:v8.21.2
    container_name: gitleaks
    restart: "no"
    volumes:
      - ../:/repo
    working_dir: /repo
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
```

### D9.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `.gitleaksignore` | ⚠️ | 已知误报白名单，按指纹 hash 忽略 |
| `--config` 自定义 rules | ⚠️ | 加企业内部 key 前缀规则 |
| `--redact` | ⚠️ | 日志中不打印真实 secret |

### D9.4 与 CI/CD 集成

```yaml
# .gitlab-ci.yml
gitleaks:
  stage: scan
  image: zricethezav/gitleaks:v8.21.2
  script:
    - gitleaks detect --source . --redact
        --report-format json --report-path gitleaks-report.json
        --config .gitleaks.toml
  artifacts:
    reports:
      secret_detection: gitleaks-report.json
  allow_failure: false
```

pre-commit：
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

### D9.5 验证与排障

```bash
echo "AKIA1234567890ABCD" > /tmp/test-secret.txt
gitleaks detect --source /tmp --no-banner   # 应报警
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| 误报太多 | 项目内大量已脱敏样例 | `.gitleaksignore` 加指纹 |
| 漏报已知 key | 自研 key 前缀不识别 | `.gitleaks.toml` 加自定义 rule |
| 历史 commit 扫超时 | 大仓很慢 | `--log-opts="--since=2025-01-01"` 限定范围 |
| `--redact` 仍打印 | 输出含明文 | 用 `--report-format sarif` |

### D9.6 生产建议

- **全历史扫描**：上线初期跑一次 `gitleaks detect --source . --log-opts="--all"` 摸底。
- **告警**：发现真实 secret 立即撤回并轮换，GitLab variable `allow_failure: false`。
- **与 S1 联动**：发现 secret → 推 Vault 轮换 → 更新 External Secrets。

---

## D10. Prometheus + Grafana + Loki + Promtail

### D10.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB | 200 GB SSD（Loki 数据） |

### D10.2 docker-compose.yml

```yaml
# /opt/cicd/monitoring/docker-compose.yml
version: "3.9"

services:
  prometheus:
    image: prom/prometheus:v3.1.0
    container_name: prometheus
    restart: unless-stopped
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=30d
      - --web.enable-lifecycle
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
      - prometheus-data:/prometheus
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G

  grafana:
    image: grafana/grafana:11.4.0
    container_name: grafana
    restart: unless-stopped
    depends_on:
      prometheus:
        condition: service_healthy
    environment:
      GF_SECURITY_ADMIN_PASSWORD: grafana_admin_change_me
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_INSTALL_PLUGINS: grafana-loki-datasource
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 1G

  loki:
    image: grafana/loki:3.3.2
    container_name: loki
    restart: unless-stopped
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    volumes:
      - ./loki/loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G

  promtail:
    image: grafana/promtail:3.3.2
    container_name: promtail
    restart: unless-stopped
    command:
      - -config.file=/etc/promtail/config.yml
    volumes:
      - ./promtail/promtail.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

volumes:
  prometheus-data:
  grafana-data:
  loki-data:
```

配套 `prometheus/prometheus.yml`：
```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']
  - job_name: gitlab
    static_configs:
      - targets: ['gitlab:9168']
  - job_name: harbor
    static_configs:
      - targets: ['harbor-core:9090']
  - job_name: sonarqube
    static_configs:
      - targets: ['sonarqube:9000']
```

### D10.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `retention.time=30d` | ⚠️ | 默认 15d，按磁盘调 |
| `GF_SECURITY_ADMIN_PASSWORD` | ✅ | 改默认 admin |
| Loki `local-config.yaml` | ⚠️ | fs 类 storage；生产用 S3 |
| Promtail `docker_sd` | ⚠️ | 自动发现容器日志 |

### D10.4 与 CI/CD 集成

Pipeline 指标用 D11 Pushgateway 推送，Prometheus scrape Pushgateway：
```yaml
# prometheus.yml 追加
  - job_name: pushgateway
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
```

Grafana Dashboard：导入社区 dashboard ID 11074（GitLab）、13639（Harbor）、15983（Loki）。

### D10.5 验证与排障

```bash
curl -s http://localhost:9090/-/healthy
curl -s http://localhost:3100/ready
curl -s http://localhost:3000/api/health
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| Prometheus 不抓 target | `server returned HTTP 404` | exporter 端口或 path 写错 |
| Loki `too many outstanding requests` | 写入失败 | 调 `chunk_idle_period` / 加 `max_streams_per_user` |
| Grafana 数据源 401 | 添加 datasource 报错 | provisioning 密码错或网络不通 |
| Promtail 不收容器日志 | label 为空 | 未挂 `/var/lib/docker/containers` |

### D10.6 生产建议

- **存储**：Loki 切 S3/MinIO，避免本地盘满。
- **告警**：通过 D13 Alertmanager 转发。
- **保留**：Prometheus 30d，Loki 14d，超期转对象存储冷备。
- **HA**：Prometheus 双副本 + Thanos；Grafana 用 PostgreSQL 后端共享 dashboard。

---

## D11. Pushgateway

### D11.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.2 核 | 0.5 核 |
| 内存 | 128 MB | 256 MB |
| 磁盘 | 1 GB | 5 GB |

### D11.2 docker-compose.yml

```yaml
# /opt/cicd/monitoring/docker-compose-pushgateway.yml
version: "3.9"

services:
  pushgateway:
    image: prom/pushgateway:v1.10.0
    container_name: pushgateway
    restart: unless-stopped
    command:
      - --web.listen-address=0.0.0.0:9091
      - --persistence.file=/data/pushgateway.db
      - --persistence.interval=60s
    ports:
      - "9091:9091"
    volumes:
      - pushgateway-data:/data
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9091/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M

volumes:
  pushgateway-data:
```

### D11.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `--persistence.file` | ✅ | 不持久化重启后指标全丢 |
| `--persistence.interval` | ⚠️ | 默认 5min，建议 60s 防止丢数据 |
| `honor_labels: true`（Prom 侧） | ✅ | 否则 job/instance 被覆盖 |

### D11.4 与 CI/CD 集成

GitLab CI 推送 job 指标：
```yaml
deploy:
  stage: deploy
  script:
    - ./deploy.sh
    - |
      echo "deployment_duration_seconds $SECONDS" | curl --data-binary @- \
        "http://pushgateway:9091/metrics/job/deploy/instance/$CI_PROJECT_NAME"
```

Python 推送：
```python
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()
g = Gauge('test_cases_passed', 'passed test cases', registry=registry, labelnames=['suite'])
g.labels(suite='unit').set(42)
push_to_gateway('pushgateway:9091', job='ci_test', registry=registry)
```

### D11.5 验证与排障

```bash
echo "test_metric 1" | curl --data-binary @- http://localhost:9091/metrics/job/test
curl http://localhost:9091/metrics
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| 指标永远不消失 | 老指标一直存在 | Pushgateway 不会自动过期；用 `DELETE` 方法或重启 |
| Prom 抓不到 | `instance` 全相同 | 加 label 区分；`honor_labels` 未开 |
| 文件丢失 | 重启后空 | 未挂 `--persistence.file` 卷 |

### D11.6 生产建议

- **不滥用**：仅用于批处理/短任务；常驻服务用 exporter 直接 scrape。
- **清理**：cron 定时 `DELETE` 旧指标，避免内存涨。
- **告警**：监控 Pushgateway 自身 `up=0`。

---

## D12. OpenTelemetry Collector + Tempo

### D12.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 20 GB | 100 GB（trace 数据） |

### D12.2 docker-compose.yml

```yaml
# /opt/cicd/tracing/docker-compose.yml
version: "3.9"

services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.116.1
    container_name: otel-collector
    restart: unless-stopped
    command: ["--config=/etc/otelcol/config.yaml"]
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # metrics
    volumes:
      - ./otelcol/config.yaml:/etc/otelcol/config.yaml:ro
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:13133/"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

  tempo:
    image: grafana/tempo:2.6.0
    container_name: tempo
    restart: unless-stopped
    command: ["-config.file=/etc/tempo.yaml"]
    ports:
      - "3200:3200"   # tempo HTTP
      - "14268:14268" # jaeger ingest
    volumes:
      - ./tempo/tempo.yaml:/etc/tempo.yaml:ro
      - tempo-data:/var/tempo
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  tempo-data:
```

`otelcol/config.yaml`：
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:8889

extensions:
  health_check:
    endpoint: 0.0.0.0:13133

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

### D12.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `otlp/tempo.endpoint` | ✅ | Collector → Tempo 地址 |
| `memory_limiter` | ⚠️ | 防止 OOM |
| Tempo `storage` | ⚠️ | 生产用 S3 |
| `trace_ids` 采样 | ⚠️ | 高 QPS 用 tail sampling |

### D12.4 与 CI/CD 集成

CI 通常不发 trace。集成在应用代码（Python/Java）：
```python
# Python 应用
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True))
)
# 自动 instrumentation 推荐 opentelemetry-instrument
```

Grafana 添加 Tempo 数据源即可查询 trace。

### D12.5 验证与排障

```bash
# 用 tracegen 测试
docker run --rm --network cicd-net \
  ghcr.io/open-telemetry/opentelemetry-collector-contrib/tracegen:0.116.1 \
  -duration 5s -workers 5 -otel-collector-endpoint otel-collector:4317
curl http://localhost:3200/ready
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| Collector 报 `connection refused` | Tempo 不通 | Tempo 启动慢，等 ready；检查 endpoint |
| Grafana 查不到 trace | Tempo 数据源测试 200 但空 | 时区 / 时间范围错；trace ID 没传 |
| OOMKilled | Collector 反复重启 | 调小 batch / 加 memory_limiter |
| TLS 报错 | `insecure` 报警 | Tempo 用 `tls.insecure: true` |

### D12.6 生产建议

- **采样**：高流量用 tail sampling processor，仅采 10%。
- **存储**：Tempo 后端切 S3/MinIO。
- **关联**：trace_id 注入 Loki 日志（structured logging）。
- **保留**：trace 7 天，超期删除。

---

## D13. Alertmanager + Unleash

### D13.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 5 GB | 20 GB（Unleash 历史事件） |

### D13.2 docker-compose.yml

```yaml
# /opt/cicd/alert-feature/docker-compose.yml
version: "3.9"

services:
  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager
    restart: unless-stopped
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  unleash-db:
    image: postgres:16-alpine
    container_name: unleash-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: unleash
      POSTGRES_PASSWORD: unleash_db_change_me
      POSTGRES_DB: unleash
    volumes:
      - unleash-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U unleash"]
      interval: 10s
      timeout: 5s
      retries: 5

  unleash:
    image: unleash/unleash-server:5.16.0
    container_name: unleash
    restart: unless-stopped
    depends_on:
      unleash-db:
        condition: service_healthy
    environment:
      DATABASE_HOST: unleash-db
      DATABASE_PORT: "5432"
      DATABASE_USERNAME: unleash
      DATABASE_PASSWORD: unleash_db_change_me
      DATABASE_NAME: unleash
      INIT_ADMIN_API_TOKENS: "default:default.unleash-secret-token"
    ports:
      - "4242:4242"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:4242/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  alertmanager-data:
  unleash-db:
```

`alertmanager/alertmanager.yml`：
```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: default
  routes:
    - match:
        severity: critical
      receiver: feishu
      continue: true

receivers:
  - name: default
    webhook_configs:
      - url: 'http://localhost:5000/default'
        send_resolved: true
  - name: feishu
    webhook_configs:
      - url: 'https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx'
        send_resolved: true
```

### D13.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `INIT_ADMIN_API_TOKENS` | ✅ | Unleash client token，CI 调用必需 |
| Alertmanager webhook url | ✅ | 改成实际飞书/钉钉群机器人 |
| `DATABASE_*` | ✅ | Unleash 必须用外部 PG |
| `repeat_interval` | ⚠️ | 防止告警风暴，按团队调 |

### D13.4 与 CI/CD 集成

Feature Flag 在部署阶段查询 Unleash：
```yaml
# .gitlab-ci.yml
deploy-canary:
  stage: deploy
  image: python:3.12-slim
  variables:
    UNLEASH_URL: "http://unleash:4242/api"
    UNLEASH_TOKEN: "$UNLEASH_TOKEN"
  script:
    - pip install UnleashClient==5.1.1
    - |
      python -c "
      from UnleashClient import UnleashClient
      uc = UnleashClient('$UNLEASH_URL', '$UNLEASH_TOKEN')
      uc.initialize_client()
      if uc.is_enabled('enable-blue-green', context={'env': 'staging'}):
          print('ENABLED')
      else:
          print('DISABLED')
      "
```

告警规则放 D10 Prometheus `rules/`：
```yaml
# rules/cicd-alerts.yml
groups:
  - name: cicd
    rules:
      - alert: PipelineFailureRate
        expr: rate(gitlab_ci_pipeline_failed_total[10m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "CI pipeline failure rate > 10%"
```

### D13.5 验证与排障

```bash
curl http://localhost:9093/-/healthy
curl http://localhost:4242/health
curl -H "Authorization: default:default.unleash-secret-token" \
  http://localhost:4242/api/client/features
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| 告警不触发 | Alertmanager 一直没收到 | Prom `rule_files` 路径错；alert `for` 还没到 |
| 飞书收不到 | webhook 200 但群无消息 | url 不对或群机器人被禁言 |
| Unleash 启动失败 | DB 连不上 | depends_on healthcheck 未生效 |
| Unleash client 401 | token 失效 | 客户端 token 默认 1 年，到期需新建 |

### D13.6 生产建议

- **告警分级**：critical → 飞书电话加急；warning → 群消息；info → 日志。
- **Feature Flag 渐进**：先 1% → 10% → 50% → 100%，每档观察 30 分钟。
- **备份**：Unleash DB 每日 pg_dump；Alertmanager 配置纳入 git 版本控制。

---

## D14. Cosign + Rekor

### D14.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 0.5 核（签名任务） | 1 核 |
| 内存 | 256 MB | 512 MB |
| 磁盘 | 5 GB | 10 GB（Rekor 透明日志） |

### D14.2 docker-compose.yml（Rekor server）

Cosign 通常是 CLI 签名，Rekor 为可选透明日志服务（自建签名生态才需要）。

```yaml
# /opt/cicd/signing/docker-compose.yml
version: "3.9"

services:
  rekor-redis:
    image: redis:7-alpine
    container_name: rekor-redis
    restart: unless-stopped
    command: ["--save", "", "--appendonly", "no"]
    deploy:
      resources:
        limits:
          cpus: "0.3"
          memory: 256M

  rekor-server:
    image: ghcr.io/sigstore/rekor-server:v1.3.7
    container_name: rekor-server
    restart: unless-stopped
    depends_on:
      - rekor-redis
    command:
      - serve
      - --rekor_server_address=0.0.0.0
      - --redis-server-address=rekor-redis:6379
      - --trillian_log_server.address=trillian-logserver:8090
    ports:
      - "3000:3000"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes: {}
```

> **说明**：完整 Rekor 部署需要 Trillian log server + signer + MySQL，本专题只列出主线。生产建议直接用公共 Sigstore Rekor (`https://rekor.sigstore.dev`)，除非有合规要求才自建。

Cosign 二进制安装：
```bash
curl -sSL https://github.com/sigstore/cosign/releases/download/v2.4.1/cosign-linux-amd64 \
  -o /usr/local/bin/cosign
chmod +x /usr/local/bin/cosign
cosign version
```

### D14.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| Cosign key pair | ✅ | `cosign generate-key-pair` 生成，私钥放 Vault |
| `COSIGN_PASSWORD` | ✅ | 私钥加密密码 |
| `--rekor-url` | ⚠️ | 自建才配，默认公共 |
| OIDC vs key-based | ⚠️ | K8s 内用 OIDC（keyless）；本地用 key-based |

### D14.4 与 CI/CD 集成

```yaml
# .gitlab-ci.yml
sign-image:
  stage: sign
  image: alpine:3.20
  variables:
    COSIGN_PRIVATE_KEY: "$COSIGN_PRIVATE_KEY"   # CI 变量
    COSIGN_PASSWORD: "$COSIGN_PASSWORD"
    IMAGE: "$HARBOR_REGISTRY/myteam/app:$CI_COMMIT_SHA"
  before_script:
    - apk add --no-cache cosign
  script:
    - echo "$COSIGN_PRIVATE_KEY" > /tmp/cosign.key
    - COSIGN_PASSWORD=$COSIGN_PASSWORD cosign sign --key /tmp/cosign.key --yes $IMAGE
    - cosign verify --key /tmp/cosign.pub $IMAGE
  after_script:
    - rm -f /tmp/cosign.key
```

凭据：私钥放 D15 Vault，CI 通过 External Secrets 拉到 GitLab CI 变量。

### D14.5 验证与排障

```bash
cosign verify --key cosign.pub harbor.example.com/myteam/app:v1
cosign triangulate harbor.example.com/myteam/app:v1
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| `private key not found` | CI 中报错 | 私钥变量未注入或换行被吞，用 base64 编码后传递 |
| `EOF` 输入错误 | `--yes` 提示 | 加 `--yes` 跳过交互确认 |
| `tlog` 超时 | 公共 Rekor 慢 | 加 `--timeout 5m` 或离线签名 `--tlog-upload=false` |
| 验签失败 | `no matching signatures` | tag 与签名时引用不一致，用 digest 验证 |

### D14.6 生产建议

- **密钥**：私钥进 Vault + 轮换周期 90 天。
- **强制验签**：K8s 部署用 Kyverno / OPA Gatekeeper 强制只允许已签名镜像。
- **生产建议**：除非特殊合规，优先用公共 Rekor，节省运维成本。

---

## D15. Vault + External Secrets

### D15.1 资源需求

| 资源 | 最低 | 推荐 |
| ---- | ---- | ---- |
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 5 GB | 10 GB（Raft 存储） |

### D15.2 docker-compose.yml

```yaml
# /opt/cicd/vault/docker-compose.yml
version: "3.9"

services:
  vault:
    image: hashicorp/vault:1.18.3
    container_name: vault
    restart: unless-stopped
    cap_add:
      - IPC_LOCK    # 必须，Vault 用 mlock 防止 secret 被交换到磁盘
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
      # 生产模式去 dev root token，用配置文件初始化
    ports:
      - "8200:8200"
    volumes:
      - vault-data:/vault/file
      - vault-config:/vault/config
      - ./vault/vault.hcl:/etc/vault/vault.hcl:ro
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G

volumes:
  vault-data:
  vault-config:
```

`vault/vault.hcl`（生产配置）：
```hcl
storage "raft" {
  path    = "/vault/file"
  node_id = "vault-1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/tls/tls.crt"
  tls_key_file  = "/vault/tls/tls.key"
}

api_addr     = "https://vault.example.com:8200"
cluster_addr = "https://vault.example.com:8201"
ui           = true
disable_mlock = false
```

> **注意**：dev 模式（`VAULT_DEV_ROOT_TOKEN_ID`）仅用于测试，生产必须用 raft + TLS。

### D15.3 关键配置项说明

| 配置 | 必改 | 说明 |
| ---- | ---- | ---- |
| `IPC_LOCK` capability | ✅ | 不加 mlock 失败，secret 可能落盘 |
| `storage raft` | ✅ | 生产存储后端 |
| TLS | ✅ | 生产强制 TLS，dev 才允许 `tls_disable=1` |
| `api_addr` | ✅ | 外部访问地址 |
| KV v2 vs v1 | ⚠️ | 推 v2，支持版本历史与软删除 |

### D15.4 与 CI/CD 集成

External Secrets Operator（K8s）：将 Vault secret 同步为 K8s Secret，CI 通过 service account 拉取。

GitLab CI 直接读 Vault（Python）：
```yaml
# .gitlab-ci.yml
deploy:
  stage: deploy
  image: hashicorp/vault:1.18.3
  variables:
    VAULT_ADDR: "http://vault:8200"
  script:
    - export VAULT_TOKEN=$(vault write -field=token auth/jwt/login role=gitlab jwt=$CI_JOB_JWT_V2)
    - export DB_PASSWORD=$(vault kv get -field=password secret/myapp/db)
    - ./deploy.sh
```

GitLab CI 原生 Vault 集成（推荐 OIDC）：
```yaml
secrets:
  DATABASE_PASSWORD:
    vault: myapp/db/password@secret   # path@mount
```

需在 GitLab 配 OIDC + Vault JWT auth role。

### D15.5 验证与排障

```bash
vault status
vault operator init    # 首次初始化，记录 5 个 unseal key + root token
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
vault login
vault secrets enable -path=secret kv-v2
vault kv put secret/myapp/db password="real_password"
```

| 故障 | 现象 | 解决 |
| ---- | ---- | ---- |
| `vault is sealed` | API 403 | 重启后需 unseal，生产用 auto-unseal（AWS KMS） |
| mlock failed | 启动报错 | 缺 `IPC_LOCK` capability |
| JWT 登录失败 | 403 invalid role | role 配置的 bound_audience 与 JWT 不匹配 |
| External Secrets 不同步 | K8s 中无 Secret | 检查 SecretStore + ExternalSecret CRD |

### D15.6 生产建议

- **自动解封**：用 AWS KMS / GCP KMS auto-unseal，避免人工。
- **HA**：3 节点 raft 集群，5 个 unseal key 3 人持有（Shamir）。
- **审计**：开 `audit` device，所有 secret 访问记录到日志。
- **轮换**：DB 凭据用 `database secrets engine` 动态生成，定期轮换。
- **备份**：`vault operator raft snapshot save` 每日，与 S1 联动。

---

## 附录 A：一键部署总 compose

将 15 套设施整合为单个 `docker-compose.yml`。**注意**：实际部署建议按附录 B 分散到 3 台服务器，本附录仅用于演示联动与端口规划。

```yaml
# /opt/cicd/all-in-one/docker-compose.yml
# 网络：cicd-net 用于设施间互通；外部访问通过反向代理
version: "3.9"

networks:
  cicd-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  gitlab-config:
  gitlab-logs:
  gitlab-data:
  runner-config:
  runner-cache:
  harbor-db:
  harbor-redis:
  harbor-data:
  harbor-config:
  harbor-trivy-cache:
  sonar-db:
  sonar-data:
  sonar-logs:
  sonar-extensions:
  trivy-cache:
  dtrack-db:
  dtrack-data:
  renovate-cache:
  zap-reports:
  prometheus-data:
  grafana-data:
  loki-data:
  pushgateway-data:
  tempo-data:
  alertmanager-data:
  unleash-db:
  vault-data:
  vault-config:

services:

  # ============ D1 GitLab ============
  gitlab:
    image: gitlab/gitlab-ce:17.6.1-ce.0
    networks: [cicd-net]
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://gitlab.example.com:8080'
        gitlab_rails['initial_root_password'] = 'ChangeMe!2026'
        gitlab_rails['gitlab_shell_ssh_port'] = 8022
    ports: ["8080:8080", "8022:22"]
    volumes: [gitlab-config:/etc/gitlab, gitlab-logs:/var/log/gitlab, gitlab-data:/var/opt/gitlab]
    shm_size: "256m"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/-/health"]
      interval: 60s
      timeout: 10s
      retries: 5
      start_period: 300s

  gitlab-runner:
    image: gitlab/gitlab-runner:ubuntu-v17.6.1
    networks: [cicd-net]
    depends_on: { gitlab: { condition: service_healthy } }
    volumes:
      - runner-config:/etc/gitlab-runner
      - /var/run/docker.sock:/var/run/docker.sock
      - runner-cache:/cache

  # ============ D2 Harbor ============
  harbor-db:
    image: goharbor/harbor-db:v2.12.2
    networks: [cicd-net]
    environment:
      POSTGRES_PASSWORD: harbor_db_change_me
      POSTGRES_USER: postgres
      POSTGRES_DB: registry
    volumes: [harbor-db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  harbor-redis:
    image: goharbor/redis-photon:v2.12.2
    networks: [cicd-net]
    volumes: [harbor-redis:/var/lib/redis]

  harbor-core:
    image: goharbor/harbor-core:v2.12.2
    networks: [cicd-net]
    depends_on: { harbor-db: { condition: service_healthy } }
    environment:
      POSTGRESQL_HOST: harbor-db
      POSTGRESQL_PORT: "5432"
      POSTGRESQL_USERNAME: postgres
      POSTGRESQL_PASSWORD: harbor_db_change_me
      POSTGRESQL_DATABASE: registry
      REDIS_HOST: harbor-redis
      REDIS_PORT: "6379"
      HARBOR_ADMIN_PASSWORD: HarborAdmin123!
      SELF_REGISTRATION: "off"
      AUTH_MODE: db_auth
    ports: ["8081:8080", "8443:8443"]
    volumes: [harbor-data:/data, harbor-config:/etc/harbor]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v2.0/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  harbor-jobservice:
    image: goharbor/harbor-jobservice:v2.12.2
    networks: [cicd-net]
    depends_on: { harbor-core: { condition: service_healthy } }
    environment: { REDIS_HOST: harbor-redis, REDIS_PORT: "6379" }

  harbor-registryctl:
    image: goharbor/harbor-registryctl:v2.12.2
    networks: [cicd-net]
    depends_on: { harbor-core: { condition: service_healthy } }

  harbor-registry:
    image: goharbor/registry-photon:v2.12.2
    networks: [cicd-net]
    depends_on: { harbor-core: { condition: service_healthy } }
    volumes: [harbor-data:/data]

  harbor-trivy:
    image: goharbor/trivy-adapter-photon:v2.12.2
    networks: [cicd-net]
    depends_on: { harbor-core: { condition: service_healthy } }
    environment: { TRIVY_OFFLINE_SCAN: "false", TRIVY_SKIP_UPDATE: "false" }
    volumes: [harbor-trivy-cache:/root/.cache/trivy]

  # ============ D3 SonarQube ============
  sonar-db:
    image: postgres:16-alpine
    networks: [cicd-net]
    environment: { POSTGRES_USER: sonar, POSTGRES_PASSWORD: sonar_db_change_me, POSTGRES_DB: sonar }
    volumes: [sonar-db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sonar"]
      interval: 10s
      timeout: 5s
      retries: 5

  sonarqube:
    image: sonarqube:25.1.0.102705-community
    networks: [cicd-net]
    depends_on: { sonar-db: { condition: service_healthy } }
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://sonar-db:5432/sonar
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: sonar_db_change_me
    ports: ["9000:9000"]
    volumes: [sonar-data:/opt/sonarqube/data, sonar-logs:/opt/sonarqube/logs, sonar-extensions:/opt/sonarqube/extensions]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/system/status"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 180s

  # ============ D4 Trivy Server ============
  trivy-server:
    image: aquasec/trivy:0.58.2
    networks: [cicd-net]
    command: ["server", "--listen", "0.0.0.0:8082"]
    ports: ["8082:8082"]
    volumes: [trivy-cache:/root/.cache/trivy]

  # ============ D5 Dependency-Track ============
  dtrack-db:
    image: postgres:16-alpine
    networks: [cicd-net]
    environment: { POSTGRES_USER: dtrack, POSTGRES_PASSWORD: dtrack_db_change_me, POSTGRES_DB: dtrack }
    volumes: [dtrack-db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dtrack"]
      interval: 10s
      timeout: 5s
      retries: 5

  dtrack-apiserver:
    image: dependencytrack/apiserver:4.12.5
    networks: [cicd-net]
    depends_on: { dtrack-db: { condition: service_healthy } }
    environment:
      ALPINE_DATABASE_MODE: external
      ALPINE_DATABASE_URL: jdbc:postgresql://dtrack-db:5432/dtrack
      ALPINE_DATABASE_DRIVER: org.postgresql.Driver
      ALPINE_DATABASE_USERNAME: dtrack
      ALPINE_DATABASE_PASSWORD: dtrack_db_change_me
    ports: ["8083:8080"]
    volumes: [dtrack-data:/data]
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/api/v1/version"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s

  dtrack-frontend:
    image: dependencytrack/frontend:4.12.5
    networks: [cicd-net]
    depends_on: { dtrack-apiserver: { condition: service_healthy } }
    environment: { API_URL: http://localhost:8083 }
    ports: ["8084:8080"]

  # ============ D7 OWASP ZAP（按需启动）============
  zap-runner:
    image: softwaresecurityproject/zap2docker-stable:2.15.0
    networks: [cicd-net]
    profiles: ["scan"]   # 仅 docker-compose --profile scan up 才起
    volumes: [zap-reports:/zap/wrk]

  # ============ D10 Monitoring ============
  prometheus:
    image: prom/prometheus:v3.1.0
    networks: [cicd-net]
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=30d
    ports: ["9090:9090"]
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
      - prometheus-data:/prometheus
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3

  grafana:
    image: grafana/grafana:11.4.0
    networks: [cicd-net]
    depends_on: { prometheus: { condition: service_healthy } }
    environment:
      GF_SECURITY_ADMIN_PASSWORD: grafana_admin_change_me
      GF_USERS_ALLOW_SIGN_UP: "false"
    ports: ["3000:3000"]
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro

  loki:
    image: grafana/loki:3.3.2
    networks: [cicd-net]
    command: -config.file=/etc/loki/local-config.yaml
    ports: ["3100:3100"]
    volumes:
      - ./loki/loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki

  promtail:
    image: grafana/promtail:3.3.2
    networks: [cicd-net]
    command: [-config.file=/etc/promtail/config.yml]
    volumes:
      - ./promtail/promtail.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro

  # ============ D11 Pushgateway ============
  pushgateway:
    image: prom/pushgateway:v1.10.0
    networks: [cicd-net]
    command:
      - --web.listen-address=0.0.0.0:9091
      - --persistence.file=/data/pushgateway.db
      - --persistence.interval=60s
    ports: ["9091:9091"]
    volumes: [pushgateway-data:/data]

  # ============ D12 Tracing ============
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.116.1
    networks: [cicd-net]
    command: ["--config=/etc/otelcol/config.yaml"]
    ports: ["4317:4317", "4318:4318", "8888:8888"]
    volumes:
      - ./otelcol/config.yaml:/etc/otelcol/config.yaml:ro

  tempo:
    image: grafana/tempo:2.6.0
    networks: [cicd-net]
    command: ["-config.file=/etc/tempo.yaml"]
    ports: ["3200:3200", "14268:14268"]
    volumes:
      - ./tempo/tempo.yaml:/etc/tempo.yaml:ro
      - tempo-data:/var/tempo

  # ============ D13 Alert + Feature Flag ============
  alertmanager:
    image: prom/alertmanager:v0.27.0
    networks: [cicd-net]
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
    ports: ["9093:9093"]
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager-data:/alertmanager

  unleash-db:
    image: postgres:16-alpine
    networks: [cicd-net]
    environment: { POSTGRES_USER: unleash, POSTGRES_PASSWORD: unleash_db_change_me, POSTGRES_DB: unleash }
    volumes: [unleash-db:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U unleash"]
      interval: 10s
      timeout: 5s
      retries: 5

  unleash:
    image: unleash/unleash-server:5.16.0
    networks: [cicd-net]
    depends_on: { unleash-db: { condition: service_healthy } }
    environment:
      DATABASE_HOST: unleash-db
      DATABASE_PORT: "5432"
      DATABASE_USERNAME: unleash
      DATABASE_PASSWORD: unleash_db_change_me
      DATABASE_NAME: unleash
      INIT_ADMIN_API_TOKENS: "default:default.unleash-secret-token"
    ports: ["4242:4242"]

  # ============ D14 Rekor（可选）============
  rekor-redis:
    image: redis:7-alpine
    networks: [cicd-net]
    profiles: ["signing"]

  rekor-server:
    image: ghcr.io/sigstore/rekor-server:v1.3.7
    networks: [cicd-net]
    profiles: ["signing"]
    depends_on: [rekor-redis]
    ports: ["3001:3000"]

  # ============ D15 Vault ============
  vault:
    image: hashicorp/vault:1.18.3
    networks: [cicd-net]
    cap_add: [IPC_LOCK]
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    ports: ["8200:8200"]
    volumes:
      - vault-data:/vault/file
      - vault-config:/vault/config
      - ./vault/vault.hcl:/etc/vault/vault.hcl:ro
```

**启动顺序**（`depends_on` 已处理）：
1. 基础设施（DB / Redis）
2. 主服务（GitLab / Harbor-core / SonarQube / Vault）
3. 附属服务（Harbor-jobservice / dtrack-frontend / grafana）
4. Agent（gitlab-runner / promtail / otel-collector）

**一键启动**：
```bash
docker-compose -f docker-compose.yml up -d
# 只起扫描组件
docker-compose --profile scan run --rm zap-runner ...
# 只起签名组件
docker-compose --profile signing up -d rekor-server
```

---

## 附录 B：资源需求汇总表与 3 台 4C8G 分工建议

### B.1 总资源需求汇总

| 设施 | CPU（核） | 内存（GB） | 磁盘（GB） | 常驻 |
| ---- | -------- | ---------- | ---------- | ---- |
| D1 GitLab + Runner | 4 + 2 | 6 + 2 | 50 | ✅ |
| D2 Harbor 全栈 | 4 | 4 | 200 | ✅ |
| D3 SonarQube + DB | 3 | 5 | 100 | ✅ |
| D4 Trivy Server | 1 | 1 | 10 | ✅ |
| D5 Dependency-Track | 3 | 5 | 50 | ✅ |
| D6 Renovate | 1 | 1 | 0 | ❌（CI 触发） |
| D7 ZAP | 1 | 2 | 5 | ❌（CI 触发） |
| D8 Bandit/Semgrep | 1 | 0.5 | 0 | ❌ |
| D9 Gitleaks | 0.5 | 0.25 | 0 | ❌ |
| D10 Prom+Grafana+Loki+Promtail | 3 | 5 | 200 | ✅ |
| D11 Pushgateway | 0.5 | 0.25 | 5 | ✅ |
| D12 OTel + Tempo | 2 | 2 | 100 | ✅ |
| D13 Alertmanager + Unleash | 1.5 | 1.5 | 20 | ✅ |
| D14 Rekor（可选） | 1.3 | 1.25 | 10 | 可选 |
| D15 Vault | 1 | 1 | 10 | ✅ |
| **合计（含可选）** | **~28** | **~37** | **~760** | — |

### B.2 3 台 4C8G 服务器分工建议

> 单台 4C8G 内存上限 8GB，无法承载全部常驻设施（合计 ~37GB）。按"职责隔离 + 资源互补"分三台。

| 服务器 | 部署设施 | CPU/内存占用 | 角色 |
| ------ | -------- | ----------- | ---- |
| **节点 A：代码与构建** | D1 GitLab + Runner、D6 Renovate（CI 触发） | 6C / 8G | 代码仓 + CI 引擎 |
| **节点 B：安全与质量** | D3 SonarQube + DB、D5 Dependency-Track、D2 Harbor、D4 Trivy Server | 11C / 15G ⚠️ | 扫描与镜像仓 |
| **节点 C：可观测性 + Secret** | D10 监控栈、D11 Pushgateway、D12 Tracing、D13 Alert+Unleash、D15 Vault | 8C / 10G ⚠️ | 监控 + 配置 |

**节点 B/C 资源超出 8G**，建议：
1. 升级到 16G 内存（CPU 4 核可保持）
2. 或拆为 4 台：B1 SonarQube、B2 Harbor+Trivy+DTrack、C1 监控、C2 Vault+Unleash
3. 或非核心设施（DTrack / Tempo）改用对象存储后端以省本地内存

**网络规划**：
- 三台同子网，内网互通
- 通过 Nginx/Traefik 反向代理统一对外 80/443
- GitLab Runner 在节点 A，可调度到 B/C 的 docker socket

---

## 附录 C：备份与恢复脚本

### C.1 统一备份脚本（cron 每日 02:00）

```bash
#!/usr/bin/env bash
# /opt/cicd/backup/backup-all.sh
set -euo pipefail

BACKUP_DIR="/data/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
RETAIN_DAYS=7

log() { echo "[$(date '+%F %T')] $*"; }

# PostgreSQL 类（GitLab 内置、Harbor、SonarQube、Dependency-Track、Unleash）
backup_pg() {
  local name=$1 container=$2 db=$3 user=$4
  log "backing up postgres: $name"
  docker exec "$container" pg_dump -U "$user" "$db" | gzip > "$BACKUP_DIR/${name}-$(date +%H%M).sql.gz"
}

backup_pg gitlab    gitlab           -        gitlab-psql 2>/dev/null || true
backup_pg harbor    harbor-db        registry postgres
backup_pg sonar     sonar-db         sonar    sonar
backup_pg dtrack    dtrack-db        dtrack   dtrack
backup_pg unleash   unleash-db      unleash  unleash

# GitLab 配置 + 备份 artifact
log "gitlab application backup"
docker exec gitlab gitlab-backup create 2>/dev/null || true
docker cp gitlab:/etc/gitlab "$BACKUP_DIR/gitlab-etc" 2>/dev/null || true

# Vault 快照
log "vault raft snapshot"
docker exec vault vault operator raft snapshot save /vault/backup/raft.snap 2>/dev/null || true
docker cp vault:/vault/backup/raft.snap "$BACKUP_DIR/vault-raft.snap" 2>/dev/null || true

# 卷数据快照（非 DB 类）
for vol in sonar-data harbor-data grafana-data loki-data tempo-data unleash-db vault-data; do
  log "backing up volume: $vol"
  docker run --rm -v "$vol:/src:ro" -v "$BACKUP_DIR:/dst" alpine:3.20 \
    tar czf "/dst/${vol}.tar.gz" -C /src . 2>/dev/null || true
done

# 清理旧备份
find /data/backups -maxdepth 1 -type d -mtime +${RETAIN_DAYS} -exec rm -rf {} \;

log "backup done: $BACKUP_DIR"
```

cron 配置：
```cron
# /etc/cron.d/cicd-backup
0 2 * * * root /opt/cicd/backup/backup-all.sh >> /var/log/cicd-backup.log 2>&1
```

### C.2 恢复示例（GitLab）

```bash
# 1. 停止 GitLab
docker-compose stop gitlab

# 2. 恢复配置
docker cp /data/backups/20260803/gitlab-etc gitlab:/etc/gitlab

# 3. 恢复应用数据
docker cp /data/backups/20260803/1700000000_gitlab_backup.tar gitlab:/var/opt/gitlab/backups/
docker exec gitlab gitlab-backup restore BACKUP=1700000000

# 4. 启动并校验
docker-compose start gitlab
docker exec gitlab gitlab-rake gitlab:check SANITIZE=true
```

### C.3 恢复示例（Vault）

```bash
# 1. 启动空 Vault（已 unseal 状态）
docker exec vault vault operator raft snapshot restore /vault/backup/raft.snap
# 2. 重启 + 重 unseal
docker-compose restart vault
```

---

## 附录 D：与主章节引用关系

| 主章节 | 主题 | 本专题对应章节 |
| ------ | ---- | -------------- |
| 02 环境与前置技能 | Docker / Compose 基础 | D1~D15（均使用 docker-compose，前置在 02 章） |
| 02 环境与前置技能 | 镜像仓库基础使用 | D2 Harbor 部署（使用见 S11） |
| 04 核心工具深入 | GitLab CI Runner 部署 | D1 GitLab + Runner 部署与注册 |
| 04 核心工具深入 | CI 凭据管理 | D1.4 凭据管理、D15 Vault |
| 06 容器化与制品管理 | 镜像签名 | D14 Cosign + Rekor |
| 06 容器化与制品管理 | 镜像漏扫 | D2.2 trivy-adapter、D4 Trivy |
| 06 容器化与制品管理 | SBOM 生成与上传 | D5 Dependency-Track |
| 08 安全与质量门禁 | SAST | D3 SonarQube、D8 Bandit/Semgrep |
| 08 安全与质量门禁 | Secret 扫描 | D9 Gitleaks |
| 08 安全与质量门禁 | DAST | D7 OWASP ZAP |
| 08 安全与质量门禁 | 依赖更新与漏洞监控 | D5 Dependency-Track、D6 Renovate |
| 09 监控可观测性与回滚 | 指标 | D10 Prometheus、D11 Pushgateway |
| 09 监控可观测性与回滚 | 日志 | D10 Loki + Promtail |
| 09 监控可观测性与回滚 | 链路追踪 | D12 OTel Collector + Tempo |
| 09 监控可观测性与回滚 | 告警 | D13 Alertmanager |
| 09 监控可观测性与回滚 | Feature Flag | D13 Unleash（与 S7 联动） |

**反向引用**（本专题被主章节引用位置）：
- 02 章 → "部署 GitLab / Harbor 等" 段落链接到本专题 D1/D2
- 04 章 → "Runner 安装" 段落链接到 D1.2
- 06 章 → "镜像签名" 段落链接到 D14
- 08 章 → 各扫描工具部署段落链接到 D3/D7/D8/D9
- 09 章 → "搭建监控栈" 段落链接到 D10/D12/D13

---

## 与 S1~S11 的关系

| 本专题章节 | 关联补充专题 |
| ---------- | ------------ |
| D2 Harbor | S11 包仓库（使用） |
| D4 Trivy | S9 质量扫描集成、S4 供应链 |
| D5 Dependency-Track | S4 SBOM |
| D6 Renovate | S4 依赖更新 |
| D7 ZAP | S9 DAST |
| D8/D9 | S9 SAST/Secret |
| D14 Cosign | S4 供应链签名 |
| D15 Vault | S1 Secret 管理 |

> **使用建议**：S1~S11 学完某专题"是什么/怎么用"后，到本专题找对应"怎么部署"。

---

## 部署后验收清单

- [ ] `docker-compose ps` 所有 `Status` 为 `healthy`
- [ ] GitLab 可登录 + Runner `verify` 成功
- [ ] Harbor 可 push/pull 镜像 + Trivy 扫描可触发
- [ ] SonarQube 默认 quality gate 可触发
- [ ] Dependency-Track 接收 SBOM 后能在 UI 看到组件
- [ ] Gitleaks 对已知 secret 报警
- [ ] Prometheus targets 全绿（除可选）
- [ ] Grafana 添加 datasource 测试通过
- [ ] Loki 可查容器日志
- [ ] Alertmanager webhook 收到测试告警
- [ ] Unleash 可创建 flag 并被 client 读取
- [ ] Vault unsealed + 可读写 secret
- [ ] Cosign 可签名 + 验证镜像
- [ ] OTel Collector 收到测试 trace + Grafana 可查
