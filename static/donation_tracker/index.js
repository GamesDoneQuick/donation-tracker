import Spinner from './public/spinner';
import React from 'react';
import jQuery from 'jquery';

let $ = jQuery;

$(document).ready(() => {
    console.log('attaching spinner');
    React.render(
        <Spinner />,
        document.getElementById('container')
    );
});
