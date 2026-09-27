# 37 · Portal in English, guest console in English, and the guest entry that bounced back

Status: implemented on `fix/portal-redirection-20260927` (2026-09-27), awaiting deploy. Reviewer's decisions:
the portal is **English only**, and the guest instance **defaults to English regardless of the browser**.
Scope: `portal/`, `deploy/render_caddy.py`, `deploy/preflight.sh`, `plugins/src/client/`, their tests, and
the docs that describe them.

Reported on `https://portal.47.130.178.176.sslip.io/`:

1. The login portal is not fully English (the hackathon, NUS ISS Singapore, expects English).
2. "Continue as guest" never reaches the guest console's home page.

A third problem was found while verifying: the guest console opened in Chinese on a zh-CN browser.

---

## 1. Findings

### 1.1 Guest entry: a cached 301 from the seat era sends the browser back to the portal

**Root cause.** From 2026-09-20 (`592195c`, seat isolation) to 2026-09-26 (`69b55ee`, public demo)
the apex site was rendered as

```caddy
47.130.178.176.sslip.io {
    redir https://portal.47.130.178.176.sslip.io{uri} permanent   # 301, no Cache-Control
}
```

Browsers cache a 301 without an expiry and don't ask the server again. Chrome keeps it in the HTTP cache
indefinitely. Any browser that opened the apex during that week holds `https://<apex>/ → 301 →
https://portal.<apex>/`.

The guest flow before the fix:

```
portal /guest                     200 handover page (portal/src/portal_app/main.py, pages.entering)
  → https://<apex>/?token=T       dsh web: 303 Location: /  + Set-Cookie dsh-auth-…; SameSite=Strict
  → https://<apex>/               ← cached 301, never reaches the server
  → https://portal.<apex>/        login page again
```

The `?token=` URL is new on every boot, so it always reached the server. The 303 then went to bare `/`,
the exact URL the stale 301 is cached for. The user saw a flash and was back on the login card.

**Evidence.**

| Check | Result |
| --- | --- |
| Live `curl` of the whole chain | Works: `/guest` 200 with the current token, `/?token=` 303 `Location: /` with a Strict cookie, and `/` 200 with the cookie |
| Live, clean browser, clicked "Continue as guest" twice | Lands on the guest console both times |
| Local repro: a python "apex" served 301 for `/`, was visited once, then switched to dsh behaviour (`/?token=` → 303 `/`) | Browser ends on the **portal**. The server log shows `GET /?token=abc` and no following `GET /`, so the 301 came from the cache |
| Same repro behind real Caddy with the fix (§2.2) | Token entry lands on the guest home, and bare `/` reaches the server again (cache purged) |
| `git log -S permanent -- deploy/render_caddy.py` | Introduced in `592195c` (2026-09-20) |

**Ruled out:**

- Same-site cookie loss: `sslip.io` is not on the Public Suffix List, so `portal.<apex>` and `<apex>` are
  same-site.
- Stale or missing launch token: the portal serves the current token, a bad token is a plain 401 with no
  loop, and the token is reusable within a boot.
- The portal session: `/guest` ignores it.

**Contributing risks, all fixed:**

- R1. The seat-mode apex still rendered `permanent`. Turning the guest unit off and on again would have
  poisoned a new set of browsers.
- R2. The loop guard only checked `token == ""`. Any new landing URL that 401s would have looped through
  `/__enter`.
- R3. The restarting page (nightly reset, every deploy) was half Chinese.

### 1.2 Portal language: page copy was hard-coded Chinese

There was no locale logic. Every page in `portal/src/portal_app/pages.py` had `lang="zh-CN"` and Chinese copy,
and the browser-facing errors in `portal/src/portal_app/main.py` were Chinese. Backend text that reaches
portal pages (`/identity/console-access` `detail`) was already English.

### 1.3 Guest console language: the English default never fired on the public page

`plugins/src/client/index.tsx` already defaults a user with no saved preference to English (#110), but only
after the Host settings document loads. dsh gives the settings scope only to **loopback** pages. The page
hostname must be `localhost`, `[::1]` or `127.x.x.x` (`isLoopbackHostname` in
`dsh-client-connection/lib/client.js`). Everywhere else the scope is memory-only and never reports a
loaded section.

So on the public apex the #110 default never ran, and dsh's provisional locale, taken from
`navigator.languages`, won. The live guest console opened in Chinese on a zh-CN browser, sample-notebook
title included (`sampleNotebookTitle` in `ui.ts` is a bilingual label, so it follows the locale). The
sample data's field names are data and stay as written.

---

## 2. What changed

### 2.1 Portal: English only

- `pages.py`: `lang="en"` on every page. All copy is English. Section labels are written in sentence case
  and uppercased by CSS, so screen readers read words, not letters. The CJK font fallbacks stay because
  Feishu display names can be Chinese.
- `main.py`: every `error(...)`, `blocked(...)` and `ConsoleUnavailable(...)` message is English. Code
  comments are unchanged.
- No locale switch, by decision. The portal is an edge page with no framework, and the rubric does not
  score a second language.

| Before | After |
| --- | --- |
| 统一登录门户 · 选择登录方式 | Sign-in portal · Choose how to sign in |
| 飞书登录 | Sign in with Feishu (Lark) |
| 以访客身份进入 · Continue as guest (+ bilingual note) | Continue as guest (+ English note) |
| 进入 {app} · 退出登录 | Open {app} · Sign out |
| 出错了 · 返回首页重新登录 → | Something went wrong · Back to sign-in → |
| 返回门户首页 → | Back to the portal → |
| 需要先登录，正在跳转… | Sign-in required. Taking you to the portal… |
| 演示实例正在启动… (bilingual) | The demo is starting. This page retries in 15 seconds. |
| 正在进入 BridgeFlow AI…… | Opening BridgeFlow AI… |
| 13 error titles and details in `main.py` | English equivalents, same meaning (e.g. "This is not a refusal: the system could not confirm your access.") |

### 2.2 Guest entry survives a stale 301 (`deploy/render_caddy.py`)

(a) **A dedicated handle for the token exchange**, matched before the catch-all in `demo_site()`:

```caddy
@token_entry {
    path /
    query token=*
}
handle @token_entry {
    reverse_proxy 127.0.0.1:3090 {
        header_down Clear-Site-Data "\"cache\""
        header_down Location "^/$" "/?entered=1"
    }
}
```

- `Clear-Site-Data: "cache"` purges the stale 301 from this origin's HTTP cache. It is cache only: `"cookies"`
  would drop the dsh session that the same response sets. It is sent only on this one response, so ordinary
  asset caching is unaffected.
- The `Location` rewrite lands on a URL no stale entry can hold, for browsers that ignore the header. dsh
  serves `/?entered=1` like `/` (verified live: 200 with the cookie).

(b) **Loop guard**: `{query.token} == "" && {query.entered} == ""`. A browser whose cookie did not stick now
sees the 401 instead of circling through `/__enter`.

(c) **No permanent redirects**: the seat-mode apex is `redir https://portal.<domain>{uri} 302`. The front
door changes with a unit toggle, so nothing Caddy answers may be cacheable forever.

`deploy/preflight.sh` gains `apex demo token exchange purges stale redirects`. It fetches this boot's token
URL from `/__enter` and requires `303`, `location: /?entered=1` and `clear-site-data: "cache"`. Before
deploy it correctly fails against the live instance.

No portal code change was needed for this problem: `/guest`, `handover()` and `pages.entering()` were
correct.

### 2.3 Guest console defaults to English (`plugins/src/client/`)

- New `guest-locale.ts`, with no imports so it is testable without a browser:
  - `applyGuestLocale()` sets the locale through `setLocale` (the locale plugin's only write entry) to the
    guest's remembered choice if it is still selectable, otherwise `en`.
  - After that it records every later `locale/change` in `localStorage['bridgeflow.guest.locale']`.
- `guest.tsx`: the `/config` read is now `guestMode()`, a single promise shared by `useGuestMode` and plugin
  activation.
- `index.tsx`: in guest mode, `apply()` calls `applyGuestLocale` off that promise before the shell mounts.
  The same promise resolves this first, so the auto-opened sample notebook is created with its English
  title. The #110 default for staff consoles is unchanged.
- **Default, not a lock.** A guest who picks 中文 in Settings → General keeps it across reloads. On a
  non-loopback page dsh holds a choice only for the page's lifetime, which is why this browser's storage
  remembers it. Storage that is missing or refuses never blocks the default.

---

## 3. Verification done

| What | Result |
| --- | --- |
| `cd portal && pytest -q` | 49 passed. New: `test_every_portal_page_is_english` renders all eight page shapes and allows no CJK outside `<style>`. `test_error_pages_from_routes_are_english` hits three real error routes. Chinese Feishu profile names stay in fixtures as data |
| `cd backend && pytest -q tests/test_deploy_config.py` | 16 passed. New: `test_no_rendered_shape_issues_a_permanent_redirect` and `test_the_demo_token_exchange_purges_a_stale_redirect_and_cannot_loop`. `caddy validate` runs on both shapes |
| `ruff check` (portal, deploy test) | Clean |
| `pnpm run typecheck` · `pnpm run build` | Clean |
| `pnpm test` | 118/120. New `guest-locale.test.ts` 5/5. The 2 failures are pre-existing and unrelated: `dsh-preflight.test.ts` compares `/var/…` with macOS's `/private/var/…` |
| Poisoned-cache browser journey (python "dsh" behind real Caddy with the new config) | Old config: bounced to the portal. New config: lands on the guest home, and bare `/` is un-poisoned |
| Local guest instance (`run.sh --guest`) opened on `http://bf.localhost:3190` (non-loopback to dsh, like the public apex) in a **zh-CN** browser | `<html lang="en">`, English UI, notebook "Business demo · monthly review (fictional concrete supplier, 2024-07)". Switched to 中文 and reloaded: stays 中文 (`bridgeflow.guest.locale=zh`) |
| `bash -n deploy/preflight.sh` | OK |

Not verifiable before deploy: Safari's handling of `Clear-Site-Data`. The `?entered=1` rewrite covers guest
entry either way (§4 step 5).

---

## 4. Operations guide: rolling this out to the live instance

Nothing in `env.sh` changes, and no unit needs enabling. `deploy.sh` already does the rest on every deploy:

- re-renders the Caddyfile and reloads Caddy only when it changed;
- rebuilds the client bundle;
- restarts the portal and the guest instance.

### Before merging

1. Open the PR and wait for CI green. The `test` job runs backend and portal pytest, plugin typecheck, build
   and unit tests.
2. Optional, to confirm the diagnosis on a browser that fails today: open DevTools → Network, tick
   "Disable cache", then click "Continue as guest". Or use an incognito window. If it lands, this is the bug
   being fixed. Keep one failing browser **untouched** (don't clear its cache) for step 5 below.

### Deploy

3. Merge to `main`. The `deploy` job runs `deploy/deploy.sh` over SSH (`DEPLOY_ENABLED=true`). For a
   manual deploy on the instance:

   ```bash
   cd ~/Hackathon2026/BridgeFlow-AI
   bash deploy/deploy.sh origin/main 47.130.178.176.sslip.io
   ```

   Expect the line `Caddyfile updated and caddy reloaded` and a final `deployed <sha>`.
   The guest instance restarts, which is also its nightly-style reset: sample data only, no loss. For about
   15–30 s the portal's `/guest` shows the English "The demo is starting" page and retries on its own.

   If `caddy reload` rejects the new file, Caddy keeps serving the old config and the deploy continues.
   Check with:

   ```bash
   sudo caddy validate --adapter caddyfile --config /etc/caddy/Caddyfile
   journalctl -u caddy -n 50 --no-pager
   ```

   The new config was validated with Caddy v2.11.4. If the instance's `caddy version` is much older and the
   validate step rejects `header_down Location "^/$" …` (a find/replace form), upgrade Caddy from its
   official apt repository before redeploying.

### Verify

4. Run preflight on the instance. Every line should be `ok`, including the new
   `apex demo token exchange purges stale redirects`:

   ```bash
   bash deploy/preflight.sh 47.130.178.176.sslip.io
   ```

5. The browser that failed before (cache not cleared): open `https://portal.47.130.178.176.sslip.io/` and
   click **Continue as guest**. It should land on the guest console with the address
   `/?entered=1#bridgeflow…`. Then type the bare `https://47.130.178.176.sslip.io/`: it should now open the
   console, not the portal, which proves the purge. Repeat in Safari and note the result. If Safari still
   jumps to the portal on the bare URL, guest entry itself must still work through the rewrite.
6. Language checks:
   - The portal's anonymous page, signed-in page and one error page (e.g.
     `https://portal.47.130.178.176.sslip.io/callback`) are all English.
   - In a browser set to Chinese, the guest console opens in English, including the sample-notebook title.
   - Settings → General → 中文 → reload: it stays 中文 for that browser.
7. Loop guard from any machine:

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -H 'Accept: text/html' 'https://47.130.178.176.sslip.io/?entered=1'
   ```

   It should print `401`, not a `302` to `/__enter`.

### Rollback

8. `bash deploy/deploy.sh <previous-sha> 47.130.178.176.sslip.io` restores the old Caddyfile, portal and
   bundle. Rolling back brings the bug back only for browsers that still hold the old 301. Browsers that
   passed through the new token exchange once are already purged.

### After it passes

9. `README.md` (lines 49, 74, 130) and `README.zh.md` still say the public guest entry is not live. It is.
   Update them together with `docs/00-status.md`'s public guest entry row, and add one line to
   `HANDOFF.md` with the preflight result.

---

## 5. Out of scope

- A portal i18n framework or `Accept-Language` negotiation (English only, by decision).
- Changing dsh web's token handler, or making dsh treat proxied pages as loopback (not forking dsh, per
  CLAUDE.md).
- Staff consoles on public hosts have the same #110 gap: they follow the browser language, because the
  settings scope is withheld there too. The guest default does not apply to them. If staff should also
  default to English, that is a separate decision.
- Chinese field names inside the sample data. They are data, not UI.

---

## 6. Follow-up: English sample data on the guest instance (2026-09-27)

Reviewer's decisions: a **parallel English sample set for the guest instance only**, and
backend-written text shown in the demo follows the interface language.

### What changed

- **`data/demo_en/`** is the English translation of every built-in sample:
  - the four cases and the two earlier months;
  - the integration declaration and its templates;
  - the demo dictionary (incl. quotation and review contract);
  - the discovery sample project and its policies;
  - the Filling & handoff catalogue and sample.

  It is generated by `scripts/make_english_samples.py` from the Chinese originals plus one glossary
  (`labels.en.yaml`, overridden by `data/demo_en/glossary.yaml`). Only words change. See
  [`data/demo_en/README.md`](../data/demo_en/README.md) for the rules.
- **Declared, not hard-coded:**
  - `demo_cases_path`, `discovery_sample_path` and `workflow_samples_path` are new settings.
  - Sample file names come from the case registry's `file_name`, and department labels from the
    integration declaration. `batches.py` no longer writes `模拟-` or 生产部.
  - `start_web.py --guest` reads a **sample set** (`BRIDGEFLOW_GUEST_SAMPLE_SET`, default
    `data/demo_en/sample-set.yaml`) and points every setting at it. The Chinese set is
    `data/mock_business/sample-set.yaml`.
- **Backend text follows the interface language:**
  - Handoff board summaries (`workflow/board.py`) and the review's fixed limitation are now
    English, like every other backend sentence. The Chinese interface reads them in Chinese
    (`zh-messages.ts`: `translateBoard`, plus one rule).
  - The master workbook and the Word report take `?lang=` from the interface: sheet names,
    headers, headings and file names.
- **`.gitignore`** now tracks `data/demo_en/**/*.xlsx`. Without it the English workbooks would never
  reach the instance.

### Verified

| What | Result |
| --- | --- |
| Backend, full suite | 797 passed. The one deselected test, `test_dsh_provider…same_native_installation`, fails on `main` too because `deepseek_harness` is not installed locally |
| `tests/test_english_samples.py` (11) | Each of the four cases gives an identical outcome in both sets: status, rows, quarantined rows, issue kinds, column questions, blockers, and all 10 review values. The English tour open question is *Customer name*. The renamed column is asked as `cumulative_collections`. Discovery → scope → workflow sample works in English with no Chinese on the board. The English report and master workbook contain no Chinese. `--check` passes and the manifest matches |
| Plugins | Typecheck and build clean; unit tests 118/120, the 2 failures are the pre-existing macOS `/private/var` path tests. `gloss.test.ts` covers the board clauses in Chinese |
| Local guest (`run.sh --guest`, non-loopback host, zh-CN browser) | Banner line `samples from data/demo_en`. Files `Sample-Production-2024-07.xlsx` …; the master table and open question fully English; no CJK anywhere on the page |

The browser journeys `round1-journey.mjs` and `workflow-journey.mjs` were updated for the English
download name and board clause, but were not re-run here (they need the private dsh and a full
local stack).

### Operations: rolling it out

No `env.sh` change is needed; the English set is the guest default.

1. Merge to `main`. CI tests run, then `deploy.sh` pulls, rebuilds the client and restarts the guest
   unit. That restart wipes `data/guest/` and loads the English set.
2. On the instance, confirm the guest picked the English set:

   ```bash
   journalctl -u bridgeflow-guest -n 200 --no-pager | grep "samples from"
   ```

   It should print `… samples from data/demo_en`.
3. In a fresh browser, open `https://47.130.178.176.sslip.io/`:
   - the sources read `Sample-Production-2024-07.xlsx`;
   - Data → **Cross-department master** → **Open questions** reads *Customer name differs between
     departments*;
   - **More sample cases** titles are English;
   - **Download master xlsx** gives `Cross-department-master-….xlsx` with sheets *Master / Open items /
     Conventions*.
4. Staff seats are unaffected. They keep `data/company_templates/integration.yaml` and the
   Chinese samples.

**Rollback:** to put the guest back on the Chinese originals without a code rollback, add this to
`env.sh`, then run `sudo systemctl restart bridgeflow-guest`:

```bash
export BRIDGEFLOW_GUEST_SAMPLE_SET=data/mock_business/sample-set.yaml
```

**Changing a sample later:** edit the Chinese original (or `data/demo_en/glossary.yaml` for a
word), then run `python scripts/make_english_samples.py` and commit both. CI's
`test_english_samples.py` fails if the English set is stale.
