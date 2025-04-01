import re

def analyze_sales_data(file_path):
    """
    Analyzes sales data from a file, calculates profitability per customer,
    and ranks customers by profitability.

    Args:
        file_path (str): The path to the sales data file.

    Returns:
        None. Prints the ranked customer profitability.
    """

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    customer_data = {}
    cost_per_pcs = 0.78

    # Regex to extract relevant data.  Handles variations in spacing.
    regex = re.compile(
        r"Anonymous ID: (?P<customer_id>\w+)"
        r"\nCategory: (?P<category>\w+)"
        r"\nType of Veg: (?P<veg_type>\w+)"
        r"\nQuantity: (?P<quantity>\d+\.?\d*)"
        r"\nUOM: (?P<uom>\w+)"
        r"\nUnitPrice: (?P<unit_price>\d+\.?\d*)"
        r"\nTotalPrice: (?P<total_price>\d+\.?\d*)"
    )

    for i in range(0, len(lines), 10):  # Process in chunks of 10 lines
        match = regex.match("\n".join(lines[i:i+10]))
        if match:
            try:
                customer_id = match.group("customer_id")
                quantity = float(match.group("quantity"))
                unit_price = float(match.group("unit_price"))
                total_price = float(match.group("total_price"))

                cost = quantity * cost_per_pcs
                profit = total_price - cost

                if customer_id in customer_data:
                    customer_data[customer_id]["total_profit"] += profit
                else:
                    customer_data[customer_id] = {"total_profit": profit}
            except (ValueError, KeyError) as e:
                print(f"Skipping entry due to parsing error: {e}")
                continue

    # Rank customers by total profit
    ranked_customers = sorted(customer_data.items(), key=lambda item: item[1]["total_profit"], reverse=True)

    print("Customer Profitability Ranking:")
    for customer_id, data in ranked_customers:
        print(f"Customer {customer_id}: ${data['total_profit']:.2f}")


# Specify the file path
file_path = r"C:\Users\L\AppData\Local\Temp\tmpo81py8r6.txt"

# Analyze the sales data
analyze_sales_data(file_path)