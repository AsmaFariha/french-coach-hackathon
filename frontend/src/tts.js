// Shared browser text-to-speech helper (French voice).
//
// `getVoices()` is unreliable on first call (especially Chrome): the voice
// list often loads asynchronously, so an early call returns `[]`. We cache
// the list, refresh it on the `voiceschanged` event, and pick a French voice
// (prefer fr-FR, fall back to any fr-*) once it's available — `lang` is
// always set to 'fr-FR' regardless, so the browser still defaults sanely if
// no matching voice is found.

let cachedVoices = []

function refreshVoices() {
  if (!window.speechSynthesis) return
  const voices = window.speechSynthesis.getVoices()
  if (voices.length) cachedVoices = voices
}

if (window.speechSynthesis) {
  refreshVoices()
  window.speechSynthesis.addEventListener('voiceschanged', refreshVoices)
}

function frenchVoice() {
  refreshVoices()
  return (
    cachedVoices.find((v) => v.lang === 'fr-FR') ||
    cachedVoices.find((v) => v.lang && v.lang.startsWith('fr')) ||
    null
  )
}

function makeUtterance(text) {
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'fr-FR'
  const voice = frenchVoice()
  if (voice) u.voice = voice
  return u
}

export function speak(text) {
  if (!text || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(makeUtterance(text))
}

// Speak several lines back-to-back (e.g. consecutive dialogue turns from the
// same speaker) without one cancelling the next.
export function speakAll(texts) {
  const list = (texts || []).filter(Boolean)
  if (!list.length || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  for (const text of list) {
    window.speechSynthesis.speak(makeUtterance(text))
  }
}
