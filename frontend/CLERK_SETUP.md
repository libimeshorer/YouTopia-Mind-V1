# Clerk Authentication Setup

## Step 1: Create Clerk Account

1. Go to https://clerk.com
2. Sign up for a free account
3. Create a new application
4. Choose "React" as your framework

## Step 2: Configure Authentication Methods

In Clerk Dashboard → User & Authentication:

1. **Enable Email/Password:**
   - Go to "Email, Phone, Username"
   - Enable "Email address" and "Password"

2. **Enable Google OAuth:**
   - Go to "Social Connections"
   - Click "Google"
   - Enable it
   - Follow instructions to set up OAuth credentials

## Step 3: Get Your API Keys

1. In Clerk Dashboard → API Keys
2. Copy your **Publishable Key** (starts with `pk_test_...`)

## Step 4: Set Environment Variable

Create `.env.local` file in the `frontend/` directory:

```bash
cd /Users/libimeshorer/PycharmProjects/YouTopia-Mind-V1/frontend
touch .env.local
```

Add your Clerk key:

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_actual_key_here
```

## Step 5: Test It

1. Start dev server:
   ```bash
   npm run dev
   ```

2. Visit http://localhost:8080
3. Click "Sign In" button (top right)
4. Try signing in with email or Google

## Step 6: Configure Redirect URLs

In Clerk Dashboard → Paths:

- **After sign-in:** `/dashboard`
- **After sign-up:** `/dashboard`
- **Sign-in URL:** `/sign-in`
- **Sign-up URL:** `/sign-up`

## What's Been Implemented

✅ Sign In page (`/sign-in`) with email and Google
✅ Sign Up page (`/sign-up`)
✅ Sign In button on landing page (top right)
✅ Protected routes (Dashboard requires authentication)
✅ Dashboard page (basic, ready for clone management)
✅ User button in header (when signed in)

## Next Steps

After authentication works:
1. Build clone management features in Dashboard
2. Connect to backend API
3. Add file upload functionality
4. Add app connections (Slack, Email)


