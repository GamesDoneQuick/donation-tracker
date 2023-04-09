import * as React from 'react';
import { useQuery } from 'react-query';
import { Anchor, Button, Card, Header, Spacer, Stack, Text, usePopout } from '@spyrothon/sparx';

import { useConstants } from '@common/Constants';
import APIClient from '@public/apiv2/APIClient';
import Bars from '@uikit/icons/Bars';

import { loadMe, useMe } from './AuthStore';
import { ThemeButton } from './Theming';

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
  LOGOUT: `/tracker/user/logout/`,
  SELF_SERVICE: `/tracker/user/index/`,

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

function CurrentUser() {
  useQuery('auth.me', () => APIClient.getMe(), { onSuccess: me => loadMe(me), staleTime: 5 * 60 * 1000 });

  const me = useMe();

  return (
    <div>
      <Text variant="text-xs/normal">Logged in as</Text>
      <Text>
        <strong>{me?.username}</strong>
      </Text>
    </div>
  );
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
          <CurrentUser />
          <Anchor href={NavRoutes.SELF_SERVICE}>Self Service</Anchor>
          <Anchor href={NavRoutes.LOGOUT}>Logout</Anchor>
          <Spacer />
          <ThemeButton />
        </Stack>
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
  const [openPopout] = usePopout(() => <PrimaryNavPopout {...props} />, buttonRef, { attach: 'right' });

  return (
    <Button variant="default/outline" ref={buttonRef} onClick={openPopout}>
      <Bars />
    </Button>
  );
}
