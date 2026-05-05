import time
import json
import requests
import stomp
import argparse
from pushbullet import Pushbullet
import os
import pygame
import mutagen.mp3

#RTT login details
rttSource = 'api.rtt.io'
rttUser = #Realtime Trains API username
rttPass = #Realtime Trains API password

#TD login details
tdUser = #Train Desciber feed username
tdPass = #Train Describer feed password
tdConn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)])

#Pushbullet details
pbKey = #Pushbullet Key

#Signalling berths that can determine platform alterations at Leyland. Initialising the variables using the empty '0000' value. Names of the variables correspond to the actual name of the berth
#3>1 berths
berthPN12 = '0000'  #First determining berth for trains changing from 3>1 coming from Wigan North Western
berthPN16 = '0000'  #Second determining berth for trains changing from 3>1 coming from Wigan North Western
berthPN37 = '0000'  #First determining berth for trains changing from 3>1 coming from Buckshaw Parkway
#1>3 berths
berthPN38 = '0000'  #First determining berth for all trains changing from 1>3
#4>2 berths
berthPN72 = '0000'  #First determining berth for trains changing from 4>2 coming from Preston
berthPN56 = '0000'  #Second determining berth for trains changing from 4>2 coming from Preston
berthPN51 = '0000'  #Third determining berth for trains changing from 4>2 coming from Preston
berthPN44 = '0000'  #First determining berth for trains changing from 4>2 coming from Bamber Bridge
#2>4 berths
berthPN45 = '0000'  #First determining berth for all trains changing from 2>4

#Variable used for storing alteration information
altStatusUp = False
altDescUp = '-'
altHeadcodeUp = '0000'
altStatusDown = False
altDescDown = '-'
altHeadcodeDown = '0000'

#Variables used for error management
rttError = False
tdConnectDelay = 1

#Function which retrieves the train data requested by the RTTtrainRquest function from the RTT JSON dictionary
def RTTDataExtract(rttData, trainNo, dataType):
    try:
        if dataType == 'headcode':
            extractedValue = rttData['services'][trainNo]['runningIdentity']
        elif dataType == 'time':
            extractedValue = rttData['services'][trainNo]['locationDetail']['gbttBookedDeparture']
        elif dataType == 'destination':
            extractedValue = rttData['services'][trainNo]['locationDetail']['destination'][0]['description']
        elif dataType == 'platform':
            extractedValue = rttData['services'][trainNo]['locationDetail']['platform']
        
        return extractedValue

    except:
        return 'NONE'
    
    
#Function which generates a dictionary with the details of each booked train service
def RTTtrainRequest(trainNo):
    global rttError
    try:
        trainDetails = {
            "headcode": RTTDataExtract(rttRequest.json(),trainNo,'headcode'),
            "time": RTTDataExtract(rttRequest.json(),trainNo,'time'),
            "destination": RTTDataExtract(rttRequest.json(),trainNo,'destination'),
            "platform": RTTDataExtract(rttRequest.json(),trainNo,'platform'),
            }
        rttError = False
    except:
        rttError = True
        trainDetails = {
            "headcode": 'NONE',
            "time": 'NONE',
            "destination": 'NONE',
            "platform": 'NONe',
            }
    return trainDetails

#Connects to the TD data-feed. Is called every time the program starts and every time a disconnection occurs            
def TDConnection():
    global tdConnectDelay
    try:
        tdConn.start()
        tdConn.connect(tdUser, tdPass, wait=True)
        tdConn.subscribe(destination='/topic/TD_ALL_SIG_AREA', id=1, ack='auto')
        tdConnectDelay = 1
    except:
        #Displays error message if TD fails. Placed within function because if this feed fails, the main loop will not run
        os.system('cls' if os.name == 'nt' else 'clear')
        print('ERROR - Connection to TRUST lost')
        
        #Attemps to reconnect to TD using recursive backoff, with a maximum delay of 1000 seconds
        if tdConnectDelay < 1000:
            tdConnectDelay = tdConnectDelay * 2
        time.sleep(tdConnectDelay)
        TDConnection()

#Listens for data from TD data-feed and changes the berth variables according to what train headcode is within them
class TDDataExtract(stomp.ConnectionListener):
    def on_message(self, headers, message):
        tdData = json.loads(message)

        #Defining berth variables as global
        global berthPN12
        global berthPN16
        global berthPN37
        global berthPN38
        global berthPN72
        global berthPN56
        global berthPN51
        global berthPN44
        global berthPN45

        #The TD feed will send several messages at once in a list, for loop with length of data specified ensures all list entries are read
        for i in range(len(tdData)):

            #CA messages are sent from TD when any trains move
            movement = tdData[i].get('CA_MSG')

            #If there is no CA message, ignore the TD output
            if movement == None:
                pass

            #If statement is true when the train movement does originate from the Preston signalling area
            elif movement['area_id'] == 'PX':

                #If the train movement is moving to one of the determining berths, set the corresponding berth variable to the headcode of the train (known as 'descr' on TD feed)
                if movement['to'] == '0012':
                    berthPN12 = movement['descr']
                elif movement['to'] == '0016':
                    berthPN16 = movement['descr']
                elif movement['to'] == '0037':
                    berthPN37 = movement['descr']
                elif movement['to'] == '0038':
                    berthPN38 = movement['descr']
                elif movement['to'] == '0072':
                    berthPN72 = movement['descr']
                elif movement['to'] == '0056':
                    berthPN56 = movement['descr']
                elif movement['to'] == '0051':
                    berthPN51 = movement['descr']
                elif movement['to'] == '0044':
                    berthPN44 = movement['descr']
                elif movement['to'] == '0045':
                    berthPN45 = movement['descr']

                #If the train moving is moving away (from) one of the determining berths, reset the corresponding berth variable back to '0000'
                if movement['from'] == '0012':
                    berthPN12 = '0000'
                elif movement['from'] == '0016':
                    berthPN16 = '0000'
                elif movement['from'] == '0037':
                    berthPN37 = '0000'
                elif movement['from'] == '0038':
                    berthPN38 = '0000'
                elif movement['from'] == '0072':
                    berthPN72 = '0000'
                elif movement['from'] == '0056':
                    berthPN56 = '0000'
                elif movement['from'] == '0051':
                    berthPN51 = '0000'
                elif movement['from'] == '0044':
                    berthPN44 = '0000'
                elif movement['from'] == '0045':
                    berthPN45 = '0000'

        #Attemp to reconnect if 
        def on_disconnected(self):
            TDConnection()

#Send notification via Pushbullet when an alteration occurs. Also triggers the audio alert on the device itself
def SendNotif(altDesc):
    try:
        pb = Pushbullet(pbKey)
        pb.push_note('PLATFORM ALTERATION', altDesc)
        PlayAlertSound()
    except:
        time.sleep(1)
        SendNotif(altDesc)

#Play audio alert. Is triggered when a platform alteration is detected
def PlayAlertSound():
    audioFile = "PlatAlt.mp3"
    mp3 = mutagen.mp3.MP3(audioFile)
    pygame.mixer.init(frequency=mp3.info.sample_rate)
    pygame.mixer.music.load(audioFile)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue
    
        

#Main looping section of program
while 1 == 1:
    
    #Accessing the RTT data-feed
    try:
        session = requests.Session()
        session.auth = (rttUser, rttPass)
        auth = session.post('https://' + rttSource)
        rttRequest = (session.get('https://' + rttSource + '/api/v1/json/search/LEY'))
        rttError = False
    except:
        rttError = True
    
    #Request the next 5 trains incase any sheduled to depart first are delayed
    train1 = RTTtrainRequest(0)
    train2 = RTTtrainRequest(1)
    train3 = RTTtrainRequest(2)
    train4 = RTTtrainRequest(3)
    train5 = RTTtrainRequest(4)

    tdConn.set_listener('', TDDataExtract())
    if not tdConn.is_connected():
        TDConnection()

    #Identifying if an alteration is occuring by comparing the berth variables with the assigned platform on the timetable
    #Down (north) direction alterations
    if altStatusDown == False:
        #3>1
        if train1['platform'] != '3' and berthPN38 == train1['headcode']:
            altStatusDown = True
            altHeadcodeDown = train1['headcode']
            altDescDown = altHeadcodeDown + " - The " + train1['time'] + " service to " + train1['destination'] + ' will now depart from platform 3'
            SendNotif(altDescDown)
        
        elif train2['platform'] != '3' and berthPN38 == train2['headcode']:
            altStatusDown = True
            altHeadcodeDown = train2['headcode']
            altDescDown = altHeadcodeDown + " - The " + train2['time'] + " service to " + train2['destination'] + ' will now depart from platform 3'
            SendNotif(altDescDown)
        
        elif train3['platform'] != '3' and berthPN38 == train3['headcode']:
            altStatusDown = True
            altHeadcodeDown = train3['headcode']
            altDescDown = altHeadcodeDown + " - The " + train3['time'] + " service to " + train3['destination'] + ' will now depart from platform 3'
            SendNotif(altDescDown)
        
        elif train4['platform'] != '3' and berthPN38 == train4['headcode']:
            altStatusDown = True
            altHeadcodeDown = train4['headcode']
            altDescDown = altHeadcodeDown + " - The " + train4['time'] + " service to " + train4['destination'] + ' will now depart from platform 3'
            SendNotif(altDescDown)
        
        elif train5['platform'] != '3' and berthPN38 == train5['headcode']:
            altStatusDown = True
            altHeadcodeDown = train5['headcode']
            altDescDown = altHeadcodeDown + " - The " + train5['time'] + " service to " + train5['destination'] + ' will now depart from platform 3'
            SendNotif(altDescDown)
        
        #1>3
        elif train1['platform'] != '1':
            if berthPN12 == train1['headcode'] or berthPN16 == train1['headcode'] or berthPN37 == train1['headcode']:
                altStatusDown = True
                altHeadcodeDown = train1['headcode']
                altDescDown = altHeadcodeDown + " - The " + train1['time'] + " service to " + train1['destination'] + ' will now depart from platform 1'
                SendNotif(altDescDown)
        
        elif train2['platform'] != '1':
            if berthPN12 == train2['headcode'] or berthPN16 == train2['headcode'] or berthPN37 == train2['headcode']:
                altStatusDown = True
                altHeadcodeDown = train2['headcode']
                altDescDown = altHeadcodeDown + " - The " + train2['time'] + " service to " + train2['destination'] + ' will now depart from platform 1'
                SendNotif(altDescDown)
        
        elif train3['platform'] != '1':
            if berthPN12 == train3['headcode'] or berthPN16 == train3['headcode'] or berthPN37 == train3['headcode']:
                altStatusDown = True
                altHeadcodeDown = train3['headcode']
                altDescDown = altHeadcodeDown + " - The " + train3['time'] + " service to " + train3['destination'] + ' will now depart from platform 1'
                SendNotif(altDescDown)
        
        elif train4['platform'] != '1':
            if berthPN12 == train4['headcode'] or berthPN16 == train4['headcode'] or berthPN37 == train4['headcode']:
                altStatusDown = True
                altHeadcodeDown = train4['headcode']
                altDescDown = altHeadcodeDown + " - The " + train4['time'] + " service to " + train4['destination'] + ' will now depart from platform 1'
                SendNotif(altDescDown)
        
        elif train5['platform'] != '1':
            if berthPN12 == train1['headcode'] or berthPN16 == train1['headcode'] or berthPN37 == train1['headcode']:
                altStatusDown = True
                altHeadcodeDown = train5['headcode']
                altDescDown = altHeadcodeDown + " - The " + train5['time'] + " service to " + train5['destination'] + ' will now depart from platform 1'
                SendNotif(altDescDown)


    #Up (south) direction alterations
    if altStatusUp == False:
        #2>4
        if train1['platform'] != '4' and berthPN45 == train1['headcode']:
            altStatusUp = True
            altHeadcodeUp = train1['headcode']
            altDescUp = altHeadcodeUp + " - The " + train1['time'] + " service to " + train1['destination'] + ' will now depart from platform 4'
            SendNotif(altDescUp)
        
        elif train2['platform'] != '4' and berthPN45 == train2['headcode']:
            altStatusUp = True
            altHeadcodeUp = train2['headcode']
            altDescUp = altHeadcodeUp + " - The " + train2['time'] + " service to " + train2['destination'] + ' will now depart from platform 4'
            SendNotif(altDescUp)
        
        elif train3['platform'] != '4' and berthPN45 == train3['headcode']:
            altStatusUp = True
            altHeadcodeUp = train3['headcode']
            altDescUp = altHeadcodeUp + " - The " + train3['time'] + " service to " + train3['destination'] + ' will now depart from platform 4'
            SendNotif(altDescUp)
        
        elif train4['platform'] != '4' and berthPN45 == train4['headcode']:
            altStatusUp = True
            altHeadcodeUp = train4['headcode']
            altDescUp = altHeadcodeUp + " - The " + train4['time'] + " service to " + train4['destination'] + ' will now depart from platform 4'
            SendNotif(altDescUp)
        
        elif train5['platform'] != '4' and berthPN45 == train5['headcode']:
            altStatusUp = True
            altHeadcodeUp = train5['headcode']
            altDescUp = altHeadcodeUp + " - The " + train5['time'] + " service to " + train5['destination'] + ' will now depart from platform 4'
            SendNotif(altDescUp)
        
        #4>2
        elif train1['platform'] != '2':
            if berthPN72 == train1['headcode'] or berthPN56 == train1['headcode'] or berthPN51 == train1['headcode'] or berthPN44 == train1['headcode']:
                altStatusUp = True
                altHeadcodeUp = train1['headcode']
                altDescUp = altHeadcodeUp + " - The " + train1['time'] + " service to " + train1['destination'] + ' will now depart from platform 2'
                SendNotif(altDescUp)
        
        elif train2['platform'] != '2':
            if berthPN72 == train2['headcode'] or berthPN56 == train2['headcode'] or berthPN51 == train2['headcode'] or berthPN44 == train2['headcode']:
                altStatusUp = True
                altHeadcodeUp = train2['headcode']
                altDescUp = altHeadcodeUp + " - The " + train2['time'] + " service to " + train2['destination'] + ' will now depart from platform 2'
                SendNotif(altDescUp)
        
        elif train3['platform'] != '2':
            if berthPN72 == train3['headcode'] or berthPN56 == train3['headcode'] or berthPN51 == train3['headcode'] or berthPN44 == train3['headcode']:
                altStatusUp = True
                altHeadcodeUp = train3['headcode']
                altDescUp = altHeadcodeUp + " - The " + train3['time'] + " service to " + train3['destination'] + ' will now depart from platform 2'
                SendNotif(altDescUp)
        
        elif train4['platform'] != '2':
            if berthPN72 == train4['headcode'] or berthPN56 == train4['headcode'] or berthPN51 == train4['headcode'] or berthPN44 == train4['headcode']:
                altStatusUp = True
                altHeadcodeUp = train4['headcode']
                altDescUp = altHeadcodeUp + " - The " + train4['time'] + " service to " + train4['destination'] + ' will now depart from platform 2'
                SendNotif(altDescUp)
        
        elif train5['platform'] != '2':
            if berthPN72 == train5['headcode'] or berthPN56 == train5['headcode'] or berthPN51 == train5['headcode'] or berthPN44 == train5['headcode']:
                altStatusUp = True
                altHeadcodeUp = train5['headcode']
                altDescUp = altHeadcodeUp + " - The " + train5['time'] + " service to " + train5['destination'] + ' will now depart from platform 2'
                SendNotif(altDescUp)



    #Clearing existing alteration condition when once an affected train has left the station and removed from the timetable
    if altStatusUp == True and altHeadcodeUp !=  train1['headcode'] and altHeadcodeUp !=  train2['headcode'] and altHeadcodeUp !=  train3['headcode'] and altHeadcodeUp !=  train4['headcode'] and altHeadcodeUp !=  train5['headcode']:
        altStatusUp = False
        altDescUp = '-'

    if altStatusDown == True and altHeadcodeDown !=  train1['headcode'] and altHeadcodeDown !=  train2['headcode'] and altHeadcodeDown !=  train3['headcode'] and altHeadcodeDown !=  train4['headcode'] and altHeadcodeDown !=  train5['headcode']:
        altStatusDown = False
        altDescDown = '-'

    #Clearing visual display
    os.system('cls' if os.name == 'nt' else 'clear')
    #Displaying alteration information visually
    if altStatusUp == True and altStatusDown == True:
        print('***MULTIPLE PLATFORM ALTERATIONS***')
        print('')
        print(altDescUp)
        print('')
        print(altDescDown)
    elif altStatusUp == True:
        print('***PLATFORM ALTERATION***')
        print('')
        print(altDescUp)
    elif altStatusDown == True:
        print('***PLATFORM ALTERATION***')
        print('')
        print(altDescDown)
    elif rttError == True:
        print('ERROR - Connection to timetable lost')
    else:
        print('Real-time platform alteration notifier for Leyland station')
        print('Powered by TRUST (TD) and Realtime Trains')
        print('')
        print('System running - No alterations detected')



    time.sleep(1)
