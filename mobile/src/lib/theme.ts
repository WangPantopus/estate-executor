/**
 * Estate Executor OS — Mobile Theme
 *
 * Luxury palette matching the web app: deep navy, warm gold accents,
 * cream surfaces, and premium typography feel.
 */

export const colors = {
  // Primary palette
  primary: "#1a1a2e",
  primaryLight: "#2d2d44",
  gold: "#c5a44e",
  goldLight: "#d4b96a",

  // Surfaces
  background: "#fafaf8",
  surface: "#ffffff",
  surfaceElevated: "#f5f5f0",
  muted: "#f0efe8",

  // Text
  foreground: "#1a1a2e",
  foregroundMuted: "#6b7280",
  foregroundLight: "#9ca3af",

  // Semantic
  success: "#059669",
  successLight: "#d1fae5",
  warning: "#d97706",
  warningLight: "#fef3c7",
  danger: "#dc2626",
  dangerLight: "#fee2e2",
  info: "#2563eb",
  infoLight: "#dbeafe",

  // Borders
  border: "#e5e5dc",
  borderLight: "#f0efe8",

  // Status colors
  statusGreen: "#059669",
  statusAmber: "#d97706",
  statusRed: "#dc2626",

  // White/transparent
  white: "#ffffff",
  black: "#000000",
  transparent: "transparent",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 32,
  "4xl": 40,
  "5xl": 48,
} as const;

export const fontSize = {
  xs: 11,
  sm: 13,
  base: 15,
  lg: 17,
  xl: 20,
  "2xl": 24,
  "3xl": 30,
  "4xl": 36,
} as const;

export const fontWeight = {
  normal: "400" as const,
  medium: "500" as const,
  semibold: "600" as const,
  bold: "700" as const,
};

export const borderRadius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

export const shadow = {
  sm: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  lg: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
} as const;
