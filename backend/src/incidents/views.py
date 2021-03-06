from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import (
    BrowsableAPIRenderer,
    JSONRenderer,
    HTMLFormRenderer,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django.db.models import Q

from .models import Incident, StatusType, SeverityType, ReopenWorkflow as Reopened, \
    CannedResponse, IncidentType, Reporter
from django.contrib.auth.models import Group, Permission
from .serializers import (
    IncidentSerializer,
    ReporterSerializer,
    RecipientSerializer,
    IncidentCommentSerializer,
    IncidentPoliceReportSerializer,
    CannedResponseSerializer,
)
from .services import (
    generate_refId,
    get_incident_by_id,
    create_incident_postscript,
    update_incident_postscript,
    update_incident_status,
    get_reporter_by_id,
    get_recipient_by_id,
    get_comments_by_incident,
    create_incident_comment_postscript,
    # incident_auto_assign,
    incident_escalate,
    incident_change_assignee,
    incident_close,
    incident_escalate_external_action,
    incident_complete_external_action,
    incident_request_information,
    incident_provide_information,
    incident_verify,
    incident_invalidate,
    incident_reopen,
    get_user_by_id,
    get_police_report_by_incident,
    get_incidents_to_escalate,
    auto_escalate_incidents,
    attach_media,
    get_fitlered_incidents_report,
    get_guest_user,
    get_incident_by_reporter_unique_id,
    user_level_has_permission,
    find_incident_assignee,
    find_escalation_candidate,
    create_reporter,
    validateRecaptcha,
    send_incident_created_mail_sms,
    get_incident_status_guest,
    send_canned_response,
    get_incident_status_guest,
    get_incident_list_by_organization_code
)

from ..events import services as event_service
from ..file_upload import services as file_services
from .exceptions import IncidentException
from ..renderer import CustomJSONRenderer
from rest_framework.renderers import JSONRenderer

import json
from datetime import datetime, timedelta

from ..custom_auth.models import UserLevel
from ..custom_auth.services import user_can
from .permissions import *
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class IncidentResultsSetPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "pageSize"
    max_page_size = 100


class IncidentList(APIView, IncidentResultsSetPagination):
    # authentication_classes = (JSONWebTokenAuthentication, )
    # permission_classes = (IsAuthenticated,)

    serializer_class = IncidentSerializer

    def get_paginated_response(self, data):
        return Response(
            dict(
                [
                    ("count", self.page.paginator.count),
                    ("pages", self.page.paginator.num_pages),
                    ("pageNumber", self.page.number),
                    ("incidents", data),
                ]
            )
        )

    def get(self, request, format=None):
        # #debug
        # _user = get_guest_user()
        # _user = User.objects.get(username="police1")
        # print("assigneee", find_incident_assignee(_user))

        # following was set default on one election
        # election_code = settings.ELECTION
        # incidents = Incident.objects.all().filter(election=election_code).order_by('created_date').reverse()

        incidents = Incident.objects.all().order_by('due_date')
        user = request.user

        # for external entities, they can only view related incidents
        if not user_can(user, CAN_REVIEW_ALL_INCIDENTS):
            incidents = incidents.filter(linked_individuals__id=user.id)

        # filtering
        param_query = self.request.query_params.get('q', None)
        if param_query is not None and param_query != "":
            incidents = incidents.filter(
                Q(refId__icontains=param_query) | Q(title__icontains=param_query) |
                Q(description__icontains=param_query))

        # filter by title
        param_title = self.request.query_params.get('title', None)
        if param_title is not None:
            incidents = incidents.filter(title__contains=param_title)

        # filter by language
        param_language = self.request.query_params.get('language', None)
        if param_language is not None:
            incidents = incidents.filter(language=param_language)

        # filter by channel
        param_info_channel = self.request.query_params.get('channel', None)
        if param_info_channel is not None:
            incidents = incidents.filter(infoChannel=param_info_channel)

        # filter by city
        param_city = self.request.query_params.get('city', None)
        if param_city is not None:
            incidents = incidents.filter(city__contains=param_city)

        param_incident_type = self.request.query_params.get('incident_type', None)
        if param_incident_type is not None:
            incidents = incidents.filter(incidentType=param_incident_type)

        param_category = self.request.query_params.get('category', None)
        if param_category is not None:
            incidents = incidents.filter(category=param_category)

        param_response_time = self.request.query_params.get('response_time', None)
        if param_response_time is not None:
            incidents = incidents.filter(response_time__lte=int(param_response_time))

        param_start_date = self.request.query_params.get('start_date', None)
        param_end_date = self.request.query_params.get('end_date', None)

        if param_start_date and param_end_date:
            incidents = incidents.filter(
                created_date__range=(param_start_date, param_end_date))

        param_assignee = self.request.query_params.get('assignee', None)
        if param_assignee is not None:
            if param_assignee == "me":
                # get incidents of the current user
                incidents = incidents.filter(assignee=user)

        param_linked = self.request.query_params.get('user_linked', None)
        if param_linked is not None:
            if param_linked == "me":
                # get incidents of the current user
                incidents = incidents.filter(linked_individuals__id=user.id)

        param_status = self.request.query_params.get('status', None)
        if param_status is not None:
            try:
                status_type = StatusType[param_status]
                incidents = incidents.filter(current_status=param_status)
            except Exception as e:
                return Response("Invalid status", status=status.HTTP_400_BAD_REQUEST)

        param_severity = self.request.query_params.get('severity', None)
        if param_severity is not None:
            try:
                incidents = incidents.filter(current_severity=param_severity)
            except Exception as e:
                raise IncidentException(e)

        param_closed = self.request.query_params.get('show_closed', None)
        if param_closed is not None and param_closed == "true":
            # by default CLOSED incidents are not shown, and also INVALIDATED.
            incidents = incidents.filter(Q(current_status=StatusType.CLOSED.name) | Q(current_status=StatusType.INVALIDATED.name))
        else:
            incidents = incidents.exclude(current_status=StatusType.CLOSED.name).exclude(current_status=StatusType.INVALIDATED.name)

        param_institution = self.request.query_params.get('institution', None)
        if param_institution is not None:
            incidents = incidents.filter(institution=param_institution)

        param_district = self.request.query_params.get('district', None)
        if param_district is not None:
            incidents = incidents.filter(district=param_district)

        param_export = self.request.query_params.get('export', None)
        if param_export is not None:
            # export path will send a different response
            return get_fitlered_incidents_report(incidents, param_export)

        # organization filter shoulb de the last filter as it only returns generic list.
        # not a Incident object list.

        # filter by organization
        param_organization = self.request.query_params.get('organization', None)
        if param_organization is not None:
            incidents = get_incident_list_by_organization_code(param_organization)

        results = self.paginate_queryset(incidents, request, view=self)
        serializer = IncidentSerializer(results, many=True)
        all_results = list(serializer.data)
        for result in all_results:
            reporter = Reporter.objects.get(id=result["reporter"])
            result["reporterTitle"] = reporter.title
            result["reporterName"] = reporter.name
        return self.get_paginated_response(serializer.data)

    def post(self, request, format=None):
        incident_data = request.data
        if request.data["showRecipient"] == "YES":
            # collect recipient information
            recipient_data = {}
            recipient_data["title"] = incident_data["recipientTitle"]
            recipient_data["nic"] = incident_data["recipientNic"]
            recipient_data["name"] = incident_data["recipientName"]
            recipient_data["address"] = incident_data["recipientAddress"]
            recipient_data["mobile"] = incident_data["recipientMobile"]
            recipient_data["telephone"] = incident_data["recipientTelephone"]
            recipient_data["email"] = incident_data["recipientEmail"]
            recipient_data["city"] = incident_data["recipientCity"]
            recipient_data["district"] = incident_data["recipientDistrict"]
            recipient_data["gnDivision"] = incident_data["recipientGramaNiladhari"]
            # recipient_data["location"] = incident_data["recipientLocation"]
            # create recipient
            recipient_serializer = RecipientSerializer(data=recipient_data)
            if recipient_serializer.is_valid():
                recipient = recipient_serializer.save()
                # linking recipient with the incident to be created
                incident_data["recipient"] = recipient.id

        incident_data["refId"] = generate_refId(request.user)
        incident_data["dueDate"] = (datetime.now()+timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        serializer = IncidentSerializer(data=incident_data)

        if serializer.is_valid() == False:
            print("errors: ", serializer.errors)

        if serializer.is_valid():
            incident = serializer.save()

            incident_police_report_data = request.data
            incident_police_report_data["incident"] = serializer.data["id"]
            incident_police_report_serializer = IncidentPoliceReportSerializer(data=incident_police_report_data)
            return_data = serializer.data

            if incident_police_report_serializer.is_valid():
                incident_police_report = incident_police_report_serializer.save()
                return_data = incident_police_report_serializer.data
                return_data.update(incident_police_report_serializer.data)
                # return_data["id"] = serializer.data["id"]

            incident_data = IncidentSerializer(create_incident_postscript(incident, request.user)).data
            return_data.update(incident_data)

            return Response(return_data, status=status.HTTP_201_CREATED)

        raise IncidentException(serializer.errors)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SMSIncident(APIView):

    serializer_class = IncidentSerializer

    def post(self, request, format=None):

        sms_incident_data = request.data
        telephone = request.data.get("telephone", "No Telephone Number")
        sms_incident_data["title"] = "SMS by " + telephone
        sms_incident_data["infoChannel"] = "SMS"
        serializer = IncidentSerializer(data=sms_incident_data)

        if serializer.is_valid():
            incident = serializer.save()
            reporter = create_reporter()
            reporter.telephone = telephone
            reporter.save()
            incident.reporter = reporter
            return_data = serializer.data

            incident_data = IncidentSerializer(create_incident_postscript(incident, request.user)).data
            return_data = incident_data

            return Response(return_data, status=status.HTTP_201_CREATED)

        raise IncidentException(serializer.errors)

class IncidentDetail(APIView):
    """
    Retrieve, update or delete a Incident instance
    """
    serializer_class = IncidentSerializer

    def get(self, request, incident_id, format=None):
        """
            Get incident by incident id
        """
        incident = get_incident_by_id(incident_id)

        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        serializer = IncidentSerializer(incident)
        incident_data = serializer.data

        # get the reopen count of the incident
        reopened_incidents = Reopened.objects.filter(incident_id=incident_id)
        incident_data["reopenedCount"] = len(reopened_incidents)

        police_report = get_police_report_by_incident(incident)
        if police_report is not None:
            police_report_data = IncidentPoliceReportSerializer(police_report).data
            for key in police_report_data:
                if key != "id" and key != "incident":
                    incident_data[key] = police_report_data[key]

        return Response(incident_data)

    def put(self, request, incident_id, format=None):
        """
            Update existing incident
        """
        incident = get_incident_by_id(incident_id)
        serializer = IncidentSerializer(incident, data=request.data)
        incident_police_report = get_police_report_by_incident(incident)

        if serializer.is_valid():
            # store the revision
            revision_serializer = IncidentSerializer(incident)
            json_renderer = JSONRenderer()
            revision = json_renderer.render(revision_serializer.data)

            serializer.save()
            return_data = serializer.data

            if incident_police_report is not None:
                incident_police_report_data = request.data
                incident_police_report_data["incident"] = incident_id
                incident_police_report_serializer = IncidentPoliceReportSerializer(incident_police_report, data=incident_police_report_data)

                if incident_police_report_serializer.is_valid():
                    incident_police_report_serializer.save()
                    return_data.update(incident_police_report_serializer.data)
                    return_data["id"] = incident_id

            update_incident_postscript(incident, request.user, revision)

            return Response(return_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReporterDetail(APIView):
    serializer_class = ReporterSerializer

    def get(self, request, reporter_id, format=None):
        reporter = get_reporter_by_id(reporter_id)

        if reporter is None:
            return Response("Invalid reporter id", status=status.HTTP_404_NOT_FOUND)

        serializer = ReporterSerializer(reporter)
        return Response(serializer.data)

    def put(self, request, reporter_id, format=None):
        snippet = get_reporter_by_id(reporter_id)
        serializer = ReporterSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            # send the incident created email and sms once the reporter details are saved
            send_incident_created_mail_sms(reporter_id)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecipientList(APIView):
    serializer_class = RecipientSerializer

    def post(self, request, format=None):
        serializer = RecipientSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUESET)

class RecipientDetail(APIView):
    serializer_class = RecipientSerializer

    def get(self, request, recipient_id, format=None):
        recipient = get_recipient_by_id(recipient_id)

        if recipient is None:
            return Response("Invalid recipient id", status=status.HTTP_404_NOT_FOUND)

        serializer = RecipientSerializer(recipient)
        return Response(serializer.data)

    def put(self, request, recipient_id, format=None):
        snippet = get_recipient_by_id(recipient_id)
        serializer = RecipientSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentCommentView(APIView):
    serializer_class = IncidentCommentSerializer

    def get(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        comments = get_comments_by_incident(incident)
        serializer = IncidentCommentSerializer(comments)
        return Response(serializer.data)

    def post(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        comment_data = request.data
        serializer = IncidentCommentSerializer(data=comment_data)
        if serializer.is_valid():
            comment = serializer.save(incident=incident)
            create_incident_comment_postscript(incident, request.user, comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentWorkflowView(APIView):
    def post(self, request, incident_id, workflow, format=None):

        incident = get_incident_by_id(incident_id)

        if workflow == "close":
            if not user_can(request.user, CAN_CLOSE_INCIDENT):
                return Response("User can't close incident", status=status.HTTP_401_UNAUTHORIZED)

            details = request.data['details']
            incident_close(request.user, incident, details)

        elif workflow == "request-action":
            if not user_can(request.user, CAN_ESCALATE_EXTERNAL):
                return Response("User can't refer incident to external organization", status=status.HTTP_401_UNAUTHORIZED)

            entity = request.data['entity']
            comment = request.data['comment']
            incident_escalate_external_action(request.user, incident, entity, comment)

        elif workflow == "complete-action":
            comment = request.data['comment']
            start_event_id = request.data['start_event']
            start_event = event_service.get_event_by_id(start_event_id)
            incident_complete_external_action(
                request.user, incident, comment, start_event)

        elif workflow == "request-information":
            comment = request.data['comment']
            # assignee_id = request.data['assignee']
            # assignee = get_user_by_id(assignee_id)
            incident_request_information(request.user, incident, comment)

        elif workflow == "provide-information":
            comment = request.data['comment']
            start_event_id = request.data['start_event']
            start_event = event_service.get_event_by_id(start_event_id)
            incident_provide_information(request.user, incident, comment, start_event)

        elif workflow == "verify":
            if not user_can(request.user, CAN_VERIFY_INCIDENT):
                return Response("User can't verify incident", status=status.HTTP_401_UNAUTHORIZED)

            comment = request.data['comment']
            proof = request.data['proof']
            incident_verify(request.user, incident, comment, proof)
            # incident_escalate(request.user, incident, comment=comment)

        elif workflow == "invalidate":
            if not user_can(request.user, CAN_INVALIDATE_INCIDENT):
                return Response("User can't invalidate incident", status=status.HTTP_401_UNAUTHORIZED)

            comment = request.data['comment']
            incident_invalidate(request.user, incident, comment)

        elif workflow == "assign":
            if not user_can(request.user, CAN_CHANGE_ASSIGNEE):
                return Response("User can't change assignee", status=status.HTTP_401_UNAUTHORIZED)

            assignee_id = self.request.data['assignee']
            assignee = get_user_by_id(assignee_id)

            incident_change_assignee(request.user, incident, assignee)

        elif workflow == "escalate":
            if not user_can(request.user, CAN_ESCALATE_INCIDENT):
                return Response("User can't escalate incident", status=status.HTTP_401_UNAUTHORIZED)

            comment = request.data['comment']
            response_time = request.data['responseTime']
            incident_escalate(request.user, incident, comment=comment, response_time=response_time)

        elif workflow == "reopen":
            if not user_can(request.user, CAN_REOPEN_INCIDENT):
                return Response("User can't reopen incident", status=status.HTTP_401_UNAUTHORIZED)

            comment = request.data['comment']
            incident_reopen(request.user, incident, comment)
        elif workflow == "send_canned_response":
            response_id = request.data['id']
            send_canned_response(request.user, incident, response_id)

        else:
            return Response("Invalid workflow", status=status.HTTP_400_BAD_REQUEST)

        return Response("Incident workflow success", status=status.HTTP_200_OK)

class IncidentMediaView(APIView):
    def post(self, request, incident_id, format=None):

        incident = get_incident_by_id(incident_id)
        file_id_set = request.data['file_id_set']

        for file_id in file_id_set:
            attach_media(request.user, incident, file_services.get_file_by_id(file_id))

        return Response("Incident workflow success", status=status.HTTP_200_OK)

# NO AUTO ESCALATE FOR NOW
class IncidentAutoEscalate(APIView):
    def get(self, request):
        pass
        # escalated_incidents = auto_escalate_incidents()

        # return Response(escalated_incidents, status=status.HTTP_200_OK)

class Test(APIView):
    def get(self, request):
        data = get_incidents_to_escalate()

        return Response(data)

class CannedResponseList(APIView):

    def get(self, request, format=None):
        """
        Return a list of all canned responses.
        """
        canned_responses = CannedResponse.objects.all()
        serializer = CannedResponseSerializer(canned_responses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK )


# public user views
# todo
# check guest user here
class IncidentPublicUserView(APIView):
    permission_classes = []
    serializer_class = IncidentSerializer

    def get(self, request, format=None):
        param_refId = self.request.query_params.get('refId', None)
        if (param_refId):
            return_data = get_incident_status_guest(param_refId)
            return Response(return_data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        incident_data = request.data
        if request.data["showRecipient"] == "YES":
            # collect recipient information
            recipient_data = {}
            recipient_data["title"] = incident_data["recipientTitle"]
            recipient_data["nic"] = incident_data["recipientNic"]
            recipient_data["name"] = incident_data["recipientName"]
            recipient_data["address"] = incident_data["recipientAddress"]
            recipient_data["mobile"] = incident_data["recipientMobile"]
            recipient_data["telephone"] = incident_data["recipientTelephone"]
            recipient_data["email"] = incident_data["recipientEmail"]
            recipient_data["city"] = incident_data["recipientCity"]
            recipient_data["district"] = incident_data["recipientDistrict"]
            # recipient_data["gnDivision"] = incident_data["recipientGramaNiladhari"]
            # recipient_data["location"] = incident_data["recipientLocation"]
            # create recipient
            recipient_serializer = RecipientSerializer(data=recipient_data)
            if recipient_serializer.is_valid():
                recipient = recipient_serializer.save()
                # linking recipient with the incident to be created
                incident_data["recipient"] = recipient.id

        incident_data["refId"] = generate_refId("GUEST")
        serializer = IncidentSerializer(data=incident_data)

        if serializer.is_valid():
            incidentReqValues = serializer.initial_data
            if(validateRecaptcha(incidentReqValues['recaptcha'])):
                incident = serializer.save()
                create_incident_postscript(incident, None)
                return_data = serializer.data

                return Response(return_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def put(self, request, incident_id, format=None):
    #     """
    #         Update existing incident
    #     """
    #     incident = get_incident_by_id(incident_id)
    #     serializer = IncidentSerializer(incident, data=request.data)

    #     if serializer.is_valid():
    #         serializer.save()
    #         return_data = serializer.data

    #         return Response(return_data)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReporterPublicUserView(APIView):
    serializer_class = ReporterSerializer
    permission_classes = []

    def put(self, request, reporter_id, format=None):
        snippet = get_reporter_by_id(reporter_id)
        serializer = ReporterSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()

            # send notifications once reporter is updated
            # reason: this is the last function call on creation of incident
            send_incident_created_mail_sms(reporter_id)

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IncidentMediaPublicUserView(APIView):
    permission_classes = []

    def post(self, request, incident_id, format=None):

        incident = get_incident_by_id(incident_id)
        file_id_set = request.data['file_id_set']

        for file_id in file_id_set:
            attach_media(get_guest_user(), incident, file_services.get_file_by_id(file_id))

        return Response("Incident workflow success", status=status.HTTP_200_OK)

class IncidentViewPublicUserView(APIView):
    permission_classes = []

    def post(self, request):
        # enter the unique code and retrieve the corresponding incident
        # send the incident back
        # get incident for public user
        unique_id = request.data['unique_id']
        incident = get_incident_by_reporter_unique_id(unique_id)
        serializer = IncidentSerializer(incident)
        return Response(serializer.data, status=status.HTTP_200_OK)

class IncidentWorkflowPublicView(APIView):
    permission_classes = []

    def post(self, request, incident_id, workflow, format=None):
        incident = get_incident_by_id(incident_id)

        if workflow == "provide-information":
            comment = request.data['comment']
            start_event_id = request.data['start_event']
            start_event = event_service.get_event_by_id(start_event_id)
            user = get_guest_user()
            incident_provide_information(user, incident, comment, start_event)

        else:
            return Response("Invalid workflow", status=status.HTTP_400_BAD_REQUEST)

        return Response("Incident workflow success", status=status.HTTP_200_OK)
