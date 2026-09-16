/**
 * Feishu Drive browsing with the signed-in user's own permissions (docs/30).
 *
 * The list answers carry metadata only — token, name, type, size, mtime — so this
 * panel stays bounded no matter how large the files behind it are. Sheets and
 * bitables are listed but not importable this phase; picking one is a dead end
 * that says so, not a silent skip.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { api, describeError, feishuUserToken, useUI, type Summary } from './ui.ts'
import { departments } from './workspace.tsx'

type DriveItem = { token: string; name: string; type: string; size: number; modified_time: string }
type DrivePage = { files: DriveItem[]; has_more: boolean; next_page_token: string }

async function listFolder(folder: string, pageToken = ''): Promise<DrivePage> {
  const token = await feishuUserToken()
  return api<DrivePage>('/tools/feishu-list', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
    body: JSON.stringify({ folder_token: folder, page_token: pageToken }),
  })
}

/** Breadcrumb + paged folder listing. `row` renders one item; `currentFolder` gets the open folder's token. */
function Browser({ row, currentFolder, extra }: {
  row: (item: DriveItem, enter: (item: DriveItem) => void) => ReactNode
  currentFolder?: (token: string) => void
  extra?: (page: DrivePage, loadMore: () => void) => ReactNode
}) {
  const { t } = useUI()
  const [trail, setTrail] = useState<DriveItem[]>([])
  const [page, setPage] = useState<DrivePage | null>(null)
  const [error, setError] = useState('')
  const folder = trail.length ? trail[trail.length - 1]!.token : ''
  const load = (pageToken = '') => {
    setError('')
    listFolder(folder, pageToken).then(setPage).catch(e => { setPage(null); setError(describeError(e, t)) })
  }
  useEffect(() => { load() }, [folder])
  useEffect(() => { currentFolder?.(folder) }, [folder])
  const enter = (item: DriveItem) => setTrail([...trail, item])
  const jump = (index: number) => setTrail(trail.slice(0, index))
  return <div className="bf-feishu-browser">
    <nav className="bf-feishu-crumbs" aria-label={t('feishuRoot')}>
      <button aria-current={!trail.length ? 'true' : undefined} onClick={() => jump(0)}>{t('feishuRoot')}</button>
      {trail.map((item, i) => <button key={item.token} aria-current={i === trail.length - 1 ? 'true' : undefined} onClick={() => jump(i + 1)}>{item.name}</button>)}
    </nav>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!error && !page && <p role="status">{t('loading')}</p>}
    {page && <>
      {!page.files.length && <p className="bf-hint">{t('feishuEmpty')}</p>}
      <ul className="bf-resource-list">{page.files.map(item => <li key={item.token}>{row(item, enter)}</li>)}</ul>
      {extra?.(page, () => load(page.next_page_token))}
    </>}
  </div>
}

const MORE = (page: DrivePage, loadMore: () => void, t: (k: string) => string) =>
  page.has_more ? <button className="bf-hint" onClick={loadMore}>{t('feishuMore')}</button> : null

/** Pick one file per department from the user's own Drive and import them as a batch. */
export function FeishuImport({ onSaved }: { onSaved: (batch: Summary) => void }) {
  const { t } = useUI()
  const [assign, setAssign] = useState<Partial<Record<string, DriveItem>>>({})
  const [period, setPeriod] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const chosen = departments.filter(d => assign[d])
  const importable = (item: DriveItem) => item.type === 'file' && /\.(csv|xlsx)$/i.test(item.name)
  const usedBy = (token: string) => chosen.find(d => assign[d]?.token === token)
  async function run() {
    if (!period || !chosen.length) return
    setBusy(true); setError('')
    try {
      const token = await feishuUserToken()
      const result = await api<{ batch: Summary }>('/tools/feishu-import-user', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
        body: JSON.stringify({ period, files: chosen.map(d => ({ department: d, file_token: assign[d]!.token })) }),
      })
      onSaved(result.batch)
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  return <section className="bf-feishu-import" aria-label={t('feishuPick')}>
    <p className="bf-hint">{t('feishuPickHelp')}</p>
    <Browser extra={(page, loadMore) => MORE(page, loadMore, t)} row={(item, enter) => {
      if (item.type === 'folder') {
        return <button className="bf-feishu-folder" onClick={() => enter(item)}><span aria-hidden="true">▸</span> {item.name}</button>
      }
      if (!importable(item)) {
        return <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {item.name} <small>{t('feishuUnsupported')}</small></span>
      }
      const dept = usedBy(item.token)
      return <span className="bf-feishu-item"><span aria-hidden="true">▤</span> {item.name}
        <select aria-label={t('feishuAssign')} value={dept ?? ''}
          onChange={e => setAssign(prev => {
            const next = { ...prev }
            for (const d of departments) if (next[d]?.token === item.token) delete next[d]
            if (e.target.value) next[e.target.value] = item
            return next
          })}>
          <option value="">—</option>
          {departments.map(d => <option key={d} value={d}>{t(d)}</option>)}
        </select>
      </span>
    }} />
    <div className="bf-feishu-go">
      <input type="month" aria-label={t('month')} value={period} onChange={e => setPeriod(e.target.value)} required />
      <button className="bf-primary" disabled={busy || !period || !chosen.length} onClick={() => void run()}>
        {busy ? t('busy') : `${t('feishuImportGo')} (${chosen.length})`}
      </button>
    </div>
    {error && <p role="alert" className="bf-error">{error}</p>}
  </section>
}

/** Pick a folder in the user's own Drive and upload the saved report into it. */
export function FeishuUpload({ batchId, reportId, onDone }: { batchId: string; reportId: string | null; onDone: (filename: string) => void }) {
  const { t } = useUI()
  const [folder, setFolder] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function run() {
    setBusy(true); setError('')
    try {
      const token = await feishuUserToken()
      const result = await api<{ filename: string }>('/tools/feishu-upload-user', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
        body: JSON.stringify({ batch_id: batchId, folder_token: folder, report_id: reportId }),
      })
      onDone(result.filename)
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  if (!reportId) return <p className="bf-hint">{t('feishuNoReport')}</p>
  return <section className="bf-feishu-upload" aria-label={t('feishuUpload')}>
    <Browser currentFolder={setFolder} extra={(page, loadMore) => MORE(page, loadMore, t)} row={(item, enter) =>
      item.type === 'folder'
        ? <button className="bf-feishu-folder" onClick={() => enter(item)}><span aria-hidden="true">▸</span> {item.name}</button>
        : <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {item.name}</span>
    } />
    <button className="bf-primary" disabled={busy} onClick={() => void run()}>{busy ? t('busy') : t('feishuUploadHere')}</button>
    {error && <p role="alert" className="bf-error">{error}</p>}
  </section>
}
