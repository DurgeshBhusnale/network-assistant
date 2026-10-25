import { RequireAuth } from "@/components/shell/Gates";

export default function OnboardingLayout({ children }: LayoutProps<"/onboarding">) {
  return (
    <RequireAuth>
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-5 px-screen-x pt-6 pb-8">
        {children}
      </main>
    </RequireAuth>
  );
}
