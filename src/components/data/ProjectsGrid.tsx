import { ProjectCard } from "./ProjectCard";

const mockProjects = [
  {
    name: "Space Shooter",
    description: "Um jogo de nave espacial com gráficos neon e física realista",
    tags: ["shooter", "arcade", "2D"],
    createdAt: "15/01/2024",
    views: 234,
  },
  {
    name: "Platformer Adventure",
    description: "Jogo de plataforma com mecânicas inovadoras e level design criativo",
    tags: ["platformer", "adventure"],
    createdAt: "20/01/2024",
    views: 156,
  },
  {
    name: "Puzzle Master",
    description: "Quebra-cabeças desafiadores com progressão de dificuldade",
    tags: ["puzzle", "casual"],
    createdAt: "18/01/2024",
    views: 89,
  },
  {
    name: "Racing Fury",
    description: "Corrida de alta velocidade com customização de veículos",
    tags: ["racing", "multiplayer"],
    createdAt: "22/01/2024",
    views: 312,
  },
  {
    name: "RPG Quest",
    description: "RPG com sistema de combate por turnos e história envolvente",
    tags: ["rpg", "story"],
    createdAt: "10/01/2024",
    views: 445,
  },
  {
    name: "Tower Defense",
    description: "Defenda sua base contra ondas de inimigos",
    tags: ["strategy", "tower-defense"],
    createdAt: "25/01/2024",
    views: 178,
  },
];

export const ProjectsGrid = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {mockProjects.map((project, index) => (
        <ProjectCard key={index} {...project} />
      ))}
    </div>
  );
};
