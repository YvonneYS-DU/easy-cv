import { useEffect, useMemo, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import {
  Download,
  FileText,
  Menu,
  PanelLeft,
  Sparkles,
  TextQuote,
  Upload,
} from 'lucide-react'
import {
  addMaterial,
  generateFull,
  getMeta,
  getOrCreateSession,
  listDomains,
  listMaterials,
  listResumeVersions,
  listStrategies,
  matchJd,
  rewriteBlock,
  saveResumeVersion,
  updateBlockRewriteStatus,
  updateSuggestionStatus,
  upsertStrategy,
  type MetaInfo,
} from './api/client'
import { AiPanel } from './components/AiPanel'
import {
  LibrarySidebar,
  type ResumeLibraryItem,
} from './components/LibrarySidebar'
import { ResumePaper } from './components/ResumePaper'
import { ToolsPanel } from './components/ToolsPanel'
import { sampleResume } from './data/sampleResume'
import type {
  ApplicationStrategy,
  ChatSession,
  ChatTurn,
  DomainInfo,
  JDMatchResult,
  MaterialRecord,
  ResumeDocument,
  ResumeVersion,
  StructuredBlock,
  SuggestionItem,
} from './types/resume'
import {
  applyPlainTextToBlock,
  applyStructuredToBlock,
  getBlockNode,
  markdownSectionsToDocument,
  normalizeHiddenKeywords,
  parseBlockHtml,
  parseImportedText,
  plainToStructured,
  resumeToMarkdown,
  resumeToPlainText,
  structuredToPlain,
} from './utils/resume'

const LIBRARY_KEY = 'easy-cv-library-v1'

function uid(prefix = 'id') {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`
}

function sessionToUi(session: ChatSession): {
  turns: ChatTurn[]
  suggestions: SuggestionItem[]
} {
  const turns: ChatTurn[] = []
  const suggestions: SuggestionItem[] = []

  for (const msg of session.messages) {
    if (msg.role === 'user') {
      turns.push({
        id: msg.id,
        role: 'user',
        text: msg.content || msg.instruction || '',
      })
      continue
    }
    if (msg.role !== 'ai') continue

    if (msg.suggested_text) {
      const status =
        msg.suggestion_status === 'applied' || msg.suggestion_status === 'ignored'
          ? msg.suggestion_status
          : 'pending'
      const suggestion: SuggestionItem = {
        id: msg.id,
        blockId: msg.block_id || '',
        instruction: msg.instruction || '',
        originalText: msg.original_text || '',
        suggestedText: msg.suggested_text,
        status,
      }
      suggestions.push(suggestion)
      turns.push({
        id: `turn-${msg.id}`,
        role: 'ai',
        text: msg.content || '已生成修改建议',
        suggestionId: suggestion.id,
      })
    } else {
      turns.push({
        id: msg.id,
        role: 'ai',
        text: msg.content || '',
      })
    }
  }

  return { turns, suggestions }
}

function cloneSample(): ResumeDocument {
  return {
    ...sampleResume,
    id: sampleResume.id,
    updatedAt: new Date().toISOString(),
    nodes: sampleResume.nodes.map((n) => ({ ...n })),
  }
}

function blankResume(title = '未命名简历', domain = 'ai_engineer'): ResumeDocument {
  return {
    id: uid('resume'),
    title,
    domain,
    updatedAt: new Date().toISOString(),
    nodes: [
      {
        type: 'block',
        id: 'contact',
        chip: '基本信息',
        kind: 'contact',
        html: `<div class="cv-name">${escapeHtml(title)}</div>
<div class="cv-contact-line">email@example.com · Your City</div>`,
      },
      {
        type: 'section',
        id: 'sec-summary',
        title: 'Professional Summary',
      },
      {
        type: 'block',
        id: 'summary-1',
        chip: 'Summary',
        kind: 'summary',
        html: `<div class="cv-skill-line">在此填写职业摘要…</div>`,
      },
    ],
  }
}

function escapeHtml(input: string): string {
  return input
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function extractKeywords(doc: ResumeDocument): string[] {
  const text = doc.nodes
    .filter((n) => n.type === 'block')
    .map((n) => (n.type === 'block' ? n.chip : ''))
    .join(' ')
  const tokens = text
    .split(/[·|,/\s]+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 2 && t.length <= 24)
  return Array.from(new Set(tokens)).slice(0, 8)
}

function guessProject(doc: ResumeDocument, fallback = ''): string {
  if (fallback) return fallback
  const work = doc.nodes.find((n) => n.type === 'block' && n.kind === 'work')
  if (work && work.type === 'block') {
    const m = work.chip.match(/Work\s*[·•]\s*(.+)/i)
    if (m?.[1]) return m[1].trim()
    const el = document.createElement('div')
    el.innerHTML = work.html
    const title = el.querySelector('.cv-entry-title')?.textContent || ''
    const company = title.split('-').slice(1).join('-').trim()
    if (company) return company.replace(/\(.*/, '').trim()
  }
  return ''
}

function toLibraryItem(
  doc: ResumeDocument,
  extras?: Partial<Pick<ResumeLibraryItem, 'project' | 'keywords' | 'createdAt'>>,
): ResumeLibraryItem {
  const now = new Date().toISOString()
  return {
    id: doc.id,
    title: doc.title || '未命名简历',
    domain: doc.domain,
    project: extras?.project ?? guessProject(doc),
    keywords: extras?.keywords ?? extractKeywords(doc),
    updatedAt: doc.updatedAt || now,
    createdAt: extras?.createdAt || now,
    document: doc,
  }
}

function loadLibrary(): { items: ResumeLibraryItem[]; activeId: string } {
  try {
    const raw = localStorage.getItem(LIBRARY_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as {
        items?: ResumeLibraryItem[]
        activeId?: string
      }
      if (parsed.items?.length) {
        const activeId =
          parsed.activeId && parsed.items.some((i) => i.id === parsed.activeId)
            ? parsed.activeId
            : parsed.items[0].id
        return { items: parsed.items, activeId }
      }
    }
  } catch {
    // ignore corrupt storage
  }
  const demo = toLibraryItem(cloneSample(), {
    project: 'RightShip',
    keywords: ['AI', 'RAG', 'LangChain', 'RightShip'],
    createdAt: sampleResume.updatedAt,
  })
  return { items: [demo], activeId: demo.id }
}

export default function App() {
  const initial = useMemo(() => loadLibrary(), [])
  const [library, setLibrary] = useState<ResumeLibraryItem[]>(initial.items)
  const [activeId, setActiveId] = useState<string>(initial.activeId)
  const [selectedId, setSelectedId] = useState<string | null>('edu-nus')
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([])
  const [panelOpen, setPanelOpen] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [tab, setTab] = useState<'edit' | 'tools'>('edit')
  const [toast, setToast] = useState<string | null>(null)
  const [meta, setMeta] = useState<MetaInfo | null>(null)
  const [domains, setDomains] = useState<DomainInfo[]>([
    { key: 'ai_engineer', label: 'AI/ML 工程师', core_keywords: [] },
  ])
  const [domain, setDomain] = useState('ai_engineer')
  const [materialText, setMaterialText] = useState('')
  const [materials, setMaterials] = useState<MaterialRecord[]>([])
  const [materialsLoading, setMaterialsLoading] = useState(false)
  const [toolsBusy, setToolsBusy] = useState(false)
  const [initBusy, setInitBusy] = useState(false)
  const [jdText, setJdText] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [strategy, setStrategy] = useState<ApplicationStrategy | null>(null)
  const [versions, setVersions] = useState<ResumeVersion[]>([])
  const [matchLoading, setMatchLoading] = useState(false)
  const [matchResult, setMatchResult] = useState<JDMatchResult | null>(null)
  const [jdRewriteMarkdown, setJdRewriteMarkdown] = useState<string | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [exportHiddenDraft, setExportHiddenDraft] = useState('')
  const [exportIncludeHidden, setExportIncludeHidden] = useState(true)
  const [draft, setDraft] = useState<StructuredBlock | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const skipPersist = useRef(true)
  const draftSourceRef = useRef<string | null>(null)

  const activeItem = library.find((i) => i.id === activeId) || library[0]
  const doc = activeItem?.document || cloneSample()

  const selectedNode = useMemo(
    () => (selectedId ? getBlockNode(doc.nodes, selectedId) : null),
    [doc, selectedId],
  )
  const selectedChip = selectedNode?.chip || null

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch(() => setMeta({ status: 'offline', service: 'easy-cv', mode: 'mock' }))
    listDomains()
      .then((res) => {
        if (res.domains?.length) {
          setDomains(res.domains)
          setDomain((prev) => prev || res.domains[0].key)
        }
      })
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    void refreshMaterials()
  }, [domain])

  useEffect(() => {
    if (!activeId) return
    let cancelled = false
    setTurns([])
    setSuggestions([])
    setSessionId('')
    setMatchResult(null)
    setJdRewriteMarkdown(null)

    getOrCreateSession({
      resume_id: activeId,
      domain: activeItem?.domain || domain,
      title: activeItem?.title || 'AI 会话',
    })
      .then((res) => {
        if (cancelled) return
        setSessionId(res.session.id)
        const ui = sessionToUi(res.session)
        setTurns(ui.turns)
        setSuggestions(ui.suggestions)
      })
      .catch(() => {
        if (!cancelled) {
          setSessionId('')
          setTurns([])
          setSuggestions([])
        }
      })

    void refreshVersions(activeId)
    void refreshStrategy(activeItem?.domain || domain, activeId)

    return () => {
      cancelled = true
    }
  }, [activeId])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 2600)
    return () => window.clearTimeout(t)
  }, [toast])

  useEffect(() => {
    if (skipPersist.current) {
      skipPersist.current = false
      return
    }
    localStorage.setItem(
      LIBRARY_KEY,
      JSON.stringify({ items: library, activeId }),
    )
  }, [library, activeId])

  useEffect(() => {
    if (activeItem) {
      setDomain(activeItem.domain || 'ai_engineer')
    }
  }, [activeItem?.id])

  useEffect(() => {
    if (!selectedId || !selectedNode) {
      setDraft(null)
      draftSourceRef.current = null
      return
    }
    const blockKey = `${activeId}:${selectedId}`
    const sourceKey = `${blockKey}:${selectedNode.html}`
    if (draftSourceRef.current === sourceKey) return
    if (draftSourceRef.current?.startsWith(`${blockKey}:`)) {
      draftSourceRef.current = sourceKey
      return
    }
    setDraft(parseBlockHtml(selectedNode.kind, selectedNode.html))
    draftSourceRef.current = sourceKey
  }, [activeId, selectedId, selectedNode])

  function showToast(msg: string) {
    setToast(msg)
  }

  function updateActiveDoc(
    updater: (prev: ResumeDocument) => ResumeDocument,
    extras?: Partial<Pick<ResumeLibraryItem, 'title' | 'project' | 'keywords' | 'domain'>>,
  ) {
    setLibrary((prev) =>
      prev.map((item) => {
        if (item.id !== activeId) return item
        const nextDoc = updater(item.document)
        return {
          ...item,
          title: extras?.title ?? nextDoc.title ?? item.title,
          domain: extras?.domain ?? nextDoc.domain ?? item.domain,
          project: extras?.project ?? item.project,
          keywords: extras?.keywords ?? extractKeywords(nextDoc),
          updatedAt: nextDoc.updatedAt,
          document: nextDoc,
        }
      }),
    )
  }

  function setDoc(next: ResumeDocument | ((prev: ResumeDocument) => ResumeDocument)) {
    updateActiveDoc((prev) => (typeof next === 'function' ? next(prev) : next))
  }

  function activateResume(id: string, nextDoc?: ResumeDocument) {
    setActiveId(id)
    setTurns([])
    setSuggestions([])
    setMatchResult(null)
    setJdRewriteMarkdown(null)
    draftSourceRef.current = null
    const target = nextDoc || library.find((i) => i.id === id)?.document
    const firstBlock = target?.nodes.find((n) => n.type === 'block')
    setSelectedId(firstBlock?.id || null)
    setDraft(null)
    setSidebarOpen(false)
  }

  function addToLibrary(item: ResumeLibraryItem, select = true) {
    setLibrary((prev) => [item, ...prev.filter((i) => i.id !== item.id)])
    if (select) activateResume(item.id, item.document)
  }

  async function refreshMaterials() {
    setMaterialsLoading(true)
    try {
      const list = await listMaterials(domain, true)
      setMaterials(list)
    } catch {
      setMaterials([])
    } finally {
      setMaterialsLoading(false)
    }
  }

  async function refreshVersions(resumeId = activeId) {
    if (!resumeId) {
      setVersions([])
      return
    }
    try {
      const res = await listResumeVersions(resumeId, 20)
      setVersions(res.versions || [])
    } catch {
      setVersions([])
    }
  }

  async function refreshStrategy(nextDomain = domain, resumeId = activeId) {
    try {
      const res = await listStrategies(nextDomain, resumeId)
      if (res.strategies?.length) {
        setStrategy(res.strategies[0])
        return
      }
      const created = await upsertStrategy({
        domain: nextDomain,
        target_role: targetRole,
        resume_id: resumeId,
        name: targetRole
          ? `${nextDomain || '通用'} · ${targetRole}`
          : `${nextDomain || '默认'} 投递策略`,
        why: '同一套真实经历按不同方向重新取景：事实不变，强调点与措辞可变，提高入选率。',
      })
      setStrategy(created.strategy)
    } catch {
      setStrategy(null)
    }
  }

  function handleSelect(blockId: string) {
    if (blockId !== selectedId) {
      draftSourceRef.current = null
    }
    setSelectedId(blockId)
    setPanelOpen(true)
    setTab('edit')
  }

  function clearSelection() {
    draftSourceRef.current = null
    setSelectedId(null)
    setDraft(null)
  }

  function handleDraftChange(next: StructuredBlock) {
    if (!selectedId || !selectedNode) return
    setDraft(next)
    draftSourceRef.current = `${activeId}:${selectedId}:pending`
    setDoc((prev) => applyStructuredToBlock(prev, selectedId, next))
  }

  async function handleSend(prompt?: string) {
    const text = (prompt ?? instruction).trim()
    if (!selectedId || !selectedNode || !text) return
    const current = draft || parseBlockHtml(selectedNode.kind, selectedNode.html)
    const original = structuredToPlain(current)
    if (!original.trim()) return

    setLoading(true)
    const userTurn: ChatTurn = { id: uid('u'), role: 'user', text }
    setTurns((prev) => [...prev, userTurn])
    setInstruction('')

    try {
      // Ensure a directional phrasing/strategy branch exists
      let strategyId = strategy?.id || ''
      if (targetRole || !strategyId) {
        try {
          const s = await upsertStrategy({
            id: strategyId,
            domain,
            target_role: targetRole,
            resume_id: activeId,
            name: targetRole
              ? `${domain || '通用'} · ${targetRole}`
              : strategy?.name || `${domain || '默认'} 写法分支`,
            why:
              strategy?.why ||
              '同一源经历按投递方向改写法：事实不变，角度可变。',
          })
          setStrategy(s.strategy)
          strategyId = s.strategy.id
        } catch {
          // ignore strategy bootstrap failure
        }
      }

      const res = await rewriteBlock({
        selected_text: original,
        instruction: text,
        chip: selectedChip || '',
        domain,
        block_id: selectedId,
        session_id: sessionId || undefined,
        resume_id: activeId,
        use_history: true,
        strategy_id: strategyId || undefined,
        target_role: targetRole,
        resume_markdown: resumeToMarkdown(doc, { includeHidden: false }),
        mine_materials: true,
        material_ids: materials.map((m) => m.id),
      })
      if (res.session_id) setSessionId(res.session_id)
      if (res.strategy) setStrategy(res.strategy)

      const note = res.ai_note || '已生成修改建议'
      const suggestion: SuggestionItem = {
        id: res.ai_message_id || res.rewrite_id || uid('s'),
        blockId: selectedId,
        instruction: text,
        originalText: original,
        suggestedText: res.suggested_text,
        status: 'pending',
      }
      if (res.session) {
        const ui = sessionToUi(res.session)
        setTurns(ui.turns)
        setSuggestions(ui.suggestions)
      } else {
        setSuggestions((prev) => [...prev, suggestion])
        setTurns((prev) => [
          ...prev,
          { id: uid('a'), role: 'ai', text: note, suggestionId: suggestion.id },
        ])
      }
      const n = res.forgotten_experiences?.length || 0
      if (n > 0) showToast(`建议已生成，并入 ${n} 条可补素材`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'AI 请求失败'
      setTurns((prev) => [...prev, { id: uid('a'), role: 'ai', text: msg }])
      showToast(msg)
    } finally {
      setLoading(false)
    }
  }

  function handleApply(id: string) {
    const item = suggestions.find((s) => s.id === id)
    if (!item || item.status !== 'pending') return
    const node = getBlockNode(doc.nodes, item.blockId)
    if (node && item.blockId === selectedId) {
      const structured = plainToStructured(node.kind, item.suggestedText)
      setDraft(structured)
      draftSourceRef.current = `${activeId}:${selectedId}:pending`
    } else {
      draftSourceRef.current = null
    }
    const nextDoc = applyPlainTextToBlock(doc, item.blockId, item.suggestedText)
    setDoc(nextDoc)
    setSuggestions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: 'applied' } : s)),
    )
    if (sessionId) {
      void updateSuggestionStatus(sessionId, id, 'applied')
        .then(() => refreshStrategy())
        .catch(() => undefined)
    }
    void updateBlockRewriteStatus(id, 'applied', sessionId).catch(() => undefined)
    void saveResumeVersion({
      resume_id: activeId,
      raw_markdown: resumeToMarkdown(nextDoc, { includeHidden: false }),
      domain,
      title: `应用改写 · ${item.instruction.slice(0, 24) || item.blockId}`,
      source: 'block_apply',
      note: item.instruction,
      target_role: targetRole,
      strategy_id: strategy?.id,
    })
      .then(() => refreshVersions())
      .catch(() => undefined)
    showToast('已应用 AI 修改并记入策略/版本')
  }

  function handleIgnore(id: string) {
    setSuggestions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: 'ignored' } : s)),
    )
  }

  function ingestImportedDoc(next: ResumeDocument, project = '', fileName = '') {
    const title = next.title || fileName.replace(/\.(md|txt|markdown)$/i, '') || '导入简历'
    const item = toLibraryItem(
      { ...next, id: next.id || uid('resume'), title, domain: next.domain || domain },
      { project: project || guessProject(next) },
    )
    addToLibrary(item)
    showToast(fileName ? `已导入：${fileName}` : '已创建简历')
  }

  function handleImportFile(file: File, project = '') {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || '')
      try {
        const next = parseImportedText(text)
        ingestImportedDoc(next, project, file.name)
      } catch {
        showToast('导入失败，请使用 .txt / .md 文本')
      }
    }
    reader.readAsText(file)
  }

  function handleCreateBlank() {
    const docBlank = blankResume('未命名简历', domain)
    const item = toLibraryItem(docBlank, { project: '' })
    addToLibrary(item)
    showToast('已创建空白简历')
  }

  async function handleSubmitInit(payload: {
    text: string
    project: string
    title: string
  }) {
    setInitBusy(true)
    try {
      let nextDoc: ResumeDocument
      if (payload.text) {
        try {
          nextDoc = parseImportedText(payload.text)
        } catch {
          nextDoc = blankResume(payload.title, domain)
        }
        nextDoc = {
          ...nextDoc,
          id: uid('resume'),
          title: payload.title || nextDoc.title || '未命名简历',
          domain,
          updatedAt: new Date().toISOString(),
        }
        try {
          await addMaterial(
            [
              payload.project ? `项目: ${payload.project}` : '',
              payload.title ? `标题: ${payload.title}` : '',
              payload.text,
            ]
              .filter(Boolean)
              .join('\n'),
            domain,
          )
          await refreshMaterials()
        } catch {
          // Memory write failure must not block local init
        }
      } else {
        nextDoc = blankResume(payload.title, domain)
      }

      const item = toLibraryItem(nextDoc, {
        project: payload.project,
        keywords: [
          ...extractKeywords(nextDoc),
          ...(payload.project ? [payload.project] : []),
        ].slice(0, 8),
      })
      addToLibrary(item)
      showToast(payload.text ? '已初始化并写入记忆' : '已创建简历')
    } finally {
      setInitBusy(false)
    }
  }

  function openExportModal() {
    setExportHiddenDraft((doc.hiddenKeywords || []).join('\n'))
    setExportIncludeHidden(doc.includeHiddenKeywords !== false)
    setExportOpen(true)
  }

  function persistExportSettings(nextKeywords?: string[], nextInclude?: boolean) {
    const keywords = nextKeywords ?? normalizeHiddenKeywords(exportHiddenDraft)
    const include = nextInclude ?? exportIncludeHidden
    setExportHiddenDraft(keywords.join('\n'))
    setExportIncludeHidden(include)
    setDoc((prev) => ({
      ...prev,
      hiddenKeywords: keywords,
      includeHiddenKeywords: include,
      updatedAt: new Date().toISOString(),
    }))
    return { keywords, include }
  }

  function withExportDoc() {
    const { keywords, include } = persistExportSettings()
    return {
      ...doc,
      hiddenKeywords: keywords,
      includeHiddenKeywords: include,
    }
  }

  function exportMarkdown() {
    const exportDoc = withExportDoc()
    const md = resumeToMarkdown(exportDoc, { includeHidden: exportDoc.includeHiddenKeywords !== false })
    downloadText(`${exportDoc.title || 'resume'}.md`, md, 'text/markdown;charset=utf-8')
    setExportOpen(false)
    showToast(
      exportDoc.includeHiddenKeywords !== false && (exportDoc.hiddenKeywords?.length || 0) > 0
        ? '已导出 Markdown（含隐藏关键词）'
        : '已导出 Markdown',
    )
  }

  function exportText() {
    const exportDoc = withExportDoc()
    const text = resumeToPlainText(exportDoc, { includeHidden: exportDoc.includeHiddenKeywords !== false })
    downloadText(`${exportDoc.title || 'resume'}.txt`, text, 'text/plain;charset=utf-8')
    setExportOpen(false)
    showToast(
      exportDoc.includeHiddenKeywords !== false && (exportDoc.hiddenKeywords?.length || 0) > 0
        ? '已导出文本（含隐藏关键词）'
        : '已导出文本',
    )
  }

  function exportPrint() {
    flushSync(() => {
      persistExportSettings()
      setExportOpen(false)
    })
    window.requestAnimationFrame(() => {
      window.print()
    })
  }

  function fillHiddenFromMatch() {
    const fromMatch = [
      ...(matchResult?.missing_keywords || []),
      ...(matchResult?.matched_keywords || []),
    ]
    if (!fromMatch.length) {
      showToast('请先在「素材 / JD」里完成 JD 匹配')
      return
    }
    const merged = normalizeHiddenKeywords([
      ...normalizeHiddenKeywords(exportHiddenDraft),
      ...fromMatch,
    ])
    setExportHiddenDraft(merged.join('\n'))
    showToast(`已填入 ${merged.length} 个关键词`)
  }

  async function handleAddMaterial() {
    if (!materialText.trim()) return
    setToolsBusy(true)
    try {
      const res = await addMaterial(materialText.trim(), domain)
      setMaterialText('')
      await refreshMaterials()
      showToast(`素材已提取：${res.material.content.summary.slice(0, 24)}`)
    } catch (err) {
      showToast(err instanceof Error ? err.message : '素材提取失败')
    } finally {
      setToolsBusy(false)
    }
  }

  async function handleGenerateFromMaterials() {
    setToolsBusy(true)
    try {
      const ids = materials.map((m) => m.id)
      const res = await generateFull(domain, ids, '', {
        resume_id: activeId,
        title: doc.title || 'Generated Resume',
        strategy_id: strategy?.id,
        target_role: targetRole,
        save_version: true,
      })
      const next = markdownSectionsToDocument(
        doc.title || 'Generated Resume',
        domain,
        res.resume.sections,
      )
      setDoc({
        ...next,
        hiddenKeywords: doc.hiddenKeywords,
        includeHiddenKeywords: doc.includeHiddenKeywords,
      })
      setSelectedId(next.nodes.find((n) => n.type === 'block')?.id || null)
      setTab('edit')
      await refreshVersions()
      showToast('已根据素材生成简历（已存版本）')
    } catch (err) {
      showToast(err instanceof Error ? err.message : '生成失败')
    } finally {
      setToolsBusy(false)
    }
  }

  async function handleMatchJd() {
    if (!jdText.trim()) return
    setMatchLoading(true)
    try {
      let strategyId = strategy?.id || ''
      if (targetRole || !strategyId) {
        const s = await upsertStrategy({
          id: strategyId,
          domain,
          target_role: targetRole,
          resume_id: activeId,
          name: targetRole
            ? `${domain || '通用'} · ${targetRole}`
            : strategy?.name || `${domain || '默认'} 投递策略`,
          why:
            strategy?.why ||
            '同一套真实经历按不同方向重新取景：事实不变，强调点与措辞可变，提高入选率。',
        })
        setStrategy(s.strategy)
        strategyId = s.strategy.id
      }

      const res = await matchJd({
        resume_markdown: resumeToMarkdown(doc, { includeHidden: false }),
        jd_text: jdText.trim(),
        domain,
        resume_id: activeId,
        strategy_id: strategyId,
        target_role: targetRole,
        material_ids: materials.map((m) => m.id),
        mine_forgotten: true,
        save_version: true,
        title: targetRole ? `JD · ${targetRole}` : 'JD 改写稿',
      })
      setMatchResult(res.match_result)
      setJdRewriteMarkdown(res.suggested_resume?.raw_markdown || null)
      if (res.strategy) setStrategy(res.strategy)
      await refreshVersions()
      const forgottenCount = res.match_result.forgotten_experiences?.length || 0
      showToast(
        `匹配 ${Math.round(res.match_result.match_score * 100)}%` +
          (forgottenCount ? ` · 挖出 ${forgottenCount} 条忽略经历` : ''),
      )
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'JD 匹配失败')
    } finally {
      setMatchLoading(false)
    }
  }

  function handleApplyJdRewrite() {
    if (!jdRewriteMarkdown) return
    const sections = jdRewriteMarkdown
      .split(/\n(?=# )/)
      .map((chunk) => chunk.trim())
      .filter(Boolean)
      .map((chunk) => {
        const lines = chunk.split('\n')
        const name = lines[0].replace(/^#\s*/, '').trim().toLowerCase()
        return { name, content: lines.slice(1).join('\n').trim() }
      })
    const next = markdownSectionsToDocument(doc.title, domain, sections)
    setDoc({
      ...next,
      hiddenKeywords: doc.hiddenKeywords,
      includeHiddenKeywords: doc.includeHiddenKeywords,
    })
    showToast('已应用 JD 改写稿')
  }

  async function handleSaveVersion() {
    try {
      await saveResumeVersion({
        resume_id: activeId,
        raw_markdown: resumeToMarkdown(doc, { includeHidden: false }),
        document_json: doc as unknown as Record<string, unknown>,
        domain,
        title: targetRole ? `${doc.title} · ${targetRole}` : doc.title || '手动快照',
        source: 'manual',
        note: targetRole ? `投递方向: ${targetRole}` : '手动保存',
        target_role: targetRole,
        strategy_id: strategy?.id,
      })
      await refreshVersions()
      showToast('已保存简历版本')
    } catch (err) {
      showToast(err instanceof Error ? err.message : '保存版本失败')
    }
  }

  async function handleRestoreVersion(versionId: string) {
    const version = versions.find((v) => v.id === versionId)
    if (!version) return
    try {
      if (version.document_json && Object.keys(version.document_json).length > 0) {
        const restored = version.document_json as unknown as ResumeDocument
        setDoc({
          ...restored,
          id: activeId,
          updatedAt: new Date().toISOString(),
        })
      } else if (version.raw_markdown) {
        const sections = version.raw_markdown
          .split(/\n(?=# )/)
          .map((chunk) => chunk.trim())
          .filter(Boolean)
          .map((chunk) => {
            const lines = chunk.split('\n')
            const name = lines[0].replace(/^#\s*/, '').trim().toLowerCase()
            return { name, content: lines.slice(1).join('\n').trim() }
          })
        const next = markdownSectionsToDocument(
          version.title || doc.title,
          version.domain || domain,
          sections,
        )
        setDoc({
          ...next,
          id: activeId,
          hiddenKeywords: doc.hiddenKeywords,
          includeHiddenKeywords: doc.includeHiddenKeywords,
        })
      } else {
        showToast('该版本没有可恢复内容')
        return
      }
      showToast(`已恢复 v${version.version_no}`)
    } catch (err) {
      showToast(err instanceof Error ? err.message : '恢复失败')
    }
  }

  return (
    <div className="cv-shell">
      <header className="cv-topbar">
        <div className="cv-topbar-left">
          <button
            className="cv-btn-outline body-md cv-mobile-lib-toggle"
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            <PanelLeft size={14} />
            简历库
          </button>
          <FileText size={16} />
          <span className="heading-xs">Easy CV</span>
          <span className="cv-chip-outline body-xs hide-sm">可运行版</span>
          {activeItem ? (
            <span className="cv-chip-outline body-xs hide-sm" title={activeItem.title}>
              {activeItem.title}
            </span>
          ) : null}
        </div>
        <div className="cv-topbar-right">
          <button className="cv-btn-outline body-md" type="button" onClick={() => fileRef.current?.click()}>
            <Upload size={14} />
            <span className="hide-sm">导入文本</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.markdown,text/plain"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleImportFile(f)
              e.target.value = ''
            }}
          />
          <button className="cv-btn-outline body-md" type="button" onClick={openExportModal}>
            <Download size={14} />
            <span className="hide-sm">导出</span>
          </button>
          <button
            className="cv-btn-outline body-md cv-mobile-ai-toggle"
            type="button"
            onClick={() => setPanelOpen((v) => !v)}
          >
            <Menu size={14} />
            AI
          </button>
          <span className="cv-ai-badge">
            <span className={`cv-ai-dot${meta?.mode === 'mock' ? ' mock' : ''}`} />
            <span className="body-xs">{meta?.mode === 'llm' ? 'AI' : 'Mock'}</span>
          </span>
        </div>
      </header>

      <div className="cv-body">
        <LibrarySidebar
          items={library}
          activeId={activeId}
          open={sidebarOpen}
          onSelect={(id) => activateResume(id)}
          onCreateBlank={handleCreateBlank}
          onImportFile={(file) => handleImportFile(file)}
          onSubmitInit={(payload) => void handleSubmitInit(payload)}
          initBusy={initBusy}
        />

        <section className="cv-left">
          <div className="cv-left-hint">
            <span className="body-xs">
              <TextQuote size={12} />
              点击任意区块进行编辑
            </span>
          </div>
          <ResumePaper doc={doc} selectedId={selectedId} onSelect={handleSelect} />
        </section>

        <AiPanel
          open={panelOpen}
          selectedChip={selectedChip}
          draft={draft}
          onDraftChange={handleDraftChange}
          instruction={instruction}
          loading={loading}
          turns={turns}
          suggestions={suggestions}
          onInstructionChange={setInstruction}
          onSend={() => handleSend()}
          onQuick={(text) => {
            setInstruction(text)
            void handleSend(text)
          }}
          onApply={handleApply}
          onIgnore={handleIgnore}
          onClose={() => {
            if (window.matchMedia('(max-width: 960px)').matches) {
              setPanelOpen(false)
            } else {
              clearSelection()
            }
          }}
          tab={tab}
          onTabChange={setTab}
          toolsSlot={
            <ToolsPanel
              domain={domain}
              domains={domains}
              onDomainChange={(d) => {
                setDomain(d)
                setDoc((prev) => ({ ...prev, domain: d, updatedAt: new Date().toISOString() }))
                void refreshStrategy(d, activeId)
              }}
              materialText={materialText}
              onMaterialTextChange={setMaterialText}
              materials={materials}
              materialsLoading={materialsLoading}
              onAddMaterial={() => void handleAddMaterial()}
              onRefreshMaterials={() => void refreshMaterials()}
              onGenerateFromMaterials={() => void handleGenerateFromMaterials()}
              jdText={jdText}
              onJdTextChange={setJdText}
              targetRole={targetRole}
              onTargetRoleChange={setTargetRole}
              matchLoading={matchLoading}
              matchResult={matchResult}
              strategy={strategy}
              versions={versions}
              onMatchJd={() => void handleMatchJd()}
              onApplyJdRewrite={handleApplyJdRewrite}
              onSaveVersion={() => void handleSaveVersion()}
              onRestoreVersion={(id) => void handleRestoreVersion(id)}
              canApplyJd={Boolean(jdRewriteMarkdown)}
              busy={toolsBusy}
            />
          }
        />
      </div>

      {exportOpen ? (
        <div
          className="cv-modal-backdrop"
          onClick={() => {
            persistExportSettings()
            setExportOpen(false)
          }}
        >
          <div className="cv-modal" onClick={(e) => e.stopPropagation()}>
            <div className="heading-sm">导出简历</div>
            <div className="body-md" style={{ color: 'var(--text-secondary)' }}>
              支持 Markdown / 纯文本下载，或直接打印为 PDF。可先配置 ATS 隐藏关键词。
            </div>

            <div className="cv-export-section">
              <div className="cv-export-section-head">
                <div>
                  <div className="cv-export-title body-md">隐藏关键词（ATS）</div>
                  <div className="cv-export-desc body-xs">
                    人眼几乎看不见，但解析器仍可读到。适合补充 JD 关键词、项目术语、积极表述。
                  </div>
                </div>
                <label className="cv-switch body-xs">
                  <input
                    type="checkbox"
                    checked={exportIncludeHidden}
                    onChange={(e) => setExportIncludeHidden(e.target.checked)}
                  />
                  导出时注入
                </label>
              </div>
              <textarea
                className="cv-textarea"
                rows={4}
                disabled={!exportIncludeHidden}
                placeholder={
                  '每行一个，或用逗号分隔\n例如：\nRAG\nLangChain\nmaritime compliance\nmulti-agent\nquantified impact'
                }
                value={exportHiddenDraft}
                onChange={(e) => setExportHiddenDraft(e.target.value)}
              />
              <div className="cv-export-meta body-xs">
                <span>
                  {normalizeHiddenKeywords(exportHiddenDraft).length} 个词
                  {exportIncludeHidden ? ' · 将注入导出/打印' : ' · 已关闭注入'}
                </span>
                <button
                  type="button"
                  className="cv-text-btn body-xs"
                  onClick={fillHiddenFromMatch}
                >
                  从 JD 匹配填入
                </button>
              </div>
              <div className="cv-export-hint body-xs">
                打印/PDF：页面底部极淡隐藏层；Markdown/文本：文末追加关键词。请仅用于真实相关技能，避免堆砌无关词。
              </div>
            </div>

            <div className="cv-modal-actions">
              <button
                className="cv-btn-outline body-md"
                type="button"
                onClick={() => {
                  persistExportSettings()
                  setExportOpen(false)
                }}
              >
                仅保存设置
              </button>
              <button className="cv-btn-outline body-md" type="button" onClick={exportMarkdown}>
                Markdown
              </button>
              <button className="cv-btn-outline body-md" type="button" onClick={exportText}>
                文本
              </button>
              <button className="cv-btn-primary body-md" type="button" onClick={exportPrint}>
                <Sparkles size={14} />
                打印 / PDF
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? <div className="cv-toast">{toast}</div> : null}
    </div>
  )
}

function downloadText(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
