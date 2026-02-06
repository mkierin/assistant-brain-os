---
name: "qlik-incremental-loads"
domain: "qlik-data-modeling"
version: "1.0"
description: "Incremental load patterns for Qlik to efficiently update QVD files without full reloads"
tags:
  - "qlik"
  - "incremental"
  - "QVD"
  - "performance"
  - "ETL"
keywords:
  - "incremental load"
  - "QVD"
  - "delta load"
  - "insert only"
  - "upsert"
  - "performance"
  - "optimization"
output_types:
  - "qvs"
  - "md"
author: "Assistant Brain OS"
---

# Qlik Incremental Load Patterns

## Overview

Incremental loads update only new or changed records instead of reloading everything from scratch. This dramatically reduces reload times for large datasets.

## Pattern 1: Insert-Only (Append)

Use when source data only adds new records (e.g., log events, transactions).

### Template: Insert-Only Load

```qvs
///$tab Incremental_{{table_name}}
/**
 * Incremental Load: {{table_name}} (Insert-Only)
 * Only loads records newer than the last load.
 */

// Step 1: Load existing QVD
[{{table_name}}]:
LOAD * FROM [lib://{{connection}}/QVD/{{table_name}}.qvd] (qvd);

// Step 2: Get the max date from existing data
LET vMaxDate = Peek('{{date_field}}', -1, '{{table_name}}');

// Step 3: Load only new records from source
[{{table_name}}_New]:
LOAD
    *
FROM [lib://{{connection}}/{{source_path}}]
WHERE {{date_field}} > '$(vMaxDate)';

// Step 4: Concatenate new records
Concatenate([{{table_name}}])
LOAD * RESIDENT [{{table_name}}_New];

DROP TABLE [{{table_name}}_New];

// Step 5: Store updated QVD
STORE [{{table_name}}] INTO [lib://{{connection}}/QVD/{{table_name}}.qvd] (qvd);
DROP TABLE [{{table_name}}];
```

## Pattern 2: Insert/Update (Upsert)

Use when source records can be updated (e.g., customer profiles, order statuses).

### Template: Upsert Load

```qvs
///$tab Incremental_{{table_name}}
/**
 * Incremental Load: {{table_name}} (Upsert)
 * Loads new records and updates existing ones.
 */

// Step 1: Load new/changed records from source
[{{table_name}}_Delta]:
LOAD
    *
FROM [lib://{{connection}}/{{source_path}}]
WHERE {{modified_date_field}} >= '$(vLastReloadDate)';

// Step 2: Load existing QVD, excluding records that were updated
[{{table_name}}]:
LOAD
    *
FROM [lib://{{connection}}/QVD/{{table_name}}.qvd] (qvd)
WHERE NOT EXISTS({{primary_key}});

// Step 3: Concatenate delta records
Concatenate([{{table_name}}])
LOAD * RESIDENT [{{table_name}}_Delta];

DROP TABLE [{{table_name}}_Delta];

// Step 4: Store updated QVD
STORE [{{table_name}}] INTO [lib://{{connection}}/QVD/{{table_name}}.qvd] (qvd);
DROP TABLE [{{table_name}}];

// Step 5: Track reload date
LET vLastReloadDate = Now();
```

## Best Practices

1. **Always store QVDs** after incremental loads. The next reload reads from the QVD.
2. **Track the last reload timestamp** in a variable or separate tracking QVD.
3. **Use optimized QVD loads** where possible (no WHERE clause, no field transformations). Optimized loads are 10-100x faster.
4. **Full reload periodically**: Run a full reload weekly/monthly to catch any missed changes and clean up deleted records.
5. **Log row counts**: Print row counts before and after each step to verify the incremental load is working correctly.

## Anti-Patterns

1. **Never modify fields during a QVD read** if you want optimized load speed. Apply transformations in a subsequent LOAD RESIDENT step.
2. **Don't skip the full reload**: Incremental loads can drift over time. Schedule periodic full reloads.
3. **Don't use incremental loads for small tables** (<100K rows). The complexity isn't worth it for fast-loading tables.
