// @ts-check
import { test, expect } from '@playwright/test'
import { appendFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const LOG = join(__dirname, '..', 'debug-4561a6.log')
const PORTS = [5176, 5177, 5173, 5174, 5175]

async function findDevServer() {
  for (const port of PORTS) {
    try {
      const r = await fetch(`http://localhost:${port}/%E6%A8%A1%E6%8B%9F%E6%8C%81%E4%BB%93/%E4%B8%AA%E8%82%A1%E9%A3%8E%E9%99%A9%E8%B7%9F%E8%B8%AA`, { signal: AbortSignal.timeout(2000) })
      if (r.ok) return port
    } catch {}
  }
  throw new Error('VitePress dev server not found')
}

function writeLog(entry) {
  appendFileSync(LOG, JSON.stringify(entry) + '\n', 'utf8')
}

test('table status dots are visible with color', async ({ page }) => {
  const port = await findDevServer()
  await page.goto(`http://localhost:${port}/%E6%A8%A1%E6%8B%9F%E6%8C%81%E4%BB%93/%E4%B8%AA%E8%82%A1%E9%A3%8E%E9%99%A9%E8%B7%9F%E8%B8%AA`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.rd-tbl .dot', { timeout: 30000 })

  const dotInfo = await page.evaluate(() => {
    const dots = Array.from(document.querySelectorAll('.rd-tbl .dot'))
    const rdRoot = document.querySelector('.rd-root')
    return {
      count: dots.length,
      samples: dots.slice(0, 5).map((d) => {
        const cs = getComputedStyle(d)
        return { className: d.className, background: cs.backgroundColor, width: cs.width, height: cs.height }
      }),
      rdRootVarG: rdRoot ? getComputedStyle(rdRoot).getPropertyValue('--rd-g').trim() : null,
      docVarG: getComputedStyle(document.documentElement).getPropertyValue('--g').trim(),
    }
  })

  writeLog({
    sessionId: '4561a6',
    runId: 'playwright-dot-fix',
    timestamp: Date.now(),
    location: 'tests/risk-dashboard-dots.spec.mjs',
    message: 'dot visibility check',
    data: dotInfo,
    hypothesisId: 'G',
  })

  expect(dotInfo.count).toBeGreaterThan(0)
  expect(dotInfo.rdRootVarG).toBe('#22c55e')

  const colored = dotInfo.samples.filter((s) => s.background && s.background !== 'rgba(0, 0, 0, 0)' && s.background !== 'transparent')
  expect(colored.length).toBeGreaterThan(0)
})
