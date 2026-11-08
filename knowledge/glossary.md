# Data Glossary

## Tables
- customers: one row per customer (customer_id, customer_name, country, city, segment, signup_date).
- products: product catalog (product_id, product_name, category, unit_price, unit_cost).
- orders: order header (order_id, customer_id, order_date, status, channel, shipping_fee).
- order_items: order lines (order_item_id, order_id, product_id, quantity, unit_price, discount).
  discount is a fraction between 0 and 1 (0.1 = 10% off).

## Joins
orders.customer_id = customers.customer_id; order_items.order_id = orders.order_id;
order_items.product_id = products.product_id.

## Customer Segments
Consumer (individuals), Small Business, and Enterprise (largest basket sizes). When asked about
"B2B" customers, include both Small Business and Enterprise segments.

## Sales Channels
web = desktop website, mobile_app = iOS/Android apps, marketplace = third-party marketplaces.
"Digital channels" or "owned channels" means web + mobile_app (excludes marketplace).

## Regions
APAC = India and Singapore. EMEA = United Kingdom and Germany. AMER = United States.
