import * as React from 'react';
import {
  Button,
  Card,
  FormControl,
  Header,
  SelectInput,
  Spacer,
  Stack,
  TabColor,
  Tabs,
  TextInput,
} from '@spyrothon/sparx';

import useDonationGroupsStore, { DonationGroup } from './DonationGroupsStore';

import styles from './CreateEditDonationGroupModal.mod.css';

interface GroupColorItem {
  name: string;
  value: TabColor;
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
  const [color, setColor] = React.useState<GroupColorItem>(() => {
    return GROUP_COLOR_ITEMS.find(item => item.value === group?.color) || GROUP_COLOR_ITEMS[0];
  });

  const { createDonationGroup, deleteDonationGroup, updateDonationGroup } = useDonationGroupsStore();

  function handleCreate() {
    const action = isEditing ? updateDonationGroup : createDonationGroup;
    action({ id: isEditing ? group.id : newId, name, color: color.value });
    onClose();
  }

  function handleDelete() {
    if (group == null) return;
    deleteDonationGroup(group.id);
    onClose();
  }

  return (
    <Card floating className={styles.modal}>
      <Stack spacing="space-lg">
        <Header tag="h1">{isEditing ? 'Edit Donation Group' : 'Create Donation Group'}</Header>
        <Tabs.Tab color={color.value} label={name || '\b'} badge={15} selected></Tabs.Tab>
        <Spacer />
        <FormControl label="Group Name">
          <TextInput
            value={name}
            // eslint-disable-next-line react/jsx-no-bind
            onChange={event => setName(event.target.value)}
          />
        </FormControl>
        <FormControl label="Group Color">
          <SelectInput
            items={GROUP_COLOR_ITEMS}
            // eslint-disable-next-line react/jsx-no-bind
            onSelect={item => item != null && setColor(item)}
            selectedItem={color}
          />
        </FormControl>
        <Stack direction="horizontal" justify="space-between">
          <Button variant="primary" onClick={handleCreate}>
            {isEditing ? 'Save Group' : 'Create Group'}
          </Button>
          {isEditing ? (
            <Button variant="danger/outline" onClick={handleDelete}>
              Delete Group
            </Button>
          ) : null}
        </Stack>
      </Stack>
    </Card>
  );
}
