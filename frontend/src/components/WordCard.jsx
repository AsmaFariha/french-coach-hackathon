import { speak } from '../tts'

const POS_LABELS = {
  NOUN: 'Noun', VERB: 'Verb', ADJ: 'Adjective', ADV: 'Adverb', DET: 'Determiner',
  PRON: 'Pronoun', ADP: 'Preposition', CCONJ: 'Conjunction', PART: 'Particle', PUNCT: 'Punctuation',
}
const GENDER_LABELS = { Masc: 'Masculine ♂', Fem: 'Feminine ♀' }
const GENDER_COLORS = { Masc: '#4A90D9', Fem: '#D96B8A' }

export default function WordCard({ data, loading }) {
  if (!data) {
    return <div className="fc-muted">👆 Click any word to see its gender, lemma, and part of speech.</div>
  }
  const color = GENDER_COLORS[data.gender] || '#888'
  const genderLabel = GENDER_LABELS[data.gender] || '—'
  const posLabel = POS_LABELS[data.pos] || data.pos

  return (
    <div className="fc-word-card">
      <div className="fc-word-card-text" style={{ color }}>{data.text}</div>
      <table className="fc-word-card-table">
        <tbody>
          <tr><td>Lemma</td><td><strong>{data.lemma}</strong></td></tr>
          <tr><td>Gender</td><td style={{ color, fontWeight: 600 }}>{genderLabel}</td></tr>
          <tr><td>Part of speech</td><td>{posLabel}</td></tr>
          <tr>
            <td>Meaning</td>
            <td>{loading ? <span className="fc-muted">Loading…</span> : (data.meaning || '—')}</td>
          </tr>
          {data.grammar && (
            <tr><td>Grammar</td><td className="fc-grammar">{data.grammar}</td></tr>
          )}
        </tbody>
      </table>
      <button className="fc-btn fc-btn-secondary" onClick={() => speak(data.text)}>🔊 Hear it</button>
    </div>
  )
}
