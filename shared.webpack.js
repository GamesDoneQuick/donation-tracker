const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const _ = require('lodash');
const packageJSON = require('./package.json');

function keyMirror(obj) {
  return Object.keys(obj).reduce(function (memo, key) {
    memo[key] = key;
    return memo;
  }, {});
}


module.exports = function (opts = {}) {
  const hmr = opts.hmr || process.env.NODE_ENV === 'development';
  return {
    module: {
      rules: [
        {
          test: /\.(t|j)sx?$/,
          exclude: /(node_modules|bower_components)/,
          use: _.compact([
            hmr && 'react-hot-loader/webpack',
            'babel-loader',
          ]),
        },
        {
          test: /\.css$/,
          use: [
            {
              loader: MiniCssExtractPlugin.loader,
              options: {
                // only enable hot in development
                hmr,
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
            }
          ],
        },
        {
          test: /\.(png|jpg|svg)$/,
          use: [
            'url-loader',
          ],
        },
        {
          test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
          use: [
            {
              loader: 'url-loader',
              options: {
                limit: 10000,
                mimetype: 'application/font-woff',
              },
            }
          ],
        },
        {
          test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
          use: [
            'file-loader',
          ],
        }
      ],
    },
    node: {
      fs: 'empty'
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.json'],
    },
    poll: 1000,
    externals: keyMirror(packageJSON.dependencies),
    devServer: {
      proxy: [{
        context: [
          '/admin',
          '/logout',
          '/api',
          '/ui',
          '/static',
          '/tracker',
          '/donate',
        ],
        target: 'http://localhost:8000/',
        headers: {'X-Webpack': 1},
      }],
      allowedHosts: [
        'localhost',
        '127.0.0.1',
        '.ngrok.io',
      ],
    },
  };
};
