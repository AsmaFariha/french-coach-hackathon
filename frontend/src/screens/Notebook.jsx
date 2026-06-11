import { useEffect, useState } from 'react'
import {
  annotate,
  renderAnnotations,
  wordCard,
  saveLesson,
  updateLesson,
  renameLesson,
  deleteLesson,
  getLesson,
} from '../api'
import { speak } from '../tts'
import WordCard from '../components/WordCard'
import BlockEditor from '../components/BlockEditor'
import { stripMarkdown } from '../blocks'

const SAMPLE_TEXT =
  'Le petit chat noir dort sur la grande table. ' +
  "La femme mange une pomme délicieuse avec son ami. " +
  'Le livre est ouvert sur le bureau.'

export default function Notebook({ openLessonId, onLessonOpened, onTextChange }) {
  const [lessonId, setLessonId] = useState(null)
  const [title, setTitle] = useState('')
  const [text, setText] = useState(SAMPLE_TEXT)
  const [ann, setAnn] = useState({ tokens: [], meanings: {} })
  const [html, setHtml] = useState('')
  const [colorsOn, setColorsOn] = useState(true)
  const [status, setStatus] = useState('')
  const [wordCardData, setWordCardData] = useState(null)
  const [wordCardLoading, setWordCardLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Show a colored sample on first load, like the old Blocks app did.
  useEffect(() => {
    annotate(SAMPLE_TEXT, true)
      .then((data) => {
        setAnn({ tokens: data.tokens, meanings: data.meanings })
        setHtml(data.html)
      })
      .catch(() => {})
  }, [])

  // Let App.jsx know the current lesson text, so other screens (Exercises,
  // Chat) can use it as context without lifting the whole editor state.
  // Markdown markers are stripped so the LLM/spaCy see clean prose.
  useEffect(() => {
    onTextChange?.(stripMarkdown(text))
  }, [text, onTextChange])

  // Load a lesson opened from the Lessons browser.
  useEffect(() => {
    if (!openLessonId) return
    let cancelled = false
    getLesson(openLessonId)
      .then((page) => {
        if (cancelled) return
        const a = page.annotations && page.annotations.tokens ? page.annotations : { tokens: [], meanings: {} }
        setLessonId(page.id)
        setTitle(page.title || '')
        setText(page.raw_text || '')
        setAnn(a)
        setStatus('')
        setWordCardData(null)
        setConfirmDelete(false)
        return renderAnnotations(a, colorsOn)
      })
      .then((r) => { if (r && !cancelled) setHtml(r.html) })
      .catch((e) => setStatus(`⚠ Could not load page: ${e.message}`))
      .finally(() => onLessonOpened?.())
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openLessonId])

  const handleAnnotate = async () => {
    try {
      const data = await annotate(stripMarkdown(text), colorsOn)
      setAnn({ tokens: data.tokens, meanings: data.meanings })
      setHtml(data.html)
      setWordCardData(null)
    } catch (e) {
      setStatus(`⚠ Could not annotate: ${e.message}`)
    }
  }

  const handleToggleColors = async (checked) => {
    setColorsOn(checked)
    try {
      const r = await renderAnnotations(ann, checked)
      setHtml(r.html)
    } catch {
      /* ignore */
    }
  }

  const handleContainerClick = async (e) => {
    const tok = e.target.closest('[data-token]')
    if (!tok) return
    const tokenInfo = {
      text: tok.dataset.text,
      gender: tok.dataset.gender || '',
      pos: tok.dataset.pos || '',
      lemma: tok.dataset.lemma || tok.dataset.text,
    }
    speak(tokenInfo.text)
    setWordCardLoading(true)
    setWordCardData({ ...tokenInfo, meaning: '', grammar: '' })
    try {
      const data = await wordCard(tokenInfo, ann.meanings)
      setAnn((prev) => ({ ...prev, meanings: data.meanings }))
      setWordCardData(data)
    } catch (err) {
      setWordCardData({ ...tokenInfo, meaning: `⚠ ${err.message}`, grammar: '' })
    } finally {
      setWordCardLoading(false)
    }
  }

  const handleSave = async () => {
    if (!text.trim()) { setStatus('Nothing to save — type or paste some French text first.'); return }
    try {
      const { id, title: newTitle } = await saveLesson(text, ann)
      setLessonId(id)
      setTitle(newTitle)
      setStatus(`✅ Saved as ${newTitle}`)
    } catch (e) {
      setStatus(`⚠ Could not save: ${e.message}`)
    }
  }

  const handleUpdate = async () => {
    if (!lessonId) return
    if (!text.trim()) { setStatus('Nothing to save.'); return }
    try {
      const { title: t } = await updateLesson(lessonId, text, ann)
      setTitle(t)
      setStatus(`✅ Updated ${t}`)
    } catch (e) {
      setStatus(`⚠ Could not update: ${e.message}`)
    }
  }

  const handleRename = async () => {
    if (!lessonId) return
    if (!title.trim()) { setStatus("⚠ Title can't be empty."); return }
    try {
      const { title: t } = await renameLesson(lessonId, title)
      setTitle(t)
      setStatus(`✅ Renamed to ${t}`)
    } catch (e) {
      setStatus(`⚠ Could not rename: ${e.message}`)
    }
  }

  const handleDelete = async () => {
    if (!lessonId) return
    try {
      await deleteLesson(lessonId)
      setLessonId(null)
      setTitle('')
      setText('')
      setAnn({ tokens: [], meanings: {} })
      setHtml('')
      setWordCardData(null)
      setConfirmDelete(false)
      setStatus('🗑️ Page deleted.')
    } catch (e) {
      setStatus(`⚠ Could not delete: ${e.message}`)
    }
  }

  return (
    <div className="fc-notebook">
      <div className="fc-notebook-main">
        <div className="fc-row">
          <input
            className="fc-input fc-title-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="A title is generated automatically when you save…"
          />
          {lessonId && (
            <button className="fc-btn" onClick={handleRename}>✏️ Rename</button>
          )}
        </div>

        <BlockEditor key={lessonId ?? 'new'} value={text} onChange={setText} />

        <div className="fc-row">
          <button className="fc-btn fc-btn-primary" onClick={handleAnnotate}>Annotate</button>
          <button className="fc-btn" onClick={handleSave}>💾 Save as new page</button>
          <label className="fc-checkbox">
            <input type="checkbox" checked={colorsOn} onChange={(e) => handleToggleColors(e.target.checked)} />
            Gender colors
          </label>
        </div>

        {lessonId && !confirmDelete && (
          <div className="fc-row">
            <button className="fc-btn fc-btn-secondary" onClick={handleUpdate}>✏️ Update page</button>
            <button className="fc-btn fc-btn-danger-outline" onClick={() => setConfirmDelete(true)}>🗑️ Delete page</button>
          </div>
        )}

        {confirmDelete && (
          <div className="fc-confirm-row">
            <span>⚠️ Delete this page? All exercises saved to it will also be removed.</span>
            <button className="fc-btn fc-btn-danger" onClick={handleDelete}>Yes, delete</button>
            <button className="fc-btn" onClick={() => setConfirmDelete(false)}>Cancel</button>
          </div>
        )}

        {status && <div className="fc-status">{status}</div>}

        <div className="fc-annotated" dangerouslySetInnerHTML={{ __html: html }} onClick={handleContainerClick} />
      </div>

      <div className="fc-notebook-side">
        <h3>🔤 Word card</h3>
        <div className="fc-card">
          <WordCard data={wordCardData} loading={wordCardLoading} />
        </div>
      </div>
    </div>
  )
}
