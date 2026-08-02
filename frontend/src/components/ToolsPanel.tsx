import { LoaderCircle } from 'lucide-react'
import type {
  ApplicationStrategy,
  DomainInfo,
  JDMatchResult,
  MaterialRecord,
  ResumeVersion,
} from '../types/resume'

interface Props {
  domain: string
  domains: DomainInfo[]
  onDomainChange: (domain: string) => void
  materialText: string
  onMaterialTextChange: (v: string) => void
  materials: MaterialRecord[]
  materialsLoading: boolean
  onAddMaterial: () => void
  onRefreshMaterials: () => void
  onGenerateFromMaterials: () => void
  jdText: string
  onJdTextChange: (v: string) => void
  targetRole: string
  onTargetRoleChange: (v: string) => void
  matchLoading: boolean
  matchResult: JDMatchResult | null
  strategy: ApplicationStrategy | null
  versions: ResumeVersion[]
  onMatchJd: () => void
  onApplyJdRewrite: () => void
  onSaveVersion: () => void
  onRestoreVersion: (id: string) => void
  canApplyJd: boolean
  busy: boolean
}

export function ToolsPanel({
  domain,
  domains,
  onDomainChange,
  materialText,
  onMaterialTextChange,
  materials,
  materialsLoading,
  onAddMaterial,
  onRefreshMaterials,
  onGenerateFromMaterials,
  jdText,
  onJdTextChange,
  targetRole,
  onTargetRoleChange,
  matchLoading,
  matchResult,
  strategy,
  versions,
  onMatchJd,
  onApplyJdRewrite,
  onSaveVersion,
  onRestoreVersion,
  canApplyJd,
  busy,
}: Props) {
  const forgotten = matchResult?.forgotten_experiences || []
  const questions = matchResult?.probing_questions || []

  return (
    <>
      <div>
        <span className="cv-field-label body-xs">目标领域</span>
        <select className="cv-select" value={domain} onChange={(e) => onDomainChange(e.target.value)}>
          {domains.map((d) => (
            <option key={d.key} value={d.key}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginTop: 10 }}>
        <span className="cv-field-label body-xs">投递方向 / 目标岗位</span>
        <input
          className="cv-select"
          style={{ width: '100%' }}
          placeholder="例如：AI Engineer / Backend / Applied Scientist"
          value={targetRole}
          onChange={(e) => onTargetRoleChange(e.target.value)}
        />
        <p className="body-xs" style={{ color: 'var(--text-tertiary)', margin: '6px 0 0' }}>
          同一套经历会按方向「一样话两样说」；AI 会记住你为什么这样取景。
        </p>
      </div>

      {strategy ? (
        <div className="cv-card-item" style={{ marginTop: 10 }}>
          <div className="body-md" style={{ fontWeight: 600 }}>
            策略：{strategy.name || '默认'}
          </div>
          <div className="body-xs" style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
            {strategy.why || '事实不变，按方向调整强调点。'}
          </div>
          {strategy.emphasis?.length ? (
            <div className="cv-tag-row" style={{ marginTop: 8 }}>
              {strategy.emphasis.slice(0, 8).map((k) => (
                <span key={k} className="cv-tag">
                  {k}
                </span>
              ))}
            </div>
          ) : null}
          {strategy.variants?.length ? (
            <div className="body-xs" style={{ marginTop: 8, color: 'var(--text-tertiary)' }}>
              已沉淀 {strategy.variants.length} 种取景说法
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="cv-divider" />

      <div>
        <span className="cv-field-label body-xs">添加素材（事实库，直接写入）</span>
        <textarea
          className="cv-textarea"
          rows={4}
          placeholder="粘贴经历原文…技术栈会尽量完整保留（少删除）"
          value={materialText}
          onChange={(e) => onMaterialTextChange(e.target.value)}
        />
        <p className="body-xs" style={{ color: 'var(--text-tertiary)', margin: '6px 0 0' }}>
          偏好：tech stack 少删。素材无「接受/忽略」，改了即生效。
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="cv-btn-primary body-md" type="button" disabled={busy || !materialText.trim()} onClick={onAddMaterial}>
            {busy ? <LoaderCircle size={14} /> : null}
            提取素材
          </button>
          <button className="cv-btn-outline body-md" type="button" onClick={onRefreshMaterials} disabled={materialsLoading}>
            刷新
          </button>
        </div>
      </div>

      <div>
        <span className="cv-field-label body-xs">素材库（{materials.length}）</span>
        <div className="cv-card-list">
          {materials.length === 0 ? (
            <div className="body-sm" style={{ color: 'var(--text-tertiary)' }}>
              暂无素材。入库后，选中简历区块让 AI 改写时会自动挖漏写点。
            </div>
          ) : (
            materials.map((m) => {
              const stack = Array.isArray(m.content.fields?.tech_stack)
                ? (m.content.fields.tech_stack as string[]).slice(0, 6)
                : Array.isArray(m.content.fields?.skills)
                  ? (m.content.fields.skills as string[]).slice(0, 6)
                  : m.content.tags.filter((t) => t !== 'mock').slice(0, 6)
              return (
                <div key={m.id} className="cv-card-item">
                  <div className="body-md" style={{ fontWeight: 600 }}>
                    {m.content.summary || m.id}
                  </div>
                  <div className="body-xs" style={{ color: 'var(--text-tertiary)', marginTop: 4 }}>
                    {m.content.type} · {m.status} · {m.domain || 'common'}
                    {m.preferences?.preserve_tech_stack !== false ? ' · stack少删' : ''}
                  </div>
                  {stack.length ? (
                    <div className="cv-tag-row" style={{ marginTop: 6 }}>
                      {stack.map((t) => (
                        <span key={String(t)} className="cv-tag">
                          {String(t)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              )
            })
          )}
        </div>
        <button
          className="cv-send-btn body-md"
          style={{ marginTop: 12 }}
          type="button"
          disabled={busy || materials.length === 0}
          onClick={onGenerateFromMaterials}
        >
          用素材生成完整简历
        </button>
      </div>

      <div className="cv-divider" />

      <div>
        <span className="cv-field-label body-xs">JD 匹配 + 挖经历</span>
        <textarea
          className="cv-textarea"
          rows={5}
          placeholder="粘贴目标职位 JD…"
          value={jdText}
          onChange={(e) => onJdTextChange(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
          <button className="cv-btn-primary body-md" type="button" disabled={matchLoading || !jdText.trim()} onClick={onMatchJd}>
            {matchLoading ? <LoaderCircle size={14} /> : null}
            分析并挖掘
          </button>
          <button className="cv-btn-outline body-md" type="button" disabled={!canApplyJd} onClick={onApplyJdRewrite}>
            应用 JD 改写稿
          </button>
          <button className="cv-btn-outline body-md" type="button" disabled={busy} onClick={onSaveVersion}>
            存版本
          </button>
        </div>
      </div>

      {matchResult ? (
        <div className="cv-card-item">
          <div className="cv-score">{Math.round(matchResult.match_score * 100)}%</div>
          <div className="body-sm" style={{ marginTop: 6, color: 'var(--text-secondary)' }}>
            {matchResult.gap_analysis}
          </div>
          {matchResult.strategy_notes ? (
            <div className="body-sm" style={{ marginTop: 8, color: 'var(--text-brand)' }}>
              策略理解：{matchResult.strategy_notes}
            </div>
          ) : null}
          <div style={{ marginTop: 10 }}>
            <div className="cv-field-label body-xs">已匹配</div>
            <div className="cv-tag-row">
              {matchResult.matched_keywords.length ? (
                matchResult.matched_keywords.map((k) => (
                  <span key={k} className="cv-tag">
                    {k}
                  </span>
                ))
              ) : (
                <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
                  暂无
                </span>
              )}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <div className="cv-field-label body-xs">缺失</div>
            <div className="cv-tag-row">
              {matchResult.missing_keywords.length ? (
                matchResult.missing_keywords.map((k) => (
                  <span key={k} className="cv-tag muted">
                    {k}
                  </span>
                ))
              ) : (
                <span className="body-xs" style={{ color: 'var(--text-tertiary)' }}>
                  暂无
                </span>
              )}
            </div>
          </div>

          {forgotten.length ? (
            <div style={{ marginTop: 12 }}>
              <div className="cv-field-label body-xs">可能漏写（参考）</div>
              <div className="body-xs" style={{ color: 'var(--text-tertiary)', marginBottom: 6 }}>
                要写入简历：选中相关区块 → AI 助手（会自动并入这些点）→ 应用
              </div>
              <div className="cv-card-list" style={{ marginTop: 6 }}>
                {forgotten.map((h, idx) => (
                  <div key={`${h.material_id}-${idx}`} className="cv-card-item">
                    <div className="body-md" style={{ fontWeight: 600 }}>
                      {h.summary}
                    </div>
                    <div className="body-xs" style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                      {h.why_relevant}
                    </div>
                    <div className="body-xs" style={{ color: 'var(--text-brand)', marginTop: 4 }}>
                      建议角度：{h.suggested_angle}
                    </div>
                    {h.evidence?.length ? (
                      <div className="cv-tag-row" style={{ marginTop: 6 }}>
                        {h.evidence.map((e) => (
                          <span key={e} className="cv-tag">
                            {e}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {questions.length ? (
            <div style={{ marginTop: 12 }}>
              <div className="cv-field-label body-xs">帮你回忆的追问</div>
              <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                {questions.map((q) => (
                  <li key={q} className="body-sm" style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="cv-divider" />

      <div>
        <span className="cv-field-label body-xs">简历版本（{versions.length}）</span>
        <div className="cv-card-list">
          {versions.length === 0 ? (
            <div className="body-sm" style={{ color: 'var(--text-tertiary)' }}>
              生成 / JD 改写 / 手动保存后会出现版本快照。
            </div>
          ) : (
            versions.map((v) => (
              <div key={v.id} className="cv-card-item">
                <div className="body-md" style={{ fontWeight: 600 }}>
                  v{v.version_no} · {v.title || v.source || 'snapshot'}
                </div>
                <div className="body-xs" style={{ color: 'var(--text-tertiary)', marginTop: 4 }}>
                  {v.source}
                  {v.target_role ? ` · ${v.target_role}` : ''}
                  {v.note ? ` · ${v.note.slice(0, 48)}` : ''}
                </div>
                <button
                  className="cv-btn-outline body-xs"
                  type="button"
                  style={{ marginTop: 8 }}
                  onClick={() => onRestoreVersion(v.id)}
                >
                  恢复此版本
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  )
}
