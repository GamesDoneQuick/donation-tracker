import * as React from 'react';
import { Item, Select } from '@spyrothon/sparx';

import { ProcessingMode } from './ProcessingStore';

interface ProcessingModeSelectorProps {
  initialMode: ProcessingMode;
  onSelect: (mode: ProcessingMode) => unknown;
}

export default function ProcessingModeSelector(props: ProcessingModeSelectorProps) {
  const { onSelect, initialMode } = props;
  const PROCESSING_MODE_ITEMS = [
    {
      name: 'Regular',
      value: 'flag',
    },
    {
      name: 'Confirm',
      value: 'confirm',
    },
  ];

  const [selectedMode, setSelectedMode] = React.useState(initialMode);

  const handleSelect = React.useCallback(
    (item: string) => {
      if (item == null) return;

      setSelectedMode(item as ProcessingMode);
      onSelect(item as ProcessingMode);
    },
    [onSelect],
  );

  return (
    <Select items={PROCESSING_MODE_ITEMS} onSelect={handleSelect} selectedKey={selectedMode}>
      {item => <Item key={item.value}>{item.name}</Item>}
    </Select>
  );
}
