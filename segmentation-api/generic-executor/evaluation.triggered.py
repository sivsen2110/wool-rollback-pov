import os
import requests
import json
import time
from datetime import datetime, timedelta
import html
import uuid

#print('running')
#exit()

#
# Usage
# Mandatory Labels
# DTEnv and Dashboard (case sensitive)
#
# keptn trigger evaluation ^
# --project=PROJECTNAME ^
# --service=service1 ^
# --stage=stage1 ^
# --timeframe=24h ^
# --labels=RunBy=Adam,Please=Ignore,DTEnv=https://abc12345.live.dynatrace.com,Dashboard=12345678-abcd-1234-abcd-1234abcd1234

#print(os.environ)
#exit()

# CONFIGURABLE PARAMETERS START
# Set this to False if you're testing and only want output to Keptn
# Set this to True if you're ready to send Payloads to third party systems
PROD_MODE = True

# DEBUG mode enables extra logging
DEBUG = False

# Cloud Automation runs in UTC
# So times come in as UTC
# Therefore shift into our timezone but moving time FORWARD by X hours
# eg. time comes in as 01:00:00, TIME_SHIFT_HOURS = 10 would output a time of 11:00:00
TIME_SHIFT_HOURS = 10

# CONFIGURABLE PARAMETERS END
# DO NOT MODIFY ANYTHING BELOW THIS LINE UNLESS DEVELOPING THE SCRIPT

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def waitForEvent(eventType, keptnContext):

    loopCount = 1
    
    keptn_headers = {
                "x-token": KEPTN_TOKEN,
                "Content-Type": "application/json"
              }

    # For safety, wait a max of 30s for the finished event
    while loopCount < 30: # Each loop sleeps for 1 second so max waiting time for a workflow is 30s. This isn't right for production use. Note we break out the loop sooner if event is found.
        loopCount += 1;

        # Poll Keptn and wait until the finished event is found then return import

        url = KEPTN_API_URL + '/mongodb-datastore/event/type/' + eventType + '?filter=shkeptncontext:' + keptnContext + '&excludeInvalidated=true&limit=1'
        #print(url)
        keptn_response = requests.get(url, headers=keptn_headers)

        #print('----------------')
        #print(keptn_response)
        #print('----------------')
        keptn_response_json = keptn_response.json()
        if DEBUG:
            print(keptn_response_json)
            print('Events Length Received: ' + str(len(keptn_response_json['events'])))

        if "events" in keptn_response_json and len(keptn_response_json['events']) > 0:
          print(f'Found a corresponding finished event for Keptn Context {keptnContext}. Returning now.')
	  # An array of events containing 1 item so this hardcoded lookup it OK
          # An array of 1 is always returned because in waitForEvent, we wait for a specific keptnContext whcih will always be unique
          return keptn_response_json['events'][0]
        else:
            time.sleep(1)

    # If we got here, we timedout waiting for the Keptn finished event
    print("Timed out waiting for finished event. We waited for: " + str(loopCount) + " seconds.")
    return

KEPTN_BRIDGE_URL = os.getenv('KEPTN_BRIDGE_URL','')
KEPTN_TOKEN = os.getenv('KEPTN_API_TOKEN','')
KEPTN_API_URL = KEPTN_BRIDGE_URL.replace('/bridge','/api')
KEPTN_CONTEXT = os.getenv('SHKEPTNCONTEXT','')

print("Keptn Context:", KEPTN_CONTEXT)
print("Keptn Bridge URL: ", KEPTN_BRIDGE_URL)
print("Keptn API URL: ", KEPTN_API_URL)

finished_event_json = waitForEvent("sh.keptn.event.evaluation.finished", KEPTN_CONTEXT)
print("Finished waiting for event...")
if finished_event_json == None:
  print('Script timed out. No info to progress further so exiting. Please investigate connection between generic-executor pod and CloudAutomation')
  exit()

# If we have an incoming start / end time they'll come in from the CLI in this format
# Note LoadRunner only sends the timeframe so we need to cater for that eventuality
INCOMING_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z" 
OUTBOUND_TIME_FORMAT = "%d.%m.%Y %H:%M:%S"
DASHBOARD_TIME_FORMAT = f"%Y-%m-%dT%H:%M:%S+{TIME_SHIFT_HOURS}:00" # DT dashboards expect a different timeframe
SLACK_HOOK_URL = os.getenv('SLACK_HOOK_URL','')
# Get this by going to https://admin.atlassian.com
# Click on your site
# Go to billing > your site
# The URL should be: https://admin.atlassian.com/s/{YOUR-SITE-ID}/billing/applications
CONFLUENCE_SITE_ID = os.getenv('CONFLUENCE_SITE_ID','')
#CONFLUENCE_SPACE_ID = os.getenv('CONFLUENCE_SPACE_ID','')
CONFLUENCE_SPACE_ID = 'PE'
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER','')
# Confluence API Token. Generate one here: https://id.atlassian.com/manage-profile/security/api-tokens
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_API_TOKEN','')

PROJECT = os.getenv('DATA_PROJECT','')
SERVICE = os.getenv('DATA_SERVICE','')
STAGE = os.getenv('DATA_STAGE','')
INCOMING_START_TIME = os.getenv('DATA_EVALUATION_START','')
INCOMING_END_TIME = os.getenv('DATA_EVALUATION_END','')
TIMEFRAME = os.getenv('DATA_EVALUATION_TIMEFRAME','')
#Adding exit to check what time is coming through
print(INCOMING_START_TIME)
print(INCOMING_END_TIME)
exit()
# If start or end time is an empty string, we must have been given a timeframe
# Then we can get the end time from the TIME environment variable and calculate the start time as TIME-timeframe
# If we don't have start, end OR timeframe, we cannot proceeed. Exit
if INCOMING_START_TIME == '' and INCOMING_END_TIME == '' and TIMEFRAME == '':
  print('Script needs either START and END time or TIMEFRAME. Not enough info to proceed. Exiting safely.')
  exit()
# If start and 
if (INCOMING_START_TIME == '' or INCOMING_END_TIME == '') and TIMEFRAME != '':
  print('Start or end time not provided but we do have timeframe. Calculating times')
  time_from_env_var = os.getenv('TIME','')
  if time_from_env_var == '':
    print('Still dont have time from TIME env var. Cannot proceed. Exiting.')
    exit()
  # Finally! If we have the TIME variable, we can use it as the END time as-is
  # Then take TIME, format it correctly and shift is back by TIMEFRAME
  # TIME comes in as '2021-10-14T07:22:21.032Z'
  # To match the INCOMING_TIME_FORMAT lets remove those milliseconds and the Z and replace with .000Z
  time_from_env_var = time_from_env_var[:-5] + '.000Z'
  time_shift = int(TIMEFRAME[:-1])
  time_shift_units = TIMEFRAME[-1:] # eg. m=mins, h=hours
  print(f'Time From Env Var: {time_from_env_var}')
  print(f'Time Shift: {time_shift}')
  print(f'Time Shift Units: {time_shift_units}')
  INCOMING_END_TIME = time_from_env_var
  INCOMING_START_TIME = datetime.strptime(time_from_env_var, INCOMING_TIME_FORMAT)
  print(f'Incoming End time straight from TIME env var: {INCOMING_END_TIME}')
  print(f'Incoming Start Time before we shift it back: {INCOMING_START_TIME}')
  if time_shift_units == 'm':
    INCOMING_START_TIME -= timedelta(minutes=time_shift)
  if time_shift_units == 'h':
    INCOMING_START_TIME -= timedelta(hours=time_shift)
  # Now that we've calculated the start time, cast back to string as we need to shift it once move for timezones below
  INCOMING_START_TIME = INCOMING_START_TIME.strftime(INCOMING_TIME_FORMAT)

  print('Finished calculating start and end time from timeframe. Printing')
  print(INCOMING_START_TIME)
  print(INCOMING_END_TIME)
  print(TIMEFRAME)

KEPTN_CONTEXT = os.getenv('SHKEPTNCONTEXT','')
KEPTN_BRIDGE_URL = os.getenv('KEPTN_BRIDGE_URL','')
print(INCOMING_START_TIME)
EVENT_LABELS = ""
try:
  EVENT_LABELS = finished_event_json['data']['labels']
except:
  print('Error retrieving event labels.')

TEST_NAME = os.getenv('DATA_LABELS_TESTNAME','LABEL_TESTNAME_NOT_SET')
BUILD_ID = os.getenv('DATA_LABELS_BUILDID','LABEL_BUILDID_NOT_SET')

# Shift time forward
LOCAL_START_TIME_OBJECT = datetime.strptime(INCOMING_START_TIME, INCOMING_TIME_FORMAT)
LOCAL_END_TIME_OBJECT = datetime.strptime(INCOMING_END_TIME, INCOMING_TIME_FORMAT)
LOCAL_START_TIME_OBJECT += timedelta(hours=TIME_SHIFT_HOURS)
LOCAL_END_TIME_OBJECT += timedelta(hours=TIME_SHIFT_HOURS)
LOCAL_START_TIME = LOCAL_START_TIME_OBJECT.strftime(OUTBOUND_TIME_FORMAT)
LOCAL_END_TIME = LOCAL_END_TIME_OBJECT.strftime(OUTBOUND_TIME_FORMAT)
DASHBOARD_START_TIME = LOCAL_START_TIME_OBJECT.strftime(DASHBOARD_TIME_FORMAT)
DASHBOARD_END_TIME = LOCAL_END_TIME_OBJECT.strftime(DASHBOARD_TIME_FORMAT)

if DEBUG:
  print(f'Local Start Time: {LOCAL_START_TIME}')
  print(f'Local Start Time: {LOCAL_END_TIME}')

# Test variables
TEST_RESULT = ""
try:
  TEST_RESULT = finished_event_json['data']['evaluation']['result']
except:
  print('exception caught parsing TEST_RESULT. Cannot continue.')
  exit()

TEST_RESULT_CONFLUENCE = ""
TEST_RESULT_SLACK = ""
# Add nice icons
if TEST_RESULT == "pass":
	TEST_RESULT_CONFLUENCE = "<ac:emoticon ac:name=\"tick\" /> pass"
	TEST_RESULT_SLACK = ":white_check_mark: pass"
if TEST_RESULT == "warning":
	TEST_RESULT_CONFLUENCE = "<ac:emoticon ac:name=\"warning\" /> warning"
	TEST_RESULT_SLACK = ":warning: warning"
if TEST_RESULT == "fail":
	TEST_RESULT_CONFLUENCE = "<ac:emoticon ac:name=\"cross\" /> fail"
	TEST_RESULT_SLACK = ":x: fail"
TEST_SCORE = ""
try:
  TEST_SCORE = finished_event_json['data']['evaluation']['score']
  TEST_SCORE_STRING = str(round(TEST_SCORE,2)) + "%"
except:
  print('exception parsing or processing TEST_SCORE. Cannot continue. Exiting')
  exit()

DT_ENV_LINK = ""
if EVENT_LABELS != "":
  DT_ENV_LINK = EVENT_LABELS.get("DTEnv","") # Requires --labels=DTEnv=https://abc123.live.dynatrace.com
  DT_DASHBOARD_UUID = EVENT_LABELS.get("Dashboard","") # Requires --labels=Dashboard=307166d8-7b70-46dd-8ba2-04ee8cf14043
dt_dashboard_link = "" # This will be built below
# Work in progress
# Note: The following dashboard parsing code contains bugs since we moved away from a dashboard based model, so this DEFINITELY needs a fix.
# EXPECT BUGS until this comment is removed.

# If a dashboard UUID has been provided, create a time filter for it and add to the payload
# Else set the dashboard ID to https://example.com

if DEBUG:
  print(f'DT_ENV_LINK: {DT_ENV_LINK}')
  print(f'DT_DASHBOARD_UUID: {DT_DASHBOARD_UUID}')

if DT_ENV_LINK != "" and DT_DASHBOARD_UUID != "" and is_valid_uuid(DT_DASHBOARD_UUID):
  # Like: https://abc123.live.dynatrace.com/#dashboard;id=62eeba9e-b23b-46c7-b3c4-cef18222c281;gtf=2021-10-11T08:10:00+10:00%20to%202021-10-11T08:20:00+10:00
  dt_dashboard_link = f"{DT_ENV_LINK}#dashboard;id={DT_DASHBOARD_UUID};gtf={DASHBOARD_START_TIME}to{DASHBOARD_END_TIME}"
else:
  dt_dashboard_link = "https://example.com"
if DEBUG:
  print(f'dt_dashboard_link: {dt_dashboard_link}')

# Build Confluence Page Body
CONFLUENCE_TEMPLATE_BODY = f"""<img src="https://raw.githubusercontent.com/keptn/community/master/logos/keptn-small.png" />
                  <h2><strong>Performance Engineering - Test Summary Report (Powered by DynaTrace and Keptn Quality Gate)</strong></h2>
		  <h3><a href=\"{dt_dashboard_link}\">View Dynatrace Dashboard</a></h3>
		  <h3><a href=\"{KEPTN_BRIDGE_URL}/evaluation/{KEPTN_CONTEXT}/{STAGE}\">View Cloud Automation Evaluation</a></h3>
		  <h3><strong>PT Execution Summary</strong></h3>
		  <table>
		    <tr><td><strong>Performance Centre Scenario</strong></td><td>{TEST_NAME}</td></tr>
		    <tr><td><strong>Trader Backend and Engine deployment version</strong></td><td>{BUILD_ID}</td></tr>
		    <tr><td><strong>PT Outcome (PASS/Warning/FAIL)</strong></td><td>{TEST_RESULT_CONFLUENCE}</td></tr>
		    <tr><td><strong>Keptn QualityGate Score</strong></td><td>{TEST_SCORE_STRING}</td></tr>
		    <tr><td><strong>PT Start DateTime (Steady State)</strong></td><td>{LOCAL_START_TIME}</td></tr>
		    <tr><td><strong>PT End DateTime  (Steady State)</strong></td><td>{LOCAL_END_TIME}</td></tr>
		    <tr><td><strong>Rampup - steadystate - rampdown</strong></td><td>60 min - 60 min - 30 min</td></tr>
		    <tr><td><strong>JIRA Ticket - Release Page</strong></td><td></td></tr>
		    <tr><td><strong>Project</strong></td><td>{PROJECT}</td></tr>
		    <tr><td><strong>Service</strong></td><td>{SERVICE}</td></tr>
		    <tr><td><strong>Stage</strong></td><td>{STAGE}</td></tr>
		  </table>
	       """
#Objective Summary
CONFLUENCE_TEMPLATE_BODY += f"""
                  <h2><strong>Objective Summary</strong></h2>
		  
		  
	       """

#Defects
CONFLUENCE_TEMPLATE_BODY += f"""
                  <h2><strong>Defects</strong></h2>
		  <table>
		    <tr><th><strong>Defect Link</strong></th><th><strong>Details</strong></th></tr>
		    <tr><td><strong></strong></td><td></td></tr>
		  </table>
	       """

## OUTPUT SLI BREAKDOWN
slis = None
try:
  slis = finished_event_json['data']['evaluation']['indicatorResults']
except:
  print('Exception parsing slis')

if slis == None or len(slis) == 0:
  CONFLUENCE_TEMPLATE_BODY += "<h3>No Metrics Available</h3>"
else:
  CONFLUENCE_TEMPLATE_BODY += "<h3>SLI Breakdown</h3>"
  CONFLUENCE_TEMPLATE_BODY += "<table><tr><th>Name</th><th>Value</th><th>Pass Criteria</th><th>Warning Criteria</th><th>Result</th></tr>"

  for sli in slis:
    metric_name = sli['value']['metric']
    metric_value = sli['value']['value']
    metric_status = sli['status']
    # Add nice icons
    if metric_status == "pass":
      metric_status = "<ac:emoticon ac:name=\"tick\" /> pass"
    if metric_status == "warning":
      metric_status = "<ac:emoticon ac:name=\"warning\" /> warning"
    if metric_status == "fail":
      metric_status = "<ac:emoticon ac:name=\"cross\" /> fail"
    if metric_status == "info":
      metric_status = "<ac:emoticon ac:name=\"information\" /> info"
	
    #metric_score = sli['score']
    passTargets = sli['passTargets'] # Could be null if info only metric
    if passTargets:
      metric_pass_target = passTargets[0]['criteria']
    else:
      metric_pass_target = "-"
    # Replace special charts with HTML safe versions
    # Replaces things like < with &lt;
    # Otherwise confluence API breaks
    metric_pass_target = html.escape(metric_pass_target)

    warningTargets = sli['warningTargets'] # Could be null if no warning threshold set
    if warningTargets:
      metric_warning_target = warningTargets[0]['criteria']
      # Replace special charts with HTML safe versions
      metric_warning_target = html.escape(metric_warning_target)
    else:
      metric_warning_target = "-"
  
    CONFLUENCE_TEMPLATE_BODY += "<tr><td>" + str(metric_name) + "</td><td>" + str(round(metric_value,2)) + "</td><td>" + str(metric_pass_target) + "</td><td>" + str(metric_warning_target) + "</td><td>" + str(metric_status) + "</td></tr>"

  CONFLUENCE_TEMPLATE_BODY += "</table>"
#Infrastructure Output
CONFLUENCE_TEMPLATE_BODY += f"""
                  <h2>Infrastructure Configuration [NO Autoscaling]</h2>
		  <table>
		    <tr><th><strong>Infrastructure</strong></th><th><strong>Count</strong></th></tr>
		    <tr><td><strong>No. of Trader UI Pods (wowdk8suiaae - UI)</strong></td><td>16</td></tr>
		    <tr><td><strong>No. of Trader API Pods (wowdksapiaae - API)</strong></td><td>5</td></tr>
		    <tr><td><strong>No. of SearchAPI Pods (Microservice)</strong></td><td>12</td></tr>
		    <tr><td><strong>No. of Nginx-Ingress Pods</strong></td><td>2</td></tr>
		    <tr><td><strong>Database Capacity (vCores)</strong></td><td>40</td></tr>
		    <tr><td><strong>Redis</strong></td><td>16</td></tr>
		  </table>
	       """

### OUTPUT Test  Screenshots
CONFLUENCE_TEMPLATE_BODY += "<h3><strong>TEST DETAILS</strong></h3>"


### OUTPUT LABELS
CONFLUENCE_TEMPLATE_BODY += "<h3>Labels</h3>"
CONFLUENCE_TEMPLATE_BODY += "<table><tr><th>Key</th><th>Value</th></tr>"

# Ignore some tags that are printed above as "specially treated tags"
special_tags_to_ignore = ["testname", "buildid", "dashboard link", "dtcreds"]

if EVENT_LABELS != "":
  for key in EVENT_LABELS:
    # Only print "non special tags"
    # Special tags are simply those printed above in the main table.
    # So don't print them again
    if key.lower() not in special_tags_to_ignore:
      CONFLUENCE_TEMPLATE_BODY += "<tr><td><strong>" + key + "</strong></td><td>" + EVENT_LABELS.get(key) + "</td></tr>"

CONFLUENCE_TEMPLATE_BODY += "</table>"

WARNINGS = "" # By default there will be no warnings. If any errors, print some useful output to slack.
if slis == None or len(slis) == 0:
  WARNINGS = "*Warning: No Metrics Retrieved*\n\n"

SLACK_TEXT = f"""
*Cloud Automation Evaluation*\n\n{WARNINGS}*Test Name:* {TEST_NAME}\n*Build ID:* {BUILD_ID}\n*Result*: {TEST_RESULT_SLACK}\n*Score*: {TEST_SCORE_STRING}\n*Project:* {PROJECT}\n*Service:* {SERVICE}\n*Stage:* {STAGE}\n*Start Time:* {LOCAL_START_TIME}\n*End Time:* {LOCAL_END_TIME}
"""
#############################
#     POST TO SLACK
#############################
payload = {
	"blocks": [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": SLACK_TEXT
            }, "accessory": {
				"type": "image",
				"image_url": "https://raw.githubusercontent.com/keptn/community/master/logos/keptn-small.png",
				"alt_text": "Keptn Logo"
			}
        }, {
            "type": "divider"
        }, {
			"type": "actions",
			"elements": [{
                       "type": "button",
				        "text": {
						"type": "plain_text",
						"text": ":arrow_right: View Dashboard",
						"emoji": True
					},
					"url": dt_dashboard_link
			             }, {
                       "type": "button",
				        "text": {
						"type": "plain_text",
						"text": ":bar_chart: View Evaluation Results",
						"emoji": True
					},
					"url": KEPTN_BRIDGE_URL + "/evaluation/" + KEPTN_CONTEXT + "/" + STAGE
			             },
				     {
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": ":unlock: Confluence Page",
						"emoji": True
					},
					"url": "https://woolworthsdigital.atlassian.net/wiki/spaces/PE/pages"
				}
			]
		}]
}

if PROD_MODE:
  r = requests.post(SLACK_HOOK_URL, json=payload)

  print('Slack Notification Status Code: ' + str(r.status_code))
  #print(r.text)

##########################
# POST TO CONFLUENCE
##########################
url = f"https://api.atlassian.com/ex/confluence/{CONFLUENCE_SITE_ID}/wiki/rest/api/content"

headers = {
   "Accept": "application/json",
   "Content-Type": "application/json"
}

payload = json.dumps( {
  "title": TEST_NAME + "(" + BUILD_ID + ")",
  "type": "page",
  "space": {
    "key": CONFLUENCE_SPACE_ID
  },
  "status": "current",
  "body": {
    "storage": {
      "value": CONFLUENCE_TEMPLATE_BODY,
      "representation": "storage"
    }
  }
} )

if PROD_MODE: 
  response = requests.request(
     "POST",
     url,
     data=payload,
     headers=headers,
     auth=(CONFLUENCE_USER, CONFLUENCE_API_TOKEN)
  )

  print('Confluence Page Status Code: ' + str(response.status_code))
  print('Confluence Page url: ' + str(response.url))
  print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))

#get the Page Id for the confluence 

def get_pageId():
    r = requests.get(url, verify=False, headers=headers, auth=(CONFLUENCE_USER, CONFLUENCE_API_TOKEN))
    data = r.json()
    for results in data["results"]:
        id = (results["id"])
    return id

pageID = get_pageId()
print('Confluence Page ID: ' + pageID)
