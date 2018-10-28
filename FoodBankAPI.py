import json
import math
import requests
from urllib.parse import quote

UK_FOOD_BANK_DATA_URL = "https://www.trusselltrust.org/get-help/find-a-foodbank/foodbank-search/?foodbank_s=all&callback=?"

_dataLoaded        = False
_ukFoodBanksList   = []
_ukFoodBanksByCity = {}

class FoodBankSchedule:
    def __init__(self):
        self.day         = ""
        self.isOpen      = True
        self.openingTime = ""
        self.closingTime = ""

class FoodBankLocation:
    def __init__(self):
        self.address = ""
        self.lat     = 0.0
        self.lng     = 0.0

class FoodBank:
    def __init__(self):
        self.name      = ""
        self.phoneNum  = ""
        self.schedules = []
        self.address   = ""
        self.postCode  = ""
        self.location  = FoodBankLocation()
        self.city      = ""
        self.link      = ""

    def toJSON(self):
        return json.dumps(self, default = lambda o: o.__dict__, sort_keys = True, indent = 0).replace("\n", "")

def _listToMap(keyFunction, values):
    return dict((keyFunction(v), v) for v in values)

def loadFoodBankData():
    if _ukFoodBanksList == []:
        #Intialise food bank data
        jsonText = requests.get(UK_FOOD_BANK_DATA_URL).text

        #We need to remove the last 2 and first 2 characters which are "?(" and ");"
        jsonText = jsonText[2 :   ]
        jsonText = jsonText[  : -2]

        jsonData = json.loads(jsonText)

        foodBanksNum = 0
        skippedFoodBanksNum = 0

        #Load groups of Food Banks
        for groupJson in jsonData:

            groupInformation = groupJson["foodbank_information"]

            #The value foodbank_centre in a group is either an array of objects or False (no idea why its not an empty array)
            if groupJson["foodbank_centre"] == False: 
                continue

            #Iterate over the food banks in the group
            for foodBankJson in groupJson["foodbank_centre"]:
                foodBanksNum += 1

                #If the name or post code of a center is not available we won't bother with it
                if "post_code" not in foodBankJson or "foodbank_name" not in foodBankJson:
                    #We count the ones we skip though
                    skippedFoodBanksNum += 1
                    continue

                #Create a food bank instance
                foodBank = FoodBank()

                #Extract the data and fill the struct
                try:
                    foodBank.name = foodBankJson["foodbank_name"]
                    foodBank.postCode = foodBankJson["post_code"]

                    if "permalink" in groupInformation:
                        foodBank.link = groupInformation["permalink"]
                    else:
                        foodBank.link = None

                    #Phone number might not be available
                    if "foodbank_telephone_number" in foodBankJson:
                        foodBank.phoneNum = foodBankJson["foodbank_telephone_number"]
                    elif "telephone_number" in groupInformation:
                        foodBank.phoneNum = groupInformation["telephone_number"]
                    else:
                        foodBank.phoneNum = None
                    
                    locationJson = foodBankJson["centre_geolocation"]
                    
                    #Centre address might not be available but we can get it from the centre_geolocation field then
                    if "centre_address" in foodBankJson:
                        foodBank.address = foodBankJson["centre_address"]
                    else:
                        foodBank.address = locationJson["address"]

                    foodBank.location.address = locationJson["address"]
                    foodBank.location.lat     = float(locationJson["lat"])
                    foodBank.location.lng     = float(locationJson["lng"])
                    
                    #The schedule can be haphazard so there can be multiple 
                    if "opening_time" in foodBankJson:
                        for scheduleJson in foodBankJson["opening_time"]:
                            schedule             = FoodBankSchedule()
                            schedule.day         = scheduleJson["day"]
                            schedule.isOpen      = scheduleJson["foodbank_status"] == "open"
                            schedule.openingTime = scheduleJson["opening_time"]
                            schedule.closingTime = scheduleJson["closing_time"]
                            foodBank.schedules.append(schedule)

                    _ukFoodBanksList.append(foodBank)
                except Exception as e:
                    #For error checking
                    print("\n\n\nError!\nException message:{}\nFood bank index: {}\nSkipped food banks num: {}\nJson: {}\n".format(str(e), foodBanksNum, skippedFoodBanksNum, foodBankJson)) 
                    exit()

        #Get city names
        postalCodes = list(map(lambda it: '"{}"'.format(it.postCode), _ukFoodBanksList))

        postalCodesBegin = 0
        postalCodesEnd   = 0
        
        while postalCodesEnd != len(postalCodes):
            postalCodesEnd = min(postalCodesBegin + 100, len(postalCodes))
            jsonPostArgs = "{{ \"postcodes\": [ {} ] }}".format(','.join(postalCodes[postalCodesBegin : postalCodesEnd]))

            response = requests.post("http://api.postcodes.io/postcodes", json = json.loads(jsonPostArgs))
            
            assert(response.ok)

            results = json.loads(response.text)["result"]

            for i in range(postalCodesBegin, postalCodesEnd):
                if results[i - postalCodesBegin]["result"] != None:
                    city = results[i - postalCodesBegin]["result"]["admin_district"]
                    _ukFoodBanksList[i].city = city
                    
                    if city not in _ukFoodBanksByCity:
                        _ukFoodBanksByCity[city] = []

                    _ukFoodBanksByCity[city].append(_ukFoodBanksList[i])

            postalCodesBegin = postalCodesEnd

        global _dataLoaded
        _dataLoaded = True
        #print("\n\nData extracted succesfully.\nNum of entries: {}\nTotal amount: {}\nSkipped food banks: {}".format(foodBanksNum - skippedFoodBanksNum, foodBanksNum, skippedFoodBanksNum))

def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def getFoodBanks():
    assert(_dataLoaded)
    return _ukFoodBanksList

def getCities():
    assert(_dataLoaded)
    return list(_ukFoodBanksByCity.keys())

def getFoodBanksByCity(city):
    assert(_dataLoaded)
    return _ukFoodBanksByCity[city]

def getSortedFoodBanksByLocation(lat, lng, foodBanks):
    assert(_dataLoaded)
    return sorted(foodBanks, key = lambda fb: distance((lat, lng), (fb.location.lat, fb.location.lng)))