import type { TestId } from "@/lib/testid";

const headingTestId: TestId = "orders-list-heading";

export default function OrdersPage() {
  return (
    <h1 data-testid={headingTestId}>Pedidos</h1>
  );
}
