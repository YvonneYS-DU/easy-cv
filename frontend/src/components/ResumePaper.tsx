import type { ResumeDocument } from '../types/resume'
import { getEffectiveHiddenKeywords, hiddenKeywordsToText } from '../utils/resume'

interface Props {
  doc: ResumeDocument
  selectedId: string | null
  onSelect: (blockId: string) => void
}

export function ResumePaper({ doc, selectedId, onSelect }: Props) {
  const hidden = getEffectiveHiddenKeywords(doc)

  return (
    <article className="cv-paper">
      {doc.nodes.map((node) => {
        if (node.type === 'section') {
          return (
            <div key={node.id} className="cv-section-title">
              {node.title}
            </div>
          )
        }
        return (
          <div
            key={node.id}
            className={`cv-block${selectedId === node.id ? ' cv-block-selected' : ''}`}
            data-block-id={node.id}
            onClick={() => onSelect(node.id)}
            dangerouslySetInnerHTML={{ __html: node.html }}
          />
        )
      })}
      {hidden.length > 0 ? (
        <div className="cv-ats-hidden" aria-hidden="true" data-ats-keywords="true">
          {hiddenKeywordsToText(hidden)}
        </div>
      ) : null}
    </article>
  )
}
