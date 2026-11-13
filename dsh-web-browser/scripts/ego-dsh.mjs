#!/usr/bin/env node
/**
 * 让 ego lite 连上本机 DSH Web。一行命令，无需 token，无需人工重签。
 *
 *   node scripts/ego-dsh.mjs                  # 打开 DSH 首页
 *   node scripts/ego-dsh.mjs --path /settings # 打开指定路径
 *   node scripts/ego-dsh.mjs --keep           # 完成后保留页面给用户
 *   node scripts/ego-dsh.mjs --port 57837     # 指定端口（默认自动探测）
 *
 * 认证原理（来自 DSH 源码 dsh-client-connection/src/browser-auth.ts）：
 *   cookie 名 = PREFIX + b64url_nopad(sha256(authority))
 *   cookie 值 = "v1." + b64url_nopad(JSON{version,authority,issuedAt,expiresAt})
 *                    + "." + b64url_nopad(HMAC-SHA256(secret, body))
 *   authority = "127.0.0.1:<port>"
 *
 * 关键点：签名密钥持久化在 ~/.dsh/.credentials.yaml 里，重启 DSH 不变。
 * 所以 cookie 可以离线签出来，不必去拿每次重启都变的启动 token。
 * 这是能跨会话复用的根本原因。
 *
 * 实现要点（踩过的坑）：
 *   - cookie 必须写在已加载目标域的页面上，在 about:blank 上写会静默丢弃。
 *     所以顺序是：先 goto 拿到 401 页面 → 设 cookie → 重新 goto。
 *   - 端口每次重启都变，旧 cookie 名字也随之变化；设新 cookie 前清掉旧前缀。
 *   - ego 不接受脚本文件路径（会把路径当代码），只能从 stdin 喂脚本。
 *   - ego 的日志写 stderr，必须原样转发，否则失败时看不到原因。
 *
 * 只用 Node 内置模块，无 npm 依赖；执行时 PATH 里需要有 ego-browser。
 */
import { createHash, createHmac } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { execFileSync, spawnSync } from 'node:child_process'

const COOKIE_PREFIX = ['dsh-', 'auth-'].join('')
const COOKIE_VERSION = 1
const SECRET_BYTES = 32
const DAY_MS = 86_400_000
const TASK_SPACE = 'dsh web'

const argv = process.argv.slice(2)
const argOf = (flag) => {
  const i = argv.indexOf(flag)
  return i === -1 ? undefined : argv[i + 1]
}
const hasFlag = (flag) => argv.includes(flag)

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

function decodeBase64Url(value) {
  const padded = value.replaceAll('-', '+').replaceAll('_', '/')
  return Buffer.from(padded + '='.repeat((4 - (padded.length % 4)) % 4), 'base64')
}

/** 读取持久的浏览器会话签名密钥。 */
function readSecret() {
  const file = join(homedir(), '.dsh', '.credentials.yaml')
  let text
  try {
    text = readFileSync(file, 'utf8')
  } catch {
    throw new Error(`无法读取 ${file}；先启动一次 DSH Web 以创建设备密钥`)
  }
  const block = text.match(/client-connection\/browser-session:[\s\S]*?(?=\n {2}\S|\nrefs:|\n\S|$)/)
  const raw = block?.[0].match(/secret:\s*(\S+)/)?.[1]
  if (!raw) throw new Error(`没在 ${file} 里找到 browser-session 密钥`)
  const secret = decodeBase64Url(raw)
  if (secret.byteLength !== SECRET_BYTES) throw new Error(`密钥长度异常：${secret.byteLength}`)
  return secret
}

/** 找到正在运行的 DSH web 端口：lsof 候选 + HTTP 探测确认。 */
async function detectPort() {
  const explicit = argOf('--port')
  if (explicit) return Number(explicit)
  if (process.env.DSH_WEB_PORT) return Number(process.env.DSH_WEB_PORT)

  const candidates = []
  try {
    const out = execFileSync('lsof', ['-nP', '-iTCP', '-sTCP:LISTEN'], { encoding: 'utf8' })
    for (const line of out.split(/\r?\n/)) {
      if (!line.startsWith('DeepSeek') || !line.includes('(LISTEN)')) continue
      const at = line.lastIndexOf('127.0.0.1:')
      if (at === -1) continue
      const port = Number(line.slice(at + 10).split(/[^0-9]/)[0])
      if (Number.isFinite(port) && port > 1024 && !candidates.includes(port)) candidates.push(port)
    }
  } catch {
    /* lsof 不可用 */
  }
  // 进程可能还监听调试端口，只认真正响应 HTTP 的那个
  for (const port of candidates.sort((a, b) => b - a)) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/`, {
        redirect: 'manual',
        signal: AbortSignal.timeout(1500),
      })
      if ([200, 303, 401].includes(res.status)) return port
    } catch {
      /* 不是 HTTP 服务 */
    }
  }
  throw new Error('没找到正在运行的 DSH web 端口；用 --port 显式指定')
}

function buildCookie(authority, days = 7) {
  const now = Date.now()
  const name = COOKIE_PREFIX + b64url(createHash('sha256').update(authority).digest())
  const body = b64url(
    Buffer.from(
      JSON.stringify({ version: COOKIE_VERSION, authority, issuedAt: now, expiresAt: now + days * DAY_MS }),
      'utf8',
    ),
  )
  const signature = b64url(createHmac('sha256', readSecret()).update(body).digest())
  return { name, value: `v${COOKIE_VERSION}.${body}.${signature}` }
}

async function main() {
  if (hasFlag('-h') || hasFlag('--help')) {
    console.log(readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0])
    return
  }

  const port = await detectPort()
  const authority = `127.0.0.1:${port}`
  const baseUrl = `http://${authority}/`
  const cookie = buildCookie(authority)
  const targetPath = argOf('--path') ?? '/'
  const target = baseUrl.replace(/\/$/, '') + (targetPath.startsWith('/') ? targetPath : `/${targetPath}`)
  const keep = hasFlag('--keep')

  const script = `
// 优先复用同名 space；若它已被交还给用户（上次 --keep），先找回再接管
let task;
try {
  task = await taskSpace(${JSON.stringify(TASK_SPACE)});
} catch (error) {
  const spaces = await listTaskSpaces();
  const mine = spaces.find((s) => s.name === ${JSON.stringify(TASK_SPACE)});
  if (!mine) throw error;
  task = await claimTaskSpace(mine.id);
}
const pages = await task.pages();
const page = pages.length > 0 ? pages[0] : await task.newPage();
const cookie = ${JSON.stringify(cookie)};

// 先落到目标域：cookie 只能写给已经加载的域。about:blank 上读 document.cookie
// 会抛 SecurityError。判定只看页面实际状态，不看 goto 的返回值——实测连续 goto
// 同一 URL 会间歇性报 "had not committed" 超时，而页面其实已经停在正确文档上。
const onOrigin = async () =>
  page.evaluate(() => location.href.startsWith("http://127.0.0.1:")).catch(() => false);

if (!(await onOrigin())) {
  await page.goto(${JSON.stringify(baseUrl)}, { timeout: 15000 }).catch((error) => {
    console.error("landing: " + error.message);
  });
}
// goto 报超时但页面已经在域名上：用 reload 再确认一次，仍不行才放弃。
if (!(await onOrigin())) {
  await page.reload({ timeout: 15000 }).catch(() => {});
}
if (!(await onOrigin())) {
  console.error("landing 失败：页面未进入 " + ${JSON.stringify(baseUrl)} + "，无法设置 cookie；请重跑，或用 --port 指定端口");
  process.exitCode = 1;
} else {
await page.evaluate(({ name, value, prefix }) => {
  for (const raw of document.cookie.split(";")) {
    const key = raw.split("=")[0].trim();
    if (key.startsWith(prefix) && key !== name) document.cookie = key + "=; Max-Age=0; Path=/";
  }
  document.cookie = name + "=" + value + "; Path=/; Domain=127.0.0.1";
}, { name: cookie.name, value: cookie.value, prefix: ${JSON.stringify(COOKIE_PREFIX)} });

// 目标导航：同样的误判风险，所以 goto 之后以页面状态为准。cookie 已就位，
// 正常情况下这里直接拿到 200；若确实还是错误页，把原因打印出来。
await page.goto(${JSON.stringify(target)}, { timeout: 20000 }).catch((error) => {
  console.error("goto:  " + String(error.message).split(String.fromCharCode(10))[0]);
});
// 等待 DSH SPA 真正渲染完成：「Loading plugins…」消失后才有可操作的界面
await page.waitForFunction(
  () => !document.body?.innerText?.includes('Loading plugins'),
  { timeout: 15000 }
).catch(() => {});
await page.waitForLoadState("networkidle").catch(() => {});
console.log("url:   " + (await page.url()));
console.log("title: " + (await page.title()));
console.log(await page.snapshot());
${keep ? 'await task.finish({ keep: ["p1"] }); console.log("page kept for user");' : ''}
}
`
  // ego 从 stdin 读脚本（传文件路径会被当成代码）；它把日志写到 stderr，需一并转发
  const run = spawnSync('ego-browser', ['nodejs'], { input: script, encoding: 'utf8' })
  if (run.error) {
    throw new Error(`无法执行 ego-browser：${run.error.message}；确认已在 PATH 中`)
  }
  if (run.stdout) process.stdout.write(run.stdout)
  if (run.stderr) process.stderr.write(run.stderr)
  if (run.status !== 0) process.exitCode = run.status ?? 1
}

main().catch((error) => {
  console.error(`[dsh] ${error.message}`)
  process.exitCode = 1
})