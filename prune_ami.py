# Prune all AMIs older than X days that are not in use by a Launch Configuration provided a minimum of Y exists

import boto3
import logging
import os
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from dateutil.parser import parse

aws_account_id = os.getenv('aws_account_id', default=None)
aws_region = os.getenv('aws_region', 'eu-west-1')
node_types = os.getenv('node_types').split(',')
min_number_to_retain = int(os.getenv('min_number_to_retain'))
min_days_to_retain = int(os.getenv('min_days_to_retain'))
dry_run = os.getenv('dry_run')

# Create Autoscaling and EC2 clients
ec2client = boto3.client('ec2', aws_region)
asclient = boto3.client('autoscaling', aws_region)


def lambda_handler(event, context):
    logger = logging.getLogger()
    # Set log level to INFO
    logger.setLevel(20)

    try:
        oldest_allowed = datetime.now() - timedelta(days=min_days_to_retain)

        for nodetype in node_types:
            images = []
            images_for_deletion = []
            images = get_images(nodetype)
            logger.info("Now evaluating nodetype %s", nodetype)

            # Count previous images for this nodetype
            num_existing_images = check_count(images)

            if num_existing_images > min_number_to_retain:
                # Check if the image meets the criteria for deletion
                logger.info(
                    "There are %s existing images for %s which exceeds the number to retain (%s)",
                    num_existing_images, nodetype, min_number_to_retain)

                for image in images:
                    if check_date(image, oldest_allowed) and not is_in_launch_config(image):
                        images_for_deletion.append(image)
                    else:
                        logger.info("%s will not be deleted",
                                    image['ImageId'])
            else:
                logger.info("There are %s existing images for %s We want to keep %s at a minimum so no images will be deleted",
                            num_existing_images, nodetype, min_number_to_retain)

            # Remove the images up to the limit

            if images_for_deletion:
                # Ensure we don't delete more than we should
                upper_limit = num_existing_images - min_number_to_retain
                deleted_count = 0
                for image in images_for_deletion:
                    if deleted_count >= upper_limit:
                        break
                    remove_image(image)
                    deleted_count += 1
            else:
                logger.info("No %s AMIs will be deleted this time", nodetype)

    except Exception as e:
        logger.error("Prune AMIs failed")
        print(type(e))
        raise e


def get_images(nodetype):
    # Get all available images that match the nodetype tag

    response = ec2client.describe_images(
        Filters=[
            {
                'Name': 'tag:' 'nodetype',
                'Values': [
                    nodetype,
                ]
            },
            {
                'Name': 'state',
                'Values': [
                    'available',
                ]
            },
        ],
        Owners=[
            aws_account_id,
        ],
    )

    sorted_list = sort_by_age(response)
    return sorted_list


def is_in_launch_config(image):
    # Check all launch configs to make sure the image isn't in use

    logger = logging.getLogger()
    # Set log level to INFO
    logger.setLevel(20)

    image_id = image['ImageId']
    response = asclient.describe_launch_configurations()
    in_lc = False
    for launch_configuration in response['LaunchConfigurations']:
        if launch_configuration['ImageId'] == image_id:
            in_lc = True
            logger.info(
                "%s is part of a launch configuration and cannot be deleted", image_id)
    return in_lc


def check_count(images):
    count = 0
    for image in images:
        count += 1
    return count


def check_date(images, threshold_date):
    logger = logging.getLogger()
    # Set log level to INFO
    logger.setLevel(20)

    creation_timestamp = images['CreationDate']
    creation_date = parse(creation_timestamp)

    # Just strip the timezone info
    creation_date = creation_date.replace(tzinfo=None)
    if creation_date < threshold_date:
        logger.info("Creation date for image %s is %s which is before threshold date %s. Date check passed.",
                    images['ImageId'], creation_date, threshold_date)
    else:
        logger.info("Creation date for image %s is %s which is before threshold date %s. Date check not passed.",
                    images['ImageId'], creation_date, threshold_date)
    return creation_date < threshold_date


def remove_image(image):
    logger = logging.getLogger()
    # Set log level to INFO
    logger.setLevel(20)

    # Remove the image and snapshots
    snaps = []
    for storage in image['BlockDeviceMappings']:
        snaps.append(storage['Ebs']['SnapshotId'])
    if dry_run == "false":
        logger.info("Image %s is being deleted", image['ImageId'])
        ec2client.deregister_image(ImageId=image['ImageId'])
    else:
        logger.info("Dry run is enabled. Image %s would be deleted",
                    image['ImageId'])
    for snapshot in snaps:
        if dry_run == "false":
            logger.info("Snapshot %s is being deleted", snapshot)
            ec2client.delete_snapshot(SnapshotId=snapshot)
        else:
            logger.info(
                "Dry run enabled. Snapshot %s would be deleted", snapshot)


def sort_by_age(images):
    # Sort images by creation date

    list_images = []
    sorted_images = []

    for image in images['Images']:
        creation_timestamp = image['CreationDate']
        creation_date = parse(creation_timestamp)

        # Just strip the timezone info
        creation_date = creation_date.replace(tzinfo=None)
        list_images.append(image)
    sorted_images = sorted(list_images, key=lambda k: k['CreationDate'])

    return sorted_images
