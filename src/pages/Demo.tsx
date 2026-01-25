import { VisualShowcase } from "@/components/demo/VisualShowcase";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

const Demo = () => {
  return (
    <div className="min-h-screen">
      <div className="fixed top-4 left-4 z-50">
        <Link to="/">
          <Button variant="outline" className="glass-panel border-border/50 hover:border-primary/30">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Workspace
          </Button>
        </Link>
      </div>
      <VisualShowcase />
    </div>
  );
};

export default Demo;
