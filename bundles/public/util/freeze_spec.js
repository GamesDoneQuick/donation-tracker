import freeze from './freeze';

describe('util.freeze', () => {
    let frozen;

    beforeEach(() => {
        frozen = freeze({a: {b: 1}});
    });

    it('returns the original', () => {
        expect(frozen.a.b).toBe(1);
    });

    it('returns the same object if it is already frozen', () => {
        expect(freeze(frozen)).toBe(frozen);
    });

    it('freezes top level', () => {
        try {
            frozen.a = 'bad';
        } catch(e) {} // doesn't always throw?
        expect(frozen.a).not.toBe('bad');
    });

    it('deeply freezes', () => {
        try {
            frozen.a.d = 'bad';
        } catch(e) {} // doesn't always throw?
        expect(frozen.a.d).not.toBe('bad');
    });
});
