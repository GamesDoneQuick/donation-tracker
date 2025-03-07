import React from 'react';
import { faThumbtack } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Pin = (props: any) => {
  return (
    <FontAwesomeIcon
      // TODO: This should be a design system color token, not a raw color
      color="#e20039"
      style={{ transform: 'rotate(40deg)' }}
      {...props}
      icon={faThumbtack}
    />
  );
};

export default Pin;
