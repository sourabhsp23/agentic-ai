"""Generate a realistic, deterministic e-commerce dataset (2 years of orders).

Usage:  python scripts/generate_sample_data.py [output_dir]
"""

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[2] / "sample_data" / "ecommerce")
OUT.mkdir(parents=True, exist_ok=True)

COUNTRIES = {
    "India": ["Bengaluru", "Mumbai", "Pune", "Delhi", "Hyderabad"],
    "United States": ["New York", "Austin", "Seattle", "Chicago"],
    "United Kingdom": ["London", "Manchester"],
    "Germany": ["Berlin", "Munich"],
    "Singapore": ["Singapore"],
}
COUNTRY_WEIGHTS = [0.4, 0.3, 0.12, 0.1, 0.08]
SEGMENTS = ["Consumer", "Small Business", "Enterprise"]
CHANNELS = ["web", "mobile_app", "marketplace"]
FIRST = [
    "Aarav",
    "Diya",
    "Ishaan",
    "Meera",
    "Rohan",
    "Ananya",
    "Liam",
    "Emma",
    "Noah",
    "Olivia",
    "Lukas",
    "Mia",
    "Wei",
    "Priya",
    "Arjun",
    "Sofia",
    "Kabir",
    "Zara",
    "Ethan",
    "Ava",
]
LAST = [
    "Sharma",
    "Patel",
    "Iyer",
    "Reddy",
    "Smith",
    "Johnson",
    "Brown",
    "Müller",
    "Schmidt",
    "Tan",
    "Lim",
    "Gupta",
    "Khan",
    "Garcia",
    "Williams",
    "Nair",
]
CATALOG = {
    "Electronics": [
        ("Wireless Earbuds", 59),
        ("Smartwatch", 199),
        ("4K Monitor", 329),
        ("Mechanical Keyboard", 89),
        ("USB-C Hub", 39),
        ("Noise Cancelling Headphones", 249),
        ("Portable SSD 1TB", 119),
        ("Webcam HD", 69),
    ],
    "Home & Kitchen": [
        ("Espresso Machine", 279),
        ("Air Fryer", 129),
        ("Chef Knife", 79),
        ("Smart Bulb Pack", 49),
        ("Robot Vacuum", 349),
        ("Blender", 99),
    ],
    "Fashion": [
        ("Running Shoes", 119),
        ("Denim Jacket", 89),
        ("Leather Wallet", 45),
        ("Sunglasses", 129),
        ("Backpack", 75),
        ("Wool Sweater", 95),
    ],
    "Sports & Outdoors": [
        ("Yoga Mat", 35),
        ("Camping Tent", 189),
        ("Dumbbell Set", 149),
        ("Cycling Helmet", 65),
        ("Water Bottle", 25),
    ],
    "Books": [
        ("Designing Data-Intensive Applications", 45),
        ("Clean Code", 38),
        ("The Pragmatic Programmer", 42),
        ("AI Engineering", 55),
        ("Atomic Habits", 22),
    ],
    "Beauty": [("Skincare Set", 65), ("Hair Dryer", 89), ("Perfume", 110), ("Electric Toothbrush", 79)],
}

# --- products ---------------------------------------------------------------
products = []
pid = 1
for category, items in CATALOG.items():
    for name, price in items:
        margin = random.uniform(0.25, 0.55)
        products.append(
            {
                "product_id": pid,
                "product_name": name,
                "category": category,
                "unit_price": price,
                "unit_cost": round(price * (1 - margin), 2),
            }
        )
        pid += 1

# --- customers --------------------------------------------------------------
START, END = date(2024, 1, 1), date(2025, 12, 31)
customers = []
for cid in range(1, 801):
    country = random.choices(list(COUNTRIES), COUNTRY_WEIGHTS)[0]
    customers.append(
        {
            "customer_id": cid,
            "customer_name": f"{random.choice(FIRST)} {random.choice(LAST)}",
            "country": country,
            "city": random.choice(COUNTRIES[country]),
            "segment": random.choices(SEGMENTS, [0.7, 0.22, 0.08])[0],
            "signup_date": (START + timedelta(days=random.randint(0, 650))).isoformat(),
        }
    )

# --- orders & items (growth trend + Nov/Dec seasonality) -------------------
orders, items = [], []
oid, item_id = 1, 1
day = START
while day <= END:
    months_in = (day.year - 2024) * 12 + day.month
    base = 5 + months_in * 0.25
    if day.month in (11, 12):
        base *= 1.8
    if day.weekday() >= 5:
        base *= 1.2
    for _ in range(max(0, int(random.gauss(base, 2)))):
        cust = random.choice(customers)
        if cust["signup_date"] > day.isoformat():
            continue
        status = random.choices(["completed", "cancelled", "returned"], [0.88, 0.07, 0.05])[0]
        orders.append(
            {
                "order_id": oid,
                "customer_id": cust["customer_id"],
                "order_date": day.isoformat(),
                "status": status,
                "channel": random.choices(CHANNELS, [0.45, 0.4, 0.15])[0],
                "shipping_fee": random.choice([0, 0, 4.99, 9.99]),
            }
        )
        mult = 2.5 if cust["segment"] == "Enterprise" else 1.4 if cust["segment"] == "Small Business" else 1
        for prod in random.sample(products, k=random.choices([1, 2, 3, 4], [0.5, 0.3, 0.15, 0.05])[0]):
            items.append(
                {
                    "order_item_id": item_id,
                    "order_id": oid,
                    "product_id": prod["product_id"],
                    "quantity": max(1, int(random.expovariate(1 / mult)) + 1),
                    "unit_price": prod["unit_price"],
                    "discount": random.choices([0, 0.05, 0.1, 0.2], [0.65, 0.15, 0.12, 0.08])[0],
                }
            )
            item_id += 1
        oid += 1
    day += timedelta(days=1)


def write(name: str, rows: list[dict]) -> None:
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


write("products", products)
write("customers", customers)
write("orders", orders)
write("order_items", items)
