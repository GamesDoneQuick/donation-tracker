const sharedConfig = require('./shared.webpack')({context: {DEBUG: true}});
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
      module: sharedConfig.module,
      node: sharedConfig.node,
      resolve: sharedConfig.resolve,
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
