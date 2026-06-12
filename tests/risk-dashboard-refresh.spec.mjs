// @ts-check
import { test, expect } from '@playwright/test'
import { appendFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const LOG = join(__dirname, '..', 'debug-4561a6.log')
const PORTS = [5176, 5177, 5173, 5174, 5175]
const CANONICAL = '/模拟持仓/个股风险跟踪'
const LEGACY = '/risk-dashboard.html'

async function findDevServer() {
  for (const port of PORTS) {
    try {
      const r = await fetch(`http://localhost:${port}${CANONICAL}`, { signal: AbortSignal.timeout(2000) })
      if (r.ok) return port
    } catch {}
  }
  throw new Error(`VitePress dev server not found. Run: npm run docs:dev`)
}

function writeLog(entry) {
  appendFileSync(LOG, JSON.stringify(entry) + '\n', 'utf8')
}

test('refresh keeps VitePress risk dashboard (no standalone flash route)', async ({ page }) => {
  const port = await findDevServer()
  const base = `http://localhost:${port}`

  // Legacy URL must redirect, not render standalone dashboard
  const legacyResp = await page.goto(`${base}${LEGACY}`, { waitUntil: 'commit' })
  expect(page.url()).toContain(encodeURIComponent('个股风险跟踪'))
  await page.waitForSelector('.rd-root', { timeout: 30000 })

  const afterLegacy = await page.evaluate(() => ({
    pathname: location.pathname,
    hasRdRoot: !!document.querySelector('.rd-root'),
    hasStandaloneSidebar: !!document.querySelector('body > .sidebar'),
    hasVpNav: !!document.querySelector('.VPNav'),
  }))

  writeLog({
    sessionId: '4561a6',
    runId: 'playwright-refresh-fix',
    timestamp: Date.now(),
    location: 'tests/risk-dashboard-refresh.spec.mjs',
    message: 'after legacy redirect',
    data: afterLegacy,
    hypothesisId: 'F',
  })

  expect(afterLegacy.hasRdRoot).toBe(true)
  expect(afterLegacy.hasStandaloneSidebar).toBe(false)
  expect(afterLegacy.hasVpNav).toBe(true)

  // Canonical page: reload must stay on Vue dashboard
  await page.goto(`${base}${CANONICAL}`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.rd-tbl', { timeout: 30000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForSelector('.rd-root', { timeout: 30000 })

  const afterReload = await page.evaluate(() => ({
    pathname: location.pathname,
    hasRdRoot: !!document.querySelector('.rd-root'),
    hasStandaloneSidebar: !!document.querySelector('body > .sidebar'),
    hasVpNav: !!document.querySelector('.VPNav'),
  }))

  writeLog({
    sessionId: '4561a6',
    runId: 'playwright-refresh-fix',
    timestamp: Date.now(),
    location: 'tests/risk-dashboard-refresh.spec.mjs',
    message: 'after canonical reload',
    data: afterReload,
    hypothesisId: 'F',
  })

  expect(afterReload.hasRdRoot).toBe(true)
  expect(afterReload.hasStandaloneSidebar).toBe(false)
  expect(afterReload.hasVpNav).toBe(true)
})
