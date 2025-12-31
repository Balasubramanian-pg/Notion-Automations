import pandas as pd

# Create a simple finance dataset for Power BI training
data = {
    "Date": pd.date_range(start="2025-01-01", periods=12, freq="M"),
    "Department": ["Sales", "Marketing", "Finance", "HR", "IT", "Operations"] * 2,
    "Revenue": [850000, 640000, 910000, 400000, 700000, 880000, 930000, 710000, 950000, 450000, 760000, 890000],
    "Expense": [550000, 420000, 700000, 350000, 580000, 670000, 640000, 500000, 720000, 390000, 600000, 710000],
}

# Create DataFrame
df = pd.DataFrame(data)

# Calculate profit and margin
df["Profit"] = df["Revenue"] - df["Expense"]
df["ProfitMargin%"] = round((df["Profit"] / df["Revenue"]) * 100, 2)

# Save to Excel
excel_path = r"Downloads/Finance_Demo_Data.xlsx"
df.to_excel(excel_path, index=False)

excel_path
