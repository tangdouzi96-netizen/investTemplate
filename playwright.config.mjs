/** @type {import('@playwright/test').PlaywrightTestConfig} */
export default {
  testDir: './tests',
  timeout: 60000,
  use: {
    viewport: { width: 1440, height: 900 },
    headless: true,
    channel: 'chrome',
  },
}
