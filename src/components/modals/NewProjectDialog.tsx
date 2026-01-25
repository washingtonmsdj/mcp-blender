import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus } from "lucide-react";
import { toast } from "sonner";

export const NewProjectDialog = () => {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const handleCreate = () => {
    if (!name.trim()) {
      toast.error("Digite um nome para o projeto");
      return;
    }
    
    console.log("Creating project:", name);
    toast.success(`Projeto "${name}" criado com sucesso!`);
    setOpen(false);
    setName("");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="neon-glow">
          <Plus className="h-4 w-4 mr-2" />
          Novo Projeto
        </Button>
      </DialogTrigger>
      <DialogContent className="glass-panel sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="neon-text">Criar Novo Projeto</DialogTitle>
          <DialogDescription className="text-xs">
            Digite o nome do seu novo projeto abaixo.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name" className="font-mono text-sm">Nome</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Meu Projeto Incrível"
              className="glass-panel font-mono"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleCreate();
                }
              }}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" className="glass-panel" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} className="neon-glow">Criar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
