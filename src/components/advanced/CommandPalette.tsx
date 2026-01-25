import { useState, useEffect } from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Search, FileCode, Image, Music, Settings, Gamepad2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

export const CommandPalette = () => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // Atalho de teclado Ctrl+K ou Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const handleSelect = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  return (
    <>
      <Button
        variant="outline"
        className="w-full justify-start text-muted-foreground glass-panel font-mono text-xs"
        onClick={() => setOpen(true)}
      >
        <Search className="mr-2 h-4 w-4" />
        Buscar... (Ctrl+K)
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Digite para buscar..." className="font-mono" />
        <CommandList>
          <CommandEmpty>Nenhum resultado encontrado.</CommandEmpty>
          
          <CommandGroup heading="Páginas">
            <CommandItem onSelect={() => handleSelect("/")}>
              <Gamepad2 className="mr-2 h-4 w-4 text-primary" />
              <span className="font-mono text-sm">Home</span>
            </CommandItem>
            <CommandItem onSelect={() => handleSelect("/workspace")}>
              <FileCode className="mr-2 h-4 w-4 text-neon-cyan" />
              <span className="font-mono text-sm">Workspace</span>
            </CommandItem>
            <CommandItem onSelect={() => handleSelect("/demo")}>
              <Sparkles className="mr-2 h-4 w-4 text-neon-magenta" />
              <span className="font-mono text-sm">Visual Demo</span>
            </CommandItem>
            <CommandItem onSelect={() => handleSelect("/components")}>
              <FileCode className="mr-2 h-4 w-4 text-neon-green" />
              <span className="font-mono text-sm">Components Library</span>
            </CommandItem>
          </CommandGroup>
          
          <CommandGroup heading="Projetos">
            <CommandItem>
              <FileCode className="mr-2 h-4 w-4 text-primary" />
              <span className="font-mono text-sm">Space Shooter</span>
            </CommandItem>
            <CommandItem>
              <FileCode className="mr-2 h-4 w-4 text-primary" />
              <span className="font-mono text-sm">Platformer Game</span>
            </CommandItem>
            <CommandItem>
              <FileCode className="mr-2 h-4 w-4 text-primary" />
              <span className="font-mono text-sm">Puzzle Master</span>
            </CommandItem>
          </CommandGroup>
          
          <CommandGroup heading="Assets">
            <CommandItem>
              <Image className="mr-2 h-4 w-4 text-neon-magenta" />
              <span className="font-mono text-sm">player_sprite.png</span>
            </CommandItem>
            <CommandItem>
              <Music className="mr-2 h-4 w-4 text-neon-green" />
              <span className="font-mono text-sm">background_music.mp3</span>
            </CommandItem>
            <CommandItem>
              <Image className="mr-2 h-4 w-4 text-neon-magenta" />
              <span className="font-mono text-sm">enemy_sprite.png</span>
            </CommandItem>
          </CommandGroup>
          
          <CommandGroup heading="Configurações">
            <CommandItem>
              <Settings className="mr-2 h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm">Preferências</span>
            </CommandItem>
            <CommandItem>
              <Settings className="mr-2 h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm">Atalhos de Teclado</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
};
