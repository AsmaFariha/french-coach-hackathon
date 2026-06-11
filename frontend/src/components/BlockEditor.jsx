import { useEffect, useRef, useState } from 'react'
import { markdownToBlocks, blocksToMarkdown, newBlock, BLOCK_TAGS, BLOCK_TYPES, PLACEHOLDERS } from '../blocks'

// ── Selection / caret helpers (operate on a single block's DOM node) ───────

function isCaretAtStart(el) {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount) return false
  const range = sel.getRangeAt(0)
  if (!range.collapsed) return false
  const pre = range.cloneRange()
  pre.selectNodeContents(el)
  pre.setEnd(range.startContainer, range.startOffset)
  return pre.toString().length === 0
}

function isCaretAtEnd(el) {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount) return false
  const range = sel.getRangeAt(0)
  if (!range.collapsed) return false
  const post = range.cloneRange()
  post.selectNodeContents(el)
  post.setStart(range.endContainer, range.endOffset)
  return post.toString().length === 0
}

function placeCaretAtStart(el) {
  const range = document.createRange()
  range.selectNodeContents(el)
  range.collapse(true)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
}

function placeCaretAtEnd(el) {
  const range = document.createRange()
  range.selectNodeContents(el)
  range.collapse(false)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
}

function setCaretOffset(el, offset) {
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
  let remaining = offset
  let target = el
  let targetOffset = 0
  let node = walker.nextNode()
  while (node) {
    const len = node.nodeValue.length
    if (remaining <= len) {
      target = node
      targetOffset = remaining
      break
    }
    remaining -= len
    target = node
    targetOffset = len
    node = walker.nextNode()
  }
  const range = document.createRange()
  range.setStart(target, targetOffset)
  range.collapse(true)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
}

// Split a block's content at the caret into "before"/"after" HTML fragments.
function splitAtCaret(el) {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount) return { before: el.innerHTML, after: '' }
  const range = sel.getRangeAt(0)

  const beforeRange = document.createRange()
  beforeRange.selectNodeContents(el)
  beforeRange.setEnd(range.startContainer, range.startOffset)

  const afterRange = document.createRange()
  afterRange.selectNodeContents(el)
  afterRange.setStart(range.endContainer, range.endOffset)

  const beforeDiv = document.createElement('div')
  beforeDiv.appendChild(beforeRange.cloneContents())
  const afterDiv = document.createElement('div')
  afterDiv.appendChild(afterRange.cloneContents())

  return { before: beforeDiv.innerHTML, after: afterDiv.innerHTML }
}

// Remove the first `n` characters of text content (the markdown marker that
// triggered an auto-format conversion), keeping any inline formatting intact.
function stripLeadingMarker(el, n) {
  let remaining = n
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
  let node = walker.nextNode()
  while (node && remaining > 0) {
    const len = node.nodeValue.length
    if (len <= remaining) {
      node.nodeValue = ''
      remaining -= len
    } else {
      node.nodeValue = node.nodeValue.slice(remaining)
      remaining = 0
    }
    node = walker.nextNode()
  }
}

const SHORTCUT_RE = /^(#{1,3}|[-*]|\d+\.|>)\s(.*)$/

function shortcutType(marker) {
  if (/^#{1,3}$/.test(marker)) return `heading${marker.length}`
  if (marker === '-' || marker === '*') return 'bulleted'
  if (/^\d+\.$/.test(marker)) return 'numbered'
  if (marker === '>') return 'quote'
  return null
}

// ── Component ────────────────────────────────────────────────────────────

export default function BlockEditor({ value, onChange }) {
  const [blocks, setBlocks] = useState(() => markdownToBlocks(value))
  const [slashMenu, setSlashMenu] = useState(null) // {blockId, top, left}
  const [slashIndex, setSlashIndex] = useState(0)
  const [toolbar, setToolbar] = useState(null) // {top, left}
  const [pendingFocus, setPendingFocus] = useState(null) // {id, position, offset}
  const blockRefs = useRef({})
  const containerRef = useRef(null)

  // Debounced serialize-up to the parent (raw_text / `text` state).
  useEffect(() => {
    const t = setTimeout(() => onChange(blocksToMarkdown(blocks)), 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blocks])

  // Restore focus/caret after structural edits (split, merge, convert…).
  useEffect(() => {
    if (!pendingFocus) return
    const el = blockRefs.current[pendingFocus.id]
    if (el) {
      el.focus()
      if (pendingFocus.position === 'end') placeCaretAtEnd(el)
      else if (pendingFocus.position === 'offset') setCaretOffset(el, pendingFocus.offset || 0)
      else placeCaretAtStart(el)
    }
    setPendingFocus(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blocks, pendingFocus])

  // Floating selection toolbar (Bold/Italic/Strikethrough).
  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection()
      const container = containerRef.current
      if (!sel || sel.isCollapsed || sel.rangeCount === 0 || !container) {
        setToolbar(null)
        return
      }
      const range = sel.getRangeAt(0)
      if (!container.contains(range.commonAncestorContainer)) {
        setToolbar(null)
        return
      }
      const rect = range.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) {
        setToolbar(null)
        return
      }
      const containerRect = container.getBoundingClientRect()
      setToolbar({
        top: rect.top - containerRect.top - 42,
        left: rect.left - containerRect.left + rect.width / 2,
      })
    }
    document.addEventListener('selectionchange', handler)
    return () => document.removeEventListener('selectionchange', handler)
  }, [])

  function focusBlock(id, position) {
    const el = blockRefs.current[id]
    if (!el) return
    el.focus()
    if (position === 'end') placeCaretAtEnd(el)
    else placeCaretAtStart(el)
  }

  function applyFormat(cmd) {
    document.execCommand(cmd)
    const sel = window.getSelection()
    const node = sel && sel.anchorNode
    const anchorEl = node && (node.nodeType === 1 ? node : node.parentElement)
    const blockEl = anchorEl && anchorEl.closest('[data-block-id]')
    if (blockEl) {
      const id = blockEl.dataset.blockId
      const html = blockEl.innerHTML
      setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, html } : b)))
    }
  }

  function handleInput(id, el) {
    let html = el.innerHTML
    const text = el.textContent || ''
    if (text === '') html = ''

    const block = blocks.find((b) => b.id === id)
    if (!block) return

    if (block.type === 'paragraph') {
      if (text === '/') {
        const rect = el.getBoundingClientRect()
        const containerRect = containerRef.current.getBoundingClientRect()
        setSlashMenu({ blockId: id, top: rect.bottom - containerRect.top + 4, left: rect.left - containerRect.left })
        setSlashIndex(0)
      } else if (slashMenu && slashMenu.blockId === id) {
        setSlashMenu(null)
      }

      if (text === '---') {
        const next = newBlock('paragraph', '')
        setBlocks((prev) => {
          const idx = prev.findIndex((b) => b.id === id)
          const copy = [...prev]
          copy[idx] = { ...copy[idx], type: 'divider', html: '' }
          copy.splice(idx + 1, 0, next)
          return copy
        })
        setPendingFocus({ id: next.id, position: 'start' })
        return
      }

      const m = SHORTCUT_RE.exec(text)
      const newType = m && shortcutType(m[1])
      if (newType) {
        stripLeadingMarker(el, m[1].length + 1)
        const newHtml = el.innerHTML
        setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, type: newType, html: newHtml } : b)))
        setPendingFocus({ id, position: 'start' })
        return
      }
    } else if (slashMenu && slashMenu.blockId === id) {
      setSlashMenu(null)
    }

    setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, html } : b)))
  }

  function handleEnter(id, el, block) {
    if ((block.type === 'bulleted' || block.type === 'numbered') && el.textContent.trim() === '') {
      el.innerHTML = ''
      setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, type: 'paragraph', html: '' } : b)))
      setPendingFocus({ id, position: 'start' })
      return
    }

    const { before, after } = splitAtCaret(el)
    const newType = block.type === 'bulleted' || block.type === 'numbered' ? block.type : 'paragraph'
    const next = newBlock(newType, after)

    el.innerHTML = before
    setBlocks((prev) => {
      const idx = prev.findIndex((b) => b.id === id)
      const copy = [...prev]
      copy[idx] = { ...copy[idx], html: before }
      copy.splice(idx + 1, 0, next)
      return copy
    })
    setPendingFocus({ id: next.id, position: 'start' })
  }

  function mergeWithPrevious(idx) {
    const prevBlock = blocks[idx - 1]
    const curBlock = blocks[idx]

    if (prevBlock.type === 'divider') {
      setBlocks((prev) => prev.filter((b) => b.id !== prevBlock.id))
      setPendingFocus({ id: curBlock.id, position: 'start' })
      return
    }

    const prevEl = blockRefs.current[prevBlock.id]
    const caretOffset = (prevEl ? prevEl.textContent : '').length
    const mergedHtml = (prevEl ? prevEl.innerHTML : prevBlock.html) + curBlock.html

    if (prevEl) prevEl.innerHTML = mergedHtml
    setBlocks((prev) => {
      const copy = prev.filter((b) => b.id !== curBlock.id)
      const pIdx = copy.findIndex((b) => b.id === prevBlock.id)
      copy[pIdx] = { ...copy[pIdx], html: mergedHtml }
      return copy
    })
    setPendingFocus({ id: prevBlock.id, position: 'offset', offset: caretOffset })
  }

  function applySlashChoice(id, type) {
    setSlashMenu(null)
    if (type === 'divider') {
      const next = newBlock('paragraph', '')
      setBlocks((prev) => {
        const idx = prev.findIndex((b) => b.id === id)
        const copy = [...prev]
        copy[idx] = { ...copy[idx], type: 'divider', html: '' }
        copy.splice(idx + 1, 0, next)
        return copy
      })
      setPendingFocus({ id: next.id, position: 'start' })
    } else {
      const el = blockRefs.current[id]
      if (el) el.innerHTML = ''
      setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, type, html: '' } : b)))
      setPendingFocus({ id, position: 'start' })
    }
  }

  function handleKeyDown(e, id) {
    const el = blockRefs.current[id]
    const block = blocks.find((b) => b.id === id)
    if (!el || !block) return

    if (slashMenu && slashMenu.blockId === id) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSlashIndex((i) => (i + 1) % BLOCK_TYPES.length); return }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSlashIndex((i) => (i - 1 + BLOCK_TYPES.length) % BLOCK_TYPES.length); return }
      if (e.key === 'Enter') { e.preventDefault(); applySlashChoice(id, BLOCK_TYPES[slashIndex].type); return }
      if (e.key === 'Escape') { e.preventDefault(); setSlashMenu(null); return }
    }

    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault()
      document.execCommand('insertHTML', false, '<br>')
      return
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      handleEnter(id, el, block)
      return
    }

    if (e.key === 'Backspace' && isCaretAtStart(el)) {
      if (block.type !== 'paragraph') {
        e.preventDefault()
        setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, type: 'paragraph' } : b)))
        return
      }
      const idx = blocks.findIndex((b) => b.id === id)
      if (idx > 0) {
        e.preventDefault()
        mergeWithPrevious(idx)
      }
      return
    }

    if (e.key === 'ArrowUp' && isCaretAtStart(el)) {
      const idx = blocks.findIndex((b) => b.id === id)
      if (idx > 0) {
        e.preventDefault()
        focusBlock(blocks[idx - 1].id, 'end')
      }
      return
    }

    if (e.key === 'ArrowDown' && isCaretAtEnd(el)) {
      const idx = blocks.findIndex((b) => b.id === id)
      if (idx < blocks.length - 1) {
        e.preventDefault()
        focusBlock(blocks[idx + 1].id, 'start')
      }
    }
  }

  function renderBlock(block) {
    if (block.type === 'divider') {
      return <hr key={block.id} className="fc-block fc-block-divider" contentEditable={false} />
    }
    const Tag = BLOCK_TAGS[block.type]
    return (
      <Tag
        key={block.id}
        ref={(el) => {
          if (el) {
            blockRefs.current[block.id] = el
            if (el.innerHTML === '' && block.html) el.innerHTML = block.html
          } else {
            delete blockRefs.current[block.id]
          }
        }}
        className={`fc-block fc-block-${block.type}`}
        contentEditable
        suppressContentEditableWarning
        data-block-id={block.id}
        data-placeholder={!block.html ? PLACEHOLDERS[block.type] || PLACEHOLDERS.paragraph : ''}
        onInput={(e) => handleInput(block.id, e.currentTarget)}
        onKeyDown={(e) => handleKeyDown(e, block.id)}
      />
    )
  }

  function renderBlocks() {
    const out = []
    let i = 0
    while (i < blocks.length) {
      const block = blocks[i]
      if (block.type === 'bulleted' || block.type === 'numbered') {
        const groupType = block.type
        const group = []
        while (i < blocks.length && blocks[i].type === groupType) {
          group.push(blocks[i])
          i += 1
        }
        const ListTag = groupType === 'bulleted' ? 'ul' : 'ol'
        out.push(
          <ListTag className="fc-block-list" key={group[0].id}>
            {group.map((b) => renderBlock(b))}
          </ListTag>
        )
      } else {
        out.push(renderBlock(block))
        i += 1
      }
    }
    return out
  }

  return (
    <div className="fc-block-editor" ref={containerRef}>
      {renderBlocks()}
      {slashMenu && (
        <div className="fc-slash-menu" style={{ top: slashMenu.top, left: slashMenu.left }}>
          {BLOCK_TYPES.map((bt, i) => (
            <div
              key={bt.type}
              className={`fc-slash-menu-item${i === slashIndex ? ' fc-slash-menu-item-active' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); applySlashChoice(slashMenu.blockId, bt.type) }}
              onMouseEnter={() => setSlashIndex(i)}
            >
              <span className="fc-slash-menu-icon">{bt.icon}</span>
              {bt.label}
            </div>
          ))}
        </div>
      )}
      {toolbar && (
        <div className="fc-floating-toolbar" style={{ top: toolbar.top, left: toolbar.left }}>
          <button className="fc-floating-toolbar-btn" onMouseDown={(e) => { e.preventDefault(); applyFormat('bold') }}><b>B</b></button>
          <button className="fc-floating-toolbar-btn" onMouseDown={(e) => { e.preventDefault(); applyFormat('italic') }}><i>I</i></button>
          <button className="fc-floating-toolbar-btn" onMouseDown={(e) => { e.preventDefault(); applyFormat('strikeThrough') }}><s>S</s></button>
        </div>
      )}
    </div>
  )
}
