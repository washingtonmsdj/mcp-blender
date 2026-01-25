import { forwardRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  PanelLeft,
  PanelRight,
  Settings,
  FileText,
  Package,
  Plus,
  FolderOpen,
  Download,
  MapPin,
  User,
  Bell,
  Save,
  Gamepad2,
} from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { PresetSelectionModal } from "./PresetSelectionModal";
import type { OrdaxSpec } from "@/lib/ordax/types";

type Props = {
  onSave?: () => void;
  onExport?: () => void;
  onToggleLeft?: () => void;
  onToggleRight?: () => void;
  onPresetConfirm?: (spec: OrdaxSpec) => void;
};

export const StudioTopBar = forwardRef<HTMLDivElement, Props>(function StudioTopBar(
  { onSave, onExport, onToggleLeft, onToggleRight, onPresetConfirm }: Props,
  ref,
) {
  const [presetModalOpen, setPresetModalOpen] = useState(false);

  const handlePresetConfirm = (spec: OrdaxSpec) => {
    onPresetConfirm?.(spec);
    toast.success('Jogo criado!', {
      description: 'Seu jogo está pronto para jogar'
    });
  };

  return (
    <div ref={ref} className="h-12 border-b border-border/50 bg-card/60 flex items-center justify-between px-4">
      {/* Left Section */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onToggleLeft}
          aria-label="Alternar sidebar esquerda"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <div className="flex items-center gap-2 mr-4">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center">
            <span className="text-xs font-bold">OX</span>
          </div>
          <span className="font-bold text-sm">Ordax Studio</span>
        </div>

        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={() => toast.info("Setup em desenvolvimento")}
        >
          <Settings className="h-3 w-3" />
          Setup
        </Button>

        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={() => toast.info("Templates em desenvolvimento")}
        >
          <FileText className="h-3 w-3" />
          Templates
        </Button>

        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={() => toast.info("Assets em desenvolvimento")}
        >
          <Package className="h-3 w-3" />
          Assets
        </Button>

        <Button 
          variant="default" 
          size="sm" 
          className="h-8 text-xs gap-2 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700"
          onClick={() => setPresetModalOpen(true)}
        >
          <Gamepad2 className="h-3 w-3" />
          Jogos Canônicos
        </Button>

        <Button 
          variant="default" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={() => toast.success("Novo projeto criado!")}
        >
          <Plus className="h-3 w-3" />
          Novo Projeto
        </Button>

        <Link to="/">
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-2">
            <FolderOpen className="h-3 w-3" />
            Meus Projetos
          </Button>
        </Link>

        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={onExport}
        >
          <Download className="h-3 w-3" />
          Exportar
        </Button>

        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 text-xs gap-2"
          onClick={onSave}
        >
          <Save className="h-3 w-3" />
          Salvar
        </Button>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onToggleRight}
          aria-label="Alternar painel de arquivos"
        >
          <PanelRight className="h-4 w-4" />
        </Button>

        <Badge variant="outline" className="border-neon-green/30 bg-neon-green/10 text-neon-green text-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-neon-green mr-1.5 animate-pulse"></span>
          Sem projeto
        </Badge>

        <Button 
          variant="ghost" 
          size="icon" 
          className="h-8 w-8"
          onClick={() => toast.info("Sem notificações")}
        >
          <Bell className="h-4 w-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
              <User className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => toast.info("Perfil em desenvolvimento")}>
              Perfil
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => toast.info("Configurações em desenvolvimento")}>
              Configurações
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => toast.success("Logout realizado")}>
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      
      {/* Preset Selection Modal */}
      <PresetSelectionModal
        open={presetModalOpen}
        onOpenChange={setPresetModalOpen}
        onConfirm={handlePresetConfirm}
      />
    </div>
  );
});
