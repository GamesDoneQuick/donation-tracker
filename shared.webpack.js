const packageJSON = require('./package.json');
const path = require('path');
const _ = require('lodash');

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
      loaders: [
        {
          test: /\.jsx?$/,
          exclude: /(node_modules|bower_components)/,
          loaders: _.compact([
            hmr && 'react-hot-loader/webpack',
            'babel-loader',
          ]),
        },
        {
          test: /\.css$/,
          loaders: [
            'style-loader',
            'css-loader?root=' + __dirname + '/../tracker&sourceMap&localIdentName=[local]--[hash:base64:10]',
          ],
        },
        {
          test: /\.(png|jpg|svg)$/,
          loaders: [
            'url-loader',
          ],
        },
        {
          test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
          loader: 'url-loader?limit=10000&mimetype=application/font-woff'
        },
        {
          test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
          loaders: [
            'file-loader',
          ],
        }
      ],
    },
    node: {
      fs: 'empty'
    },
    resolve: {
      alias: {
        ui: path.resolve('bundles'),
      },
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
