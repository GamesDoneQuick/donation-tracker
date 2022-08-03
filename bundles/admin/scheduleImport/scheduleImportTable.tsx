import React, { ReactFragment } from 'react';
import moment from 'moment';
import { OengusConnection, OengusRunLine, OengusSchedule } from 'oengus-api';

import styles from './scheduleImportTable.mod.css';

type Props = {
  schedule: OengusSchedule;
};

export const ScheduleImportTable = ({ schedule }: Props) => {
  const runHeaders = ['game', 'category', 'console', 'estimate', 'setup'] as const;

  const runnerHeaders = ['name', 'twitter', 'nico', 'twitch', 'pronouns'] as const;

  const connectionsToSocials = (
    connections: OengusConnection[],
  ): {
    twitter?: string;
    nico?: string;
    twitch?: string;
  } => {
    return {
      twitter: connections.find(conn => conn.platform === 'TWITTER')?.username,
      nico: connections.find(conn => conn.platform === 'TWITTER')?.username,
      twitch: connections.find(conn => conn.platform === 'TWITTER')?.username,
    };
  };

  const oengusTimeToString = (time: string): string => {
    const oengusDuration = moment.duration(time);

    return (
      `${oengusDuration.hours() ? oengusDuration.hours() + ':' : ''}` +
      `${oengusDuration.minutes().toString().padStart(2, '0')}:${oengusDuration.seconds().toString().padStart(2, '0')}`
    );
  };

  const lineToRow = (line: OengusRunLine, index: number): ReactFragment => {
    return line.runners.map((runner, idx) => (
      <tr key={`${line.categoryId}-${idx}`} className={index % 2 !== 0 ? styles.even : ''}>
        {idx === 0 && (
          <>
            <td rowSpan={line.runners.length}>{index + 1}</td>
            <td rowSpan={line.runners.length}>{line.gameName}</td>
            <td rowSpan={line.runners.length}>{line.categoryName}</td>
            <td rowSpan={line.runners.length}>{line.console}</td>
            <td rowSpan={line.runners.length}>{oengusTimeToString(line.estimate)}</td>
            <td rowSpan={line.runners.length}>{oengusTimeToString(line.setupTime)}</td>
          </>
        )}
        <td>{runner.usernameJapanese || runner.username}</td>
        <td>{connectionsToSocials(runner.connections).twitter || ''}</td>
        <td>{connectionsToSocials(runner.connections).nico || ''}</td>
        <td>{connectionsToSocials(runner.connections).twitch || ''}</td>
        <td>{runner.pronouns}</td>
      </tr>
    ));
  };

  return (
    <table className={styles.scheduleTable}>
      <thead>
        <tr>
          <th rowSpan={2}>Index</th>
          <th colSpan={runHeaders.length}>Run</th>
          <th colSpan={runnerHeaders.length}>Runner</th>
        </tr>
        <tr className={styles.even}>
          {runHeaders.map((h, index) => (
            <th key={`run-${index}`}>{h}</th>
          ))}
          {runnerHeaders.map((h, index) => (
            <th key={`runner-${index}`}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {schedule.lines.filter(line => !line.setupBlock).map((line, index) => lineToRow(line as OengusRunLine, index))}
      </tbody>
    </table>
  );
};
