import type { ResumeDocument, ResumeNode } from '../types/resume'
import { hiddenKeywordsToText } from '../utils/resume'
import { getWatermarkInsertions, groupWatermarkInsertions } from '../utils/watermark'

interface Props {
  doc: ResumeDocument
  selectedId: string | null
  onSelect: (blockId: string) => void
}

function HiddenLayer({
  insertions,
}: {
  insertions: ReturnType<typeof getWatermarkInsertions>
}) {
  if (!insertions.length) return null
  return (
    <>
      {insertions.map((insertion) => (
        <div
          key={insertion.item.id}
          className="cv-ats-hidden"
          data-ats-keywords="true"
          data-watermark-kind={insertion.item.kind}
        >
          {hiddenKeywordsToText(insertion.keywords)}
        </div>
      ))}
    </>
  )
}

function renderNode(
  node: ResumeNode,
  selectedId: string | null,
  onSelect: (blockId: string) => void,
) {
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
}

export function ResumePaper({ doc, selectedId, onSelect }: Props) {
  const grouped = groupWatermarkInsertions(getWatermarkInsertions(doc))

  return (
    <article className="cv-paper">
      {doc.nodes.map((node) => (
        <div key={node.id} className="cv-paper-slot">
          {renderNode(node, selectedId, onSelect)}
          <HiddenLayer insertions={grouped.get(node.id) || []} />
        </div>
      ))}
      <HiddenLayer insertions={grouped.get('end') || []} />
    </article>
  )
}
