const sharedConfig = require('./shared.webpack')({context: {DEBUG: true}});

module.exports = function (config) {
  config.set({
    autoWatch: true,

    browsers: ['ChromeHeadless'],

    frameworks: ['jasmine'],

    files: [
      'js/init/index.js',
      'js/**/*_spec.js',
      'js/**/*Spec.js',
    ],

    preprocessors: {
      'js/init/*.js': ['webpack'],
      'js/**/*_spec.js': ['webpack'],
      'js/**/*Spec.js': ['webpack'],
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
