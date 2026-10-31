import type { TestId } from "@/lib/testid";

const headingTestId: TestId = "app-home-heading";

export default function HomePage() {
  return (
    <main>
      <h1 data-testid={headingTestId}>LabApp</h1>
    </main>
  );
}
