import * as React from 'react';
import { Clickable, Interactive, Text, useTooltip } from '@faulty/gdq-design';

import InfoCircle from '@uikit/icons/InfoCircle';

import styles from './ModCommentTooltip.mod.css';

interface ModCommentTooltipProps {
  comment: string;
}

export default function ModCommentTooltip(props: ModCommentTooltipProps) {
  const { comment } = props;

  const [tooltipProps] = useTooltip<HTMLSpanElement>(
    <Text variant="text-sm/normal" className={styles.tooltip}>
      {comment}
    </Text>,
    {
      attach: 'bottom',
      align: 'start',
    },
  );

  return (
    <Interactive as="span">
      <Clickable as="span" {...tooltipProps}>
        <InfoCircle />
      </Clickable>
    </Interactive>
  );
}
