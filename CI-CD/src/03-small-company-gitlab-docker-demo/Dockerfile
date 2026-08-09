# 多阶段构建：Python 后端最小镜像
# 适合小企业 GitLab CI + Docker 方案的构建产物
# 修改 app/ 目录结构以适配你的实际项目

# ============== Builder Stage ==============
FROM python:3.12-slim AS builder

WORKDIR /build

# 先拷依赖文件，利用 Docker layer cache
COPY pyproject.toml requirements.txt ./

# 安装依赖到独立目录，便于后面拷贝
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 拷源码
COPY app/ ./app/

# ============== Final Stage ==============
FROM python:3.12-slim AS final

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# 从 builder 拷依赖
COPY --from=builder /install /usr/local

# 拷源码
COPY --from=builder /build/app /app/app

# 切非 root 用户
USER appuser

# 嵌入制品元数据（参见 S10.3：制品与 Git Commit 的映射）
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown
ARG VERSION=unknown
LABEL org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8080/health', timeout=3)" || exit 1

CMD ["python", "-m", "app.main"]
