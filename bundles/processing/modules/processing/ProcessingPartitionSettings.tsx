import * as React from 'react';
import { FormControl, Stack, TextInput } from '@spyrothon/sparx';

import useProcessingStore from './ProcessingStore';

import styles from './ProcessingPartitionSettings.mod.css';

export default function ProcessingPartitionSettings() {
  const { partition, setPartition, partitionCount, setPartitionCount } = useProcessingStore();

  return (
    <Stack className={styles.partitionSelector} direction="horizontal" wrap={false} justify="stretch">
      <FormControl label="Partition ID">
        <TextInput
          type="number"
          min={1}
          max={partitionCount}
          value={partition + 1}
          // eslint-disable-next-line react/jsx-no-bind
          onChange={e => setPartition(+e.target.value - 1)}
        />
      </FormControl>
      <FormControl label="Partition Count">
        <TextInput
          type="number"
          min="1"
          value={partitionCount}
          // eslint-disable-next-line react/jsx-no-bind
          onChange={e => setPartitionCount(+e.target.value)}
        />
      </FormControl>
    </Stack>
  );
}
