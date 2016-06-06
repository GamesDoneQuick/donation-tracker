var ExtractTextPlugin = require('extract-text-webpack-plugin');
var packageJSON = require('./package.json');
var path = require('path');

function keyMirror(obj) {
    return Object.keys(obj).reduce(function(memo, key) {
        memo[key] = key;
        return memo;
    }, {});
}

module.exports = function(opts) {
    return {
        module: {
            loaders: [
                {
                    test: /\.jsx?$/,
                    exclude: /(node_modules|bower_components)/,
                    loader: (opts.hmr ? 'react-hot-loader!' : '') + 'babel-loader',
                },
                {
                    test: /\.css$/,
                    loader: 'style!css-loader?root=' + __dirname + '/../tracker&sourceMap!postcss-loader',
                },
                {
                    test: /\.(png|jpg|svg)$/,
                    loader: 'url-loader'
                },
                {
                    test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
                    loader: 'url-loader?limit=10000&mimetype=application/font-woff'
                },
                {
                    test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
                    loader: 'file-loader'
                }
            ],
        },
        node: {
            fs: 'empty'
        },
        resolve: {
            alias: {
                ui: path.resolve('js'),
            },
        },
        poll: 1000,
        externals: keyMirror(packageJSON.dependencies),
        devServer: {
            proxy: {
                '*': {
                    target: 'http://localhost:8088/',
                    headers: {'X-Webpack': 1}
                }
            }
        }
    };
};
