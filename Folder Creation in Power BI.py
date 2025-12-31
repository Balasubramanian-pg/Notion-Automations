import os

ROOT = "PowerBI_Repository"   # change this to your repo folder name

# ==========================
# Folder Structure Blueprint
# ==========================
FOLDERS = [
    # Modeling
    "Modeling/Dimensions",
    "Modeling/Facts",
    "Modeling/StarSchemas",
    "Modeling/CalculationGroups",
    
    # DAX Framework
    "DAX/Measures/Finance",
    "DAX/Measures/Operations",
    "DAX/Measures/Sales",
    "DAX/Measures/Inventory",
    "DAX/Measures/Healthcare",
    
    # User Defined Functions
    "DAX/UserDefinedFunctions/01_Text",
    "DAX/UserDefinedFunctions/02_DateTime",
    "DAX/UserDefinedFunctions/03_Math",
    "DAX/UserDefinedFunctions/04_Financial",
    "DAX/UserDefinedFunctions/05_Table",
    "DAX/UserDefinedFunctions/06_KPI",
    "DAX/UserDefinedFunctions/07_DataQuality",
    "DAX/UserDefinedFunctions/08_Conversion",
    "DAX/UserDefinedFunctions/09_Performance",
    "DAX/UserDefinedFunctions/10_BusinessLogic",
    
    # Calculation Groups (optional)
    "DAX/CalculationGroups",
    
    # Datasets
    "Datasets/Airbnb-NY",
    "Datasets/Healthcare",
    "Datasets/Finance",
    "Datasets/HR",
    "Datasets/Sales",
    
    # Projects
    "Projects/Airbnb-NY/Dataset",
    "Projects/Airbnb-NY/PBIX",
    "Projects/Airbnb-NY/Model",
    "Projects/Airbnb-NY/Visuals",
    
    "Projects/HealthcareDashboard",
    "Projects/CFO-Dashboard",
    "Projects/SalesAnalytics",
    
    # SOP
    "SOP/01_DataGovernance",
    "SOP/02_DataModeling",
    "SOP/03_DAX_BestPractices",
    "SOP/04_Optimization",
    "SOP/05_Deployment",
    "SOP/06_RLS",
    "SOP/07_Performance",
    "SOP/08_Security",
    
    # Documentation
    "Documentation/Roadmaps",
    "Documentation/Architecture",
    "Documentation/Standards",
]

# ===============
# README Content
# ===============
README_TEMPLATES = {
    "Modeling": "# Modeling\nThis section contains your semantic model designs, star schemas, and calculation groups.",
    "DAX": "# DAX Framework\nYour central library for Measures, UDFs, and Calculation Groups.",
    "Datasets": "# Datasets\nRaw and cleaned datasets used across projects.",
    "Projects": "# Projects\nEnd-to-end Power BI solutions including PBIX, visuals, and documentation.",
    "SOP": "# SOP Library\nStandard Operating Procedures for Power BI development and governance.",
    "Documentation": "# Documentation\nArchitecture diagrams, standards, roadmaps, and internal documentation.",
}

# ===============
# Create folders
# ===============
for folder in FOLDERS:
    path = os.path.join(ROOT, folder)
    os.makedirs(path, exist_ok=True)

# ===============
# Create READMEs
# ===============
for name, content in README_TEMPLATES.items():
    readme_path = os.path.join(ROOT, name, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Power BI repository structure created successfully!")
