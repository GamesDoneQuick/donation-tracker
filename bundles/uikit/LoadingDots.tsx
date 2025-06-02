import React from 'react';
import cn from 'classnames';
import times from 'lodash/times';

import styles from './LoadingDots.mod.css';

const DEFAULT_WIDTH = 24;
const DEFAULT_DURATION = 1.8;
const DEFAULT_OFFSET = 0.3;
const DEFAULT_SPACING = 25;
const DEFAULT_COUNT = 3;
const DEFAULT_RADIUS = 8;

type LoadingDotsProps = {
  width?: string | number;
  duration?: number;
  offset?: number;
  count?: number;
  spacing?: number;
  radius?: number;
  className?: cn.Argument;
};

const LoadingDots = (props: LoadingDotsProps) => {
  const {
    width = DEFAULT_WIDTH,
    duration = DEFAULT_DURATION,
    offset = DEFAULT_OFFSET,
    count = DEFAULT_COUNT,
    spacing = DEFAULT_SPACING,
    radius = DEFAULT_RADIUS,
    className,
  } = props;

  const viewBoxWidth = spacing * (count + 1);
  const viewBoxHeight = spacing + radius * 2;
  const verticalCenter = radius + spacing / 2;

  return (
    <svg className={cn(styles.dots, className)} viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`} width={width}>
      {times(count, index => (
        <g key={index} transform={`translate(${spacing * (index + 1)} ${verticalCenter})`}>
          <circle cx="0" cy="0" r={radius} fill="currentColor" transform="scale(0.5 0.5)">
            <animateTransform
              attributeName="transform"
              type="scale"
              begin={`-${offset * (count - index)}s`}
              calcMode="spline"
              keySplines="0.3 0 0.7 1;0.3 0 0.7 1"
              values="0;1;0"
              keyTimes="0;0.5;1"
              dur={duration}
              repeatCount="indefinite"
            />
          </circle>
        </g>
      ))}
    </svg>
  );
};

export default LoadingDots;
