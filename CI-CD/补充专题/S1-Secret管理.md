---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S1. Secret 管理专项

> **专题编号：S1**。被引用章节：第 06、08 章。

---

## 一、介绍：为什么 Secret 管理是 CI/CD 的第一安全问题

**问题**：把数据库密码、云密钥直接塞进 CI 变量（即使加密）是企业级反模式。CI 日志泄露、Runner 缓存、第三方 Action 都可能让密钥外泄。一旦泄露，攻击者拿到部署密钥就能横向移动到生产环境。

**真实案例**：
- 2021 年 Codecov 事件：CI 上传脚本被篡改，环境变量（含密钥）被外泄到攻击者服务器，影响数千家企业。
- 2023 年 CircleCI Token 泄露：用户授权的 OAuth Token 被窃，攻击者借此横向访问 GitHub/GCP/AWS。

**核心原则**（4 条铁律）：
1. **密钥永不落盘**到制品或日志
2. **最小权限**：每个流水线只拿必需的密钥
3. **短期凭证优先**：OIDC > 长期 Token
4. **审计可追溯**：谁、何时、用了哪个密钥

---

## 二、方案对比

### 2.1 四类主流方案对照

| 方案 | 适用场景 | 关键能力 | 自建难度 | 2026 推荐度 |
| ---- | -------- | -------- | -------- | ----------- |
| **OIDC 免 Token** | GitHub Actions / GitLab CI → AWS/GCP/Azure | 短期临时凭证，无长期密钥，审计可追溯 | 极低（云厂商原生支持） | ⭐⭐⭐⭐⭐ |
| **HashiCorp Vault** | 通用企业级密钥中心 | 动态密钥、租约自动撤销、身份驱动 | 高（需运维团队） | ⭐⭐⭐⭐ |
| **External Secrets Operator** | K8s 场景 | 从 Vault/AWS SM 同步到 K8s Secret | 中（K8s 已就位的话） | ⭐⭐⭐⭐ |
| **Doppler / 1Password CI** | 中小团队 SaaS | 环境变量统一管理，轮换方便 | 极低（SaaS 即开即用） | ⭐⭐⭐ |

### 2.2 按场景选型决策树

```
是否云原生（K8s + 云厂商）？
├── 是 → 跨云还是单云？
│   ├── 单云 → 云厂商原生（AWS SM / GCP SM / Azure KV）+ IRSA/Workload Identity
│   └── 跨云 → HashiCorp Vault 统一中心
└── 否 → 是否 GitHub Actions / GitLab CI？
    ├── 是 → 优先 OIDC 免 Token（无密钥最安全）
    │       └── OIDC 不支持的场景再用 Doppler/1Password SaaS
    └── 否 → 自建 Vault 或 Doppler SaaS
```

---

## 三、常见工具基本使用

### 3.1 GitHub Actions + AWS OIDC 免 Token（2026 最推荐）

**核心原理**：GitHub 拿自己的 OIDC Token 向 AWS 换临时 STS 凭证，整个过程**没有任何长期密钥**存在 GitHub 里。

**步骤 1：AWS 侧配置 IAM Identity Provider + Role**

```bash
# 创建 OIDC Provider（每个 GitHub 组织只做一次）
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 创建 Role，信任策略限定到具体仓库和分支
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:ref:refs/heads/main"
      }
    }
  }]
}
EOF
aws iam create-role --role-name github-actions-deploy --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name github-actions-deploy --policy-arn arn:aws:iam::123456789012:policy/your-deploy-policy
```

**步骤 2：GitHub Actions workflow 配置**

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

permissions:
  id-token: write   # 关键：允许拿 OIDC token
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: ap-northeast-1
          # 注意：没有 aws-access-key-id / aws-secret-access-key
      - name: Deploy
        run: |
          aws s3 sync ./dist s3://your-bucket/
          aws ecs update-service --cluster prod --service app --force-new-deployment
```

### 3.2 HashiCorp Vault 基础使用

**启动开发模式（仅本地测试）**：
```bash
vault server -dev -dev-root-token-id="root-token"
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root-token'
```

**写入和读取密钥**：
```bash
# 写入：路径风格 KV v2
vault kv put secret/myapp/prod \
  db_user="admin" \
  db_password="$(openssl rand -base64 24)"

# 读取
vault kv get secret/myapp/prod

# 生成动态密钥（用完自动撤销，比静态密钥安全得多）
vault write database/creds/myapp-role
# 返回：username=v-token-app-xxx password=yyy lease_duration=1h
```

**CI 中读取**（GitHub Actions 示例）：
```yaml
- uses: hashicorp/vault-action@v3
  with:
    url: https://vault.example.com
    role: github-actions
    method: jwt        # 用 GitHub OIDC 换 Vault Token，无长期凭证
    secrets: |
      secret/data/myapp/prod db_user | DB_USER ;
      secret/data/myapp/prod db_password | DB_PASSWORD
```

### 3.3 External Secrets Operator（K8s 场景）

**核心思路**：把 Vault/AWS SM 的密钥**同步**到 K8s Secret，应用像用普通 Secret 一样使用，密钥轮换自动同步。

```yaml
# 1. 定义 SecretStore：连接到外部密钥源
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: https://vault.example.com
      path: secret
      auth:
        kubernetes:
          mountPath: kubernetes
          role: my-app-role

---
# 2. 定义 ExternalSecret：声明要拉哪些密钥
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-prod-secrets
spec:
  refreshInterval: 1h           # 1 小时同步一次
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: myapp-prod-secret     # 生成的 K8s Secret 名字
  data:
    - secretKey: DB_USER
      remoteRef:
        key: myapp/prod
        property: db_user
    - secretKey: DB_PASSWORD
      remoteRef:
        key: myapp/prod
        property: db_password
```

---

## 四、CI/CD 中的密钥管理 Checklist

- [ ] 所有密钥不再写死在 `.env` / 配置文件
- [ ] CI Variables 全部 masked + protected（仅受保护分支可用）
- [ ] 跨云访问使用 OIDC，无长期 AccessKey
- [ ] Vault 启用审计日志（`vault audit enable file`）
- [ ] 密钥轮换有自动化（动态密钥优先于静态密钥）
- [ ] 第三方 Action 使用 `secrets:` 时只传必需的，不传 `secrets: inherit`
- [ ] 日志输出前做密钥脱敏（GitHub Actions 自动 mask，自建 Jenkins 需要插件）

---

## 五、与主章节的关联

- 第 06 章（容器化与制品管理）：镜像签名阶段用 OIDC 拿临时凭证
- 第 08 章（安全与质量门禁）：DevSecOps 中密钥管理是核心环节
