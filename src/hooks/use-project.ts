import { useState, useEffect } from "react";
import { vfs } from "@/lib/vfs/VirtualFileSystem";
import { bundler } from "@/lib/export/bundler";
import {
  createProject,
  getProject,
  updateProject,
  saveProjectFiles,
  getProjectFiles,
  saveGameSpec,
  getLatestGameSpec,
  type Project,
} from "@/lib/db/projects";
import type { OrdaxSpec } from "@/lib/ordax/types";
import { toast } from "sonner";

export function useProject(projectId?: string) {
  const [project, setProject] = useState<Project | null>(null);
  const [spec, setSpec] = useState<OrdaxSpec | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load project
  useEffect(() => {
    if (!projectId) return;

    setLoading(true);
    Promise.all([
      getProject(projectId),
      getProjectFiles(projectId),
      getLatestGameSpec(projectId),
    ])
      .then(([projectRes, filesRes, specRes]) => {
        if (projectRes.data) {
          setProject(projectRes.data);
        }

        if (filesRes.data) {
          // TODO: Load files into VFS
          console.log("Files loaded:", filesRes.data.length);
        }

        if (specRes.data) {
          setSpec(specRes.data);
        }
      })
      .catch((error) => {
        console.error("Error loading project:", error);
        toast.error("Erro ao carregar projeto");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [projectId]);

  // Create new project
  const create = async (data: {
    name: string;
    description?: string;
    game_type?: string;
  }) => {
    setLoading(true);
    const { data: newProject, error } = await createProject(data);

    if (error) {
      toast.error("Erro ao criar projeto");
      setLoading(false);
      return null;
    }

    setProject(newProject);
    setLoading(false);
    toast.success("Projeto criado!");
    return newProject;
  };

  // Save project
  const save = async () => {
    if (!project) {
      toast.error("Nenhum projeto carregado");
      return;
    }

    setSaving(true);

    try {
      // Save files
      const files = vfs.getAllFiles();
      await saveProjectFiles(project.id, files as any);

      // Save spec
      if (spec) {
        await saveGameSpec(project.id, spec);
      }

      // Update project metadata
      await updateProject(project.id, {
        updated_at: new Date().toISOString(),
      });

      toast.success("Projeto salvo!");
    } catch (error) {
      console.error("Error saving project:", error);
      toast.error("Erro ao salvar projeto");
    } finally {
      setSaving(false);
    }
  };

  // Export project
  const exportProject = async () => {
    if (!spec) {
      toast.error("Nenhum jogo para exportar");
      return;
    }

    toast.info("Exportando projeto...");

    bundler.downloadHTML(spec, {
      projectName: project?.name || "my-game",
      includeAssets: true,
      minify: false,
    });

    toast.success("Projeto exportado!");
  };

  // Update spec
  const updateSpec = (newSpec: OrdaxSpec) => {
    setSpec(newSpec);
  };

  return {
    project,
    spec,
    loading,
    saving,
    create,
    save,
    exportProject,
    updateSpec,
  };
}
