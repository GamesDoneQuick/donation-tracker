import { createAppContainer, createThemeContext } from '@spyrothon/sparx';

import { tokens } from '../../design/generated/Tokens';

const themeContext = createThemeContext(tokens);
const AppContainer = createAppContainer(themeContext);

const { ThemeContext, ThemeProvider, getThemeClass } = themeContext;
export { AppContainer, ThemeContext, ThemeProvider, getThemeClass };
