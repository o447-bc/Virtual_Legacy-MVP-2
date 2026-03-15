"""
Smoke tests — verify every Lambda handler can be imported without errors.
Catches missing imports, syntax errors, and bad module-level code before deploy.

Run locally:
    cd SamLambda
    pip install pytest
    pytest tests/test_imports.py -v
"""
import sys
import os

# Add SamLambda root and shared layer path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'functions', 'shared', 'python'))

import importlib
import pytest

HANDLERS = [
    'functions.assignmentFunctions.acceptDeclineAssignment.app',
    'functions.assignmentFunctions.checkInResponse.app',
    'functions.assignmentFunctions.createAssignment.app',
    'functions.assignmentFunctions.getAssignments.app',
    'functions.assignmentFunctions.manualRelease.app',
    'functions.assignmentFunctions.resendInvitation.app',
    'functions.assignmentFunctions.updateAssignment.app',
    'functions.cognitoTriggers.postConfirmation.app',
    'functions.cognitoTriggers.preSignup.app',
    'functions.conversationFunctions.wsAuthorizer.app',
    'functions.conversationFunctions.wsConnect.app',
    'functions.conversationFunctions.wsDefault.app',
    'functions.conversationFunctions.wsDisconnect.app',
    'functions.inviteFunctions.sendInviteEmail.app',
    'functions.questionDbFunctions.getAudioQuestionSummaryForVideoRecording.app',
    'functions.questionDbFunctions.getNumQuestionTypes.app',
    'functions.questionDbFunctions.getNumValidQuestionsForQType.app',
    'functions.questionDbFunctions.getProgressSummary2.app',
    'functions.questionDbFunctions.getQuestionById.app',
    'functions.questionDbFunctions.getQuestionTypeData.app',
    'functions.questionDbFunctions.getQuestionTypes.app',
    'functions.questionDbFunctions.getTotalValidAllQuestions.app',
    'functions.questionDbFunctions.getUnansweredQuestionsFromUser.app',
    'functions.questionDbFunctions.getUnansweredQuestionsWithText.app',
    'functions.questionDbFunctions.getUserCompletedQuestionCount.app',
    'functions.questionDbFunctions.incrementUserLevel2.app',
    'functions.questionDbFunctions.initializeUserProgress.app',
    'functions.questionDbFunctions.invalidateTotalValidQuestionsCache.app',
    'functions.relationshipFunctions.createRelationship.app',
    'functions.relationshipFunctions.getRelationships.app',
    'functions.relationshipFunctions.validateAccess.app',
    'functions.scheduledJobs.checkInSender.app',
    'functions.scheduledJobs.inactivityProcessor.app',
    'functions.scheduledJobs.timeDelayProcessor.app',
    'functions.streakFunctions.checkStreak.app',
    'functions.streakFunctions.getStreak.app',
    'functions.streakFunctions.monthlyReset.app',
    'functions.videoFunctions.getMakerVideos.app',
    'functions.videoFunctions.getUploadUrl.app',
    'functions.videoFunctions.processTranscript.app',
    'functions.videoFunctions.processVideo.app',
    'functions.videoFunctions.startTranscription.app',
    'functions.videoFunctions.summarizeTranscript.app',
    'functions.videoFunctions.uploadVideoResponse.app',
]


@pytest.mark.parametrize('module_path', HANDLERS)
def test_handler_imports(module_path):
    """Each Lambda handler must be importable without errors."""
    importlib.import_module(module_path)
