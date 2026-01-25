import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { bundler } from "@/lib/export/bundler";
import { GAMES } from "@/games";

export default function Games() {
  const navigate = useNavigate();
  const games = useMemo(() => GAMES, []);

  return (
    <main className="min-h-screen w-full bg-background">
      <header className="mx-auto max-w-6xl px-6 py-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Games</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Biblioteca de jogos (treinamento). Carregue no Studio ou exporte como HTML.
            </p>
          </div>
          {/* Evita warning de ref (Button asChild + Link) */}
          <Link to="/workspace" className={buttonVariants({ variant: "outline" })}>
            Abrir Studio
          </Link>
        </div>
        <Separator className="mt-6" />
      </header>

      <section className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 pb-10 md:grid-cols-2">
        {games.map((g) => (
          <Card key={g.id} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-lg">{g.title}</CardTitle>
                  <CardDescription className="mt-1">{g.tagline}</CardDescription>
                </div>
                <Badge variant="secondary">MVP</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">{g.description}</p>
              <div className="flex flex-wrap gap-2">
                {g.play?.kind === "standalone" ? (
                  <Button asChild variant="secondary">
                    <Link to={g.play.route}>Jogar</Link>
                  </Button>
                ) : null}
                <Button
                  onClick={() => navigate(`/workspace?game=${encodeURIComponent(g.id)}`)}
                >
                  Carregar no Studio
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    try {
                      const spec = g.buildSpec();
                      bundler.downloadHTML(spec, {
                        projectName: g.id,
                        includeAssets: true,
                        minify: false,
                      });
                      toast.success("HTML exportado!");
                    } catch (e) {
                      console.error(e);
                      toast.error("Falha ao exportar HTML");
                    }
                  }}
                >
                  Exportar HTML
                </Button>
              </div>
              {g.docPath ? (
                <p className="text-xs text-muted-foreground">
                  Doc (repo): <span className="font-mono">{g.docPath}</span>
                </p>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}
