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
}

export default function MutationButton<T>(props: MutationButtonProps<T>) {
  const { mutation, donationId, variant = 'default', label, icon: Icon, disabled = false } = props;

  const [tooltipProps] = useTooltip<HTMLButtonElement>(label);

  return (
    <Button
      {...tooltipProps}
      // eslint-disable-next-line react/jsx-no-bind
      onClick={() => mutation.mutate(donationId)}
      disabled={disabled || mutation.isLoading}
      variant={variant}>
      <Icon />
    </Button>
  );
}
