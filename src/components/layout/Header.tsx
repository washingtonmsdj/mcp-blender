import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu, Settings, User, Gamepad2, Search } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CommandPalette } from "@/components/advanced/CommandPalette";

export const Header = () => {
  return (
    <header className="h-16 border-b border-border/50 glass-panel sticky top-0 z-50">
      <div className="h-full px-4 flex items-center justify-between max-w-screen-2xl mx-auto">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center neon-glow">
            <Gamepad2 className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-xl neon-text hidden sm:block">Ordax Engine</span>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-2 flex-1 max-w-md mx-4">
          <div className="w-full">
            <CommandPalette />
          </div>
        </nav>

        {/* User Menu */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="hidden sm:flex">
            <Settings className="h-5 w-5" />
          </Button>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="neon-glow">
                <User className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="glass-panel">
              <DropdownMenuItem>Perfil</DropdownMenuItem>
              <DropdownMenuItem>Configurações</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">Sair</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Mobile Menu */}
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
};
