/**
 * E2E: 模拟真实用户操作 — 侧栏导航、项目新建弹窗（含 GitLab/GitHub 选项）、关键页面可见
 * 运行: E2E_BASE_URL=http://8.130.50.168:3000 npm run e2e
 */
import { test, expect } from '@playwright/test'

test.describe('真实用户流程', () => {
  test('打开管理端后依次进入各主导航并看到预期内容', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Cursor Admin/i)

    // 用量总览（首页）
    await expect(page.getByRole('link', { name: '用量总览' })).toBeVisible()
    await page.getByRole('link', { name: '用量总览' }).click()
    await expect(page).toHaveURL(/\/$|\/\/[^/]+$/)

    // 项目
    await page.getByRole('link', { name: '项目' }).click()
    await expect(page).toHaveURL(/\/projects/)
    await expect(page.getByRole('heading', { name: /项目管理/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /新建项目/i })).toBeVisible()

    // 我的项目
    await page.getByRole('link', { name: '我的项目' }).click()
    await expect(page).toHaveURL(/\/my-projects/)

    // 我的贡献
    await page.getByRole('link', { name: '我的贡献' }).click()
    await expect(page).toHaveURL(/\/my-contributions/)

    // 项目参与
    await page.getByRole('link', { name: '项目参与' }).click()
    await expect(page).toHaveURL(/\/workspace/)

    // 排行榜
    await page.getByRole('link', { name: '排行榜' }).click()
    await expect(page).toHaveURL(/\/leaderboard/)

    // 激励规则
    await page.getByRole('link', { name: '激励规则' }).click()
    await expect(page).toHaveURL(/\/incentive-rules/)
  })

  test('项目页点击新建项目，弹窗中可见关联已有仓库 / GitLab / GitHub 三种方式', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /新建项目/i }).click()

    await expect(page.getByText('关联已有仓库')).toBeVisible()
    await expect(page.getByText('自动创建（GitLab）')).toBeVisible()
    await expect(page.getByText('自动创建（GitHub）')).toBeVisible()
    await expect(page.getByLabel(/项目名称/)).toBeVisible()
    await expect(page.getByLabel(/工作目录规则/)).toBeVisible()

    await page.getByRole('button', { name: '取消' }).click()
    await expect(page.getByText('关联已有仓库')).not.toBeVisible()
  })

  test('新建项目弹窗中选择自动创建（GitHub）时显示仓库路径输入框', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /新建项目/i }).click()

    await page.getByText('自动创建（GitHub）').click()
    await expect(page.getByLabel(/仓库路径/)).toBeVisible()
    await expect(page.getByPlaceholder(/如 sierac-tm/)).toBeVisible()

    await page.getByRole('button', { name: '取消' }).click()
  })
})
