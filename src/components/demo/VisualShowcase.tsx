import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Gamepad2, Sparkles, Zap } from "lucide-react";

export const VisualShowcase = () => {
  return (
    <div className="min-h-screen p-8 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 py-12">
        <h1 className="text-6xl font-bold neon-text animate-fade-in">
          Ordax Engine
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Create games with AI-powered visual design system
        </p>
        <div className="flex gap-3 justify-center">
          <Badge className="bg-neon-cyan/20 text-neon-cyan border-neon-cyan/40 neon-glow">
            <Sparkles className="w-3 h-3 mr-1" />
            AI Powered
          </Badge>
          <Badge className="bg-neon-magenta/20 text-neon-magenta border-neon-magenta/40">
            <Gamepad2 className="w-3 h-3 mr-1" />
            2D Engine
          </Badge>
          <Badge className="bg-neon-green/20 text-neon-green border-neon-green/40">
            <Zap className="w-3 h-3 mr-1" />
            Real-time
          </Badge>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
        {/* Glass Panel Card */}
        <Card className="glass-panel neon-glow">
          <CardHeader>
            <CardTitle className="text-primary">Glass Effect</CardTitle>
            <CardDescription>Frosted glass with backdrop blur</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This card uses the glass-panel utility class for a modern frosted glass effect.
            </p>
          </CardContent>
        </Card>

        {/* Neon Glow Card */}
        <Card className="glass-panel border-primary/30">
          <CardHeader>
            <CardTitle className="neon-text">Neon Glow</CardTitle>
            <CardDescription>Glowing text and borders</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Neon effects with custom shadow and glow animations.
            </p>
          </CardContent>
        </Card>

        {/* Surface Colors */}
        <Card className="bg-surface-2 border-border/50">
          <CardHeader>
            <CardTitle>Surface Layers</CardTitle>
            <CardDescription>Depth with surface colors</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="p-3 rounded bg-surface-1 text-xs font-mono">Surface 1</div>
            <div className="p-3 rounded bg-surface-2 text-xs font-mono">Surface 2</div>
            <div className="p-3 rounded bg-surface-3 text-xs font-mono">Surface 3</div>
          </CardContent>
        </Card>

        {/* Neon Colors */}
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Neon Palette</CardTitle>
            <CardDescription>Gaming color scheme</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex gap-2">
              <div className="h-10 w-10 rounded bg-neon-cyan neon-glow"></div>
              <div className="h-10 w-10 rounded bg-neon-magenta"></div>
              <div className="h-10 w-10 rounded bg-neon-green"></div>
              <div className="h-10 w-10 rounded bg-neon-orange"></div>
              <div className="h-10 w-10 rounded bg-neon-purple"></div>
            </div>
            <p className="text-xs text-muted-foreground font-mono">
              Cyan • Magenta • Green • Orange • Purple
            </p>
          </CardContent>
        </Card>

        {/* Buttons */}
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Interactive Elements</CardTitle>
            <CardDescription>Buttons with effects</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button className="w-full neon-glow">Primary Button</Button>
            <Button variant="secondary" className="w-full">Secondary</Button>
            <Button variant="outline" className="w-full glass-panel">Outline</Button>
          </CardContent>
        </Card>

        {/* Typography */}
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="font-sans">Typography</CardTitle>
            <CardDescription>Space Grotesk & JetBrains Mono</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="font-sans text-sm">Space Grotesk - UI Text</p>
            <p className="font-mono text-xs text-primary">JetBrains Mono - Code</p>
            <p className="text-xs text-muted-foreground">
              Custom fonts for modern gaming aesthetic
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Animations Demo */}
      <div className="max-w-7xl mx-auto">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Animations</CardTitle>
            <CardDescription>Built-in animation utilities</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 glass-panel rounded-lg animate-fade-in">
              <p className="text-xs font-mono">fade-in</p>
            </div>
            <div className="p-4 glass-panel rounded-lg animate-pulse">
              <p className="text-xs font-mono">pulse</p>
            </div>
            <div className="p-4 glass-panel rounded-lg animate-shimmer bg-gradient-to-r from-primary/20 via-primary/40 to-primary/20 bg-[length:200%_100%]">
              <p className="text-xs font-mono">shimmer</p>
            </div>
            <div className="p-4 glass-panel rounded-lg border-2 border-primary/50 neon-glow">
              <p className="text-xs font-mono">neon-glow</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
