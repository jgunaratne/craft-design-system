#!/usr/bin/env node
/**
 * shoot.mjs — screenshots per theme × width (× UI font size) with a machine-readable report.
 *
 *   node shoot.mjs --out DIR --widths 1280,900 --themes proMedium,studio,classic [--font-sizes small,large]
 *                  [--height 900] [--full-page] [--strict] -- <url-or-html-file ...>
 *
 * A theme is selected two ways at once, so pages with or without craft-ds.js both work:
 * `?theme=<id>` (craft-ds.js honours it) and `data-craft-theme` set on <html> before load (and kept
 * there by a MutationObserver until craft-ds.js takes over with the same id). Files land as
 * <out>/<id>-<theme>[-<font>]-<width>.png plus <out>/report.json with page errors, horizontal
 * overflow and axe-core violations (when `axe-core` is resolvable).
 *
 * Needs `playwright` or `puppeteer-core` resolvable via NODE_PATH (the CLI sets it from the repo's
 * node_modules) and, for puppeteer-core, Chrome at $CRAFT_CHROME or a usual location.
 */
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { basename, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const args = process.argv.slice(2)
const opt = { out: 'test-results/craft-shots', widths: [1280, 900], themes: ['proMedium', 'studio', 'classic'], fontSizes: [''], height: 900, fullPage: false, strict: false, targets: [] }
for (let i = 0; i < args.length; i++) {
  const a = args[i]
  const v = () => args[++i]
  if (a === '--out') opt.out = v()
  else if (a === '--widths') opt.widths = v().split(',').map(Number)
  else if (a === '--themes') opt.themes = v().split(',').filter(Boolean)
  else if (a === '--font-sizes') opt.fontSizes = v().split(',').filter(Boolean)
  else if (a === '--height') opt.height = Number(v())
  else if (a === '--full-page') opt.fullPage = true
  else if (a === '--strict') opt.strict = true
  else if (a === '--') { opt.targets.push(...args.slice(i + 1)); break }
  else opt.targets.push(a)
}
if (!opt.targets.length) { console.error('shoot: name at least one URL or HTML file'); process.exit(1) }

function tryRequire(name) { try { return require(name) } catch { return null } }
const pw = tryRequire('playwright') || tryRequire('@playwright/test')
const pptr = pw ? null : tryRequire('puppeteer-core')
if (!pw && !pptr) { console.error('shoot: neither playwright nor puppeteer-core is resolvable (npm i -D playwright, or set screenshots.command in craft-ds.json)'); process.exit(1) }
const axePath = (() => { try { return require.resolve('axe-core/axe.min.js') } catch { return null } })()
const CHROME = process.env.CRAFT_CHROME || ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find((p) => existsSync(p))

async function launch() {
  if (pw) {
    let browser
    try { browser = await pw.chromium.launch({ headless: true }) } catch (e) {
      if (!CHROME) throw e
      browser = await pw.chromium.launch({ headless: true, executablePath: CHROME })
    }
    return {
      browser,
      async page(width, height, initScript) {
        const ctx = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce', deviceScaleFactor: 1 })
        if (initScript) await ctx.addInitScript(initScript)
        const page = await ctx.newPage()
        return { page, close: () => ctx.close() }
      },
      async goto(page, url) { await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 }) },
      async shot(page, path) { await page.screenshot({ path, fullPage: opt.fullPage }) },
      async addScript(page, path) { await page.addScriptTag({ path }) },
    }
  }
  if (!CHROME) { console.error('shoot: no Chrome found for puppeteer-core (set CRAFT_CHROME)'); process.exit(1) }
  const browser = await pptr.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--headless=new', '--hide-scrollbars'] })
  return {
    browser,
    async page(width, height, initScript) {
      const page = await browser.newPage()
      await page.setViewport({ width, height, deviceScaleFactor: 1 })
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
      if (initScript) await page.evaluateOnNewDocument(initScript)
      return { page, close: () => page.close() }
    },
    async goto(page, url) { await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 }) },
    async shot(page, path) { await page.screenshot({ path, fullPage: opt.fullPage }) },
    async addScript(page, path) { await page.addScriptTag({ path }) },
  }
}

const initFor = (theme, font) => `(() => {
  const want = { 'data-craft-theme': ${JSON.stringify(theme)}, 'data-craft-font-size': ${JSON.stringify(font || '')} }
  const set = () => { for (const [k, v] of Object.entries(want)) if (v && document.documentElement.getAttribute(k) !== v) document.documentElement.setAttribute(k, v) }
  try { set() } catch (e) {}
  new MutationObserver(set).observe(document.documentElement, { attributes: true, attributeFilter: Object.keys(want) })
})()`

function themedUrl(base, theme, font) {
  const u = new URL(base)
  if (theme) u.searchParams.set('theme', theme)
  if (font) u.searchParams.set('font', font)
  return u.href
}

const engine = await launch()
mkdirSync(opt.out, { recursive: true })
const report = []
let bad = 0
try {
  for (const target of opt.targets) {
    let base, id
    if (/^https?:\/\//.test(target)) { base = target; id = (new URL(target).pathname.split('/').filter(Boolean).pop() || 'page').replace(/\.html?$/, '') }
    else if (existsSync(target)) { base = pathToFileURL(resolve(target)).href; id = basename(target).replace(/\.html?$/, '') }
    else { console.error(`shoot: ${target} is not a URL or a file`); bad++; continue }
    for (const theme of opt.themes.length ? opt.themes : ['']) {
      for (const font of opt.fontSizes) {
        for (const width of opt.widths) {
          const { page, close } = await engine.page(width, opt.height, initFor(theme, font))
          const errors = []
          page.on('pageerror', (e) => errors.push(String(e.message || e)))
          page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
          const url = themedUrl(base, theme, font)
          let overflowX = null, axe = null, applied = null
          try {
            await engine.goto(page, url)
            await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; await new Promise((r) => setTimeout(r, 400)) })
            applied = await page.evaluate(() => ({ theme: document.documentElement.getAttribute('data-craft-theme'), font: document.documentElement.getAttribute('data-craft-font-size') }))
            overflowX = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
            if (axePath) {
              await engine.addScript(page, axePath)
              axe = await page.evaluate(async () => {
                const r = await window.axe.run(document, { preload: false, runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })
                return r.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.slice(0, 5).map((n) => n.target.join(' ')) }))
              })
            }
            const name = `${id}-${theme || 'default'}${font ? '-' + font : ''}-${width}.png`
            await engine.shot(page, resolve(opt.out, name))
            const entry = { target, theme, font: font || null, width, file: name, applied, errors, overflowX, axe }
            report.push(entry)
            const flags = [errors.length ? `${errors.length} error(s)` : '', overflowX > 0 ? `overflow ${overflowX}px` : '', axe && axe.length ? `${axe.length} axe` : '', applied && theme && applied.theme !== theme ? `theme NOT applied (${applied.theme})` : ''].filter(Boolean)
            if (flags.length) bad++
            console.log(`  ${name}${flags.length ? '  ⚠ ' + flags.join(', ') : ''}`)
          } catch (e) {
            bad++
            report.push({ target, theme, font: font || null, width, error: String(e.message || e) })
            console.log(`  ${id}-${theme}-${width}: FAILED ${String(e.message || e).split('\n')[0]}`)
          } finally {
            await close()
          }
        }
      }
    }
  }
} finally {
  await engine.browser.close()
}
writeFileSync(resolve(opt.out, 'report.json'), JSON.stringify(report, null, 2))
console.log(`${report.filter((r) => r.file).length} screenshots in ${opt.out}/ (report.json alongside) — now read every PNG`)
process.exit(opt.strict && bad ? 1 : 0)
