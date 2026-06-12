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
      const r = await fetch(`http://localhost:${port}/risk-dashboard`, { signal: AbortSignal.timeout(2000) })
      if (r.ok) return port
    } catch {}
  }
  throw new Error(`VitePress dev server not found on ports ${PORTS.join(', ')}. Run: npm run docs:dev`)
}

function writeLog(entry) {
  appendFileSync(LOG, JSON.stringify(entry) + '\n', 'utf8')
}

test('risk dashboard uses wide layout and shows full note column', async ({ page }) => {
  const port = await findDevServer()
  await page.goto(`http://localhost:${port}/risk-dashboard`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.rd-tbl', { timeout: 30000 })

  const metrics = await page.evaluate(() => {
    const cs = (el) => (el ? getComputedStyle(el) : null)
    const vpDoc = document.querySelector('.VPDoc')
    const content = document.querySelector('.VPDoc .container .content')
    const rdRoot = document.querySelector('.rd-root')
    const tblCard = document.querySelector('.rd-tbl-card')
    const noteCell = document.querySelector('.td-note')
    return {
      bodyClasses: document.body.className,
      vpDocHasAside: vpDoc?.classList.contains('has-aside') ?? null,
      viewportWidth: window.innerWidth,
      content: content ? { clientWidth: content.clientWidth, maxWidth: cs(content).maxWidth } : null,
      rdRoot: rdRoot ? { clientWidth: rdRoot.clientWidth } : null,
      tblCard: tblCard ? { clientWidth: tblCard.clientWidth, overflow: cs(tblCard).overflowX } : null,
      noteCell: noteCell
        ? {
            clientWidth: noteCell.clientWidth,
            scrollWidth: noteCell.scrollWidth,
            truncated: noteCell.scrollWidth > noteCell.clientWidth + 2,
            maxWidth: cs(noteCell).maxWidth,
            whiteSpace: cs(noteCell).whiteSpace,
          }
        : null,
    }
  })

  writeLog({
    sessionId: '4561a6',
    runId: 'playwright-post-fix',
    timestamp: Date.now(),
    location: 'tests/risk-dashboard-layout.spec.mjs',
    message: 'playwright layout verification',
    data: metrics,
    hypothesisId: 'A-E',
  })

  expect(metrics.bodyClasses).toContain('dashboard-wide')
  expect(metrics.bodyClasses).toContain('risk-dashboard-active')
  expect(metrics.vpDocHasAside).toBe(false)

  // Hypothesis A: content area should use most of viewport (not ~688px narrow column)
  expect(metrics.content?.clientWidth).toBeGreaterThan(900)

  // Hypothesis C: note cell should not be ellipsis-truncated
  expect(metrics.noteCell?.truncated).toBe(false)
  expect(metrics.noteCell?.whiteSpace).not.toBe('nowrap')

  // Hypothesis D: table card allows horizontal scroll if needed
  expect(metrics.tblCard?.overflow).toBe('auto')

  // rd-root should span most of content width
  expect(metrics.rdRoot?.clientWidth).toBeGreaterThan(800)
})
