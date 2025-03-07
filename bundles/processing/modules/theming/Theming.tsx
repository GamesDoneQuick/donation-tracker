import React from 'react';
import create from 'zustand';
import { persist } from 'zustand/middleware';
import { Button } from '@faulty/gdq-design';

import Moon from '@uikit/icons/Moon';
import Sun from '@uikit/icons/Sun';

import { Accent, Theme } from '../../../../design/generated/Themes';

const darkThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
const lightThemeQuery = window.matchMedia('(prefers-color-scheme: light)');

function getCurrentColorScheme() {
  if (darkThemeQuery.matches) return 'dark';
  if (lightThemeQuery.matches) return 'light';
  return 'light';
}

interface ThemeStoreState {
  theme: Theme;
  accent: Accent;
  setTheme(theme: Theme): void;
}

export const useThemeStore = create<ThemeStoreState>()(
  persist(
    set => ({
      theme: getCurrentColorScheme(),
      accent: 'blue',
      setTheme(theme: Theme) {
        set({ theme });
      },
      setAccent(accent: Accent) {
        set({ accent });
      },
    }),
    {
      name: 'processing-theme',
    },
  ),
);

export function setCurrentThemeFromQuery() {
  useThemeStore.getState().setTheme(getCurrentColorScheme());
}

darkThemeQuery.addEventListener('change', setCurrentThemeFromQuery);
lightThemeQuery.addEventListener('change', setCurrentThemeFromQuery);

export function ThemeButton({ className }: { className?: string }) {
  const store = useThemeStore();

  const toggleTheme = React.useCallback(() => {
    store.setTheme(store.theme === 'dark' ? 'light' : 'dark');
  }, [store]);

  return (
    <Button className={className} onPress={toggleTheme} icon={store.theme === 'dark' ? Sun : Moon}>
      Switch Themes
    </Button>
  );
}
