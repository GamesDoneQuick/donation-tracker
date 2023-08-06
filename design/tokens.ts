import { makeColorPalette, makeFontPalette, makeTokens, TokenGenerator } from '@spyrothon/tokens/generator';

const staticColors = {
  white: '#ffffff',
  black: '#1b1f24',
  twitch: '#9146ff',
};

const colors = makeColorPalette({
  ...staticColors,
  'grey.50': '#f6f8fa',
  'grey.100': '#eaeef1',
  'grey.200': '#d2d9de',
  'grey.300': '#b3b9bd',
  'grey.400': '#8f9294',
  'grey.500': '#6b6d6f',
  'grey.600': '#4d4e50',
  'grey.700': '#333435',
  'grey.800': '#232425',
  'grey.900': '#171819',
  'blue.50': '#dff4fb',
  'blue.100': '#bae3f6',
  'blue.200': '#89ccf0',
  'blue.300': '#61b0e8',
  'blue.400': '#528fcf',
  'blue.500': '#416fa8',
  'blue.600': '#315584',
  'blue.700': '#244168',
  'blue.800': '#1e334f',
  'blue.900': '#12243e',
  'teal.50': '#c8fef5',
  'teal.100': '#79f9e7',
  'teal.200': '#47d4c4',
  'teal.300': '#44b3a7',
  'teal.400': '#44938b',
  'teal.500': '#3e726d',
  'teal.600': '#305853',
  'teal.700': '#204440',
  'teal.800': '#123430',
  'teal.900': '#062723',
  'green.50': '#e1f9e0',
  'green.100': '#b6edb3',
  'green.200': '#8ed986',
  'green.300': '#6ebe63',
  'green.400': '#57a047',
  'green.500': '#407c31',
  'green.600': '#306024',
  'green.700': '#214d17',
  'green.800': '#153c0e',
  'green.900': '#0a2c08',
  'yellow.50': '#fffc88',
  'yellow.100': '#f6e367',
  'yellow.200': '#e3c74f',
  'yellow.300': '#cea92c',
  'yellow.400': '#b98a00',
  'yellow.500': '#986912',
  'yellow.600': '#774f02',
  'yellow.700': '#603e01',
  'yellow.800': '#4a2e00',
  'yellow.900': '#392400',
  'orange.50': '#fff1e7',
  'orange.100': '#ffd7bc',
  'orange.200': '#ffb68a',
  'orange.300': '#fb8e5d',
  'orange.400': '#ed6524',
  'orange.500': '#c83f00',
  'orange.600': '#9f2d00',
  'orange.700': '#7e2300',
  'orange.800': '#621c00',
  'orange.900': '#4c1100',
  'red.50': '#fdebea',
  'red.100': '#fbcfcd',
  'red.200': '#f9adac',
  'red.300': '#f88589',
  'red.400': '#f14f58',
  'red.500': '#c6313f',
  'red.600': '#9d1e31',
  'red.700': '#7d1426',
  'red.800': '#620a1e',
  'red.900': '#490518',
  'purple.50': '#feeefc',
  'purple.100': '#f9d3fd',
  'purple.200': '#efb0fc',
  'purple.300': '#e388fb',
  'purple.400': '#cd5ef3',
  'purple.500': '#a343c6',
  'purple.600': '#7b3996',
  'purple.700': '#622a79',
  'purple.800': '#4d1f60',
  'purple.900': '#3b144b',
  'pink.50': '#c8fef5',
  'pink.100': '#79f9e7',
  'pink.200': '#47d4c4',
  'pink.300': '#44b3a7',
  'pink.400': '#44938b',
  'pink.500': '#3e726d',
  'pink.600': '#305853',
  'pink.700': '#204440',
  'pink.800': '#123430',
  'pink.900': '#062723',
});

const tokens = new TokenGenerator({
  themeNames: ['dark', 'light'],
  accentTokens: ['primary', 'background', 'foreground', 'hover', 'active', 'text', 'translucent'],
});

/**
 * Accents
 */
tokens.accent('purple', {
  primary: { dark: colors('purple.400'), light: colors('purple.500') },
  background: { dark: colors('purple.300'), light: colors('purple.500') },
  foreground: { dark: colors('purple.800'), light: colors('purple.50') },
  hover: { dark: colors('purple.400'), light: colors('purple.600') },
  active: { dark: colors('purple.500'), light: colors('purple.700') },
  text: { dark: colors('purple.300'), light: colors('purple.500') },
  translucent: {
    dark: colors('purple.500').alpha(0.15),
    light: colors('purple.600').alpha(0.15),
  },
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
tokens.color('background.primary', { dark: colors('grey.900'), light: colors('white') });
tokens.color('background.primary', { dark: colors('grey.900'), light: colors('white') });
tokens.color('background.secondary', { dark: colors('grey.800'), light: colors('grey.100') });
tokens.color('background.tertiary', { dark: colors('grey.700'), light: colors('grey.200') });
tokens.color('background.accent', { dark: colors('grey.700'), light: colors('grey.50') });
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

tokens.color('border.primary', { dark: colors('grey.400'), light: colors('grey.400') });
tokens.color('border.subtle', {
  dark: colors('white').alpha(0.3),
  light: colors('grey.900').alpha(0.3),
});

tokens.color('control.background', { dark: colors('grey.400'), light: colors('grey.400') });
tokens.color('control.foreground', { dark: colors('white'), light: colors('white') });

tokens.color('interaction.normal', { dark: colors('white'), light: colors('grey.900') });
tokens.color('interaction.hover', { dark: colors('grey.200'), light: colors('grey.800') });
tokens.color('interaction.active', { dark: colors('grey.300'), light: colors('grey.700') });

tokens.color('interactive-normal', { dark: colors('white'), light: colors('grey.900') });
tokens.color('interactive-hover', { dark: colors('grey.200'), light: colors('grey.600') });
tokens.color('interactive-active', { dark: colors('grey.300'), light: colors('grey.500') });
tokens.color('interactive-background-hover', {
  dark: colors('white').alpha(0.1),
  light: colors('grey.900').alpha(0.1),
});
tokens.color('interactive-background-active', {
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

tokens.color('status.accent.primary', {
  dark: 'accent.primary',
  light: 'accent.primary',
});
tokens.color('status.accent.background', {
  dark: 'accent.background',
  light: 'accent.background',
});
tokens.color('status.accent.foreground', {
  dark: 'accent.foreground',
  light: 'accent.foreground',
});
tokens.color('status.accent.hover', { dark: 'accent.hover', light: 'accent.hover' });
tokens.color('status.accent.active', { dark: 'accent.active', light: 'accent.active' });
tokens.color('status.accent.translucent', {
  dark: 'accent.translucent',
  light: 'accent.translucent',
});

tokens.color('status.success.background', {
  dark: colors('green.400'),
  light: colors('green.400'),
});
tokens.color('status.success.foreground', {
  dark: colors('green.50'),
  light: colors('green.50'),
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
  dark: colors('yellow.50'),
  light: colors('yellow.50'),
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
tokens.color('status.info.foreground', { dark: colors('white'), light: colors('teal.50') });
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
  'noto-sans': {
    name: 'Noto Sans',
    importUrl:
      'https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;0,900;1,400;1,600;1,700;1,900',
  },
  barlow: {
    name: 'Barlow',
    importUrl: 'https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,600;1,400;1,600',
  },
});

tokens.fontStack('normal', {
  stack: [fonts('noto-sans'), ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});
tokens.fontStack('accent', {
  stack: [fonts('barlow'), ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});
tokens.fontStack('monospace', {
  stack: ['monospace', ...fallbackFonts],
  weights: { thin: 300, medium: 400, semibold: 600, bold: 700, black: 900 },
});

tokens.space('xxxs', 0.5);
tokens.space('xxs', 1);
tokens.space('xs', 2);
tokens.space('sm', 4);
tokens.space('md', 8);
tokens.space('lg', 16);
tokens.space('xl', 32);
tokens.space('xxl', 48);
tokens.space('xxxl', 6);

tokens.radius('flat', 0);
tokens.radius('minimal', 1);
tokens.radius('normal', 4);
tokens.radius('large', 16);
tokens.radius('full', 9999999);

export default makeTokens({ colors, tokens });
