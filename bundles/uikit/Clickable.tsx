import * as React from 'react';
import classNames from 'classnames';

import styles from './Clickable.mod.css';

type ClickableProps = {
  tag?: 'div' | 'a' | 'span' | 'label';
  role?: string;
  tabIndex?: number;
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
  [divProp: string]: any;
};

// Anything that is not implicitly clickable (e.g., `a` or `button` tags)
// should use this component to add click actions to its children. This ensures
// that the click is handled in a consistent, accessible way.
const Clickable = (props: ClickableProps) => {
  const { tag: Tag = 'div', role = 'button', tabIndex = 0, children, className, onClick, ...clickableProps } = props;

  const handleKeyPress = React.useCallback(
    ev => {
      if (onClick != null && (ev.key === 'Enter' || ev.key === 'Spacebar' || ev.key === ' ')) {
        ev.preventDefault();
        onClick();
      }
    },
    [onClick],
  );

  return (
    <Tag
      {...clickableProps}
      className={classNames(styles.clickable, className)}
      tabIndex={tabIndex}
      role={role}
      onClick={onClick}
      onKeyPress={handleKeyPress}>
      {children}
    </Tag>
  );
};

export default Clickable;
