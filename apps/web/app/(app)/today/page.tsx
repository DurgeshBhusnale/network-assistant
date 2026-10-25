import { PlaceholderPage } from "@/components/shell/PlaceholderPage";
import { SystemStatus } from "@/components/shell/SystemStatus";
import { copy } from "@/lib/copy/en";

export default function TodayPage() {
  return (
    <PlaceholderPage title={copy.pages.today.title} body={copy.pages.today.empty}>
      <SystemStatus />
    </PlaceholderPage>
  );
}
