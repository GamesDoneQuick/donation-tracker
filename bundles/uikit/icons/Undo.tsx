import * as React from 'react';
import { faUndo } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Undo = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faUndo} />;
};

export default Undo;
