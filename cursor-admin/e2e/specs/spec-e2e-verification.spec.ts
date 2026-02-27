/**
 * E2E 与 spec 对照：仅验证可在浏览器内完成的 UI 步骤
 * 参照：cursor-admin-projects/E2E_VERIFICATION.md、cursor-admin-incentives/E2E_VERIFICATION.md
 * 运行：E2E_BASE_URL=http://8.130.50.168:3000 npm run e2e -- spec-e2e-verification
 */
import { test, expect } from '@playwright/test'

test.describe('Spec E2E：立项与治理（管理端 UI）', () => {
  test('步骤1 立项 - 新建项目弹窗含自动创建 GitLab/GitHub 与关联已有仓库', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /新建项目/i }).click()
    await expect(page.getByText('关联已有仓库')).toBeVisible()
    await expect(page.getByText('自动创建（GitLab）')).toBeVisible()
    await expect(page.getByText('自动创建（GitHub）')).toBeVisible()
    await expect(page.getByLabel(/项目名称/)).toBeVisible()
    await expect(page.getByLabel(/工作目录规则/)).toBeVisible()
    await page.getByRole('button', { name: '取消' }).click()
  })

  test('步骤1 关联已有仓库 - 必填已有仓库地址，有说明文案', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /新建项目/i }).click()
    await page.getByText('关联已有仓库').first().click()
    await expect(page.getByText(/已有仓库地址/)).toBeVisible()
    await expect(page.getByText(/保存后，在工作目录符合规则的 Cursor 会话将自动归属/)).toBeVisible()
    await expect(page.getByText(/用于 Git 采集与贡献统计|不填则无 Git/)).toBeVisible()
    await page.getByRole('button', { name: '取消' }).click()
  })

  test('步骤9 管理端展示 - 项目列表、项目参与、项目详情入口', async ({ page }) => {
    await page.goto('/projects')
    await expect(page.getByRole('heading', { name: /项目管理/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
    await page.getByRole('link', { name: '项目参与' }).click()
    await expect(page).toHaveURL(/\/workspace/)
    await expect(page.getByRole('heading', { name: /项目参与/ })).toBeVisible()
    await expect(page.getByText(/按项目与成员汇总|未归属/)).toBeVisible()
    await page.getByRole('link', { name: '项目' }).click()
    await expect(page).toHaveURL(/\/projects/)
  })

  test('项目详情 - 各部分数据来源标签与基本信息', async ({ page }) => {
    await page.goto('/projects/1')
    await expect(page).toHaveURL(/\/projects\/1/)
    await expect(page.getByText('来自 Hook 上报')).toBeVisible()
    await expect(page.getByText('来自 Git 采集')).toBeVisible()
    await expect(page.getByText(/成本|参与成员|Git 贡献/)).toBeVisible()
    await expect(page.getByText(/工作目录规则|关联仓库|仓库/)).toBeVisible()
  })
})

test.describe('Spec E2E：激励与贡献（管理端 UI）', () => {
  test('步骤4 排行榜 - 页面可打开，有周期选择', async ({ page }) => {
    await page.goto('/leaderboard')
    await expect(page).toHaveURL(/\/leaderboard/)
    await expect(page.getByRole('heading', { name: /排行榜/i })).toBeVisible()
    await expect(page.getByText(/周期|周|月/)).toBeVisible()
  })

  test('步骤5 我的贡献 - 页面可打开', async ({ page }) => {
    await page.goto('/my-contributions')
    await expect(page).toHaveURL(/\/my-contributions/)
    await expect(page.getByRole('heading', { name: /我的贡献/i })).toBeVisible()
  })

  test('步骤3 激励规则 - 规则配置页可打开', async ({ page }) => {
    await page.goto('/incentive-rules')
    await expect(page).toHaveURL(/\/incentive-rules/)
    await expect(page.getByRole('heading', { name: /激励规则/i })).toBeVisible()
    await expect(page.getByText(/规则|权重|重新计算|排行榜/)).toBeVisible()
  })
})
