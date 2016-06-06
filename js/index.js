import React from 'react';
import $ from 'jquery';

import Spinner from './public/spinner';
import ajaxSetup from './public/ajaxsetup';

$(document).ready(() => {
    React.render(
        <Spinner />,
        document.getElementById('container')
    );
});
