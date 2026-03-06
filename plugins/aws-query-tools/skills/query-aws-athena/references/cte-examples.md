# Common Table Expression (CTE) Patterns and Examples

## Overview

This document provides practical patterns and examples for using Common Table Expressions (CTEs) in AWS Athena queries. CTEs help avoid repeated subquery execution, improve query performance, and make SQL more readable.

## Basic CTE Syntax

```sql
WITH cte_name AS (
    SELECT ...
    FROM ...
    WHERE ...
)
SELECT *
FROM cte_name;
```

## Pattern 1: Avoiding Repeated Subqueries

### Problem
```sql
-- BAD: Subquery executed multiple times
SELECT
    order_id,
    total_amount,
    (SELECT AVG(total_amount) FROM orders WHERE status = 'completed') as avg_order,
    total_amount - (SELECT AVG(total_amount) FROM orders WHERE status = 'completed') as diff_from_avg
FROM orders
WHERE status = 'completed';
```

### Solution
```sql
-- GOOD: Subquery executed once
WITH order_stats AS (
    SELECT AVG(total_amount) as avg_order
    FROM orders
    WHERE status = 'completed'
)
SELECT
    o.order_id,
    o.total_amount,
    s.avg_order,
    o.total_amount - s.avg_order as diff_from_avg
FROM orders o
CROSS JOIN order_stats s
WHERE o.status = 'completed';
```

## Pattern 2: Multi-Stage Data Transformation

### Example: User Engagement Analysis
```sql
WITH
    -- Stage 1: Extract raw data
    raw_events AS (
        SELECT
            user_id,
            event_type,
            timestamp,
            date_partition
        FROM events
        WHERE date_partition BETWEEN '2025-01-01' AND '2025-01-31'
    ),

    -- Stage 2: Calculate daily metrics
    daily_metrics AS (
        SELECT
            user_id,
            date_partition,
            COUNT(*) as event_count,
            COUNT(DISTINCT event_type) as unique_event_types,
            MIN(timestamp) as first_event,
            MAX(timestamp) as last_event
        FROM raw_events
        GROUP BY user_id, date_partition
    ),

    -- Stage 3: Compute engagement scores
    engagement_scores AS (
        SELECT
            user_id,
            date_partition,
            event_count,
            unique_event_types,
            CASE
                WHEN event_count >= 50 THEN 'high'
                WHEN event_count >= 10 THEN 'medium'
                ELSE 'low'
            END as engagement_level
        FROM daily_metrics
    )

-- Final query: Aggregate by engagement level
SELECT
    engagement_level,
    COUNT(DISTINCT user_id) as user_count,
    AVG(event_count) as avg_events_per_day,
    AVG(unique_event_types) as avg_unique_events
FROM engagement_scores
GROUP BY engagement_level
ORDER BY engagement_level;
```

## Pattern 3: Reusing the Same CTE Multiple Times

### Example: Sales Analysis with Multiple Perspectives
```sql
WITH sales_summary AS (
    SELECT
        product_id,
        product_category,
        SUM(quantity) as total_quantity,
        SUM(revenue) as total_revenue,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM sales
    WHERE date_partition >= '2025-01-01'
    GROUP BY product_id, product_category
)

-- Analyze from multiple perspectives using the same CTE
SELECT
    'Top Products by Revenue' as analysis_type,
    product_id,
    total_revenue,
    total_quantity
FROM sales_summary
ORDER BY total_revenue DESC
LIMIT 10

UNION ALL

SELECT
    'Top Products by Quantity' as analysis_type,
    product_id,
    total_revenue,
    total_quantity
FROM sales_summary
ORDER BY total_quantity DESC
LIMIT 10

UNION ALL

SELECT
    'Top Products by Customer Count' as analysis_type,
    product_id,
    total_revenue,
    unique_customers as total_quantity  -- Using field name for union compatibility
FROM sales_summary
ORDER BY unique_customers DESC
LIMIT 10;
```

## Pattern 4: Self-Joins Made Easier

### Example: Finding User Retention
```sql
WITH
    -- CTE for first-time users
    first_purchases AS (
        SELECT
            customer_id,
            MIN(order_date) as first_order_date
        FROM orders
        GROUP BY customer_id
    ),

    -- CTE for repeat purchases
    repeat_purchases AS (
        SELECT
            o.customer_id,
            COUNT(*) as subsequent_orders
        FROM orders o
        JOIN first_purchases f ON o.customer_id = f.customer_id
        WHERE o.order_date > f.first_order_date
        GROUP BY o.customer_id
    )

-- Calculate retention metrics
SELECT
    DATE_TRUNC('month', f.first_order_date) as cohort_month,
    COUNT(DISTINCT f.customer_id) as total_customers,
    COUNT(DISTINCT r.customer_id) as retained_customers,
    CAST(COUNT(DISTINCT r.customer_id) AS DOUBLE) /
        CAST(COUNT(DISTINCT f.customer_id) AS DOUBLE) * 100 as retention_rate
FROM first_purchases f
LEFT JOIN repeat_purchases r ON f.customer_id = r.customer_id
GROUP BY DATE_TRUNC('month', f.first_order_date)
ORDER BY cohort_month;
```

## Pattern 5: Window Functions with CTEs

### Example: Ranking with Context
```sql
WITH
    -- Calculate rankings within each category
    ranked_products AS (
        SELECT
            product_id,
            product_name,
            category,
            revenue,
            ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) as rank_in_category,
            SUM(revenue) OVER (PARTITION BY category) as category_total_revenue
        FROM product_sales
        WHERE year = 2025
    )

-- Show top 3 products per category with category context
SELECT
    category,
    product_name,
    revenue,
    rank_in_category,
    category_total_revenue,
    CAST(revenue AS DOUBLE) / CAST(category_total_revenue AS DOUBLE) * 100 as pct_of_category
FROM ranked_products
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;
```

## Pattern 6: Filtering After Aggregation

### Example: Finding Power Users
```sql
WITH
    -- Aggregate user activity
    user_activity AS (
        SELECT
            user_id,
            COUNT(*) as total_events,
            COUNT(DISTINCT DATE(timestamp)) as active_days,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM events
        WHERE date_partition >= '2025-01-01'
        GROUP BY user_id
    ),

    -- Filter for power users (more than 30 active days)
    power_users AS (
        SELECT *
        FROM user_activity
        WHERE active_days > 30
    )

-- Analyze power user behavior
SELECT
    DATE_TRUNC('week', last_seen) as week,
    COUNT(*) as power_user_count,
    AVG(total_events) as avg_events,
    AVG(active_days) as avg_active_days
FROM power_users
GROUP BY DATE_TRUNC('week', last_seen)
ORDER BY week;
```

## Pattern 7: Complex Joins Simplified

### Example: Customer Lifetime Value with Multiple Data Sources
```sql
WITH
    -- Customer purchase history
    customer_purchases AS (
        SELECT
            customer_id,
            SUM(total_amount) as total_purchase_value,
            COUNT(*) as order_count,
            MIN(order_date) as first_order,
            MAX(order_date) as last_order
        FROM orders
        GROUP BY customer_id
    ),

    -- Customer support interactions
    customer_support AS (
        SELECT
            customer_id,
            COUNT(*) as support_ticket_count,
            AVG(resolution_time_hours) as avg_resolution_time
        FROM support_tickets
        GROUP BY customer_id
    ),

    -- Customer demographics
    customer_info AS (
        SELECT
            customer_id,
            signup_date,
            country,
            subscription_tier
        FROM customers
    )

-- Combine all data sources for comprehensive customer view
SELECT
    ci.customer_id,
    ci.country,
    ci.subscription_tier,
    COALESCE(cp.total_purchase_value, 0) as lifetime_value,
    COALESCE(cp.order_count, 0) as total_orders,
    COALESCE(cs.support_ticket_count, 0) as support_tickets,
    DATE_DIFF('day', ci.signup_date, CURRENT_DATE) as days_since_signup,
    COALESCE(cp.total_purchase_value, 0) /
        NULLIF(DATE_DIFF('day', ci.signup_date, CURRENT_DATE), 0) as daily_ltv
FROM customer_info ci
LEFT JOIN customer_purchases cp ON ci.customer_id = cp.customer_id
LEFT JOIN customer_support cs ON ci.customer_id = cs.customer_id
WHERE ci.signup_date >= DATE('2025-01-01')
ORDER BY lifetime_value DESC;
```

## Pattern 8: Pivot-Like Operations

### Example: Converting Rows to Columns
```sql
WITH
    -- Base metrics
    monthly_metrics AS (
        SELECT
            product_id,
            DATE_TRUNC('month', order_date) as month,
            SUM(quantity) as quantity_sold
        FROM sales
        WHERE order_date >= DATE('2025-01-01')
        GROUP BY product_id, DATE_TRUNC('month', order_date)
    )

-- Pivot months into columns
SELECT
    product_id,
    SUM(CASE WHEN month = DATE('2025-01-01') THEN quantity_sold ELSE 0 END) as jan_sales,
    SUM(CASE WHEN month = DATE('2025-02-01') THEN quantity_sold ELSE 0 END) as feb_sales,
    SUM(CASE WHEN month = DATE('2025-03-01') THEN quantity_sold ELSE 0 END) as mar_sales,
    SUM(quantity_sold) as total_sales
FROM monthly_metrics
GROUP BY product_id
ORDER BY total_sales DESC;
```

## Pattern 9: Recursive CTEs (Hierarchical Data)

### Example: Organization Hierarchy
```sql
WITH RECURSIVE org_hierarchy AS (
    -- Base case: Top-level managers
    SELECT
        employee_id,
        employee_name,
        manager_id,
        1 as level,
        CAST(employee_name AS VARCHAR) as path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case: Employees reporting to previous level
    SELECT
        e.employee_id,
        e.employee_name,
        e.manager_id,
        h.level + 1,
        h.path || ' > ' || e.employee_name
    FROM employees e
    JOIN org_hierarchy h ON e.manager_id = h.employee_id
)

SELECT
    employee_id,
    employee_name,
    level,
    path as reporting_chain
FROM org_hierarchy
ORDER BY level, employee_name;
```

## Pattern 10: Data Quality Checks

### Example: Identifying Data Anomalies
```sql
WITH
    -- Calculate expected ranges
    historical_stats AS (
        SELECT
            metric_name,
            AVG(metric_value) as avg_value,
            STDDEV(metric_value) as stddev_value
        FROM metrics
        WHERE date_partition BETWEEN '2025-01-01' AND '2025-01-31'
        GROUP BY metric_name
    ),

    -- Get today's metrics
    current_metrics AS (
        SELECT
            metric_name,
            metric_value,
            timestamp
        FROM metrics
        WHERE date_partition = CURRENT_DATE
    )

-- Flag anomalies (values more than 3 standard deviations from mean)
SELECT
    c.metric_name,
    c.metric_value as current_value,
    h.avg_value as historical_avg,
    ABS(c.metric_value - h.avg_value) / h.stddev_value as std_deviations,
    CASE
        WHEN ABS(c.metric_value - h.avg_value) > 3 * h.stddev_value THEN 'ANOMALY'
        ELSE 'NORMAL'
    END as status
FROM current_metrics c
JOIN historical_stats h ON c.metric_name = h.metric_name
WHERE ABS(c.metric_value - h.avg_value) > 2 * h.stddev_value
ORDER BY std_deviations DESC;
```

## Best Practices for CTEs

1. **Name CTEs descriptively** to indicate their purpose
2. **Order from simple to complex** - build up complexity gradually
3. **Add comments** to explain complex CTEs
4. **Use CTEs to avoid repetition** - if you reference the same subquery twice, use a CTE
5. **Keep CTEs focused** - each CTE should have a single, clear purpose
6. **Consider materialization** - for very large intermediate results, consider creating temporary tables instead

## Performance Tips

- **CTEs are typically optimized** by Athena's query planner
- **Avoid overly complex CTEs** - if a CTE becomes too complex, consider breaking it into multiple steps
- **Use appropriate data types** to minimize memory usage
- **Filter early** - apply WHERE clauses as early as possible in the CTE chain
- **Partition pruning** - ensure date_partition filters are applied in the earliest CTE possible

## When to Use CTEs vs. Subqueries

**Use CTEs when**:
- The same subquery is referenced multiple times
- Building complex queries with multiple transformation stages
- Improving query readability and maintainability
- Working with recursive queries

**Use subqueries when**:
- Simple, one-time transformations
- The subquery is only used once
- Very simple queries where CTE overhead is unnecessary
