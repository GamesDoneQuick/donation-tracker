var path = require('path');
var webpack = require('webpack');
var autoprefixer = require('autoprefixer');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var sharedConfig = require('./shared.webpack')({hmr: false});
var WebpackManifestPlugin = require('webpack-yam-plugin');

module.exports = {
    context: __dirname,
    entry: ['./js/init', './js/admin'],
    output: {
        'filename': 'admin-[name]-[hash].js',
        'pathinfo': true,
        'path': __dirname + '/static/gen',
        'publicPath': '/static/gen',
    },
    module: sharedConfig.module,
    postcss: [autoprefixer],
    plugins: [
        new webpack.optimize.OccurrenceOrderPlugin(),
        new webpack.NoErrorsPlugin(),
        new WebpackManifestPlugin({
            manifestPath: __dirname + '/ui-admin.manifest.json',
            outputRoot: __dirname + '/static'
        }),
        new ExtractTextPlugin('[name]-[contenthash].css'),
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: JSON.stringify('production')
            },
            __DEVTOOLS__: false,
        }),
        new webpack.optimize.DedupePlugin(),
        new webpack.optimize.UglifyJsPlugin({comments: false}),
    ],
    resolve: sharedConfig.resolve,
    devtool: 'source-map',
};
