import type { ReactNode } from 'react'
import {
  LoaderCircle,
  Sparkles,
  X,
} from 'lucide-react'
import type { ChatTurn, StructuredBlock, SuggestionItem, WatermarkItem, WatermarkKind } from '../types/resume'
import { BlockEditor } from './BlockEditor'
import { WatermarkEditor } from './WatermarkEditor'

const QUICK_PROMPTS = [
  '按当前投递方向改写这段',
  '量化成果',
  '补上素材库里相关但漏写的点',
  '润色，尽量保留技术栈',
  '精简这段文字',
]

interface Props {
  open: boolean
  selectedChip: string | null
  draft: StructuredBlock | null
  onDraftChange: (next: StructuredBlock) => void
  instruction: string
  loading: boolean
  turns: ChatTurn[]
  suggestions: SuggestionItem[]
  onInstructionChange: (value: string) => void
  onSend: () => void
  onQuick: (text: string) => void
  onApply: (id: string) => void
  onIgnore: (id: string) => void
  onClose: () => void
  tab: 'edit' | 'tools'
  onTabChange: (tab: 'edit' | 'tools') => void
  toolsSlot: ReactNode
  includeHiddenKeywords: boolean
  watermarks: WatermarkItem[]
  onIncludeHiddenChange: (value: boolean) => void
  onWatermarkChange: (
    kind: WatermarkKind,
    patch: Partial<Pick<WatermarkItem, 'enabled' | 'anchor' | 'content'>>,
  ) => void
}

export function AiPanel({
  open,
  selectedChip,
  draft,
  onDraftChange,
  instruction,
  loading,
  turns,
  suggestions,
  onInstructionChange,
  onSend,
  onQuick,
  onApply,
  onIgnore,
  onClose,
  tab,
  onTabChange,
  toolsSlot,
  includeHiddenKeywords,
  watermarks,
  onIncludeHiddenChange,
  onWatermarkChange,
}: Props) {
  const empty = !selectedChip

  return (
    <aside className={`cv-right${open ? ' open' : ''}${empty && tab === 'edit' ? ' cv-ai-empty' : ''}`}>
      <div className="cv-panel-head">
        <div className="cv-panel-head-left">
          <span className="heading-xs">AI 助手</span>
          {selectedChip ? (
            <span className="cv-selected-chip body-xs">{selectedChip}</span>
          ) : null}
        </div>
        <button className="cv-icon-btn cv-panel-mobile-close" type="button" onClick={onClose} aria-label="关闭面板">
          <X size={14} />
        </button>
        <button className="cv-icon-btn hide-mobile-only" type="button" onClick={onClose} aria-label="清除选中">
          <X size={14} />
        </button>
      </div>

      <div className="cv-panel-tabs">
        <button
          type="button"
          className={`cv-tab body-md${tab === 'edit' ? ' active' : ''}`}
          onClick={() => onTabChange('edit')}
        >
          区块编辑
        </button>
        <button
          type="button"
          className={`cv-tab body-md${tab === 'tools' ? ' active' : ''}`}
          onClick={() => onTabChange('tools')}
        >
          素材 / JD
        </button>
      </div>

      {tab === 'edit' ? (
        <div className="cv-panel-scroll">
          <div className="ai-gated" id="ai-selected-region">
            <div className="cv-edit-section-head">
              <span className="cv-field-label body-xs" style={{ marginBottom: 0 }}>
                直接编辑
              </span>
              <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
                改词即时生效
              </span>
            </div>
            <BlockEditor data={draft} onChange={onDraftChange} />
          </div>

          <div className="cv-divider" />

          <WatermarkEditor
            includeHidden={includeHiddenKeywords}
            watermarks={watermarks}
            onIncludeChange={onIncludeHiddenChange}
            onChange={onWatermarkChange}
          />

          <div className="cv-divider" />

          <div className="ai-gated" id="ai-instruction-region">
            <span className="cv-field-label body-xs">告诉 AI 如何完善</span>
            <textarea
              className="cv-textarea"
              rows={3}
              placeholder="例如：只改 GPA 为 3.9/4.0；或：按我现在的写法润色，别改结构…"
              value={instruction}
              onChange={(e) => onInstructionChange(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                  e.preventDefault()
                  onSend()
                }
              }}
            />
          </div>

          <div className="cv-quick-chips ai-gated">
            {QUICK_PROMPTS.map((p) => (
              <button key={p} className="cv-quick-chip body-xs" type="button" onClick={() => onQuick(p)}>
                {p}
              </button>
            ))}
          </div>

          <button
            className="cv-send-btn body-md ai-gated"
            type="button"
            disabled={loading || !instruction.trim() || empty}
            onClick={onSend}
          >
            {loading ? <LoaderCircle size={14} className="spin" /> : <Sparkles size={14} />}
            <span>{loading ? 'AI 生成中…' : '基于当前内容完善'}</span>
          </button>

          <div className="cv-divider" />
          <span className="cv-field-label body-xs" style={{ marginBottom: 0 }}>
            AI 修改建议
          </span>

          {turns.length === 0 ? (
            <div className="cv-msg-ai body-sm">
              选中区块后，AI 会结合投递方向、写法分支和素材库漏写点给出建议。点「应用」写入简历，「忽略」丢弃。素材本身无接受/拒绝。
            </div>
          ) : null}

          {turns.map((t) => {
            if (t.role === 'user') {
              return (
                <div key={t.id} className="cv-msg-user body-sm">
                  {t.text}
                </div>
              )
            }
            const suggestion = suggestions.find((s) => s.id === t.suggestionId)
            if (!suggestion) {
              return (
                <div key={t.id} className="cv-msg-ai body-sm">
                  {t.text}
                </div>
              )
            }
            return (
              <div key={t.id} className="cv-diff-card">
                <div className="cv-diff-head">
                  <Sparkles size={12} />
                  <span className="body-xs">
                    {suggestion.status === 'pending'
                      ? '建议修改'
                      : suggestion.status === 'applied'
                        ? '已应用'
                        : '已忽略'}
                  </span>
                </div>
                <div className="cv-diff-body">
                  <span className="cv-diff-del">{suggestion.originalText}</span>
                  {'\n'}
                  <span className="cv-diff-add">{suggestion.suggestedText}</span>
                </div>
                {suggestion.status === 'pending' ? (
                  <div className="cv-diff-actions">
                    <button className="cv-btn-apply body-xs" type="button" onClick={() => onApply(suggestion.id)}>
                      应用
                    </button>
                    <button className="cv-btn-ignore body-xs" type="button" onClick={() => onIgnore(suggestion.id)}>
                      忽略
                    </button>
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="cv-panel-scroll">{toolsSlot}</div>
      )}

      <div className="cv-panel-hint">
        <p className="body-xs" style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          {empty && tab === 'edit'
            ? '当前未选中任何区块，点击左侧简历任意位置开始'
            : '手改即时写入简历；AI 会读取你当前编辑后的内容'}
        </p>
      </div>
    </aside>
  )
}
