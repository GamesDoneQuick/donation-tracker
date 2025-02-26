import React from 'react';
import { Button, ButtonVariant, useTooltip } from '@faulty/gdq-design';

import { UseDonationMutationResult } from '@public/apiv2/hooks';
import { DataProps, dataProps } from '@public/util/Types';

import useProcessingStore from '@processing/modules/processing/ProcessingStore';

interface MutationButtonProps {
  mutation: UseDonationMutationResult[0];
  actionName?: string;
  donationId: number;
  label: string;
  icon: React.ComponentType;
  variant?: ButtonVariant;
  disabled?: boolean;
}

export default function MutationButton(props: DataProps<MutationButtonProps>) {
  const { mutation, actionName, donationId, variant = 'default', label, icon: Icon, disabled = false } = props;
  const store = useProcessingStore();

  const [tooltipProps] = useTooltip<HTMLButtonElement>(label);

  const mutate = React.useCallback(async () => {
    // let errors bubble out
    const { data: donation } = await mutation(donationId);

    if (donation && actionName) {
      store.processDonation(donation, actionName);
    }
  }, [actionName, donationId, mutation, store]);
  return (
    <Button {...tooltipProps} {...dataProps(props)} onPress={mutate} isDisabled={disabled} variant={variant}>
      <Icon />
    </Button>
  );
}
