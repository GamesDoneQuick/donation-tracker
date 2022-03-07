import React, { useState } from 'react';

import { Ad, Interview, Model, ModelFields, Run } from '@common/Models';
import { fullKey, memoizeCallback } from '@common/Util';
import Row from './Rows';

const cachedCallback = memoizeCallback(
  (callback, _, ...args) => {
    callback(...args);
  },
  (_, id) => id,
);

interface BodyProps {
  sortedItems: (Interview | Ad | Run)[];
  saveItem: (key: string, fields: Partial<ModelFields>) => void;
  canEdit: (model: Model) => boolean;
}

export default React.memo(function Body({ sortedItems, saveItem, canEdit }: BodyProps) {
  const [editing, setEditing] = useState<string | null>(null);
  return (
    <tbody>
      {sortedItems.map((item, index) => (
        <Row
          key={fullKey(item)}
          item={item}
          editing={editing === fullKey(item)}
          saveItem={
            canEdit(item)
              ? cachedCallback((fields: ModelFields) => {
                  saveItem(fullKey(item), fields);
                  setEditing(null);
                }, `save-${fullKey(item)}`)
              : null
          }
          editItem={
            canEdit(item)
              ? cachedCallback(() => {
                  setEditing(fullKey(item));
                }, `edit-${fullKey(item)}`)
              : null
          }
          cancelEdit={
            canEdit(item)
              ? cachedCallback(() => {
                  setEditing(null);
                }, `cancel-${fullKey(item)}`)
              : null
          }
        />
      ))}
    </tbody>
  );
});
