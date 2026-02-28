# Docker 配置（阿里云服务器）

## 镜像加速器（可选）

阿里云 ECS 上拉取 Docker Hub 镜像（如 `python:3.12-slim`、`node:20-alpine`）较慢时，可配置 Docker 使用阿里云镜像加速器。

1. 登录 [容器镜像服务控制台](https://cr.console.aliyun.com) → **镜像工具** → **镜像加速器**，复制你的加速器地址（形如 `https://xxxx.mirror.aliyuncs.com`）。
2. 在示例中把 `<你的加速器前缀>` 替换为控制台里显示的前缀，保存为 `/etc/docker/daemon.json`（若已有该文件，只合并添加 `registry-mirrors` 等字段）：

```bash
# 示例：从本仓库复制到服务器后编辑
sudo cp /opt/Sierac-tm/cursor-admin/docker/daemon-aliyun.json.example /etc/docker/daemon.json
sudo nano /etc/docker/daemon.json   # 替换 <你的加速器前缀>
sudo systemctl daemon-reload && sudo systemctl restart docker
```

3. 验证：`docker info` 中应出现 **Registry Mirrors** 为上述地址。

说明：2024 年 7 月起，阿里云镜像加速仅限在具备公网访问的阿里云产品上使用，详见阿里云文档。
