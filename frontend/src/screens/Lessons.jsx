import { useEffect, useMemo, useState } from 'react'
import { listLessons, listResources } from '../api'

function formatDateHeader(dateStr) {
  if (!dateStr) return 'Undated'
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

function groupByDate(lessons) {
  const groups = {}
  for (const l of lessons) {
    const key = l.date || 'Undated'
    ;(groups[key] ||= []).push(l)
  }
  return Object.entries(groups).sort((a, b) => (a[0] < b[0] ? 1 : -1))
}

function groupByCategory(lessons) {
  const groups = {}
  for (const l of lessons) {
    const key = l.category || 'General'
    ;(groups[key] ||= []).push(l)
  }
  return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))
}

function LessonCard({ lesson, onOpen }) {
  return (
    <button className="fc-lesson-card" onClick={() => onOpen(lesson.id)}>
      <div className="fc-lesson-card-title">{lesson.title || 'Untitled'}</div>
      <div className="fc-lesson-card-meta">
        <span>{lesson.date}</span>
        {lesson.category && <span className="fc-pill">{lesson.category}</span>}
      </div>
      {lesson.preview && <div className="fc-lesson-card-preview">{lesson.preview}</div>}
    </button>
  )
}

function LessonGroups({ groups, onOpen, openFirst }) {
  return groups.map(([label, items], i) => (
    <details key={label} open={openFirst ? i === 0 : undefined} className="fc-group">
      <summary className="fc-group-summary">
        {label} <span className="fc-muted">({items.length})</span>
      </summary>
      <div className="fc-lesson-grid">
        {items.map((lesson) => (
          <LessonCard key={lesson.id} lesson={lesson} onOpen={onOpen} />
        ))}
      </div>
    </details>
  ))
}

function domainOf(url) {
  try {
    const host = new URL(url).hostname
    return host.startsWith('www.') ? host.slice(4) : host
  } catch {
    return url
  }
}

function Resources() {
  const [resources, setResources] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listResources()
      .then((data) => setResources(data.resources))
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="fc-card fc-error">Could not load resources: {error}</div>
  if (resources === null) return <div className="fc-empty"><span className="fc-spinner" />Loading resources…</div>
  if (resources.length === 0) {
    return (
      <div className="fc-empty">
        📚 No resources yet. Save a page that's mostly links or book recommendations
        (e.g. "Online Resources", "Books to Read") and it'll show up here, beautifully
        laid out and out of your lecture notes.
      </div>
    )
  }

  return (
    <div className="fc-resources">
      {resources.map((page) => (
        <div className="fc-card fc-resource-section" key={page.id}>
          <h3 className="fc-resource-title">📚 {page.title}</h3>
          {page.links.length > 0 && (
            <div className="fc-link-grid">
              {page.links.map((link, i) => (
                <a className="fc-link-card" href={link.url} target="_blank" rel="noopener noreferrer" key={i}>
                  <img
                    className="fc-link-favicon"
                    alt=""
                    src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(link.domain || domainOf(link.url))}&sz=32`}
                  />
                  <span className="fc-link-text">
                    <span className="fc-link-label">{link.label}</span>
                    <span className="fc-link-domain">{link.domain || domainOf(link.url)}</span>
                  </span>
                </a>
              ))}
            </div>
          )}
          {page.books.length > 0 && (
            <div className="fc-book-list">
              {page.books.map((book, i) => {
                const meta = [book.author, book.note].filter(Boolean).join(' · ')
                return (
                  <div className="fc-book-row" key={i}>
                    <span className="fc-book-icon">📖</span>
                    <span>
                      <span className="fc-book-title">{book.title}</span>
                      {meta && <span className="fc-book-meta">{meta}</span>}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Lessons({ onOpenLesson }) {
  const [lessons, setLessons] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [view, setView] = useState('date')

  useEffect(() => {
    listLessons()
      .then((data) => setLessons(data.lessons))
      .catch((e) => setError(e.message))
  }, [])

  const filtered = useMemo(() => {
    if (!lessons) return []
    const q = query.trim().toLowerCase()
    if (!q) return lessons
    return lessons.filter((l) => (l.title || '').toLowerCase().includes(q))
  }, [lessons, query])

  if (error) return <div className="fc-card fc-error">Could not load lessons: {error}</div>
  if (lessons === null) return <div className="fc-empty"><span className="fc-spinner" />Loading lessons…</div>

  return (
    <div>
      <div className="fc-row">
        <input
          className="fc-input"
          placeholder="🔍 Search lessons…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <nav className="fc-subtabs">
        <button className={`fc-subtab${view === 'date' ? ' fc-subtab-active' : ''}`} onClick={() => setView('date')}>
          📅 By Date
        </button>
        <button className={`fc-subtab${view === 'topic' ? ' fc-subtab-active' : ''}`} onClick={() => setView('topic')}>
          🏷️ By Topic
        </button>
        <button className={`fc-subtab${view === 'resources' ? ' fc-subtab-active' : ''}`} onClick={() => setView('resources')}>
          📚 Resources
        </button>
      </nav>

      {view === 'resources' && <Resources />}

      {view !== 'resources' && lessons.length === 0 && (
        <div className="fc-empty">
          📓 No lessons saved yet. Open the Notebook tab, paste some French text, and save it.
        </div>
      )}

      {view !== 'resources' && lessons.length > 0 && filtered.length === 0 && (
        <div className="fc-empty">No lessons match "{query}".</div>
      )}

      {view === 'date' && filtered.length > 0 && (
        <LessonGroups groups={groupByDate(filtered).map(([d, items]) => [formatDateHeader(d), items])} onOpen={onOpenLesson} openFirst />
      )}

      {view === 'topic' && filtered.length > 0 && (
        <LessonGroups groups={groupByCategory(filtered)} onOpen={onOpenLesson} />
      )}
    </div>
  )
}
