import * as React from 'react';

import styles from './ThemeProvider.mod.css';

const ThemeProvider = (props) => {
  const {children} = props;

  return (
    <div className={styles.themeMap}>
      {children}
    </div>
  );
};

export default ThemeProvider;
