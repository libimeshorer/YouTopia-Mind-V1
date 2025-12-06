import { useUser } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Plus, Bot } from "lucide-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import Header from "@/components/layout/Header";

const Dashboard = () => {
  const { user } = useUser();

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-24">
        <div className="max-w-6xl mx-auto">
          {/* Welcome Section */}
          <div className="mb-12">
            <h1 className="text-4xl md:text-6xl font-bold mb-4">
              Welcome back, {user?.firstName || user?.emailAddresses[0]?.emailAddress}!
            </h1>
            <p className="text-xl text-muted-foreground">
              Manage your digital twins and create new ones
            </p>
          </div>

          {/* Clones Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold">Your Clones</h2>
              <Button size="lg" className="bg-gradient-primary hover:shadow-glow">
                <Plus className="w-5 h-5 mr-2" />
                Create New Clone
              </Button>
            </div>

            {/* Empty State */}
            <Card className="p-12 text-center border-border/50 bg-gradient-secondary">
              <div className="flex justify-center mb-6">
                <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="w-10 h-10 text-primary" />
                </div>
              </div>
              <h3 className="text-2xl font-semibold mb-3">No clones yet</h3>
              <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                Create your first digital twin to get started. Upload your data, connect your apps, and train your AI clone.
              </p>
              <Button size="lg" className="bg-gradient-primary hover:shadow-glow">
                <Plus className="w-5 h-5 mr-2" />
                Create Your First Clone
              </Button>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="grid md:grid-cols-3 gap-6">
            <Card className="p-6 border-border/50 hover:border-primary/30 transition-all">
              <h3 className="font-semibold mb-2">Upload Documents</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add PDFs, Word docs, and text files to train your clone
              </p>
              <Button variant="outline" size="sm" className="w-full">
                Upload Files
              </Button>
            </Card>

            <Card className="p-6 border-border/50 hover:border-primary/30 transition-all">
              <h3 className="font-semibold mb-2">Connect Apps</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Link Slack, email, and other services to your clone
              </p>
              <Button variant="outline" size="sm" className="w-full">
                Connect Apps
              </Button>
            </Card>

            <Card className="p-6 border-border/50 hover:border-primary/30 transition-all">
              <h3 className="font-semibold mb-2">Start Interview</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Use our AI interviewer to collect initial data
              </p>
              <Button variant="outline" size="sm" className="w-full" disabled>
                Coming Soon
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;




