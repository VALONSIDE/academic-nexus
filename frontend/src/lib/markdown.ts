import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
  'a', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'hr', 'li',
  'ol', 'p', 'pre', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
]
const ALLOWED_ATTRIBUTES = ['href', 'rel', 'target']

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function safeLink(label: string, rawUrl: string): string {
  try {
    const url = new URL(rawUrl)
    if (url.protocol !== 'https:' && url.protocol !== 'http:') return label
    return `<a href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">${label}</a>`
  } catch {
    return label
  }
}

function inlineMarkdown(source: string): string {
  return source
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label: string, url: string) => safeLink(label, url))
}

/**
 * Render the intentionally small Markdown subset used by assistant messages.
 * All source text is escaped before markup is introduced, then DOMPurify
 * enforces an allowlist as a second line of defense for future renderer edits.
 */
export function renderMarkdown(source: string): string {
  const lines = escapeHtml(source).replace(/\r\n?/g, '\n').split('\n')
  const output: string[] = []
  let index = 0
  const at = (position: number) => lines[position] ?? ''
  const isSpecial = (line: string) => /^(#{1,3}\s+|```|&gt;\s?|[-*+]\s+|\d+\.\s+|\|)/.test(line)

  while (index < lines.length) {
    const line = at(index)
    if (!line.trim()) {
      index += 1
      continue
    }
    if (line.startsWith('```')) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !at(index).startsWith('```')) {
        code.push(at(index))
        index += 1
      }
      if (index < lines.length) index += 1
      output.push(`<pre><code>${code.join('\n')}</code></pre>`)
      continue
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      const level = heading[1] ?? '#'
      output.push(`<h${level.length}>${inlineMarkdown(heading[2] ?? '')}</h${level.length}>`)
      index += 1
      continue
    }
    if (/^([-*_])\1\1+$/.test(line.trim())) {
      output.push('<hr>')
      index += 1
      continue
    }
    if (line.startsWith('&gt;')) {
      const quote: string[] = []
      while (index < lines.length && at(index).startsWith('&gt;')) {
        quote.push(at(index).replace(/^&gt;\s?/, ''))
        index += 1
      }
      output.push(`<blockquote>${inlineMarkdown(quote.join('<br>'))}</blockquote>`)
      continue
    }
    const unordered = line.match(/^[-*+]\s+(.+)$/)
    const ordered = line.match(/^\d+\.\s+(.+)$/)
    if (unordered || ordered) {
      const tag = unordered ? 'ul' : 'ol'
      const entries: string[] = []
      while (index < lines.length) {
        const match = at(index).match(unordered ? /^[-*+]\s+(.+)$/ : /^\d+\.\s+(.+)$/)
        if (!match) break
        entries.push(`<li>${inlineMarkdown(match[1] ?? '')}</li>`)
        index += 1
      }
      output.push(`<${tag}>${entries.join('')}</${tag}>`)
      continue
    }
    if (line.startsWith('|') && line.endsWith('|')) {
      const rows: string[][] = []
      while (index < lines.length && at(index).startsWith('|') && at(index).endsWith('|')) {
        const cells = at(index).slice(1, -1).split('|').map((cell) => cell.trim())
        if (!cells.every((cell) => /^:?-{3,}:?$/.test(cell))) rows.push(cells)
        index += 1
      }
      if (rows.length) {
        const header = rows[0] ?? []
        const body = rows.slice(1)
        output.push(`<table><thead><tr>${header.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join('')}</tr></thead><tbody>${body.map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table>`)
      }
      continue
    }
    const paragraph: string[] = [line]
    index += 1
    while (index < lines.length && at(index).trim() && !isSpecial(at(index))) {
      paragraph.push(at(index))
      index += 1
    }
    output.push(`<p>${inlineMarkdown(paragraph.join('<br>'))}</p>`)
  }

  return DOMPurify.sanitize(output.join(''), {
    ALLOWED_TAGS,
    ALLOWED_ATTR: ALLOWED_ATTRIBUTES,
    ALLOW_DATA_ATTR: false,
    ALLOW_ARIA_ATTR: false,
  })
}
