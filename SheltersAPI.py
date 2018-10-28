import json
import math
import requests
from urllib.parse import quote

_dataLoaded     = False
_sheltersList   = []
_sheltersByCity = {}

class ShelterLocation:
    def __init__(self):
        self.thoroughfare = ""
        self.premise      = ""
        self.locality     = ""
        self.postCode   = ""

class Shelter:
    def __init__(self):
        self.name      = ""
        self.phoneNum  = ""
        self.location  = ShelterLocation()
        self.city      = ""
        self.link      = ""
        self.email     = ""
        self.info      = ""

    def toJSON(self):
        return json.dumps(self, default = lambda o: o.__dict__, sort_keys = True, indent = 0).replace("\n", "")

def _listToMap(keyFunction, values):
    return dict((keyFunction(v), v) for v in values)

def loadShelterData():
    if _sheltersList == []:
        #Intialise shelter data
        jsonText = open("shelters.json", "r").read()
        jsonData = json.loads(jsonText)

        sheltersNum        = 0
        skippedSheltersNum = 0

        #Iterate over the food banks in the group
        for shelterJson in jsonData["Shelters"]:
            sheltersNum += 1

            #Create a Shelter instance
            shelter = Shelter()

            #Extract the data and fill the struct
            try:
                shelter.name = shelterJson["title"]

                if "permalink" in shelterJson:
                    shelter.link = shelterJson["permalink"]
                else:
                    shelter.link = None

                #Phone number might not be available
                if "phone" in shelterJson:
                    shelter.phoneNum = shelterJson["phone"]
                else:
                    shelter.phoneNum = None

                shelter.email = shelterJson["email"]
                shelter.info  = shelterJson["info"]
                
                locationJson = shelterJson["address"]

                shelter.location.thoroughfare = locationJson["thoroughfare"]
                shelter.location.premise      = locationJson["premise"]
                shelter.location.locality     = locationJson["locality"]
                shelter.location.postCode   = locationJson["postal_code"]

                _sheltersList.append(shelter)
            except Exception as e:
                #For error checking
                print("\n\n\nError!\nException message:{}\nShelter index: {}\nSkipped shelter num: {}\nJson: {}\n".format(str(e), sheltersNum, skippedSheltersNum, shelterJson)) 
                exit()

        #Get city names
        postCodes = list(map(lambda it: '"{}"'.format(it.location.postCode), _sheltersList))

        postCodesBegin = 0
        postCodesEnd   = 0
        
        while postCodesEnd != len(postCodes):
            postCodesEnd = min(postCodesBegin + 100, len(postCodes))
            jsonPostArgs = "{{ \"postcodes\": [ {} ] }}".format(','.join(postCodes[postCodesBegin : postCodesEnd]))

            response = requests.post("http://api.postcodes.io/postcodes", json = json.loads(jsonPostArgs))
            
            assert(response.ok)

            results = json.loads(response.text)["result"]

            for i in range(postCodesBegin, postCodesEnd):
                if results[i - postCodesBegin]["result"] != None:
                    city = results[i - postCodesBegin]["result"]["admin_district"]
                    _sheltersList[i].city = city
                    
                    if city not in _sheltersByCity:
                        _sheltersByCity[city] = []

                    _sheltersByCity[city].append(_sheltersList[i])

            postCodesBegin = postCodesEnd

        global _dataLoaded
        _dataLoaded = True
        #print("\n\nData extracted succesfully.\nNum of entries: {}\nTotal amount: {}\nSkipped food banks: {}".format(sheltersNum - skippedSheltersNum, sheltersNum, skippedSheltersNum))

def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def getShelters():
    assert(_dataLoaded)
    return _sheltersList

def getCities():
    assert(_dataLoaded)
    return list(_sheltersByCity.keys())

def getSheltersByCity(city):
    assert(_dataLoaded)
    return _sheltersByCity[city]

def getSortedSheltersByLocation(lat, lng, shelters):
    assert(_dataLoaded)
    return sorted(shelters, key = lambda fb: distance((lat, lng), (fb.location.lat, fb.location.lng)))
