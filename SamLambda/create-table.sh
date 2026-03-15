#!/bin/bash
aws dynamodb create-table \
    --table-name allQuestionsDB \
    --attribute-definitions \
        AttributeName=id,AttributeType=S \
        AttributeName=questionType,AttributeType=S \
    --key-schema \
        AttributeName=id,KeyType=HASH \
        AttributeName=questionType,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST