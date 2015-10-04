var path = require('path');
var webpack = require('webpack');
var build = require('webpack-build');
var autoprefixer = require('autoprefixer-core');
var ExtractTextPlugin = require('extract-text-webpack-plugin');

module.exports = function(opts) {
	console.log(JSON.stringify(opts));
	var config = {
		context: __dirname,
		entry: './static/donation_tracker',
		output: {
			'filename': 'public-[name]-[hash].js',
			'pathinfo': opts.context.DEBUG,
		},
		module: {
			loaders: [
				{
					test: /\.jsx?$/,
					exclude: /(node_modules|bower_components)/,
					loader: (opts.hmr ? 'react-hot-loader!': '') + 'babel-loader'
				},
				{
					test: /\.css$/,
					loader: opts.hmr ?
						'style!css-loader?sourceMap!postcss-loader' :
						ExtractTextPlugin.extract('style', 'css-loader?sourceMap!postcss-loader')
				},
				{
					test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,
					loader: 'url-loader?limit=10000&mimetype=application/font-woff'
				},
				{
					test: /\.(ttf|eot|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
					loader: 'file-loader'
				}
			]
		},
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
