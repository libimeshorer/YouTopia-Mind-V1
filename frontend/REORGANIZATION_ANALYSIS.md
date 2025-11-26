# Frontend Reorganization Analysis

## Issues Found

### 1. **Duplicate Files** ❌
- `src/hooks/use-toast.ts` - Actual implementation
- `src/components/ui/use-toast.ts` - Just re-exports (redundant)
- **Fix**: Remove the one in `components/ui/` and update imports

### 2. **Lock Files** ⚠️
- Both `bun.lockb` and `package-lock.json` exist
- **Fix**: Remove `bun.lockb` (using npm, not bun)

### 3. **Lovable Dependencies** 🧹
- `lovable-tagger` in `package.json` and `vite.config.ts`
- **Fix**: Remove from both files

### 4. **Reference Files in Root** 📁
- `reference.css`, `reference.html`, `referense.js` in project root
- **Fix**: Move to `docs/reference/` or delete if no longer needed

### 5. **Missing Structure** 🏗️
Missing folders for future development:
- `src/api/` - API client
- `src/services/` - Business logic
- `src/types/` - TypeScript types
- `src/constants/` - Constants
- `src/contexts/` - React contexts (for auth, etc.)

### 6. **Inconsistent Styling** 🎨
- `NotFound.tsx` uses inline styles instead of Tailwind
- **Fix**: Convert to Tailwind classes

### 7. **Assets Organization** 🖼️
- Multiple logo files (3 variants)
- Hero images mixed with logos
- **Fix**: Organize into subfolders

## Proposed Structure

```
frontend/
├── src/
│   ├── api/              # NEW: API client
│   │   └── client.ts
│   ├── assets/
│   │   ├── logos/        # NEW: Organize logos
│   │   │   ├── crystal.png
│   │   │   ├── logo.png
│   │   │   └── logo-new.png
│   │   └── images/       # NEW: Organize images
│   │       ├── hero.jpg
│   │       ├── hero-brand-only.jpg
│   │       └── hero-with-white.jpg
│   ├── components/
│   │   ├── ui/           # shadcn/ui components
│   │   ├── layout/       # NEW: Layout components
│   │   └── features/     # NEW: Feature-specific components
│   ├── constants/        # NEW: Constants
│   │   └── routes.ts
│   ├── contexts/         # NEW: React contexts
│   │   └── auth.tsx
│   ├── hooks/            # Custom hooks
│   ├── lib/              # Utilities
│   ├── pages/            # Page components
│   ├── services/         # NEW: Business logic
│   ├── types/            # NEW: TypeScript types
│   └── ...
```

## Action Items

1. ✅ Remove duplicate `use-toast.ts` from `components/ui/`
2. ✅ Remove `bun.lockb`
3. ✅ Remove `lovable-tagger` dependency
4. ✅ Move reference files to `docs/` folder
5. ✅ Reorganize assets into subfolders
6. ✅ Fix `NotFound.tsx` styling
7. ✅ Create missing folder structure
8. ✅ Update imports after reorganization

