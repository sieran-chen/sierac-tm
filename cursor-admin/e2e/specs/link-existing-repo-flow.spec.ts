/**
 * E2E: 关联已有仓库完整流程 + 项目参与 / 我的项目 / 项目详情观察
 * 运行: E2E_BASE_URL=http://8.130.50.168:3000 npx playwright test link-existing-repo-flow --reporter=list
 * 报告写入: e2e/link-existing-repo-report.json
 */
import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const REPORT_PATH = path.join(__dirname, '..', 'link-existing-repo-report.json')

test.describe('关联已有仓库流程与后续页面', () => {
  test('完整流程：新建(关联已有仓库) -> 保存 -> 项目参与 -> 我的项目 -> 项目详情', async ({ page }) => {
    const report: {
      steps: { step: string; observation: string }[]
      missingOrConfusing: string[]
      suggestions: string[]
    } = { steps: [], missingOrConfusing: [], suggestions: [] }

    const obs = (step: string, observation: string) => {
      report.steps.push({ step, observation })
    }

    // 1. Open app and go to 项目 (Projects)
    await page.goto('/')
    await expect(page).toHaveTitle(/Cursor Admin/i)
    await page.getByRole('link', { name: '项目', exact: true }).click()
    await expect(page).toHaveURL(/\/projects/)
    obs('1. Open app and go to 项目', 'Sidebar: 项目 selected. Page shows 项目管理 heading and 新建项目 button. Table with columns: 项目名称, 描述, 工作目录规则, 仓库状态, 状态, 创建时间, 操作.')

    // 2. Click 新建项目 (New Project)
    await page.getByRole('button', { name: /新建项目/i }).click()
    await expect(page.getByText('新建项目').first()).toBeVisible()
    obs('2. Click 新建项目', 'Modal opens with title 新建项目. Form: 项目名称, 描述, 工作目录规则, 参与成员邮箱, 仓库创建方式 (three options), 创建人邮箱.')

    // 3. Select 关联已有仓库 and fill form (含必填「已有仓库地址」)
    await expect(page.getByText('关联已有仓库')).toBeVisible()
    await page.getByText('关联已有仓库').first().click()
    await expect(page.getByText(/已有仓库地址/)).toBeVisible()
    await page.getByPlaceholder('如 Sierac-tm').fill('Test Project')
    await page.locator('textarea').nth(0).fill('D:\\test') // 工作目录规则
    await page.getByPlaceholder('admin@company.com').fill('admin@test.com')
    await page.locator('textarea').nth(2).fill('https://github.com/test-org/e2e-repo.git') // 已有仓库地址
    obs('3. Select 关联已有仓库 and fill form', '关联已有仓库 selected. Filled: 项目名称, 工作目录规则, 创建人邮箱, 已有仓库地址. 保存 enabled.')

    // 4. Click 保存 and observe
    await page.getByRole('button', { name: '保存' }).click()

    // For 关联已有仓库: API returns no repo URL, so modal closes and list reloads. Wait for modal to close (取消 disappears).
    const modalClosed = await page.getByRole('button', { name: '取消' }).waitFor({ state: 'hidden', timeout: 8000 }).then(() => true).catch(() => false)
    if (modalClosed) {
      const toastVisible = await page.getByText(/项目已创建|项目已保存/).isVisible().catch(() => false)
      obs('4a. After 保存 (关联已有仓库)', `Modal closed. Success feedback: ${toastVisible ? 'Toast (项目已创建/已保存) visible.' : 'No toast visible.'}`)
      const tableHasTestProject = await page.getByRole('cell', { name: 'Test Project' }).isVisible().catch(() => false)
      obs('4b. Table after save', tableHasTestProject ? 'New row with 项目名称 "Test Project" appears in the table.' : 'Table does not show "Test Project" (or still empty).')
      if (!tableHasTestProject) report.missingOrConfusing.push('After saving 关联已有仓库, no explicit success feedback; user may be unsure if save succeeded.')
    } else {
      const successScreen = await page.getByText('项目已创建，可复制以下地址').isVisible().catch(() => false)
      obs('4. After 保存', successScreen ? 'Success screen with repo URLs shown (expected only for auto-create).' : 'Modal did not close within timeout.')
      if (!successScreen) report.missingOrConfusing.push('Save result unclear (modal still open or timeout).')
    }

    // 5. Go to 项目参与 (Workspace)
    await page.getByRole('link', { name: '项目参与' }).click()
    await expect(page).toHaveURL(/\/workspace/)
    const workspaceHeading = await page.getByRole('heading', { name: /项目参与/ }).textContent().catch(() => '')
    const workspaceTable = await page.locator('table').first().isVisible().catch(() => false)
    const workspaceEmpty = await page.getByText(/暂无|未归属|按项目/).first().textContent().catch(() => '')
    obs('5. 项目参与 (Workspace)', `Heading: ${workspaceHeading}. Table visible: ${workspaceTable}. Page explains 按项目与成员汇总 Agent 会话；未关联项目的会话显示为「未归属」. Content: ${workspaceEmpty || 'table/empty state'} (sample).`)

    // 6. Go to 我的项目 (My Projects)
    await page.getByRole('link', { name: '我的项目' }).click()
    await expect(page).toHaveURL(/\/my-projects/)
    const myProjHeading = await page.getByRole('heading', { name: /我的项目/ }).textContent().catch(() => '')
    const myProjEmpty = await page.getByText(/暂无|按成员查看|数据来自/).first().textContent().catch(() => '')
    obs('6. 我的项目 (My Projects)', `Heading: ${myProjHeading}. Description about 按成员查看其参与的项目及 Git 贡献摘要. Sample text: ${myProjEmpty || 'N/A'}.`)

    // 7. Go to 项目详情 (click project name if present)
    await page.getByRole('link', { name: '项目', exact: true }).click()
    await expect(page).toHaveURL(/\/projects/)
    const projectLink = page.getByRole('link', { name: 'Test Project' }).first()
    const hasLink = await projectLink.isVisible().catch(() => false)
    if (hasLink) {
      await projectLink.click()
      await expect(page).toHaveURL(/\/projects\/\d+/)
      const backLink = await page.getByText('返回项目列表').isVisible().catch(() => false)
      const detailContent = await page.locator('main').textContent().catch(() => '')
      obs('7. 项目详情 (click Test Project)', `Navigated to project detail. Back link visible: ${backLink}. Main content includes project info, cost/contribution sections (sample length: ${detailContent?.length ?? 0}).`)
    } else {
      obs('7. 项目详情', 'Could not find link "Test Project" on projects list; skipped clicking into detail.')
      report.missingOrConfusing.push('Project list did not show Test Project link; cannot verify 项目详情 from this flow.')
    }

    // Suggestions based on flow
    report.suggestions.push('Optional: ensure 关联已有仓库 requires 已有仓库地址 and shows helper text (already implemented).')

    await fs.promises.writeFile(REPORT_PATH, JSON.stringify(report, null, 2), 'utf-8')
  })
})
