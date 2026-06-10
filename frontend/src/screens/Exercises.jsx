import { useEffect, useRef, useState } from 'react'
import {
  generateTextExercise,
  checkTextExercise,
  startDialogue,
  sendDialogueReply,
  generateVisualExercise,
  getPronunciationTarget,
  checkPronunciation,
} from '../api'
import { speak, speakAll } from '../tts'

const SUBTABS = [
  { id: 'text', label: '📝 Text' },
  { id: 'dialogue', label: '💬 Dialogue' },
  { id: 'visual', label: '📷 Visual' },
  { id: 'pronunciation', label: '🎤 Pronunciation' },
]

// ── Text exercise ─────────────────────────────────────────────────────────

function TextExercise({ lessonText }) {
  const [exercise, setExercise] = useState(null)
  const [html, setHtml] = useState('')
  const [answer, setAnswer] = useState('')
  const [feedbackHtml, setFeedbackHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    setFeedbackHtml('')
    setAnswer('')
    try {
      const data = await generateTextExercise(lessonText)
      setExercise(data.exercise)
      setHtml(data.html)
    } catch (e) {
      setError(`Could not generate an exercise: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCheck = async () => {
    if (!exercise) return
    setChecking(true)
    setError('')
    try {
      const data = await checkTextExercise(exercise, answer)
      setFeedbackHtml(data.html)
    } catch (e) {
      setError(`Could not check your answer: ${e.message}`)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        Generates a fill-in-the-blank exercise from your current notebook lesson.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Generating…' : exercise ? '✨ New exercise' : '✨ Generate exercise'}
        </button>
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}

      {exercise && (
        <>
          <div className="fc-row" style={{ marginTop: 12 }}>
            <input
              className="fc-input"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Your answer…"
              onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            />
            <button className="fc-btn" onClick={handleCheck} disabled={checking || !answer.trim()}>
              {checking ? 'Checking…' : 'Check answer'}
            </button>
          </div>
          {feedbackHtml && <div dangerouslySetInnerHTML={{ __html: feedbackHtml }} />}
        </>
      )}
    </div>
  )
}

// ── Dialogue exercise ─────────────────────────────────────────────────────

// render_dialogue (exercises.py) shows every agent line up front — user
// turns are revealed progressively as replies come in, but the agent's
// side of the script is fixed from the start.
function agentLines(turns) {
  return (turns || []).filter((t) => t.speaker === 'agent').map((t) => t.text)
}

function DialogueExercise({ lessonText }) {
  const [dialogue, setDialogue] = useState(null)
  const [replies, setReplies] = useState([])
  const [transcriptHtml, setTranscriptHtml] = useState('')
  const [hint, setHint] = useState('')
  const [feedbackHtml, setFeedbackHtml] = useState('')
  const [reply, setReply] = useState('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const done = dialogue && hint.startsWith('🎉')

  const handleStart = async () => {
    setLoading(true)
    setError('')
    setFeedbackHtml('')
    setReply('')
    try {
      const data = await startDialogue(lessonText)
      setDialogue(data.dialogue)
      setReplies(data.replies)
      setTranscriptHtml(data.transcript_html)
      setHint(data.hint)
      speakAll(agentLines(data.dialogue.turns))
    } catch (e) {
      setError(`Could not start a dialogue: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!reply.trim() || !dialogue) return
    setSending(true)
    setError('')
    try {
      const data = await sendDialogueReply(dialogue, replies, reply)
      setReplies(data.replies)
      setTranscriptHtml(data.transcript_html)
      setHint(data.hint)
      setFeedbackHtml(data.feedback_html)
      setReply('')
    } catch (e) {
      setError(`Could not send your reply: ${e.message}`)
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        The coach starts a short scene from your current lesson and plays its lines aloud — you reply in French.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleStart} disabled={loading}>
          {loading ? 'Starting…' : dialogue ? '🔄 New dialogue' : '🎬 Start dialogue'}
        </button>
        {dialogue && (
          <button className="fc-btn" onClick={() => speakAll(agentLines(dialogue.turns))}>
            🔊 Replay
          </button>
        )}
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {transcriptHtml && <div dangerouslySetInnerHTML={{ __html: transcriptHtml }} />}

      {dialogue && !done && (
        <div className="fc-row" style={{ marginTop: 12 }}>
          <input
            className="fc-input"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            placeholder="Type your reply in French…"
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button className="fc-btn" onClick={handleSend} disabled={sending || !reply.trim()}>
            {sending ? 'Sending…' : 'Send reply'}
          </button>
        </div>
      )}

      {hint && <div className="fc-status">{hint}</div>}

      {feedbackHtml && <div dangerouslySetInnerHTML={{ __html: feedbackHtml }} />}
    </div>
  )
}

// ── Visual exercise ───────────────────────────────────────────────────────

function VisualExercise() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [html, setHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
    setHtml('')
    setError('')
  }

  const handleGenerate = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const data = await generateVisualExercise(file)
      setHtml(data.html)
    } catch (e) {
      setError(`Could not generate exercises from this photo: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        Snap a photo of a menu, sign, or recipe — the coach reads it and builds exercises from what's in the picture.
      </p>
      <div className="fc-row">
        <input className="fc-input" type="file" accept="image/*" onChange={handleFileChange} />
        <button className="fc-btn fc-btn-primary" onClick={handleGenerate} disabled={!file || loading}>
          {loading ? 'Reading photo…' : '✨ Generate exercises'}
        </button>
      </div>

      {previewUrl && (
        <div className="fc-row">
          <img className="fc-visual-preview" src={previewUrl} alt="Selected" />
        </div>
      )}

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  )
}

// ── Pronunciation exercise ────────────────────────────────────────────────

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function PronunciationExercise({ lessonText }) {
  const [target, setTarget] = useState(null)
  const [html, setHtml] = useState('')
  const [transcription, setTranscription] = useState('')
  const [feedbackHtml, setFeedbackHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const recognitionRef = useRef(null)

  const speechSupported = !!getSpeechRecognition()

  const handleGetPhrase = async () => {
    setLoading(true)
    setError('')
    setFeedbackHtml('')
    setTranscription('')
    try {
      const data = await getPronunciationTarget(lessonText)
      setTarget(data.target)
      setHtml(data.html)
      speak(data.target.phrase)
    } catch (e) {
      setError(`Could not get a phrase: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleMic = () => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'fr-FR'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognitionRef.current = recognition

    recognition.onresult = (e) => {
      setTranscription(e.results[0][0].transcript)
    }
    recognition.onerror = () => {
      setError('Could not hear you — check microphone permissions and try again.')
      setListening(false)
    }
    recognition.onend = () => setListening(false)

    setError('')
    setListening(true)
    recognition.start()
  }

  const handleCheck = async () => {
    if (!target || !transcription.trim()) return
    setChecking(true)
    setError('')
    try {
      const data = await checkPronunciation(target, transcription)
      setFeedbackHtml(data.html)
    } catch (e) {
      setError(`Could not check pronunciation: ${e.message}`)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <p className="fc-muted">
        The coach speaks a phrase from your lesson aloud — repeat it, and get gentle feedback on your pronunciation.
      </p>
      <div className="fc-row">
        <button className="fc-btn fc-btn-primary" onClick={handleGetPhrase} disabled={loading}>
          {loading ? 'Thinking…' : target ? '🔄 New phrase' : '🎯 Get a phrase'}
        </button>
        {target && (
          <button className="fc-btn" onClick={() => speak(target.phrase)}>🔊 Hear it again</button>
        )}
      </div>

      {error && <div className="fc-status fc-error">⚠ {error}</div>}

      {html && <div dangerouslySetInnerHTML={{ __html: html }} />}

      {target && (
        <>
          <div className="fc-row" style={{ marginTop: 12 }}>
            <input
              className="fc-input"
              value={transcription}
              onChange={(e) => setTranscription(e.target.value)}
              placeholder="What you said (or type it yourself)…"
              onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            />
            {speechSupported && (
              <button className={`fc-btn fc-mic-btn${listening ? ' fc-mic-listening' : ''}`} onClick={handleMic}>
                {listening ? '🎙️ Listening…' : '🎤 Use microphone'}
              </button>
            )}
            <button className="fc-btn" onClick={handleCheck} disabled={checking || !transcription.trim()}>
              {checking ? 'Checking…' : 'Check pronunciation'}
            </button>
          </div>
          {!speechSupported && (
            <p className="fc-muted">
              Your browser doesn't support speech input — type what you said instead.
            </p>
          )}
          {feedbackHtml && <div dangerouslySetInnerHTML={{ __html: feedbackHtml }} />}
        </>
      )}
    </div>
  )
}

// ── Screen ─────────────────────────────────────────────────────────────────

export default function Exercises({ lessonText }) {
  const [view, setView] = useState('text')

  return (
    <div>
      <nav className="fc-subtabs">
        {SUBTABS.map((t) => (
          <button
            key={t.id}
            className={`fc-subtab${view === t.id ? ' fc-subtab-active' : ''}`}
            onClick={() => setView(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {view === 'text' && <TextExercise lessonText={lessonText} />}
      {view === 'dialogue' && <DialogueExercise lessonText={lessonText} />}
      {view === 'visual' && <VisualExercise />}
      {view === 'pronunciation' && <PronunciationExercise lessonText={lessonText} />}
    </div>
  )
}
