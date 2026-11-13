# DSH Web 认证内部机制

本文记录 DSH Web GUI 的浏览器认证是如何工作的，以及在什么情况下会失效。内容来自实际的安装包源码，不是猜测。

## 源码位置

DSH 桌面 App 把代码打包在 `app.asar` 里。认证逻辑在：

```
dsh/node_modules/@deepseek-ai/dsh-client-connection/src/browser-auth.ts
```

macOS 桌面 App 的包路径是 `/Applications/DeepSeek Harness.app/Contents/Resources/app.asar`；其他平台按自己的安装目录找同名文件。`app.asar` 是「16 字节头 + JSON 目录 + 拼接文件体」的格式，可以用 Node 直接解析，不需要任何依赖：

1. 读开头 16 字节，第 12 字节起是 `uint32 LE` 的目录长度
2. 读该长度的 JSON 目录，得到每个文件的 `offset` 和 `size`
3. 文件体基准 = `16 + 目录长度`，实际位置 = `基准 + offset`

```js
// 例：取出 browser-auth.ts 原文（把 ASAR 换成实际路径）
const fs = require('node:fs')
const ASAR = '/Applications/DeepSeek Harness.app/Contents/Resources/app.asar'
const fd = fs.openSync(ASAR, 'r')
const head = Buffer.alloc(16)
fs.readSync(fd, head, 0, 16, 0)
const dirLen = head.readUInt32LE(12)
const dir = Buffer.alloc(dirLen)
fs.readSync(fd, dir, 0, dirLen, 16)
const tree = JSON.parse(dir.toString('utf8'))
const base = 16 + dirLen

// 目录树是嵌套对象，叶子节点带 { offset, size }
const found = (function walk(node, prefix) {
  for (const [key, value] of Object.entries(node)) {
    if (value && typeof value === 'object' && value.files) {
      const hit = walk(value.files, prefix + key + '/')
      if (hit) return hit
    } else if (value && typeof value === 'object' && 'offset' in value) {
      const name = prefix + key
      if (name.endsWith('dsh-client-connection/src/browser-auth.ts')) return { name, value }
    }
  }
  return null
})(tree.files, '')

const body = Buffer.alloc(found.value.size)
fs.readSync(fd, body, 0, found.value.size, base + Number(found.value.offset))
console.log(body.toString('utf8'))
```

包内同时带 `src/*.ts`（原始 TypeScript）和 `lib/*.js`（编译产物），所以能直接读可读的源码。

## cookie 格式

```
名字 = "dsh-auth-" + b64url_nopad(sha256(authority))
值   = "v1." + B + "." + S

B = b64url_nopad(JSON.stringify({
      version:   1,
      authority: "127.0.0.1:<port>",
      issuedAt:  <ms>,
      expiresAt: <ms>,
    }))
S = b64url_nopad(HMAC-SHA256(secret, B))
```

`b64url_nopad` 指标准 base64 后把 `+`→`-`、`/`→`_`、去掉尾部 `=`。

服务器校验时还要求：

- `payload.authority` 必须等于请求的 `Host`
- `issuedAt` 不晚于当前时间
- `expiresAt` 晚于当前时间，且晚于 `issuedAt`
- `expiresAt - issuedAt` 不超过配置的最大有效期（默认 7 天）

cookie 属性是 `Path=/; HttpOnly; SameSite=Strict`，HTTPS 时再加 `Secure`。`HttpOnly` 意味着页面 JS 读不到它，只有浏览器发请求时会带上。

## secret 存在哪

`~/.dsh/.credentials.yaml`：

```yaml
records:
  client-connection/browser-session:
    kind: grant
    payload:
      version: 1
      secret: <base64url, 32 字节原始密钥>
```

这个文件由 DSH 首次启动时创建，之后一直复用。**这就是 cookie 能跨重启复用的根本原因**——secret 不变，签出来的 cookie 一直有效，只要 authority 对得上且没过期。

脚本里用 `os.homedir()` 拼这个路径，不写死任何一台机器的绝对路径。

## 为什么 token 路线不可取

`BrowserAuth` 里有一个 `launchToken`，由 `randomBytes(32)` 在进程内生成，存在 `WeakMap` 里：

```ts
function processLaunchToken(owner: object): string {
  const existing = PROCESS_LAUNCH_TOKENS.get(owner)
  if (existing !== undefined) return existing
  const created = encodeBase64url(randomBytes(SECRET_BYTES))
  PROCESS_LAUNCH_TOKENS.set(owner, created)
  return created
}
```

它只出现在 DSH 启动时打印的那条 `http://127.0.0.1:<port>/?token=...` 里，不落盘。进程一重启就是新值，外部无从获取。

它的作用是把 token 换成 cookie：

- `GET /?token=<launchToken>` → `303` 到 `./`，同时 `Set-Cookie` 一枚正式 cookie
- 带有效 cookie 访问首页 → `200`

所以 token 只是一次性的引导凭据。既然 cookies 才是长期凭据，而 cookie 可以用磁盘上的 secret 离线签，就完全没必要去拿 token。

## 什么时候会失效

| 情况 | 表现 | 处理 |
| --- | --- | --- |
| 端口变了（重启） | cookie 名字和 authority 都不匹配 | 按新端口重签 |
| 超过 7 天 | 服务器判 `expiresAt` 过期 | 重签 |
| `.credentials.yaml` 被删或重装 | secret 变了 | DSH 会新建 secret，重签即可 |
| 不是本机（走了反代/公网域名） | authority 不再收 `127.0.0.1:port` | 按实际 Host 换 authority |

注意最后一条：authority 取自请求的 `Host` 头，所以如果是通过域名或局域网 IP 访问，cookie 名字里的哈希也要按那个 authority 算。

## 给 ego lite 设 cookie 的顺序

浏览器有两条限制会导致 cookie 设不上：

1. **cookie 只能写给已加载的域。** 页面还停在 `about:blank` 时写 `document.cookie`，浏览器直接丢弃，不报错。
2. **端口不同就是不同的 origin。** 旧端口签的 cookie 帮不上新端口，而且名字不同也无法覆盖。

正确顺序：

```
goto(http://127.0.0.1:<port>/)      # 落地，拿 401 也没关系
document.cookie = 新 cookie         # 此时域已就位，写入生效
清掉其他 dsh-auth-* 旧 cookie
goto(目标路由)                       # 这次带 cookie，得到 200
```

脚本 `scripts/ego-dsh.mjs` 就按这个顺序实现。第一次 `goto` 用 `.catch(() => {})` 包住，是因为 401 响应本身可能让某些加载状态报错，但不影响后续设 cookie。

设 cookie 时写 `Path=/; Domain=127.0.0.1`；`HttpOnly` 只影响读取，不影响用 JS 写入。

## 路由与 404

DSH Web 是单页应用，**没有 URL 路由**：前端 bundle 里没有 `history.pushState` / hash 路由，服务端也只对 `/` 返回 200。除 `/` 之外的路径（`/settings`、`/plugins`、`/skills` 等）即使带有效 cookie 也是 404；`/api` 返回纯文本 404。

所以「打开某个面板」不能靠拼 URL，只能打开 `/` 后按 snapshot 里的按钮名点击。`scripts/ego-dsh.mjs --path` 保留了这个参数以备将来服务端增加路由，导航失败时打印 `goto:` 行并继续输出 snapshot，不中断流程。

## 验证方法

认证成功与否看页面内容，不看状态码之外的信号：

- 失败：纯文本 `dsh web authentication required; reopen the URL printed by dsh web.`
- 成功：出现会话列表、工作区、输入框

`curl http://127.0.0.1:<port>/` 永远是 `401`（不带浏览器 cookie），这不能用来判断 ego 是否连得上。

`document.cookie` 里也看不到它（`HttpOnly`）。想看 cookie 是否设上，用 `page.evaluate` 读不到就对了；真要确认，看页面能否正常加载会话列表。

只想拿到 cookie 字符串、不做浏览器操作时，用 `scripts/dsh-cookie.mjs --json`：它按当前探测到的端口签一枚 cookie，返回 `url`、`name`、`value`、`header` 与过期时间。