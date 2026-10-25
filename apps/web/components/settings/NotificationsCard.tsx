"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { Card } from "@/components/ui/Card";
import { CheckboxRow } from "@/components/ui/CheckboxRow";
import { useUpdateMe, type Profile } from "@/lib/api/hooks/account";
import {
  useDeletePushSubscription,
  usePushConfig,
  useSavePushSubscription,
} from "@/lib/api/hooks/notifications";
import { copy } from "@/lib/copy/en";
import {
  currentPushSubscription,
  pushSupported,
  subscribePush,
  unsubscribePush,
} from "@/lib/device/push";

const t = copy.settings;

/** FR-NOT-1/2: push on this device, weekly email digest. */
export function NotificationsCard({ profile }: { profile: Profile }) {
  const supported = useSyncExternalStore(
    () => () => {},
    pushSupported,
    () => false,
  );
  const config = usePushConfig();
  const save = useSavePushSubscription();
  const remove = useDeletePushSubscription();
  const updateMe = useUpdateMe();
  const [pushOn, setPushOn] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!supported) return;
    let alive = true;
    void currentPushSubscription().then((sub) => {
      if (alive) setPushOn(sub !== null);
    });
    return () => {
      alive = false;
    };
  }, [supported]);

  async function togglePush(on: boolean) {
    setNote(null);
    const key = config.data?.public_key ?? process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (on) {
      if (!key) {
        setNote(t.pushUnsupported);
        return;
      }
      const sub = await subscribePush(key);
      if (!sub) {
        setNote(t.pushDenied);
        return;
      }
      await save.mutateAsync(sub);
      setPushOn(true);
    } else {
      const sub = await unsubscribePush();
      if (sub) await remove.mutateAsync(sub);
      setPushOn(false);
    }
  }

  return (
    <Card>
      <h2 className="m-0 font-display text-h2 font-semibold">{t.notificationsTitle}</h2>
      {supported ? (
        <CheckboxRow
          label={t.pushLabel}
          detail={t.pushDetail}
          checked={pushOn}
          onChange={(on) => void togglePush(on)}
        />
      ) : (
        <p className="text-small text-muted">{t.pushUnsupported}</p>
      )}
      <CheckboxRow
        label={t.emailLabel}
        detail={t.emailDetail}
        checked={profile.email_digest}
        onChange={(on) => updateMe.mutate({ email_digest: on })}
      />
      {note && (
        <p role="status" className="text-small text-ink-2">
          {note}
        </p>
      )}
    </Card>
  );
}
