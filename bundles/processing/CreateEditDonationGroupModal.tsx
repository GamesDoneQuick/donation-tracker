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
  const [name, setName] = React.useState(group?.name || 'New Group');
  const [color, setColor] = React.useState<GroupColorItem>(() => {
    return GROUP_COLOR_ITEMS.find(g => g.name === group?.name) || GROUP_COLOR_ITEMS[0];
  });
  const { createDonationGroup, updateDonationGroup } = useDonationGroupsStore();

  function handleCreate() {
    const action = group != null ? updateDonationGroup : createDonationGroup;
    action({ name, color: color.value });
    onClose();
  }

  return (
    <Card floating className={styles.modal}>
      <Stack spacing="space-lg">
        <Header tag="h1">Create Donation Group</Header>
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
        <Button onClick={handleCreate}>Create Group</Button>
        <Spacer />
        <Tabs.Tab color={color.value} label={name || '\b'} badge={15} selected></Tabs.Tab>
      </Stack>
    </Card>
  );
}
