const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const sharedConfig = require('./shared.webpack')({hmr: true});
const WebpackManifestPlugin = require('webpack-yam-plugin');

module.exports = {
    context: __dirname,
    entry: ['./js/init', './js/admin'],
    output: {
        'filename': 'admin.js',
        'pathinfo': true,
        'path': __dirname + '/static/gen',
        'publicPath': '/webpack/gen',
    },
    module: sharedConfig.module,
    plugins: [
        new webpack.optimize.OccurrenceOrderPlugin(),
        new webpack.NoEmitOnErrorsPlugin(),
        new WebpackManifestPlugin({
            manifestPath: __dirname + '/ui-admin.manifest.json',
            outputRoot: __dirname + '/static'
        }),
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: JSON.stringify('development')
            },
            __DEVTOOLS__: true,
        }),
        new ExtractTextPlugin("admin.css", {
            allChunks: true
        }),
    ],
    devServer: sharedConfig.devServer,
    resolve: sharedConfig.resolve,
    devtool: 'eval-source-map',
};
