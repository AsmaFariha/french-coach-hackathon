// Shared browser text-to-speech helper (French voice).
export function speak(text) {
  if (!text || !window.speechSynthesis) return
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'fr-FR'
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(u)
}

// Speak several lines back-to-back (e.g. consecutive dialogue turns from the
// same speaker) without one cancelling the next.
export function speakAll(texts) {
  const list = (texts || []).filter(Boolean)
  if (!list.length || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  for (const text of list) {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'fr-FR'
    window.speechSynthesis.speak(u)
  }
}
