import * as React from 'react';
import { SelectInput } from '@spyrothon/sparx';

import { ProcessingMode } from './ProcessingStore';

interface ProcessingModeSelectItem {
  name: string;
  value: ProcessingMode;
}

interface ProcessingModeSelectorProps {
  initialMode: ProcessingMode;
  onSelect: (mode: ProcessingMode) => unknown;
}

export default function ProcessingModeSelector(props: ProcessingModeSelectorProps) {
  const { onSelect, initialMode } = props;

  const PROCESSING_MODE_ITEMS: ProcessingModeSelectItem[] = [
    {
      name: 'Regular',
      value: 'flag',
    },
    {
      name: 'Confirm',
      value: 'confirm',
    },
  ];

  const [selectedMode, setSelectedMode] = React.useState<ProcessingModeSelectItem | undefined>(() =>
    PROCESSING_MODE_ITEMS.find(mode => mode.value === initialMode),
  );

  function handleSelect(item: ProcessingModeSelectItem | undefined) {
    if (item == null) return;

    setSelectedMode(item);
    onSelect(item.value as ProcessingMode);
  }

  return <SelectInput items={PROCESSING_MODE_ITEMS} onSelect={handleSelect} selectedItem={selectedMode} />;
}
