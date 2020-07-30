from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.core import serializers
from django.urls import reverse
import pymongo
from pymongo import MongoClient
from datetime import datetime
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import LineChart
from django.template.loader import render_to_string
import requests

locations = ["Andhra Pradesh","Arunachal Pradesh ","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
"Haryana","Himachal Pradesh","Jammu and Kashmir","Jharkhand","Karnataka","Kerala",
"Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha",
"Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand",
"West Bengal","Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli","Daman and Diu",
"Lakshadweep","Delhi","Puducherry"]

def connect():
    client = MongoClient('mongodb+srv://coderescue:sih2020@trycluster-rfees.mongodb.net/test?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE' , ssl = True)
    # client = MongoClient('mongodb+srv://user:user@sih-jhvxc.mongodb.net/test?retryWrites=true&w=majority')
    return client

def index(request , latitude='' , longitude=''):
    context = {}
    client = connect()
    print(latitude)
    print(longitude)
    if request.session.has_key('locationIndex'):
        context['locationIndex'] = request.session['locationIndex']
        print(context['locationIndex'])
        context['locationName'] = request.session['locationName']

    location_names = []
    for location in locations :
        location_names.append(location)
    context['location_names'] = location_names

    db = client.main.disaster
    print("HELLO Main Dashboard")

    info = db.find({})
    temp_data = list(info)

    data = {}
    for disaster in temp_data:
        if "name" in disaster:
            data[disaster["name"]] = disaster

    context['data'] = data
    if latitude != '' and longitude != '' and request.session['locationName'] != '':
        dataSafeHouses = list(client.main.safeHouses.find({}))
        listSafeHousesInUserLocation = dataSafeHouses[0][request.session['locationName']]
        print(listSafeHousesInUserLocation)
        context['listSafeHouses'] = listSafeHousesInUserLocation
        URL_BING_API = "https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix?origins="
        URL_BING_API += latitude + "," + longitude + "&destinations="
        for obj in listSafeHousesInUserLocation:
            URL_BING_API += obj["latitude"] + "," + obj["longitude"] + ";"
        URL_BING_API = URL_BING_API[:-1]

        URL_BING_API += "&travelMode=driving&key=AvINDoc3SxM9iNoyy6FaioCFuKWu9qowxEk1U1EeY4oEut8puIbYP0W9gjZWeO7F"
        # print(URL_BING_API)
        r = requests.get(url = URL_BING_API)
        r = r.json()
        min = 100000
        destinationIndex = -1
        if len(r['resourceSets']) > 0:
            for safeHouseDistance in  r['resourceSets'][0]['resources'][0]['results']:
                print(safeHouseDistance['travelDistance'])
                if float(safeHouseDistance['travelDistance']) < min:
                    min = float(safeHouseDistance['travelDistance'])
                    destinationIndex = safeHouseDistance['destinationIndex']
            context['nearest_safe_house'] = {
                'latitude': listSafeHousesInUserLocation[destinationIndex]['latitude'] ,
                'longitude': listSafeHousesInUserLocation[destinationIndex]['longitude']
            }
            print(context['nearest_safe_house'])
    return render(request , 'main/index.html' , context)

def getUserLocation(request):
    if request.method == 'POST':
        locName = request.POST.get('location')
        # location = location.tolower()
        if locName in locations:
            request.session['locationName'] = locName
            request.session['locationIndex'] = locations.index(locName)
    return HttpResponseRedirect(reverse('main:index'))

def notifications(request, loc_no):
    client = connect()
    db = client.main.notification
    print("connected")
    data = db.find().sort("date", pymongo.DESCENDING)
    allnotfs = list(data)
    if 0 <= loc_no < len(locations):
        notfLocation = locations[loc_no]
    else:
        HttpResponseRedirect(reverse('main:index'))
    ########################
    # some error chances bcoz i m considering last time of
    # or may be not
    notfs = []
    for notf in allnotfs:
        if 'location' in notf and notfLocation in notf['location']:
            notf['date'] = notf['date'].strftime('%d/%m/%Y %H:%M:%S')
            # date_time_obj = datetime. strptime(date_time_str, '%d/%m/%y %H:%M:%S')
            notfs.append(notf)

    if notfs != []:
        request.session['lastNotification'] = notfs[0]['date']
    context = {
        'notifications' : notfs,
        'notfLocIndex' : loc_no
    }
    return render(request , 'main/notification.html' , context)

def get_new_notifications(request, loc_no):
    if request.is_ajax and request.method == "GET":
        lastNotif = request.session['lastNotification']
        if(lastNotif == ''):
            client = connect()
            db = client.main.notification
            data = db.find().sort("date", pymongo.DESCENDING)
            allnotfs = list(data)
            notfs = []
            for notf in allnotfs:
                if 'location' in notf and notfLocation in notf['location']:
                    notf['date'] = notf['date'].strftime('%d/%m/%Y %H:%M:%S')
                    notfs.append(notf)
            if notfs != []:
                request.session['lastNotification'] = notfs[0]['date']

        locName = locations[loc_no]
        client = connect()
        db = client.main.notification
        print("Queried new notifications")
        data = db.find().sort("date", pymongo.DESCENDING)
        allnotfs = list(data)
        # print(allnotfs)
        # print(lastNotif)
        newnotfs = []
        for notf in allnotfs:
            if 'location' in notf and locName in notf['location']:
                notf['date'] = notf['date'].strftime('%d/%m/%Y %H:%M:%S')
                if notf['date'] != lastNotif:
                    ########### since ObjectId is not json serializable
                    notf['_id'] = 0
                    newnotfs.append(notf)
                else:
                    break
        if newnotfs != []:
            request.session['lastNotification'] = newnotfs[0]['date']
            newnotfs.reverse()
        # so that last notification is picked first to add
        # print(newnotfs)
        return JsonResponse({"new_notifications": newnotfs}, status=200)
    else:
        HttpResponseRedirect(reverse('main:index'))
        ############ change this

#mayank code starts here... kindly accept my part of code if merge conflict arises

def headquarters_dashboard(request):
    client = connect()
    success = 0
    dt_string = datetime.now()

    if( request.method == 'POST' ):
        if( request.POST['is_disaster'] == "disaster_wise" ):

            id = request.POST['all_disasters']

            db = client.main.disaster
            disaster = list(db.find({ "id" : id }))[0]

            data = {
                "is_disaster" :  1,
                "name" : disaster["name"],
                "location" : disaster["location"],
                "directed_to" : "people",
                "directed_from" : "headquarters",
                "message" : request.POST['message'],
                "date" : dt_string
            }
            db = client.main.notification
            db.insert_one(data)
            success = 1

        if( request.POST['is_disaster'] == "location_wise" ):
            data = {
                "is_disaster" :  0,
                "location" : request.POST['location_names'],
                "directed_to" : "people",
                "directed_from" : "headquarters",
                "message" : request.POST['message'],
                "date" : dt_string
            }
            db = client.main.notification
            db.insert_one(data)
            success = 1

    db = client.main.disaster
    print("HELLO")
    info = db.find({})
    data = list(info)

    all_disasters = []
    location_names = []
    rescue_teams_names = {}
    active_disasters = []
    for data1 in data:
        all_disasters.append({
            "name" : data1["name"],
            "id" : data1["id"]
        })
        if data1['isactive'] == 1:
            active_disasters.append(data1)

    for data1 in data :
        rescue_teams_names[data1["name"]] = data1["rescue_teams_usernames"]

    for location in locations :
        location_names.append(location)

    print(all_disasters)
    context = {
        "all_disasters" : all_disasters ,
        "location_names": location_names ,
        "success" : success ,
        "rescue_teams_names" : rescue_teams_names,
        "active_disasters" : active_disasters
    }

    return render( request , 'headquarters/dashboard.html' , context )

def rescue_team_dashboard(request):
    return render( request , 'rescue_team/dashboard.html' )

def all_disasters(request):
    client = connect()
    db = client.main.disaster
    print("Connected")
    info = db.find({})
    data = list(info)
    data.reverse()

    disasters_data = []
    for record in data:
        temp = {}
        temp['id'] = record['id']
        temp['name'] = record['name']
        temp['location'] = record['location']
        temp['isactive'] = record['isactive']
        disasters_data.append(temp)

    context = {
        'disasters_data' : disasters_data
    }
    return render(request, 'headquarters/disasters.html', context)

def change_active_status(request):
    if request.is_ajax and request.method == "POST":
        data = request.POST
        status = int(data['status'])
        id = data['id']
        print(id + " " + str(status))
        client = connect()
        db = client.main.disaster
        print("Connected")
        db.update_one(
        { "id" : id },
        { "$set": { "isactive" : status } }
        )
        return JsonResponse({}, status=200)
    return JsonResponse({"error": "some error"}, status=400)

def add_disaster(request):
    if request.method == "GET":
        return render(request, 'headquarters/add_disaster.html')

    elif request.method == "POST":
        print("From received")
        client = connect()
        db = client.main.disaster
        id = db.count() + 1
        location = []
        for loc in request.POST.getlist('location'):
            if loc != '':
                location.append(loc)

        data = {
            'id' : "unique_id_" + str(id),
            'name' : request.POST['name'],
            'isactive' : int(request.POST['activeStatus']),
            'scale' : int(request.POST['scale']),
            'coordinates' : {
                'latitude' : request.POST['latitude'],
                'longitude' : request.POST['longitude'],
                'radius' : request.POST['radius']
            },
            'rescue_teams_usernames' : [],
            'statistics' : {
                'total' : {
                    'affected' : 0,
                    'deaths' : 0
                },
                'day_0' : {
                    'affected' : 0,
                    'deaths' : 0
                }
            },
            'location' : location,
            'starting_date' : str(datetime.now().date())
        }
        print(data)
        db.insert_one(data)
        return HttpResponseRedirect(reverse('main:all_disasters'))

def update_statistics(request, disaster_id):
    if request.method == "GET":
        client = connect()
        db = client.main.disaster
        disaster = list(db.find({ "id" : disaster_id }))[0]
        stats = {}
        if 'statistics' in disaster:
            stats = disaster['statistics']
        total_stats = {
            'affected' : 0,
            'deaths' : 0
        }

        daily_stats = []
        for key, value in stats.items():
            if key == 'total':
                total_stats = stats['total']
            else:
                daily_stats.append(value)

        if not daily_stats:
            daily_stats = [
                {
                    'affected' : 0,
                    'deaths' : 0
                }
            ]

        print(daily_stats)
        context = {
            "disaster_id" : disaster_id,
            "disaster_name" : disaster['name'],
            "location" : disaster['location'],
            "total_stats" : total_stats,
            "daily_stats" : daily_stats
        }
        return render(request, 'headquarters/update_statistics.html', context)

    elif request.method == "POST":
        affected_stats = request.POST.getlist('affected_stats')
        deaths_stats = request.POST.getlist('deaths_stats')

        total_stats = {
            'affected' : 0,
            'deaths' : 0
        }

        for stat in affected_stats:
            total_stats['affected'] += int(stat)
        for stat in deaths_stats:
            total_stats['deaths'] += int(stat)

        stats = {
            "total" : total_stats
        }

        for x in range(len(affected_stats)):
            day_no = "day_" + str(x)
            day_stats = {
                'affected' : int(affected_stats[x]),
                'deaths' : int(deaths_stats[x])
            }
            stats[day_no] = day_stats

        print(stats)
        client = connect()
        db = client.main.disaster
        db.update_one(
            { "id" : disaster_id },
            { "$set": { "statistics" : stats } }
        )

        return HttpResponseRedirect(reverse('main:headquarters_dashboard'))
