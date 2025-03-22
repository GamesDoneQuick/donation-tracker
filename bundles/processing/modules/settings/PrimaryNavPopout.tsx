import React from 'react';
import classNames from 'classnames';
import { Anchor, Button, Card, FormSwitch, Header, Spacer, Stack, Text, usePopout } from '@faulty/gdq-design';

import { useConstants } from '@common/Constants';
import { useMeQuery } from '@public/apiv2/reducers/trackerApi';
import Bars from '@uikit/icons/Bars';

import { ThemeButton } from '@processing/modules/theming/Theming';

import { setUseRelativeTimestamps, useUserPreferencesStore } from './UserPreferencesStore';

import styles from './PrimaryNavPopout.mod.css';

// NOTE: These are relatively-static routes, they really aren't likely to
// change, but they should still come from some more authoritative source,
// or be put into one, similar to API routes are.
//
// These are hardcoded with `/tracker` as the root path to avoid changing
// the structure of `CONSTANTS` that gets sent by the bundle host.
const NavRoutes = {
  HOME: (eventId: string | number) => `/tracker/event/${eventId}`,
  BIDS: (eventId: string | number) => `/tracker/bids/${eventId}`,
  DONATIONS: (eventId: string | number) => `/tracker/donations/${eventId}`,
  DONORS: (eventId: string | number) => `/tracker/donors/${eventId}`,
  EVENTS: `/tracker`,
  MILESTONES: (eventId: string | number) => `/tracker/milestones/${eventId}`,
  PRIZES: (eventId: string | number) => `/tracker/prizes/${eventId}`,
  RUNS: (eventId: string | number) => `/tracker/runs/${eventId}`,
  LOGOUT: `/tracker/user/logout/`,
  SELF_SERVICE: `/tracker/user/index/`,

  ADMIN_HOME: `/`,
  PROCESS_DONATIONS: (eventId: number) => `v2/${eventId}/processing/donations`,
  READ_DONATIONS: (eventId: number) => `v2/${eventId}/processing/read`,
  SCHEDULE_EDITOR: (eventId: number) => `schedule_editor/${eventId}`,
};

let adminPath = '';

export function setAdminPath(path: string) {
  adminPath = path;
}

function path(route: string) {
  return adminPath + route;
}

function CurrentUser() {
  const { data: me } = useMeQuery();

  return (
    <div>
      <Text variant="text-xs/normal">Logged in as</Text>
      <Text>
        <strong>{me?.username}</strong>
      </Text>
    </div>
  );
}

function RelativeTimeSwitch() {
  const useRelativeTimestamps = useUserPreferencesStore(state => state.useRelativeTimestamps);

  const handleChange = React.useCallback((isSelected: boolean) => {
    setUseRelativeTimestamps(isSelected);
  }, []);

  return (
    <FormSwitch
      label="Use Relative Timestamps"
      description={
        <>
          {new Date().toDateString()} vs {'"1 hour ago"'}
        </>
      }
      checked={useRelativeTimestamps}
      onChange={handleChange}
    />
  );
}

interface PrimaryNavPopoutProps {
  eventId: number;
}

export function PrimaryNavPopout(props: PrimaryNavPopoutProps) {
  const { eventId } = props;
  const { SWEEPSTAKES_URL } = useConstants();
  const hasPrizes = SWEEPSTAKES_URL !== '';

  return (
    <Card floating className={classNames(styles.container, styles.test)}>
      <Stack direction="horizontal" spacing="space-xl" justify="stretch">
        <Stack spacing="space-lg">
          <CurrentUser />
          <Anchor href={NavRoutes.SELF_SERVICE}>Self Service</Anchor>
          <Anchor href={NavRoutes.LOGOUT}>Logout</Anchor>
          <Spacer />
          <Header tag="h2" variant="header-md/normal">
            Settings
          </Header>
          <RelativeTimeSwitch />
          <ThemeButton />
        </Stack>
        <Stack spacing="space-lg">
          <Header tag="h2" variant="header-md/normal">
            Admin
          </Header>
          <Anchor href={path(NavRoutes.ADMIN_HOME)}>Admin Home</Anchor>
          <Anchor href={path(NavRoutes.PROCESS_DONATIONS(eventId))}>Process Donations</Anchor>
          <Anchor href={path(NavRoutes.READ_DONATIONS(eventId))}>Read Donations</Anchor>
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
  const [openPopout, isOpen] = usePopout(() => <PrimaryNavPopout {...props} />, buttonRef, {
    attach: 'right',
    noStyle: true,
  });

  return (
    <Button variant="default/outline" ref={buttonRef} onPress={isOpen ? undefined : openPopout}>
      <Bars />
    </Button>
  );
}
