# 登录门户（portal/）

门户通过飞书 OAuth 验证身份，签发短期应用 JWT，并提供登录后的工作区入口。应用通过门户公布的 JWKS 公钥验签。部署结构和配置边界见[部署说明](../docs/deployment.md)。

## 入口与行为

| 路由 | 行为 |
| --- | --- |
| `GET /` | 显示门户首页和登录状态；启用访客入口后显示访客选项 |
| `GET /login?app=bridgeflow` | 发起飞书登录；有效会话可跳过重复登录 |
| `GET /callback` | 处理 OAuth 回调并设置门户会话 |
| `GET /enter` | 校验登录，进入已分配席位或单控制台；通过交接页面建立原生 Web 会话 |
| `GET /guest` | 进入已配置的独立访客控制台；未启用时返回 404，启动令牌尚未就绪时返回 503 |
| `GET /verify` | 供反向代理验证登录、席位归属及已启用的控制台权限 |
| `GET /token?app=bridgeflow` | 为有效会话签发短期应用 JWT，默认有效期 15 分钟 |
| `GET /.well-known/jwks.json` | 返回验签公钥 |
| `GET /me`、`POST /logout`、`GET /health` | 当前身份、退出登录和运行状态 |

配置席位池时，获授权用户首次进入会领取空闲席位，后续进入复用该席位。席位满额或需要释放时由管理员处理。席位隔离不等于完整的业务数据多租户隔离，见[已知限制](../docs/limitations.md)。

## 本地搭建

以下命令从仓库根目录执行。先完成[安装说明](../docs/setup.md)中的虚拟环境配置：

```bash
source ../.venv/bin/activate
python -m pip install -e 'portal[dev]'
python -m portal_app.keygen "$HOME/Hackathon2026/.portal-key.pem"
```

密钥只在首次配置时生成。编辑本地 `env.sh`，让 `PORTAL_KEY_PATH` 指向该私钥，并填入下表中需要的设置。启动门户：

```bash
source env.sh
python -m uvicorn portal_app.main:app --host 127.0.0.1 --port 8100 --ws none
```

| 环境变量 | 用途 |
| --- | --- |
| `PORTAL_FEISHU_APP_ID` / `PORTAL_FEISHU_APP_SECRET` | 自己的飞书应用凭据；开启网页应用并配置 `$PORTAL_EXTERNAL_BASE_URL/callback` 回调 |
| `PORTAL_KEY_PATH` | 仓库外的 Ed25519 签名私钥 |
| `PORTAL_SESSION_SECRET` | 门户会话与登录 state 的 HMAC 密钥 |
| `PORTAL_EXTERNAL_BASE_URL` | 门户对外地址，同时是应用 JWT 的签发方标识 |
| `PORTAL_APPS_PATH` | 应用注册配置；默认 `portal/apps.yaml` 仅用于 localhost 开发 |
| `PORTAL_COOKIE_SECURE` / `PORTAL_COOKIE_DOMAIN` | HTTPS 安全 Cookie 与需要共享登录状态的父域名 |
| `PORTAL_CONSOLE_CHECK_URL` | 后端 `/identity/console-access` 地址；不设置时不检查角色的控制台访问权限 |
| `PORTAL_DSH_TOKEN_FILE` | 单控制台的启动令牌文件；默认从 `DSH_HOME` 派生 |
| `PORTAL_SEATS_PATH` / `PORTAL_SEAT_BASE_DOMAIN` / `PORTAL_SEAT_ASSIGNMENTS` | 可选席位池配置、基础域名及私有席位分配文件 |
| `PORTAL_GUEST_APP_URI` / `PORTAL_GUEST_TOKEN_FILE` | 可选访客入口及访客启动令牌文件；需同时配置且令牌可读 |

应用注册声明 audience、回调地址、工作区地址和允许的来源。生产环境通过 `PORTAL_APPS_PATH` 指向私有配置，不在版本控制中填写真实站点信息。后端还需设置 `PORTAL_BASE_URL` 才会启用身份校验。

凭据通过启动 shell 导出；可以保存在被 Git 忽略的本地 `env.sh` 中，不得提交。`env.sh.example` 只放空值或占位示例。

## 测试

从仓库根目录执行：

```bash
python -m pytest portal/tests -q
```

测试使用模拟飞书响应，不需要真实租户凭据。
