import { SignedIn, SignedOut, UserButton } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";

const Header = () => {
  return (
    <header className="absolute top-0 left-0 right-0 z-50 p-6">
      <div className="container mx-auto flex justify-end items-center">
        <SignedOut>
          <Link to={ROUTES.SIGN_IN}>
            <Button
              variant="outline"
              size="sm"
              className="bg-card/80 backdrop-blur-sm border-border/50 hover:bg-card hover:border-primary/30"
            >
              <LogIn className="w-4 h-4 mr-2" />
              Sign In
            </Button>
          </Link>
        </SignedOut>
        <SignedIn>
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-10 h-10",
              },
            }}
          />
        </SignedIn>
      </div>
    </header>
  );
};

export default Header;


