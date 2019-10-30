import React from 'react';
import ReactDOM from 'react-dom';

import Donate from './donate';
import ErrorBoundary from '../public/errorBoundary';

type DonateAppProps = any;

window.DonateApp = function(props: DonateAppProps) {
  ReactDOM.render(
    <ErrorBoundary>
      <Donate {...props} />
    </ErrorBoundary>,
    document.getElementById('container')
  );
};
