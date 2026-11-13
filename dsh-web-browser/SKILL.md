---
name: dsh-web-browser
display_name_zh: DSH 网页版连接
display_name_en: DSH Web Connect
description: "用 ego lite 连接本机 DeepSeek Harness（DSH）Web GUI 的技能：用户说「用 ego lite 打开 DSH 网页版」「连上本机 DSH 界面」「重启后重新进 DSH Web」「在浏览器里操作 DSH 自己的界面」「DSH Web 连不上或返回 401」时使用。一条命令连通，不需要 token，重启后也能直接连，不用每次重新推理认证方式。不用于操作外部网站，那走 ego-browser 常规流程。"
description_en: "Connect ego lite to the local DeepSeek Harness (DSH) Web GUI. Load this when the user wants to open DSH in a browser, reconnect after a restart, automate or inspect the DSH interface itself, or when the DSH page keeps failing with 401. One command signs the auth cookie offline from the on-disk secret, so no launch token and no re-deriving the auth flow each time. Not for browsing external websites; use the normal ego-browser workflow for those."
version: v20261112
---

# 用 ego lite 连接本机 DSH Web

本技能只做一件事：把 ego lite 接到**本机正在运行的** DSH Web GUI 上，并打开可用的页面。认证细节与源码依据见 [references/dsh-web-auth.md](references/dsh-web-auth.md)。

## 直接用

```bash
node ~/.dsh/skills/dsh-web-browser/scripts/ego-dsh.mjs
```

就这样。脚本自己找到运行中的 DSH 端口、签好认证 cookie、等待页面加载完成并打印 snapshot。

常用变体：

```bash
# 完成后保留页面给用户操作
node ~/.dsh/skills/dsh-web-browser/scripts/ego-dsh.mjs --keep

# 手动指定端口（默认自动探测）
node ~/.dsh/skills/dsh-web-browser/scripts/ego-dsh.mjs --port 63137
```

连上后，拿到 snapshot 就可以继续用 `ego-browser nodejs` 操作页面——用 `taskSpace("dsh web")` 复用同一个 TaskSpace，以 snapshot 里的 `ref=N` 或 `loc=...` 定位按钮点击。

只需要 cookie（例如写进别的请求或调试）：

```bash
node ~/.dsh/skills/dsh-web-browser/scripts/dsh-cookie.mjs --json
```

两个脚本只依赖 Node 内置模块，没有 npm 依赖。`ego-dsh.mjs` 需要 PATH 里有 `ego-browser`。

## 认证原理

**不要再去想办法拿 token。** DSH 的启动 token 由 `randomBytes(32)` 在进程内生成、只存在内存里，每次重启都是新值，外部读不到——这就是每次重启都挣扎半天的根源。

稳定做法是绕过 token：DSH 用一枚 **HMAC-SHA256 签名的 cookie** 认证浏览器会话，而签名密钥持久化在 `~/.dsh/.credentials.yaml` 的 `client-connection/browser-session` 记录里，**重启不变**。所以 cookie 可以离线签出来：

```
cookie 名  = "dsh-auth-" + b64url_nopad(sha256(authority))
cookie 值  = "v1." + b64url_nopad(JSON{version,authority,issuedAt,expiresAt})
                   + "."  + b64url_nopad(HMAC-SHA256(secret, body))
authority  = "127.0.0.1:<port>"
```

服务器还要求 `authority` 等于请求的 `Host`、`issuedAt` 不晚于当前时间、`expiresAt` 晚于当前时间且与签发间隔不超过最大有效期（默认 7 天）。

## 必须知道的坑

1. **cookie 只能写给已加载的域。** 在 `about:blank` 上写会被浏览器静默丢弃，不报错。必须先 `goto` 一次目标地址（哪怕拿到 401 页），再设 cookie，再重新 `goto`。脚本里的顺序就是这个原因，第一次 `goto` 用 `.catch()` 包住是因为 401 响应可能让加载状态报错，但不影响后续设 cookie。
2. **端口每次重启都变。** authority 变了，cookie 名也跟着变（名字是 authority 的哈希），旧 cookie 也无法覆盖新名字。所以每次都要按当前端口重新签，顺便清掉 `dsh-auth-` 前缀的旧 cookie。
3. **同名 TaskSpace 被 `--keep` 交还后，`taskSpace()` 会报 name-in-use。** 脚本已处理：先 `listTaskSpaces()` 找同名项，再 `claimTaskSpace(id)` 接管，所以反复 `--keep` 不会卡住。

## 判断是否连对了

真实的本机 DSH 实例，snapshot 里能看到你自己的会话列表（含「进行中」标记）、工作区、输入框。如果只有一个空壳或看起来像 demo 的内容，说明连错了端口。

`document.cookie` 读不到 `dsh-auth-*` 是正常的：cookie 带 `HttpOnly`，只由浏览器在请求头里自动发送。不要用「读不到 cookie」判断登录失败。

## 验证边界

- 连接是否通畅看页面内容，不要只看 `title`；`title` 在 401 页也可能有值。
- 失败页是纯文本 `dsh web authentication required; reopen the URL printed by dsh web.`，成功页才有会话列表与输入框。
- 不要用 curl 单独验证了事：curl 不带浏览器 cookie 必然 401，不代表 ego 连不上。
- 非本机访问（反代、公网域名、局域网 IP）不在本技能范围内：那时 authority 不再是 `127.0.0.1:<port>`，需要按实际 `Host` 重算，见 references 的失效场景表。