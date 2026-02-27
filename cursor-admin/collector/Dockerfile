FROM python:3.12-slim

# Git 用于采集服务定时 clone/fetch 项目仓库（git_collector）
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# 国内服务器构建可传 PIP_INDEX_URL，如: --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir --timeout 120 \
    ${PIP_INDEX_URL:+--index-url ${PIP_INDEX_URL}} \
    poetry \
    && poetry config virtualenvs.create false \
    && if [ -n "${PIP_INDEX_URL}" ]; then poetry config repositories.default "${PIP_INDEX_URL}"; fi

WORKDIR /app

COPY collector/pyproject.toml collector/poetry.lock ./
RUN poetry install --only main --no-interaction --no-root

COPY collector/ ./
COPY db/ /db/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
