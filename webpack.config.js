const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HTMLWebpackPlugin = require('html-webpack-plugin');
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
const path = require('path');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');

const PROD = process.env.NODE_ENV === 'production';
const SOURCE_MAPS = process.env.SOURCE_MAPS ?? false;
const ANALYZE = process.env.ANALYZE ?? false;
const NO_MANIFEST = !!process.env.NO_MANIFEST ?? false;
const PROJECT_ROOT = __dirname;
const STATIC_ROOT = process.env.STATIC_ROOT ?? '/static/gen';

console.log(PROD ? 'PRODUCTION BUILD' : 'DEVELOPMENT BUILD');

const BUNDLE_TO_TEMPLATE_MAP = {
  admin: PROJECT_ROOT + '/tracker/templates/ui/index.html',
  tracker: PROJECT_ROOT + '/tracker/templates/ui/index.html',
  processing: PROJECT_ROOT + '/tracker/templates/ui/minimal.html',
};

function generateHTMLWebpackPlugins() {
  return Object.entries(BUNDLE_TO_TEMPLATE_MAP).map(([bundle, template]) => {
    return new HTMLWebpackPlugin({
      template,
      chunks: [bundle],
      filename: PROJECT_ROOT + `/tracker/templates/ui/generated/${bundle}.html`,
      minify: false,
      inject: false,
    });
  });
}

function compact(array) {
  return [...array].filter(n => !!n);
}

module.exports = {
  context: PROJECT_ROOT,
  mode: PROD ? 'production' : 'development',
  entry: {
    admin: './bundles/admin',
    tracker: './bundles/tracker',
    processing: './bundles/processing',
  },
  output: {
    filename: PROD ? 'tracker-[name]-[contenthash].js' : 'tracker-[name].js',
    pathinfo: true,
    path: PROJECT_ROOT + '/tracker/static/gen',
    publicPath: STATIC_ROOT,
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
              env: {
                targets: 'defaults',
              },
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
      '@processing': path.resolve('bundles', 'processing'),
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
  devServer: PROD
    ? {}
    : {
        proxy: [
          {
            context: ['/tracker/api'],
            target: process.env.TRACKER_API_HOST || process.env.TRACKER_HOST || 'http://127.0.0.1:8000/',
            changeOrigin: !!(process.env.TRACKER_API_HOST || process.env.TRACKER_HOST),
          },
          {
            context: ['/admin', '/logout', '/ui', '/static', '/tracker', '/donate', '/media'],
            target: process.env.TRACKER_HOST || 'http://127.0.0.1:8000/',
            changeOrigin: !!process.env.TRACKER_HOST,
            cookieDomainRewrite: '',
            ws: true,
          },
        ],
        allowedHosts: ['localhost', '127.0.0.1', '.ngrok.io', '.ngrok.app'],
        hot: true,
        // HTMLWebpackPlugin generates Django templates for the backend to load
        // for each bundle. Because Django still needs to interpret those and
        // turn them into real HTML, it needs to have the files on disk, even
        // during development. Without this, webpack-dev-server just keeps the
        // files in memory and Django won't be able to find the templates.
        devMiddleware: {
          writeToDisk: true,
        },
      },
  plugins: compact([
    ...(NO_MANIFEST ? [] : generateHTMLWebpackPlugins()),
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
    ANALYZE && new BundleAnalyzerPlugin(),
  ]),
  devtool: SOURCE_MAPS ? (PROD ? 'source-map' : 'eval-source-map') : false,
};
