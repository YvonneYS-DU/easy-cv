import type {
  BlockKind,
  ResumeDocument,
  ResumeNode,
  StructuredBlock,
} from '../types/resume'

export function plainTextFromHtml(html: string): string {
  const el = document.createElement('div')
  el.innerHTML = html
  return (el.textContent || '').replace(/\s+/g, ' ').trim()
}

export function blockPlainText(nodes: ResumeNode[], blockId: string): string {
  const node = nodes.find((n) => n.type === 'block' && n.id === blockId)
  if (!node || node.type !== 'block') return ''
  return structuredToPlain(parseBlockHtml(node.kind, node.html))
}

export function updateBlockHtml(
  doc: ResumeDocument,
  blockId: string,
  html: string,
): ResumeDocument {
  return {
    ...doc,
    updatedAt: new Date().toISOString(),
    nodes: doc.nodes.map((n) =>
      n.type === 'block' && n.id === blockId ? { ...n, html } : n,
    ),
  }
}

export function getBlockNode(nodes: ResumeNode[], blockId: string) {
  const node = nodes.find((n) => n.type === 'block' && n.id === blockId)
  return node && node.type === 'block' ? node : null
}

export function parseBlockHtml(kind: BlockKind, html: string): StructuredBlock {
  const root = document.createElement('div')
  root.innerHTML = html

  if (kind === 'contact') {
    return {
      form: 'contact',
      name: textOf(root.querySelector('.cv-name')) || plainTextFromHtml(html),
      contact: textOf(root.querySelector('.cv-contact-line')),
    }
  }

  if (kind === 'skill') {
    const line = root.querySelector('.cv-skill-line')
    const label = textOf(line?.querySelector('b')).replace(/[:：]\s*$/, '')
    const full = textOf(line)
    let value = full
    if (label && full.startsWith(label)) {
      value = full.slice(label.length).replace(/^[:：]\s*/, '').trim()
    }
    if (!label && !value) {
      const m = plainTextFromHtml(html).match(/^([^:：]+)[:：]\s*(.+)$/)
      if (m) {
        return { form: 'skill', label: m[1].trim(), value: m[2].trim() }
      }
    }
    return { form: 'skill', label, value }
  }

  if (kind === 'work' || kind === 'project' || kind === 'education') {
    const bullets = Array.from(root.querySelectorAll('.cv-bullets li')).map((li) =>
      (li.textContent || '').trim(),
    )
    return {
      form: 'entry',
      title: textOf(root.querySelector('.cv-entry-title')),
      date: textOf(root.querySelector('.cv-entry-date')),
      subtitle: textOf(root.querySelector('.cv-entry-sub')),
      meta: textOf(root.querySelector('.cv-entry-meta')),
      bullets: bullets.length ? bullets : [''],
    }
  }

  const lines = Array.from(root.querySelectorAll('.cv-skill-line, .cv-entry-meta, p, div'))
    .map((el) => (el.textContent || '').trim())
    .filter(Boolean)
  if (lines.length) {
    return { form: 'text', lines }
  }
  const plain = plainTextFromHtml(html)
  return { form: 'text', lines: plain ? [plain] : [''] }
}

export function structuredToHtml(kind: BlockKind, data: StructuredBlock): string {
  if (data.form === 'contact' || kind === 'contact') {
    const d = data.form === 'contact' ? data : { name: '', contact: '' }
    return `<div class="cv-name">${escapeHtml(d.name || 'Name')}</div>
<div class="cv-contact-line">${escapeHtml(d.contact)}</div>`
  }

  if (data.form === 'skill' || kind === 'skill') {
    const d = data.form === 'skill' ? data : { label: '', value: '' }
    if (d.label) {
      return `<div class="cv-skill-line"><b>${escapeHtml(d.label)}:</b> ${escapeHtml(d.value)}</div>`
    }
    return `<div class="cv-skill-line">${escapeHtml(d.value)}</div>`
  }

  if (data.form === 'entry' || kind === 'work' || kind === 'project' || kind === 'education') {
    const d =
      data.form === 'entry'
        ? data
        : { title: '', date: '', subtitle: '', meta: '', bullets: [] as string[] }
    const bullets = d.bullets.map((b) => b.trim()).filter(Boolean)
    const bulletHtml =
      bullets.length > 0
        ? `<ul class="cv-bullets">${bullets
            .map((b) => `<li>${escapeHtml(b)}</li>`)
            .join('')}</ul>`
        : ''
    return `<div class="cv-entry-head">
  <span class="cv-entry-title">${escapeHtml(d.title)}</span>
  <span class="cv-entry-date">${escapeHtml(d.date)}</span>
</div>
${d.subtitle ? `<div class="cv-entry-sub">${escapeHtml(d.subtitle)}</div>` : ''}
${d.meta ? `<div class="cv-entry-meta">${escapeHtml(d.meta)}</div>` : ''}
${bulletHtml}`
  }

  const lines =
    data.form === 'text' ? data.lines.map((l) => l.trim()).filter(Boolean) : []
  if (!lines.length) {
    return `<div class="cv-skill-line"></div>`
  }
  return lines.map((l) => `<div class="cv-skill-line">${escapeHtml(l)}</div>`).join('\n')
}

export function structuredToPlain(data: StructuredBlock): string {
  if (data.form === 'contact') {
    return [data.name, data.contact].filter(Boolean).join('\n')
  }
  if (data.form === 'skill') {
    return data.label ? `${data.label}: ${data.value}` : data.value
  }
  if (data.form === 'entry') {
    const lines = [
      data.title ? `Title: ${data.title}` : '',
      data.date ? `Date: ${data.date}` : '',
      data.subtitle ? `Subtitle: ${data.subtitle}` : '',
      data.meta ? `Meta: ${data.meta}` : '',
      ...data.bullets.map((b) => b.trim()).filter(Boolean).map((b) => `- ${b}`),
    ].filter(Boolean)
    return lines.join('\n')
  }
  return data.lines.filter(Boolean).join('\n')
}

export function plainToStructured(kind: BlockKind, plain: string): StructuredBlock {
  const lines = plain
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  if (kind === 'contact') {
    return {
      form: 'contact',
      name: stripLabel(lines[0] || '', ['Name', '姓名']) || 'Name',
      contact: lines
        .slice(1)
        .map((l) => stripLabel(l, ['Contact', '联系方式']))
        .join(' · '),
    }
  }

  if (kind === 'skill') {
    const joined = lines.join(' ')
    const labeled = joined.match(/^(?:Label|技能)?\s*[:：]?\s*([^:：]+)[:：]\s*(.+)$/i)
    if (labeled) {
      return { form: 'skill', label: labeled[1].trim(), value: labeled[2].trim() }
    }
    const m = joined.match(/^([^:：]+)[:：]\s*(.+)$/)
    if (m) return { form: 'skill', label: m[1].trim(), value: m[2].trim() }
    return { form: 'skill', label: '', value: joined }
  }

  if (kind === 'work' || kind === 'project' || kind === 'education') {
    const bullets = lines
      .filter((l) => /^[-•*]/.test(l) || /^\d+\./.test(l))
      .map((b) => b.replace(/^[-•*]\s*/, '').replace(/^\d+\.\s*/, '').trim())
    const heads = lines.filter((l) => !/^[-•*]/.test(l) && !/^\d+\./.test(l))

    let title = ''
    let date = ''
    let subtitle = ''
    let meta = ''

    for (const h of heads) {
      const t = matchField(h, ['Title', '标题', '职位', '学校', 'Company', 'Role'])
      const d = matchField(h, ['Date', '时间', '日期', 'Period'])
      const s = matchField(h, ['Subtitle', '副标题', '学位', 'Degree', 'Role'])
      const m = matchField(h, ['Meta', '补充', 'GPA', 'Courses', '课程'])
      if (t !== null && !title) title = t
      else if (d !== null && !date) date = d
      else if (s !== null && !subtitle) subtitle = s
      else if (m !== null && !meta) meta = m
      else if (!title) title = h
      else if (!date && /\d{4}/.test(h) && h.length < 40) date = h
      else if (!subtitle) subtitle = h
      else if (!meta) meta = h
    }

    return {
      form: 'entry',
      title,
      date,
      subtitle,
      meta,
      bullets: bullets.length ? bullets : [''],
    }
  }

  return {
    form: 'text',
    lines: lines.length ? lines : [''],
  }
}

export function applyStructuredToBlock(
  doc: ResumeDocument,
  blockId: string,
  data: StructuredBlock,
): ResumeDocument {
  const node = getBlockNode(doc.nodes, blockId)
  if (!node) return doc
  return updateBlockHtml(doc, blockId, structuredToHtml(node.kind, data))
}

export function applyPlainTextToBlock(
  doc: ResumeDocument,
  blockId: string,
  plain: string,
): ResumeDocument {
  const node = getBlockNode(doc.nodes, blockId)
  if (!node) return doc
  const structured = plainToStructured(node.kind, plain)
  return applyStructuredToBlock(doc, blockId, structured)
}

function textOf(el: Element | null | undefined): string {
  return (el?.textContent || '').trim()
}

function stripLabel(line: string, labels: string[]): string {
  for (const label of labels) {
    const re = new RegExp(`^${label}\\s*[:：]\\s*`, 'i')
    if (re.test(line)) return line.replace(re, '').trim()
  }
  return line
}

function matchField(line: string, labels: string[]): string | null {
  for (const label of labels) {
    const re = new RegExp(`^${label}\\s*[:：]\\s*(.+)$`, 'i')
    const m = line.match(re)
    if (m) return m[1].trim()
  }
  return null
}

export function normalizeHiddenKeywords(input: string | string[] | undefined | null): string[] {
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

export function getEffectiveHiddenKeywords(doc: ResumeDocument): string[] {
  if (doc.includeHiddenKeywords === false) return []
  return normalizeHiddenKeywords(doc.hiddenKeywords)
}

export function hiddenKeywordsToText(keywords: string[]): string {
  return keywords.join(' · ')
}

export function resumeToMarkdown(doc: ResumeDocument, opts?: { includeHidden?: boolean }): string {
  const parts: string[] = []
  for (const node of doc.nodes) {
    if (node.type === 'section') {
      parts.push(`\n## ${node.title}\n`)
    } else {
      parts.push(plainTextFromHtml(node.html))
    }
  }
  let body = parts.join('\n').trim() + '\n'
  const includeHidden = opts?.includeHidden ?? doc.includeHiddenKeywords !== false
  const hidden = includeHidden ? normalizeHiddenKeywords(doc.hiddenKeywords) : []
  if (hidden.length) {
    body += `\n<!-- ATS Hidden Keywords: ${hidden.join(', ')} -->\n`
    body += `\n${hiddenKeywordsToText(hidden)}\n`
  }
  return body
}

export function resumeToPlainText(doc: ResumeDocument, opts?: { includeHidden?: boolean }): string {
  const parts: string[] = []
  for (const node of doc.nodes) {
    if (node.type === 'section') {
      parts.push(`\n${node.title}\n`)
    } else {
      parts.push(plainTextFromHtml(node.html))
    }
  }
  let body = parts.join('\n').trim() + '\n'
  const includeHidden = opts?.includeHidden ?? doc.includeHiddenKeywords !== false
  const hidden = includeHidden ? normalizeHiddenKeywords(doc.hiddenKeywords) : []
  if (hidden.length) {
    body += `\n${hiddenKeywordsToText(hidden)}\n`
  }
  return body
}

export function parseImportedText(text: string): ResumeDocument {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  const nodes: ResumeNode[] = []
  let i = 0
  const name = lines[0] || 'Imported Resume'
  const contact = lines[1] || ''
  nodes.push({
    type: 'block',
    id: 'contact',
    chip: '基本信息',
    kind: 'contact',
    html: `<div class="cv-name">${escapeHtml(name.replace(/^#\s*/, ''))}</div>
<div class="cv-contact-line">${escapeHtml(contact.replace(/^#\s*/, ''))}</div>`,
  })
  i = contact ? 2 : 1

  let sectionCount = 0
  let blockCount = 0
  let currentSection = ''
  let buffer: string[] = []

  const flush = () => {
    if (!buffer.length) return
    blockCount += 1
    const id = `block-${blockCount}`
    const chip = currentSection ? `${currentSection} · ${blockCount}` : `Block · ${blockCount}`
    const kind =
      /education/i.test(currentSection) || /教育/.test(currentSection)
        ? 'education'
        : /skill/i.test(currentSection) || /技能/.test(currentSection)
          ? 'skill'
          : /work|experience|项目|project/i.test(currentSection)
            ? 'work'
            : 'custom'
    const bullets = buffer.filter((l) => /^[-•*]/.test(l) || /^\d+\./.test(l))
    let html = ''
    if (kind === 'skill') {
      html = buffer
        .map((l) => {
          const m = l.match(/^([^:：]+)[:：]\s*(.+)$/)
          if (m) {
            return `<div class="cv-skill-line"><b>${escapeHtml(m[1])}:</b> ${escapeHtml(m[2])}</div>`
          }
          return `<div class="cv-skill-line">${escapeHtml(l)}</div>`
        })
        .join('\n')
    } else if (bullets.length) {
      const heads = buffer.filter((l) => !bullets.includes(l))
      html = `<div class="cv-entry-head">
  <span class="cv-entry-title">${escapeHtml(heads[0] || chip)}</span>
  <span class="cv-entry-date">${escapeHtml(heads[1] || '')}</span>
</div>
${heads[2] ? `<div class="cv-entry-sub">${escapeHtml(heads[2])}</div>` : ''}
<ul class="cv-bullets">${bullets
        .map((b) => `<li>${escapeHtml(b.replace(/^[-•*]\s*/, '').replace(/^\d+\.\s*/, ''))}</li>`)
        .join('')}</ul>`
    } else {
      html = `<div class="cv-entry-title">${escapeHtml(buffer[0] || '')}</div>
${buffer
  .slice(1)
  .map((l) => `<div class="cv-entry-meta">${escapeHtml(l)}</div>`)
  .join('\n')}`
    }
    nodes.push({ type: 'block', id, chip, kind, html })
    buffer = []
  }

  while (i < lines.length) {
    const line = lines[i].replace(/^#+\s*/, '')
    const isHeading =
      /^(education|professional skills|skills|work experience|experience|projects|project|summary|教育|技能|工作经历|项目)/i.test(
        line,
      ) && line.length < 40
    if (isHeading) {
      flush()
      sectionCount += 1
      currentSection = line
      nodes.push({ type: 'section', id: `sec-${sectionCount}`, title: line })
    } else if (!line) {
      flush()
    } else {
      buffer.push(line)
      const next = lines[i + 1]
      const nextIsHeading =
        next &&
        /^(education|professional skills|skills|work experience|experience|projects|project|summary|教育|技能|工作经历|项目)/i.test(
          next.replace(/^#+\s*/, ''),
        ) &&
        next.length < 40
      if (nextIsHeading) flush()
    }
    i += 1
  }
  flush()

  return {
    id: `import-${Date.now()}`,
    title: name.replace(/^#\s*/, ''),
    domain: 'ai_engineer',
    updatedAt: new Date().toISOString(),
    nodes,
  }
}

export function markdownSectionsToDocument(
  title: string,
  domain: string,
  sections: Array<{ name: string; content: string }>,
): ResumeDocument {
  const nodes: ResumeNode[] = [
    {
      type: 'block',
      id: 'contact',
      chip: '基本信息',
      kind: 'contact',
      html: `<div class="cv-name">${escapeHtml(title)}</div>
<div class="cv-contact-line">email@example.com · Your City</div>`,
    },
  ]

  sections.forEach((sec, idx) => {
    const titleMap: Record<string, string> = {
      summary: 'Professional Summary',
      education: 'Education',
      skills: 'Professional Skills',
      work_experience: 'Work Experience',
      projects: 'Projects',
    }
    const sectionTitle = titleMap[sec.name] || sec.name
    nodes.push({ type: 'section', id: `sec-${idx}`, title: sectionTitle })
    const chunks = sec.content
      .split(/\n{2,}/)
      .map((c) => c.trim())
      .filter(Boolean)
    chunks.forEach((chunk, j) => {
      const kind =
        sec.name === 'skills'
          ? 'skill'
          : sec.name === 'education'
            ? 'education'
            : sec.name === 'work_experience'
              ? 'work'
              : sec.name === 'projects'
                ? 'project'
                : 'custom'
      const lines = chunk.split('\n').map((l) => l.trim()).filter(Boolean)
      let html = ''
      if (kind === 'skill') {
        html = lines
          .map((l) => {
            const clean = l.replace(/^\*\*|\*\*$/g, '').replace(/\*\*/g, '')
            const m = clean.match(/^([^:：]+)[:：]\s*(.+)$/)
            if (m) {
              return `<div class="cv-skill-line"><b>${escapeHtml(m[1])}:</b> ${escapeHtml(m[2])}</div>`
            }
            return `<div class="cv-skill-line">${escapeHtml(clean)}</div>`
          })
          .join('\n')
      } else {
        const bullets = lines.filter((l) => /^[-•*]/.test(l))
        const heads = lines.filter((l) => !bullets.includes(l))
        html = `<div class="cv-entry-head">
  <span class="cv-entry-title">${escapeHtml(heads[0] || sectionTitle)}</span>
  <span class="cv-entry-date"></span>
</div>
${heads
  .slice(1)
  .map((h) => `<div class="cv-entry-meta">${escapeHtml(h)}</div>`)
  .join('\n')}
${
  bullets.length
    ? `<ul class="cv-bullets">${bullets
        .map((b) => `<li>${escapeHtml(b.replace(/^[-•*]\s*/, ''))}</li>`)
        .join('')}</ul>`
    : ''
}`
      }
      nodes.push({
        type: 'block',
        id: `${sec.name}-${j}`,
        chip: `${sectionTitle} · ${j + 1}`,
        kind,
        html,
      })
    })
  })

  return {
    id: `gen-${Date.now()}`,
    title,
    domain,
    updatedAt: new Date().toISOString(),
    nodes,
  }
}

function escapeHtml(input: string): string {
  return input
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}
