import * as React from 'react';
import { Header, Stack, Text } from '@spyrothon/sparx';

import { Event } from '@public/apiv2/APITypes';

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
      <Header tag="h1" variant="header-md/normal">
        Loading...
      </Header>
    );
  }

  return (
    <Stack direction="horizontal" justify="space-between" align="center" spacing="space-lg" wrap={false}>
      <div>
        <Header tag="h1" variant="header-md/normal">
          {event.name}
        </Header>
        <Text>{subtitle}</Text>
      </div>
      <PrimaryNavPopoutButton eventId={`${event.id}`} />
    </Stack>
  );
}

interface SidebarLayoutProps {
  event: Event | undefined;
  subtitle: string;
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

export default function SidebarLayout(props: SidebarLayoutProps) {
  const { event, subtitle, sidebar, children } = props;

  return (
    <div className={styles.container}>
      <Stack className={styles.sidebar} spacing="space-xl">
        <LayoutHeader event={event} subtitle={subtitle} />
        {sidebar}
      </Stack>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
