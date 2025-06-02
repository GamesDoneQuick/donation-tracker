import React from 'react';
import cn from 'classnames';
import { Header, Stack, Text } from '@faulty/gdq-design';

import { useEventFromRoute } from '@public/apiv2/hooks';

import EventTotalDisplay from '../event/EventTotalDisplay';
import { PrimaryNavPopoutButton } from '../settings/PrimaryNavPopout';

import styles from './SidebarLayout.mod.css';

interface LayoutHeaderProps {
  subtitle: string;
}

function LayoutHeader(props: LayoutHeaderProps) {
  const { subtitle } = props;
  const { data: event } = useEventFromRoute();

  if (event == null) {
    return (
      <Header className={styles.sidebarHeader} tag="h1" variant="header-md/normal">
        Loading...
      </Header>
    );
  }

  return (
    <Stack spacing="space-md" className={styles.sidebarHeader}>
      <Stack direction="horizontal" justify="space-between" align="center" spacing="space-lg" wrap={false}>
        <div>
          <Header tag="h1" variant="header-md/normal">
            {event.name}
          </Header>
          <Text variant="text-sm/normal">{subtitle}</Text>
        </div>
        <PrimaryNavPopoutButton />
      </Stack>
      <EventTotalDisplay />
    </Stack>
  );
}

interface SidebarLayoutProps {
  subtitle: string;
  sidebar: React.ReactNode;
  children: React.ReactNode;
  mainClassName?: string;
}

export default function SidebarLayout(props: SidebarLayoutProps) {
  const { subtitle, sidebar, children, mainClassName } = props;

  return (
    <div className={styles.container}>
      <Stack className={styles.sidebar} spacing="space-xl" wrap={false}>
        <LayoutHeader subtitle={subtitle} />
        {sidebar}
      </Stack>
      <main className={cn(styles.main, mainClassName)}>{children}</main>
    </div>
  );
}
