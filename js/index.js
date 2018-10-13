import React from 'react';
import ReactDOM from 'react-dom';
import $ from 'jquery';

import Spinner from './public/spinner';
import ajaxSetup from './public/ajaxsetup';

$(document).ready(() => {
    ajaxSetup();
    ReactDOM.render(
        <Spinner />,
        document.getElementById('container')
    );
});
