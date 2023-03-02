import * as React from 'react';
import { useQuery } from 'react-query';

import APIClient from '@public/apiv2/APIClient';

import useProcessingStore from './ProcessingStore';

interface DonationCountsProps {
  eventId: string;
}

export default function DonationCounts(props: DonationCountsProps) {
  const { eventId } = props;

  const [counts, setCounts] = useProcessingStore(state => [state.counts, state.setCounts]);
  const countsQuery = useQuery(`donations.${eventId}.counts`, () => APIClient.getDonationCounts(eventId), {
    onSuccess: counts => setCounts(counts),
  });

  return (
    <div>
      <h5>Counts</h5>
      <table className="table table-sm">
        <thead>
          <tr>
            <th>Status</th>
            <th>Count</th>
          </tr>
        </thead>

        <tbody>
          {countsQuery.isLoading ? (
            <tr>
              <td colSpan={2}>Loading donation counts...</td>
            </tr>
          ) : (
            Object.entries(counts).map(([status, count]) => (
              <tr key={status}>
                <th>{status}</th>
                <td>{count}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
