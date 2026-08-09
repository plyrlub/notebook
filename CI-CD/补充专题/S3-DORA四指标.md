---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S3. DORA 四指标

> **专题编号：S3**。被引用章节：第 09、10 章。

---

## 一、介绍：CI/CD 成熟度的国际通用语言

**背景**：Google DORA（DevOps Research and Assessment）团队提出的衡量软件交付效能的四大指标，是 CI/CD 成熟度的国际通用语言，面试常考。

**为何重要**：CI/CD 不是"装上工具就完了"，而是要能用数据证明"我们交付更快更稳了"。DORA 把 CI/CD 从工程实践提升到**可度量的组织能力**。

**DORA 四级别**（2023 更新版）：
- **Elite（精英级）**：按需多次/天部署，<1 小时前置时间，<5% 失败率，<1 小时恢复
- **High（高效）**：每日~每周部署，1 天~1 周前置，<10% 失败率，<1 天恢复
- **Medium（中等）**：每周~每月部署，1 周~1 月前置，<15% 失败率，<1 天恢复
- **Low（低效）**：每月~半年部署，>1 月前置，>15% 失败率，>6 月恢复

---

## 二、四指标详解

### 2.1 指标对照表

| 指标 | 含义 | 计算方式 | Elite 基线 | Low 基线 |
| ---- | ---- | -------- | ---------- | -------- |
| **部署频率** (Deployment Frequency) | 多久部署一次到生产 | 时间窗口内的部署次数 / 时间 | 多次/天 | <1 次/6 月 |
| **变更前置时间** (Lead Time for Changes) | 代码提交到生产的时间 | prod 部署时间 - commit 时间 | <1 小时 | >6 月 |
| **变更失败率** (Change Failure Rate) | 部署后导致故障的比例 | 故障部署数 / 总部署数 | <5% | >60% |
| **平均恢复时间** (MTTR) | 故障到恢复的时间 | 故障恢复时间 - 故障开始时间 | <1 小时 | >6 月 |

### 2.2 前两个是"速度指标"，后两个是"稳定性指标"

- **速度指标**（部署频率 + 前置时间）：衡量"快不快"
- **稳定性指标**（失败率 + MTTR）：衡量"稳不稳"

**关键认知**：DORA 研究表明，**速度和稳定性不矛盾**——Elite 团队既快又稳，Low 团队又慢又容易出事。这打破了很多管理者的"求稳就慢"认知。

---

## 三、各指标的采集方法

### 3.1 部署频率（Deployment Frequency）

**采集点**：每次成功部署到生产环境计 1 次。

**实现方式**：
```python
# CI/CD 流水线 Deploy Stage 成功后埋点
import requests
from datetime import datetime

def record_deployment(env: str, version: str):
    """部署成功后调用，记录到 metrics 系统"""
    requests.post("https://metrics.example.com/api/deployment", json={
        "env": env,
        "version": version,
        "timestamp": datetime.utcnow().isoformat(),
        "deployer": "ci-bot",
    })
```

**统计方式**：
- 按天统计：`deployment_count_per_day`，Elite 阈值 ≥ 1
- 滚动 30 天平均：避免某天突发部署拉高指标

### 3.2 变更前置时间（Lead Time for Changes）

**采集点**：commit 时间（git log） → prod 部署时间。

**实现方式**：
```python
import subprocess
from datetime import datetime

def get_lead_time(commit_sha: str, deploy_time: datetime) -> int:
    """返回 commit 到部署的分钟数"""
    commit_time_str = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", commit_sha],
        text=True
    ).strip()
    commit_time = datetime.fromisoformat(commit_time_str.replace("Z", "+00:00"))
    return int((deploy_time - commit_time).total_seconds() / 60)
```

**注意点**：
- 一个部署可能包含多个 commit，取**最早未部署 commit** 到本次部署的时间
- 测的是"代码合主干到生产"的时间，不含"PR 开发时间"（那是另一个指标 Cycle Time）

### 3.3 变更失败率（Change Failure Rate）

**采集点**：导致故障的部署 / 总部署数。

**故障判定**（避免主观）：
- 触发回滚的部署
- 部署后 1 小时内告警 >阈值
- 部署后人工确认的 P0/P1 故障

**统计方式**：
- 滑动 30 天窗口：`failed_deployments_30d / total_deployments_30d`
- Elite 阈值 <5%

### 3.4 平均恢复时间（MTTR）

**采集点**：故障开始 → 故障恢复。

**故障开始**：告警系统第一次收到告警
**故障恢复**：服务健康检查连续 N 次通过（通常 3 次，间隔 30s）

```python
# 用 Prometheus Alertmanager + 自定义恢复检测
mttr = alert_resolved_timestamp - alert_fired_timestamp
```

**统计方式**：
- 滑动 30 天中位数（不是平均数，避免长尾拉偏）
- Elite 阈值 <1 小时

---

## 四、DORA 仪表盘实现

### 4.1 用 Grafana 展示 DORA

**数据源**：Prometheus（部署频率、MTTR）+ 自定义 API（前置时间、失败率）

**4 个核心 Panel**：

| Panel | 查询 | 展示形式 |
| ----- | ---- | -------- |
| 部署频率 | `rate(deployment_total{env="prod"}[1d])` | 折线图，按天聚合 |
| 变更前置时间 | `histogram_quantile(0.5, lead_time_minutes_bucket)` | 单值 + 趋势 |
| 变更失败率 | `rate(deployment_failed_total[30d]) / rate(deployment_total[30d])` | 仪表盘 |
| MTTR | `histogram_quantile(0.5, mttr_minutes_bucket)` | 单值 + 趋势 |

### 4.2 开源工具推荐

| 工具 | 特点 | 适用 |
| ---- | ---- | ---- |
| **DX Flow** | DORA 创始团队自家产品 | 商业方案，最专业 |
| **LinearB** | 商业 SaaS，与 GitHub/Jira 深度集成 | 中大型团队 |
| **DevLake** | Apache 孵化，开源自建 | 自建团队 |
| **Grafana + Prometheus** | 自己组装 | 已有可观测性基础设施的团队 |

---

## 五、从 Low 到 Elite 的提升路径

### 5.1 Low → Medium（最容易，3~6 个月）

- **加 CI**：所有 PR 必须过 Lint + 单元测试
- **分支策略**：从 GitFlow 简化到 GitHub Flow
- **自动化部署**：dev/test 环境自动部署，prod 人工按按钮

### 5.2 Medium → High（6~12 个月）

- **Trunk-based + Feature Flag**：解锁"小步快跑"
- **prod 自动部署**：去掉人工按钮，测试充分后自动上
- **可观测性**：Prometheus + Grafana + 告警系统

### 5.3 High → Elite（12+ 个月）

- **渐进式发布**：金丝雀 / 蓝绿自动切流
- **自动回滚**：异常指标自动触发回滚
- **测试金字塔**：单元测试覆盖率 >80%，E2E 充分且稳定
- **数据库零停机迁移**：Expand-Contract 模式（见 S6）

---

## 六、与主章节的关联

- 第 09 章（监控回滚）：MTTR 和失败率的数据来源
- 第 10 章（工程化度量）：DORA 是核心度量体系
