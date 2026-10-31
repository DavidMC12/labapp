import type { TestId } from "@/lib/testid";

const headingTestId: TestId = "customers-list-heading";

export default function CustomersPage() {
  return (
    <h1 data-testid={headingTestId}>Clientes</h1>
  );
}
