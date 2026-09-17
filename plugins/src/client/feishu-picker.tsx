/**
 * Feishu Drive browsing with the signed-in user's own permissions (docs/30).
 *
 * The list answers carry metadata only — token, name, type, size, mtime — so this
 * panel stays bounded no matter how large the files behind it are. Sheets and
 * bitables are listed but not importable this phase; picking one is a dead end
 * that says so, not a silent skip.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, describeError, feishuUserToken, useUI, type Summary } from './ui.ts'
import { departments } from './workspace.tsx'

type DriveItem = { token: string; name: string; type: string; size: number; modified_time: string }
type DrivePage = { files: DriveItem[]; has_more: boolean; next_page_token: string }

// Wiki (docs/31): a node is browsed by its own token but its file body lives at
// obj_token; importing submits obj_token, navigating submits the node token.
type WikiSpace = { space_id: string; name: string; description: string }
type SpacePage = { spaces: WikiSpace[]; has_more: boolean; next_page_token: string }
type WikiNode = { token: string; obj_token: string; obj_type: string; title: string; has_child: boolean }
type WikiNodePage = { nodes: WikiNode[]; has_more: boolean; next_page_token: string }

async function listFolder(folder: string, pageToken = ''): Promise<DrivePage> {
  const token = await feishuUserToken()
  return api<DrivePage>('/tools/feishu-list', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
    body: JSON.stringify({ folder_token: folder, page_token: pageToken }),
  })
}

async function listSpaces(pageToken = ''): Promise<SpacePage> {
  const token = await feishuUserToken()
  return api<SpacePage>('/tools/feishu-wiki-spaces', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
    body: JSON.stringify({ page_token: pageToken }),
  })
}

async function listNodes(spaceId: string, parent: string, pageToken = ''): Promise<WikiNodePage> {
  const token = await feishuUserToken()
  return api<WikiNodePage>('/tools/feishu-wiki-list', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
    body: JSON.stringify({ space_id: spaceId, parent_node_token: parent, page_token: pageToken }),
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
  // Navigation changes folder while a list call is in flight; a late answer must
  // not overwrite the new location's page (or load-more merge into it).
  const folderRef = useRef(folder)
  folderRef.current = folder
  const load = (pageToken = '') => {
    setError('')
    const at = folder
    listFolder(at, pageToken)
      .then(p => { if (folderRef.current === at) setPage(prev => pageToken && prev ? { ...p, files: [...prev.files, ...p.files] } : p) })
      .catch(e => { if (folderRef.current !== at) return; setPage(null); setError(describeError(e, t)) })
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

const MORE = (page: { has_more: boolean }, loadMore: () => void, t: (k: string) => string) =>
  page.has_more ? <button className="bf-hint" onClick={loadMore}>{t('feishuMore')}</button> : null

/** Space list, then a lazily-loaded node tree inside the chosen space. */
function WikiBrowser({ row, currentLocation, extra }: {
  row: (node: WikiNode, enter: (node: WikiNode) => void) => ReactNode
  currentLocation?: (spaceId: string, parentToken: string) => void
  extra?: (page: WikiNodePage, loadMore: () => void) => ReactNode
}) {
  const { t } = useUI()
  const [space, setSpace] = useState<WikiSpace | null>(null)
  const [trail, setTrail] = useState<WikiNode[]>([])
  const [spaces, setSpaces] = useState<SpacePage | null>(null)
  const [page, setPage] = useState<WikiNodePage | null>(null)
  const [error, setError] = useState('')
  const parent = trail.length ? trail[trail.length - 1]!.token : ''
  // Same late-answer guard as Browser: a response is only live while the
  // space/parent (or space-less state) that asked for it is still current.
  const locationRef = useRef({ space: '', parent: '' })
  locationRef.current = { space: space?.space_id ?? '', parent }
  const loadSpaces = (pageToken = '') => {
    setError('')
    listSpaces(pageToken)
      .then(p => { if (!locationRef.current.space) setSpaces(prev => pageToken && prev ? { ...p, spaces: [...prev.spaces, ...p.spaces] } : p) })
      .catch(e => { if (locationRef.current.space) return; setSpaces(null); setError(describeError(e, t)) })
  }
  const loadNodes = (pageToken = '') => {
    if (!space) return
    setError('')
    const at = locationRef.current
    listNodes(at.space, at.parent, pageToken)
      .then(p => { const now = locationRef.current; if (now.space === at.space && now.parent === at.parent) setPage(prev => pageToken && prev ? { ...p, nodes: [...prev.nodes, ...p.nodes] } : p) })
      .catch(e => { const now = locationRef.current; if (now.space !== at.space || now.parent !== at.parent) return; setPage(null); setError(describeError(e, t)) })
  }
  useEffect(() => { if (!space) loadSpaces() }, [space])
  useEffect(() => { if (space) loadNodes() }, [space, parent])
  useEffect(() => { currentLocation?.(space?.space_id ?? '', parent) }, [space, parent])
  const back = () => { setSpace(null); setTrail([]); setPage(null) }
  return <div className="bf-feishu-browser">
    <nav className="bf-feishu-crumbs" aria-label={t('feishuWiki')}>
      <button aria-current={!space ? 'true' : undefined} onClick={back}>{t('feishuSpaces')}</button>
      {space && <button aria-current={!trail.length ? 'true' : undefined} onClick={() => setTrail([])}>{space.name}</button>}
      {trail.map((node, i) => <button key={node.token} aria-current={i === trail.length - 1 ? 'true' : undefined} onClick={() => setTrail(trail.slice(0, i + 1))}>{node.title}</button>)}
    </nav>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!error && !space && !spaces && <p role="status">{t('loading')}</p>}
    {!error && !space && spaces && <>
      {!spaces.spaces.length && <p className="bf-hint">{t('feishuSpacesEmpty')}</p>}
      <ul className="bf-resource-list">{spaces.spaces.map(item =>
        <li key={item.space_id}><button className="bf-feishu-folder" onClick={() => setSpace(item)}><span aria-hidden="true">▸</span> {item.name}</button></li>)}</ul>
      {spaces.has_more && <button className="bf-hint" onClick={() => loadSpaces(spaces.next_page_token)}>{t('feishuMore')}</button>}
    </>}
    {!error && space && !page && <p role="status">{t('loading')}</p>}
    {!error && space && page && <>
      {!page.nodes.length && <p className="bf-hint">{t('feishuEmpty')}</p>}
      <ul className="bf-resource-list">{page.nodes.map(node => <li key={node.token}>{row(node, item => setTrail([...trail, item]))}</li>)}</ul>
      {extra?.(page, () => loadNodes(page.next_page_token))}
    </>}
  </div>
}

/** Pick one file per department from the user's own Drive and import them as a batch. */
export function FeishuImport({ onSaved }: { onSaved: (batch: Summary) => void }) {
  const { t } = useUI()
  const [source, setSource] = useState<'drive' | 'wiki'>('drive')
  const [assign, setAssign] = useState<Partial<Record<string, DriveItem>>>({})
  const [period, setPeriod] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const chosen = departments.filter(d => assign[d])
  const importable = (item: DriveItem) => item.type === 'file' && /\.(csv|xlsx)$/i.test(item.name)
  const importableNode = (node: WikiNode) => node.obj_type === 'file' && /\.(csv|xlsx)$/i.test(node.title)
  const usedBy = (token: string) => chosen.find(d => assign[d]?.token === token)
  const choose = (token: string, name: string, dept: string) => setAssign(prev => {
    const next = { ...prev }
    for (const d of departments) if (next[d]?.token === token) delete next[d]
    if (dept) next[dept] = { token, name, type: 'file', size: 0, modified_time: '' }
    return next
  })
  const deptSelect = (token: string, name: string) =>
    <select aria-label={t('feishuAssign')} value={usedBy(token) ?? ''} onChange={e => choose(token, name, e.target.value)}>
      <option value="">—</option>
      {departments.map(d => <option key={d} value={d}>{t(d)}</option>)}
    </select>
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
    <div className="bf-feishu-mode">
      <button aria-pressed={source === 'drive'} onClick={() => setSource('drive')}>{t('feishuRoot')}</button>
      <button aria-pressed={source === 'wiki'} onClick={() => setSource('wiki')}>{t('feishuWiki')}</button>
    </div>
    <p className="bf-hint">{t(source === 'drive' ? 'feishuPickHelp' : 'feishuWikiHelp')}</p>
    {source === 'drive' && <Browser extra={(page, loadMore) => MORE(page, loadMore, t)} row={(item, enter) => {
      if (item.type === 'folder') {
        return <button className="bf-feishu-folder" onClick={() => enter(item)}><span aria-hidden="true">▸</span> {item.name}</button>
      }
      if (!importable(item)) {
        return <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {item.name} <small>{t('feishuUnsupported')}</small></span>
      }
      return <span className="bf-feishu-item"><span aria-hidden="true">▤</span> {item.name} {deptSelect(item.token, item.name)}</span>
    }} />}
    {source === 'wiki' && <WikiBrowser extra={(page, loadMore) => MORE(page, loadMore, t)} row={(node, enter) => {
      const pickable = importableNode(node)
      return <span className="bf-feishu-item" data-disabled={pickable || node.has_child ? undefined : 'true'}>
        {node.has_child
          ? <button className="bf-feishu-folder" onClick={() => enter(node)}><span aria-hidden="true">▸</span> {node.title}</button>
          : <><span aria-hidden="true">▤</span> {node.title}</>}
        {!pickable && !node.has_child && <small>{t('feishuUnsupported')}</small>}
        {pickable && deptSelect(node.obj_token, node.title)}
      </span>
    }} />}
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
  const [target, setTarget] = useState<'drive' | 'wiki'>('drive')
  const [folder, setFolder] = useState('')
  const [wikiLoc, setWikiLoc] = useState({ space: '', parent: '' })
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  async function run() {
    setBusy(true); setError('')
    try {
      const token = await feishuUserToken()
      const body = target === 'drive'
        ? { batch_id: batchId, folder_token: folder, report_id: reportId }
        : { batch_id: batchId, report_id: reportId, wiki_space_id: wikiLoc.space, parent_wiki_token: wikiLoc.parent }
      const result = await api<{ filename: string }>('/tools/feishu-upload-user', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-feishu-user-token': token },
        body: JSON.stringify(body),
      })
      onDone(result.filename)
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  if (!reportId) return <p className="bf-hint">{t('feishuNoReport')}</p>
  const wikiNodeRow = (node: WikiNode, enter: (node: WikiNode) => void) =>
    node.has_child
      ? <button className="bf-feishu-folder" onClick={() => enter(node)}><span aria-hidden="true">▸</span> {node.title}</button>
      : <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {node.title}</span>
  return <section className="bf-feishu-upload" aria-label={t('feishuUpload')}>
    <div className="bf-feishu-mode" aria-label={t('feishuTarget')}>
      <button aria-pressed={target === 'drive'} onClick={() => setTarget('drive')}>{t('feishuRoot')}</button>
      <button aria-pressed={target === 'wiki'} onClick={() => setTarget('wiki')}>{t('feishuWiki')}</button>
    </div>
    {target === 'drive'
      ? <Browser currentFolder={setFolder} extra={(page, loadMore) => MORE(page, loadMore, t)} row={(item, enter) =>
          item.type === 'folder'
            ? <button className="bf-feishu-folder" onClick={() => enter(item)}><span aria-hidden="true">▸</span> {item.name}</button>
            : <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {item.name}</span>
        } />
      : <WikiBrowser currentLocation={(space, parent) => setWikiLoc({ space, parent })} extra={(page, loadMore) => MORE(page, loadMore, t)} row={wikiNodeRow} />}
    <button className="bf-primary" disabled={busy || (target === 'wiki' && !wikiLoc.space)} onClick={() => void run()}>
      {busy ? t('busy') : t(target === 'drive' ? 'feishuUploadHere' : 'feishuUploadWikiHere')}
    </button>
    {error && <p role="alert" className="bf-error">{error}</p>}
  </section>
}

/** Upload a local file into a wiki position the user picked (docs/31). */
export function WikiFileUpload() {
  const { t } = useUI()
  const [loc, setLoc] = useState({ space: '', parent: '' })
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [done, setDone] = useState('')
  async function run() {
    const file = fileRef.current?.files?.[0]
    if (!file || !loc.space) return
    setBusy(true); setError(''); setDone('')
    try {
      const token = await feishuUserToken()
      const body = new FormData()
      body.set('space_id', loc.space)
      body.set('parent_wiki_token', loc.parent)
      body.set('file', file)
      const result = await api<{ name: string }>('/tools/feishu-wiki-upload', {
        method: 'POST', headers: { 'x-feishu-user-token': token }, body,
      })
      setDone(result.name)
      if (fileRef.current) fileRef.current.value = ''
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  return <section className="bf-feishu-upload" aria-label={t('feishuUploadFileWiki')}>
    <WikiBrowser currentLocation={(space, parent) => setLoc({ space, parent })} extra={(page, loadMore) => MORE(page, loadMore, t)} row={(node, enter) =>
      node.has_child
        ? <button className="bf-feishu-folder" onClick={() => enter(node)}><span aria-hidden="true">▸</span> {node.title}</button>
        : <span className="bf-feishu-item" data-disabled="true"><span aria-hidden="true">▤</span> {node.title}</span>
    } />
    <div className="bf-feishu-go">
      <input type="file" ref={fileRef} aria-label={t('feishuPickFile')} />
      <button className="bf-primary" disabled={busy || !loc.space} onClick={() => void run()}>
        {busy ? t('busy') : t('feishuUploadWikiHere')}
      </button>
    </div>
    {done && <p className="bf-hint" role="status">{t('feishuWikiUploaded')} · {done}</p>}
    {error && <p role="alert" className="bf-error">{error}</p>}
  </section>
}
