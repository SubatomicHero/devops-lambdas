# Alfresco DevOps Lambdas
---
[![Build Status](https://travis-ci.org/Alfresco/devops-lambdas.svg?branch=master)](https://travis-ci.org/Alfresco/devops-lambdas)

This repo is a collection of Lambdas that we use internally for projects that are both internal and customer facing. We believe in sharing what we use and will continually add/improve and maintain the code.

## Structure
We have structured the repo by language and the structure isnt exhaustive either. Within each directory (Python, Java etc) are sub-directories containing our Lambdas. They *should* also contain the accompanying tests which also *should* be added to Travis to ensure that we maintain a quality codebase.

## Testing
We currently only test the Python Lambdas in the Python directory. The Python code is written using Python 2.6 (as was the supported Python platform at the time of development). Each test for each Lambda can be run using `python test_(name of test)`.

## WIP
* Implement Java improvements to produce JARS using Maven. Guide is [here](http://docs.aws.amazon.com/lambda/latest/dg/java-create-jar-pkg-maven-no-ide.html). Testing should happen in Travis first, then internally we use a build agent to produce the JARS.
* The Python Lambdas "ApiGatewayDomainName", "EbsSnapshot" and "ElbSgHardening" need unit testing.
* Some JS and Ruby Lambdas would be great!

## How to contribute
We use git-flow wherever possible so contributions must follow these guidelines:
1. Fork the repo
2. Branch from Develop
3. Make your changes
4. Test your changes
5. Make a PR to Develop

License and Author
---
Copyright 2016, Alfresco

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.