import * as React from 'react';

import { faSun } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

const Sun = (props: any) => {
  return <FontAwesomeIcon {...props} icon={faSun} />;
};

export default Sun;
