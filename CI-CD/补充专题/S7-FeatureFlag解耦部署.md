---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S7. Feature Flag 与解耦部署

> **专题编号：S7**。被引用章节：第 07 章。

---

## 一、介绍：部署 ≠ 发布

**核心理念**：**部署 ≠ 发布**。
- **部署（Deploy）**：代码放到生产服务器
- **发布（Release）**：让用户看到新功能

Feature Flag 把这两件事解耦：代码先部署但默认关闭，按需逐步打开给部分用户。

**为什么 2026 主流**：
- Trunk-based 开发的基石：没合并完的功能用 Flag 关掉，主干永远可部署
- 紧急回滚秒级：出问题关 Flag，不用回滚代码、不用重新部署
- A/B 测试天然支持：Flag 控制流量比例

---

## 二、Flag 分类与生命周期

### 2.1 四种 Flag 类型

| Flag 类型 | 用途 | 生命周期 | 示例 |
| --------- | ---- | -------- | ---- |
| **Release Flag（发布开关）** | 控制新功能是否对用户开放 | 发布完稳定后删除（2~4 周） | `is_new_checkout_enabled` |
| **Experiment Flag（实验开关）** | A/B 测试、灰度放量 | 实验结论出来后删除 | `10% 用户启用新推荐算法` |
| **Ops Flag（运维开关）** | 限流、降级、开关第三方依赖 | 长期保留 | `payment_provider_use_new_api` |
| **Kill Switch（熔断开关）** | 紧急关闭高风险功能 | 长期保留 | `disable_llm_stream_output` |

### 2.2 生命周期管理（防 Flag 爆炸）

**问题**：100 个 Flag 没人清理 → 代码里全是 `if flag` 分支，复杂度剧增。

**生命周期四阶段**：
```
创建 → 灰度 → 全量 → 清理
                  ↑
            长期 Flag 不走这步
```

**清理机制**：
- 每个 Release Flag 加"清理截止日期"字段：`cleanup_at: 2026-09-01`
- 定期扫描：超过截止日期且全量开启 >2 周的 Flag，自动创建清理 PR
- 强制清理流程：Flag 删除 → 代码里 `if flag` 分支删除 → 单元测试保证不破坏

---

## 三、主流工具对比

**表 7-1：主流 Feature Flag 工具对比**

| 工具 | 类型 | 优势 | 劣势 | 2026 推荐度 |
| ---- | ---- | ---- | ---- | ----------- |
| **Unleash** | 开源自建 | 企业级，API 完善，社区活跃 | 自建需运维 | ⭐⭐⭐⭐⭐ 中大团队 |
| **LaunchDarkly** | SaaS 鼻祖 | 功能最全，集成最深 | 收费贵（按 MAU） | ⭐⭐⭐⭐ 预算充足团队 |
| **Flagsmith** | 开源 SaaS 都有 | 简单易用，支持自建 | 生态不如 Unleash | ⭐⭐⭐ 中小团队 |
| **OpenFeature** | 标准化 SDK | 厂商中立，可切换后端 | 标准化中，2026 仍在发展 | ⭐⭐⭐ 长期投资 |
| **ConfigCat** | SaaS | 简单，免费额度大 | 功能少 | ⭐⭐⭐ 小团队 |
| **自研** | — | 完全可控 | 维护成本高 | ⭐⭐ 不推荐 |

### 3.1 Unleash 基本使用

**部署**（Docker Compose 快速启动）：
```yaml
version: '3'
services:
  unleash-db:
    image: postgres:15
    environment:
      POSTGRES_DB: unleash
      POSTGRES_USER: unleash
      POSTGRES_PASSWORD: pass
  unleash:
    image: unleashorg/unleash-server:5
    ports: ["4242:4242"]
    environment:
      DATABASE_URL: postgres://unleash:pass@unleash-db/unleash
      INIT_ADMIN_API_TOKENS: "*:*.unleash-token"
    depends_on: [unleash-db]
```

**应用集成**（Python SDK 示例）：
```python
from unleash import UnleashClient

client = UnleashClient(
    url="https://unleash.example.com/api",
    app_name="my-python-service",
    custom_headers={"Authorization": "*:*.unleash-token"},
)
client.initialize_client()

if client.is_enabled("new_checkout_flow", context={"user_id": "user-123"}):
    return render_new_checkout()
else:
    return render_old_checkout()
```

**渐进式策略**：
- 用户 ID Hash：`hash(user_id) % 100 < percentage` → 稳定灰度
- 用户列表：指定白名单用户先用
- 环境策略：dev 全开、staging 10%、prod 1% → 10% → 100%

### 3.2 LaunchDarkly 基本使用

**应用集成**（Java SDK 示例）：
```java
import com.launchdarkly.sdk.LDUser;
import com.launchdarkly.sdk.server.LDClient;

LDClient client = new LDClient("sdk-key-xxx");
LDUser user = new LDUser.Builder("user-123")
    .email("user@example.com")
    .build();

boolean showNewFeature = client.boolVariation("new-checkout-flow", user, false);
if (showNewFeature) {
    return renderNewCheckout();
}
```

---

## 四、Flag 工程化三大坑

### 4.1 Flag 爆炸

**症状**：代码里 100+ 个 Flag，没人知道哪些还在用。

**解法**：
- Flag 数量设上限（单仓库活跃 Flag 不超过 20 个）
- Flag 中心做依赖声明：哪个 Flag 用在哪些代码路径
- 自动清理：超过截止日期的 Flag 自动创建删除 PR

### 4.2 组合爆炸

**症状**：N 个 Flag 有 2^N 种状态，不可能全测。

**解法**：
- 限制同时活跃的 Flag 数（避免 N>5）
- 测试时只测"全开"和"全关"两种状态
- 复杂功能用 1 个 Flag 控制，不要内部又拆多个

### 4.3 配置泄露影响生产

**症状**：Flag 配置写死在代码仓库里，dev 改了影响 prod。

**解法**：
- Flag 配置与代码解耦，存独立 Flag 中心
- 后端服务通过 SDK 拉取，本地缓存 + Webhook 更新
- 不同环境（dev/test/stage/prod）的 Flag 状态独立配置

---

## 五、典型流程

```
1. 代码合并即部署（CI/CD 自动化）
2. Flag 默认 OFF，生产无影响
3. 灰度开 1% → 10% → 100%
4. 出问题秒级关闭，无需回滚代码
5. 稳定后删除 Flag
```

**与 Trunk-based 开发的关系**：Feature Flag 是 Trunk-based 的基石——没合并完的功能用 Flag 关掉，主干永远可部署。

---

## 六、与主章节的关联

- 第 07 章（部署发布策略）：Feature Flag 是解耦部署与发布的核心机制
- 第 02 章（Git 工作流）：Trunk-based 必须配 Flag
