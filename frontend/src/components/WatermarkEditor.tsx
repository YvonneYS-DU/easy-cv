import type { WatermarkAnchor, WatermarkItem, WatermarkKind } from '../types/resume'
import { normalizeHiddenKeywords } from '../utils/resume'
import {
  WATERMARK_ANCHORS,
  WATERMARK_KIND_META,
  WATERMARK_KINDS,
} from '../utils/watermark'

interface Props {
  includeHidden: boolean
  watermarks: WatermarkItem[]
  onIncludeChange: (value: boolean) => void
  onChange: (kind: WatermarkKind, patch: Partial<Pick<WatermarkItem, 'enabled' | 'anchor' | 'content'>>) => void
}

export function WatermarkEditor({ includeHidden, watermarks, onIncludeChange, onChange }: Props) {
  const enabledCount = watermarks.filter((item) => item.enabled && normalizeHiddenKeywords(item.content).length).length

  return (
    <div className="cv-watermark-editor">
      <div className="cv-edit-section-head">
        <span className="cv-field-label body-xs" style={{ marginBottom: 0 }}>
          隐藏水印
        </span>
        <label className="cv-switch body-xs">
          <input
            type="checkbox"
            checked={includeHidden}
            onChange={(e) => onIncludeChange(e.target.checked)}
          />
          插入白字
        </label>
      </div>
      <p className="cv-export-desc body-xs" style={{ margin: '0 0 8px' }}>
        不同类型插到不同位置。类型开关和插入位点会记住。
      </p>
      <div className="cv-watermark-list">
        {WATERMARK_KINDS.map((kind) => {
          const item = watermarks.find((wm) => wm.kind === kind)
          if (!item) return null
          const meta = WATERMARK_KIND_META[kind]
          const count = normalizeHiddenKeywords(item.content).length
          return (
            <div key={kind} className={`cv-watermark-card${!item.enabled || !includeHidden ? ' is-off' : ''}`}>
              <div className="cv-watermark-card-head">
                <label className="cv-switch body-xs">
                  <input
                    type="checkbox"
                    checked={item.enabled}
                    disabled={!includeHidden}
                    onChange={(e) => onChange(kind, { enabled: e.target.checked })}
                  />
                  {meta.label}
                </label>
                <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {meta.hint}
                </span>
              </div>
              <label className="cv-field">
                <span className="cv-field-label body-xs">插入位置</span>
                <select
                  className="cv-select"
                  disabled={!includeHidden || !item.enabled}
                  value={item.anchor}
                  onChange={(e) => onChange(kind, { anchor: e.target.value as WatermarkAnchor })}
                >
                  {WATERMARK_ANCHORS.map((anchor) => (
                    <option key={anchor.value} value={anchor.value}>
                      {anchor.label}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                className="cv-textarea"
                rows={3}
                disabled={!includeHidden || !item.enabled}
                placeholder={meta.placeholder}
                value={item.content}
                onChange={(e) => onChange(kind, { content: e.target.value })}
              />
              <div className="cv-export-meta body-xs">
                <span>
                  {count} 个词
                  {item.enabled && includeHidden ? ' · 已插入' : ' · 未插入'}
                </span>
              </div>
            </div>
          )
        })}
      </div>
      <div className="cv-export-meta body-xs">
        <span>
          {enabledCount} 类已插入
          {includeHidden ? '' : ' · 总开关已关'}
        </span>
      </div>
    </div>
  )
}
