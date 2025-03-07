import React from 'react';

import { IconTypes } from './IconTypes';

type IconProps = {
  name: (typeof IconTypes)[keyof typeof IconTypes];
  color?: string;
  className?: string;
};

const Icon = (props: IconProps) => {
  const { name: Component, color = 'currentColor', className } = props;

  return <Component style={{ color: color }} className={className} />;
};

Icon.Types = IconTypes;

export default Icon;
