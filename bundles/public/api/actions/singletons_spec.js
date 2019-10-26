import fetchMock from 'fetch-mock';
import thunk from 'redux-thunk';
import configureMockStore from 'redux-mock-store';

import singletons from './singletons';

const mockStore = configureMockStore([thunk]);

const expectActions = (store, action, expected) => {
    store.dispatch(action).then(() => {
        expect(store.getActions()).toEqual(expected);
    });
}

describe('singletons actions', () => {
    let action;
    let store;

    beforeEach(() => {
        window.API_ROOT = 'http://localhost:55555/';
        fetchMock.restore();
    });

    describe('#fetchMe', () => {
        beforeEach(() => {
            action = singletons.fetchMe();
            store = mockStore();
        });

        it('returns a thunk', () => {
            expect(action).toEqual(jasmine.any(Function));
        });

        describe('when the thunk is called', () => {
            beforeEach(() => {
                fetchMock
                    .restore()
                    .getOnce(`${API_ROOT}me`, {
                        body: { todos: ['do something'] },
                        headers: { 'content-type': 'application/json' }
                    });
            });

            it('dispatches a loading action for "me"', () => {
                expectActions(store, action, [{type: 'MODEL_STATUS_LOADING', model: { type: 'me'}}]);
            });

            it('sends a request to the ME endpoint', () => {
                store.dispatch(action).then(() => {
                    expect(fetchMock.done());
                });
            });

            describe('when the call succeeds', () => {
                const ME_DATA = {username: 'jazzaboo'};
                beforeEach(() => {
                    fetchMock
                        .restore()
                        .getOnce(`${API_ROOT}me`, {
                            body: ME_DATA,
                            headers: { 'content-type': 'application/json' }
                        });
                });

                it('dispatches a load success and LOAD_ME for "me"', () => {
                    const expectedActions = [
                        {type: 'MODEL_STATUS_SUCCESS', model: { type: 'me'}},
                        {type: 'LOAD_ME', me: ME_DATA},
                    ];
                    expectActions(store, action, expectedActions);
                });
            });

            describe('when the call fails', () => {
                beforeEach(() => {
                    fetchMock
                        .restore()
                        .getOnce(`${API_ROOT}me`, new Promise((res, reject) => reject()));
                });

                it('dispatches a load error and LOAD_ME for an anonymous user', () => {
                    const expectedActions = [{type: 'MODEL_STATUS_ERROR', model: { type: 'me'}}];
                    store.dispatch(action).then(() => {
                        expect(store.getActions()).toEqual(expectedActions);
                    });
                });
            });
        });
    });
});
