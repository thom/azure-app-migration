# TechConf Registration Website

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Dependencies](#dependencies)
- [Instructions](#instructions)
  - [Create Azure Resources and Deploy Web App](#create-azure-resources-and-deploy-web-app)
    - [Login with Azure CLI](#login-with-azure-cli)
    - [Create a Resource Group](#create-a-resource-group)
    - [Create an Azure Postgres Database single server](#create-an-azure-postgres-database-single-server)
    - [Create a Service Bus resource](#create-a-service-bus-resource)
    - [Configuration](#configuration)
    - [Create a storage account](#create-a-storage-account)
    - [Create App Service plan and deploy the web app](#create-app-service-plan-and-deploy-the-web-app)
  - [Part 2: Create and Publish Azure Function](#part-2-create-and-publish-azure-function)
  - [Part 3: Refactor `routes.py`](#part-3-refactor-routespy)
- [Monthly Cost Analysis](#monthly-cost-analysis)
- [Architecture Explanation](#architecture-explanation)
- [Clean-up](#clean-up)
- [References](#references)
- [Requirements](#requirements)
- [License](#license)

## Introduction

The TechConf website allows attendees to register for an upcoming conference. Administrators can also view the list of attendees and notify all attendees via a personalized email message.

The application is currently working but the following pain points have triggered the need for migration to Azure:

- The web application is not scalable to handle user load at peak
- When the admin sends out notifications, it's currently taking a long time because it's looping through all attendees, resulting in some HTTP timeout exceptions
- The current architecture is not cost-effective

This project accomplishes the following:

- Migrates and deploys the pre-existing web app to an Azure App Service
- Migrates a PostgreSQL database backup to an Azure Postgres database instance
- Refactors the notification logic to an Azure Function via a service bus queue message

## Getting Started

1. Clone this repository
2. Ensure you have all the dependencies
3. Follow the instructions below

## Dependencies

You will need to install the following locally:

- [PostgreSQL](https://www.postgresql.org/download/)
- [Visual Studio Code](https://code.visualstudio.com/download)
- [Azure Function tools V3](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Ccsharp%2Cbash#install-the-azure-functions-core-tools)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
- [Azure Tools for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-node-azure-pack)

## Instructions

### Create Azure Resources and Deploy Web App

#### Login with Azure CLI

This project uses your Azure user and the Azure CLI to login and execute commands:

```bash
az login
```

Check [Create an Azure service principal with the Azure CLI](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest) if you prefer using a service principal instead.

#### Create a Resource Group

Run the code below to create a new Resource Group:

```bash
az group create \
    --name techconf-app-rg \
    --location eastus \
    --tags "dept=Engineering" \
    --tags "environment=Production" \
    --tags "project=Udacity TechConf App" \
    --tags "createdby=CLI"
```

#### Create an Azure Postgres Database single server

Create an Azure Database for PostgreSQL server by using the `az postgres server create` command. A server can contain multiple databases:

```bash
az postgres server create \
    --resource-group techconf-app-rg \
    --name techconf-app-psql \
    --location eastus \
    --admin-user adminuser \
    --admin-password <yourpassword> \
    --sku-name B_Gen5_1 \
    --version 11
```

Add a new database `techconfdb`:

```bash
az postgres db create \
    --resource-group techconf-app-rg \
    --server-name techconf-app-psql \
    --name techconfdb
```

Allow your IP to connect to database server:

```bash
az postgres server firewall-rule create \
    --resource-group techconf-app-rg \
    --server techconf-app-psql \
    --name AllowMyIP \
    --start-ip-address <yourip> \
    --end-ip-address <yourip>
```

Check [What Is My IP Address](https://whatismyipaddress.com/) to see your IP address.

Create the database tables:

```bash
psql -h techconf-app-psql.postgres.database.azure.com -p 5432 -d techconfdb -U adminuser@techconf-app-psql -f data/techconfdb_backup.sql
```

Restore the database with the backup located in the data folder:

```bash
pg_restore \
    -h techconf-app-psql.postgres.database.azure.com \
    -p 5432 \
    --no-tablespaces \
    -W -O -F t -x \
    -d techconfdb \
    -U adminuser@techconf-app-psql \
    data/techconfdb_backup.tar
```

#### Create a Service Bus resource

Create a Service Bus resource with a `notificationqueue` that will be used to communicate between the web and the function.

Run the following command to create a Service Bus messaging namespace:

```bash
az servicebus namespace create \
    --resource-group techconf-app-rg \
    --name techconf-app-sbus \
    --location eastus \
    --sku Basic
```

Run the following command to create a queue in the namespace you created in the previous step:

```bash
az servicebus queue create \
    --resource-group techconf-app-rg \
    --namespace-name techconf-app-sbus \
    --name notificationqueue
```

Run the following command to get the primary connection string for the namespace. You use this connection string to connect to the queue and send and receive messages:

```bash
az servicebus namespace authorization-rule keys list \
    --resource-group techconf-app-rg \
    --namespace-name techconf-app-sbus \
    --name RootManageSharedAccessKey \
    --query primaryConnectionString \
    --output tsv
```

#### Configuration

Open the web folder and update the following in the `config.py` file

- `POSTGRES_URL`
- `POSTGRES_USER`
- `POSTGRES_PW`
- `POSTGRES_DB`
- `SERVICE_BUS_CONNECTION_STRING`

#### Create a storage account

```bash
az storage account create \
    --name techconfappst \
    --resource-group techconf-app-rg \
    --location eastus \
    --sku Standard_LRS
```

#### Create App Service plan and deploy the web app

Change into the `web` directory and deploy the web app with a new service plan:

```bash
az webapp up \
    --resource-group techconf-app-rg \
    --name techconf-app \
    --plan techconf-app-asp \
    --sku F1 \
    --verbose
```

### Part 2: Create and Publish Azure Function

1. Create an Azure Function in the `function` folder that is triggered by the service bus queue created in Part 1.

   **Note**: Skeleton code has been provided in the **README** file located in the `function` folder. You will need to copy/paste this code into the `__init.py__` file in the `function` folder.

   - The Azure Function should do the following:
     - Process the message which is the `notification_id`
     - Query the database using `psycopg2` library for the given notification to retrieve the subject and message
     - Query the database to retrieve a list of attendees (**email** and **first name**)
     - Loop through each attendee and send a personalized subject message
     - After the notification, update the notification status with the total number of attendees notified

2. Publish the Azure Function

### Part 3: Refactor `routes.py`

1. Refactor the post logic in `web/app/routes.py -> notification()` using servicebus `queue_client`:
   - The notification method on POST should save the notification object and queue the notification id for the function to pick it up
2. Re-deploy the web app to publish changes

## Monthly Cost Analysis

Complete a month cost analysis of each Azure resource to give an estimate total cost using the table below:

| Azure Resource            | Service Tier | Monthly Cost |
| ------------------------- | ------------ | ------------ |
| _Azure Postgres Database_ |              |              |
| _Azure Service Bus_       |              |              |
| ...                       |              |              |

## Architecture Explanation

This is a placeholder section where you can provide an explanation and reasoning for your architecture selection for both the Azure Web App and Azure Function.

## Clean-up

Clean up and remove all services, or else you will incur charges:

```bash
az group delete --name techconf-app-rg
```

## References

TBD

- []()

## Requirements

Graded according to the [Project Rubric](https://review.udacity.com/#!/rubrics/2824/view).

## License

- **[MIT license](http://opensource.org/licenses/mit-license.php)**
- Copyright 2021 © [Thomas Weibel](https://github.com/thom).
