const webpack = require('webpack');
const keyMirror = require('keymirror');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const WebpackManifestPlugin = require('webpack-yam-plugin');
const path = require('path');
const packageJSON = require('./package');
const TerserPlugin = require('terser-webpack-plugin');

const PROD = process.env.NODE_ENV === 'production';

console.log(PROD ? 'PRODUCTION BUILD' : 'DEVELOPMENT BUILD');

function compact(array) {
  return [...array].filter(n => !!n);
}

module.exports = {
  context: __dirname,
  mode: PROD ? 'production' : 'development',
  entry: {
    admin: './bundles/admin',
    tracker: './bundles/tracker',
  },
  output: {
    filename: PROD ? 'tracker-[name]-[hash].js' : 'tracker-[name].js',
    pathinfo: true,
    path: __dirname + '/static/gen',
    publicPath: '/static/gen',
  },
  module: {
    rules: [
      {
        test: /\.[jt]sx?$/,
        exclude: /node_modules/,
        use: compact([!PROD && 'react-hot-loader/webpack', 'babel-loader']),
      },
      {
        test: /\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
            options: {
              // only enable hot in development
              hmr: !PROD,
            },
          },
          {
            loader: 'css-loader',
            options: {
              sourceMap: true,
              modules: {
                mode: 'local',
                localIdentName: '[local]--[hash:base64:10]',
              },
            },
          },
          'postcss-loader',
        ],
      },
      {
        test: /\.(png|jpg|svg)$/,
        use: ['url-loader'],
      },
      {
        test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        use: ['url-loader?limit=10000&mimetype=application/font-woff'],
      },
      {
        test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        use: ['file-loader'],
      },
    ],
  },
  node: {
    fs: 'empty',
  },
  resolve: {
    alias: {
      ui: path.resolve('bundles'),
      ...(PROD ? {} : { 'react-dom': '@hot-loader/react-dom' }),
    },
    extensions: ['.js', '.ts', '.tsx'],
  },
  optimization: {
    splitChunks: {
      chunks: 'async',
    },
    minimizer: [
      new TerserPlugin({
        cache: true,
        parallel: true,
        sourceMap: true,
        terserOptions: {
          output: {
            comments: /@license/i,
          },
        },
      }),
    ],
  },
  externals: keyMirror(packageJSON.dependencies),
  devServer: PROD
    ? {}
    : {
        proxy: [
          {
            context: ['/admin', '/logout', '/api', '/ui', '/static', '/tracker', '/donate', '/media'],
            target: 'http://localhost:8000/',
            headers: { 'X-Webpack': 1 },
          },
        ],
        allowedHosts: ['localhost', '127.0.0.1', '.ngrok.io'],
      },
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
  devtool: PROD ? 'source-map' : 'eval-source-map',
};
