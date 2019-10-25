const sharedConfig = require('./shared.webpack')({context: {DEBUG: true}});
const webpackConfig = require('./webpack.config.js');
process.env.CHROME_BIN = require('puppeteer').executablePath();
module.exports = function (config) {
  config.set({
    autoWatch: true,
    browsers: ['ChromeHeadless'],
    frameworks: ['jasmine'],
    files: [
      'bundles/init/index.js',
      'bundles/**/*_spec.js',
      'bundles/**/*Spec.js',
    ],
    preprocessors: {
      'bundles/init/*.js': ['webpack'],
      'bundles/**/*_spec.js': ['webpack'],
      'bundles/**/*Spec.js': ['webpack'],
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
    plugins: [
      require('karma-webpack'),
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
    ],
  });
};
