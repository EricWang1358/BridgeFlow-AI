import pandas as pd
import yaml

# Load the field dictionary
with open('data/mappings/field-dictionary.example.yaml', 'r', encoding='utf-8') as f:
    field_dict = yaml.safe_load(f)

# Read all four departments' files
departments = {
    'production': pd.read_excel('data/mock_business/cases/clean/production.xlsx'),
    'procurement': pd.read_excel('data/mock_business/cases/clean/procurement.xlsx'),
    'finance': pd.read_excel('data/mock_business/cases/clean/finance.xlsx'),
    'marketing': pd.read_excel('data/mock_business/cases/clean/marketing.xlsx')
}

# Print columns for each department to verify
for dept, df in departments.items():
    print(f"{dept} columns: {df.columns.tolist()}")

# Column mapping (simplified example, needs to match the dictionary)
column_mapping = {
    'production': {
        '货品名称': 'sku',
        '生产量': 'output_quantity',
        '项目编号': 'line'
    },
    'procurement': {
        '货品名称': 'material',
        '采购数量': 'purchase_quantity',
        '单价': 'unit_price'
    },
    'finance': {
        '总账科目': 'gl_account',
        '客户': 'customer',
        '本期实现收入': 'revenue_amount'
    },
    'marketing': {
        '客户名称': 'customer',
        '产品名称': 'product'
    }
}

# Apply mapping to each department
mapped_dfs = {}
for dept, df in departments.items():
    mapped = df.rename(columns=column_mapping[dept])
    # Keep only columns that are in the dictionary for this dept
    valid_cols = list(field_dict['columns'][dept].values()) + list(field_dict['measures'][dept].values())
    mapped = mapped[[col for col in mapped.columns if col in valid_cols or col in ['项目编号', '客户', '客户名称']]]
    mapped_dfs[dept] = mapped

# Merge into Master Table on common keys (项目编号, customer)
master = mapped_dfs['production'].merge(mapped_dfs['finance'], on=['项目编号', '客户'], how='outer')
master = master.merge(mapped_dfs['procurement'], on='项目编号', how='outer')
master = master.merge(mapped_dfs['marketing'], on='客户', how='outer')

# Save Master Table
master.to_excel('Master_Table.xlsx', index=False)
print(f"\nMaster Table created with {len(master)} rows, saved to Master_Table.xlsx")
