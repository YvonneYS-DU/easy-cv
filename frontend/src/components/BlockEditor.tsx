import { Plus, Trash2 } from 'lucide-react'
import type { StructuredBlock } from '../types/resume'

interface Props {
  data: StructuredBlock | null
  onChange: (next: StructuredBlock) => void
}

export function BlockEditor({ data, onChange }: Props) {
  if (!data) {
    return (
      <div className="cv-selected-text body-sm" style={{ color: 'var(--text-tertiary)' }}>
        点击左侧简历区块开始编辑
      </div>
    )
  }

  if (data.form === 'contact') {
    return (
      <div className="cv-block-editor">
        <label className="cv-field">
          <span className="cv-field-label body-xs">姓名</span>
          <input
            className="cv-input"
            value={data.name}
            onChange={(e) => onChange({ ...data, name: e.target.value })}
            placeholder="Zhang Wei"
          />
        </label>
        <label className="cv-field">
          <span className="cv-field-label body-xs">联系方式</span>
          <input
            className="cv-input"
            value={data.contact}
            onChange={(e) => onChange({ ...data, contact: e.target.value })}
            placeholder="email · phone · city · linkedin"
          />
        </label>
      </div>
    )
  }

  if (data.form === 'skill') {
    return (
      <div className="cv-block-editor">
        <label className="cv-field">
          <span className="cv-field-label body-xs">类别</span>
          <input
            className="cv-input"
            value={data.label}
            onChange={(e) => onChange({ ...data, label: e.target.value })}
            placeholder="Programming Languages"
          />
        </label>
        <label className="cv-field">
          <span className="cv-field-label body-xs">内容</span>
          <input
            className="cv-input"
            value={data.value}
            onChange={(e) => onChange({ ...data, value: e.target.value })}
            placeholder="Python, Rust, R"
          />
        </label>
      </div>
    )
  }

  if (data.form === 'entry') {
    return (
      <div className="cv-block-editor">
        <div className="cv-field-row">
          <label className="cv-field cv-field-grow">
            <span className="cv-field-label body-xs">标题 / 职位 / 学校</span>
            <input
              className="cv-input"
              value={data.title}
              onChange={(e) => onChange({ ...data, title: e.target.value })}
              placeholder="AI Engineer - RightShip"
            />
          </label>
          <label className="cv-field cv-field-date">
            <span className="cv-field-label body-xs">时间</span>
            <input
              className="cv-input"
              value={data.date}
              onChange={(e) => onChange({ ...data, date: e.target.value })}
              placeholder="Sep 2024 - Now"
            />
          </label>
        </div>
        <label className="cv-field">
          <span className="cv-field-label body-xs">副标题 / 学位</span>
          <input
            className="cv-input"
            value={data.subtitle}
            onChange={(e) => onChange({ ...data, subtitle: e.target.value })}
            placeholder="Master of Tech · optional"
          />
        </label>
        <label className="cv-field">
          <span className="cv-field-label body-xs">补充信息</span>
          <input
            className="cv-input"
            value={data.meta}
            onChange={(e) => onChange({ ...data, meta: e.target.value })}
            placeholder="GPA / courses / location"
          />
        </label>
        <div className="cv-field">
          <div className="cv-bullet-head">
            <span className="cv-field-label body-xs" style={{ marginBottom: 0 }}>
              要点
            </span>
            <button
              type="button"
              className="cv-text-btn body-xs"
              onClick={() => onChange({ ...data, bullets: [...data.bullets, ''] })}
            >
              <Plus size={12} />
              添加
            </button>
          </div>
          <div className="cv-bullet-list">
            {data.bullets.map((bullet, idx) => (
              <div key={idx} className="cv-bullet-row">
                <span className="cv-bullet-dot">•</span>
                <textarea
                  className="cv-textarea cv-bullet-input"
                  rows={2}
                  value={bullet}
                  onChange={(e) => {
                    const bullets = data.bullets.slice()
                    bullets[idx] = e.target.value
                    onChange({ ...data, bullets })
                  }}
                  placeholder="写一条可量化的成果…"
                />
                <button
                  type="button"
                  className="cv-icon-btn"
                  aria-label="删除要点"
                  disabled={data.bullets.length <= 1}
                  onClick={() => {
                    const bullets = data.bullets.filter((_, i) => i !== idx)
                    onChange({ ...data, bullets: bullets.length ? bullets : [''] })
                  }}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="cv-block-editor">
      <label className="cv-field">
        <span className="cv-field-label body-xs">正文</span>
        <textarea
          className="cv-textarea"
          rows={5}
          value={data.lines.join('\n')}
          onChange={(e) =>
            onChange({
              form: 'text',
              lines: e.target.value.split('\n'),
            })
          }
          placeholder="直接编辑这段文字…"
        />
      </label>
    </div>
  )
}
