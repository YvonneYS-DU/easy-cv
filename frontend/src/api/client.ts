import type {
  ApplicationStrategy,
  BlockRewriteRecord,
  ChatSession,
  DomainInfo,
  JDMatchResult,
  MaterialRecord,
  ResumeVersion,
} from '../types/resume'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export interface MetaInfo {
  status: string
  service: string
  mode: 'mock' | 'llm'
  model?: string | null
}

export function getMeta() {
  return request<MetaInfo>('/api/v1/meta')
}

export function listDomains() {
  return request<{ domains: DomainInfo[] }>('/api/v1/domains')
}

export function rewriteBlock(payload: {
  selected_text: string
  instruction: string
  chip?: string
  domain?: string
  block_id?: string
  session_id?: string
  resume_id?: string
  use_history?: boolean
  strategy_id?: string
  target_role?: string
  resume_markdown?: string
  mine_materials?: boolean
  material_ids?: string[]
}) {
  return request<{
    original_text: string
    suggested_text: string
    block_id: string
    chip: string
    session_id: string
    user_message_id: string
    ai_message_id: string
    rewrite_id: string
    ai_note: string
    session?: ChatSession | null
    rewrite?: BlockRewriteRecord | null
    strategy?: ApplicationStrategy | null
    forgotten_experiences?: Array<{
      material_id: string
      summary: string
      why_relevant: string
      suggested_angle: string
      evidence: string[]
      confidence: number
    }>
  }>('/api/v1/resume/block-rewrite', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getOrCreateSession(payload: {
  resume_id?: string
  domain?: string
  title?: string
  session_id?: string
}) {
  return request<{ session: ChatSession }>('/api/v1/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getSession(sessionId: string) {
  return request<{ session: ChatSession }>(`/api/v1/sessions/${sessionId}`)
}

export function listSessions(resumeId = '') {
  const q = resumeId ? `?resume_id=${encodeURIComponent(resumeId)}` : ''
  return request<{ sessions: ChatSession[] }>(`/api/v1/sessions${q}`)
}

export function updateSuggestionStatus(
  sessionId: string,
  messageId: string,
  status: 'applied' | 'ignored' | 'pending',
) {
  return request<{ session: ChatSession }>(
    `/api/v1/sessions/${sessionId}/messages/${messageId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    },
  )
}

export function matchJd(payload: {
  resume_markdown: string
  jd_text: string
  domain?: string
  resume_id?: string
  strategy_id?: string
  target_role?: string
  material_ids?: string[]
  mine_forgotten?: boolean
  save_version?: boolean
  title?: string
}) {
  return request<{
    match_result: JDMatchResult
    suggested_resume?: {
      raw_markdown: string
      domain: string
      version: number
    } | null
    strategy?: ApplicationStrategy | null
    version?: ResumeVersion | null
  }>('/api/v1/resume/match', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listMaterials(domain = '', allDomains = false) {
  const params = new URLSearchParams()
  if (domain) params.set('domain', domain)
  if (allDomains) params.set('all_domains', 'true')
  const q = params.toString() ? `?${params}` : ''
  return request<MaterialRecord[]>(`/api/v1/materials${q}`)
}

export function addMaterial(raw_text: string, domain = '') {
  return request<{ material: MaterialRecord; ai_questions: string[] }>(
    '/api/v1/materials',
    {
      method: 'POST',
      body: JSON.stringify({ raw_text, domain }),
    },
  )
}

export function refineMaterial(material_id: string, user_response: string) {
  return request<{ material: MaterialRecord; ai_questions: string[] }>(
    '/api/v1/materials/refine',
    {
      method: 'PUT',
      body: JSON.stringify({ material_id, user_response }),
    },
  )
}

export function generateFull(
  domain: string,
  material_ids: string[] = [],
  jd_text = '',
  extras?: {
    resume_id?: string
    title?: string
    strategy_id?: string
    target_role?: string
    save_version?: boolean
  },
) {
  return request<{
    resume: {
      domain: string
      raw_markdown: string
      sections: Array<{ name: string; content: string }>
      version: number
    }
    version?: ResumeVersion | null
  }>('/api/v1/resume/full', {
    method: 'POST',
    body: JSON.stringify({
      domain,
      material_ids,
      jd_text,
      resume_id: extras?.resume_id || '',
      title: extras?.title || '',
      strategy_id: extras?.strategy_id || '',
      target_role: extras?.target_role || '',
      save_version: extras?.save_version ?? true,
    }),
  })
}

export function saveResumeVersion(payload: {
  resume_id: string
  raw_markdown?: string
  document_json?: Record<string, unknown>
  domain?: string
  title?: string
  source?: string
  note?: string
  target_role?: string
  strategy_id?: string
  tags?: string[]
}) {
  return request<{ version: ResumeVersion }>('/api/v1/resume/versions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listResumeVersions(resumeId = '', limit = 30) {
  const params = new URLSearchParams()
  if (resumeId) params.set('resume_id', resumeId)
  params.set('limit', String(limit))
  return request<{ versions: ResumeVersion[] }>(
    `/api/v1/resume/versions?${params.toString()}`,
  )
}

export function listBlockRewrites(resumeId = '', blockId = '', status = '') {
  const params = new URLSearchParams()
  if (resumeId) params.set('resume_id', resumeId)
  if (blockId) params.set('block_id', blockId)
  if (status) params.set('status', status)
  const q = params.toString() ? `?${params}` : ''
  return request<{ rewrites: BlockRewriteRecord[] }>(`/api/v1/rewrites${q}`)
}

export function updateBlockRewriteStatus(
  rewriteId: string,
  status: 'applied' | 'ignored' | 'pending',
  sessionId = '',
) {
  return request<{ rewrite: BlockRewriteRecord }>(`/api/v1/rewrites/${rewriteId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, session_id: sessionId }),
  })
}

export function listStrategies(domain = '', resumeId = '') {
  const params = new URLSearchParams()
  if (domain) params.set('domain', domain)
  if (resumeId) params.set('resume_id', resumeId)
  const q = params.toString() ? `?${params}` : ''
  return request<{ strategies: ApplicationStrategy[] }>(`/api/v1/strategies${q}`)
}

export function upsertStrategy(payload: {
  id?: string
  name?: string
  domain?: string
  target_role?: string
  company_type?: string
  core_message?: string
  emphasis?: string[]
  de_emphasis?: string[]
  framing_rules?: string[]
  why?: string
  notes?: string
  resume_id?: string
}) {
  return request<{ strategy: ApplicationStrategy }>('/api/v1/strategies', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
