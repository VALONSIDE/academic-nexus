import { describe, expect, it } from 'vitest'

import { renderMarkdown } from '@/lib/markdown'

describe('renderMarkdown', () => {
  it('escapes HTML supplied by an assistant or user message', () => {
    const html = renderMarkdown('<img src=x onerror=alert(1)><script>alert(1)</script>')
    const rendered = new DOMParser().parseFromString(html, 'text/html')

    expect(rendered.querySelector('img')).toBeNull()
    expect(rendered.querySelector('script')).toBeNull()
    expect(html).toContain('&lt;img')
  })

  it('does not permit attributes to escape a Markdown link', () => {
    const html = renderMarkdown('[Open](https://example.test/\"onmouseover=\"alert(1))')
    const link = new DOMParser().parseFromString(html, 'text/html').querySelector('a')

    expect(html).toContain('href="https://example.test/')
    expect(link?.getAttribute('onmouseover')).toBeNull()
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('preserves the supported safe Markdown subset', () => {
    const html = renderMarkdown('## Heading\n\n**bold** and [link](https://example.test)')

    expect(html).toContain('<h2>Heading</h2>')
    expect(html).toContain('<strong>bold</strong>')
    expect(html).toContain('href="https://example.test/"')
  })
})
