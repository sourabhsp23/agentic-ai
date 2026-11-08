# Business Metric Definitions (e-commerce)

These are the official definitions the analytics team uses. Agents must follow them.

## Revenue (Net Revenue)
Net revenue = SUM(order_items.quantity * order_items.unit_price * (1 - order_items.discount)).
Only orders with orders.status = 'completed' count towards revenue. Cancelled and returned
orders are excluded. Shipping fees are NOT part of revenue.

## Gross Margin
Gross profit = net revenue - SUM(order_items.quantity * products.unit_cost) for completed orders.
Gross margin % = gross profit / net revenue * 100, rounded to 1 decimal.

## Average Order Value (AOV)
AOV = net revenue / number of distinct completed orders.

## Active Customer
A customer is "active" in a period if they placed at least one completed order in that period.

## Repeat Customer Rate
Share of customers with 2 or more completed orders, among all customers with at least one completed order.

## Return Rate and Cancellation Rate
Return rate = orders with status 'returned' / all orders. Cancellation rate = orders with
status 'cancelled' / all orders. Express both as percentages with 1 decimal.

## Time Periods
The fiscal year equals the calendar year. "Last year" means 2025 for this dataset (data spans
2024-01-01 to 2025-12-31). Months are bucketed with date_trunc('month', order_date).
Q4 means October to December.
