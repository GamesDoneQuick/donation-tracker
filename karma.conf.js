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
    files: ['./spec/entry.js'],
    preprocessors: {
      './spec/entry.js': ['webpack'],
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
