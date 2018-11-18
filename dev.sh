#!/bin/bash
`npm bin`/webpack-dev-server --config tracker.webpack.js --host 0.0.0.0 --watch-poll --hot --inline --allowed-hosts localhost,127.0.0.1,.ngrok.io
