import React, { useRef, useEffect } from 'react';
import { TrackData } from '../audioEngine';

interface PianoRollProps {
  tracks: TrackData[];
  currentBeat: number;
  totalBars?: number;
  activeTrackIndex?: number;
}

const PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function midiToName(m: number): string {
  const name = PITCH_NAMES[m % 12];
  const oct = Math.floor(m / 12) - 1;
  return `${name}${oct}`;
}

const TRACK_COLORS: { [key: string]: { bg: string; border: string } } = {
  drums: { bg: '#10b981', border: '#059669' },
  bass: { bg: '#f59e0b', border: '#d97706' },
  chords: { bg: '#06b6d4', border: '#0891b2' },
  melody: { bg: '#a855f7', border: '#9333ea' },
  default: { bg: '#3b82f6', border: '#2563eb' }
};

export const PianoRoll: React.FC<PianoRollProps> = ({
  tracks,
  currentBeat,
  totalBars = 16,
  activeTrackIndex = -1
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Compute pitch range
  let minPitch = 127;
  let maxPitch = 0;

  tracks.forEach((trk) => {
    trk.notes.forEach((n) => {
      if (n.pitch < minPitch) minPitch = n.pitch;
      if (n.pitch > maxPitch) maxPitch = n.pitch;
    });
  });

  if (minPitch > maxPitch) {
    minPitch = 36;
    maxPitch = 72;
  } else {
    minPitch = Math.max(24, minPitch - 2);
    maxPitch = Math.min(96, maxPitch + 2);
  }

  const pitchCount = maxPitch - minPitch + 1;
  const rowHeight = 16;
  const totalBeats = Math.max(16, totalBars * 4);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const pixelsPerBeat = (width - 50) / totalBeats;

    ctx.fillStyle = '#0f1219';
    ctx.fillRect(0, 0, width, height);

    // Draw pitch grid rows
    for (let p = maxPitch; p >= minPitch; p--) {
      const rowY = (maxPitch - p) * rowHeight;
      const isBlackKey = [1, 3, 6, 8, 10].includes(p % 12);

      ctx.fillStyle = isBlackKey ? '#141824' : '#1a2030';
      ctx.fillRect(50, rowY, width - 50, rowHeight);

      // Row separator
      ctx.strokeStyle = '#22293d';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, rowY + rowHeight);
      ctx.lineTo(width, rowY + rowHeight);
      ctx.stroke();

      // Pitch Key on the left
      ctx.fillStyle = isBlackKey ? '#1e2538' : '#2b344d';
      ctx.fillRect(0, rowY, 50, rowHeight);

      ctx.fillStyle = isBlackKey ? '#94a3b8' : '#e2e8f0';
      ctx.font = '10px monospace';
      ctx.fillText(midiToName(p), 6, rowY + 12);
    }

    // Draw vertical bar lines
    for (let b = 0; b <= totalBeats; b++) {
      const x = 50 + b * pixelsPerBeat;
      const isBarLine = b % 4 === 0;

      ctx.strokeStyle = isBarLine ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = isBarLine ? 1.5 : 0.8;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();

      if (isBarLine && b < totalBeats) {
        ctx.fillStyle = '#64748b';
        ctx.font = '9px monospace';
        ctx.fillText(`${b / 4 + 1}`, x + 4, 12);
      }
    }

    // Render notes
    tracks.forEach((trk, trkIdx) => {
      if (trk.muted) return;
      if (activeTrackIndex !== -1 && activeTrackIndex !== trkIdx) return;

      const trackKey = trk.is_drum
        ? 'drums'
        : trk.name.toLowerCase().includes('bass')
        ? 'bass'
        : trk.name.toLowerCase().includes('chord') || trk.name.toLowerCase().includes('key')
        ? 'chords'
        : trk.name.toLowerCase().includes('melody') || trk.name.toLowerCase().includes('lead')
        ? 'melody'
        : 'default';

      const color = TRACK_COLORS[trackKey] || TRACK_COLORS.default;

      trk.notes.forEach((note) => {
        if (note.pitch < minPitch || note.pitch > maxPitch) return;

        const x = 50 + note.start * pixelsPerBeat;
        const noteWidth = Math.max(4, note.duration * pixelsPerBeat - 1.5);
        const y = (maxPitch - note.pitch) * rowHeight + 1.5;
        const noteHeight = rowHeight - 3;

        ctx.fillStyle = color.bg;
        ctx.fillRect(x, y, noteWidth, noteHeight);

        ctx.strokeStyle = color.border;
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, noteWidth, noteHeight);
      });
    });

    // Draw playhead cursor
    if (currentBeat >= 0) {
      const playheadX = 50 + currentBeat * pixelsPerBeat;
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();

      // Top marker flag
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.moveTo(playheadX - 5, 0);
      ctx.lineTo(playheadX + 5, 0);
      ctx.lineTo(playheadX, 10);
      ctx.closePath();
      ctx.fill();
    }
  }, [tracks, currentBeat, totalBars, activeTrackIndex, minPitch, maxPitch, pitchCount]);

  return (
    <div className="w-full overflow-x-auto rounded border border-neutral-800 bg-[#0f1219]">
      <canvas
        ref={canvasRef}
        width={960}
        height={Math.max(240, pitchCount * rowHeight)}
        className="block"
      />
    </div>
  );
};
