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

## Step 7: Deploy to Vercel

### Setting Environment Variables in Vercel

1. **Go to Vercel Dashboard:**
   - Navigate to your project → **Settings** → **Environment Variables**

2. **Add the Environment Variable:**
   - **Key:** `VITE_CLERK_PUBLISHABLE_KEY`
   - **Value:** Your Clerk publishable key (e.g., `pk_test_...` or `pk_live_...`)
   - **Environment:** Select **Production**, **Preview**, and **Development** (or at least Production and Preview)

3. **Important Notes:**
   - ✅ The variable name must be **exactly** `VITE_CLERK_PUBLISHABLE_KEY` (case-sensitive)
   - ✅ In Vite, only variables prefixed with `VITE_` are exposed to the client
   - ✅ After adding/modifying environment variables, you **must redeploy** for changes to take effect
   - ✅ Vercel does NOT automatically redeploy when you change environment variables

4. **Redeploy:**
   - Go to **Deployments** tab
   - Click the three dots (⋯) on your latest deployment
   - Select **Redeploy** (or push a new commit to trigger a new deployment)

### Troubleshooting Vercel Deployment

**If you see "Authentication is not configured" error:**

1. **Verify the variable is set:**
   - Go to Settings → Environment Variables
   - Confirm `VITE_CLERK_PUBLISHABLE_KEY` exists
   - Check it's set for the correct environment (Production/Preview)

2. **Check the variable value:**
   - Make sure it starts with `pk_test_` or `pk_live_`
   - No extra spaces or quotes
   - Copy the exact value from Clerk Dashboard

3. **Redeploy after setting variables:**
   - Environment variables are only available after a new deployment
   - Old deployments won't have new environment variables

4. **Check build logs:**
   - Go to your deployment → View build logs
   - Look for any errors related to environment variables
   - The build should complete successfully

5. **Check Build Logs in Vercel:**
   - Go to your deployment → View build logs
   - Look for `[Vite Build]` messages
   - ✅ You should see: "VITE_CLERK_PUBLISHABLE_KEY is available during build"
   - ❌ If you see: "VITE_CLERK_PUBLISHABLE_KEY is NOT available during build", the variable isn't being passed to the build process
   - **This is the most important check!** If the variable isn't in the build logs, it won't be in your app

6. **Verify in browser console:**
   - Open your deployed site
   - Open browser DevTools → Console
   - Look for `[Clerk Config]` messages
   - If you see "VITE_CLERK_PUBLISHABLE_KEY is not set", the variable wasn't available during build

7. **Common Issues:**
   - ❌ Variable name typo (e.g., `VITE_CLERK_KEY` instead of `VITE_CLERK_PUBLISHABLE_KEY`)
   - ❌ Variable not set for the environment you're viewing (Preview vs Production)
   - ❌ Forgot to redeploy after adding the variable (most common!)
   - ❌ Variable has extra spaces or quotes around the value
   - ❌ Build cache issue - try "Redeploy" with "Clear Cache" option
   - ❌ Variable was added AFTER the build completed - must redeploy

### Important: Environment Variables are Build-Time Only

⚠️ **Critical Understanding:** In Vite, `VITE_*` environment variables are embedded into your JavaScript bundle **during the build process**. This means:

- ✅ The variable must be available **when Vercel runs `npm run build`**
- ❌ Setting it after the build won't help - you must redeploy
- ✅ Check the **build logs** to verify the variable is available during build
- ✅ If build logs show the variable is missing, it won't work even if it's set in Vercel settings

### If Variable is Set But Not Available During Build

**If you see in build logs: "VITE_CLERK_PUBLISHABLE_KEY is NOT available during build" but you've confirmed it's set in Vercel:**

1. **Double-check the variable name:**
   - Go to Vercel → Settings → Environment Variables
   - Verify it's exactly `VITE_CLERK_PUBLISHABLE_KEY` (no typos, correct case)
   - Look for any trailing spaces in the variable name

2. **Verify environment selection:**
   - Make sure the variable is checked for **Production**, **Preview**, AND **Development**
   - Click "Edit" on the variable to see which environments are selected
   - If you're viewing a Preview deployment, make sure "Preview" is selected

3. **Check Root Directory setting:**
   - Go to Settings → General → Root Directory
   - If Root Directory is set to `frontend`, that's correct
   - Environment variables should still work with a root directory set

4. **Try redeploying with cache cleared:**
   - Go to Deployments → Latest deployment
   - Click the three dots (⋯) → Redeploy
   - **Check the "Clear Build Cache" option** before redeploying
   - This ensures a completely fresh build

5. **Verify in build logs what VITE_ variables are available:**
   - Look for the log line: "All VITE_* env vars: [...]"
   - This shows all environment variables that start with `VITE_`
   - If `VITE_CLERK_PUBLISHABLE_KEY` is not in that list, it's not being passed to the build

6. **Last resort - Delete and re-add the variable:**
   - In Vercel → Settings → Environment Variables
   - Delete `VITE_CLERK_PUBLISHABLE_KEY`
   - Add it again with the exact same name and value
   - Make sure all environments (Production, Preview, Development) are selected
   - Redeploy with cache cleared

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


