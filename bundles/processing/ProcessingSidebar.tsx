import * as React from 'react';
import { Header, Stack, Text } from '@spyrothon/sparx';

import { Event } from '@public/apiv2/APITypes';

import { PrimaryNavPopoutButton } from './PrimaryNavPopout';
import { ThemeButton } from './Theming';

interface ProcessingHeaderProps {
  event: Event | undefined;
  subtitle: string;
}

function ProcessingHeader(props: ProcessingHeaderProps) {
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

interface ProcessingSidebarProps {
  event: Event | undefined;
  subtitle: string;
  className?: string;
  children: React.ReactNode;
}

export default function ProcessingSidebar(props: ProcessingSidebarProps) {
  const { event, subtitle, className, children } = props;

  return (
    <Stack className={className} spacing="space-xl">
      <ProcessingHeader event={event} subtitle={subtitle} />
      <ThemeButton />
      {children}
    </Stack>
  );
}
