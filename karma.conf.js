const webpackConfig = require('./webpack.config.js');
process.env.CHROME_BIN = require('puppeteer').executablePath();
module.exports = function(config) {
  config.set({
    autoWatch: true,
    browsers: ['ChromeHeadless_without_sandbox'],
    frameworks: ['jasmine'],
    customLaunchers: {
      ChromeHeadless_without_sandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox'],
      },
    },
    files: [
      'bundles/**/*Spec.js',
      'bundles/**/*Spec.ts',
      'bundles/**/*Spec.tsx',
      'bundles/**/*.spec.tsx',
      'bundles/**/*.spec.ts',
      './spec/Suite.tsx',
    ],
    preprocessors: {
      'bundles/**/*Spec.js': ['webpack'],
      'bundles/**/*Spec.ts': ['webpack'],
      'bundles/**/*Spec.tsx': ['webpack'],
      'bundles/**/*.spec.tsx': ['webpack'],
      'bundles/**/*.spec.ts': ['webpack'],
      './spec/Suite.tsx': ['webpack'],
    },
    webpack: {
      ...webpackConfig,
      mode: 'development',
    },
    webpackMiddleware: {
      // webpack-dev-middleware configuration
      // i. e.
      noInfo: true,
      poll: 1000,
    },
    plugins: ['karma-*'],
  });
};
