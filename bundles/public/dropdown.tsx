import React, { useCallback, useContext, useMemo, useState } from 'react';
import invariant from 'invariant';
import Globals from '../common/Globals';

interface DropdownProps {
  closeOnClick?: boolean;
  children?: React.ReactNode;
  openFile?: string;
  closedFile?: string;
  toggle?: () => void; // controlled
  open?: boolean; // controlled
  initiallyOpen?: boolean; // uncontrolled
}

export default function Dropdown({
  toggle,
  open,
  initiallyOpen,
  closeOnClick = true,
  children,
  openFile = 'asc.png',
  closedFile = 'next.png',
}: DropdownProps) {
  invariant(
    open == null || initiallyOpen == null,
    'do not provide both `open` (controlled) and `initiallyOpen` (uncontrolled) props',
  );
  invariant((toggle == null) === (open == null), 'if either `toggle` and `open` are used, both must be');
  const { STATIC_URL } = useContext(Globals);
  const [openState, setOpenState] = useState(initiallyOpen);
  const isOpen = useMemo(() => (toggle ? open : openState), [open, openState, toggle]);
  const toggleOpen = useCallback(() => {
    if (toggle) {
      toggle();
    } else {
      setOpenState(openState => !openState);
    }
  }, [toggle]);
  return (
    <span style={{ position: 'relative' }}>
      <img alt="toggle" src={STATIC_URL + (isOpen ? openFile : closedFile)} onClick={toggleOpen} />
      {isOpen ? <div onClick={closeOnClick ? toggleOpen : undefined}>{children}</div> : null}
    </span>
  );
}
