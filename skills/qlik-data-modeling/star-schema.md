---
name: "qlik-star-schema"
domain: "qlik-data-modeling"
version: "1.0"
description: "Star schema design patterns for Qlik Sense/QlikView data models including fact tables, dimension tables, and load scripts"
tags:
  - "qlik"
  - "data-modeling"
  - "star-schema"
  - "qvd"
  - "load-script"
keywords:
  - "fact table"
  - "dimension table"
  - "star schema"
  - "surrogate key"
  - "QVD"
  - "load script"
  - "data model"
  - "qlik sense"
  - "qlikview"
  - "e-commerce"
  - "sales"
  - "orders"
output_types:
  - "qvs"
  - "md"
author: "Assistant Brain OS"
---

# Qlik Star Schema Data Modeling

## Overview

Star schema is the recommended approach for Qlik data models. It consists of:
- **Fact tables**: Central tables containing measurable business events (transactions, orders, clicks)
- **Dimension tables**: Descriptive reference tables (customers, products, dates, stores)
- **Keys**: Surrogate keys linking facts to dimensions using AutoNumber()

The star schema minimizes circular references and synthetic keys, which are the two most common Qlik modeling issues.

## Naming Conventions

- Fact tables: `Fact_<BusinessProcess>` (e.g., `Fact_Orders`, `Fact_Returns`)
- Dimension tables: `Dim_<Entity>` (e.g., `Dim_Customers`, `Dim_Products`)
- Key fields: `<Entity>_Key` (e.g., `Customer_Key`, `Product_Key`)
- Measures: Descriptive names without abbreviations (e.g., `Order_Amount`, `Quantity_Sold`)
- Date fields: `<Event>_Date` (e.g., `Order_Date`, `Ship_Date`)
- Source ID fields: `<Entity>_ID` (original key from source system)

## Templates

### Template: Fact Table Load Script

```qvs
///$tab Fact_{{table_name}}
/**
 * Fact Table: Fact_{{table_name}}
 * Description: {{description}}
 * Grain: One row per {{grain}}
 * Source: {{source_system}}
 */

[Fact_{{table_name}}]:
LOAD
    AutoNumber({{primary_key}})           as [{{primary_key}}_Key],
    // Dimension keys
    AutoNumber({{dimension_key_1}})       as [{{dimension_key_1}}_Key],
    AutoNumber({{dimension_key_2}})       as [{{dimension_key_2}}_Key],
    // Measures
    {{measure_1}}                         as [{{measure_1_alias}}],
    {{measure_2}}                         as [{{measure_2_alias}}],
    // Date fields
    Date({{date_field}}, 'YYYY-MM-DD')    as [{{date_field}}_Date],
    // ETL metadata
    Timestamp(now(), 'YYYY-MM-DD hh:mm:ss') as [ETL_Loaded_At]
FROM [lib://{{connection}}/{{source_path}}]
(qvd);
```

### Template: Dimension Table Load Script

```qvs
///$tab Dim_{{entity_name}}
/**
 * Dimension Table: Dim_{{entity_name}}
 * Description: {{description}}
 * Type: Type 1 (overwrite)
 * Source: {{source_system}}
 */

[Dim_{{entity_name}}]:
LOAD
    AutoNumber({{natural_key}})           as [{{entity_name}}_Key],
    {{natural_key}}                       as [{{entity_name}}_ID],
    // Attributes
    {{attribute_1}}                       as [{{attribute_1_alias}}],
    {{attribute_2}}                       as [{{attribute_2_alias}}],
    // ETL metadata
    Timestamp(now(), 'YYYY-MM-DD hh:mm:ss') as [ETL_Loaded_At]
FROM [lib://{{connection}}/{{source_path}}]
(qvd);
```

### Template: Master Calendar

```qvs
///$tab Dim_Calendar
/**
 * Master Calendar dimension
 * Auto-generated date reference table
 */

LET vMinDate = Num(MakeDate(2020, 1, 1));
LET vMaxDate = Num(Today());

TempCalendar:
LOAD
    $(vMinDate) + IterNo() - 1 as TempDate
AutoGenerate(1)
While $(vMinDate) + IterNo() - 1 <= $(vMaxDate);

[Dim_Calendar]:
LOAD
    Date(TempDate, 'YYYY-MM-DD')         as [Date],
    Year(TempDate)                        as [Year],
    Month(TempDate)                       as [Month],
    MonthName(TempDate)                   as [Month_Name],
    Day(TempDate)                         as [Day],
    WeekDay(TempDate)                     as [Day_of_Week],
    Week(TempDate)                        as [Week_Number],
    'Q' & Ceil(Month(TempDate)/3)         as [Quarter],
    Year(TempDate) & '-' & Num(Month(TempDate), '00') as [Year_Month],
    If(WeekDay(TempDate) >= 5, 'Weekend', 'Weekday') as [Day_Type]
RESIDENT TempCalendar;

DROP TABLE TempCalendar;
LET vMinDate = ;
LET vMaxDate = ;
```

### Template: Main Load Script

```qvs
///$tab Main
/**
 * {{project_name}} - Master Load Script
 * Generated: {{date}}
 *
 * Load order:
 * 1. Configuration & Variables
 * 2. Dimension tables
 * 3. Fact tables
 * 4. Calendar
 */

SET ThousandSep=',';
SET DecimalSep='.';
SET MoneyThousandSep=',';
SET MoneyDecimalSep='.';
SET MoneyFormat='$#,##0.00';
SET TimeFormat='h:mm:ss TT';
SET DateFormat='YYYY-MM-DD';
SET TimestampFormat='YYYY-MM-DD h:mm:ss[.fff] TT';

// --- Configuration ---
$(Must_Include=lib://{{connection}}/config/variables.qvs);

// --- Dimensions (load before facts) ---
$(Must_Include=lib://{{connection}}/src/models/dim_customers.qvs);
$(Must_Include=lib://{{connection}}/src/models/dim_products.qvs);
// Add more dimensions here

// --- Facts ---
$(Must_Include=lib://{{connection}}/src/models/fact_orders.qvs);
// Add more facts here

// --- Calendar ---
$(Must_Include=lib://{{connection}}/src/models/dim_calendar.qvs);
```

### Template: Variables Configuration

```qvs
///$tab Variables
/**
 * Global variables and configuration
 */

// Connection settings
LET vConnection = 'DataConnection';

// Date range
LET vStartDate = '2020-01-01';
LET vEndDate = Today();

// Business rules
LET vTaxRate = 0.08;
LET vFiscalYearStart = 4;  // April
```

## Best Practices

1. **Always use AutoNumber()** for key fields. This creates integer surrogate keys that are faster than composite string keys.
2. **One fact table per business process**. Do not combine orders and returns in the same fact table.
3. **Conformed dimensions** should be shared across fact tables. A customer dimension used by both orders and returns should be loaded once.
4. **Date handling**: Always use the `Date()` function to ensure consistent formatting. Store dates as proper Qlik dates, not strings.
5. **QVD layering**: Use a two-layer QVD architecture:
   - Layer 1 (Extract): Raw data from source systems
   - Layer 2 (Transform): Cleaned, transformed data
   - Final: Load scripts read from Layer 2 QVDs
6. **Tab organization**: Use `///$tab TabName` comments to organize scripts into logical tabs.
7. **Comment everything**: Every table should have a header comment with description, grain, and source.
8. **Load dimensions before facts**: Ensures AutoNumber keys are consistent.
9. **Use variables for connections**: Never hard-code connection strings in load scripts.

## Anti-Patterns

1. **Never use synthetic keys**: If Qlik creates synthetic keys, your model has shared field names. Rename fields to be unique per table.
2. **Never use circular references**: Qlik does not support circular references. If A links to B and B links to C, do not also link C to A.
3. **Avoid data islands**: Every table should connect to the rest of the model through keys.
4. **Do not store calculated fields in QVDs** unless they are expensive to compute at query time.
5. **Never hard-code connection strings**. Use variables defined in a config file.
6. **Avoid wide fact tables**: Keep facts narrow with keys + measures only. Put descriptive attributes in dimensions.

## Examples

### Example: E-Commerce Data Model

**Fact tables**: Fact_Orders, Fact_Returns, Fact_Shipments
**Dimensions**: Dim_Customers, Dim_Products, Dim_Stores, Dim_Calendar, Dim_Payment_Methods

**Key relationships**:
- Fact_Orders -> Dim_Customers (via Customer_Key)
- Fact_Orders -> Dim_Products (via Product_Key)
- Fact_Orders -> Dim_Stores (via Store_Key)
- Fact_Orders -> Dim_Calendar (via Order_Date)
- Fact_Orders -> Dim_Payment_Methods (via Payment_Key)

**Measures in Fact_Orders**: Order_Amount, Quantity, Discount_Amount, Tax_Amount, Net_Amount

### Example: HR Data Model

**Fact tables**: Fact_Attendance, Fact_Performance_Reviews
**Dimensions**: Dim_Employees, Dim_Departments, Dim_Calendar, Dim_Locations

**Key relationships**:
- Fact_Attendance -> Dim_Employees (via Employee_Key)
- Fact_Attendance -> Dim_Calendar (via Attendance_Date)
- Dim_Employees -> Dim_Departments (via Department_Key)
- Dim_Employees -> Dim_Locations (via Location_Key)
