import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Edit, Trash2, Play } from "lucide-react";

interface Project {
  id: string;
  name: string;
  status: "active" | "archived" | "draft";
  type: string;
  createdAt: string;
}

const projects: Project[] = [
  { id: "1", name: "Space Shooter", status: "active", type: "shooter", createdAt: "15/01/2024" },
  { id: "2", name: "Platformer Adventure", status: "draft", type: "platformer", createdAt: "20/01/2024" },
  { id: "3", name: "Puzzle Master", status: "active", type: "puzzle", createdAt: "18/01/2024" },
  { id: "4", name: "Racing Fury", status: "archived", type: "racing", createdAt: "10/01/2024" },
];

export const ProjectsTable = () => {
  const getStatusBadge = (status: Project["status"]) => {
    const config = {
      active: { variant: "default" as const, className: "bg-neon-green/20 text-neon-green border-neon-green/40" },
      draft: { variant: "secondary" as const, className: "bg-neon-orange/20 text-neon-orange border-neon-orange/40" },
      archived: { variant: "outline" as const, className: "bg-muted/20" },
    };

    const { variant, className } = config[status];

    return (
      <Badge variant={variant} className={`${className} font-mono text-xs`}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="glass-panel rounded-lg border border-border/50">
      <Table>
        <TableCaption className="font-mono text-xs">Lista de projetos</TableCaption>
        <TableHeader>
          <TableRow className="border-border/50">
            <TableHead className="font-mono text-xs">Nome</TableHead>
            <TableHead className="font-mono text-xs">Tipo</TableHead>
            <TableHead className="font-mono text-xs">Status</TableHead>
            <TableHead className="font-mono text-xs">Criado em</TableHead>
            <TableHead className="text-right font-mono text-xs">Ações</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {projects.map((project) => (
            <TableRow key={project.id} className="border-border/50">
              <TableCell className="font-medium font-mono">{project.name}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{project.type}</TableCell>
              <TableCell>{getStatusBadge(project.status)}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{project.createdAt}</TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Play className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
