const path = require("path");
module.exports = {
    entry: './public/app.js',
    output: {
      filename: 'bundle.js',
      path: '/public'
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: "babel-loader"
          }
        }
      ]
    }
  };