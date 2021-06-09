const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');

let mode = 'development';
// let mode = 'production';

// Production values
let devtool = false;
let minimize = true;

if (mode === 'development') {
    console.log('Building in DEV mode!')

    // devtool = 'cheap-module-source-map';
    devtool = 'eval';
    minimize = false;
} else {
    console.log('Building in PRODUCTION mode!')
}

module.exports = {
    entry: [
      './src/index.tsx',
      './src/style.css',
    ],
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'dist'),
        clean: true,
    },
    devtool: devtool,
    module: {
        rules: [{
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
            {
                test: /\.(png|svg|jpg|jpeg|gif)$/i,
                type: 'asset/inline',
            },
            {
                test: /\.tsx?$/,
                use: 'ts-loader',
                exclude: /node_modules/,
            },
            {
                test: /\.(woff|woff2|eot|ttf|otf)$/i,
                type: 'asset/inline',
            },
        ],
    },
    resolve: {
        extensions: ['.tsx', '.ts', '.js'],
    },
    plugins: [
        // Generates the index.html
        new HtmlWebpackPlugin({
            title: 'Robot Interactive Interpreter',
        }),
        new MonacoWebpackPlugin({
            // available options are documented at https://github.com/Microsoft/monaco-editor-webpack-plugin#options
            languages: []
        })
    ],
    optimization: {
        minimize: minimize
    },
    mode: mode
};