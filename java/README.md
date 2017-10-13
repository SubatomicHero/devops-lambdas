The Java code that used to be in this repository has been integrated into two new projects.

The S3 cleaner functionality has been moved to a [utility class](https://github.com/Alfresco/alfresco-lambda-java-utils/blob/master/src/main/java/org/alfresco/aws/lambda/utils/S3Cleaner.java) in https://github.com/Alfresco/alfresco-lambda-java-utils

The empty bucket lambda function has been moved to it's own repository here: https://github.com/Alfresco/alfresco-lambda-empty-s3-bucket

The [utils](https://artifacts.alfresco.com/nexus/#nexus-search;quick~alfresco-lambda-java-utils) and [empty bucket](https://artifacts.alfresco.com/nexus/#nexus-search;quick~alfresco-lambda-empty-s3-bucket) projects use maven to build and subsequently release artifcats to our [maven repository](https://artifacts.alfresco.com/nexus).
