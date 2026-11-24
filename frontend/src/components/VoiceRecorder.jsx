import { useEffect, useRef, useState } from 'react'
import { useT } from '../i18n'
import { Button, Icon } from './ui'

const MAX_SECONDS = 180
const TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/ogg']

function pickType() {
  if (typeof MediaRecorder === 'undefined') return null
  return TYPES.find((t) => MediaRecorder.isTypeSupported?.(t)) || ''
}

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/**
 * Records a voice note in the browser. The audio stays in memory (never in browser storage) until the
 * report is submitted. Falls back to choosing / capturing an audio file on phones without MediaRecorder.
 */
export default function VoiceRecorder({ value, onChange }) {
  const t = useT()
  const [state, setState] = useState('idle') // idle | recording | done | error
  const [seconds, setSeconds] = useState(0)
  const [level, setLevel] = useState(0)
  const [error, setError] = useState(null)
  const recRef = useRef(null)
  const chunks = useRef([])
  const timer = useRef(null)
  const stream = useRef(null)
  const raf = useRef(null)
  const supported = typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia && pickType() !== null

  useEffect(() => () => { stopTracks(); clearInterval(timer.current); cancelAnimationFrame(raf.current) }, [])
  useEffect(() => { if (value) setState('done') }, [value])

  function stopTracks() { stream.current?.getTracks().forEach((tr) => tr.stop()) }

  async function start() {
    setError(null)
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch {
      setError(t('voice.micDenied')); setState('error'); return
    }
    const type = pickType()
    const rec = new MediaRecorder(stream.current, type ? { mimeType: type, audioBitsPerSecond: 32000 } : undefined)
    chunks.current = []
    rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
    rec.onstop = () => {
      const blob = new Blob(chunks.current, { type: rec.mimeType || 'audio/webm' })
      stopTracks(); cancelAnimationFrame(raf.current); setLevel(0)
      onChange({ blob, url: URL.createObjectURL(blob), seconds: secondsRef.current, type: (rec.mimeType || 'audio/webm').split(';')[0] })
      setState('done')
    }
    // Simple input-level meter so the speaker can see the phone is hearing them.
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const analyser = ctx.createAnalyser()
      ctx.createMediaStreamSource(stream.current).connect(analyser)
      const data = new Uint8Array(analyser.fftSize)
      const loop = () => {
        analyser.getByteTimeDomainData(data)
        let peak = 0
        for (const v of data) peak = Math.max(peak, Math.abs(v - 128))
        setLevel(Math.min(1, peak / 60))
        raf.current = requestAnimationFrame(loop)
      }
      loop()
    } catch { /* meter is optional */ }
    rec.start(1000)
    recRef.current = rec
    setSeconds(0); secondsRef.current = 0
    setState('recording')
    timer.current = setInterval(() => {
      secondsRef.current += 1
      setSeconds(secondsRef.current)
      if (secondsRef.current >= MAX_SECONDS) stop()
    }, 1000)
  }
  const secondsRef = useRef(0)

  function stop() {
    clearInterval(timer.current)
    if (recRef.current?.state === 'recording') recRef.current.stop()
  }

  function discard() {
    if (value?.url) URL.revokeObjectURL(value.url)
    onChange(null); setState('idle'); setSeconds(0)
  }

  function pickFile(e) {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > 6 * 1024 * 1024) { setError(t('voice.tooLarge')); return }
    onChange({ blob: f, url: URL.createObjectURL(f), seconds: null, type: f.type || 'audio/mp4' })
  }

  if (state === 'done' && value) {
    return (
      <div className="rounded-2xl border border-success/30 bg-success-50 p-4">
        <p className="flex items-center gap-2 font-semibold text-success-700"><Icon name="check" className="h-5 w-5" />{t('voice.saved')}{value.seconds ? ` · ${fmt(value.seconds)}` : ''}</p>
        <audio controls src={value.url} className="mt-3 w-full" />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" size="sm" icon="x" onClick={discard}>{t('voice.discard')}</Button>
        </div>
      </div>
    )
  }

  if (!supported) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-white p-5 text-center">
        <p className="text-sm text-muted">{t('voice.fallback')}</p>
        <label className="mt-3 inline-flex min-h-[48px] cursor-pointer items-center gap-2 rounded-lg bg-teal px-4 font-semibold text-white">
          <Icon name="phone" className="h-5 w-5" />{t('voice.chooseFile')}
          <input type="file" accept="audio/*" capture className="sr-only" onChange={pickFile} />
        </label>
        {error && <p className="mt-2 text-sm text-danger-700">{error}</p>}
      </div>
    )
  }

  const recording = state === 'recording'
  return (
    <div className="flex flex-col items-center rounded-2xl border border-line bg-white px-5 py-7 text-center">
      <button type="button" onClick={recording ? stop : start}
        aria-label={recording ? t('voice.stop') : t('voice.start')}
        className={`relative flex h-24 w-24 items-center justify-center rounded-full text-white shadow-lg transition focus:outline-none focus-visible:ring-4 focus-visible:ring-teal/40 ${recording ? 'bg-danger' : 'bg-teal hover:bg-teal-700'}`}>
        {recording && <span className="absolute inset-0 rounded-full bg-danger/40" style={{ transform: `scale(${1 + level * 0.6})`, transition: 'transform 80ms linear' }} />}
        {recording
          ? <span className="relative h-8 w-8 rounded-md bg-white" />
          : <svg viewBox="0 0 24 24" className="relative h-10 w-10" fill="currentColor" aria-hidden="true"><path d="M12 15a3 3 0 003-3V6a3 3 0 10-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 006 6.9V21h2v-2.1A7 7 0 0019 12h-2z" /></svg>}
      </button>
      <p className="mt-4 font-semibold text-navy" aria-live="polite">{recording ? `${t('voice.recording')} ${fmt(seconds)} / ${fmt(MAX_SECONDS)}` : t('voice.tapToStart')}</p>
      <p className="mt-1 max-w-xs text-sm text-muted">{recording ? t('voice.tapToStop') : t('voice.hint')}</p>
      {error && <p className="mt-3 text-sm text-danger-700" role="alert">{error}</p>}
    </div>
  )
}
