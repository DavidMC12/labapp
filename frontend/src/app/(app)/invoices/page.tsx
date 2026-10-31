import type { TestId } from "@/lib/testid";

const headingTestId: TestId = "invoices-list-heading";

export default function InvoicesPage() {
  return (
    <h1 data-testid={headingTestId}>Facturas</h1>
  );
}
