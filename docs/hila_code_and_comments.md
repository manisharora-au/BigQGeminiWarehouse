### This file is for Hila's use and it doesn't go into the presentation


# VERY IMPORTANT
Hila doesn't have access to Dataflow

# Important basic commands

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


## For the CTO questions:
Serverless Data Processing with Dataflow - Batch Analytics Pipelines with Dataflow (Python)
https://www.skills.google/paths/85/course_templates/229/labs/607621


## and the dataplex:
https://cloud.google.com/dataplex?hl=en


## becuase we don't use Dataflow:
https://www.skills.google/focuses/102965?parent=catalog




