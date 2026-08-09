---
tags: [CI/CD, 补充专题]
创建日期: 2026-08-10
状态: ✅ 已归档（01-学习/DevOps/CI-CD/补充专题）
归属: 01-学习/DevOps/CI-CD/补充专题
---

# S8. Lua 场景的 CI/CD

> **专题编号：S8**。被引用章节：第 05 章。

---

## 一、介绍：中文资料最少的 CI/CD 场景

**背景**：你的技术栈含 Lua（OpenResty / Nginx / 游戏脚本），但中文 CI/CD 资料几乎不覆盖，需要专门补。

**Lua 在 CI/CD 中的三大典型场景**：
1. **OpenResty / Nginx 模块开发**：网关、API 中间件
2. **LuaRocks 包发布**：公共 Lua 库或私有企业包
3. **游戏服务器 Lua 脚本热更**：游戏逻辑、配置脚本

---

## 二、OpenResty / Nginx 模块 CI/CD

### 2.1 项目结构

```
my-gateway/
├── nginx/
│   ├── conf/
│   │   ├── nginx.conf
│   │   └── upstreams/
│   ├── lua/
│   │   ├── routes/
│   │   │   └── auth.lua
│   │   ├── middleware/
│   │   │   └── rate_limit.lua
│   │   └── lib/
│   │       └── http_client.lua
│   └── logs/
├── spec/                    # 测试
│   ├── auth_spec.lua
│   └── rate_limit_spec.lua
├── rockspec                 # LuaRocks 包描述
└── .github/workflows/ci.yml
```

### 2.2 CI 流水线（GitHub Actions）

```yaml
name: OpenResty CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    container: openresty/openresty:1.25.3.1-0-jammy
    steps:
      - uses: actions/checkout@v4
      - name: Install luacheck
        run: luarocks install luacheck
      - name: Lint
        run: luacheck nginx/lua/ --codes --ranges

  unit-test:
    runs-on: ubuntu-latest
    container: openresty/openresty:1.25.3.1-0-jammy
    steps:
      - uses: actions/checkout@v4
      - name: Install busted
        run: luarocks install busted
      - name: Unit test
        run: busted spec/

  integration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start OpenResty
        run: |
          docker run -d --name gateway \
            -v $(pwd)/nginx/conf:/usr/local/openresty/nginx/conf \
            -v $(pwd)/nginx/lua:/usr/local/openresty/nginx/lua \
            -p 8080:8080 \
            openresty/openresty:1.25.3.1-0-jammy
      - name: Wait for ready
        run: |
          for i in {1..30}; do
            curl -sf http://localhost:8080/health && break
            sleep 1
          done
      - name: Run Test::Nginx::Socket tests
        run: |
          apt-get update && apt-get install -y cpanminus libtest-nginx-perl
          prove -r t/

  docker-build:
    needs: [lint, unit-test, integration-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t ghcr.io/myorg/my-gateway:${{ github.sha }} .
      - name: Trivy scan
        run: |
          curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/install.sh | sh
          trivy image --exit-code 1 --severity CRITICAL,HIGH ghcr.io/myorg/my-gateway:${{ github.sha }}
      - name: Push
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/myorg/my-gateway:${{ github.sha }}
```

### 2.3 单元测试（busted）

```lua
-- spec/auth_spec.lua
local auth = require "routes.auth"

describe("auth middleware", function()
  before_each(function()
    -- mock ngx.var
    _G.ngx = { var = { http_authorization = "" } }
  end)

  it("rejects request without token", function()
    _G.ngx.var.http_authorization = ""
    local ok, err = auth.validate()
    assert.is_false(ok)
    assert.equals("missing token", err)
  end)

  it("accepts valid token", function()
    _G.ngx.var.http_authorization = "Bearer valid-token"
    local ok = auth.validate()
    assert.is_true(ok)
  end)
end)
```

### 2.4 集成测试（Test::Nginx::Socket）

```perl
# t/auth.t
use Test::Nginx::Socket 'no_plan';

run_tests();

__DATA__

=== TEST 1: reject without token
--- config
location /api {
  access_by_lua_block {
    local auth = require "routes.auth"
    auth.validate()
  }
  content_by_lua_block { ngx.say("ok") }
}
--- request
GET /api
--- error_code: 401
--- response_body_like: missing token

=== TEST 2: accept with token
--- request
GET /api
--- more_headers
Authorization: Bearer valid-token
--- error_code: 200
```

---

## 三、LuaRocks 包发布

### 3.1 rockspec 文件

```lua
-- mymodule-1.0.0-1.rockspec
package = "mymodule"
version = "1.0.0-1"

source = {
  url = "git://github.com/myorg/mymodule.git",
  tag = "v1.0.0",
}

description = {
  summary = "My awesome Lua module",
  homepage = "https://github.com/myorg/mymodule",
  license = "MIT",
}

dependencies = {
  "lua-cjson >= 2.1.0",
  "lua-resty-http >= 0.16",
}

build = {
  type = "builtin",
  modules = {
    ["mymodule"] = "src/mymodule.lua",
    ["mymodule.utils"] = "src/utils.lua",
  },
}
```

### 3.2 CI 自动发布（GitLab CI）

```yaml
# .gitlab-ci.yml
stages:
  - test
  - publish

test:
  stage: test
  image: openresty/openresty:1.25.3.1-0-jammy
  script:
    - luarocks install busted
    - busted spec/
    - luarocks lint *.rockspec

publish:
  stage: publish
  image: openresty/openresty:1.25.3.1-0-jammy
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/   # 仅 Tag 触发
  script:
    - |
      # 从 Tag 提取版本号
      VERSION=${CI_COMMIT_TAG#v}
      sed -i "s/version = \".*\"/version = \"${VERSION}-1\"/" mymodule-*.rockspec
    - luarocks install lua-rocks-cli
    - luarocks upload --api-key=$LUAROCKS_API_KEY mymodule-${VERSION}-1.rockspec
  only:
    - tags
```

---

## 四、游戏服务器 Lua 脚本热更

### 4.1 场景特点

游戏服务器 Lua 脚本热更要求：
- 不停服更新游戏逻辑
- 灰度热更：先在 GM 服验证，再推全服
- 热更脚本不能污染全局环境

### 4.2 CI 校验热更脚本

```lua
-- 热更脚本沙箱校验
local function validate_hotfix(script_path)
  local code = assert(io.open(script_path)):read("*a")

  -- 1. 禁止引用未声明的全局变量（防污染环境）
  local f = loadstring(code)
  setfenv(f, setmetatable({}, {
    __index = function(_, k)
      error("hotfix 不允许访问全局变量: " .. k, 2)
    end,
  }))

  -- 2. 禁止 require 新模块（防依赖缺失）
  if code:match("require%s+[\"']") then
    error("hotfix 不允许 require 新模块")
  end

  -- 3. 必须有 rollback 函数（出问题能回滚）
  if not code:match("function rollback") then
    error("hotfix 必须定义 rollback 函数")
  end
end

return validate_hotfix
```

### 4.3 CI 集成

```yaml
hotfix-check:
  stage: test
  image: openresty/openresty:1.25.3.1-0-jammy
  script:
    - lua scripts/validate_hotfix.lua hotfixes/*.lua
    - lua -e "require('busted').run('spec/hotfix_spec.lua')"
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes: [hotfixes/*]
```

### 4.4 灰度热更流程

```
1. 开发：写 hotfix 脚本，提交 PR
2. CI：跑沙箱校验 + 单元测试
3. 合并到 main：CI 构建 hotfix 包，推到内部 LuaRocks
4. GM 服拉取热更：在 GM 服测试
5. 全服推送：通过 GM 服验证后，批量推到所有游戏服
```

---

## 五、常见坑

1. **LuaJIT 与标准 Lua 行为差异**：CI 必须两边都测（5.1/5.3/5.4/LuaJIT 矩阵测试）
2. **`package.path` 在不同容器里不一致**：CI 显式设置 `LUA_PATH`
3. **C 扩展模块（`.so`）要按目标平台交叉编译**：amd64/arm64 各构建一份
4. **OpenResty 自带 LuaJIT，不是标准 Lua 5.1**：用 `resty` CLI 跑测试，不要用 `lua` CLI
5. **luarocks 默认装到 /usr/local，权限问题**：CI 用 `--local` 装到用户目录

---

## 六、多 Lua 版本矩阵测试

```yaml
strategy:
  matrix:
    lua_version: ['5.1', '5.3', '5.4', 'luajit']
steps:
  - uses: actions/checkout@v4
  - name: Setup Lua
    uses: leafo/gh-actions-lua@v10
    with:
      luaVersion: ${{ matrix.lua_version }}
  - name: Install luarocks
    uses: leafo/gh-actions-luarocks@v4
  - run: luarocks install busted
  - run: busted spec/
```

---

## 七、与主章节的关联

- 第 05 章（构建测试）：Lua 项目的构建测试特殊点
