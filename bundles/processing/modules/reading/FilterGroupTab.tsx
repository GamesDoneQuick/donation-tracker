import * as React from 'react';
import classNames from 'classnames';
import { useDrag, useDrop } from 'react-dnd';
import { Clickable, Stack, Text, useHoverFocus } from '@faulty/gdq-design';

import Dots from '@uikit/icons/Dots';

import useDonationGroupsStore, { moveDonationGroup, useDonationGroup } from '../donation-groups/DonationGroupsStore';
import { DonationState, useFilteredDonations } from '../donations/DonationsStore';
import { FilterGroupTabItem, FilterTabItem, GroupTabItem } from './ReadingTypes';

import styles from './FilterGroupTab.mod.css';

interface TabData {
  id: string;
  label: string;
  color: string;
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

const TAB_COLORS = {
  default: styles['color-default'],
  secondary: styles['color-secondary'],
  accent: styles['color-accent'],
  success: styles['color-success'],
  info: styles['color-info'],
  warning: styles['color-warning'],
  danger: styles['color-danger'],
};

type TabColor = keyof typeof TAB_COLORS;

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

  const handleSelect = React.useCallback(() => {
    onSelected(item);
  }, [item, onSelected]);

  const handleEdit = React.useCallback(() => {
    onEdit?.(item);
  }, [item, onEdit]);

  const renderTab = (tabData: TabData) => (
    <Clickable
      {...hoverFocusProps}
      className={classNames(styles.groupTab, TAB_COLORS[tabData.color as TabColor], { [styles.active]: isSelected })}
      aria-pressed={isSelected}
      onPress={handleSelect}>
      <Stack key={tabData.id} direction="horizontal" justify="space-between" align="center">
        <Text variant="text-md/inherit">{tabData.label}</Text>
        <Stack direction="horizontal" spacing="space-lg" align="center">
          {onEdit != null && active ? (
            <Clickable onPress={handleEdit}>
              <Text>
                <Dots />
              </Text>
            </Clickable>
          ) : null}
          <Text className={styles.tabCount}>{tabData.count}</Text>
        </Stack>
      </Stack>
    </Clickable>
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
