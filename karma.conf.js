const webpack = require('webpack');
const webpackConfig = require('./webpack.config.js');
process.env.CHROME_BIN = require('puppeteer').executablePath();

module.exports = function (config) {
  const mode = 'development';

  config.set({
    autoWatch: true,
    browsers: ['ChromeHeadless_without_sandbox'],
    frameworks: ['jasmine', 'webpack'],
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
      mode,
      plugins: [
        ...webpackConfig.plugins,
        new webpack.ProvidePlugin({
          // Make a global `process` variable that points to the `process` package,
          // because the `util` package expects there to be a global variable named `process`.
          // Thanks to https://stackoverflow.com/a/65018686/14239942
          process: 'process/browser.js',
        }),
      ],
      resolve: {
        ...webpackConfig.resolve,
        fallback: {
          ...webpackConfig.resolve.fallback,
          // Various packages inside of karma and around testing utilize node
          // features, but webpack 5 does not bundle polyfills by default
          // anymore, so we have to vendor them ourselves.
          buffer: require.resolve('buffer'),
          events: require.resolve('events'),
          util: require.resolve('util'),
          stream: require.resolve('stream-browserify'),
          string_decoder: require.resolve('string_decoder'),
        },
      },
    },
    webpackMiddleware: {
      // webpack-dev-middleware configuration
      // i. e.
      noInfo: true,
      poll: 1000,
    },
    plugins: [require('karma-chrome-launcher'), require('karma-jasmine'), require('karma-webpack')],
  });
};
