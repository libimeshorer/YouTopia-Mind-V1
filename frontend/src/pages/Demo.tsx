import { Button } from "@/components/ui/button";
import { ArrowLeft, Calendar } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect } from "react";

const Demo = () => {
  useEffect(() => {
    // Load Calendly widget script
    const script = document.createElement('script');
    script.src = 'https://assets.calendly.com/assets/external/widget.js';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      // Cleanup script on unmount
      const scripts = document.querySelectorAll('script[src="https://assets.calendly.com/assets/external/widget.js"]');
      scripts.forEach(script => script.remove());
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <header className="mb-12">
          <Link 
            to="/" 
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
          >
            <ArrowLeft size={20} />
            Back to Home
          </Link>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
              <Calendar className="w-6 h-6 text-primary" />
            </div>
            <h1 className="text-4xl md:text-6xl font-bold bg-gradient-primary bg-clip-text text-transparent">
              Book a Demo
            </h1>
          </div>
          <p className="text-xl text-muted-foreground max-w-2xl">
            Schedule a personalized demo to see how our AI clone technology can transform your digital presence.
          </p>
        </header>

        {/* Calendly Integration */}
        <div className="bg-gradient-secondary rounded-2xl p-8 border border-border/50">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold mb-3">What to Expect</h2>
            <ul className="space-y-2 text-muted-foreground">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-primary rounded-full" />
                15-minute personalized walkthrough
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-accent rounded-full" />
                Live demo of AI clone capabilities
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-primary rounded-full" />
                Q&A session tailored to your needs
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-accent rounded-full" />
                Custom implementation strategy
              </li>
            </ul>
          </div>

          {/* Calendly Inline Widget */}
          <div 
            className="calendly-inline-widget rounded-xl overflow-hidden border border-border/20" 
            data-url="https://calendly.com/your-calendly-username/ai-clone-demo"
            style={{ minWidth: '320px', height: '630px' }}
          />
        </div>

        {/* Alternative Contact */}
        <div className="text-center mt-12">
          <p className="text-muted-foreground mb-4">
            Can't find a suitable time? No problem!
          </p>
          <Link to="/process">
            <Button variant="outline" size="lg" className="text-lg px-8 py-6 h-auto">
              Explore the Process Instead
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Demo;