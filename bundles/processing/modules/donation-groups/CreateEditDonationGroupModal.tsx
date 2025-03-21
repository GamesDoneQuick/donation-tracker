import React from 'react';
import { Button, Header, Item, Select, Spacer, Stack, Tag, TextInput } from '@faulty/gdq-design';

import useDonationGroupsStore, { DonationGroup, DonationGroupColor } from './DonationGroupsStore';

import styles from './CreateEditDonationGroupModal.mod.css';

interface GroupColorItem {
  name: string;
  value: DonationGroupColor;
}

const GROUP_COLOR_ITEMS: GroupColorItem[] = [
  { name: 'Default', value: 'default' },
  { name: 'Teal', value: 'info' },
  { name: 'Blue', value: 'accent' },
  { name: 'Green', value: 'success' },
  { name: 'Orange', value: 'warning' },
  { name: 'Red', value: 'danger' },
];

interface CreateEditDonationGroupModalProps {
  group?: DonationGroup;
  onClose: () => unknown;
}

export default function CreateEditDonationGroupModal(props: CreateEditDonationGroupModalProps) {
  const { group, onClose } = props;
  const isEditing = group != null;

  const [newId] = React.useState(() => (Math.random() + 1).toString(36).substring(7));
  const [name, setName] = React.useState(group?.name || 'New Group');
  const [color, setColor] = React.useState<DonationGroupColor>(group?.color ?? 'default');

  const { createDonationGroup, deleteDonationGroup, updateDonationGroup } = useDonationGroupsStore();

  const handleCreate = React.useCallback(() => {
    const action = isEditing ? updateDonationGroup : createDonationGroup;
    action({ id: isEditing ? group?.id : newId, name, color });
    onClose();
  }, [color, createDonationGroup, group?.id, isEditing, name, newId, onClose, updateDonationGroup]);

  const handleDelete = React.useCallback(() => {
    if (group == null) return;
    deleteDonationGroup(group.id);
    onClose();
  }, [deleteDonationGroup, group, onClose]);

  return (
    <Stack spacing="space-lg" className={styles.modal}>
      <Header tag="h1">{isEditing ? 'Edit Donation Group' : 'Create Donation Group'}</Header>
      <Tag color={color}>{name || '\b'}</Tag>
      <Spacer />
      <TextInput
        label="Group Name"
        value={name}
        // eslint-disable-next-line react/jsx-no-bind
        onChange={name => setName(name)}
      />
      <Select
        label="Group Color"
        items={GROUP_COLOR_ITEMS}
        selectedKey={color}
        onSelect={setColor as (key: string) => void}>
        {item => <Item key={item.value}>{item.name}</Item>}
      </Select>
      <Stack direction="horizontal" justify="space-between" style={{ marginTop: 'auto' }}>
        <Button variant="primary" onPress={handleCreate}>
          {isEditing ? 'Save Group' : 'Create Group'}
        </Button>
        {isEditing ? (
          <Button variant="danger/outline" onPress={handleDelete}>
            Delete Group
          </Button>
        ) : null}
      </Stack>
    </Stack>
  );
}
