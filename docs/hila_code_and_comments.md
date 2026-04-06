### This file is for Hila's use

# important commands

What files are in the folder?:

```gsutil ls gs://intelia-hackathon-files/```

Read top 6 rows of a file:

```gcloud storage cat gs://intelia-hackathon-files/customers.csv | head -n 6```


Enable Dataflow and BigQuery APIs:

```gcloud services enable dataflow.googleapis.com bigquery.googleapis.com```

### Relavant labs with code
Using Dataflow Template (we need to start somewhere):
https://www.skills.google/paths/85/course_templates/53/labs/592802

Better with code:
Serverless Data Processing with Dataflow - Writing an ETL Pipeline using Apache Beam and Dataflow (Python)
First part uses code, Task 3 uses template

https://www.skills.google/paths/85/course_templates/229/labs/607614

Dealing with DLQ and other bad data inserted:
https://www.skills.google/paths/85/course_templates/53/labs/592810


## for the CTO questions:
Serverless Data Processing with Dataflow - Batch Analytics Pipelines with Dataflow (Python)
https://www.skills.google/paths/85/course_templates/229/labs/607621



