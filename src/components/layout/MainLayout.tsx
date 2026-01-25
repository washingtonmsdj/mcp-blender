import { ReactNode } from "react";
import { Header } from "./Header";

interface MainLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
}

export const MainLayout = ({ children, sidebar }: MainLayoutProps) => {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        {sidebar && sidebar}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
