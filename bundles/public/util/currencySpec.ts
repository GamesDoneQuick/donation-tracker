import * as CurrencyUtils from './currency';

describe('CurrencyUtils', () => {
  describe('asCurrency', () => {
    it('formats euros', () => {
      const result = CurrencyUtils.asCurrency(123456.789, { currency: 'EUR', maximumFractionDigits: 0 });

      expect(result).toEqual('€123,457');
    });

    it('formats with minimum digits', () => {
      const result = CurrencyUtils.asCurrency(20, { currency: 'USD', minimumFractionDigits: 2 });

      expect(result).toEqual('$20.00');
    });

    it('formats currency with full name', () => {
      const result = CurrencyUtils.asCurrency(20, { currency: 'UAH', currencyDisplay: 'name' });

      expect(result).toEqual('20.00 Ukrainian hryvnias');
    });
  });

  describe('getCurrencySymbol', () => {
    it('returns dollar symbol for USD', () => {
      const result = CurrencyUtils.getCurrencySymbol('USD');

      expect(result).toEqual('$');
    });
    it('returns euro symbol for EUR', () => {
      const result = CurrencyUtils.getCurrencySymbol('EUR');

      expect(result).toEqual('€');
    });
    it('returns blank string for wrong input', () => {
      const result = CurrencyUtils.getCurrencySymbol('GDQ');

      expect(result).toEqual('');
    });
  });
});
