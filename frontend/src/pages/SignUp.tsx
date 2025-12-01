import { SignUp as ClerkSignUp } from "@clerk/clerk-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import youtopiaLogo from "@/assets/logos/youtopia-crystal-logo.png";

const SignUp = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-hero">
      <div className="container mx-auto px-6 py-12">
        <div className="max-w-md mx-auto">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <Link to={ROUTES.HOME}>
              <img
                src={youtopiaLogo}
                alt="YouTopia Logo"
                className="w-24 h-24 md:w-32 md:h-32"
              />
            </Link>
          </div>

          {/* Sign Up Form */}
          <div className="bg-card/80 backdrop-blur-sm rounded-2xl p-8 border border-border/50 shadow-lg">
            <div className="text-center mb-6">
              <h1 className="text-3xl md:text-4xl font-bold mb-2">Create your account</h1>
              <p className="text-muted-foreground">
                Start building your digital twin today
              </p>
            </div>

            <ClerkSignUp
              appearance={{
                elements: {
                  rootBox: "mx-auto",
                  card: "shadow-none bg-transparent",
                  headerTitle: "hidden",
                  headerSubtitle: "hidden",
                  socialButtonsBlockButton:
                    "bg-card border-2 border-border hover:border-primary/30 hover:bg-card",
                  socialButtonsBlockButtonText: "text-foreground",
                  formButtonPrimary:
                    "bg-gradient-primary hover:shadow-glow transition-all duration-300",
                  formFieldInput:
                    "bg-card border-2 border-border focus:border-foreground/30",
                  footerActionLink: "text-primary hover:text-primary/80",
                },
              }}
              routing="path"
              path="/sign-up"
              signInUrl={ROUTES.SIGN_IN}
            />

            <div className="mt-6 text-center">
              <Link
                to={ROUTES.HOME}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                ← Back to home
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignUp;


