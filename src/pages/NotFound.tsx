import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Home, Sparkles } from "lucide-react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="glass-panel neon-glow max-w-lg w-full">
        <CardHeader className="text-center">
          <CardTitle className="text-6xl font-bold neon-text mb-4">404</CardTitle>
          <CardDescription className="text-lg">
            Page not found
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-muted-foreground">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <div className="flex gap-2">
            <Link to="/" className="flex-1">
              <Button className="w-full neon-glow">
                <Home className="mr-2 h-4 w-4" />
                Go Home
              </Button>
            </Link>
            <Link to="/workspace" className="flex-1">
              <Button variant="outline" className="w-full glass-panel">
                <Sparkles className="mr-2 h-4 w-4" />
                Workspace
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotFound;
