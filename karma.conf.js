module.exports = function(config) {
    config.set({
        frameworks: ['jasmine'],

        files: [
            'static/**/*_spec.js'
        ],

        preprocessors: {
            // add webpack as preprocessor
            'static/**/*_spec.js': ['webpack']
        },

        webpack: {
            module: {
                loaders: [
                    {
                        test: /\.jsx?$/,
                        exclude: /(node_modules|bower_components)/,
                        loader: 'babel-loader',
                    },
                ],
            },
            node: {
                 fs: "empty"
            },
        },

        webpackMiddleware: {
            // webpack-dev-middleware configuration
            // i. e.
            noInfo: true
        },

        plugins: [
            require('karma-webpack'),
            require('karma-jasmine'),
        ]

    });
};
