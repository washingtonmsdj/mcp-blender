import { Progress } from "@/components/ui/progress";
import { useState, useEffect } from "react";

interface ProgressBarProps {
  value?: number;
  autoProgress?: boolean;
}

export const ProgressBar = ({ value, autoProgress = false }: ProgressBarProps) => {
  const [progress, setProgress] = useState(value || 0);

  useEffect(() => {
    if (autoProgress) {
      const timer = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(timer);
            return 100;
          }
          return prev + 10;
        });
      }, 500);

      return () => clearInterval(timer);
    } else if (value !== undefined) {
      setProgress(value);
    }
  }, [autoProgress, value]);

  return (
    <div className="space-y-2">
      <Progress value={progress} className="w-full" />
      <p className="text-xs text-muted-foreground text-center font-mono">
        {progress}% completo
      </p>
    </div>
  );
};
