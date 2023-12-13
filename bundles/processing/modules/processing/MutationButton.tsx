import * as React from 'react';
import { UseMutationResult } from 'react-query';
import { Button, ButtonVariant, useTooltip } from '@spyrothon/sparx';

interface MutationButtonProps<T> {
  mutation: UseMutationResult<T, unknown, number, unknown>;
  donationId: number;
  label: string;
  icon: React.ComponentType;
  variant?: ButtonVariant;
  disabled?: boolean;
  'data-test-id'?: string;
}

export default function MutationButton<T>(props: MutationButtonProps<T>) {
  const { mutation, donationId, variant = 'default', label, icon: Icon, disabled = false } = props;

  const [tooltipProps] = useTooltip<HTMLButtonElement>(label);

  return (
    <Button
      {...tooltipProps}
      data-test-id={props['data-test-id']}
      // eslint-disable-next-line react/jsx-no-bind
      onPress={() => mutation.mutate(donationId)}
      isDisabled={disabled || mutation.isLoading}
      variant={variant}>
      <Icon />
    </Button>
  );
}
