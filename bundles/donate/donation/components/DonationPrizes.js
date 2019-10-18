import * as React from 'react';

import * as CurrencyUtils from '../../../public/util/currency';
import Anchor from '../../../uikit/Anchor';
import Header from '../../../uikit/Header';
import Text from '../../../uikit/Text';

import styles from './DonationPrizes.mod.css';

const Prize = (props) => {
  const {
    prize
  } = props;

  return (
    <div className={styles.prize}>
      <Text size={Text.Sizes.SIZE_16} marginless>
        { prize.url != null
          ? <Anchor href={prize.url} newTab marginless>{prize.name}</Anchor>
          : prize.name
        }
      </Text>
      <Text size={Text.Sizes.SIZE_14} marginless>
        <strong>{CurrencyUtils.asCurrency(prize.minimumbid)}</strong> {prize.sumdonations ? 'Total Donations' : 'Minimum Single Donation'}
      </Text>
    </div>
  );
};

const Prizes = (props) => {
  const {
    prizes,
    prizesURL,
    rulesURL,
  } = props;

  return (
    <React.Fragment>
      <Header size={Header.Sizes.H3}>Prizes</Header>
      <div className={styles.container}>
        <div className={styles.prizeInfo}>
          <Text size={Text.Sizes.SIZE_16}>Donations can enter you to win prizes!</Text>
          <Text size={Text.Sizes.SIZE_16}>
            <Anchor href={prizesURL} external newTab>Full prize list</Anchor>
          </Text>
          { rulesURL
            ? <React.Fragment>
                <Text size={Text.Sizes.SIZE_16}>
                  <Anchor href={rulesURL} external newTab>Official Rules</Anchor>
                </Text>
                <Text size={Text.Sizes.SIZE_16}>No donation necessary for a chance to win. See sweepstakes rules for details and instructions.</Text>
              </React.Fragment>
            : null
          }
        </div>
        <div className={styles.prizeList}>
          <div className={styles.prizes}>
            {prizes.map(prize => <Prize key={prize.id} prize={prize} />)}
          </div>
        </div>
      </div>
    </React.Fragment>
  );
};

export default Prizes;
