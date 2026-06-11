import { useState } from 'react'
import './App.css'
import Notebook from './screens/Notebook'
import Lessons from './screens/Lessons'
import Exercises from './screens/Exercises'
import Chat from './screens/Chat'
import Summary from './screens/Summary'
import Tools from './screens/Tools'

const TABS = [
  { id: 'notebook', label: '📓 Notebook' },
  { id: 'lessons', label: '📚 Lessons' },
  { id: 'exercises', label: '🏋️ Exercises' },
  { id: 'chat', label: '💬 Chat Coach' },
  { id: 'summary', label: '⭐ Summary' },
  { id: 'tools', label: '🔤 Tools' },
]

export default function App() {
  const [tab, setTab] = useState('notebook')
  const [openLessonId, setOpenLessonId] = useState(null)
  const [lessonText, setLessonText] = useState('')

  const openLesson = (id) => {
    setOpenLessonId(id)
    setTab('notebook')
  }

  let screen
  switch (tab) {
    case 'lessons':
      screen = <Lessons onOpenLesson={openLesson} />
      break
    case 'exercises':
      screen = <Exercises lessonText={lessonText} />
      break
    case 'chat':
      screen = <Chat lessonText={lessonText} />
      break
    case 'summary':
      screen = <Summary />
      break
    case 'tools':
      screen = <Tools lessonText={lessonText} />
      break
    default:
      screen = (
        <Notebook
          openLessonId={openLessonId}
          onLessonOpened={() => setOpenLessonId(null)}
          onTextChange={setLessonText}
        />
      )
  }

  return (
    <div className="fc-app">
      <header className="fc-header">
        <div className="fc-header-text">
          <h1>🇫🇷 French Coach</h1>
          <p>Your daily French notebook — notes, gender at a glance, and practice from today's lesson.</p>
        </div>
      </header>
      <div className="fc-tricolor-bar" />

      <nav className="fc-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`fc-tab${tab === t.id ? ' fc-tab-active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="fc-main">{screen}</main>
    </div>
  )
}
