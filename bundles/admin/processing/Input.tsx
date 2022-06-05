import * as React from 'react';

import styles from './Input.mod.css';

interface InputProps {
  label: string;
  note?: string;
  children: React.ReactNode;
}

export default function Input(props: InputProps) {
  const { label, note, children } = props;

  return (
    <div className={styles.input}>
      <label className={styles.label}>{label}</label>
      {children}
      {note != null ? <div className={styles.note}>{note}</div> : null}
    </div>
  );
}
