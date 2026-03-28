import React, { useRef, useEffect, useState, useCallback } from 'react';

const getBarCount = () => (window.innerWidth < 400 ? 20 : 30);

interface AudioVisualizerProps {
  audioUrl: string | null;
  isPlaying: boolean;
  onAudioEnd?: () => void;
  className?: string;
  showBackground?: boolean;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  audioUrl,
  isPlaying,
  onAudioEnd,
  className = '',
  showBackground = true
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const onAudioEndRef = useRef(onAudioEnd);
  const barHeightsRef = useRef<number[]>([]);
  const [, forceUpdate] = useState({});
  const [barCount, setBarCount] = useState(getBarCount());
  const [isAnalyserReady, setIsAnalyserReady] = useState(false);

  // Keep onAudioEnd ref current without triggering effect re-runs
  useEffect(() => {
    onAudioEndRef.current = onAudioEnd;
  }, [onAudioEnd]);

  useEffect(() => {
    barHeightsRef.current = Array(barCount).fill(2);
  }, [barCount]);

  useEffect(() => {
    const handleResize = () => setBarCount(getBarCount());
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Merged effect: audio element creation + audio context wiring + playback
  useEffect(() => {
    if (!audioUrl || !isPlaying) {
      // Tear down cleanly without setting src = ''
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (sourceRef.current) {
        sourceRef.current.disconnect();
        sourceRef.current = null;
      }
      analyserRef.current = null;
      setIsAnalyserReady(false);
      return;
    }

    // Create audio element
    const audio = new Audio(audioUrl);
    audio.crossOrigin = 'anonymous';
    audioRef.current = audio;

    audio.onended = () => {
      console.log('[AudioVisualizer] Audio ended');
      onAudioEndRef.current?.();
    };

    audio.onerror = (e) => {
      console.error('[AudioVisualizer] Audio error:', e);
      console.error('[AudioVisualizer] Error details:', audio.error);
      onAudioEndRef.current?.();
    };

    // Wire up audio context and analyser on the same element, atomically
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      try {
        // Reuse existing context or create one
        if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
          audioContextRef.current = new AudioContextClass();
        }
        const audioContext = audioContextRef.current;

        if (audioContext.state === 'suspended') {
          audioContext.resume();
        }

        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.8;
        analyserRef.current = analyser;

        const source = audioContext.createMediaElementSource(audio);
        sourceRef.current = source;
        source.connect(analyser);
        analyser.connect(audioContext.destination);

        setIsAnalyserReady(true);
      } catch (err) {
        console.error('[AudioVisualizer] Audio context error:', err);
      }
    }

    audio.play().catch(err => {
      console.error('[AudioVisualizer] Play failed:', err);
    });

    return () => {
      audio.pause();
      audio.onended = null;
      audio.onerror = null;
      if (sourceRef.current) {
        sourceRef.current.disconnect();
        sourceRef.current = null;
      }
      analyserRef.current = null;
      audioRef.current = null;
      setIsAnalyserReady(false);
    };
  }, [audioUrl, isPlaying]);

  // Close audio context only on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  // Animation loop — triggered by isAnalyserReady state, not a ref in deps
  useEffect(() => {
    if (!isAnalyserReady || !analyserRef.current || !isPlaying) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(barCount);

    const animate = () => {
      analyser.getByteFrequencyData(dataArray);

      for (let i = 0; i < barCount; i++) {
        const value = dataArray[i];
        barHeightsRef.current[i] = 2 + (value / 255) * 38;
      }

      forceUpdate({});
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isAnalyserReady, isPlaying, barCount]);

  return (
    <div 
      className={`w-full max-w-md h-20 mx-auto rounded-2xl flex items-center justify-center ${showBackground ? 'bg-gray-50/50' : ''} ${className}`}
      role="img"
      aria-label="Audio visualization"
    >
      {!isPlaying && (
        <div className="flex justify-center items-center h-full gap-2.5">
          {Array.from({ length: barCount }).map((_, i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-legacy-purple/40"
              style={{
                animation: 'breathe 2s ease-in-out infinite',
                animationDelay: `${i * 0.03}s`
              }}
            />
          ))}
        </div>
      )}
      {isPlaying && (
        <svg className="w-full h-full" preserveAspectRatio="xMidYMid meet">
          <g transform="translate(0, 40)">
            {Array.from({ length: barCount }).map((_, i) => {
              const x = (i / barCount) * 100;
              const height = barHeightsRef.current[i];
              return (
                <rect
                  key={`top-${i}`}
                  x={`${x}%`}
                  y={-height}
                  width="2%"
                  height={height}
                  rx={1}
                  fill="hsl(252, 80%, 75%)"
                  opacity={0.8}
                />
              );
            })}
            {Array.from({ length: barCount }).map((_, i) => {
              const x = (i / barCount) * 100;
              const height = barHeightsRef.current[i];
              return (
                <rect
                  key={`bottom-${i}`}
                  x={`${x}%`}
                  y={0}
                  width="2%"
                  height={height}
                  rx={1}
                  fill="hsl(252, 80%, 75%)"
                  opacity={0.8}
                />
              );
            })}
          </g>
        </svg>
      )}
    </div>
  );
};
