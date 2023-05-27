import * as React from 'react';
import classNames from 'classnames';
import { Header, Stack, Text } from '@spyrothon/sparx';

import { APIEvent as Event } from '@public/apiv2/APITypes';

import EventTotalDisplay from '../event/EventTotalDisplay';
import { PrimaryNavPopoutButton } from '../settings/PrimaryNavPopout';

import styles from './SidebarLayout.mod.css';

interface LayoutHeaderProps {
  event: Event | undefined;
  subtitle: string;
}

function LayoutHeader(props: LayoutHeaderProps) {
  const { event, subtitle } = props;

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
        <PrimaryNavPopoutButton eventId={`${event.id}`} />
      </Stack>
      <EventTotalDisplay eventId={`${event.id}`} />
    </Stack>
  );
}

interface SidebarLayoutProps {
  event: Event | undefined;
  subtitle: string;
  sidebar: React.ReactNode;
  children: React.ReactNode;
  mainClassName?: string;
}

export default function SidebarLayout(props: SidebarLayoutProps) {
  const { event, subtitle, sidebar, children, mainClassName } = props;

  return (
    <div className={styles.container}>
      <Stack className={styles.sidebar} spacing="space-xl" wrap={false}>
        <LayoutHeader event={event} subtitle={subtitle} />
        {sidebar}
      </Stack>
      <main className={classNames(styles.main, mainClassName)}>{children}</main>
    </div>
  );
}
