import React from 'react';
import { Button, Callout, Header, Item, Select, Stack, Tag, TextInput } from '@faulty/gdq-design';

import APIErrorList from '@public/APIErrorList';
import { usePermission } from '@public/apiv2/helpers/auth';
import {
  useCreateDonationGroupMutation,
  useDeleteDonationGroupMutation,
  useDonationGroupsQuery,
} from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

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

  const [name, setName] = React.useState(group?.name || 'New Group');
  const [color, setColor] = React.useState<DonationGroupColor>(group?.color ?? 'default');

  const canDeleteGroups = usePermission('tracker.delete_donationgroup');

  const groupId = React.useMemo(
    () =>
      group
        ? group.id
        : name
            .trim()
            .replace(/\s+/g, '_')
            .replace(/[^-\w]/g, '')
            .toLowerCase()
            .slice(0, 32),
    [group, name],
  );

  const { updateDonationGroup } = useDonationGroupsStore();
  const { data: groups } = useDonationGroupsQuery();
  const [createDonationGroup, createResult] = useCreateDonationGroupMutation();
  const [deleteDonationGroup, deleteResult] = useDeleteDonationGroupMutation();

  const handleCreate = React.useCallback(async () => {
    try {
      if (!isEditing) {
        await createDonationGroup(groupId).unwrap();
      }
      updateDonationGroup({ id: groupId, name, color });
      onClose();
    } catch {
      // nothing, the error display will handle it
    }
  }, [color, createDonationGroup, groupId, isEditing, name, onClose, updateDonationGroup]);

  const handleDelete = React.useCallback(async () => {
    if (groupId == null) return;
    try {
      await deleteDonationGroup(groupId).unwrap();
      onClose();
    } catch {
      // nothing, the error display will handle it
    }
  }, [deleteDonationGroup, groupId, onClose]);

  const errors = React.useMemo(() => {
    const errors: string[] = [];
    if (!isEditing && groups?.includes(groupId)) {
      errors.push('Group ID already exists on the server.');
    }
    return errors;
  }, [groupId, groups, isEditing]);

  return (
    <Stack spacing="space-lg" className={styles.modal}>
      <Header tag="h1">{isEditing ? 'Edit Donation Group' : 'Create Donation Group'}</Header>
      <Tag color={color}>{name || '\b'}</Tag>
      <TextInput label="Group ID" value={groupId} isDisabled />
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
        <Spinner spinning={createResult.isLoading} showPartial>
          <Button variant="primary" onPress={handleCreate} isDisabled={errors.length > 0}>
            {isEditing ? 'Save Group' : 'Create Group'}
          </Button>
        </Spinner>
        {isEditing && canDeleteGroups && (
          <Spinner spinning={deleteResult.isLoading} showPartial>
            <Button variant="danger/outline" onPress={handleDelete}>
              Delete Group
            </Button>
          </Spinner>
        )}
        <APIErrorList errors={[createResult.error, deleteResult.error]} />
        {errors.length !== 0 && (
          <Callout type="danger">
            {errors.map((e, i) => (
              <React.Fragment key={i}>{e}</React.Fragment>
            ))}
          </Callout>
        )}
      </Stack>
    </Stack>
  );
}
