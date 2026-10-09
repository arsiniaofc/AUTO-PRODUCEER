/**
 * Web Audio Engine for Autonomous Music Producer.
 * Provides polyphonic synthesizers (Drums, Bass, Chords/Keys, Lead Melody)
 * to preview generated compositions in the browser with zero external dependencies.
 */

export interface NoteEvent {
  pitch: number;
  start: number; // in beats
  duration: number; // in beats
  velocity: number;
}

export interface TrackData {
  name: string;
  channel: number;
  is_drum: boolean;
  notes: NoteEvent[];
  muted?: boolean;
  solo?: boolean;
  volume?: number;
}

class AudioEngine {
  private ctx: AudioContext | null = null;
  private isPlaying: boolean = false;
  private currentBpm: number = 124.0;
  private scheduledSources: { stop: () => void }[] = [];
  private playbackStartTime: number = 0;
  private timerId: number | null = null;
  private onPositionUpdate: ((beat: number) => void) | null = null;
  private onPlaybackEnd: (() => void) | null = null;

  public init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  public getContext(): AudioContext {
    this.init();
    return this.ctx!;
  }

  private midiToFreq(midi: number): number {
    return 440 * Math.pow(2, (midi - 69) / 12);
  }

  // Synthesizes a kick drum
  private playKick(time: number, velocity: number) {
    if (!this.ctx) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    const velNorm = velocity / 127;

    // Pitch envelope
    osc.frequency.setValueAtTime(140, time);
    osc.frequency.exponentialRampToValueAtTime(38, time + 0.12);

    // Gain envelope
    gain.gain.setValueAtTime(0.9 * velNorm, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.35);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(time);
    osc.stop(time + 0.36);
    this.scheduledSources.push({ stop: () => { try { osc.stop(); } catch {} } });
  }

  // Synthesizes a snare drum
  private playSnare(time: number, velocity: number) {
    if (!this.ctx) return;
    const velNorm = velocity / 127;

    // Noise component
    const bufferSize = this.ctx.sampleRate * 0.2;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.setValueAtTime(1000, time);

    const noiseGain = this.ctx.createGain();
    noiseGain.gain.setValueAtTime(0.7 * velNorm, time);
    noiseGain.gain.exponentialRampToValueAtTime(0.01, time + 0.2);

    noise.connect(filter);
    filter.connect(noiseGain);
    noiseGain.connect(this.ctx.destination);

    // Tonal body
    const osc = this.ctx.createOscillator();
    const oscGain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(180, time);
    osc.frequency.exponentialRampToValueAtTime(80, time + 0.1);

    oscGain.gain.setValueAtTime(0.5 * velNorm, time);
    oscGain.gain.exponentialRampToValueAtTime(0.01, time + 0.15);

    osc.connect(oscGain);
    oscGain.connect(this.ctx.destination);

    noise.start(time);
    noise.stop(time + 0.2);
    osc.start(time);
    osc.stop(time + 0.15);

    this.scheduledSources.push({
      stop: () => {
        try { noise.stop(); osc.stop(); } catch {}
      }
    });
  }

  // Synthesizes hi-hat
  private playHiHat(time: number, velocity: number, isOpen: boolean) {
    if (!this.ctx) return;
    const velNorm = velocity / 127;
    const dur = isOpen ? 0.35 : 0.08;

    const bufferSize = this.ctx.sampleRate * dur;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(8000, time);
    filter.Q.setValueAtTime(2.0, time);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.4 * velNorm, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + dur);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    noise.start(time);
    noise.stop(time + dur);
    this.scheduledSources.push({ stop: () => { try { noise.stop(); } catch {} } });
  }

  // Synthesizes melodic synth tone (Bass, Keys, Lead)
  private playSynthNote(pitch: number, time: number, durationSec: number, velocity: number, instrumentType: 'bass' | 'chords' | 'lead') {
    if (!this.ctx) return;
    const freq = this.midiToFreq(pitch);
    const velNorm = velocity / 127;

    const osc = this.ctx.createOscillator();
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    if (instrumentType === 'bass') {
      osc.type = 'sawtooth';
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(450, time);
      filter.frequency.exponentialRampToValueAtTime(150, time + durationSec);
      filter.Q.setValueAtTime(3, time);

      gain.gain.setValueAtTime(0.001, time);
      gain.gain.linearRampToValueAtTime(0.55 * velNorm, time + 0.02);
      gain.gain.setValueAtTime(0.45 * velNorm, time + durationSec * 0.7);
      gain.gain.exponentialRampToValueAtTime(0.001, time + durationSec);
    } else if (instrumentType === 'chords') {
      osc.type = 'triangle';
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(2200, time);
      filter.Q.setValueAtTime(1.0, time);

      gain.gain.setValueAtTime(0.001, time);
      gain.gain.linearRampToValueAtTime(0.25 * velNorm, time + 0.05);
      gain.gain.setValueAtTime(0.2 * velNorm, time + durationSec * 0.8);
      gain.gain.exponentialRampToValueAtTime(0.001, time + durationSec);
    } else {
      // Lead
      osc.type = 'sawtooth';
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(3500, time);
      filter.Q.setValueAtTime(2.5, time);

      gain.gain.setValueAtTime(0.001, time);
      gain.gain.linearRampToValueAtTime(0.3 * velNorm, time + 0.03);
      gain.gain.setValueAtTime(0.25 * velNorm, time + durationSec * 0.7);
      gain.gain.exponentialRampToValueAtTime(0.001, time + durationSec);
    }

    osc.frequency.setValueAtTime(freq, time);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(time);
    osc.stop(time + durationSec);

    this.scheduledSources.push({ stop: () => { try { osc.stop(); } catch {} } });
  }

  public playTracks(tracks: TrackData[], bpm: number = 124.0, onProgress?: (beat: number) => void, onEnd?: () => void) {
    this.stop();
    this.init();
    if (!this.ctx) return;

    this.isPlaying = true;
    this.currentBpm = bpm;
    this.onPositionUpdate = onProgress || null;
    this.onPlaybackEnd = onEnd || null;

    const secondsPerBeat = 60.0 / bpm;
    const now = this.ctx.currentTime + 0.05;
    this.playbackStartTime = now;

    let maxBeats = 4;

    const hasSolo = tracks.some(t => t.solo);

    for (const track of tracks) {
      if (track.muted) continue;
      if (hasSolo && !track.solo) continue;

      const trackType: 'bass' | 'chords' | 'lead' = track.name.toLowerCase().includes('bass')
        ? 'bass'
        : track.name.toLowerCase().includes('chord') || track.name.toLowerCase().includes('key')
        ? 'chords'
        : 'lead';

      for (const note of track.notes) {
        const noteStartTime = now + note.start * secondsPerBeat;
        const noteDurationSec = Math.max(0.08, note.duration * secondsPerBeat);

        maxBeats = Math.max(maxBeats, note.start + note.duration);

        if (track.is_drum) {
          if (note.pitch === 36) {
            this.playKick(noteStartTime, note.velocity);
          } else if (note.pitch === 38 || note.pitch === 40) {
            this.playSnare(noteStartTime, note.velocity);
          } else if (note.pitch === 42 || note.pitch === 44) {
            this.playHiHat(noteStartTime, note.velocity, false);
          } else if (note.pitch === 46 || note.pitch === 49) {
            this.playHiHat(noteStartTime, note.velocity, true);
          } else {
            this.playSnare(noteStartTime, note.velocity);
          }
        } else {
          this.playSynthNote(note.pitch, noteStartTime, noteDurationSec, note.velocity, trackType);
        }
      }
    }

    const totalSeconds = maxBeats * secondsPerBeat;

    // Progress tick timer
    const intervalMs = 40;
    this.timerId = window.setInterval(() => {
      if (!this.ctx || !this.isPlaying) return;
      const elapsed = this.ctx.currentTime - this.playbackStartTime;
      const currentBeat = elapsed / secondsPerBeat;
      if (this.onPositionUpdate) {
        this.onPositionUpdate(currentBeat);
      }
      if (elapsed >= totalSeconds) {
        this.stop();
        if (this.onPlaybackEnd) {
          this.onPlaybackEnd();
        }
      }
    }, intervalMs);
  }

  public stop() {
    this.isPlaying = false;
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    for (const src of this.scheduledSources) {
      try {
        src.stop();
      } catch {}
    }
    this.scheduledSources = [];
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }
}

export const audioEngine = new AudioEngine();
