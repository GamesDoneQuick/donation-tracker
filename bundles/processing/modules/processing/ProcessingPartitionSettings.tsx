import React from 'react';
import { Stack, TextInput } from '@faulty/gdq-design';

import useProcessingStore from './ProcessingStore';

import styles from './ProcessingPartitionSettings.mod.css';

export default function ProcessingPartitionSettings() {
  const { partition, setPartition, partitionCount, setPartitionCount } = useProcessingStore();

  return (
    <Stack className={styles.partitionSelector} direction="horizontal" wrap={false} justify="stretch">
      <TextInput
        label="Partition ID"
        type="number"
        // @ts-expect-error Incorrect prop typing for number inputs
        min={1}
        max={partitionCount}
        value={String(partition + 1)}
        // eslint-disable-next-line react/jsx-no-bind
        onChange={partition => setPartition(+partition - 1)}
      />
      <TextInput
        label="Partition Count"
        type="number"
        // @ts-expect-error Incorrect prop typing for number inputs
        min={1}
        value={String(partitionCount)}
        // eslint-disable-next-line react/jsx-no-bind
        onChange={count => setPartitionCount(+count)}
      />
    </Stack>
  );
}
