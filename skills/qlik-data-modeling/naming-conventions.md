---
name: "qlik-naming-conventions"
domain: "qlik-data-modeling"
version: "1.0"
description: "Standardized naming conventions for Qlik Sense/QlikView tables, fields, variables, and files"
tags:
  - "qlik"
  - "naming"
  - "conventions"
  - "standards"
keywords:
  - "naming convention"
  - "field names"
  - "table names"
  - "variable naming"
  - "QVD naming"
  - "standards"
output_types:
  - "md"
author: "Assistant Brain OS"
---

# Qlik Naming Conventions

## Overview

Consistent naming is critical for maintainable Qlik applications. These conventions apply across all load scripts, QVD files, and application objects.

## Table Naming

| Prefix | Usage | Examples |
|--------|-------|----------|
| `Fact_` | Fact/transaction tables | `Fact_Orders`, `Fact_Sales`, `Fact_Clicks` |
| `Dim_` | Dimension/reference tables | `Dim_Customers`, `Dim_Products`, `Dim_Calendar` |
| `Bridge_` | Many-to-many bridge tables | `Bridge_Order_Products` |
| `Stg_` | Staging/temporary tables | `Stg_Raw_Orders` (dropped after use) |
| `Map_` | Mapping tables (ApplyMap) | `Map_Country_Region` |

## Field Naming

| Type | Pattern | Examples |
|------|---------|----------|
| Surrogate keys | `<Entity>_Key` | `Customer_Key`, `Product_Key` |
| Natural keys | `<Entity>_ID` | `Customer_ID`, `Order_ID` |
| Dates | `<Event>_Date` | `Order_Date`, `Ship_Date`, `Birth_Date` |
| Timestamps | `<Event>_Timestamp` | `Created_Timestamp` |
| Amounts | `<Noun>_Amount` | `Order_Amount`, `Tax_Amount` |
| Counts | `<Noun>_Count` or `Num_<Noun>` | `Line_Item_Count`, `Num_Products` |
| Flags | `Is_<Condition>` or `Has_<Feature>` | `Is_Active`, `Has_Subscription` |
| Rates/Percentages | `<Noun>_Rate` or `<Noun>_Pct` | `Tax_Rate`, `Discount_Pct` |
| Names | `<Entity>_Name` | `Customer_Name`, `Product_Name` |
| Descriptions | `<Entity>_Description` | `Product_Description` |

## Variable Naming

| Prefix | Usage | Examples |
|--------|-------|----------|
| `v` | Standard variables | `vConnection`, `vStartDate`, `vTaxRate` |
| `vSet_` | Set analysis expressions | `vSet_CurrentYear`, `vSet_ActiveCustomers` |
| `vColor_` | Color definitions | `vColor_Primary`, `vColor_Negative` |
| `vFormat_` | Number formatting | `vFormat_Currency`, `vFormat_Percent` |

## File Naming

| Type | Pattern | Examples |
|------|---------|----------|
| Load scripts | `snake_case.qvs` | `fact_orders.qvs`, `dim_customers.qvs` |
| QVD files | `PascalCase.qvd` | `FactOrders.qvd`, `DimCustomers.qvd` |
| Config files | `snake_case.qvs` | `variables.qvs`, `connection_strings.qvs` |

## Rules

1. **Use PascalCase with underscores** for table and field names: `Dim_Customers`, `Order_Amount`
2. **Never use spaces** in field names. Use underscores instead.
3. **Prefix all key fields** to avoid synthetic keys. A `Customer_ID` in `Dim_Customers` and `Fact_Orders` will create a proper association. But if both tables have a field called just `ID`, Qlik creates a synthetic key.
4. **Use descriptive names** over abbreviations. `Customer_Name` not `Cust_Nm`.
5. **Be consistent**: Pick one convention and stick to it across the entire application.
