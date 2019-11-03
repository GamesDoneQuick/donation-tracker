const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const WebpackManifestPlugin = require('webpack-yam-plugin');
const sharedConfig = require('./shared.webpack')();

const PROD = process.env.NODE_ENV === 'production';

console.log(PROD ? 'PRODUCTION BUILD' : 'DEVELOPMENT BUILD');

module.exports = {
  context: __dirname,
  mode: PROD ? 'production' : 'development',
  entry: {
    admin: ['./bundles/init', './bundles/admin'],
    donate: ['./bundles/init', './bundles/donate'],
  },
  output: {
    filename: PROD ? 'tracker-[name]-[hash].js' : 'tracker-[name].js',
    pathinfo: true,
    path: __dirname + '/static/gen',
    publicPath: '/static/gen',
  },
  module: sharedConfig.module,
  plugins: [
    new webpack.optimize.OccurrenceOrderPlugin(),
    new WebpackManifestPlugin({
      manifestPath: __dirname + '/ui-tracker.manifest.json',
      outputRoot: __dirname + '/static',
    }),
    new MiniCssExtractPlugin({
      filename: PROD ? 'tracker-[name]-[hash].css' : 'tracker-[name].css',
      chunkFilename: PROD ? '[id].[hash].css' : '[id].css',
      ignoreOrder: false,
    }),
    new webpack.EnvironmentPlugin({
      NODE_ENV: 'development',
    }),
  ],
  devServer: PROD ? {} : sharedConfig.devServer,
  resolve: sharedConfig.resolve,
  devtool: PROD ? 'source-map' : 'eval-source-map',
};
