import React from 'react';
import ReactDOM from 'react-dom';

import Donate from './donate';
import ErrorBoundary from '../public/errorBoundary';

window.DonateApp = function(props) {
  ReactDOM.render(
    <ErrorBoundary>
      <Donate {...props} />
    </ErrorBoundary>,
    document.getElementById('container')
  );
}

