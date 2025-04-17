import React from 'react';
import { Item, Select } from '@faulty/gdq-design';

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
    (key: string) => {
      setSelectedMode(key as ProcessingMode);
      onSelect(key as ProcessingMode);
    },
    [onSelect],
  );

  return (
    <Select
      data-test-id="processing-mode"
      aria-label="processing mode"
      items={PROCESSING_MODE_ITEMS}
      selectedKey={selectedMode}
      onSelect={handleSelect}>
      {item => (
        <Item key={item.value} aria-label={item.value}>
          {item.name}
        </Item>
      )}
    </Select>
  );
}
