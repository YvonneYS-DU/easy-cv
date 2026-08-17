import type {
  BlockKind,
  ResumeDocument,
  ResumeNode,
  WatermarkAnchor,
  WatermarkItem,
  WatermarkKind,
  WatermarkPrefs,
} from '../types/resume'

function normalizeKeywords(input: string | string[] | undefined | null): string[] {
  const raw = Array.isArray(input)
    ? input.join('\n')
    : typeof input === 'string'
      ? input
      : ''
  const parts = raw
    .split(/[\n,，;；|]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const seen = new Set<string>()
  const out: string[] = []
  for (const p of parts) {
    const key = p.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(p)
  }
  return out.slice(0, 80)
}

export const WATERMARK_KINDS: WatermarkKind[] = ['skill', 'role', 'soft', 'domain']

export const WATERMARK_KIND_META: Record<
  WatermarkKind,
  { label: string; hint: string; defaultAnchor: WatermarkAnchor; placeholder: string }
> = {
  skill: {
    label: '技能词',
    hint: '技术栈、工具、框架',
    defaultAnchor: 'after_skills',
    placeholder: 'RAG\nLangChain\nPython\nKubernetes',
  },
  role: {
    label: '岗位词',
    hint: '职位名、方向、职级',
    defaultAnchor: 'after_summary',
    placeholder: 'AI Engineer\nBackend Engineer\nStaff Engineer',
  },
  soft: {
    label: '软技能',
    hint: '协作、领导、表达',
    defaultAnchor: 'end',
    placeholder: 'stakeholder communication\ncross-functional\nmentoring',
  },
  domain: {
    label: '领域词',
    hint: '行业、业务场景',
    defaultAnchor: 'after_work',
    placeholder: 'maritime compliance\nfintech\nrisk management',
  },
}

export const WATERMARK_ANCHORS: Array<{ value: WatermarkAnchor; label: string }> = [
  { value: 'after_contact', label: '基本信息后' },
  { value: 'after_summary', label: '摘要后' },
  { value: 'after_education', label: '教育后' },
  { value: 'after_skills', label: '技能后' },
  { value: 'after_work', label: '工作经历后' },
  { value: 'after_project', label: '项目后' },
  { value: 'end', label: '简历末尾' },
]

const ANCHOR_KIND: Record<Exclude<WatermarkAnchor, 'end'>, BlockKind> = {
  after_contact: 'contact',
  after_summary: 'summary',
  after_education: 'education',
  after_skills: 'skill',
  after_work: 'work',
  after_project: 'project',
}

const SECTION_HINTS: Record<Exclude<WatermarkAnchor, 'end'>, string[]> = {
  after_contact: ['contact', '基本信息'],
  after_summary: ['summary', 'professional summary', '摘要', '个人总结'],
  after_education: ['education', '教育', '教育背景'],
  after_skills: ['skill', 'skills', '专业技能', '技能'],
  after_work: ['work', 'experience', '工作', '工作经历'],
  after_project: ['project', 'projects', '项目', '项目经历'],
}

const PREFS_KEY = 'easy-cv-watermark-prefs-v1'

const DEFAULT_ENABLED: WatermarkKind[] = ['skill', 'role']

export interface WatermarkInsertion {
  afterId: string | 'end'
  item: WatermarkItem
  keywords: string[]
}

function isWatermarkKind(value: unknown): value is WatermarkKind {
  return WATERMARK_KINDS.includes(value as WatermarkKind)
}

function isWatermarkAnchor(value: unknown): value is WatermarkAnchor {
  return WATERMARK_ANCHORS.some((item) => item.value === value)
}

export function loadWatermarkPrefs(): WatermarkPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<WatermarkPrefs>
      const enabledKinds = (parsed.enabledKinds || []).filter(isWatermarkKind)
      const anchors: Partial<Record<WatermarkKind, WatermarkAnchor>> = {}
      for (const kind of WATERMARK_KINDS) {
        const value = parsed.anchors?.[kind]
        if (isWatermarkAnchor(value)) anchors[kind] = value
      }
      return {
        enabledKinds: enabledKinds.length ? enabledKinds : DEFAULT_ENABLED,
        anchors,
      }
    }
  } catch {
    // ignore corrupt prefs
  }
  return { enabledKinds: [...DEFAULT_ENABLED], anchors: {} }
}

export function saveWatermarkPrefs(prefs: WatermarkPrefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    // ignore quota / private mode
  }
}

export function prefsFromWatermarks(watermarks: WatermarkItem[]): WatermarkPrefs {
  const anchors: Partial<Record<WatermarkKind, WatermarkAnchor>> = {}
  for (const item of watermarks) {
    anchors[item.kind] = item.anchor
  }
  return {
    enabledKinds: watermarks.filter((item) => item.enabled).map((item) => item.kind),
    anchors,
  }
}

export function defaultWatermarks(prefs?: WatermarkPrefs): WatermarkItem[] {
  const next = prefs || loadWatermarkPrefs()
  return WATERMARK_KINDS.map((kind) => ({
    id: `wm-${kind}`,
    kind,
    enabled: next.enabledKinds.includes(kind),
    anchor: next.anchors[kind] || WATERMARK_KIND_META[kind].defaultAnchor,
    content: '',
  }))
}

export function ensureWatermarks(doc: ResumeDocument, prefs?: WatermarkPrefs): WatermarkItem[] {
  const nextPrefs = prefs || doc.watermarkPrefs || loadWatermarkPrefs()
  const base = defaultWatermarks(nextPrefs)
  const existing = Array.isArray(doc.watermarks) ? doc.watermarks : []
  const byKind = new Map<WatermarkKind, WatermarkItem>()

  for (const item of existing) {
    if (!isWatermarkKind(item.kind)) continue
    byKind.set(item.kind, {
      id: item.id || `wm-${item.kind}`,
      kind: item.kind,
      enabled: item.enabled !== false,
      anchor: isWatermarkAnchor(item.anchor)
        ? item.anchor
        : nextPrefs.anchors[item.kind] || WATERMARK_KIND_META[item.kind].defaultAnchor,
      content: item.content || '',
    })
  }

  const merged = base.map((item) => byKind.get(item.kind) || item)
  const legacy = normalizeKeywords(doc.hiddenKeywords)
  const hasAnyContent = merged.some((item) => normalizeKeywords(item.content).length > 0)
  if (legacy.length && !hasAnyContent) {
    return merged.map((item) =>
      item.kind === 'skill'
        ? { ...item, enabled: true, content: legacy.join('\n') }
        : item,
    )
  }
  return merged
}

export function flattenWatermarkKeywords(watermarks: WatermarkItem[]): string[] {
  return normalizeKeywords(watermarks.filter((item) => item.enabled).map((item) => item.content))
}

export function hydrateResumeWatermarks(doc: ResumeDocument, prefs?: WatermarkPrefs): ResumeDocument {
  const watermarks = ensureWatermarks(doc, prefs)
  return {
    ...doc,
    watermarks,
    hiddenKeywords: flattenWatermarkKeywords(watermarks),
    watermarkPrefs: prefsFromWatermarks(watermarks),
  }
}

export function copyWatermarkState(from: ResumeDocument, to: ResumeDocument): ResumeDocument {
  return {
    ...to,
    hiddenKeywords: from.hiddenKeywords,
    includeHiddenKeywords: from.includeHiddenKeywords,
    watermarks: from.watermarks,
    watermarkPrefs: from.watermarkPrefs,
  }
}

export function resolveAnchorNodeId(nodes: ResumeNode[], anchor: WatermarkAnchor): string | 'end' {
  if (anchor === 'end') return 'end'
  const kind = ANCHOR_KIND[anchor]
  let lastBlockId: string | null = null
  for (const node of nodes) {
    if (node.type === 'block' && node.kind === kind) lastBlockId = node.id
  }
  if (lastBlockId) return lastBlockId

  const hints = SECTION_HINTS[anchor]
  let lastSectionId: string | null = null
  for (const node of nodes) {
    if (node.type !== 'section') continue
    const title = node.title.trim().toLowerCase()
    if (hints.some((hint) => title.includes(hint))) lastSectionId = node.id
  }
  return lastSectionId || 'end'
}

export function getWatermarkInsertions(doc: ResumeDocument): WatermarkInsertion[] {
  if (doc.includeHiddenKeywords === false) return []
  return ensureWatermarks(doc)
    .filter((item) => item.enabled)
    .map((item) => {
      const keywords = normalizeKeywords(item.content)
      if (!keywords.length) return null
      return {
        afterId: resolveAnchorNodeId(doc.nodes, item.anchor),
        item,
        keywords,
      }
    })
    .filter((item): item is WatermarkInsertion => Boolean(item))
}

export function groupWatermarkInsertions(
  insertions: WatermarkInsertion[],
): Map<string | 'end', WatermarkInsertion[]> {
  const grouped = new Map<string | 'end', WatermarkInsertion[]>()
  for (const insertion of insertions) {
    const list = grouped.get(insertion.afterId) || []
    list.push(insertion)
    grouped.set(insertion.afterId, list)
  }
  return grouped
}

export function updateWatermark(
  watermarks: WatermarkItem[],
  kind: WatermarkKind,
  patch: Partial<Pick<WatermarkItem, 'enabled' | 'anchor' | 'content'>>,
): WatermarkItem[] {
  return watermarks.map((item) => (item.kind === kind ? { ...item, ...patch } : item))
}
