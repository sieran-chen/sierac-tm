# E2E 测试（真实用户流程）

模拟真实用户：打开管理端 → 侧栏导航（用量总览、项目、我的项目、我的贡献、项目参与、排行榜、激励规则）→ 项目页点击「新建项目」→ 弹窗中可见「关联已有仓库」「自动创建（GitLab）」「自动创建（GitHub）」→ 选择 GitHub 时显示仓库路径输入框。

## 运行

```bash
cd cursor-admin/e2e
npm install
npx playwright install chromium
```

对**已部署环境**（确保本机可访问）：

```bash
E2E_BASE_URL=http://8.130.50.168:3000 npm run e2e
```

对**本地开发**（先在一个终端运行 `cd cursor-admin/web && npm run dev`）：

```bash
E2E_BASE_URL=http://localhost:5173 npm run e2e
```

无 `E2E_BASE_URL` 时默认使用 `http://localhost:3000`（如 docker compose 映射的 web 端口）。

## 说明

- 测试不登录、不填表单提交，仅验证主导航与新建项目弹窗的选项和控件可见。
- 若远程地址不可达（超时），请在能访问该地址的环境运行，或改用本地 URL。
