#!C:\Programs\python-3.6.5-embed-amd64 python
import sys
import logging
import json
import string
from time import sleep
import random
#import datetime
from datetime import datetime  
from datetime import timedelta 
import configparser
import re
from threading import Lock
import threading

logging.basicConfig(filename='middleware.log', level=logging.DEBUG)
logging.debug('Middleware is called')

def main():
 data = sys.stdin.readlines()
 # this is a json string in one line so we are interested in that one line
 payload = data[0]
 logging.debug("payload-->" + payload)
 
 responseCode = 200
 operationDelay = -1
 
 config = configparser.RawConfigParser()
 config.read('stub-env.properties')
 
 payload_dict = json.loads(payload)
 
 requestBodyValue = payload_dict['request']['body']
 logging.debug("***REQUEST BODY-->" + requestBodyValue)
 
 if requestBodyValue is None or requestBodyValue == "":
    requestBodyValue = payload_dict['request']['path']
    logging.debug("***REQUEST PATH-->" + requestBodyValue)
 
 bodyvalue = payload_dict['response']['body']
 bodyvalueAfter = bodyvalue
 logging.debug("RESPONSE BODY-->" + bodyvalue)
 
 operationName = getOperation(requestBodyValue, config)
 logging.debug("operationName value-->" + operationName)
 
 opResponseData, opResponseCode, opResponseDelay = retrieveConfiguredResponse(config, operationName)
 
 if opResponseData:
    bodyvalueAfter = opResponseData
 if opResponseCode:
    responseCode = opResponseCode
 if opResponseDelay:
    operationDelay = int(opResponseDelay)

 bodyvalueAfter = customizeResponse(config, operationName, requestBodyValue, bodyvalueAfter)

 logging.debug("RESPONSE BODY-->" + bodyvalueAfter)
  
 payload_dict['response']['status'] = responseCode
 payload_dict['response']['body'] = bodyvalueAfter

 # apply delay
 if operationDelay != -1:
    sleep(operationDelay)
 else:
  sleep(0.1)


 # payload_dict = bodyvalueAfter
 # returning new payload
 print(json.dumps(payload_dict))



###############################################
# load from defined location such as file, db etc
###############################################
def retrieveConfiguredResponse( config,operationName):

 dataStore = read_config(config,'StubEnvProperties', 'stub.datastore')
 
 responseData = ""
 responseCode = ""
 operationDelay = "-1"
 
 if "file" in dataStore and operationName:
    
    fileStoreAbsPath = read_config(config, 'StubResponseProperties', dataStore + '.' + operationName + '.response.store')
    definedResponseCode = read_config(config, 'StubResponseProperties', dataStore + '.' + operationName + '.response.code')
    opDelay = read_config(config, 'StubDelayProperties', operationName + '.delay')
	
    if fileStoreAbsPath is None:
        print('The value of the variable is none')
    else:
	
      if fileStoreAbsPath:
        logging.debug("loading from file-->" + fileStoreAbsPath)
        file = open(fileStoreAbsPath, "r")
        responseData = file.read()
        file.close();
		
      if definedResponseCode is None:
         print('The value of the variable is none')
      else:
         if definedResponseCode:
             responseCode = int(definedResponseCode)

      if opDelay is None:
         print('The value of the variable is none')
      else:
         if opDelay:
             operationDelay = opDelay
     
 return responseData, responseCode, operationDelay

###############################################
# identify the operation from request correctly
###############################################
def getOperation (request, config):    
    operationName = ""
	
    operationList = read_config(config,'StubOperationsSupportedProperties', 'stub.support.operation.list')
	
    for opName in operationList.split(","):
        if opName in request:
            operationName = opName
            break
	 
    return operationName

###############################################
# load properties
###############################################
def read_config(config, section, key):
    value=""
    if config.has_option(section, key):
       value = config.get(section, key)
    
    return value
	
###############################################
# load from defined location such as file, db etc
###############################################
def customizeResponse(config, operationName, requestBodyValue, bodyvalueAfter):
    logging.debug("body to customise -->" + bodyvalueAfter)
    customizedResponse = bodyvalueAfter
 
    replacementList = read_config(config,'PopulateResponseFromRequestProperties', operationName + '.replace')
	
    #text = "cpaID>*<ns2:DoubleDependentLocality/>*<ns2:PostCode>BL3 6HX</ns2:PostCode><ns2:PremisesName/>*<ns2:ThoroughFareNumber/>"
    #m = re.search('PostCode>(.*?)<', text)
    #if m:
    #    found = m.group(1)
    #logging.debug("found >>>>>>>" + found)
    #logging.debug("test replacement-->" + "<StartDate>10/06/2018</StartDate>".replace('10/06/2018', '2018-06-10T00:00:00.000+02:00'))

    if replacementList:
      for replacementText in replacementList.split("#"):
          logging.debug("replacementText -->" + replacementText)
		  
          reqRegEx = replacementText
          resRegEx=""
          if "|" in replacementText:
              reqRegEx, resRegEx = replacementText.split("|")
			  
          reqValue = findMatch(reqRegEx, requestBodyValue)	  
          logging.debug("reqValue found -->" + reqValue)
	 
          if reqValue:
              logging.debug("1.inside replacement now........[" + resRegEx + " | " + reqValue + "]")
			  
              if resRegEx is None or resRegEx == "":
                  resRegEx = reqRegEx

              resValue = findMatch(resRegEx, bodyvalueAfter)
              logging.debug("resValue found -->" + resValue)
			  
              if resValue:
                 replacePrefix = resRegEx.split('>')[0] + '>'
                 logging.debug("2.Going to replace now [" + replacePrefix + resValue + " | " + replacePrefix + reqValue + "]")
                 #customizedResponse = re.sub(resRegEx, reqValue, customizedResponse.rstrip())

                 customizedResponse = customizedResponse.replace( replacePrefix + resValue, replacePrefix + reqValue)
   
 
    # if the request is AddressSearch
    if operationName == "AddressSearch":
        postCode = findMatch('PostCode>(.+?)<', requestBodyValue)
        addressRef = findMatch('AddressReference>(.+?)<', customizedResponse)

        #addressKey = ''.join(random.choice('0123456789ABCDEF') for i in range(8))
        addressKey = getAddressReference(postCode, '/etc/hqn/stubs/')

        customizedResponse = customizedResponse.replace(addressRef, addressKey)
	
	# if the request is RequestAvailableAppointment
    if operationName == "RequestAvailableAppointment":

        appointmentStartDate = findMatch('StartDate>(.+?)<', requestBodyValue)
        appointmentType = findMatch('AppointmentType>(.+?)<', requestBodyValue)

        if appointmentType is None or appointmentType == '':
            appointmentType = 'Flexible'
			
        if appointmentStartDate:
           appointmentStartDate = appointmentStartDate.split("T")[0]
           startDate = datetime.strptime(appointmentStartDate, "%Y-%m-%d").date()
        else:
           startDate = datetime.today() 		

        #nextDate = startDate.strftime('%d/%m/%Y')
        #end_date = startDate + timedelta(days=10)
        #todayDateStr = end_date.strftime('%d/%m/%Y')
        #logging.debug("todayDateStr -->" + todayDateStr)
        #logging.debug("customizedResponse -->" + customizedResponse)
		
		
        startIdx = customizedResponse.find('&lt;ListOfAppointment&gt;')
        endIdx = customizedResponse.find('&lt;/ListOfAppointment&gt;')
        defaultAppList = customizedResponse[startIdx : endIdx + 26]
        logging.debug("defaultAppList -->" + str(startIdx))
        logging.debug("defaultAppList -->" + str(endIdx))
        logging.debug("defaultAppList -->" + defaultAppList)

        appointmentTemplate = '&lt;Appointment xmlns=\"\"&gt;&lt;AppointmentDate&gt;DATE&lt;/AppointmentDate&gt;&lt;AppointmentTimeslot&gt;SLOT&lt;/AppointmentTimeslot&gt;&lt;/Appointment&gt;'
        appointmentStr = '&lt;ListOfAppointment&gt;'
        i = 0
        while i < 5:
            nextDate = startDate + timedelta(days=i)
            nextDateStr = nextDate.strftime('%d/%m/%Y')
            appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'AM')
            appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'PM')

            if appointmentType == "Flexible":
                appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'EM')
                appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'MFALM')
                appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'MFAEA')
                appointmentStr = appointmentStr + appointmentTemplate.replace('DATE', nextDateStr).replace('SLOT', 'EV')
            i += 1

        appointmentStr = appointmentStr + '&lt;/ListOfAppointment&gt;'
        customizedResponse = customizedResponse.replace(defaultAppList, appointmentStr)
	   
    return customizedResponse;

#############################################
## match
#############################################
def findMatch(regEx, body):
    matchValue = ""
    match = re.search(regEx, body)
    if match:
        matchValue = match.group(1)

    return matchValue

def getAddressReference(postCode, seqFilePath):
    addressKeyPrefix = 'A021'
    filekey = '21cn'
    if postCode.startswith('A'):
        addressKeyPrefix = 'A020'
        filekey = '20cn'
			
    fname = seqFilePath + '/sequence/' + filekey + '/sequence-addressref-' + filekey + '.txt'
    #global lck
    #lck = Lock()
    #lck = Threading.Lock()
    lck = threading.RLock()
    lck.acquire()
    file = open(fname, 'r')
    currentSeq = file.read()
    logging.debug("currentSeq-->" + currentSeq)
    file.close()
    file = open(fname, 'w')
    n = int(currentSeq) + 1
    file.write(str(n))
    file.close()
    lck.release()
	
    return addressKeyPrefix + '%08d' % n

if __name__ == "__main__":
 main()