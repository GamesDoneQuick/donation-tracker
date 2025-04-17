import MockAdapter from 'axios-mock-adapter';
import { DateTime } from 'luxon';
import { Server } from 'mock-socket';
import { shallowEqual } from 'react-redux';

import { ProcessingEvent } from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { Donation } from '@public/apiv2/Models';
import { setRoot } from '@public/apiv2/reducers/apiRoot';
import { trackerApi, TrackerSimpleDonationMutations } from '@public/apiv2/reducers/trackerApi';
import { TrackerApiInfiniteQueryEndpoints, TrackerApiQueryEndpoints } from '@public/apiv2/reducers/trackerBaseApi';
import { RootState, store } from '@public/apiv2/Store';

import { getFixturePendingBidFlat, getFixturePendingBidTree } from '@spec/fixtures/bid';
import { getFixtureDonation, getFixturePagedDonations } from '@spec/fixtures/donation';
import { getFixturePagedEvent } from '@spec/fixtures/event';

describe('trackerApi', () => {
  let mock: MockAdapter;
  let server: Server;

  beforeAll(() => {
    mock = new MockAdapter(HTTPUtils.getInstance(), { onNoMatch: 'throwException' });
    const processing = `${window.location.origin.replace(/^http/, 'ws')}/ws/processing/`;
    server = new Server(processing);
  });

  beforeEach(() => {
    store.dispatch(trackerApi.util.resetApiState());
    store.dispatch(setRoot({ root: '//testserver/', limit: 500, csrfToken: 'deadbeef' }));
    mock.reset();
    mock
      .onGet('//testserver/' + Endpoints.EVENTS, { totals: '' })
      .reply(() => [200, getFixturePagedEvent({ amount: 25, donation_count: 1 })]);
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId: 1, tree: false }))
      .reply(() => [200, getFixturePendingBidFlat()]);
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId: 1, tree: true }))
      .reply(() => [200, getFixturePendingBidTree()]);
    mock.onGet('//testserver/' + Endpoints.DONATION_GROUPS).reply(() => [200, ['foobar']]);
    mock.onGet('//testserver/' + Endpoints.DONATIONS({ eventId: 1 })).reply(() => [
      200,
      getFixturePagedDonations([
        { comment: 'This is a comment.', groups: [] },
        { id: 2, comment: 'This is another comment.', pinned: true, commentstate: 'FLAGGED', groups: ['foobar'] },
      ]),
    ]);
  });

  afterEach(() => {
    store.dispatch(trackerApi.util.resetApiState());
  });

  afterAll(() => {
    mock.restore();
    server.close();
  });

  describe('sockets', () => {
    describe('events', () => {
      const params = { queryParams: { totals: '' }, listen: true };
      beforeEach(async () => {
        const oldLength = server.clients().length;
        store.dispatch(trackerApi.endpoints.events.initiate(params));
        expect(server.clients().length).toBe(oldLength + 1);
        await nextUpdate();
      });

      it('listens to incoming messages', async () => {
        const oldData = getData('events', params)[0];
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({ id: 1, amount: 25 }),
          event_total: oldData.amount! + 25,
          donation_count: oldData.donation_count! + 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newData = (await nextData('events', params))[0];
        expect(newData.amount).toBe(oldData.amount! + 25);
        expect(newData.donation_count).toBe(oldData.donation_count! + 1);
      });

      it('ignores messages that do not match the query', async () => {
        const oldData = getData('events', params)[0];
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({ id: 1, amount: 25, event: oldData.id + 1 }),
          event_total: 37,
          donation_count: 17,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newData = (await nextData('events', params))[0];
        expect(newData).toBe(oldData);
      });
    });

    describe('donations', () => {
      const params = { urlParams: { eventId: 1 }, listen: true };

      beforeEach(async () => {
        const oldLength = server.clients().length;
        store.dispatch(trackerApi.endpoints.donations.initiate(params));
        expect(server.clients().length).toBe(oldLength + 1);
        await nextUpdate();
      });

      it('listens to incoming messages', async () => {
        const oldData = getData('donations', params);
        const maxId = Math.max(...oldData.map(d => d.id));
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({ id: maxId + 1 }),
          event_total: 50,
          donation_count: oldData.length + 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newData = await nextData('donations', params);
        expect(newData.length).toBe(oldData.length + 1);
      });

      it('ignores messages that do not match the query', async () => {
        const oldData = getData('donations', params);
        const maxId = Math.max(...oldData.map(d => d.id));
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({ id: maxId + 1, event: 2 }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newData = await nextData('donations', params);
        expect(newData).toBe(oldData);
      });
    });

    // TODO: allDonations

    describe('donation groups', () => {
      const params = { listen: true };

      beforeEach(async () => {
        const oldLength = server.clients().length;
        store.dispatch(trackerApi.endpoints.donationGroups.initiate(params));
        expect(server.clients().length).toBe(oldLength + 1);
        await nextUpdate();
      });

      it('listens to incoming messages', async () => {
        const oldData = getData('donationGroups', params);
        const createMessage: ProcessingEvent = {
          type: 'processing_action',
          actor_name: 'JohnDoe',
          actor_id: 502,
          action: 'group_created',
          group: 'barfoo',
        };
        server.emit('message', JSON.stringify(createMessage));
        const newData = await nextData('donationGroups', params);
        expect(newData).toContain('barfoo');
        expect(newData.length).toBe(oldData.length + 1);
        const deleteMessage = {
          ...createMessage,
          action: 'group_deleted',
        };
        server.emit('message', JSON.stringify(deleteMessage));
        const moreNewData = await nextData('donationGroups', params);
        expect(moreNewData).not.toContain('barfoo');
        expect(moreNewData.length).toBe(oldData.length);
      });
    });
  });

  describe('mutations', () => {
    xdescribe('runs', () => {
      it('TODO', () => {});
    });
    describe('bids', () => {
      const params = { urlParams: { eventId: 1 } };
      let flatId: number;
      let parentId: number;
      let childId: number;

      function getFlat() {
        return getData('bids', params).find(b => b.id === flatId)!;
      }

      function getParent() {
        return getData('bidTree', params).find(b => b.id === parentId)!;
      }

      function getChild() {
        return getParent().options!.find(o => o.id === childId)!;
      }

      beforeEach(async () => {
        store.dispatch(trackerApi.endpoints.bids.initiate(params));
        store.dispatch(trackerApi.endpoints.bidTree.initiate(params));
        await nextUpdate();
        flatId = getData('bids', params).find(b => b.state === 'PENDING')?.id ?? 0;
        parentId = getData('bidTree', params).find(b => b.options?.find(o => o.state === 'PENDING'))?.id ?? 0;
        childId = getParent().options?.find(o => o.state === 'PENDING')?.id ?? 0;
        expect(flatId).toBe(childId);
      });

      it('approve', async () => {
        store.dispatch(trackerApi.endpoints.approveBid.initiate(flatId));

        expect(getFlat().state).toBe('OPENED');
        expect(getChild().state).toBe('OPENED');
        // wait for failure
        await nextUpdate();
        expect(getFlat().state).toBe('PENDING');
        expect(getChild().state).toBe('PENDING');

        mock
          .onPatch('//testserver/' + Endpoints.APPROVE_BID(flatId))
          .reply(() => [200, getFixturePendingBidFlat({}, { name: 'Approved', state: 'OPENED' }).results[1]]);

        store.dispatch(trackerApi.endpoints.approveBid.initiate(flatId));

        expect(getFlat().state).toBe('OPENED');
        expect(getChild().state).toBe('OPENED');
        // wait for success
        await nextUpdate();
        expect(getFlat()).toEqual(jasmine.objectContaining({ state: 'OPENED', name: 'Approved' }));
        // FIXME: only the state is updated for tree children
        expect(getChild().state).toBe('OPENED');
        //expect(getChild()).toEqual(jasmine.objectContaining({ state: 'OPENED', name: 'Approved' }));
      });

      it('deny', async () => {
        store.dispatch(trackerApi.endpoints.denyBid.initiate(flatId));

        expect(getFlat().state).toBe('DENIED');
        expect(getChild().state).toBe('DENIED');
        // wait for failure
        await nextUpdate();
        expect(getFlat().state).toBe('PENDING');
        expect(getChild().state).toBe('PENDING');

        mock
          .onPatch('//testserver/' + Endpoints.DENY_BID(flatId))
          .reply(() => [200, getFixturePendingBidFlat({}, { name: 'Denied', state: 'DENIED' }).results[1]]);

        store.dispatch(trackerApi.endpoints.denyBid.initiate(flatId));

        expect(getFlat().state).toBe('DENIED');
        expect(getChild().state).toBe('DENIED');
        // wait for success
        await nextUpdate();
        expect(getFlat()).toEqual(jasmine.objectContaining({ state: 'DENIED', name: 'Denied' }));
        // FIXME: only the state is updated for tree children
        expect(getChild().state).toBe('DENIED');
        //expect(getChild()).toEqual(jasmine.objectContaining({ state: 'OPENED', name: 'Approved' }));
      });
    });
    describe('donation groups', () => {
      beforeEach(async () => {
        store.dispatch(trackerApi.endpoints.donations.initiate({ urlParams: { eventId: 1 } }));
        store.dispatch(trackerApi.endpoints.donationGroups.initiate());
        await nextUpdate();
      });

      it('create group', async () => {
        store.dispatch(trackerApi.endpoints.createDonationGroup.initiate('barfoo'));
        expect(getData('donationGroups')).toContain('barfoo');
        // wait for failure
        let data = await nextData('donationGroups');
        expect(data).not.toContain('barfoo');

        mock.onPut('//testserver/' + Endpoints.DONATION_GROUP('barfoo')).reply(() => [201, null]);

        store.dispatch(trackerApi.endpoints.createDonationGroup.initiate('barfoo'));
        expect(getData('donationGroups')).toContain('barfoo');
        // wait for success
        data = await nextData('donationGroups');
        expect(data).toContain('barfoo');
      });

      it('delete group', async () => {
        store.dispatch(trackerApi.endpoints.deleteDonationGroup.initiate('foobar'));
        expect(getData('donationGroups')).not.toContain('foobar');
        expect(getData('donations', { urlParams: { eventId: 1 } })[1].groups).not.toContain('foobar');
        // wait for failure
        let data = await nextData('donationGroups');
        expect(data).toContain('foobar');
        expect(getData('donations', { urlParams: { eventId: 1 } })[1].groups).toContain('foobar');

        mock.onDelete('//testserver/' + Endpoints.DONATION_GROUP('foobar')).reply(() => [204, null]);

        store.dispatch(trackerApi.endpoints.deleteDonationGroup.initiate('foobar'));
        expect(getData('donationGroups')).not.toContain('foobar');
        expect(getData('donations', { urlParams: { eventId: 1 } })[1].groups).not.toContain('foobar');
        // wait for success
        data = await nextData('donationGroups');
        expect(data).not.toContain('foobar');
        expect(getData('donations', { urlParams: { eventId: 1 } })[1].groups).not.toContain('foobar');
      });
    });
    describe('donations', () => {
      const params = { urlParams: { eventId: 1 } };
      beforeEach(async () => {
        store.dispatch(trackerApi.endpoints.donations.initiate(params));
        await nextUpdate();
      });

      describe('simple mutations', () => {
        const actionMap: Array<
          [TrackerSimpleDonationMutations, Omit<Partial<Donation>, 'timereceived'>, (id: number) => string]
        > = [
          ['unprocessDonation', { commentstate: 'PENDING', readstate: 'PENDING' }, Endpoints.DONATIONS_UNPROCESS],
          [
            'approveDonationComment',
            { commentstate: 'APPROVED', readstate: 'IGNORED' },
            Endpoints.DONATIONS_APPROVE_COMMENT,
          ],
          ['denyDonationComment', { commentstate: 'DENIED', readstate: 'IGNORED' }, Endpoints.DONATIONS_DENY_COMMENT],
          ['flagDonation', { commentstate: 'APPROVED', readstate: 'FLAGGED' }, Endpoints.DONATIONS_FLAG],
          [
            'sendDonationToReader',
            { commentstate: 'APPROVED', readstate: 'READY' },
            Endpoints.DONATIONS_SEND_TO_READER,
          ],
          ['pinDonation', { pinned: true }, Endpoints.DONATIONS_PIN],
          ['unpinDonation', { pinned: false }, Endpoints.DONATIONS_UNPIN],
          ['readDonation', { readstate: 'READ' }, Endpoints.DONATIONS_READ],
          ['ignoreDonation', { readstate: 'IGNORED' }, Endpoints.DONATIONS_IGNORE],
        ];

        actionMap.forEach(([mutation, fields, endpoint]) => {
          it(mutation, async () => {
            // TODO: check for query parameters
            let data = getData('donations', params);
            const donation = data.find(d => !shallowEqual(d, { ...d, ...fields }));
            expect(donation).toBeDefined();
            const otherDonation = data.find(d => d.id !== donation?.id);
            const id = donation?.id ?? 0;
            store.dispatch(trackerApi.endpoints[mutation].initiate(id));
            expect(getData('donations', params).find(d => d.id === id)).toEqual(jasmine.objectContaining(fields));
            // wait for failure
            data = await nextData('donations', params);
            expect(data.find(d => d.id === id)).toEqual(donation);
            // should not touch other donation at all
            expect(data.find(d => d.id === otherDonation?.id)).toBe(otherDonation);

            mock
              .onPatch('//testserver/' + endpoint(id))
              .reply(() => [
                200,
                getFixtureDonation({ ...fields, id, comment: 'This is a comment.', modcomment: 'Mod changed.' }),
              ]);

            store.dispatch(trackerApi.endpoints[mutation].initiate(id));
            expect(getData('donations', params).find(d => d.id === id)).toEqual(jasmine.objectContaining(fields));
            // wait for success
            data = await nextData('donations', params);
            expect(data.find(d => d.id === id)).toEqual(
              jasmine.objectContaining({
                ...fields,
                modcomment: 'Mod changed.',
              }),
            );
            // should not touch other donation at all
            expect(data.find(d => d.id === otherDonation?.id)).toBe(otherDonation);
          });
        });
      });

      it('edit mod comment', async () => {
        const donation = getData('donations', params)[0];
        const otherDonation = getData('donations', params)[1];
        store.dispatch(
          trackerApi.endpoints.editDonationComment.initiate({ id: donation.id, comment: 'Edited comment.' }),
        );
        expect(getData('donations', params)[0].modcomment).toBe('Edited comment.');
        // wait for failure
        let data = await nextData('donations', params);
        expect(data[0]).toEqual(donation);
        expect(data[1]).toBe(otherDonation);

        mock
          .onPatch('//testserver/' + Endpoints.DONATIONS_COMMENT(donation.id))
          .reply(() => [200, getFixtureDonation({ id: donation.id, modcomment: 'Server comment.' })]);

        store.dispatch(
          trackerApi.endpoints.editDonationComment.initiate({ id: donation.id, comment: 'Edited comment.' }),
        );
        expect(getData('donations', params)[0].modcomment).toBe('Edited comment.');
        // wait for success
        data = await nextData('donations', params);
        expect(data[0].modcomment).toEqual('Server comment.');
        expect(data[1]).toBe(otherDonation);
      });

      it('add group', async () => {
        const donation = getData('donations', params)[0];
        const otherDonation = getData('donations', params)[1];

        store.dispatch(trackerApi.endpoints.addDonationToGroup.initiate({ donationId: donation.id, group: 'foobar' }));
        expect(getData('donations', params)[0].groups).toContain('foobar');
        // wait for failure
        let data = await nextData('donations', params);
        expect(data[0].groups).not.toContain('foobar');
        expect(data[1]).toBe(otherDonation);

        // doesn't actually need any data, just a success response
        mock
          .onPatch('//testserver/' + Endpoints.DONATIONS_GROUPS({ donationId: donation.id, group: 'foobar' }))
          .reply(() => [200, null]);

        store.dispatch(trackerApi.endpoints.addDonationToGroup.initiate({ donationId: donation.id, group: 'foobar' }));
        expect(getData('donations', params)[0].groups).toContain('foobar');
        // wait for success
        data = await nextData('donations', params);
        expect(data[0].groups).toContain('foobar');
        expect(data[1]).toBe(otherDonation);
      });

      it('remove group', async () => {
        const donation = getData('donations', params)[0];
        const otherDonation = getData('donations', params)[1];
        const group = otherDonation.groups?.[0];

        if (group == null) {
          throw new Error('broken');
        }

        store.dispatch(trackerApi.endpoints.removeDonationFromGroup.initiate({ donationId: otherDonation.id, group }));
        expect(getData('donations', params)[1].groups).not.toContain(group);
        // wait for failure
        let data = await nextData('donations', params);
        expect(data[1].groups).toContain(group);
        expect(data[0]).toBe(donation);

        // doesn't actually need any data, just a success response
        mock
          .onDelete('//testserver/' + Endpoints.DONATIONS_GROUPS({ donationId: otherDonation.id, group }))
          .reply(() => [200, null]);

        store.dispatch(trackerApi.endpoints.removeDonationFromGroup.initiate({ donationId: otherDonation.id, group }));
        expect(getData('donations', params)[1].groups).not.toContain(group);
        // wait for success
        data = await nextData('donations', params);
        expect(data[1].groups).not.toContain(group);
        expect(data[0]).toBe(donation);
      });
    });
  });

  function getData<
    const K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints,
    const Params extends Parameters<(typeof trackerApi.endpoints)[K]['select']>[0],
  >(
    k: K,
    params: Params | void,
    state: RootState = store.getState(),
  ): NonNullable<ReturnType<ReturnType<(typeof trackerApi.endpoints)[K]['select']>>['data']> {
    // @ts-ignore
    const { data, error } = trackerApi.endpoints[k].select(params)(state);
    if (data == null) {
      throw new Error(JSON.stringify(error ?? `unable to find data for ${JSON.stringify(params)}`));
    }
    return data;
  }

  async function nextData<
    const K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints,
    const Params extends Parameters<(typeof trackerApi.endpoints)[K]['select']>[0],
  >(
    k: K,
    params: Params | void,
  ): Promise<NonNullable<ReturnType<ReturnType<(typeof trackerApi.endpoints)[K]['select']>>['data']>> {
    // @ts-ignore
    return getData(k, params, await nextUpdate());
  }

  async function nextUpdate() {
    return await new Promise<RootState>(resolve => {
      const unsub = store.subscribe(() => {
        unsub();
        resolve(store.getState());
      });
    });
  }
});
