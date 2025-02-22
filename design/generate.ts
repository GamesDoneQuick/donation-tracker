import fs from 'fs';
import path from 'path';

import { formatters, generators, source } from '@faulty/tokens/generator';
import definitions from './tokens';

const TARGET_DIR = path.resolve(__dirname, './generated');
fs.mkdirSync(TARGET_DIR, { recursive: true });

const files = {
  CSS: {
    COLORS: 'colors.css',
    THEMES: 'themes.css',
    FONTS: 'fonts.css',
    FONT_IMPORTS: 'fontImports.css',
    SPACING: 'spacing.css',
    RADII: 'radii.css',
  },
  CSS_SYSTEM: 'system.css',

  TS: {
    THEMES: 'themes.tsx',
    TOKENS: 'tokens.tsx',
    FONTS_NEXT: 'fonts.tsx',
  },
};

// The System intentionally does not include font _imports_, because these
// should be managed by the application directly depending on the context.
// NextJS projects can use the `fonts.tsx` file to automatically use `next/font`
// for loading, while SPAs can use `fontImports.css` to get CSS imports instead.
const CSS_SYSTEM_FILES = [files.CSS.COLORS, files.CSS.FONTS, files.CSS.RADII, files.CSS.SPACING, files.CSS.THEMES];

const prettier = { formatter: formatters.runPrettier };

source(definitions)
  .out(path.join(TARGET_DIR, files.CSS.COLORS), generators.CSS.generateColors, prettier)
  .out(path.join(TARGET_DIR, files.CSS.THEMES), generators.CSS.generateThemes, prettier)
  .out(path.join(TARGET_DIR, files.CSS.FONTS), generators.CSS.generateFonts, prettier)
  .out(path.join(TARGET_DIR, files.CSS.FONT_IMPORTS), generators.CSS.generateFontImports, prettier)
  .out(path.join(TARGET_DIR, files.CSS.SPACING), generators.CSS.generateSpacing, prettier)
  .out(path.join(TARGET_DIR, files.CSS.RADII), generators.CSS.generateRadii, prettier)
  .out(path.join(TARGET_DIR, files.CSS_SYSTEM), () => generators.CSS.generateSystem(CSS_SYSTEM_FILES), {
    formatter: formatters.runPrettier,
  })
  .out(path.join(TARGET_DIR, files.TS.THEMES), generators.TypeScript.generateThemes, prettier)
  .out(path.join(TARGET_DIR, files.TS.TOKENS), generators.TypeScript.generateTokens, prettier)
  // NOTE: Next Fonts doesn't let you name the font in the font-face declaration,
  // meaning it can't be mapped to how consumers define them in their tokens. It'd
  // be nice to be able to use this, but right now it's just not possible.
  // Use `fontImports.css` in your code instead.
  // .out(
  //   path.join(TARGET_DIR, files.TS.FONTS_NEXT),
  //   generators.TypeScript.generateNextFonts,
  //   prettier,
  // )
  .flow();
