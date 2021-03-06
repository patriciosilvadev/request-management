from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django_filters import rest_framework as filters
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import enum
from datetime import datetime, timedelta
from .permissions import *
from ..common.models import Category
from django.conf import settings

User = settings.AUTH_USER_MODEL

class LanguageType(enum.Enum):
    SINHALA = "Sinhala"
    TAMIL = "Tamil"
    ENGLISH = "English"

    def __str__(self):
        return self.name

class Occurrence(enum.Enum):
    OCCURRED = "Occurred"
    OCCURRING = "Occurring"
    WILL_OCCUR = "Will Occur"

    def __str__(self):
        return self.name


class StatusType(enum.Enum):
    NEW = "New"
    CLOSED = "Closed"
    ACTION_TAKEN = "Action Taken"
    ACTION_PENDING = "Action Pending"
    INFORMATION_PROVIDED = "Information Provided"
    INFORMATION_REQUESTED = "Information Requested"
    VERIFIED = "Verified"
    INVALIDATED = "Invalidated"
    REOPENED = "Reopened"

    def __str__(self):
        return self.name


class SeverityType(enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    def __str__(self):
        return self.name

class IncidentType(enum.Enum):
    INQUIRY = "Inquiry"
    COMPLAINT = "Complaint"

    def __str__(self):
        return self.name

class ReportedThrough(enum.Enum):
    GUEST = "Guest"
    ELECTION_COMMISION = "Election Commision"
    POLICE = "Police"
    OTHER = "Other"

    def __str__(self):
        return self.name

class ContactType(enum.Enum):
    INDIVIDUAL = "Individual"
    ORGANIZATION = "Organization"

    def __str__(self):
        return self.name

class ContactTitle(enum.Enum):
    MR = "Mr"
    MRS = "Mrs"
    MS = "Ms"
    MISS = "Miss"
    DR = "Dr"
    PROFESSOR = "Professor"

    def __str__(self):
        return self.name

class Reporter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=10,
        choices=[(tag.name, tag.value) for tag in ContactTitle],
        blank=True,
        null=True
    )
    nic = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    sn_name = models.CharField(max_length=200, null=True, blank=True)
    tm_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.CharField(max_length=200, null=True, blank=True)
    telephone = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)

    location = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    gn_division = models.CharField(max_length=50, null=True, blank=True)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)

class Recipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=10,
        choices=[(tag.name, tag.value) for tag in ContactTitle],
        blank=True,
        null=True
    )
    nic = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    sn_name = models.CharField(max_length=200, null=True, blank=True)
    tm_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.CharField(max_length=200, null=True, blank=True)
    telephone = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)

    location = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    gn_division = models.CharField(max_length=50, null=True, blank=True)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)

class IncidentStatus(models.Model):
    previous_status = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in StatusType],
        blank=True,
        null=True,
    )
    current_status = models.CharField(
        max_length=50, choices=[(tag.name, tag.value) for tag in StatusType]
    )
    incident = models.ForeignKey("Incident", on_delete=models.DO_NOTHING)
    approved = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)


class IncidentComment(models.Model):
    body = models.TextField(max_length=200)
    incident = models.ForeignKey("Incident", on_delete=models.DO_NOTHING)
    is_active = models.BooleanField(default=True)
    is_outcome = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, blank=True)
    sn_body = models.CharField(max_length=200, blank=True)
    tm_body = models.CharField(max_length=200, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)


class Incident(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refId = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=200, blank=True, null=True)
    language = models.CharField(
        max_length=10,
        choices=[(tag.name, tag.value) for tag in LanguageType],
        default=LanguageType.ENGLISH
    )

    # the occurrence flag of the incident - check enums for more details
    occurrence = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in Occurrence],
        null=True,
        blank=True,
    )
    incidentType = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in IncidentType],
        default=IncidentType.COMPLAINT,
    )

    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, null=True, blank=True
    )

    # the medium through which the incident was reported
    infoChannel = models.CharField(max_length=200, null=True, blank=True)

    # the person who reported the incident, not ncessarily the one
    # that entered it to the system
    reporter = models.ForeignKey(
        "Reporter", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    recipient = models.ForeignKey(
        "Recipient", on_delete=models.DO_NOTHING, null=True, blank=True
    )

    # assignee is the current responsible personnel for the current incident from the EC
    assignee = models.ForeignKey(User, related_name='incident_asignees', on_delete=models.DO_NOTHING, null=True, blank=True)
    # All the relavant parties such as police,lawyer,NGO etc.
    linked_individuals =  models.ManyToManyField(User, related_name='incident_linked_individuals', blank=True)

    # location related details
    location = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    coordinates = models.CharField(max_length=200, null=True, blank=True)

    province = models.CharField(max_length=200, blank=True, null=True)
    district = models.CharField(max_length=200, blank=True, null=True)

    ds_division = models.CharField(max_length=200, blank=True, null=True)
    grama_niladhari = models.CharField(max_length=200, blank=True, null=True)

    complainer_consent = models.BooleanField(default=False, null=True, blank=True)
    proof = models.BooleanField(default=False, null=True)

    current_status = models.CharField(max_length=50, default=None, null=True, blank=True)
    current_severity = models.CharField(
        max_length=50,
        choices=[(tag.name, tag.value) for tag in SeverityType],
        default=SeverityType.LOW,
    )

    institution = models.CharField(max_length=200, blank=True, null=True) # this will save `code` of institute pulled from location-service API endpoint

    current_decision = models.CharField(max_length=50, default=None, null=True, blank=True)
    occured_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    response_time = models.IntegerField(default=12)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_date",)

        permissions = (
            (CAN_REVIEW_INCIDENTS, "Can review created incidents"),
            (CAN_REVIEW_OWN_INCIDENTS, "Can review own incidents"),
            (CAN_REVIEW_ALL_INCIDENTS, "Can review all incidents"),

            (CAN_MANAGE_INCIDENT, "Can manage incident"),

            (CAN_RUN_WORKFLOW, "Can run incident workflows"),
            (CAN_CHANGE_ASSIGNEE, "Can change incident assignee"),
            (CAN_VERIFY_INCIDENT, "Can verify incident"),
            (CAN_CLOSE_INCIDENT, "Can close incident"),
            (CAN_ESCALATE_INCIDENT, "Can escalate incident"),
            (CAN_ESCALATE_EXTERNAL, "Can refer incident to external organization"),
            (CAN_INVALIDATE_INCIDENT, "Can invalidate incident"),
            (CAN_REOPEN_INCIDENT, "Can reopen incident"),

            (CAN_ACTION_OVER_CURRENT_ASSIGNEE, "Can action over current assignee"),

            (CAN_VIEW_REPORTS, "Can view inciddent reports"),
        )

# the following signals will update the current status and severity fields
@receiver(post_save, sender=IncidentStatus)
def update_incident_current_status(sender, **kwargs):
    incident_status = kwargs['instance']
    incident = incident_status.incident
    incident.current_status = incident_status.current_status.name
    incident.save()

class IncidentPerson(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)

    # this is essentially a one-to-one mapping to common.PolicalParty
    # for future compatibiliy, it is set to char field
    political_affliation = models.CharField(max_length=200, blank=True, null=True)

class IncidentVehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle_no = models.CharField(max_length=15, null=True, blank=True)
    ownership = models.CharField(max_length=15, null=True, blank=True)

class IncidentPoliceReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey("Incident", on_delete=models.DO_NOTHING)

    nature_of_incident = models.CharField(max_length=200, null=True, blank=True)
    complainers_name = models.CharField(max_length=200, null=True, blank=True)
    complainers_address = models.CharField(max_length=200, null=True, blank=True)
    # complainers political view
    # complainers candidate status
    victims_name = models.CharField(max_length=200, null=True, blank=True)
    victims_address = models.CharField(max_length=200, null=True, blank=True)
    respondents_name = models.CharField(max_length=200, null=True, blank=True)
    respondents_address = models.CharField(max_length=200, null=True, blank=True)
    # Respondents candidate status
    no_of_vehicles_arrested =  models.IntegerField(default=0, null=True, blank=True)
    steps_taken = models.CharField(max_length=200, null=True, blank=True)
    court_case_no = models.CharField(max_length=200, null=True, blank=True)

    injured_parties = models.ManyToManyField(IncidentPerson, related_name='incident_injured_parties', blank=True)
    respondents = models.ManyToManyField(IncidentPerson, related_name='incident_respondents', blank=True)
    detained_vehicles = models.ManyToManyField(IncidentVehicle, related_name='incident_detained_vehicles', blank=True)

    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_date",)

class IncidentWorkflow(models.Model):
    id = models.BigAutoField(primary_key=True)
    incident = models.ForeignKey(Incident,
                    on_delete=models.DO_NOTHING,
                    related_name="%(app_label)s_%(class)s_related",
                    related_query_name="%(app_label)s_%(class)ss")
    actioned_user = models.ForeignKey(User,
                    on_delete=models.DO_NOTHING,
                    related_name="%(app_label)s_%(class)s_related",
                    related_query_name="%(app_label)s_%(class)ss")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class VerifyWorkflow(IncidentWorkflow):
    comment = models.TextField()
    has_proof = models.BooleanField(default=False)

class EscalateExternalWorkflow(IncidentWorkflow):
    is_internal_user = models.BooleanField(default=False, null=False)
    comment = models.TextField()
    escalated_user = models.ForeignKey(User,
                    on_delete=models.DO_NOTHING,
                    null=True,
                    blank=True,
                    related_name="escalation_related",
                    related_query_name="escalated_users")
    escalated_user_other = models.CharField(max_length=200, null=True, blank=True)
    escalated_entity_other = models.CharField(max_length=200, null=True, blank=True)
    is_action_completed = models.BooleanField(default=False)

class CompleteActionWorkflow(IncidentWorkflow):
    initiated_workflow = models.ForeignKey(EscalateExternalWorkflow, on_delete=models.DO_NOTHING)
    comment = models.TextField()

class RequestInformationWorkflow(IncidentWorkflow):
    comment = models.TextField()
    is_information_provided = models.BooleanField(default=False)

class ProvideInformationWorkflow(IncidentWorkflow):
    initiated_workflow = models.ForeignKey(RequestInformationWorkflow, on_delete=models.DO_NOTHING)
    comment = models.TextField()

class AssignUserWorkflow(IncidentWorkflow):
    assignee = models.ForeignKey(User,
                    on_delete=models.DO_NOTHING,
                    related_name="assignee_related",
                    related_query_name="assigned_users")

class EscalateWorkflow(IncidentWorkflow):
    assignee = models.ForeignKey(User,
                    on_delete=models.DO_NOTHING,
                    related_name="escalation_assignee_related",
                    related_query_name="escalation_assigned_users")
    comment = models.TextField()
    response_time = models.CharField(max_length=200, null=True, blank=True)

class CloseWorkflow(IncidentWorkflow):
    assignees = models.TextField()
    entities = models.TextField()
    departments = models.TextField()
    individuals = models.TextField()
    comment = models.TextField()

class InvalidateWorkflow(IncidentWorkflow):
    comment = models.TextField()
    response_time = models.CharField(max_length=200, null=True, blank=True)

class ReopenWorkflow(IncidentWorkflow):
    comment = models.TextField()

class IncidentFilter(filters.FilterSet):
    current_status = filters.ChoiceFilter(choices=StatusType, method='my_custom_filter')

    class Meta:
        model = Incident
        fields = ["current_status"]

    def my_custom_filter(self, queryset, name, value):
        print(queryset, name, value)


class CannedResponse(models.Model):
    title = models.CharField(max_length=30)
    message =  models.CharField(max_length=200)

    def __str__(self):
        return self.message

class SendCannedResponseWorkflow(IncidentWorkflow):
    canned_response = models.ForeignKey(CannedResponse,
                    on_delete=models.DO_NOTHING)



