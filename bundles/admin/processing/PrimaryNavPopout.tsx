import * as React from 'react';
import { Anchor, Button, Card, Header, Spacer, Stack, usePopout } from '@spyrothon/sparx';

import { useConstants } from '@common/Constants';
import Bars from '@uikit/icons/Bars';

import styles from './PrimaryNavPopout.mod.css';

// NOTE: These are relatively-static routes, they really aren't likely to
// change, but they should still come from some more authoritative source,
// or be put into one, similar to API routes are.
//
// These are hardcoded with `/tracker` as the root path to avoid changing
// the structure of `CONSTANTS` that gets sent by the bundle host.
const NavRoutes = {
  HOME: (eventId: string) => `/tracker/event/${eventId}`,
  BIDS: (eventId: string) => `/tracker/bids/${eventId}`,
  DONATIONS: (eventId: string) => `/tracker/donations/${eventId}`,
  DONORS: (eventId: string) => `/tracker/donors/${eventId}`,
  EVENTS: `/tracker`,
  MILESTONES: (eventId: string) => `/tracker/milestones/${eventId}`,
  PRIZES: (eventId: string) => `/tracker/prizes/${eventId}`,
  RUNS: (eventId: string) => `/tracker/runs/${eventId}`,

  ADMIN_HOME: `/`,
  INTERSTITIALS: (eventId: string) => `interstitials/${eventId}`,
  PROCESS_DONATIONS: (eventId: string) => `v2/${eventId}/processing/donations`,
  READ_DONATIONS: (eventId: string) => `v2/${eventId}/processing/read`,
  SCHEDULE_EDITOR: (eventId: string) => `schedule_editor/${eventId}`,
};

let adminPath = '';

export function setAdminPath(path: string) {
  adminPath = path;
}

function path(route: string) {
  return adminPath + route;
}

interface PrimaryNavPopoutProps {
  eventId: string;
}

export function PrimaryNavPopout(props: PrimaryNavPopoutProps) {
  const { eventId } = props;
  const { SWEEPSTAKES_URL } = useConstants();
  const hasPrizes = SWEEPSTAKES_URL !== '';

  return (
    <Card floating className={styles.container}>
      <Stack direction="horizontal" spacing="space-xl">
        <Stack spacing="space-lg">
          <Header tag="h2" variant="header-md/normal">
            Admin
          </Header>
          <Anchor href={path(NavRoutes.ADMIN_HOME)}>Admin Home</Anchor>
          <Anchor href={path(NavRoutes.PROCESS_DONATIONS(eventId))}>Process Donations</Anchor>
          <Anchor href={path(NavRoutes.READ_DONATIONS(eventId))}>Read Donations</Anchor>
          <Anchor href={path(NavRoutes.INTERSTITIALS(eventId))}>Interstitials</Anchor>
          <Anchor href={path(NavRoutes.SCHEDULE_EDITOR(eventId))}>Schedule Editor</Anchor>
          <Spacer />
          <Header tag="h2" variant="header-md/normal">
            Public
          </Header>
          <Anchor href={NavRoutes.HOME(eventId)}>Home</Anchor>
          <Anchor href={NavRoutes.RUNS(eventId)}>Runs</Anchor>
          {hasPrizes ? <Anchor href={NavRoutes.PRIZES(eventId)}>Prizes</Anchor> : null}
          <Anchor href={NavRoutes.BIDS(eventId)}>Bids</Anchor>
          <Anchor href={NavRoutes.MILESTONES(eventId)}>Milestones</Anchor>
          <Anchor href={NavRoutes.DONORS(eventId)}>Donors</Anchor>
          <Anchor href={NavRoutes.DONATIONS(eventId)}>Donations</Anchor>
          <Anchor href={NavRoutes.EVENTS}>All Events</Anchor>
        </Stack>
      </Stack>
    </Card>
  );
}

export function PrimaryNavPopoutButton(props: PrimaryNavPopoutProps) {
  const buttonRef = React.useRef<HTMLButtonElement>(null);
  const [openPopout] = usePopout(() => <PrimaryNavPopout {...props} />, buttonRef, { attach: 'left' });

  return (
    <Button variant="default/outline" ref={buttonRef} onClick={openPopout}>
      <Bars />
    </Button>
  );
}
