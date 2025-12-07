/**
 * Application route constants
 */
export const ROUTES = {
  HOME: "/",
  PROCESS: "/process",
  DEMO: "/demo",
  DASHBOARD: "/dashboard",
  SIGN_IN: "/sign-in",
  SIGN_UP: "/sign-up",
  SETUP: "/setup",
  TRAINING: "/training",
  ACTIVITY: "/activity",
  CLONE: (id: string) => `/clone/${id}`,
  SETUP_CLONE: (id: string) => `/setup/${id}`,
} as const;

