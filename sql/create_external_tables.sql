-- External Tables for Raw Data Layer
-- Creates external tables pointing to CSV files in GCS bucket

-- 1. Customers External Table
CREATE OR REPLACE EXTERNAL TABLE `manish-sandpit.raw_ext.customers`
OPTIONS (
  format = 'CSV',
  uris = ['gs://intelia-hackathon-dev-raw-data/customers.csv'],
  skip_leading_rows = 1,
  allow_jagged_rows = false,
  allow_quoted_newlines = false
);

-- 2. Products External Table  
CREATE OR REPLACE EXTERNAL TABLE `manish-sandpit.raw_ext.products`
OPTIONS (
  format = 'CSV',
  uris = ['gs://intelia-hackathon-dev-raw-data/products.csv'],
  skip_leading_rows = 1,
  allow_jagged_rows = false,
  allow_quoted_newlines = false
);

-- 3. Orders External Table
CREATE OR REPLACE EXTERNAL TABLE `manish-sandpit.raw_ext.orders`
OPTIONS (
  format = 'CSV',
  uris = ['gs://intelia-hackathon-dev-raw-data/orders.csv'],
  skip_leading_rows = 1,
  allow_jagged_rows = false,
  allow_quoted_newlines = false
);

-- 4. Order Items External Table
CREATE OR REPLACE EXTERNAL TABLE `manish-sandpit.raw_ext.order_items`
OPTIONS (
  format = 'CSV',
  uris = ['gs://intelia-hackathon-dev-raw-data/order_items.csv'],
  skip_leading_rows = 1,
  allow_jagged_rows = false,
  allow_quoted_newlines = false
);