import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

// Schema de validação
const formSchema = z.object({
  name: z.string().min(3, "Nome deve ter no mínimo 3 caracteres"),
  type: z.string().min(1, "Selecione um tipo"),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

export const ProjectForm = () => {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      type: "",
      description: "",
    },
  });

  const onSubmit = async (data: FormValues) => {
    try {
      console.log(data);
      toast.success("Projeto criado com sucesso!");
      form.reset();
    } catch (error) {
      toast.error("Erro ao criar projeto");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Nome */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="font-mono text-sm">Nome do Projeto</FormLabel>
              <FormControl>
                <Input 
                  placeholder="Meu Jogo Incrível" 
                  className="glass-panel font-mono" 
                  {...field} 
                />
              </FormControl>
              <FormDescription className="text-xs">
                Nome único para identificar seu projeto
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Tipo */}
        <FormField
          control={form.control}
          name="type"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="font-mono text-sm">Tipo de Jogo</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger className="glass-panel font-mono">
                    <SelectValue placeholder="Selecione um tipo" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent className="glass-panel">
                  <SelectItem value="platformer">Platformer</SelectItem>
                  <SelectItem value="shooter">Shooter</SelectItem>
                  <SelectItem value="puzzle">Puzzle</SelectItem>
                  <SelectItem value="racing">Racing</SelectItem>
                  <SelectItem value="rpg">RPG</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Descrição */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="font-mono text-sm">Descrição</FormLabel>
              <FormControl>
                <Textarea 
                  placeholder="Descreva seu projeto..."
                  className="resize-none glass-panel font-mono text-sm"
                  rows={4}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Botões */}
        <div className="flex gap-4">
          <Button type="submit" className="flex-1 neon-glow">
            Criar Projeto
          </Button>
          <Button 
            type="button" 
            variant="outline" 
            className="glass-panel"
            onClick={() => form.reset()}
          >
            Limpar
          </Button>
        </div>
      </form>
    </Form>
  );
};
