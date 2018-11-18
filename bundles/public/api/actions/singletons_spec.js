import singletons from './singletons';
import $ from 'jquery';

describe('singletons actions', () => {
    let dispatchSpy;
    let action;

    beforeEach(() => {
        dispatchSpy = jasmine.createSpy('dispatch');
        window.API_ROOT = 'http://localhost:55555/';
    });

    describe('#fetchMe', () => {
        beforeEach(() => {
            action = singletons.fetchMe();
        });

        it('returns a thunk', () => {
            expect(action).toEqual(jasmine.any(Function));
        });

        describe('when the thunk is called', () => {
            let d;
            beforeEach(() => {
                d = $.Deferred();
                spyOn($, 'ajax').and.returnValue(d.promise());
                action(dispatchSpy);
            });

            it('dispatches a loading action for "me"', () => {
                expect(dispatchSpy).toHaveBeenCalledWith(jasmine.objectContaining({type: 'MODEL_STATUS_LOADING', model: { type: 'me'}}));
            });

            it('sends a request to the ME endpoint', () => {
                expect($.ajax).toHaveBeenCalledWith(jasmine.objectContaining({url: `${API_ROOT}me`}));
            });

            describe('when the call succeeds', () => {
                beforeEach(() => {
                    d.resolve({username: 'jazzaboo'});
                });

                it('dispatches a load complete action for "me"', () => {
                    expect(dispatchSpy).toHaveBeenCalledWith(jasmine.objectContaining({type: 'MODEL_STATUS_SUCCESS', model: { type: 'me'}}));
                });

                it('dispatches a LOAD_ME action with the returned user', () => {
                    expect(dispatchSpy).toHaveBeenCalledWith(jasmine.objectContaining({type: 'LOAD_ME', me: {username: 'jazzaboo'}}));
                });
            });

            describe('when the call succeeds', () => {
                beforeEach(() => {
                    d.reject();
                });

                it('dispatches a load error action for "me"', () => {
                    expect(dispatchSpy).toHaveBeenCalledWith(jasmine.objectContaining({type: 'MODEL_STATUS_ERROR', model: { type: 'me'}}));
                });

                it('dispatches a LOAD_ME action with an anonymous user', () => {
                    expect(dispatchSpy).toHaveBeenCalledWith(jasmine.objectContaining({type: 'LOAD_ME', me: {}}));
                });
            });
        });
    });
});
