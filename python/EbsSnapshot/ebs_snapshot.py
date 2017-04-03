#!/usr/bin/env python
from __future__ import print_function

import boto3
import logging
import datetime
import sys
import os

#Set logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#define the connection region
ec = boto3.resource('ec2', region_name='us-east-1')
ec2 = boto3.client('ec2', region_name='us-east-1')

def lambda_handler(event, context):

  if os.environ['customer_name'] and os.environ['retention']:
    try:
      if isinstance(os.environ['customer_name'], basestring) and isinstance(int(os.environ['retention']), int):
        customer_name = os.environ['customer_name']
        retention = int(os.environ['retention'])
        logger.info("Starting EBS snapshot for: [customer_name = '%s', retention = '%d']" % (customer_name, retention))
    except Exception as error:
        logger.error("Environment Variables Exception: %s - %s" % (type(error), str(error)))
        sys.exit(logger.error("Please provide customer name and retention days for taking EBS Snapshot"))

  #Diff dates
  timeLimit = (datetime.datetime.now() - datetime.timedelta(days=int(retention))).date().strftime('%Y-%m-%d')
  delete_tag = (datetime.datetime.now() + datetime.timedelta(days=int(retention))).strftime('%Y-%m-%d')

  logger.info("Starting EBS snapshot for: [customer_name = '%s', retention = '%d']" % (customer_name, retention))

  #List all Customer's Solr instances
  filters = [{'Name':'tag:Customer', 'Values':[customer_name]}, {'Name':'tag:Role', 'Values':['IndexServer']}]

  base = list(ec.instances.filter(Filters=filters))

  #Narrow down to device '/dev/sdm'
  for instance in base:
    for vol in instance.volumes.all():
      dev = vol.attachments[0]['Device']
      if dev == '/dev/sdm':
        logger.info("EBS volume to backup: [Customer: '%s', Instance: '%s', Volume: '%s']"
                                         % (filters[0]['Values'][0], instance.id, vol.id))

        #Create snapshot
        try:
          create_snapshot = ec2.create_snapshot(VolumeId='%s' % (vol.id),
                                                Description= "Customer: %s, Role: %s, Instance: %s, Date: %s" 
                                                              % (filters[0]['Values'][0], filters[1]['Values'][0], instance.id,
                                                                 datetime.datetime.now().strftime('%Y-%m-%d')))
          logger.info("Creating snapshot: %s" % (create_snapshot['SnapshotId']))
        except Exception as e:
          logger.error("Create snapshot Exception: %s - %s" % (type(e), str(e)))

        #Tag snapshot
        try:
          tag_snapshot = ec2.create_tags(Resources=[create_snapshot['SnapshotId']], 
                                         Tags=[{'Key': filters[0]['Name'].split(':')[1], 'Value': filters[0]['Values'][0]},
                                               {'Key': filters[1]['Name'].split(':')[1], 'Value': filters[1]['Values'][0]},
                                               {'Key': 'DeleteOn', 'Value': delete_tag}])
          logger.info("Creating tags for snapshot")
        except Exception as e:
          logger.error("Create tag Exception: %s - %s" % (type(e), str(e)))

  #Delete snapshots older than X days
  customer_snapshots = ec2.describe_snapshots(Filters=filters)

  for snaps in customer_snapshots['Snapshots']:
    if ((snaps['StartTime']).date().strftime('%Y-%m-%d')) <= timeLimit:
      logger.info("EBS snapshot to delete: [Customer: '%s', SnapshotId: '%s', Dated: '%s']"
                   % (filters[0]['Values'][0], snaps['SnapshotId'], 
                      snaps['StartTime'].date().strftime('%Y-%m-%d')))
      try:
        delete_snaphot = ec2.delete_snapshot(SnapshotId=snaps['SnapshotId'])
        logger.info("Deleting Snapshot: %s" % (snaps['SnapshotId']))
      except Exceptin as e:
        logger.error("Delete Snapshot Exception: %s - %s" % (type(e), str(e)))

