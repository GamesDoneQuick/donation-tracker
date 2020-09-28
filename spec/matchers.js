beforeEach(() => {
  jasmine.addMatchers({
    toExist: function () {
      return {
        compare: function (actual) {
          if (!actual.exists) {
            throw new Error(`Expected ${actual} to have an 'exists' method`);
          }
          const passed = actual.exists();

          return {
            pass: passed,
            message: `Expected element ${passed ? 'not ' : ' '}to exist`,
          };
        },
      };
    },
    toHaveLength: function () {
      return {
        compare: function (actual, expected) {
          if (actual.length == null) {
            throw new Error(`Expected ${actual} to have a 'length' property`);
          }

          const passed = actual.length === expected;

          return {
            pass: passed,
            message: `Expected ${actual} ${passed ? 'not ' : ' '}to have length ${expected}, but it ${
              passed ? 'did' : `had length ${actual.length}`
            }`,
          };
        },
      };
    },
  });
});
