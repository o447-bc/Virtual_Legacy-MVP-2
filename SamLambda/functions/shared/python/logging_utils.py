"""
Structured Logging Utilities

Provides consistent JSON-formatted logging across all Lambda functions
for audit trail, debugging, and monitoring purposes.

Requirements: 3.5, 4.5, 12.5, 12.7
"""
import json
import logging
from datetime import datetime
from datetime import timezone
from typing import Dict, Any, Optional


# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted log entries.
    
    All log entries include:
    - timestamp: ISO 8601 timestamp in UTC
    - level: Log level (INFO, WARNING, ERROR)
    - event_type: Type of event being logged
    - Additional context-specific fields
    """
    
    @staticmethod
    def _log(level: str, event_type: str, data: Dict[str, Any]):
        """
        Internal method to format and output log entry.
        
        Args:
            level: Log level (INFO, WARNING, ERROR)
            event_type: Type of event
            data: Additional data to include in log entry
        """
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'event_type': event_type,
            **data
        }
        
        log_message = json.dumps(log_entry)
        
        if level == 'ERROR':
            logger.error(log_message)
        elif level == 'WARNING':
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    @staticmethod
    def log_assignment_created(
        initiator_id: str,
        related_user_id: str,
        benefactor_email: str,
        is_registered: bool,
        access_conditions: list,
        invitation_sent: bool
    ):
        """
        Log assignment creation event.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'assignment_created', {
            'initiator_id': initiator_id,
            'related_user_id': related_user_id,
            'benefactor_email': benefactor_email,
            'benefactor_registered': is_registered,
            'access_condition_count': len(access_conditions),
            'access_condition_types': [c.get('condition_type') for c in access_conditions],
            'invitation_sent': invitation_sent
        })
    
    @staticmethod
    def log_assignment_status_change(
        initiator_id: str,
        related_user_id: str,
        old_status: str,
        new_status: str,
        changed_by: str,
        reason: Optional[str] = None
    ):
        """
        Log assignment status change event.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'assignment_status_changed', {
            'initiator_id': initiator_id,
            'related_user_id': related_user_id,
            'old_status': old_status,
            'new_status': new_status,
            'changed_by': changed_by,
            'reason': reason
        })
    
    @staticmethod
    def log_assignment_deleted(
        initiator_id: str,
        related_user_id: str,
        deleted_by: str,
        conditions_deleted: int
    ):
        """
        Log assignment deletion event.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'assignment_deleted', {
            'initiator_id': initiator_id,
            'related_user_id': related_user_id,
            'deleted_by': deleted_by,
            'conditions_deleted': conditions_deleted
        })
    
    @staticmethod
    def log_access_validation(
        requesting_user_id: str,
        target_user_id: str,
        has_access: bool,
        reason: str,
        unmet_conditions: Optional[list] = None
    ):
        """
        Log access validation attempt and decision.
        
        Requirements: 12.5, 12.7
        """
        log_data = {
            'requesting_user_id': requesting_user_id,
            'target_user_id': target_user_id,
            'access_granted': has_access,
            'reason': reason
        }
        
        if unmet_conditions:
            log_data['unmet_conditions'] = unmet_conditions
        
        StructuredLogger._log('INFO', 'access_validation', log_data)
    
    @staticmethod
    def log_check_in_sent(
        relationship_key: str,
        condition_id: str,
        user_id: str,
        email: str,
        token: str,
        consecutive_missed: int
    ):
        """
        Log check-in email sent event.
        
        Requirements: 3.5
        """
        StructuredLogger._log('INFO', 'check_in_sent', {
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'user_id': user_id,
            'email': email,
            'token': token,
            'consecutive_missed_check_ins': consecutive_missed
        })
    
    @staticmethod
    def log_check_in_response(
        user_id: str,
        condition_id: str,
        relationship_key: str,
        token: str,
        previous_missed_count: int
    ):
        """
        Log check-in response received event.
        
        Requirements: 3.5
        """
        StructuredLogger._log('INFO', 'check_in_response_received', {
            'user_id': user_id,
            'condition_id': condition_id,
            'relationship_key': relationship_key,
            'token': token,
            'previous_missed_count': previous_missed_count,
            'counter_reset': True
        })
    
    @staticmethod
    def log_condition_activated(
        relationship_key: str,
        condition_id: str,
        condition_type: str,
        activation_trigger: str,
        scheduled_date: Optional[str] = None
    ):
        """
        Log access condition activation event.
        
        Requirements: 12.5
        """
        log_data = {
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'condition_type': condition_type,
            'activation_trigger': activation_trigger
        }
        
        if scheduled_date:
            log_data['scheduled_activation_date'] = scheduled_date
        
        StructuredLogger._log('INFO', 'condition_activated', log_data)
    
    @staticmethod
    def log_manual_release(
        initiator_id: str,
        released_by: str,
        conditions_released: int,
        benefactors_notified: int
    ):
        """
        Log manual release event.
        
        Requirements: 4.5
        """
        StructuredLogger._log('INFO', 'manual_release_triggered', {
            'initiator_id': initiator_id,
            'released_by': released_by,
            'conditions_released': conditions_released,
            'benefactors_notified': benefactors_notified
        })
    
    @staticmethod
    def log_scheduled_job_execution(
        job_name: str,
        items_processed: int,
        items_successful: int,
        items_failed: int,
        errors: list
    ):
        """
        Log scheduled job execution summary.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'scheduled_job_executed', {
            'job_name': job_name,
            'items_processed': items_processed,
            'items_successful': items_successful,
            'items_failed': items_failed,
            'error_count': len(errors),
            'errors': errors[:10]  # Limit to first 10 errors to avoid log bloat
        })
    
    @staticmethod
    def log_invitation_sent(
        initiator_id: str,
        benefactor_email: str,
        invitation_token: str,
        invitation_type: str
    ):
        """
        Log invitation email sent event.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'invitation_sent', {
            'initiator_id': initiator_id,
            'benefactor_email': benefactor_email,
            'invitation_token': invitation_token,
            'invitation_type': invitation_type
        })
    
    @staticmethod
    def log_invitation_accepted(
        initiator_id: str,
        related_user_id: str,
        invitation_token: str,
        new_user_registered: bool
    ):
        """
        Log invitation acceptance event.
        
        Requirements: 12.5
        """
        StructuredLogger._log('INFO', 'invitation_accepted', {
            'initiator_id': initiator_id,
            'related_user_id': related_user_id,
            'invitation_token': invitation_token,
            'new_user_registered': new_user_registered
        })
    
    @staticmethod
    def log_error(
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        stack_trace: Optional[str] = None
    ):
        """
        Log error event with context.
        
        Requirements: 12.5
        """
        log_data = {
            'error_type': error_type,
            'error_message': error_message,
            'context': context
        }
        
        if stack_trace:
            log_data['stack_trace'] = stack_trace
        
        StructuredLogger._log('ERROR', 'error_occurred', log_data)
    
    @staticmethod
    def log_warning(
        warning_type: str,
        warning_message: str,
        context: Dict[str, Any]
    ):
        """
        Log warning event with context.
        
        Requirements: 12.5
        """
        StructuredLogger._log('WARNING', 'warning', {
            'warning_type': warning_type,
            'warning_message': warning_message,
            'context': context
        })
