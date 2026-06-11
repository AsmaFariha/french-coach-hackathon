// Pure helpers for the Notion-style block editor (BlockEditor.jsx).
//
// Storage format stays a single string (raw_text / `text` state) — but it's
// now a small Markdown-ish dialect instead of plain prose, so old plain-text
// lessons keep working unchanged (they parse as paragraph blocks).
//
// Grammar (intentionally minimal — internal round-trip only, not CommonMark):
//   - heading1/2/3, bulleted, numbered, quote, divider = exactly one line
//   - paragraph = one or more consecutive "plain" lines, joined with <br>
//   - blank lines separate blocks and are otherwise dropped
//   - inline marks: **bold**, *italic*, ~~strikethrough~~

let idCounter = 0
export function genId() {
  idCounter += 1
  return `b${Date.now().toString(36)}${idCounter}`
}

export function newBlock(type = 'paragraph', html = '') {
  return { id: genId(), type, html }
}

export const BLOCK_TAGS = {
  paragraph: 'p',
  heading1: 'h1',
  heading2: 'h2',
  heading3: 'h3',
  bulleted: 'li',
  numbered: 'li',
  quote: 'blockquote',
  divider: 'hr',
}

export const BLOCK_TYPES = [
  { type: 'paragraph', label: 'Text', icon: 'Aa' },
  { type: 'heading1', label: 'Heading 1', icon: 'H1' },
  { type: 'heading2', label: 'Heading 2', icon: 'H2' },
  { type: 'heading3', label: 'Heading 3', icon: 'H3' },
  { type: 'bulleted', label: 'Bulleted list', icon: '•' },
  { type: 'numbered', label: 'Numbered list', icon: '1.' },
  { type: 'quote', label: 'Quote', icon: '❝' },
  { type: 'divider', label: 'Divider', icon: '―' },
]

export const PLACEHOLDERS = {
  paragraph: "Type '/' for commands…",
  heading1: 'Heading 1',
  heading2: 'Heading 2',
  heading3: 'Heading 3',
  bulleted: 'List item',
  numbered: 'List item',
  quote: 'Quote',
}

const HEADING_RE = /^(#{1,3})\s(.*)$/
const BULLETED_RE = /^[-*]\s(.*)$/
const NUMBERED_RE = /^\d+\.\s(.*)$/
const QUOTE_RE = /^>\s?(.*)$/
const DIVIDER_RE = /^-{3,}$/

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function inlineMarkdownToHtml(text) {
  let html = escapeHtml(text)
  html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/~~([^~]+?)~~/g, '<s>$1</s>')
  html = html.replace(/\*([^*]+?)\*/g, '<em>$1</em>')
  return html
}

// Walk inline HTML (only <strong>/<b>/<em>/<i>/<s>/<strike>/<del>/<br> + text
// expected) back into our inline markdown dialect.
function serializeInlineNode(node) {
  let out = ''
  for (const child of node.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      out += child.nodeValue
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      const tag = child.tagName.toLowerCase()
      const inner = serializeInlineNode(child)
      if (tag === 'strong' || tag === 'b') out += `**${inner}**`
      else if (tag === 'em' || tag === 'i') out += `*${inner}*`
      else if (tag === 's' || tag === 'strike' || tag === 'del') out += `~~${inner}~~`
      else if (tag === 'br') out += '\n'
      else out += inner
    }
  }
  return out
}

function htmlToInlineMarkdown(html) {
  if (!html) return ''
  const container = document.createElement('div')
  container.innerHTML = html
  return serializeInlineNode(container)
}

function htmlToPlainText(html) {
  if (!html) return ''
  const container = document.createElement('div')
  container.innerHTML = html.replace(/<br\s*\/?>/gi, ' ')
  return container.textContent
}

export function markdownToBlocks(markdown) {
  const lines = (markdown || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let paraLines = []

  const flushPara = () => {
    if (paraLines.length === 0) return
    const html = paraLines.map(inlineMarkdownToHtml).join('<br>')
    blocks.push(newBlock('paragraph', html))
    paraLines = []
  }

  for (const line of lines) {
    if (line.trim() === '') {
      flushPara()
      continue
    }
    let m
    if (DIVIDER_RE.test(line.trim())) {
      flushPara()
      blocks.push(newBlock('divider', ''))
    } else if ((m = HEADING_RE.exec(line))) {
      flushPara()
      blocks.push(newBlock(`heading${m[1].length}`, inlineMarkdownToHtml(m[2])))
    } else if ((m = QUOTE_RE.exec(line))) {
      flushPara()
      blocks.push(newBlock('quote', inlineMarkdownToHtml(m[1])))
    } else if ((m = BULLETED_RE.exec(line))) {
      flushPara()
      blocks.push(newBlock('bulleted', inlineMarkdownToHtml(m[1])))
    } else if ((m = NUMBERED_RE.exec(line))) {
      flushPara()
      blocks.push(newBlock('numbered', inlineMarkdownToHtml(m[1])))
    } else {
      paraLines.push(line)
    }
  }
  flushPara()

  if (blocks.length === 0) blocks.push(newBlock('paragraph', ''))
  return blocks
}

export function blocksToMarkdown(blocks) {
  const lines = []
  let numberCounter = 0
  for (const block of blocks) {
    if (block.type === 'numbered') numberCounter += 1
    else numberCounter = 0

    const flat = () => htmlToInlineMarkdown(block.html).replace(/\n/g, ' ')

    switch (block.type) {
      case 'heading1': lines.push(`# ${flat()}`); break
      case 'heading2': lines.push(`## ${flat()}`); break
      case 'heading3': lines.push(`### ${flat()}`); break
      case 'bulleted': lines.push(`- ${flat()}`); break
      case 'numbered': lines.push(`${numberCounter}. ${flat()}`); break
      case 'quote': lines.push(`> ${flat()}`); break
      case 'divider': lines.push('---'); break
      case 'paragraph':
      default: lines.push(htmlToInlineMarkdown(block.html)); break
    }
  }
  return lines.join('\n')
}

// Plain-text extraction for spaCy/LLM context (no markdown markers, no HTML).
export function blocksToPlainText(blocks) {
  return blocks
    .map((b) => (b.type === 'divider' ? '' : htmlToPlainText(b.html)))
    .filter((t) => t.trim() !== '')
    .join('\n')
}

export function stripMarkdown(markdown) {
  return blocksToPlainText(markdownToBlocks(markdown))
}
