import * as React from 'react';

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
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedMode(e.target.value as ProcessingMode);
      onSelect(e.target.value as ProcessingMode);
    },
    [onSelect],
  );

  return (
    <select data-test-id="processing-mode" value={selectedMode} onChange={handleSelect}>
      {PROCESSING_MODE_ITEMS.map(item => (
        <option key={item.value} value={item.value}>
          {item.name}
        </option>
      ))}
    </select>
  );
}
