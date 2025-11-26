# Deployment Guide: you-topia.ai

## Recommended: Vercel (Easiest & Best for React/Vite)

Vercel is the best option because:
- ✅ Automatic deployments from Git (push to main = deploy)
- ✅ Free tier with custom domains
- ✅ Built-in SSL certificates
- ✅ Fast global CDN
- ✅ Preview deployments for PRs
- ✅ Zero configuration needed for Vite

## Setup Steps

### 1. Push Code to GitHub

Make sure your code is pushed to GitHub:

```bash
cd /Users/libimeshorer/PycharmProjects/YouTopia-Mind-V1
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### 2. Deploy to Vercel

**Option A: Via Vercel Dashboard (Recommended)**

1. Go to [vercel.com](https://vercel.com) and sign up/login
2. Click "Add New Project"
3. Import your GitHub repository: `libimeshorer/YouTopia-Mind-V1`
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
5. Click "Deploy"

**Option B: Via Vercel CLI**

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy (from project root)
cd /Users/libimeshorer/PycharmProjects/YouTopia-Mind-V1
vercel

# Follow prompts:
# - Set root directory to: frontend
# - Override settings? No
```

### 3. Connect Custom Domain

1. In Vercel dashboard, go to your project → Settings → Domains
2. Add domain: `you-topia.ai`
3. Add `www.you-topia.ai` (optional)
4. Vercel will show DNS records to add

### 4. Update DNS Records

In your domain registrar (where you bought you-topia.ai):

**Add these DNS records:**

```
Type: A
Name: @
Value: 76.76.21.21

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

Or use the exact values Vercel provides (they may vary).

### 5. Wait for DNS Propagation

- Usually takes 5-60 minutes
- Vercel will automatically issue SSL certificate
- You'll get an email when it's ready

## Automatic Deployments

Once set up:
- **Every push to `main` branch** → Automatic production deployment
- **Every PR** → Preview deployment (get a unique URL)
- **Deployments are instant** (usually < 2 minutes)

## Alternative: Netlify

If you prefer Netlify:

1. Go to [netlify.com](https://netlify.com)
2. Connect GitHub repository
3. Build settings:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/dist`
4. Add custom domain: `you-topia.ai`

## Alternative: AWS Amplify

If you want everything on AWS:

1. Go to AWS Amplify Console
2. Connect GitHub repository
3. Build settings:
   - App root: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
4. Add custom domain

## Environment Variables

If you need environment variables (for API URLs, etc.):

1. In Vercel dashboard → Settings → Environment Variables
2. Add variables:
   - `VITE_API_URL` = `https://api.you-topia.ai` (or your backend URL)
   - Any other variables starting with `VITE_`

## Testing Production Build Locally

Before deploying, test the production build:

```bash
cd frontend
npm run build
npm run preview
```

Visit http://localhost:4173 to see production build.

## Troubleshooting

### Build Fails
- Check build logs in Vercel dashboard
- Ensure all dependencies are in `package.json`
- Check for TypeScript errors: `npm run lint`

### Domain Not Working
- Wait 24-48 hours for DNS propagation
- Check DNS records are correct
- Verify SSL certificate is issued (Vercel does this automatically)

### Assets Not Loading
- Ensure assets are in `public/` folder (they'll be copied automatically)
- Check paths use relative URLs, not absolute

## Quick Deploy Checklist

- [ ] Code pushed to GitHub
- [ ] Vercel account created
- [ ] Project imported from GitHub
- [ ] Root directory set to `frontend`
- [ ] Build settings configured
- [ ] Custom domain added
- [ ] DNS records updated
- [ ] SSL certificate issued (automatic)
- [ ] Site accessible at you-topia.ai

