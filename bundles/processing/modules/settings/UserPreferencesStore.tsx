import React from 'react';
import create from 'zustand';
import { persist } from 'zustand/middleware';

interface UserPreferencesStoreState {
  useRelativeTimestamps: boolean;
}

export const useUserPreferencesStore = create<UserPreferencesStoreState>()(
  persist(
    _set => ({
      useRelativeTimestamps: false,
    }),
    {
      name: 'user-preferences',
    },
  ),
);

export function setUseRelativeTimestamps(useRelativeTimestamps: boolean) {
  useUserPreferencesStore.setState({ useRelativeTimestamps });
}
