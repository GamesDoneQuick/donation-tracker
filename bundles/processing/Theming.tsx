import * as React from 'react';
import create from 'zustand';
import { persist } from 'zustand/middleware';
import { Button } from '@spyrothon/sparx';

import Moon from '@uikit/icons/Moon';
import Sun from '@uikit/icons/Sun';

const darkThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
const lightThemeQuery = window.matchMedia('(prefers-color-scheme: light)');

function getCurrentColorScheme() {
  if (darkThemeQuery.matches) return 'dark';
  if (lightThemeQuery.matches) return 'light';
  return 'light';
}

interface ThemeStoreState {
  theme: string;
  accent: string;
  setTheme(theme: string): void;
}

export const useThemeStore = create<ThemeStoreState>()(
  persist(
    set => ({
      theme: getCurrentColorScheme(),
      accent: 'blue',
      setTheme(theme: string) {
        set({ theme });
      },
      setAccent(accent: string) {
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

  function toggleTheme() {
    store.setTheme(store.theme === 'dark' ? 'light' : 'dark');
  }

  return (
    <Button className={className} onClick={toggleTheme} icon={store.theme === 'dark' ? Sun : Moon}>
      Switch Themes
    </Button>
  );
}
