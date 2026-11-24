/**
 * Complainant → police flow in a real browser with a fake microphone that plays a Luganda voice clip.
 * Prerequisites: server on E2E_BASE (default :8000) after `seed_demo --reset`; SUNBIRD_API_KEY set on the
 * server for the AI step (otherwise the report reaches police without AI, which is also handled).
 */
import { createRequire } from 'module'
import fs from 'fs'
const require = createRequire(import.meta.url)
const { chromium } = require('playwright')

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:8000'
const PASSWORD = 'Tuliwamu#Demo2026'
const SHOTS = new URL('./screenshots/', import.meta.url).pathname
const CLIP = new URL('./fixtures/luganda-voice.wav', import.meta.url).pathname
fs.mkdirSync(SHOTS, { recursive: true })
const ok = (m) => console.log('  ✓', m)

const browser = await chromium.launch({ args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-audio-capture=${CLIP}`] })
async function session(username, viewport = { width: 1280, height: 900 }) {
  const ctx = await browser.newContext({ viewport, permissions: ['microphone'] })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.error('PAGE ERROR', e.message))
  await page.goto(`${BASE}/login`)
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL(/\/(app|me)/)
  return page
}

console.log('1. Complainant sees a welcome page, then reports by voice')
const c = await session('complainant.demo', { width: 400, height: 860 })
await c.getByRole('heading', { name: /Welcome/ }).waitFor()
if (await c.getByText(/TLW-|CR-/).count()) throw new Error('Welcome page shows a case/report before reporting')
await c.screenshot({ path: `${SHOTS}c1-welcome.png`, fullPage: true })
ok('welcome page, no case details')
await c.getByRole('link', { name: /Tell us what happened/ }).first().click()
await c.getByRole('button', { name: 'My child' }).click()
await c.getByRole('button', { name: '9–11 years' }).click()
await c.getByLabel('District or area').fill('Kampala')
await c.getByRole('button', { name: 'No / not sure' }).click()
await c.getByRole('button', { name: 'Next' }).click()
await c.getByRole('button', { name: 'Luganda' }).click()
await c.getByRole('button', { name: 'Start recording' }).click()
await c.waitForTimeout(6500)
await c.getByRole('button', { name: 'Stop recording' }).click()
await c.getByText('Voice note ready').waitFor()
await c.screenshot({ path: `${SHOTS}c2-voice-recorded.png`, fullPage: true })
ok('voice note recorded in the browser')
await c.getByRole('button', { name: 'Next' }).click()
await c.getByText('Check before sending').waitFor()
await c.getByRole('button', { name: 'Send my report' }).click()
await c.getByText('Thank you for telling us').waitFor({ timeout: 60000 })
const reportRef = (await c.locator('.font-mono').first().innerText()).trim()
await c.screenshot({ path: `${SHOTS}c3-thanks.png`, fullPage: true })
ok(`report sent: ${reportRef}`)
await c.getByRole('button', { name: 'Go to my home page' }).click()
await c.getByText('Please wait — the police are checking your report').waitFor()
ok('dashboard shows "please wait" with the 24-hour promise')

console.log('2. Police verify the AI-prepared report')
const p = await session('police.officer')
await p.goto(`${BASE}/app/complaints`)
await p.getByRole('link', { name: reportRef }).click()
let aiDone = false
for (let i = 0; i < 30; i++) {
  await p.getByText("Complainant's statement").waitFor()
  if (await p.getByText(/Prepared by sunbird/).count()) { aiDone = true; break }
  if (await p.getByText(/AI analysis (failed|not used)/).count()) break
  await p.waitForTimeout(8000)
  await p.reload()
}
console.log(aiDone ? '  ✓ Sunbird AI transcribed, translated and categorised the voice note' : '  ! AI did not finish — continuing with manual verification')
await p.screenshot({ path: `${SHOTS}c4-police-verify.png`, fullPage: true })
await p.getByRole('button', { name: 'Ask' }).click()
await p.getByLabel('Message to the complainant').fill('Thank you. Is your daughter safe tonight? Which village do you live in?')
await p.getByRole('button', { name: 'Send message' }).click()
await p.getByText('Waiting for complainant').first().waitFor({ timeout: 120000 })
ok('police asked a question (translated to the complainant\'s language when possible)')

console.log('3. Complainant answers')
await c.reload()
await c.getByRole('link', { name: 'Answer the police' }).click()
await c.getByText('Messages with the police').waitFor()
await c.getByPlaceholder('Write your answer…').fill('Ali bulungi kati. Tubeera Kawempe.')
await c.getByRole('button', { name: 'Send', exact: true }).click()
await c.getByText('Ali bulungi kati. Tubeera Kawempe.').waitFor({ timeout: 120000 })
await c.screenshot({ path: `${SHOTS}c5-conversation.png`, fullPage: true })
ok('complainant replied')

console.log('4. Police register the case')
await p.reload()
await p.getByText("Complainant's statement").waitFor()
await p.getByRole('button', { name: 'Register', exact: true }).click()
await p.getByRole('button', { name: 'Verify and register case' }).click()
await p.waitForURL(/\/app\/cases\/.+created=1/, { timeout: 60000 })
await p.locator('h1', { hasText: 'TLW-' }).waitFor()
const caseRef = (await p.locator('h1').innerText()).trim()
ok(`case registered: ${caseRef}`)

console.log('5. Complainant follows the case')
await c.goto(`${BASE}/me`)
await c.getByText(caseRef).first().waitFor()
await c.getByText('Where is my case now?').first().waitFor()
await c.screenshot({ path: `${SHOTS}c6-following-case.png`, fullPage: true })
for (const secret of ['AI-prepared', 'Transcript', 'Internal note']) if (await c.getByText(secret).count()) throw new Error(`Complainant sees ${secret}`)
ok('complainant now follows the case; no AI output or police notes visible')
await browser.close()
console.log('\nComplainant flow passed.')
