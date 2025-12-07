import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Mic, Square, Loader2 } from "lucide-react";
import { apiClient } from "@/api/client";
import { useToast } from "@/hooks/use-toast";

interface VoiceRecorderProps {
  onTranscriptionComplete?: (transcription: string) => void;
  onSave?: (transcription: string) => void;
}

export const VoiceRecorder = ({ onTranscriptionComplete, onSave }: VoiceRecorderProps) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcription, setTranscription] = useState<string>("");
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await handleTranscription(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setDuration(0);

      // Start duration timer
      intervalRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } catch (error) {
      console.error("Error starting recording:", error);
      toast({
        title: "Recording Error",
        description: "Could not access microphone. Please check permissions.",
        variant: "destructive",
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };

  const handleTranscription = async (audioBlob: Blob) => {
    setIsTranscribing(true);
    try {
      const result = await apiClient.transcribe.upload(audioBlob);
      const transcribedText = result.transcription || result.text || "";
      setTranscription(transcribedText);
      onTranscriptionComplete?.(transcribedText);
    } catch (error) {
      console.error("Transcription error:", error);
      toast({
        title: "Transcription Error",
        description: "Failed to transcribe audio. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSave = () => {
    if (transcription.trim()) {
      onSave?.(transcription);
      setTranscription("");
      setDuration(0);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        {!isRecording ? (
          <Button
            onClick={startRecording}
            className="bg-gradient-primary hover:shadow-glow"
            size="lg"
          >
            <Mic className="w-5 h-5 mr-2" />
            Start Recording
          </Button>
        ) : (
          <Button
            onClick={stopRecording}
            variant="destructive"
            size="lg"
          >
            <Square className="w-5 h-5 mr-2" />
            Stop Recording
          </Button>
        )}

        {isRecording && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            <span className="text-sm font-mono">{formatDuration(duration)}</span>
          </div>
        )}

        {isTranscribing && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Transcribing...</span>
          </div>
        )}
      </div>

      {transcription && (
        <div className="space-y-2">
          <div className="p-4 bg-muted rounded-lg border">
            <p className="text-sm text-muted-foreground mb-2">Transcription:</p>
            <p className="text-sm">{transcription}</p>
          </div>
          <Button onClick={handleSave} size="sm" variant="outline">
            Save as Insight
          </Button>
        </div>
      )}
    </div>
  );
};

