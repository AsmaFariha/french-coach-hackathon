import { useEffect, useState } from 'react'
import { listLessons } from '../api'

export default function Lessons({ onOpenLesson }) {
  const [lessons, setLessons] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listLessons()
      .then((data) => setLessons(data.lessons))
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="fc-card fc-error">Could not load lessons: {error}</div>
  if (lessons === null) return <div className="fc-card fc-muted">Loading lessons…</div>
  if (lessons.length === 0) {
    return (
      <div className="fc-card fc-muted">
        No lessons saved yet. Open the Notebook tab, paste some French text, and save it.
      </div>
    )
  }

  return (
    <div className="fc-lesson-grid">
      {lessons.map((lesson) => (
        <button key={lesson.id} className="fc-lesson-card" onClick={() => onOpenLesson?.(lesson.id)}>
          <div className="fc-lesson-card-title">{lesson.title || 'Untitled'}</div>
          <div className="fc-lesson-card-meta">
            <span>{lesson.date}</span>
            {lesson.category && <span className="fc-pill">{lesson.category}</span>}
          </div>
          {lesson.preview && <div className="fc-lesson-card-preview">{lesson.preview}</div>}
        </button>
      ))}
    </div>
  )
}
