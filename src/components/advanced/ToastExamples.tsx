import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { CheckCircle, XCircle, Info, AlertTriangle, Loader2 } from "lucide-react";

export const ToastExamples = () => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {/* Success */}
      <Button 
        onClick={() => toast.success("Operação realizada com sucesso!")}
        className="neon-glow"
      >
        <CheckCircle className="h-4 w-4 mr-2" />
        Success
      </Button>

      {/* Error */}
      <Button 
        variant="destructive"
        onClick={() => toast.error("Algo deu errado!")}
      >
        <XCircle className="h-4 w-4 mr-2" />
        Error
      </Button>

      {/* Info */}
      <Button 
        variant="outline"
        className="glass-panel"
        onClick={() => toast.info("Informação importante")}
      >
        <Info className="h-4 w-4 mr-2" />
        Info
      </Button>

      {/* Warning */}
      <Button 
        variant="secondary"
        onClick={() => toast.warning("Atenção!")}
      >
        <AlertTriangle className="h-4 w-4 mr-2" />
        Warning
      </Button>

      {/* Loading */}
      <Button onClick={() => {
        const promise = new Promise((resolve) => 
          setTimeout(resolve, 2000)
        );
        
        toast.promise(promise, {
          loading: 'Carregando...',
          success: 'Concluído!',
          error: 'Erro!',
        });
      }}>
        <Loader2 className="h-4 w-4 mr-2" />
        Loading
      </Button>

      {/* Com ação */}
      <Button 
        variant="outline"
        className="glass-panel"
        onClick={() => {
          toast("Arquivo deletado", {
            action: {
              label: "Desfazer",
              onClick: () => toast.success("Ação desfeita!"),
            },
          });
        }}
      >
        Com Ação
      </Button>
    </div>
  );
};
