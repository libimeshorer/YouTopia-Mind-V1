import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Bot, Brain, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

const Process = () => {
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
          <h1 className="text-4xl md:text-6xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-4">
            How It Works
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl">
            Building your AI clone is a simple 3-step process that transforms your personality into an intelligent digital companion.
          </p>
        </header>

        {/* Process Steps */}
        <div className="grid gap-8 md:gap-12 mb-16">
          {/* Step 1 */}
          <Card className="p-8 bg-gradient-secondary border-border/50 hover:border-primary/30 transition-all duration-300">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0 w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                <Brain className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h3 className="text-2xl font-semibold mb-4 flex items-center gap-3">
                  <span className="text-primary font-mono">01.</span>
                  Personality Analysis
                </h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  We'll analyze your communication patterns, preferences, and personality traits through interactive questionnaires and conversation samples to understand your unique voice.
                </p>
              </div>
            </div>
          </Card>

          {/* Step 2 */}
          <Card className="p-8 bg-gradient-secondary border-border/50 hover:border-primary/30 transition-all duration-300">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0 w-16 h-16 rounded-full bg-accent/20 flex items-center justify-center">
                <Bot className="w-8 h-8 text-accent" />
              </div>
              <div>
                <h3 className="text-2xl font-semibold mb-4 flex items-center gap-3">
                  <span className="text-accent font-mono">02.</span>
                  AI Training
                </h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Our advanced AI models learn from your data to replicate your speaking style, decision-making patterns, and personality quirks, creating a digital version of you.
                </p>
              </div>
            </div>
          </Card>

          {/* Step 3 */}
          <Card className="p-8 bg-gradient-secondary border-border/50 hover:border-primary/30 transition-all duration-300">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0 w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h3 className="text-2xl font-semibold mb-4 flex items-center gap-3">
                  <span className="text-primary font-mono">03.</span>
                  Clone Deployment
                </h3>
                <p className="text-muted-foreground text-lg leading-relaxed">
                  Once trained, your AI clone is ready to interact, make decisions, and represent you in digital spaces while maintaining your authentic personality and values.
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <div className="bg-gradient-hero rounded-2xl p-8 md:p-12 border border-border/50">
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Ready to Create Your Digital Twin?
            </h2>
            <p className="text-muted-foreground text-lg mb-8 max-w-2xl mx-auto">
              The process typically takes 15-30 minutes and results in a sophisticated AI that thinks and responds just like you.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button variant="gradient" size="lg" className="text-lg px-8 py-6 h-auto">
                Let's Start!
              </Button>
              <Link to="/demo">
                <Button variant="outline" size="lg" className="text-lg px-8 py-6 h-auto border-border/50 hover:border-accent/50">
                  Book a Demo First
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Process;