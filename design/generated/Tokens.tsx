/** Generated file. Do not edit manually */

import {
  Accent,
  Accents,
  rawColors,
  resolveThemeColorToken,
  resolveThemeShadowToken,
  Theme,
  Themes,
  themeTokens as colors,
} from './Themes';

const tokens = {
  rawColors,
  colors,
  themes: Themes,
  accents: Accents,
  resolveThemeColorToken,
  resolveThemeShadowToken,
} as const;

export type Tokens = typeof tokens;

export { Accents, Themes, tokens };
export type { Accent, Theme };
