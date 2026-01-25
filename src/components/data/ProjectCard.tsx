import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Eye, Edit, Play } from "lucide-react";

interface ProjectCardProps {
  name: string;
  description: string;
  tags: string[];
  createdAt: string;
  views: number;
}

export const ProjectCard = ({ 
  name, 
  description, 
  tags, 
  createdAt, 
  views 
}: ProjectCardProps) => {
  return (
    <Card className="glass-panel hover:neon-glow transition-all duration-300 group">
      <CardHeader>
        <CardTitle className="group-hover:neon-text transition-all font-bold">
          {name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground line-clamp-2">
          {description}
        </p>
        
        {/* Tags */}
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="font-mono text-xs">
              {tag}
            </Badge>
          ))}
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {createdAt}
          </div>
          <div className="flex items-center gap-1">
            <Eye className="h-3 w-3" />
            {views}
          </div>
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button className="flex-1 neon-glow">
          <Play className="h-4 w-4 mr-2" />
          Abrir
        </Button>
        <Button variant="outline" className="flex-1 glass-panel">
          <Edit className="h-4 w-4 mr-2" />
          Editar
        </Button>
      </CardFooter>
    </Card>
  );
};
