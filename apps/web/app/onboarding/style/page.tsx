import { OnboardingPlaceholderStep } from "@/components/shell/OnboardingPlaceholderStep";
import { copy } from "@/lib/copy/en";

export default function StyleStepPage() {
  return (
    <OnboardingPlaceholderStep
      step={3}
      title={copy.onboarding.styleTitle}
      body={copy.onboarding.styleBody}
      next="done"
      nextRoute="/today"
    />
  );
}
