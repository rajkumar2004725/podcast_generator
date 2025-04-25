import { useEffect, useState, useRef } from "react";
// Base URL for backend API; fallback ensures correct port if env var missing
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Play, Loader, Pause } from "lucide-react";

interface PodcastProgressProps {
  taskId: string;
}

interface PodcastStatus {
  status: "processing" | "completed";
  message: string;
  progress: number;
  audio_url?: string;
}

export function PodcastProgress({ taskId }: PodcastProgressProps) {
  const [status, setStatus] = useState<PodcastStatus | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [playProgress, setPlayProgress] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0'+s : s}`;
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/podcast_status/${taskId}`);
        const data = await response.json();
        setStatus(data);

        if (data.status === "completed" && data.audio_url) {
          setAudioUrl(`${API_BASE}${data.audio_url}`);
        }

        if (data.status === "processing") {
          setTimeout(() => checkStatus(), 2000); // Poll every 2 seconds
        }
      } catch (error) {
        console.error("Error checking podcast status:", error);
      }
    };

    checkStatus();
  }, [taskId]);

  const handleDownload = () => {
    if (audioUrl) {
      const link = document.createElement("a");
      link.href = audioUrl;
      link.download = `podcast_${taskId}.mp3`;
      link.click();
    }
  };

  const togglePlay = () => {
    if (!audioRef.current && audioUrl) {
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      // set duration
      audio.addEventListener('loadedmetadata', () => setDuration(audio.duration));
      // update time and progress
      audio.addEventListener('timeupdate', () => {
        setCurrentTime(audio.currentTime);
        setPlayProgress((audio.currentTime / audio.duration) * 100);
      });
      audio.onended = () => setIsPlaying(false);
    }
    if (!audioRef.current) return;
    if (isPlaying) audioRef.current.pause();
    else audioRef.current.play();
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const pct = Number(e.target.value);
    if (audioRef.current && audioRef.current.duration) {
      audioRef.current.currentTime = (pct / 100) * audioRef.current.duration;
      setPlayProgress(pct);
    }
  };

  const skip = (secs: number) => {
    if (!audioRef.current) return;
    const newTime = Math.max(0, audioRef.current.currentTime + secs);
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
    setPlayProgress((newTime / audioRef.current.duration) * 100);
  };

  if (!status) return null;

  return (
    <Card className="backdrop-blur-sm bg-white/80 dark:bg-gray-900/80 border-0 shadow-lg overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center justify-center space-x-2">
          {status.status === "completed" ? (
            "Podcast Ready"
          ) : (
            "Converting PDF"
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <p className="text-sm text-center text-muted-foreground">
            {status.message}
          </p>
          {status.status === "processing" && (
            <div className="flex items-center justify-center gap-3">
              <Loader className="animate-spin text-primary" />
              <span className="text-primary font-medium">
                {Math.round(status.progress * 100)}%
              </span>
            </div>
          )}
          {status.status === "completed" && (
            <div className="flex flex-col space-y-4 justify-center">
              <div className="flex space-x-4 justify-center">
                <Button 
                  onClick={togglePlay}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                >
                  {isPlaying ? <Pause /> : <Play />}
                  {isPlaying ? "Pause" : "Play"}
                </Button>
                <Button
                  onClick={handleDownload}
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  <Download className="mr-2" />
                  Download
                </Button>
              </div>
              <div className="mt-2 flex flex-col items-center space-y-2">
                <p className="text-sm">{formatTime(currentTime)} / {formatTime(duration)}</p>
                <div className="flex items-center space-x-2 w-full">
                  <Button onClick={() => skip(-5)} variant="outline">-5s</Button>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={playProgress}
                    onChange={handleSeek}
                    className="flex-1"
                  />
                  <Button onClick={() => skip(5)} variant="outline">+5s</Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
