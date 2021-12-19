import React from 'react';
import { useSelector } from 'react-redux';

import * as CurrencyUtils from '../../../public/util/currency';
import Anchor from '../../../uikit/Anchor';
import Button from '../../../uikit/Button';
import Container from '../../../uikit/Container';
import CurrencyInput from '../../../uikit/CurrencyInput';
import ErrorAlert from '../../../uikit/ErrorAlert';
import Header from '../../../uikit/Header';
import Text from '../../../uikit/Text';
import TextInput from '../../../uikit/TextInput';
import useDispatch from '../../hooks/useDispatch';
import * as EventDetailsStore from '../../event_details/EventDetailsStore';
import { StoreState } from '../../Store';
import * as DonationActions from '../DonationActions';
import * as DonationStore from '../DonationStore';

import { AMOUNT_PRESETS } from '../DonationConstants';
import styles from './Donate.mod.css';
import { useCachedCallback } from '../../../public/hooks/useCachedCallback';
import { useConstants } from '../../../common/Constants';
import DonationIncentives from './DonationIncentives';
import Markdown from '../../../uikit/Markdown';

type DonateProps = {
  eventId: string | number;
};

const Donate = (props: DonateProps) => {
  const { PRIVACY_POLICY_URL } = useConstants();
  const dispatch = useDispatch();

  const { eventDetails, donation, bids, donationValidity, commentErrors } = useSelector((state: StoreState) => ({
    eventDetails: EventDetailsStore.getEventDetails(state),
    prizes: EventDetailsStore.getPrizes(state),
    donation: DonationStore.getDonation(state),
    bids: DonationStore.getBids(state),
    commentErrors: DonationStore.getCommentFormErrors(state),
    donationValidity: DonationStore.validateDonation(state),
  }));

  const { receiverName, donateUrl, minimumDonation, maximumDonation, step } = eventDetails;
  const { name, email, amount, comment } = donation;

  const updateDonation = React.useCallback(
    (fields = {}) => {
      dispatch(DonationActions.updateDonation(fields));
    },
    [dispatch],
  );

  const handleSubmit = React.useCallback(() => {
    if (donationValidity.valid) {
      DonationActions.submitDonation(donateUrl, eventDetails.csrfToken, donation, bids);
    }
  }, [donateUrl, eventDetails.csrfToken, donation, bids, donationValidity]);

  const updateName = React.useCallback(name => updateDonation({ name }), [updateDonation]);
  const updateEmail = React.useCallback(email => updateDonation({ email }), [updateDonation]);
  const updateAmount = React.useCallback(amount => updateDonation({ amount }), [updateDonation]);
  const updateAmountPreset = useCachedCallback(amountPreset => updateDonation({ amount: amountPreset }), [
    updateDonation,
  ]);
  const updateComment = React.useCallback(comment => updateDonation({ comment }), [updateDonation]);

  const markdown = `**※寄付の前にお読みください**

いただいた寄付の返金対応はできません。ご注意ください。

**■ 国境なき医師団からの領収書発行について**

希望される方には、国境なき医師団から領収書を発行いたします。 着金の都合上、領収書の日付は2022年1月以降となりますので、2021年度分の確定申告の寄付金控除にはご利用頂けません。

イベント期間中に**1回1,000円以上**寄付いただいた方が、領収書発行の対象となります。

領収書の発行には、別途領収書の発行依頼フォームに入力いただく必要があります。

領収書の発行依頼フォームは1,000円以上の寄付完了後に表示されますので、
**PayPal での決済後、必ず「ショッピングサイトに戻る」からサイトに戻るようにしてください。**

領収書発行に関する問い合わせは以下のメールアドレス宛にお願いいたします。

国境なき医師団(RTA in Japan 関連): corporate.rta@tokyo.msf.org
  `;

  return (
    <Container>
      <ErrorAlert errors={commentErrors.__all__} />
      <Header size={Header.Sizes.H1} marginless>
        ご協力ありがとうございます。
      </Header>
      <Text size={Text.Sizes.SIZE_16}>いただいた寄付は全て {receiverName} に直接送られます。</Text>

      <Text size={Text.Sizes.SIZE_14} className={styles.eventNotice}>
        <Markdown>{markdown}</Markdown>
      </Text>

      <section className={styles.section}>
        <ErrorAlert errors={commentErrors.requestedalias} />
        <TextInput
          name="alias"
          value={name}
          label="ニックネームなど"
          hint="匿名での寄付をご希望の場合は空白にしてください。"
          size={TextInput.Sizes.LARGE}
          onChange={updateName}
          maxLength={32}
          autoFocus
        />
        <ErrorAlert errors={commentErrors.requestedemail} />
        <TextInput
          name="email"
          value={email}
          label="メールアドレス"
          hint={
            PRIVACY_POLICY_URL && (
              <>
                プライバシーポリシーは <Anchor href={PRIVACY_POLICY_URL}>こちら</Anchor>
              </>
            )
          }
          size={TextInput.Sizes.LARGE}
          type={TextInput.Types.EMAIL}
          onChange={updateEmail}
          maxLength={128}
        />

        <ErrorAlert errors={commentErrors.amount} />

        <CurrencyInput
          name="amount"
          value={amount}
          label="金額"
          hint={
            <React.Fragment>
              最低寄付金額は <strong>{CurrencyUtils.asCurrency(minimumDonation)} です。</strong>
            </React.Fragment>
          }
          size={CurrencyInput.Sizes.LARGE}
          onChange={updateAmount}
          step={step}
          min={minimumDonation}
          max={maximumDonation}
          leader="&yen;"
          decimalPlaces={0}
          placeholder="0"
        />
        <div className={styles.amountPresets}>
          {AMOUNT_PRESETS.map(amountPreset => (
            <Button
              className={styles.amountPreset}
              key={amountPreset}
              look={Button.Looks.OUTLINED}
              onClick={updateAmountPreset(amountPreset)}>
              &yen;{amountPreset}
            </Button>
          ))}
        </div>

        <ErrorAlert errors={commentErrors.comment} />

        <TextInput
          name="comment"
          value={comment}
          label="寄付にコメントを残しますか？"
          placeholder="コメントを入力"
          hint="攻撃的な表現や人を傷つける言葉は避けて下さい。全ての寄付コメントは一覧に表示され、不適切と判断された場合には削除されることがあります。"
          multiline
          onChange={updateComment}
          maxLength={5000}
          rows={5}
        />
      </section>

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>インセンティブ</Header>
        <Text>
          寄付によるインセンティブは
          {/* スケジュールにボーナスゲームを追加したり、 */}
          RTA 中のプレイヤーの選択を決めるのに使われます。あなたの寄付をインセンティブに加えてみませんか？
        </Text>
        <DonationIncentives className={styles.incentives} step={step} total={amount != null ? amount : 0} />
      </section>

      <section className={styles.section}>
        <Header size={Header.Sizes.H3}>寄付</Header>
        {!donationValidity.valid && <Text>{donationValidity.errors.map(error => error.message)}</Text>}
        <Text>
          ※PayPalの送金画面に遷移します。「説明」等の入力フォームが表示されることがありますが、空欄のままお進みください。
        </Text>
        <Button
          size={Button.Sizes.LARGE}
          disabled={!donationValidity.valid}
          fullwidth
          onClick={handleSubmit}
          data-testid="donation-submit">
          {amount != null ? `${CurrencyUtils.asCurrency(amount)} を寄付する` : '寄付する'}
        </Button>
      </section>
    </Container>
  );
};

export default Donate;
