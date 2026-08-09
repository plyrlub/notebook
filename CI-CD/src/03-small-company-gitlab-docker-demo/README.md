# 小企业 GitLab CI + Docker 方案 Demo

> 关联章节：[03 章 3.10.4 小企业轻量方案](../../03-工具选型与对比.md#376-3104-小企业轻量方案gitlab-ci--docker1-50-人团队)
> 关联实践：[我的实践记录.md P1（分支即环境）](../../我的实践记录.md)

## 一、目录结构

```
03-small-company-gitlab-docker-demo/
├── .gitlab-ci.yml          # CI/CD 配置（lint/test/build/deploy 全流程）
├── Dockerfile              # 多阶段构建（Python 后端最小镜像）
├── docker-compose.yml      # 部署机上的应用编排（app + nginx + redis）
├── .env.example            # 部署机环境变量模板
├── requirements.txt        # Python 依赖
├── pyproject.toml          # Python 项目元信息
├── app/                    # 应用源码
│   ├── __init__.py
│   └── main.py             # Flask 最小入口（含 /health 端点）
├── config/                 # 多环境配置（挂载到容器）
│   ├── dev.yml
│   ├── test.yml
│   ├── stage.yml
│   └── prod.yml
└── nginx/
    └── nginx.conf          # 反向代理配置
```

## 二、流程图

```
开发流程：
  feature/f1 → merge dev    → 触发 CI → 构建 → 自动部署 dev
             → merge test   → 触发 CI → 构建 → 自动部署 test
             → merge stage  → 触发 CI → 构建 → 手动确认部署 stage
             → merge main   → 触发 CI → 构建 → 手动确认部署 prod
             → 打 tag v1.0.0 → 镜像打 stable tag（审计/回滚用）
```

## 三、关键设计点

### 3.1 制品 = 分支名-短SHA
```
main-abc1234    # main 分支某次 commit 的镜像
dev-def5678     # dev 分支某次 commit 的镜像
v1.0.0          # tag 发版后的稳定 tag
```
回滚 = 切换 IMAGE_TAG 重启容器，秒级。

### 3.2 CI 用 Kaniko 不用 dind
- dind 需要 privileged 模式，安全风险大
- Kaniko 无需特权，更安全更快
- 自动用 `--cache-repo` 做层缓存

### 3.3 部署带健康检查 + 自动回滚
- `docker-compose up` 后等待 60 秒健康检查
- 失败则切回上一个 tag 自动回滚
- 成功才清理旧镜像

### 3.4 四分支对应四环境（兼容 P1 实践）
| 分支 | 环境 | 部署方式 |
| ---- | ---- | -------- |
| dev | dev | 自动 |
| test | test | 自动 |
| stage | stage | 手动 |
| main | prod | 手动 |

## 四、使用步骤

### 4.1 准备 GitLab CE 服务器
```bash
# 安装 GitLab CE（Omnibus）
sudo apt-get install -y curl openssh-server ca-certificates
curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo EXTERNAL_URL="http://gitlab.example.com" apt-get install gitlab-ce

# 启用内置 Container Registry（编辑 /etc/gitlab/gitlab.rb）
# registry_external_url 'https://registry.example.com'
sudo gitlab-ctl reconfigure
```

### 4.2 注册 Runner（docker executor）
```bash
sudo gitlab-runner register
# URL:     https://gitlab.example.com/
# Token:   项目设置 → CI/CD → Runners 获取
# Executor: docker
# Image:    python:3.12-slim（默认）
```

### 4.3 配置 CI/CD 变量
在 GitLab 项目 → Settings → CI/CD → Variables 中配置：

| 变量名 | 说明 |
| ------ | ---- |
| DEV_HOST / DEV_USER | dev 部署机地址 / SSH 用户 |
| TEST_HOST / TEST_USER | test 部署机地址 / SSH 用户 |
| STAGE_HOST / STAGE_USER | stage 部署机地址 / SSH 用户 |
| PROD_HOST / PROD_USER | prod 部署机地址 / SSH 用户 |
| SSH_PRIVATE_KEY | 部署机 SSH 私钥（masked + protected） |
| SSH_KNOWN_HOSTS | `ssh-keyscan` 输出 |
| DB_PASSWORD | 数据库密码（masked） |

### 4.4 部署机准备
```bash
# 在每台部署机上
mkdir -p /opt/app
cd /opt/app
# 拷贝 docker-compose.yml, nginx/, config/ 到这里
cp /path/to/docker-compose.yml .
cp -r /path/to/nginx .
cp -r /path/to/config .

# 配置 .env
cp .env.example .env
vim .env  # 填实际值
```

### 4.5 推送代码触发 CI
```bash
git add . && git commit -m "init project"
git push origin main
# CI 自动触发：lint → test → build
# deploy:prod 需要在 GitLab UI 手动点确认
```

## 五、本地调试

```bash
# 构建镜像
docker build -t myapp:local .

# 启动
APP_ENV=dev IMAGE_TAG=local docker-compose up -d

# 测试
curl http://localhost/health
curl http://localhost/

# 查看日志
docker-compose logs -f app

# 停止
docker-compose down
```

## 六、升级路径

当业务规模扩大（>10 微服务 / 多机房 / 自动扩缩容）时，升级到：

```
GitLab CI + Docker（当前）
    ↓
GitLab CI + K8s + Argo CD（参见 03 章 3.10.2）
```

升级要点：
1. docker-compose.yml → Helm Chart / Kustomize
2. SSH 部署 → Argo CD Pull 模型
3. 单机双副本 → K8s Deployment + HPA
4. 配置文件挂载 → ConfigMap + Secret
