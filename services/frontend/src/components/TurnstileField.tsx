import { Turnstile, type TurnstileInstance } from '@marsidev/react-turnstile';
import { forwardRef } from 'react';

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '';

export const isTurnstileEnabled = Boolean(SITE_KEY);

type TurnstileFieldProps = {
  onSuccess: (token: string) => void;
  onExpire?: () => void;
  onError?: () => void;
};

const TurnstileField = forwardRef<TurnstileInstance, TurnstileFieldProps>(
  function TurnstileField({ onSuccess, onExpire, onError }, ref) {
    if (!isTurnstileEnabled) {
      return null;
    }

    return (
      <Turnstile
        ref={ref}
        siteKey={SITE_KEY}
        options={{ theme: 'light', size: 'flexible' }}
        onSuccess={onSuccess}
        onExpire={onExpire}
        onError={onError}
      />
    );
  },
);

export default TurnstileField;
