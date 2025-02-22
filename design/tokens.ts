import { makeFontPalette, makeTokens, TokenGenerator } from '@faulty/tokens/generator';
import { colors } from './colors';

const tokens = new TokenGenerator({
  themeNames: ['dark', 'light'],
  accentTokens: ['primary', 'background', 'foreground', 'hover', 'active', 'text', 'translucent'],
});

/**
 * Accents
 */
tokens.accent('red', {
  primary: { dark: colors('red.400'), light: colors('red.500') },
  background: { dark: colors('red.300'), light: colors('red.500') },
  foreground: { dark: colors('red.800'), light: colors('red.50') },
  hover: { dark: colors('red.400'), light: colors('red.600') },
  active: { dark: colors('red.500'), light: colors('red.700') },
  text: { dark: colors('red.300'), light: colors('red.500') },
  translucent: { dark: colors('red.500').alpha(0.15), light: colors('red.600').alpha(0.15) },
});

tokens.accent('blue', {
  primary: { dark: colors('blue.400'), light: colors('blue.500') },
  background: { dark: colors('blue.300'), light: colors('blue.500') },
  foreground: { dark: colors('blue.800'), light: colors('blue.50') },
  hover: { dark: colors('blue.400'), light: colors('blue.600') },
  active: { dark: colors('blue.500'), light: colors('blue.700') },
  text: { dark: colors('blue.300'), light: colors('blue.500') },
  translucent: { dark: colors('blue.500').alpha(0.15), light: colors('blue.600').alpha(0.15) },
});

/**
 * Colors
 */
tokens.color('background.primary', { dark: colors('grey.1100'), light: colors('white') });
tokens.color('background.secondary', { dark: colors('grey.1000'), light: colors('grey.100') });
tokens.color('background.tertiary', { dark: colors('grey.800'), light: colors('grey.200') });
tokens.color('background.accent', { dark: colors('grey.900'), light: colors('grey.50') });
tokens.color('background.floating', { dark: colors('grey.900'), light: colors('white') });
tokens.color('background.mod.subtle', {
  dark: colors('black').alpha(0.1),
  light: colors('grey.900').alpha(0.1),
});
tokens.color('background.mod.backdrop', {
  dark: colors('black').alpha(0.7),
  light: colors('grey.900').alpha(0.7),
});
tokens.color('background.highlight', {
  dark: colors('grey.100').alpha(0.1),
  light: colors('grey.900').alpha(0.1),
});

tokens.color('border.primary', {
  dark: colors('white').alpha(0.5),
  light: colors('grey.900').alpha(0.5),
});
tokens.color('border.subtle', {
  dark: colors('white').alpha(0.3),
  light: colors('grey.900').alpha(0.3),
});

tokens.color('control.background', { dark: colors('grey.400'), light: colors('grey.400') });
tokens.color('control.foreground', { dark: colors('white'), light: colors('white') });

tokens.color('interactive.normal', { dark: colors('white'), light: colors('grey.900') });
tokens.color('interactive.hover', { dark: colors('grey.200'), light: colors('grey.600') });
tokens.color('interactive.active', { dark: colors('grey.300'), light: colors('grey.500') });
tokens.color('interactive.background.hover', {
  dark: colors('white').alpha(0.1),
  light: colors('grey.900').alpha(0.1),
});
tokens.color('interactive.background.active', {
  dark: colors('white').alpha(0.15),
  light: colors('grey.900').alpha(0.15),
});

tokens.color('text.normal', { dark: colors('grey.100'), light: colors('grey.900') });
tokens.color('text.secondary', { dark: colors('grey.400'), light: colors('grey.400') });
tokens.color('text.success', { dark: colors('green.400'), light: colors('green.500') });
tokens.color('text.info', { dark: colors('teal.300'), light: colors('teal.500') });
tokens.color('text.warning', { dark: colors('yellow.400'), light: colors('yellow.500') });
tokens.color('text.danger', { dark: colors('red.400'), light: colors('red.500') });
tokens.color('text.default', { dark: colors('grey.100'), light: colors('grey.900') });
tokens.color('text.accent', { dark: 'accent.text', light: 'accent.text' });
tokens.color('text.link', { dark: 'accent.text', light: 'accent.text' });

tokens.color('status.success.background', {
  dark: colors('green.400'),
  light: colors('green.400'),
});
tokens.color('status.success.foreground', {
  dark: colors('green.100'),
  light: colors('green.100'),
});
tokens.color('status.success.hover', { dark: colors('green.500'), light: colors('green.500') });
tokens.color('status.success.active', {
  dark: colors('green.600'),
  light: colors('green.500'),
});
tokens.color('status.success.translucent', {
  dark: colors('green.600').alpha(0.15),
  light: colors('green.600').alpha(0.15),
});

tokens.color('status.warning.background', {
  dark: colors('yellow.400'),
  light: colors('yellow.400'),
});
tokens.color('status.warning.foreground', {
  dark: colors('yellow.100'),
  light: colors('yellow.100'),
});
tokens.color('status.warning.hover', {
  dark: colors('yellow.500'),
  light: colors('yellow.600'),
});
tokens.color('status.warning.active', {
  dark: colors('yellow.600'),
  light: colors('yellow.500'),
});
tokens.color('status.warning.translucent', {
  dark: colors('yellow.500').alpha(0.15),
  light: colors('yellow.600').alpha(0.15),
});

tokens.color('status.danger.background', { dark: colors('red.500'), light: colors('red.500') });
tokens.color('status.danger.foreground', { dark: colors('red.50'), light: colors('red.50') });
tokens.color('status.danger.hover', { dark: colors('red.600'), light: colors('red.600') });
tokens.color('status.danger.active', { dark: colors('red.700'), light: colors('red.500') });
tokens.color('status.danger.translucent', {
  dark: colors('red.600').alpha(0.15),
  light: colors('red.600').alpha(0.15),
});

tokens.color('status.info.background', { dark: colors('teal.400'), light: colors('teal.500') });
tokens.color('status.info.foreground', { dark: colors('white'), light: colors('teal.100') });
tokens.color('status.info.hover', { dark: colors('teal.500'), light: colors('teal.600') });
tokens.color('status.info.active', { dark: colors('teal.600'), light: colors('teal.500') });
tokens.color('status.info.translucent', {
  dark: colors('teal.500').alpha(0.15),
  light: colors('teal.600').alpha(0.15),
});

tokens.color('status.default.background', {
  dark: colors('grey.500'),
  light: colors('grey.500'),
});
tokens.color('status.default.foreground', {
  dark: colors('grey.50'),
  light: colors('grey.50'),
});
tokens.color('status.default.hover', { dark: colors('grey.600'), light: colors('grey.600') });
tokens.color('status.default.active', { dark: colors('grey.700'), light: colors('grey.500') });
tokens.color('status.default.translucent', {
  dark: colors('grey.500').alpha(0.2),
  light: colors('grey.600').alpha(0.3),
});

/**
 * Fonts
 */
const fallbackFonts = [
  '-apple-system',
  'BlinkMacSystemFont',
  'avenir next',
  'avenir',
  'helvetica neue',
  'helvetica',
  'Ubuntu',
  'roboto',
  'noto',
  'segoe ui',
  'arial',
  'sans-serif',
];

const fonts = makeFontPalette({
  dosis: {
    name: 'Dosis',
    source: 'google',
    importUrl: 'https://fonts.googleapis.com/css2?family=Dosis:wght@400;700',
    weight: [400, 700],
    style: ['normal'],
    subsets: ['latin'],
    display: 'swap',
  },
  noto: {
    name: 'Noto Sans',
    source: 'google',
    importUrl: 'https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,700;0,900;1,400;1,700;1,900',
    weight: [400, 700, 900],
    style: ['normal', 'italic'],
    subsets: ['latin'],
    display: 'swap',
  },
});

tokens.fontStack('normal', {
  stack: [fonts('noto'), ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});
tokens.fontStack('accent', {
  stack: [fonts('dosis'), ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});
tokens.fontStack('monospace', {
  stack: ['monospace', ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});

/**
 * Spaces
 */
tokens.space('xxxs', 0.5);
tokens.space('xxs', 1);
tokens.space('xs', 2);
tokens.space('sm', 4);
tokens.space('md', 8);
tokens.space('lg', 16);
tokens.space('xl', 32);
tokens.space('xxl', 48);
tokens.space('xxxl', 6);

/**
 * Radii
 */
tokens.radius('flat', 0);
tokens.radius('minimal', 2);
tokens.radius('normal', 4);
tokens.radius('large', 8);
tokens.radius('xlarge', 16);
tokens.radius('full', 9999999);

/**
 * Shadows
 */
tokens.shadow('low', {
  dark: [
    '0px 0.2px 0.5px rgba(0, 0, 0, 0.077)',
    '0px 0.5px 1.5px rgba(0, 0, 0, 0.11)',
    '0px 1.2px 3.6px rgba(0, 0, 0, 0.143)',
    '0px 4px 12px rgba(0, 0, 0, 0.22)',
  ],
  light: [
    '0px 0.1px 0.3px rgba(0, 0, 0, 0.042)',
    '0px 0.3px 0.8px rgba(0, 0, 0, 0.06)',
    '0px 0.6px 1.8px rgba(0, 0, 0, 0.078)',
    '0px 2px 6px rgba(0, 0, 0, 0.12)',
  ],
});
tokens.shadow('medium', {
  dark: [
    '0px 0.2px 0.9px rgba(0, 0, 0, 0.115)',
    '0px 0.5px 2.5px rgba(0, 0, 0, 0.165)',
    '0px 1.2px 6px rgba(0, 0, 0, 0.215)',
    '0px 4px 20px rgba(0, 0, 0, 0.33)',
  ],
  light: [
    '0px 0.1px 0.5px rgba(0, 0, 0, 0.056)',
    '0px 0.3px 1.5px rgba(0, 0, 0, 0.08)',
    '0px 0.6px 3.6px rgba(0, 0, 0, 0.104)',
    '0px 2px 12px rgba(0, 0, 0, 0.16)',
  ],
});
tokens.shadow('high', {
  dark: [
    '0px 0.2px 1.4px rgba(0, 0, 0, 0.157)',
    '0px 0.5px 4px rgba(0, 0, 0, 0.225)',
    '0px 1.2px 9.6px rgba(0, 0, 0, 0.293)',
    '0px 4px 32px rgba(0, 0, 0, 0.45)',
  ],
  light: [
    '0px 0.2px 0.7px rgba(0, 0, 0, 0.066)',
    '0px 0.5px 2px rgba(0, 0, 0, 0.095)',
    '0px 1.2px 4.8px rgba(0, 0, 0, 0.124)',
    '0px 4px 16px rgba(0, 0, 0, 0.19)',
  ],
});

export default makeTokens({ colors, tokens });
