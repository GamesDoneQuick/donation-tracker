import * as React from 'react';

import styles from './Input.mod.css';

interface InputProps {
  label: string;
  children: React.ReactNode;
}

export default function Input(props: InputProps) {
  const { label, children } = props;

  return (
    <div className={styles.input}>
      <label>{label}</label>
      {children}
    </div>
  );
}
