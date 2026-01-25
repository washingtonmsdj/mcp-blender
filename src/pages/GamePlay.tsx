import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { StellarVanguardStandaloneView } from "@/games/stellar-vanguard/StandaloneView";

export default function GamePlay() {
  const params = useParams();
  const id = params.id;

  const view = useMemo(() => {
    if (id === "stellar-vanguard") return <StellarVanguardStandaloneView />;
    return (
      <main className="min-h-screen w-full bg-background grid place-items-center px-6">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold text-foreground">Game não encontrado</h1>
          <p className="mt-2 text-sm text-muted-foreground">O runner standalone ainda não existe para este id.</p>
          <div className="mt-4">
            <Button asChild variant="outline">
              <Link to="/games">Voltar para Games</Link>
            </Button>
          </div>
        </div>
      </main>
    );
  }, [id]);

  return view;
}
