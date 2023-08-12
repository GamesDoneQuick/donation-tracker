/** Generated file. Do not edit manually */

import { Accent, Accents, rawColors, resolveThemeColorToken, Theme, Themes, themeTokens as colors } from './Themes';

const tokens = {
  rawColors,
  colors,
  themes: Themes,
  accents: Accents,
  resolveThemeColorToken,
} as const;

export type Tokens = typeof tokens;

export { tokens };
export type { Accent, Theme };
