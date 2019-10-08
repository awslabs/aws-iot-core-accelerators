import sys
import json
import logging
import cfnresponse
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

policyDocument = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "iot:*", "Resource": "*"},
    ],
}


def handler(event, context):
    responseData = {}
    try:
        logger.info("Received event: {}".format(json.dumps(event)))
        result = cfnresponse.FAILED
        iote_client = boto3.client('iotevents')
        iot_client = boto3.client('iot')
        SNSArn = event["ResourceProperties"]["SNSArn"]
        
        if event["RequestType"] == "Create":
            logger.info(
                "In Create "
            ) 
            logger.info("create the iote input")

            # create iotevents
            resp = iote_client.create_input(
                inputName = 'IoTCoreAccelInput',
                inputDescription = 'IoTCoreAccelInput',
                inputDefinition = {
                    'attributes': [
                        {
                            "jsonPath": "deviceType"
                        },
                        {
                            "jsonPath": "deviceID"
                        },
                        {
                            "jsonPath": "deviceData"
                        }
                    ]
                }
            )

            logger.info("Create the detector model for iote")

            # create iotevents
            response = iote_client.create_detector_model(
                detectorModelName = 'IoTCoreAccelDetectorModel',
                detectorModelDefinition = {
                'states': [
                    {
                        "stateName": "NormalState",
                        "onInput": {
                            "events": [
                                {
                                    "eventName": "Error",
                                    "condition": "$input.IoTCoreAccelInput.deviceData > 2049",                                   
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "$variable.errorEvent + 1"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "Good",
                                    "condition": "$input.IoTCoreAccelInput.deviceData <= 2049",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        }
                                    ]
                                }
                            ],
                            "transitionEvents": [
                                {
                                    "eventName": "ErrorTransition",
                                    "condition": "$variable.errorEvent > 4",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "$variable.errorEvent"
                                            }
                                        }                                        
                                    ],
                                    "nextState": "ErrorState"
                                }
                            ]
                        },
                        "onEnter": {
                            "events": [
                                {
                                    "eventName": "initial",
                                    "condition": "true",
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                        "onExit": {
                            "events": []
                        }
                    }, #arun
                    {
                        "stateName": "ErrorState",
                        "onInput": {
                            "transitionEvents": [
                                {
                                    "eventName": "NormalTransition",
                                    "condition": "$variable.errorEvent == 0",                                       
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        }
                                    ],
                                    "nextState": "NormalState"
                                }
                            ],
                            "events": [
                                {
                                    "eventName": "Error",
                                    "condition": "$input.IoTCoreAccelInput.deviceData > 2049",                                   
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "$variable.errorEvent + 1"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "Good",
                                    "condition": "$input.IoTCoreAccelInput.deviceData <= 2049",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "SendSNS",
                                    "condition": "$variable.errorEvent > 4",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        },
                                        {
                                            "sns": {
                                                "targetArn": SNSArn
                                            }
                                        }
                                    ],
                                }                                
                            ]
                        },
                        "onEnter": {
                            "events": [
                                {
                                    "eventName": "SendSNS",
                                    "condition": "$variable.errorEvent > 4",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "errorEvent",
                                                "value": "0"
                                            }
                                        },
                                        {
                                            "sns": {
                                                "targetArn": SNSArn
                                            }
                                        }
                                    ],
                                }
                            ]
                        },
                        "onExit": {
                            "events": []
                        }
                    }
                ],
                "initialStateName": "NormalState"
                },
            
                detectorModelDescription = 'Detector Model for IoT Core Accel',
                key = 'deviceData',
                roleArn = event['ResourceProperties']['IoTEventRoleArn']
            )

            logger.info('update rule action with iote input')
            #update rule action with iote input
            response = iot_client.create_topic_rule(
                ruleName='IoTCoreAccelRule',
                topicRulePayload={
                    'sql': "select * from 'iotcore_accelerator'",
                    'description': 'Routes IoTCoreAccel data for processing.',
                    'actions': [
                        {
                            'iotEvents': {
                                'inputName': 'IoTCoreAccelInput',
                                'roleArn': event['ResourceProperties']['IoTEventRoleArn']
                            }
                        },
                    ],
                    'ruleDisabled': False,
                }
            )
            result = cfnresponse.SUCCESS       
            
        elif event["RequestType"] == "Update":
            logger.info(
                "In Update "
            ) 
            result = cfnresponse.SUCCESS

        elif event["RequestType"] == "Delete":
            logger.info(
                "In Delete "
            ) 

            #delete topic rule
            response = iot_client.delete_topic_rule(
                ruleName='IoTCoreAccelRule'
            )

            #delete detector
            response = iote_client.delete_detector_model(
                detectorModelName='IoTCoreAccelDetectorModel'
            )
            
            #delete input
            response = iote_client.delete_input(
                inputName='IoTCoreAccelInput'
            )            
            
            result = cfnresponse.SUCCESS   

    except ClientError as e:
        logger.error("Error: {}".format(e))

    logger.info(
        "Returning response of: "
    )

    sys.stdout.flush()
    cfnresponse.send(event, context, result, responseData)