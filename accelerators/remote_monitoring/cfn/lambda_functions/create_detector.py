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

            # create iotevents input - This is supported in CFN       
            logger.info("create the iote input")
            resp = iote_client.create_input(
                inputName = 'IoTRmAccelInput',
                inputDescription = 'IoTRmAccelInput',
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

            # create iotevents detector model - This is supported in CFN
            logger.info("Create the detector model for iote")
            response = iote_client.create_detector_model(
                detectorModelName = 'IoTRmAccelDetectorModel',
                detectorModelDefinition = {
                'states': [
                    {
                        "stateName": "NormalState",
                        "onInput": {
                            "events": [
                                {
                                    "eventName": "TimerStart",
                                    "condition": "$variable.inputReceived == 0",                                    
                                    "actions": [
                                        {
                                            "setTimer": {
                                                "timerName": "dataRecevied",
                                                "seconds": 120
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "TimerReset",
                                    "condition": "$variable.inputReceived == 1",                                    
                                    "actions": [
                                        {
                                            "resetTimer": {
                                                "timerName": "dataRecevied"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "InputReceived",
                                    "condition": "true",                                    
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "inputReceived",
                                                "value": "1"
                                            }
                                        }
                                    ]
                                },
                                {
                                    "eventName": "ErrorDataOnNormal",
                                    "condition": "$input.IoTRmAccelInput.deviceData > 1023",                                   
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
                                    "eventName": "GoodDataOnNormal",
                                    "condition": "$input.IoTRmAccelInput.deviceData <= 1023",                                    
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
                                    "condition": "$variable.errorEvent > 4 || timeout('dataRecevied')",                                    
                                    "actions": [],
                                    "nextState": "ErrorState"
                                }
                            ]
                        },
                        "onEnter": {
                            "events": [
                                {
                                    "eventName": "initializeErrorEvent",
                                    "condition": "true",
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
                                    "eventName": "initializeInputReceived",
                                    "condition": "true",
                                    "actions": [
                                        {
                                            "setVariable": {
                                                "variableName": "inputReceived",
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
                    },
                    {
                        "stateName": "ErrorState",
                        "onInput": {
                            "transitionEvents": [
                                {
                                    "eventName": "NormalTransition",
                                    "condition": "$variable.errorEvent == 0 && timeout('snsSent')",                                       
                                    "actions": [
                                        {
                                            "resetTimer": {
                                                "timerName": "dataRecevied"
                                            }
                                        }                                          
                                    ],
                                    "nextState": "NormalState"
                                }
                            ],
                            "events": [
                                {
                                    "eventName": "DataOnError",
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
                        "onEnter": {
                            "events": [
                                {
                                    "eventName": "SendSNSonEnterError",
                                    "condition": "true",                                    
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
                                        },
                                        {
                                            "setTimer": {
                                                "timerName": "snsSent",
                                                "seconds": 120
                                            }
                                        }                                                                                                                
                                    ]
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
                detectorModelDescription = 'Detector Model for IoT RM Accel',
                key = 'deviceID',
                roleArn = event['ResourceProperties']['IoTEventRoleArn']
            )

            #update rule action with iote input - This is not supported in CFN and hence this Lambda function
            logger.info('update rule action with iote input')
            response = iot_client.create_topic_rule(
                ruleName='IoTRmAccelRule',
                topicRulePayload={
                    'sql': "select * from 'remote_monitoring'",
                    'description': 'Routes IoTRmAccel data for processing.',
                    'actions': [
                        {
                            'iotEvents': {
                                'inputName': 'IoTRmAccelInput',
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
                ruleName='IoTRmAccelRule'
            )

            #delete detector
            response = iote_client.delete_detector_model(
                detectorModelName='IoTRmAccelDetectorModel'
            )
            
            #delete input
            response = iote_client.delete_input(
                inputName='IoTRmAccelInput'
            )            
            
            result = cfnresponse.SUCCESS   

    except ClientError as e:
        logger.error("Error: {}".format(e))

    logger.info(
        "Returning response of: "
    )

    sys.stdout.flush()
    cfnresponse.send(event, context, result, responseData)