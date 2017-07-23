const path = require('path');
const glob = require('glob');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const PurifyCSSPlugin = require('purifycss-webpack');

const folderDistribute = 'dist';
const switchMinify = false;
const cssConfigEnvironments = {
    'dev': ['style-loader', 'css-loader', 'sass-loader'],
    'prod': ExtractTextPlugin.extract({
        fallback: 'style-loader',
        use: ['css-loader', 'sass-loader']
    })
}

const envIsProd = process.env.NODE_ENV === 'prod'
const cssConfig = envIsProd ? cssConfigEnvironments['prod'] : cssConfigEnvironments['dev'];

module.exports = {
    entry: {
        app: ['./src/app.js']
    },
    output: {
        path: path.resolve(__dirname, folderDistribute),
        filename: 'app.bundle.js'
    },
    module: {
        rules: [
            {                                                                                   // Converts sass to css
                test: /\.scss$/,
                use: cssConfig
            },
            {
                test: /\.(jpe?g|png|gif|svg)$/i,
                loaders: [
                    'file-loader?name=img/[name].[ext]',                                        // See https://github.com/webpack-contrib/file-loader
                    'image-webpack-loader?bypassOnDebug&optimizationLevel=7&interlaced=false'   // See https://github.com/tcoopman/image-webpack-loader
                ]
            }
        ]
    },
    devServer: {
        contentBase: path.join(__dirname, folderDistribute),                                    // Configure development server
        compress: true,
        port: 8080,
        https: true,
        stats: 'errors-only',
        open: true
    },
    plugins: [
        new HtmlWebpackPlugin({                                                                 // Builds .html, see https://github.com/jantimon/html-webpack-plugin
            title: 'Hello World from HtmlWebpackPlugin',
            minify: {
                collapseWhitespace: switchMinify
            },
            hash: true,
            template: './src/content.html'
        }),
        new ExtractTextPlugin({                                                                 // Builds .css, see https://github.com/webpack-contrib/extract-text-webpack-plugin
            filename: '[name].css',
            allChunks: true,
            disable: !envIsProd
        }),
        new webpack.HotModuleReplacementPlugin(),                                               // Enable HMR, see https://webpack.js.org/guides/hot-module-replacement/
        new webpack.NamedModulesPlugin(),                                                       // See https://webpack.js.org/plugins/named-modules-plugin/
        new PurifyCSSPlugin({
            // Give paths to parse for rules. These should be absolute!
            paths: glob.sync(path.join(__dirname, 'src/*.html')),
        })
    ]
};
