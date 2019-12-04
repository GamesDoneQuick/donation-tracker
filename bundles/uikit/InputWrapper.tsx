import * as React from 'react';
import classNames from 'classnames';

import Text from './Text';

import styles from './InputWrapper.mod.css';

const InputWrapperSizes = {
  NORMAL: styles.sizeNormal,
  LARGE: styles.sizeLarge,
};

type InputWrapperProps = {
  size?: typeof InputWrapperSizes[keyof typeof InputWrapperSizes];
  label?: React.ReactNode;
  name: string;
  required?: boolean;
  hint?: React.ReactNode;
  leader?: React.ReactNode;
  trailer?: React.ReactNode;
  marginless?: boolean;
  className?: string;
  children: React.ReactNode;
};

export type InputWrapperPassthroughProps = Omit<InputWrapperProps, 'children'>;

const InputWrapper = (props: InputWrapperProps) => {
  const {
    size = InputWrapperSizes.NORMAL,
    label,
    name,
    hint,
    leader,
    trailer,
    marginless = false,
    className,
    children,
  } = props;

  return (
    <div className={classNames(styles.container, size, className, { [styles.marginless]: marginless })}>
      {label != null && (
        <label className={styles.label} htmlFor={name}>
          {label}
        </label>
      )}
      <div className={styles.input}>
        {leader != null && <div className={styles.leader}>{leader}</div>}
        {children}
        {trailer != null && <div className={styles.trailer}>{trailer}</div>}
      </div>
      {hint != null && (
        <Text className={styles.hint} color={Text.Colors.MUTED} size={Text.Sizes.SIZE_14} marginless>
          {hint}
        </Text>
      )}
    </div>
  );
};

InputWrapper.Sizes = InputWrapperSizes;

export default InputWrapper;
