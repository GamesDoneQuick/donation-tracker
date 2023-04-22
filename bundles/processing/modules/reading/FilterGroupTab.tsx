import * as React from 'react';
import { Clickable, Stack, TabColor, Tabs, useHoverFocus } from '@spyrothon/sparx';

import Dots from '@uikit/icons/Dots';

import { useDonationGroup } from '../donation-groups/DonationGroupsStore';
import { DonationState, useFilteredDonations } from '../donations/DonationsStore';
import { FilterGroupTabItem, FilterTabItem, GroupTabItem } from './ReadingTypes';

interface TabData {
  id: string;
  label: string;
  color: TabColor;
  count: number;
}
type TabDataRenderer = (tabData: TabData) => React.ReactElement;

interface TabProps<T extends FilterGroupTabItem> {
  item: T;
  donationState: DonationState;
  children: TabDataRenderer;
}

function FilterTab({ item, donationState, children }: TabProps<FilterTabItem>) {
  const donations = useFilteredDonations(donationState, item.predicate);

  return children({
    id: item.id,
    label: item.label,
    color: item.color,
    count: donations.length,
  });
}

function GroupTab({ item, children }: TabProps<GroupTabItem>) {
  const group = useDonationGroup(item.id);
  if (group == null) return null;

  return children({
    id: item.id,
    label: group.name,
    color: group.color,
    count: group.donationIds.length,
  });
}

interface FilterGroupTabProps {
  donationState: DonationState;
  item: FilterGroupTabItem;
  isSelected: boolean;
  onEdit?: (item: FilterGroupTabItem) => void;
  onSelected: (item: FilterGroupTabItem) => void;
}

export default function FilterGroupTab(props: FilterGroupTabProps) {
  const { donationState, item, isSelected, onEdit, onSelected } = props;

  const [hoverFocusProps, active] = useHoverFocus();

  function handleSelect() {
    onSelected(item);
  }

  function handleEdit(event: React.MouseEvent) {
    event.stopPropagation();
    onEdit?.(item);
  }

  const renderTab = (tabData: TabData) => (
    <Tabs.Tab
      key={tabData.id}
      {...hoverFocusProps}
      label={tabData.label}
      color={tabData.color}
      onClick={handleSelect}
      selected={isSelected}
      badge={
        <Stack direction="horizontal" spacing="space-lg">
          {onEdit != null && active ? (
            <Clickable onClick={handleEdit}>
              <Dots />
            </Clickable>
          ) : null}
          {tabData.count}
        </Stack>
      }
    />
  );

  return item.type === 'filter' ? (
    <FilterTab donationState={donationState} item={item}>
      {renderTab}
    </FilterTab>
  ) : (
    <GroupTab donationState={donationState} item={item}>
      {renderTab}
    </GroupTab>
  );
}
