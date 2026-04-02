// Sound effects using Web Audio API — no external files, works everywhere
export function playCorrectSound() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()

    // Pleasant ascending ding: two tones
    const times = [0, 0.15]
    const freqs = [523.25, 783.99] // C5, G5

    times.forEach((time, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = freqs[i]
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.3, ctx.currentTime + time)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + time + 0.4)
      osc.start(ctx.currentTime + time)
      osc.stop(ctx.currentTime + time + 0.4)
    })
  } catch (_e) { /* audio not supported */ }
}

export function playWrongSound() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()

    // Gentle descending buzz: low tone
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 220 // A3 — low but not harsh
    osc.type = 'sine'
    gain.gain.setValueAtTime(0.2, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.5)
  } catch (_e) { /* audio not supported */ }
}
