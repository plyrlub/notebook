---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S4. 供应链安全（SBOM）

> **专题编号：S4**。被引用章节：第 06、08 章。

---

## 一、介绍：为什么供应链安全已成合规刚需

**问题**：Log4Shell、xz-utils 后门事件后，软件供应链安全已成合规刚需。欧盟 EU CRA（网络弹性法案）2026 落地，要求软件供应商必须能证明组件来源。

**核心术语**：
- **SBOM（Software Bill of Materials）**：软件物料清单，记录"这个制品里包含哪些组件、什么版本、什么来源"
- **SLSA（Supply-chain Levels for Software Artifacts）**：Google 提出的构建来源可追溯框架，分 4 级
- **Cosign + Sigstore**：镜像签名工具栈，2026 事实标准
- **in-toto**：证明构建过程每个步骤的元数据格式

---

## 二、核心实践对照

| 实践 | 解决什么问题 | 关键工具 | 2026 状态 |
| ---- | ------------ | -------- | --------- |
| **生成 SBOM** | 知道制品里有什么 | Syft / CycloneDX CLI / `mvn cyclonedx:makeBom` | ⭐⭐⭐⭐⭐ 主流 |
| **镜像签名** | 证明镜像是可信来源构建的 | Cosign + Sigstore | ⭐⭐⭐⭐⭐ 主流 |
| **可验证构建** | 证明构建过程没被篡改 | SLSA Provenance + in-toto | ⭐⭐⭐ 兴起 |
| **策略门禁** | 部署前验证签名 | OPA / Cosign Verify | ⭐⭐⭐⭐ 推广中 |

---

## 三、SBOM 详解

### 3.1 SBOM 格式对比

| 格式 | 主导方 | 特点 | 适用场景 |
| ---- | ------ | ---- | -------- |
| **CycloneDX** | OWASP | JSON/XML，专为安全设计，支持镜像/包/固件 | ⭐⭐⭐⭐⭐ 首选 |
| **SPDX** | Linux Foundation | JSON/RDF/Tag-Value，更偏许可证合规 | 法律合规场景 |
| **SWID** | ISO | 标签格式，偏企业资产盘点 | 较少在 CI/CD 用 |

### 3.2 用 Syft 生成 SBOM（推荐工具）

```bash
# 安装
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# 扫镜像生成 SBOM（CycloneDX 格式）
syft myapp:v1.2.0 -o cyclonedx-json > sbom.json

# 扫文件系统生成 SBOM
syft dir:./src -o cyclonedx-json > sbom-src.json

# 扫 Git 仓库
syft https://github.com/myorg/myrepo -o cyclonedx-json > sbom.json
```

**SBOM 内容示例**：
```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "components": [
    {
      "type": "library",
      "name": "requests",
      "version": "2.31.0",
      "purl": "pkg:pypi/requests@2.31.0",
      "licenses": [{"license": {"id": "Apache-2.0"}}]
    },
    {
      "type": "library",
      "name": "log4j-core",
      "version": "2.17.1",
      "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.17.1"
    }
  ]
}
```

### 3.3 在 Maven 中生成 SBOM（Java 项目）

```xml
<!-- pom.xml -->
<plugin>
  <groupId>org.cyclonedx</groupId>
  <artifactId>cyclonedx-maven-plugin</artifactId>
  <version>2.8.0</version>
  <executions>
    <execution>
      <phase>package</phase>
      <goals><goal>makeBom</goal></goals>
    </execution>
  </executions>
</plugin>
```

`mvn package` 后自动生成 `target/bom.json` 和 `target/bom.xml`。

---

## 四、镜像签名（Cosign + Sigstore）

### 4.1 为什么用 Cosign

| 方案 | 优势 | 劣势 |
| ---- | ---- | ---- |
| **Cosign + Sigstore** | 2026 事实标准，免费，Keyless 模式（用 OIDC） | 早期（2021 才发布） |
| **Notation + Notary v2** | OCI 标准化更早 | 工具链相对复杂 |
| **Docker Content Trust** | 内置 | 已被社区边缘化，不支持 Keyless |

### 4.2 Cosign 三种签名模式

**模式 1：Key 签名（自管密钥）**
```bash
# 生成密钥对
cosign generate-key-pair
# 用私钥签名
cosign sign --key cosign.key myregistry/myapp:v1.2.0
# 用公钥验证
cosign verify --key cosign.pub myregistry/myapp:v1.2.0
```

**模式 2：Keyless 签名（用 OIDC，2026 推荐）**
```bash
# CI 中用 OIDC Token 签名，无密钥管理
cosign sign --yes \
  --identity-token="$OIDC_TOKEN" \
  myregistry/myapp:v1.2.0

# 验证：检查签名者是不是预期的 GitHub 仓库
cosign verify myregistry/myapp:v1.2.0 \
  --certificate-identity-regexp="https://github.com/myorg/myrepo/.+" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com"
```

**模式 3：KMS 签名（企业级，密钥在 KMS 里）**
```bash
cosign sign --key awskms:///alias/my-signing-key myregistry/myapp:v1.2.0
```

### 4.3 在 CI 中签名 + 验证（GitHub Actions 完整示例）

```yaml
name: Build, Sign, Verify
on:
  push:
    tags: ['v*']

permissions:
  contents: read
  id-token: write    # 关键：拿 OIDC token
  packages: write

jobs:
  build-sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t ghcr.io/myorg/myapp:${{ github.ref_name }} .

      - name: Generate SBOM
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          syft ghcr.io/myorg/myapp:${{ github.ref_name }} -o cyclonedx-json > sbom.json

      - name: Sign image with Cosign (Keyless)
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes ghcr.io/myorg/myapp:${{ github.ref_name }}

      - name: Attach SBOM to image
        run: |
          cosign attach sbom --sbom sbom.json ghcr.io/myorg/myapp:${{ github.ref_name }}
          cosign sign --yes --attachment sbom ghcr.io/myorg/myapp:${{ github.ref_name }}

      - name: Push image
        run: docker push ghcr.io/myorg/myapp:${{ github.ref_name }}
```

### 4.4 部署前验证签名（K8s 准入控制）

用 **Kyverno** 或 **OPA Gatekeeper** 在部署前验证镜像签名：

```yaml
# Kyverno 策略：未通过 Cosign 签名验证的镜像禁止部署
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-cosign-signature
      match:
        resources:
          kinds: [Pod]
      verifyImages:
        - imageReferences:
            - "ghcr.io/myorg/*"
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/myorg/*"
                    issuer: "https://token.actions.githubusercontent.com"
```

---

## 五、SLSA 框架

### 5.1 SLSA 四级

| 级别 | 要求 | 现实状态 |
| ---- | ---- | -------- |
| **L1** | 构建过程有文档 | 90% 团队能做到 |
| **L2** | 构建在托管平台跑，有构建出处 | 60% 团队能做 |
| **L3** | 构建过程不可篡改（隔离构建） | 20% 团队能做 |
| **L4** | 双人审核 + 可复现构建 | <5% 团队 |

### 5.2 在 GitHub Actions 中生成 SLSA Provenance

```yaml
- uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.0.0
  with:
    image: ghcr.io/myorg/myapp
    digest: ${{ steps.build.outputs.digest }}
    registry-username: ${{ github.actor }}
  secrets:
    registry-password: ${{ secrets.GITHUB_TOKEN }}
```

会自动生成一个 `slsa-provenance.intoto.jsonl`，附加到镜像作为 attestation。

---

## 六、供应链安全 Checklist

- [ ] 所有镜像构建后用 Cosign 签名（Keyless 优先）
- [ ] 镜像生成 SBOM 并 attach 到镜像
- [ ] 第三方 Action 锁 SHA（S5 详述）
- [ ] 部署前用 Kyverno / OPA 验证签名
- [ ] 依赖漏洞用 Trivy / Grype 扫描，高危阻断
- [ ] 关键制品走 SLSA L3（隔离构建）

---

## 七、与主章节的关联

- 第 06 章（容器化与制品管理）：镜像签名 + SBOM 是镜像推送前必做
- 第 08 章（安全与质量门禁）：供应链安全是 DevSecOps 的核心环节
