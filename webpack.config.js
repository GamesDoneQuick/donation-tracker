const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const WebpackManifestPlugin = require('webpack-yam-plugin');
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');

const PROD = process.env.NODE_ENV === 'production';
const SOURCE_MAPS = +(process.env.SOURCE_MAPS || 0);
const NO_MANIFEST = +(process.env.NO_MANIFEST || 0);
const NO_HMR = PROD || +(process.env.NO_HMR || 0);

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
    filename: PROD ? 'tracker-[name]-[contenthash].js' : 'tracker-[name].js',
    pathinfo: true,
    path: __dirname + '/tracker/static/gen',
    publicPath: '/static/gen',
  },
  stats: 'minimal',
  module: {
    rules: [
      {
        test: /\.[jt]sx?$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'swc-loader',
            options: {
              jsc: {
                assumptions: {
                  iterableIsArray: false,
                },
                parser: {
                  syntax: 'typescript',
                  tsx: true,
                },
                loose: false,
                transform: {
                  react: {
                    refresh: !PROD,
                    runtime: 'classic',
                  },
                },
              },
            },
          },
        ],
      },
      {
        test: /\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
          },
          {
            loader: 'css-loader',
            options: {
              modules: false,
            },
          },
          'postcss-loader',
        ],
        exclude: /\.mod\.css$/,
      },
      {
        test: /\.mod\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
          },
          {
            loader: 'css-loader',
            options: {
              sourceMap: true,
              modules: {
                mode: 'local',
                localIdentName: '[local]--[contenthash:base64:10]',
              },
            },
          },
          'postcss-loader',
        ],
      },
      {
        test: /\.(png|jpg|svg)$/,
        use: ['asset/resource'],
      },
      {
        test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        type: 'asset',
        generator: {
          mimetype: 'application/font-woff',
        },
      },
      {
        test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        type: 'asset/resource',
      },
    ],
  },
  resolve: {
    alias: {
      '@admin': path.resolve('bundles', 'admin'),
      '@common': path.resolve('bundles', 'common'),
      '@public': path.resolve('bundles', 'public'),
      '@tracker': path.resolve('bundles', 'tracker'),
      '@uikit': path.resolve('bundles', 'uikit'),
    },
    extensions: ['.js', '.ts', '.tsx'],
    fallback: {
      fs: false,
      path: false,
      util: false,
    },
  },
  optimization: {
    minimizer: [
      new TerserPlugin({
        parallel: true,
      }),
    ],
  },
  devServer: PROD
    ? {}
    : {
        proxy: [
          {
            context: ['/admin', '/logout', '/api', '/ui', '/static', '/tracker', '/donate', '/media'],
            target: process.env.TRACKER_HOST || 'http://127.0.0.1:8000/',
            ws: true,
          },
        ],
        allowedHosts: ['localhost', '127.0.0.1', '.ngrok.io'],
        hot: true,
      },
  plugins: compact([
    !NO_MANIFEST &&
      new WebpackManifestPlugin({
        manifestPath: __dirname + '/tracker/ui-tracker.manifest.json',
        outputRoot: __dirname + '/tracker/static',
        fileFilter: file => !/\.hot-update\.js$/.test(file),
      }),
    new MiniCssExtractPlugin({
      filename: PROD ? 'tracker-[name]-[contenthash].css' : 'tracker-[name].css',
      chunkFilename: PROD ? '[id].[contenthash].css' : '[id].css',
      ignoreOrder: false,
    }),
    new webpack.EnvironmentPlugin({
      NODE_ENV: 'development',
    }),
    !PROD && new ReactRefreshWebpackPlugin(),
    new webpack.ProgressPlugin(),
  ]),
  devtool: SOURCE_MAPS ? (PROD ? 'source-map' : 'eval-source-map') : false,
};
