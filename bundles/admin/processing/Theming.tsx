import * as React from 'react';
import create from 'zustand';

import Moon from '@uikit/icons/Moon';
import Sun from '@uikit/icons/Sun';

import Button from './Button';

const darkThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
const lightThemeQuery = window.matchMedia('(prefers-color-scheme: light)');

function getCurrentColorScheme() {
  if (darkThemeQuery.matches) return 'dark';
  if (lightThemeQuery.matches) return 'light';
  return 'light';
}

interface ThemeStoreState {
  theme: string;
  setTheme(theme: string): void;
}

export const useThemeStore = create<ThemeStoreState>(set => ({
  theme: getCurrentColorScheme(),
  setTheme(theme: string) {
    set({ theme });
  },
}));

export function setCurrentTheme() {
  useThemeStore.getState().setTheme(getCurrentColorScheme());
}

export function toggleTheme() {
  useThemeStore.setState(state => ({
    theme: state.theme === 'dark' ? 'light' : 'dark',
  }));
}

darkThemeQuery.addEventListener('change', setCurrentTheme);
lightThemeQuery.addEventListener('change', setCurrentTheme);

export function ThemeButton({ className }: { className: string }) {
  const store = useThemeStore();

  return (
    <Button className={className} tertiary onClick={toggleTheme} icon={store.theme === 'dark' ? Sun : Moon}>
      Switch Themes
    </Button>
  );
}

export default function ThemeProvider({ children }: React.ComponentProps<'div'>) {
  const store = useThemeStore();

  return <div className={`theme-${store.theme}`}>{children}</div>;
}
