import { Loader2 } from "lucide-react";

interface SpinnerProps {
  size?: "sm" | "default" | "lg";
}

export const Spinner = ({ size = "default" }: SpinnerProps) => {
  const sizeClasses = {
    sm: "h-4 w-4",
    default: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <Loader2 className={`${sizeClasses[size]} animate-spin text-primary neon-glow`} />
  );
};

export const LoadingScreen = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-muted-foreground font-mono text-sm">Carregando...</p>
      </div>
    </div>
  );
};
