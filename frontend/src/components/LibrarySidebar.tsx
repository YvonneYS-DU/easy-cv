import { useMemo, useRef, useState } from 'react'
import {
  Calendar,
  FilePlus2,
  FileText,
  FolderKanban,
  LoaderCircle,
  Plus,
  Search,
  Upload,
} from 'lucide-react'
import type { ResumeDocument } from '../types/resume'

export type LibrarySortMode = 'time' | 'keyword' | 'project'

export interface ResumeLibraryItem {
  id: string
  title: string
  domain: string
  project: string
  keywords: string[]
  updatedAt: string
  createdAt: string
  document: ResumeDocument
}

interface Props {
  items: ResumeLibraryItem[]
  activeId: string | null
  open?: boolean
  onSelect: (id: string) => void
  onCreateBlank: () => void
  onImportFile: (file: File) => void
  onSubmitInit: (payload: { text: string; project: string; title: string }) => void
  initBusy?: boolean
}

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function extractPreview(doc: ResumeDocument): string {
  const contact = doc.nodes.find((n) => n.type === 'block' && n.kind === 'contact')
  if (contact && contact.type === 'block') {
    const el = document.createElement('div')
    el.innerHTML = contact.html
    const line = el.querySelector('.cv-contact-line')?.textContent?.trim()
    if (line) return line
  }
  const block = doc.nodes.find((n) => n.type === 'block' && n.kind !== 'contact')
  if (block && block.type === 'block') {
    const el = document.createElement('div')
    el.innerHTML = block.html
    return (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80)
  }
  return '空简历'
}

export function LibrarySidebar({
  items,
  activeId,
  open = false,
  onSelect,
  onCreateBlank,
  onImportFile,
  onSubmitInit,
  initBusy = false,
}: Props) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<LibrarySortMode>('time')
  const [initOpen, setInitOpen] = useState(false)
  const [initTitle, setInitTitle] = useState('')
  const [initProject, setInitProject] = useState('')
  const [initText, setInitText] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    let list = [...items]

    if (q) {
      list = list.filter((item) => {
        const hay = [
          item.title,
          item.project,
          item.domain,
          ...item.keywords,
          item.document.nodes
            .filter((n) => n.type === 'block')
            .map((n) => (n.type === 'block' ? n.chip : ''))
            .join(' '),
        ]
          .join(' ')
          .toLowerCase()
        return hay.includes(q)
      })
    }

    if (mode === 'project') {
      list.sort((a, b) => {
        const pa = a.project || '未分类'
        const pb = b.project || '未分类'
        if (pa !== pb) return pa.localeCompare(pb, 'zh-CN')
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      })
    } else if (mode === 'keyword') {
      list.sort((a, b) => {
        if (q) {
          const as = a.title.toLowerCase().includes(q) ? 0 : 1
          const bs = b.title.toLowerCase().includes(q) ? 0 : 1
          if (as !== bs) return as - bs
        }
        return (b.keywords?.length || 0) - (a.keywords?.length || 0)
      })
    } else {
      list.sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
      )
    }

    return list
  }, [items, mode, query])

  const grouped =
    mode === 'project'
      ? filtered.reduce<Record<string, ResumeLibraryItem[]>>((acc, item) => {
          const key = item.project?.trim() || '未分类'
          if (!acc[key]) acc[key] = []
          acc[key].push(item)
          return acc
        }, {})
      : null

  function handleSubmitInit() {
    if (!initText.trim() && !initTitle.trim()) return
    onSubmitInit({
      text: initText.trim(),
      project: initProject.trim(),
      title: initTitle.trim() || '未命名简历',
    })
    setInitText('')
    setInitTitle('')
    setInitProject('')
    setInitOpen(false)
  }

  function renderItem(item: ResumeLibraryItem) {
    const active = item.id === activeId
    return (
      <button
        key={item.id}
        type="button"
        className={`cv-lib-item${active ? ' active' : ''}`}
        onClick={() => onSelect(item.id)}
      >
        <div className="cv-lib-item-top">
          <FileText size={14} className="cv-lib-item-icon" />
          <span className="cv-lib-item-title body-md">{item.title || '未命名简历'}</span>
        </div>
        <div className="cv-lib-item-preview body-xs">{extractPreview(item.document)}</div>
        <div className="cv-lib-item-meta body-xs">
          <span>{formatRelative(item.updatedAt)}</span>
          {item.project ? <span className="cv-lib-pill">{item.project}</span> : null}
        </div>
        {item.keywords.length > 0 ? (
          <div className="cv-lib-tags">
            {item.keywords.slice(0, 3).map((k) => (
              <span key={k} className="cv-lib-tag">
                {k}
              </span>
            ))}
          </div>
        ) : null}
      </button>
    )
  }

  return (
    <aside className={`cv-sidebar${open ? ' open' : ''}`}>
      <div className="cv-sidebar-head">
        <span className="heading-xs">我的简历</span>
        <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
          {items.length}
        </span>
      </div>

      <div className="cv-sidebar-search">
        <div className="cv-search-box">
          <Search size={14} />
          <input
            className="cv-search-input body-md"
            type="search"
            placeholder={
              mode === 'project'
                ? '按项目名搜索…'
                : mode === 'keyword'
                  ? '按关键词搜索…'
                  : '搜索简历…'
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="cv-search-modes">
          <button
            type="button"
            className={`cv-mode-chip body-xs${mode === 'time' ? ' active' : ''}`}
            onClick={() => setMode('time')}
          >
            <Calendar size={12} />
            时间
          </button>
          <button
            type="button"
            className={`cv-mode-chip body-xs${mode === 'keyword' ? ' active' : ''}`}
            onClick={() => setMode('keyword')}
          >
            <Search size={12} />
            关键词
          </button>
          <button
            type="button"
            className={`cv-mode-chip body-xs${mode === 'project' ? ' active' : ''}`}
            onClick={() => setMode('project')}
          >
            <FolderKanban size={12} />
            项目
          </button>
        </div>
      </div>

      <div className="cv-sidebar-init">
        {!initOpen ? (
          <button
            type="button"
            className="cv-init-trigger body-md"
            onClick={() => setInitOpen(true)}
          >
            <Plus size={14} />
            提交文件 / 项目，完成初始化
          </button>
        ) : (
          <div className="cv-init-box">
            <div className="cv-init-box-head">
              <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
                初始化 / 记忆
              </span>
              <button
                type="button"
                className="cv-text-btn body-xs"
                onClick={() => setInitOpen(false)}
              >
                收起
              </button>
            </div>
            <input
              className="cv-input"
              placeholder="简历标题（可选）"
              value={initTitle}
              onChange={(e) => setInitTitle(e.target.value)}
            />
            <input
              className="cv-input"
              placeholder="所属项目（如 RightShip）"
              value={initProject}
              onChange={(e) => setInitProject(e.target.value)}
            />
            <textarea
              className="cv-textarea"
              rows={3}
              placeholder="粘贴简历/项目经历原文，用于初始化记忆…"
              value={initText}
              onChange={(e) => setInitText(e.target.value)}
            />
            <div className="cv-init-actions">
              <button
                type="button"
                className="cv-btn-outline body-xs"
                onClick={() => fileRef.current?.click()}
              >
                <Upload size={12} />
                上传文件
              </button>
              <button
                type="button"
                className="cv-btn-outline body-xs"
                onClick={onCreateBlank}
              >
                <FilePlus2 size={12} />
                空白简历
              </button>
              <button
                type="button"
                className="cv-btn-primary body-xs"
                disabled={initBusy || (!initText.trim() && !initTitle.trim())}
                onClick={handleSubmitInit}
              >
                {initBusy ? <LoaderCircle size={12} className="spin" /> : null}
                提交
              </button>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.markdown,text/plain"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) onImportFile(f)
                e.target.value = ''
              }}
            />
          </div>
        )}
      </div>

      <div className="cv-sidebar-list no-scrollbar">
        {filtered.length === 0 ? (
          <div className="cv-lib-empty body-sm">
            {items.length === 0
              ? '还没有简历。上方提交文件或新建空白简历开始。'
              : '没有匹配的简历，试试换个关键词。'}
          </div>
        ) : grouped ? (
          Object.entries(grouped).map(([project, group]) => (
            <div key={project} className="cv-lib-group">
              <div className="cv-lib-group-title body-xs">
                <FolderKanban size={12} />
                {project}
                <span>{group.length}</span>
              </div>
              {group.map(renderItem)}
            </div>
          ))
        ) : (
          filtered.map(renderItem)
        )}
      </div>
    </aside>
  )
}
