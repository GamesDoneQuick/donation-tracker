import React from 'react';
import { faGripVertical } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const DragHandle = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faGripVertical} />;
};

export default DragHandle;
