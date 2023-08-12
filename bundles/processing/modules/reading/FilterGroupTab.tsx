import * as React from 'react';
import classNames from 'classnames';
import { useDrag, useDrop } from 'react-dnd';
import { Clickable, Stack, TabColor, Tabs, useHoverFocus } from '@spyrothon/sparx';

import Dots from '@uikit/icons/Dots';

import useDonationGroupsStore, { moveDonationGroup, useDonationGroup } from '../donation-groups/DonationGroupsStore';
import { DonationState, useFilteredDonations } from '../donations/DonationsStore';
import { FilterGroupTabItem, FilterTabItem, GroupTabItem } from './ReadingTypes';

import styles from './FilterGroupTab.mod.css';

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

  const tabRef = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag(
    () => ({
      type: 'donation-group',
      item,
      canDrag: () => item.type === 'group',
      collect: monitor => ({
        isDragging: monitor.isDragging(),
      }),
    }),
    [item],
  );
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: ['donation-group'],
      drop(draggedItem: GroupTabItem) {
        moveDonationGroup(draggedItem.id, item.id, false);
      },
      canDrop(draggedItem: GroupTabItem) {
        return draggedItem.id !== item.id;
      },
      collect: monitor => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    [item],
  );
  drag(drop(tabRef));

  if (group == null) return null;

  return (
    <div
      ref={tabRef}
      className={classNames(styles.draggableTabContainer, {
        [styles.isDropOver]: isOver && canDrop,
        [styles.dragging]: isDragging,
      })}>
      <div className={styles.dropIndicator} />
      {children({
        id: item.id,
        label: group.name,
        color: group.color,
        count: group.donationIds.length,
      })}
    </div>
  );
}

export function FilterGroupTabDropTarget() {
  const lastItemId = useDonationGroupsStore(state => state.groups[state.groups.length - 1]?.id);
  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: ['donation-group'],
      drop(draggedItem: GroupTabItem) {
        moveDonationGroup(draggedItem.id, lastItemId, true);
      },
      canDrop(draggedItem: GroupTabItem) {
        return draggedItem.id !== lastItemId;
      },
      collect: monitor => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    [lastItemId],
  );

  if (lastItemId == null) return null;

  return (
    <div ref={drop} className={classNames(styles.emptyDropTarget, { [styles.isDropOver]: isOver && canDrop })}>
      <div className={styles.dropIndicator} />
    </div>
  );
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

  function handleEdit() {
    onEdit?.(item);
  }

  const renderTab = (tabData: TabData) => (
    <Tabs.Tab
      key={tabData.id}
      {...hoverFocusProps}
      label={tabData.label}
      color={tabData.color}
      onPress={handleSelect}
      selected={isSelected}
      badge={
        <Stack direction="horizontal" spacing="space-lg">
          {onEdit != null && active ? (
            <Clickable onPress={handleEdit}>
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
