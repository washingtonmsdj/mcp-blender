import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const FAQ = () => {
  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="item-1" className="border-border/50">
        <AccordionTrigger className="font-mono text-sm hover:text-primary">
          Como criar um novo projeto?
        </AccordionTrigger>
        <AccordionContent className="text-sm text-muted-foreground">
          Clique no botão "Novo Projeto" no canto superior direito e preencha
          as informações necessárias. Você pode escolher entre diferentes tipos
          de jogos como platformer, shooter, puzzle, etc.
        </AccordionContent>
      </AccordionItem>
      
      <AccordionItem value="item-2" className="border-border/50">
        <AccordionTrigger className="font-mono text-sm hover:text-primary">
          Como importar assets?
        </AccordionTrigger>
        <AccordionContent className="text-sm text-muted-foreground">
          Vá para a aba "Assets" no seu projeto e clique em "Upload" para importar seus
          arquivos de imagem, áudio ou outros recursos. Formatos suportados: PNG, JPG,
          MP3, WAV, OGG.
        </AccordionContent>
      </AccordionItem>
      
      <AccordionItem value="item-3" className="border-border/50">
        <AccordionTrigger className="font-mono text-sm hover:text-primary">
          Como exportar meu projeto?
        </AccordionTrigger>
        <AccordionContent className="text-sm text-muted-foreground">
          No menu do projeto, selecione "Exportar" e escolha o formato
          desejado (HTML5, executável Windows, executável Linux, etc). O processo
          de build pode levar alguns minutos dependendo do tamanho do projeto.
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="item-4" className="border-border/50">
        <AccordionTrigger className="font-mono text-sm hover:text-primary">
          Como usar a IA para gerar jogos?
        </AccordionTrigger>
        <AccordionContent className="text-sm text-muted-foreground">
          No painel de chat à esquerda, descreva o jogo que você quer criar.
          Por exemplo: "jogo de nave espacial com asteroides". A IA irá gerar
          automaticamente a especificação do jogo e você poderá visualizar em tempo real.
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="item-5" className="border-border/50">
        <AccordionTrigger className="font-mono text-sm hover:text-primary">
          Quais sistemas estão disponíveis?
        </AccordionTrigger>
        <AccordionContent className="text-sm text-muted-foreground">
          O Ordax Engine possui diversos sistemas modulares: InputSystem, PhysicsSystem,
          CollisionSystem, ParticleSystem, AnimationSystem, AudioSystem, CameraSystem,
          AISystem, SpawnerSystem, ScoreSystem, UISystem, TimerSystem, DialogueSystem,
          InventorySystem e SaveSystem.
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
};
