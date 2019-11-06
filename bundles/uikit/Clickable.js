import * as React from 'react';
import classNames from 'classnames';

import styles from './Clickable.mod.css';

// Anything that is not implicitly clickable (e.g., `a` or `button` tags)
// should use this component to add click actions to its children. This ensures
// that the click is handled in a consistent, accessible way.
const Clickable = props => {
  const {
    tag: Tag = 'div', // Tag to use as a container: 'div' | 'a' | 'span' | 'label'
    role = 'button', // ARIA role: 'button' | switch' | 'menuitem'
    tabIndex = 0,
    children,
    className,
    onClick,
    onKeyPress,
    ...clickableProps
  } = props;

  const ref = React.useRef();
  const handleKeyPress = React.useCallback(
    ev => {
      if (onClick != null && (ev.key === 'Enter' || ev.key === 'Spacebar' || ev.key === ' ')) {
        ev.preventDefault();
        ref.current.click();
      }
    },
    [ref, onClick],
  );

  return (
    <Tag
      {...clickableProps}
      className={classNames(styles.clickable, className)}
      ref={ref}
      tabIndex={tabIndex}
      role={role}
      onClick={onClick}
      onKeyPress={handleKeyPress}>
      {children}
    </Tag>
  );
};

export default Clickable;
