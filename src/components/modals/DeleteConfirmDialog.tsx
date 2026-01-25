import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface DeleteConfirmDialogProps {
  onConfirm: () => void;
  itemName?: string;
}

export const DeleteConfirmDialog = ({ onConfirm, itemName = "este item" }: DeleteConfirmDialogProps) => {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive" size="icon">
          <Trash2 className="h-4 w-4" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent className="glass-panel">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-destructive">Tem certeza?</AlertDialogTitle>
          <AlertDialogDescription className="text-sm">
            Esta ação não pode ser desfeita. Isso irá deletar permanentemente{" "}
            <span className="font-mono text-primary">{itemName}</span> e todos os seus dados.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="glass-panel">Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} className="bg-destructive hover:bg-destructive/90">
            Deletar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
