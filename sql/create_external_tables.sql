-- ==============================================================================
-- External Tables Creation for Validated Layer
-- Description: Creates external tables over GCS validated files with hive partitioning
-- Run this AFTER Terraform deployment completes
-- ==============================================================================

-- External Table: Customers
CREATE OR REPLACE EXTERNAL TABLE `${project_id}.validated_external.ext_customers`
OPTIONS (
  format = 'CSV',
  uris = ['gs://${bucket_name}/validated/customers/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  allow_jagged_rows = false,
  allow_quoted_newlines = false,
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://${bucket_name}/validated/customers/'
  )
) AS (
  SELECT 
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    date_of_birth,
    gender,
    registration_date,
    country,
    city,
    acquisition_channel,
    customer_tier,
    is_email_subscribed,
    is_sms_subscribed,
    preferred_device,
    preferred_category,
    loyalty_points,
    account_status,
    last_login_date,
    referral_source_id,
    marketing_segment,
    -- Delta-specific columns (nullable for full loads)
    _delta_type,
    _batch_id,
    _batch_date
  FROM
    EXTERNAL_QUERY(
      'projects/${project_id}/locations/${region}/connections/validated-external',
      'SELECT * FROM customers_schema'
    )
);

-- External Table: Products  
CREATE OR REPLACE EXTERNAL TABLE `${project_id}.validated_external.ext_products`
OPTIONS (
  format = 'CSV',
  uris = ['gs://${bucket_name}/validated/products/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  allow_jagged_rows = false,
  allow_quoted_newlines = false,
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://${bucket_name}/validated/products/'
  )
) AS (
  SELECT 
    product_id,
    sku,
    product_name,
    category,
    subcategory,
    brand,
    unit_cost,
    unit_price,
    discount_eligible,
    stock_quantity,
    weight_kg,
    supplier_id,
    is_active,
    created_date,
    last_updated_date,
    average_rating,
    review_count,
    return_rate,
    tags,
    -- Delta-specific columns
    _delta_type,
    _batch_id,
    _batch_date
  FROM
    EXTERNAL_QUERY(
      'projects/${project_id}/locations/${region}/connections/validated-external',
      'SELECT * FROM products_schema'
    )
);

-- External Table: Orders
CREATE OR REPLACE EXTERNAL TABLE `${project_id}.validated_external.ext_orders`
OPTIONS (
  format = 'CSV',
  uris = ['gs://${bucket_name}/validated/orders/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  allow_jagged_rows = false,
  allow_quoted_newlines = false,
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://${bucket_name}/validated/orders/'
  )
) AS (
  SELECT 
    order_id,
    customer_id,
    order_date,
    total_amount,
    tax_amount,
    shipping_amount,
    discount_amount,
    payment_method,
    shipping_method,
    order_status,
    shipping_address_line1,
    shipping_address_line2,
    shipping_city,
    shipping_state,
    shipping_country,
    shipping_postal_code,
    created_at,
    updated_at,
    -- Delta-specific columns
    _delta_type,
    _batch_id,
    _batch_date
  FROM
    EXTERNAL_QUERY(
      'projects/${project_id}/locations/${region}/connections/validated-external',
      'SELECT * FROM orders_schema'
    )
);

-- External Table: Order Items
CREATE OR REPLACE EXTERNAL TABLE `${project_id}.validated_external.ext_order_items`
OPTIONS (
  format = 'CSV',
  uris = ['gs://${bucket_name}/validated/order_items/*.csv'],
  skip_leading_rows = 1,
  field_delimiter = ',',
  allow_jagged_rows = false,
  allow_quoted_newlines = false,
  hive_partitioning_options = STRUCT(
    mode = 'AUTO',
    source_uri_prefix = 'gs://${bucket_name}/validated/order_items/'
  )
) AS (
  SELECT 
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    total_price,
    discount_amount,
    -- Delta-specific columns
    _delta_type,
    _batch_id,
    _batch_date
  FROM
    EXTERNAL_QUERY(
      'projects/${project_id}/locations/${region}/connections/validated-external',
      'SELECT * FROM order_items_schema'
    )
);

-- Grant access to Dataform service account
GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.validated_external.ext_customers`
TO "serviceAccount:${dataform_sa_email}";

GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.validated_external.ext_products`
TO "serviceAccount:${dataform_sa_email}";

GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.validated_external.ext_orders`
TO "serviceAccount:${dataform_sa_email}";

GRANT `roles/bigquery.dataViewer` ON TABLE `${project_id}.validated_external.ext_order_items`
TO "serviceAccount:${dataform_sa_email}";