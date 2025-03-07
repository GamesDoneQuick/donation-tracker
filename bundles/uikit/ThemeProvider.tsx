import React from 'react';

import styles from './ThemeProvider.mod.css';

type ThemeProviderProps = {
  children?: React.ReactNode;
};

const ThemeProvider = (props: ThemeProviderProps) => {
  const { children } = props;

  return <div className={styles.themeMap}>{children}</div>;
};

export default ThemeProvider;
