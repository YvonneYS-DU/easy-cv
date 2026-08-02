export type BlockKind =
  | 'contact'
  | 'education'
  | 'skill'
  | 'work'
  | 'project'
  | 'summary'
  | 'custom'

export type StructuredBlock =
  | {
      form: 'contact'
      name: string
      contact: string
    }
  | {
      form: 'skill'
      label: string
      value: string
    }
  | {
      form: 'entry'
      title: string
      date: string
      subtitle: string
      meta: string
      bullets: string[]
    }
  | {
      form: 'text'
      lines: string[]
    }

export type ResumeNode =
  | {
      type: 'section'
      id: string
      title: string
    }
  | {
      type: 'block'
      id: string
      chip: string
      kind: BlockKind
      html: string
    }

export interface ResumeDocument {
  id: string
  title: string
  domain: string
  nodes: ResumeNode[]
  updatedAt: string
  /** ATS hidden keywords: injected on print/export; nearly invisible to humans */
  hiddenKeywords?: string[]
  /** Whether to inject hidden keywords on export; default true */
  includeHiddenKeywords?: boolean
}

export interface SuggestionItem {
  id: string
  blockId: string
  instruction: string
  originalText: string
  suggestedText: string
  status: 'pending' | 'applied' | 'ignored'
}

export interface ChatTurn {
  id: string
  role: 'user' | 'ai'
  text: string
  suggestionId?: string
}

export interface SessionMessage {
  id: string
  role: string
  content: string
  timestamp: string
  block_id: string
  chip: string
  instruction: string
  original_text: string
  suggested_text: string
  suggestion_status: string
  meta: Record<string, unknown>
}

export interface ChatSession {
  id: string
  resume_id: string
  domain: string
  title: string
  messages: SessionMessage[]
  created_at: string
  updated_at: string
}

export interface DomainInfo {
  key: string
  label: string
  core_keywords: string[]
}

export interface MaterialRecord {
  id: string
  domain: string
  status: string
  content: {
    id: string
    type: string
    summary: string
    tags: string[]
    fields: Record<string, unknown>
  }
  preferences?: {
    preserve_tech_stack: boolean
    notes: string
  }
  chat_log: Array<{ role: string; msg: string; timestamp: string }>
  created_at: string
  updated_at: string
}

export interface ForgottenExperienceHint {
  material_id: string
  summary: string
  why_relevant: string
  suggested_angle: string
  evidence: string[]
  confidence: number
}

export interface JDMatchResult {
  jd_text: string
  match_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  section_suggestions: Record<string, string>
  gap_analysis: string
  strategy_notes?: string
  forgotten_experiences?: ForgottenExperienceHint[]
  probing_questions?: string[]
}

export interface ResumeVersion {
  id: string
  resume_id: string
  domain: string
  title: string
  source: string
  note: string
  target_role: string
  strategy_id: string
  parent_version_id: string
  version_no: number
  raw_markdown: string
  document_json: Record<string, unknown>
  tags: string[]
  created_at: string
}

export interface BlockRewriteRecord {
  id: string
  resume_id: string
  session_id: string
  message_id: string
  block_id: string
  chip: string
  domain: string
  instruction: string
  original_text: string
  suggested_text: string
  status: string
  strategy_id: string
  target_role: string
  created_at: string
  updated_at: string
}

export interface FramingVariant {
  id: string
  direction: string
  angle: string
  phrasing: string
  why: string
  source_block_id: string
  source_resume_id: string
}

export interface ApplicationStrategy {
  id: string
  name: string
  domain: string
  target_role: string
  company_type: string
  core_message: string
  emphasis: string[]
  de_emphasis: string[]
  framing_rules: string[]
  why: string
  variants: FramingVariant[]
  related_resume_ids: string[]
  related_material_ids: string[]
  notes: string
  created_at: string
  updated_at: string
}
