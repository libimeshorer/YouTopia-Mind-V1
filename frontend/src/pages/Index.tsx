import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Mail } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import youtopiaLogo from "@/assets/logos/youtopia-crystal-logo.png";

const Index = () => {
  const [email, setEmail] = useState("");
  const { toast } = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      // Here you would typically send the email to your backend
      toast({
        title: "Thank you!",
        description: "We'll be in touch soon.",
      });
      setEmail("");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-hero">
      <div className="container mx-auto px-6 py-12">
        <div className="max-w-4xl mx-auto text-center space-y-16">
          {/* Logo */}
          <div className="flex justify-center pt-8">
            <div className="relative">
              <div className="absolute inset-0 rounded-3xl blur-3xl" style={{ backgroundColor: 'hsl(25 100% 60% / 0.2)' }} />
              <img 
                src={youtopiaLogo} 
                alt="YouTopia Logo" 
                className="relative w-48 h-48 md:w-64 md:h-64 animate-fade-in"
              />
            </div>
          </div>

          {/* Brand Name */}
          <h1 className="text-6xl md:text-8xl font-semibold tracking-tight animate-fade-in">
            YouTopia
          </h1>

          {/* Tagline */}
          <h2 className="text-2xl md:text-4xl font-medium bg-gradient-primary bg-clip-text text-transparent animate-fade-in">
            Unique brilliance, scaled
          </h2>

          {/* Coming Soon */}
          <div className="py-4 animate-fade-in">
            <span className="inline-block px-8 py-3 text-xl md:text-2xl font-semibold bg-card rounded-full border-2 border-foreground/20" style={{ color: 'hsl(240, 8%, 25%)', textShadow: '0 0 40px hsl(240 10% 10% / 0.6), 0 0 60px hsl(240 10% 10% / 0.4), 0 0 80px hsl(240 10% 10% / 0.2)' }}>
              Coming Soon
            </span>
          </div>

          {/* Contact Form */}
          <div className="max-w-md mx-auto pb-8 animate-fade-in">
            <p className="text-lg text-muted-foreground mb-6">
              Be the first to know when we launch
            </p>
            <form onSubmit={handleSubmit} className="flex gap-3">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-12 text-base bg-card border-2 border-border focus:border-foreground/30 focus-visible:ring-foreground/30"
              />
              <Button 
                type="submit" 
                size="lg"
                className="h-12 px-6 bg-gradient-primary hover:shadow-glow transition-all duration-300"
              >
                <Mail className="w-5 h-5" />
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
