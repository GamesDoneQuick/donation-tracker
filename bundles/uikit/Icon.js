import * as React from 'react';

import { IconTypes } from './IconTypes';

const Icon = props => {
  const { name: IconComponent, color = 'currentColor', className } = props;

  return <IconComponent style={{ color: color }} className={className} />;
};

Icon.Types = IconTypes;

export default Icon;
