import * as React from 'react';

import Container from '@uikit/Container';
import Header from '@uikit/Header';
import Text from '@uikit/Text';

const NotFound = () => {
  return (
    <Container size={Container.Sizes.NORMAL}>
      <Header>That page does not exist</Header>
      <Text>Sorry about that.</Text>
    </Container>
  );
};

export default NotFound;
