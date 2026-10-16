# CartIQ — Retail Intelligence Dashboard (Flask + Python)

A dark-themed, three-page e-commerce analytics website designed to open and run in PyCharm.

## Pages
1. **Overview** (`/`) — revenue, order count, customers, average order value, monthly sales chart, customer segment chart, category revenue, latest orders.
2. **Customer insights** (`/customers`) — searchable/filterable customer table with frequency, recency, lifetime spend, average basket, reorder score, and RFM-inspired segment.
3. **Reorder lab** (`/reorder`) — interactive form that calculates reorder likelihood, expected basket and probability-weighted revenue. Buttons for Calculate, Load sample customer, Clear values all work.

## Dataset
`data/ecommerce_orders.csv` is an included **synthetic educational dataset** with 180 customer IDs, order IDs, dates, product/category, quantity, unit price, discount and line total. It is not a real customer dataset. Download it from the website's sidebar or Export CSV button.

## Run in PyCharm
1. Extract `CartIQ_PyCharm_Project.zip`.
2. Open the extracted `CartIQ_PyCharm_Project` folder in PyCharm.
3. Create a virtual environment when prompted, or open PyCharm Terminal and run:

   ```bash
   python -m venv .venv
   ```

   Windows:
   ```bash
   .venv\Scripts\activate
   ```

   macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

4. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Run `app.py` (green Run button) or:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

## Calculations
- **Frequency** = number of distinct orders for a customer.
- **Recency** = latest order date in the dataset minus that customer's most recent order date.
- **Monetary / lifetime spend** = sum of discounted order line totals.
- **Average basket** = customer lifetime spend divided by their distinct order count.
- **Reorder score** = `45% × recency_score + 35% × frequency_score + 20% × spend_score`, where each component is capped between 0 and 1. The interactive lab also slightly adjusts the score based on expected basket value.
- **Probability-weighted revenue** = reorder score × expected basket value.

This is a transparent heuristic for a student demo, **not a trained model** and not a calibrated probability. The website describes it accurately.

## Notes
- The app uses local CSV data; no database setup or API key is needed.
- Chart.js is loaded from a CDN, so charts need an internet connection. The rest of the website and calculations run locally.
- To use a real dataset later, replace `data/ecommerce_orders.csv` with a CSV using the same column names.
