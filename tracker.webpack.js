var path = require('path');
var webpack = require('webpack');
var autoprefixer = require('autoprefixer');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var sharedConfig = require('./shared.webpack');

module.exports = function(opts) {
    var config = {
        context: __dirname,
        entry: ['./js/init', './js'],
        output: {
            'filename': 'public-[name]-[hash].js',
            'pathinfo': opts.context.DEBUG,
        },
        externals: sharedConfig(opts).externals,
        module: sharedConfig(opts).module,
        postcss: [autoprefixer],
        plugins: [
            new webpack.optimize.OccurrenceOrderPlugin(),
            new webpack.NoErrorsPlugin(),
            new webpack.DefinePlugin({
                'process.env': {
                    NODE_ENV: JSON.stringify(
                        opts.context.DEBUG ? 'development' : 'production'
                    )
                },
                __DEVTOOLS__: opts.context.DEBUG
            })
        ],
        devtool: opts.context.DEBUG ? 'eval-source-map' : 'source-map'
    };

    if (!opts.hmr) {
        // Move css assets into separate files
        config.plugins.push(new ExtractTextPlugin('[name]-[contenthash].css'));
    }

    if (!opts.context.DEBUG) {
        // Remove duplicates and activate compression
        config.plugins.push(
            new webpack.optimize.DedupePlugin(),
            new webpack.optimize.UglifyJsPlugin({comments: false})
        );
    }

    return config;
};
