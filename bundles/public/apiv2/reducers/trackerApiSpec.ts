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
import {
  BidQuery,
  DonationGroupQuery,
  DonationQuery,
  TrackerApiInfiniteQueryEndpoints,
  TrackerApiQueryArgument,
  TrackerApiQueryData,
  TrackerApiQueryEndpoints,
} from '@public/apiv2/reducers/trackerBaseApi';
import { RootState, store } from '@public/apiv2/Store';

import { getFixtureDonationBid, getFixtureMixedBidsFlat, getFixtureMixedBidsTree } from '@spec/fixtures/bid';
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
    mock.onGet('//testserver/' + Endpoints.EVENTS, { totals: '' }).reply(() => [200, getFixturePagedEvent({}, [25])]);
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId: 1, feed: 'all', tree: false }))
      .reply(() => [200, getFixtureMixedBidsFlat()]);
    mock
      .onGet('//testserver/' + Endpoints.BIDS({ eventId: 1, feed: 'all', tree: true }))
      .reply(() => [200, getFixtureMixedBidsTree()]);
    mock.onGet('//testserver/' + Endpoints.DONATION_GROUPS).reply(() => [200, ['foobar']]);
    mock.onGet('//testserver/' + Endpoints.DONATIONS(1)).reply(() => [
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
      const params: DonationQuery = { urlParams: 1, listen: true };

      beforeEach(async () => {
        const oldLength = server.clients().length;
        store.dispatch(trackerApi.endpoints.donations.initiate(params));
        store.dispatch(trackerApi.endpoints.allDonations.initiate(params));
        expect(server.clients().length).toBe(oldLength + 1);
        await nextUpdate();
      });

      it('listens to incoming messages', async () => {
        const oldData = getData('donations', params);
        const oldAllData = getData('allDonations', params);
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
        const newAllData = getData('allDonations', params);
        expect(newData.length).toBe(oldData.length + 1);
        expect(newAllData.pages[0].results.length).toBe(oldAllData.pages[0].results.length + 1);
      });

      it('ignores messages that do not match the query', async () => {
        const oldData = getData('donations', params);
        const oldAllData = getData('allDonations', params);
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
        const newAllData = getData('allDonations', params);
        expect(newData).toBe(oldData);
        expect(newAllData).toBe(oldAllData);
      });
    });

    describe('donation groups', () => {
      const params: DonationGroupQuery = { listen: true };

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

    describe('bids', () => {
      const params: BidQuery = { urlParams: { eventId: 1, feed: 'all' }, listen: true };

      beforeEach(async () => {
        const oldLength = server.clients().length;
        store.dispatch(trackerApi.endpoints.bids.initiate(params));
        store.dispatch(trackerApi.endpoints.bidTree.initiate(params));
        expect(server.clients().length).toBe(oldLength + 1);
        await nextUpdate();
      });

      it('processes top level challenges', async () => {
        const oldFlatData = getData('bids', params);
        const oldTreeData = getData('bidTree', params);
        const flatChallenge = oldFlatData.find(b => b.parent == null && b.istarget === true)!;
        const treeChallenge = oldTreeData.find(b => b.istarget === true)!;
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({
            bids: [
              getFixtureDonationBid({
                bid: flatChallenge.id,
                bid_state: 'CLOSED', // simulating autoclose
                bid_count: flatChallenge.count + 1,
                bid_total: flatChallenge.total + flatChallenge.goal!,
                amount: flatChallenge.goal!,
              }),
            ],
          }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newFlatData = await nextData('bids', params);
        const newTreeData = getData('bidTree', params);
        const newFlatChallenge = newFlatData.find(b => b.parent == null && b.istarget === true);
        expect(newFlatChallenge?.count).toBe(flatChallenge.count + 1);
        expect(newFlatChallenge?.total).toBe(flatChallenge.total + flatChallenge.goal!);
        expect(newFlatChallenge?.state).toBe('CLOSED');
        const newTreeChallenge = newTreeData.find(b => b.istarget === true);
        expect(newTreeChallenge?.count).toBe(treeChallenge.count + 1);
        expect(newTreeChallenge?.total).toBe(treeChallenge.total + treeChallenge.goal!);
        expect(newTreeChallenge?.state).toBe('CLOSED');
      });

      it('processes chains', async () => {
        const oldFlatData = getData('bids', params);
        const oldTreeData = getData('bidTree', params);
        const flatChain = oldFlatData.find(b => b.chain && b.istarget)!;
        const flatSteps = oldFlatData.filter(b => b.chain && !b.istarget);
        const treeChain = oldTreeData.find(b => b.chain)!;
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({
            bids: [
              getFixtureDonationBid({
                bid: flatChain.id,
                bid_count: flatChain.count + 1,
                bid_total: flatChain.total + flatChain.goal! + 50,
                amount: flatChain.goal! + 50,
              }),
            ],
          }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newFlatData = await nextData('bids', params);
        const newTreeData = getData('bidTree', params);
        const newFlatChain = newFlatData.find(b => b.chain && b.istarget)!;
        const newFlatSteps = newFlatData.filter(b => b.chain && !b.istarget);
        const newTreeChain = newTreeData.find(b => b.chain)!;
        expect(newFlatChain.total)
          .withContext('new flat total')
          .toBe(flatChain.total + flatChain.goal! + 50);
        expect(newFlatSteps[0].total)
          .withContext('new flat step total')
          .toBe(flatSteps[0].total + 50);
        expect(newTreeChain.total)
          .withContext('new tree total')
          .toBe(treeChain.total + treeChain.goal! + 50);
        expect(newTreeChain.chain_steps?.[0].total)
          .withContext('new tree step total')
          .toBe((treeChain.chain_steps?.[0].total ?? 0) + 50);
      });

      it('processes children and updates parent totals', async () => {
        const oldFlatData = getData('bids', params);
        const oldTreeData = getData('bidTree', params);
        const flatParent = oldFlatData.find(b => b.parent == null && b.istarget === false)!;
        const flatAccepted = oldFlatData.find(b => b.parent === flatParent.id && b.state === flatParent.state)!;
        const treeParent = oldTreeData.find(b => b.istarget === false)!;
        const treeAccepted = treeParent.options!.find(c => c.state === treeParent.state)!;
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({
            bids: [
              getFixtureDonationBid({
                bid: flatAccepted.id,
                bid_count: flatAccepted.count + 1,
                bid_total: flatAccepted.total + 25,
                amount: 25,
              }),
            ],
          }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newFlatData = await nextData('bids', params);
        const newTreeData = getData('bidTree', params);
        const newFlatParent = newFlatData.find(b => b.id === flatParent.id);
        expect(newFlatParent?.count)
          .withContext('flat parent')
          .toBe(flatParent.count + 1);
        expect(newFlatParent?.total)
          .withContext('flat parent')
          .toBe(flatParent.total + 25);
        const newFlatAccepted = newFlatData.find(b => b.id === flatAccepted.id);
        expect(newFlatAccepted?.count)
          .withContext('flat child')
          .toBe(flatAccepted.count + 1);
        expect(newFlatAccepted?.total)
          .withContext('flat child')
          .toBe(flatAccepted.total + 25);
        const newTreeParent = newTreeData.find(b => b.id === treeParent.id);
        expect(newTreeParent?.count).toBe(treeParent.count + 1);
        expect(newTreeParent?.total).toBe(treeParent.total + 25);
        const newTreeAccepted = newTreeParent?.options?.find(b => b.id === treeAccepted.id);
        expect(newTreeAccepted?.count).toBe(treeAccepted.count + 1);
        expect(newTreeAccepted?.total).toBe(treeAccepted.total + 25);
      });

      it('does not apply pending bids to the parent total', async () => {
        const oldFlatData = getData('bids', params);
        const oldTreeData = getData('bidTree', params);
        const flatParent = oldFlatData.find(b => b.parent == null && b.istarget === false)!;
        const flatPending = oldFlatData.find(b => b.parent === flatParent.id && b.state === 'PENDING')!;
        const treeParent = oldTreeData.find(b => b.istarget === false)!;
        const treePending = treeParent.options!.find(c => c.state === 'PENDING')!;
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({
            bids: [
              getFixtureDonationBid({
                bid: flatPending.id,
                bid_state: 'PENDING',
                bid_count: flatPending.count + 1,
                bid_total: flatPending.total + 25,
                amount: 25,
              }),
            ],
          }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newFlatData = await nextData('bids', params);
        const newTreeData = getData('bidTree', params);
        // does not modify flat parent at all
        expect(newFlatData.find(b => b.id === flatParent.id)).toBe(flatParent);
        const newFlatPending = newFlatData.find(b => b.id === flatPending.id);
        expect(newFlatPending?.count).toBe(flatPending.count + 1);
        expect(newFlatPending?.total).toBe(flatPending.total + 25);
        // does not modify tree parent count/total, just the options
        const newTreeParent = newTreeData.find(b => b.id === treeParent.id);
        expect(newTreeParent?.count).toBe(treeParent.count);
        expect(newTreeParent?.total).toBe(treeParent.total);
        const newTreePending = newTreeParent?.options?.find(b => b.id === treePending.id);
        expect(newTreePending?.count).toBe(treePending.count + 1);
        expect(newTreePending?.total).toBe(treePending.total + 25);
      });

      it('ignores messages that do not match the query', async () => {
        const oldFlatData = getData('bids', params);
        const oldTreeData = getData('bidTree', params);
        const message: ProcessingEvent = {
          type: 'donation_received',
          donation: getFixtureDonation({
            event: 2,
            bids: [getFixtureDonationBid()],
          }),
          event_total: 50,
          donation_count: 1,
          posted_at: DateTime.now().toISO()!,
        };
        server.emit('message', JSON.stringify(message));
        const newFlatData = await nextData('bids', params);
        const newTreeData = getData('bidTree', params);
        expect(newFlatData).toBe(oldFlatData);
        expect(newTreeData).toBe(oldTreeData);
      });

      describe('invalidates tags', () => {
        function waitForNextLoading() {
          return new Promise<void>(resolve => {
            let bids = false,
              bidTree = false;
            const unsub = store.subscribe(() => {
              const state = store.getState();

              if (trackerApi.endpoints.bids.select(params)(state).isLoading) {
                bids = true;
              }
              if (trackerApi.endpoints.bidTree.select(params)(state).isLoading) {
                bidTree = true;
              }
              if (bids && bidTree) {
                resolve();
                unsub();
              }
            });
          });
        }

        it('when bid belongs but was not known already', async () => {
          const loading = waitForNextLoading();
          const message: ProcessingEvent = {
            type: 'donation_received',
            donation: getFixtureDonation({
              bids: [
                getFixtureDonationBid({
                  bid: 501,
                  bid_count: 1,
                  bid_total: 25,
                  amount: 25,
                }),
              ],
            }),
            event_total: 50,
            donation_count: 1,
            posted_at: DateTime.now().toISO()!,
          };
          server.emit('message', JSON.stringify(message));
          await loading;
        });

        xit('when bid parent cannot be found', async () => {
          // TODO this is pathological, and I'm not sure how it could happen in the real world
        });

        xit('when bid no longer belongs', async () => {
          // TODO e.g. listening to open feed but a bid gets closed
        });
      });
    });
  });

  describe('mutations', () => {
    xdescribe('runs', () => {
      it('TODO', () => {});
    });

    describe('bids', () => {
      const params: BidQuery = { urlParams: { eventId: 1, feed: 'all' } };
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
          .reply(() => [
            200,
            { ...getFixtureMixedBidsFlat().results.find(b => b.id === flatId), name: 'Approved', state: 'OPENED' },
          ]);

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
          .reply(() => [
            200,
            { ...getFixtureMixedBidsFlat().results.find(b => b.id === flatId), name: 'Denied', state: 'DENIED' },
          ]);

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
      const donationParams: DonationQuery = { urlParams: 1 };
      beforeEach(async () => {
        store.dispatch(trackerApi.endpoints.donations.initiate(donationParams));
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
        expect(getData('donations', donationParams)[1].groups).not.toContain('foobar');
        // wait for failure
        let data = await nextData('donationGroups');
        expect(data).toContain('foobar');
        expect(getData('donations', donationParams)[1].groups).toContain('foobar');

        mock.onDelete('//testserver/' + Endpoints.DONATION_GROUP('foobar')).reply(() => [204, null]);

        store.dispatch(trackerApi.endpoints.deleteDonationGroup.initiate('foobar'));
        expect(getData('donationGroups')).not.toContain('foobar');
        expect(getData('donations', donationParams)[1].groups).not.toContain('foobar');
        // wait for success
        data = await nextData('donationGroups');
        expect(data).not.toContain('foobar');
        expect(getData('donations', donationParams)[1].groups).not.toContain('foobar');
      });
    });

    describe('donations', () => {
      const params: DonationQuery = { urlParams: 1 };
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
    const Params extends TrackerApiQueryArgument<K>,
  >(k: K, params: Params | void, state: RootState = store.getState()): TrackerApiQueryData<K> {
    // @ts-expect-error params is unhappy
    const { data, error } = trackerApi.endpoints[k].select(params)(state);
    if (data == null) {
      throw new Error(JSON.stringify(error ?? `unable to find data for \`${k}\`, ${JSON.stringify(params)}`));
    }
    // @ts-expect-error return value is unhappy
    return data;
  }

  async function nextData<
    const K extends keyof TrackerApiQueryEndpoints | keyof TrackerApiInfiniteQueryEndpoints,
    const Params extends TrackerApiQueryArgument<K>,
  >(k: K, params: Params | void): Promise<TrackerApiQueryData<K>> {
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
