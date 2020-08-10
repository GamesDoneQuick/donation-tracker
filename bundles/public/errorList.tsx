import React from 'react';

import styles from './errorList.mod.css';

function ErrorList({ errors = [] }: { errors?: React.ReactNode[] }) {
  return errors.length ? (
    <ul className={styles['errorlist']}>
      {errors.map((error, i) => (
        <li key={i}>{error}</li>
      ))}
    </ul>
  ) : null;
}

export default ErrorList;
