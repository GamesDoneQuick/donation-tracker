import fs from 'fs';
import path from 'path';
import { formatters, generators, source } from '@spyrothon/tokens/generator';

import definitions from './tokens';

const TARGET_DIR = path.resolve(__dirname, './generated');
fs.mkdirSync(TARGET_DIR, { recursive: true });

const files = {
  CSS: {
    COLORS: 'colors.css',
    THEMES: 'themes.css',
    FONTS: 'fonts.css',
    SPACING: 'spacing.css',
    RADII: 'radii.css',
  },
  CSS_SYSTEM: 'system.css',

  TS: {
    COLORS: 'Colors.tsx',
    THEMES: 'Themes.tsx',
    TOKENS: 'Tokens.tsx',
  },
};

const prettier = { formatter: formatters.runPrettier };

source(definitions)
  .out(path.join(TARGET_DIR, files.CSS.COLORS), generators.CSS.generateColors, prettier)
  .out(path.join(TARGET_DIR, files.CSS.THEMES), generators.CSS.generateThemeColors, prettier)
  .out(path.join(TARGET_DIR, files.CSS.FONTS), generators.CSS.generateFonts, prettier)
  .out(path.join(TARGET_DIR, files.CSS.SPACING), generators.CSS.generateSpacing, prettier)
  .out(path.join(TARGET_DIR, files.CSS.RADII), generators.CSS.generateRadii, prettier)
  .out(path.join(TARGET_DIR, files.CSS_SYSTEM), () => generators.CSS.generateSystem(Object.values(files.CSS)), {
    formatter: formatters.runPrettier,
  })
  .out(path.join(TARGET_DIR, files.TS.THEMES), generators.TypeScript.generateThemes, prettier)
  .out(path.join(TARGET_DIR, files.TS.TOKENS), generators.TypeScript.generateTokens, prettier)
  .flow();
