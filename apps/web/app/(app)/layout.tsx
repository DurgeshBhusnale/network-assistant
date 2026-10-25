import { AppShell } from "@/components/shell/AppShell";
import { RequireOnboarded } from "@/components/shell/Gates";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <RequireOnboarded>
      <AppShell>{children}</AppShell>
    </RequireOnboarded>
  );
}
