// Thin wrappers around the /api/... contract in frontend/API_CONTRACT.md.
// All calls are relative (e.g. "/api/lessons") so they work both:
//  - in dev, via the Vite proxy (vite.config.js -> http://localhost:7861)
//  - in production, served same-origin by app_custom.py at /custom/

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.error || data.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

const get = (path) => request(path)
const post = (path, body) =>
  request(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body ?? {}) })
const put = (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body ?? {}) })
const patch = (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body ?? {}) })
const del = (path) => request(path, { method: 'DELETE' })

// Lessons
export const listLessons = () => get('/lessons')
export const getLesson = (id) => get(`/lessons/${id}`)
export const saveLesson = (text, annotations) => post('/lessons', { text, annotations })
export const updateLesson = (id, text, annotations) => put(`/lessons/${id}`, { text, annotations })
export const renameLesson = (id, title) => patch(`/lessons/${id}/title`, { title })
export const deleteLesson = (id) => del(`/lessons/${id}`)

// Resources
export const listResources = () => get('/resources')

// Annotation / word card
export const annotate = (text, colorsOn) => post('/annotate', { text, colors_on: colorsOn })
export const renderAnnotations = (annotations, colorsOn) => post('/render', { annotations, colors_on: colorsOn })
export const wordCard = (token, meanings) => post('/word-card', { ...token, meanings })

// Chat
export const sendChat = (message, history, lessonText) =>
  post('/chat', { message, history, lesson_text: lessonText })

// Exercises — coach (mixed set)
export const generateCoachSet = (lessonText) => post('/exercises/coach', { lesson_text: lessonText })
export const checkCoachExercise = (exercise, answer) => post('/exercises/coach/check', { exercise, answer })

// Exercises — dialogue
export const startDialogue = (lessonText) => post('/exercises/dialogue', { lesson_text: lessonText })
export const sendDialogueReply = (dialogue, replies, reply) =>
  post('/exercises/dialogue/reply', { dialogue, replies, reply })

// Exercises — visual
export const generateVisualExercise = (file) => {
  const form = new FormData()
  form.append('image', file)
  return post('/exercises/visual', form)
}
export const generateSampleVisualExercise = (lessonText) =>
  post('/exercises/visual/sample', { lesson_text: lessonText })

// Exercises — pronunciation
export const getPronunciationTarget = (lessonText) => post('/exercises/pronunciation/target', { lesson_text: lessonText })
export const checkPronunciation = (target, transcription) =>
  post('/exercises/pronunciation/check', { target, transcription })

// Summary
export const getSummary = () => get('/summary')
