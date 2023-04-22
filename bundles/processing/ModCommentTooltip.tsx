import * as React from 'react';
import { Clickable, Text, useTooltip } from '@spyrothon/sparx';

import InfoCircle from '@uikit/icons/InfoCircle';

import styles from './Processing.mod.css';

interface ModCommentTooltipProps {
  comment: string;
}

export default function ModCommentTooltip(props: ModCommentTooltipProps) {
  const { comment } = props;

  const [tooltipProps] = useTooltip<HTMLSpanElement>(<Text className={styles.modcommentTooltip}>{comment}</Text>, {
    attach: 'bottom',
    align: 'start',
  });

  return (
    <Clickable as="span" {...tooltipProps}>
      <InfoCircle />
    </Clickable>
  );
}
