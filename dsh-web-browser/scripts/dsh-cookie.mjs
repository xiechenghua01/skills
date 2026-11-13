#!/usr/bin/env node
/**
 * 生成可用于 ego lite 直连本机 DSH Web 的认证 cookie。
 *
 * 原理（来自 DSH 源码 dsh-client-connection/src/browser-auth.ts）：
 *   cookie 名  = "dsh-auth-" + b64url_nopad(sha256(authority))
 *   cookie 值  = "v1." + b64url_nopad(JSON{version,authority,issuedAt,expiresAt})
 *                     + "." + b64url_nopad(HMAC-SHA256(secret, body))
 *   authority  = Host 头，即 "127.0.0.1:<port>"
 *   secret     = ~/.dsh/.credentials.yaml 中 client-connection/browser-session 的 32 字节密钥
 *
 * secret 持久化在 credentials 里，重启 DSH 不变，因此 cookie 可离线生成，
 * 无需从 DSH 进程读取运行时 token，也无需重启。
 *
 * 只用 Node 内置模块，无 npm 依赖。
 *
 * 用法：
 *   node scripts/dsh-cookie.mjs                       # 自动探测端口 + 人读输出
 *   node scripts/dsh-cookie.mjs --json                # 机器可读
 *   node scripts/dsh-cookie.mjs --port 57837          # 指定端口
 *   node scripts/dsh-cookie.mjs --days 7              # 有效期天数
 *   node scripts/dsh-cookie.mjs --port 57837 --json
 */

import { createHash, createHmac } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const COOKIE_PREFIX = ['dsh-', 'auth-'].join('')
const COOKIE_VERSION = 1
const SECRET_BYTES = 32
const DAY_MS = 24 * 60 * 60 * 1000
const DEFAULT_PORT = 58179

function parseArgs(argv) {
  const out = { json: false, port: undefined, days: 7 }
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i]
    if (a === '--json') out.json = true
    else if (a === '--port') out.port = Number(argv[++i])
    else if (a === '--days') out.days = Number(argv[++i])
    else if (a === '-h' || a === '--help') out.help = true
    else if (/^\d+$/.test(a)) out.port = Number(a)
  }
  return out
}

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

function decodeBase64Url(value) {
  const padded = value.replaceAll('-', '+').replaceAll('_', '/')
  return Buffer.from(padded + '='.repeat((4 - (padded.length % 4)) % 4), 'base64')
}

/** 从 ~/.dsh/.credentials.yaml 读取浏览器会话签名密钥（只做最小解析，避免引入 yaml 依赖）。 */
function readBrowserSecret() {
  const file = join(homedir(), '.dsh', '.credentials.yaml')
  let text
  try {
    text = readFileSync(file, 'utf8')
  } catch {
    throw new Error(`无法读取 ${file}；先启动一次 DSH Web 以创建设备密钥`)
  }
  const block = text.match(/client-connection\/browser-session:[\s\S]*?(?=\n {2}\S|\nrefs:|\n\S|$)/)
  if (!block) throw new Error('credentials.yaml 中缺少 client-connection/browser-session 记录')
  const raw = block[0].match(/secret:\s*(\S+)/)?.[1]
  if (!raw) throw new Error('browser-session 记录中缺少 secret')
  const secret = decodeBase64Url(raw)
  if (secret.byteLength !== SECRET_BYTES) throw new Error(`secret 长度异常：${secret.byteLength} 字节`)
  return secret
}

/** 找出正在运行的 DSH 实际监听端口（桌面 App 每次重启端口会变）。 */
async function detectPort(explicit) {
  if (explicit !== undefined && Number.isFinite(explicit)) return explicit
  if (process.env.DSH_WEB_PORT && /^[0-9]+$/.test(process.env.DSH_WEB_PORT)) return Number(process.env.DSH_WEB_PORT)

  const { execFileSync } = await import('node:child_process')
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
  return DEFAULT_PORT
}

export function buildCookie(secret, authority, days = 7, now = Date.now()) {
  const name = COOKIE_PREFIX + b64url(createHash('sha256').update(authority).digest())
  const issuedAt = now
  const expiresAt = now + days * DAY_MS
  const body = b64url(
    Buffer.from(JSON.stringify({ version: COOKIE_VERSION, authority, issuedAt, expiresAt }), 'utf8'),
  )
  const sig = b64url(createHmac('sha256', secret).update(body).digest())
  return {
    name,
    value: `v${COOKIE_VERSION}.${body}.${sig}`,
    header: `${name}=v${COOKIE_VERSION}.${body}.${sig}`,
    authority,
    issuedAt,
    expiresAt,
    expiresAtISO: new Date(expiresAt).toISOString(),
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    console.log(readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0])
    return
  }
  const port = await detectPort(args.port)
  const authority = `127.0.0.1:${port}`
  const secret = readBrowserSecret()
  const cookie = buildCookie(secret, authority, args.days)
  const url = `http://${authority}/`

  if (args.json) {
    console.log(JSON.stringify({ url, ...cookie }, null, 2))
    return
  }
  console.log(`URL       ${url}`)
  console.log(`Authority ${cookie.authority}`)
  console.log(`Expires   ${cookie.expiresAtISO}（${args.days} 天）`)
  console.log(`Cookie    ${cookie.header}`)
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop())) {
  main().catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}