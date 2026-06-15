import { Download, Pause, Play, RotateCcw, RotateCw, Volume2, Waves } from "lucide-react";
import { useRef, useState } from "react";

type AudioPlayerProps = {
  src: string;
  downloadUrl: string;
};

function formatTime(value: number): string {
  if (!Number.isFinite(value)) {
    return "0:00";
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function AudioPlayer({ src, downloadUrl }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState("");
  const [isReady, setIsReady] = useState(false);

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio || !src) {
      return;
    }
    setError("");
    if (audio.paused) {
      try {
        await audio.play();
        setIsPlaying(true);
      } catch {
        setError("Audio could not be played.");
      }
    } else {
      audio.pause();
      setIsPlaying(false);
    }
  }

  function seek(value: number) {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }
    audio.currentTime = value;
    setCurrentTime(value);
  }

  function skip(delta: number) {
    seek(Math.max(0, Math.min(duration || 0, currentTime + delta)));
  }

  function changeSpeed(value: number) {
    const audio = audioRef.current;
    if (audio) {
      audio.playbackRate = value;
    }
    setSpeed(value);
  }

  function changeVolume(value: number) {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = value;
    }
    setVolume(value);
  }

  return (
    <div className="custom-player" aria-label="Custom audio player">
      <audio
        aria-label="Generated podcast audio source"
        ref={audioRef}
        src={src}
        onCanPlay={() => setIsReady(true)}
        onEnded={() => setIsPlaying(false)}
        onError={() => {
          setIsReady(false);
          setError("Audio could not be loaded.");
        }}
        onLoadedMetadata={(event) => {
          setDuration(event.currentTarget.duration);
          setIsReady(true);
        }}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
      >
        <track kind="captions" />
      </audio>

      <div className="player-topline">
        <div className="player-title">
          <Waves aria-hidden="true" />
          <div>
            <strong>Generated WAV</strong>
            <span>{isReady ? "Ready to review" : "Preparing audio"}</span>
          </div>
        </div>
        <span className="time-readout">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      <input
        aria-label="Seek audio"
        className="timeline"
        disabled={!src}
        max={duration || 0}
        min={0}
        onChange={(event) => seek(Number(event.target.value))}
        type="range"
        value={currentTime}
      />

      <div className="player-controls">
        <button className="icon-button" onClick={() => skip(-15)} aria-label="Skip back 15 seconds" type="button">
          <RotateCcw aria-hidden="true" />
        </button>
        <button
          className="icon-button play-button"
          onClick={togglePlayback}
          aria-label={isPlaying ? "Pause" : "Play"}
          type="button"
        >
          {isPlaying ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
        </button>
        <button className="icon-button" onClick={() => skip(15)} aria-label="Skip forward 15 seconds" type="button">
          <RotateCw aria-hidden="true" />
        </button>
        <label className="compact-select">
          <span>Speed</span>
          <select
            aria-label="Playback speed"
            value={speed}
            onChange={(event) => changeSpeed(Number(event.target.value))}
          >
            <option value={0.75}>0.75x</option>
            <option value={1}>1x</option>
            <option value={1.25}>1.25x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
        </label>
        <label className="volume-control">
          <Volume2 aria-hidden="true" />
          <span className="sr-only">Volume</span>
          <input
            aria-label="Volume"
            max={1}
            min={0}
            onChange={(event) => changeVolume(Number(event.target.value))}
            step={0.05}
            type="range"
            value={volume}
          />
        </label>
        <a className="action-link" href={downloadUrl} download>
          <Download aria-hidden="true" />
          Download WAV
        </a>
      </div>
      {error && <p className="message">{error}</p>}
    </div>
  );
}
