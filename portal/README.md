# 统一登录门户（portal/）

一个解耦的登录门户：飞书证明「你是谁」，门户签发短期 JWT，各接入应用用门户公布的
JWKS 公钥本地验签。门户看不到任何应用数据，应用拿不到飞书凭据——双向解耦。

设计决策记录见 [`docs/deployment.md)。

## 流程

```
GET /login?app=bridgeflow        → 302 到飞书授权页（state 为 HMAC 签名，防 CSRF）；
                                   已持有效会话则跳过飞书，直接 302 到该应用的 redirect_uri
GET /callback?code=&state=       → 换 user_access_token、取 user_info，种会话 Cookie，302 回应用
GET /token?app=bridgeflow        → 凭会话 Cookie 签发应用 JWT（Ed25519，aud=bridgeflow，15 分钟）
GET /.well-known/jwks.json       → 验签公钥（应用侧只持有这一半）
GET /me · POST /logout · GET /health
```

`GET /` 是门户首页：未登录时列应用登录入口；已登录且只注册了一个应用时直接 302 进应用，
多个应用时显示「已登录为…」与应用列表。

接入新应用 = 在 `apps.yaml` 里加一段声明（audience、回调地址、允许的跨域来源），
不改代码——与 `data/mappings/` 字段字典同一条约定。

## 搭建

```bash
source ../env.sh                      # PORTAL_* 变量只能由启动 shell export（见下）
python -m portal_app.keygen ~/Hackathon2026/.portal-key.pem   # 私钥放仓库外
uvicorn portal_app.main:app --port 8100
```

`env.sh` 里需要（模板见 `env.sh.example`）：

| 变量 | 用途 |
| --- | --- |
| `PORTAL_FEISHU_APP_ID` / `PORTAL_FEISHU_APP_SECRET` | 飞书自建应用（需开通「网页应用」登录能力，回调地址填 `$PORTAL_EXTERNAL_BASE_URL/callback`） |
| `PORTAL_KEY_PATH` | Ed25519 签名私钥 PEM，仓库外，绝不入库 |
| `PORTAL_SESSION_SECRET` | 会话 Cookie 与登录 state 的 HMAC 密钥 |
| `PORTAL_EXTERNAL_BASE_URL` | 门户对外地址，同时是 JWT 的 iss |
| `PORTAL_COOKIE_SECURE` | HTTPS 部署时置 true |

凭据绝不写进仓库里的任何文件——与 `DSH_*` 同一条安全边界（见根目录 `env.sh.example` 的说明）。

## 测试

```bash
cd portal && pytest -q     # 模拟飞书租户，无网络、无真实凭据
```
