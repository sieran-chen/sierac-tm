# 罐装机数字孪生 (sierac-twin)

## 模型 001

- 当前已从仓库根目录 **3d/** 下的 GLB 复制到 **public/models/001.glb**，刷新页面即可加载（约 70MB，首次加载请稍候）。
- 若你更新了 3d 里的模型，在 `sierac-twin` 目录执行：**`npm run sync-model`**，会重新复制到 public。
- 查看模型节点名以配置部件映射：`python scripts/read_glb_nodes.py public/models/001.glb`

## 本地运行

1. **后端**（在 `server` 目录）：
   ```bash
   cd sierac-twin/server
   python -m uvicorn main:app --host 127.0.0.1 --port 8100 --reload
   ```

2. **前端**（在 `sierac-twin` 目录）：
   ```bash
   cd sierac-twin
   npm run dev
   ```

3. 浏览器打开 **http://localhost:3001**（若 3001 被占用，Vite 会使用 3002 等端口，见终端输出）。

前端通过 Vite 代理将 `/api` 请求转发到后端 8100 端口。
