import overpy as overpy
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, Polygon
from knox.serializers import UserSerializer
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from django.http import JsonResponse
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from knox.models import AuthToken, User
from rest_framework.utils import json
from . import serializers
from .models import Profile
from .serializers import ProfileSerializer, RegisterSerializer
from django.contrib.auth import login
from rest_framework import permissions
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView


# Register API
class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })


class LoginAPI(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginAPI, self).post(request, format=None)


# @api_view(['POST'])
# def update_database(request):
#     try:
#         my_profile = request.user
#
#     except Profile.DoesNotExist:
#         return Response(status=status.HTTP_404_NOT_FOUND)
#
#     if request.method == 'POST':
#         data = request.data
#         serializer = ProfileSerializer(instance=my_profile, data=data)
#         if serializer.is_valid():
#             my_location = request.data['last_location']
#             my_coords = [float(coord) for coord in my_location.split(", ")]
#             my_profile.last_location = Point(my_coords)
#             my_profile.save()
#             serializer.save()
#
#             return Response(data=data)
#     return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def update_database(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        data = request.data
        serializer = ProfileSerializer(instance=profile, data=data)
        if serializer.is_valid():
            my_location = request.data['last_location']
            my_coords = [float(coord) for coord in my_location.split(", ")]
            profile.last_location = Point(my_coords)
            profile.save()

            return Response(data=data)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def check_auth(request):

    if request.method == 'POST':
        data = request.data

        return Response(data=data)
    return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
# @api_view(['POST'])
# def update_database(request):
#     """
#     Updates the database with user location
#     :param request:
#     :return:
#     """
#     my_location = request.POST.get("last_location", None)
#     if not my_location:
#         return JsonResponse({"message": "No location found."}, status=400)
#
#     try:
#         my_coords = [float(coord) for coord in my_location.split(", ")]
#         my_profile = Profile.objects.get(user=request.user)
#         my_profile.last_location = Point(my_coords)
#         my_profile.save()
#
#         message = f"Updated {request.user.username} with {f'POINT({my_location})'}"
#
#         return JsonResponse({"message": message}, status=200)
#     except:
#         return JsonResponse({"message": "No profile found."}, status=400)

class QueryOverpass(views.APIView):
    """
    Query Overpass (OpenStreetMap) API

    This class-based view accepts a request containing a free-form query and the bounding box of the visible map
    viewport. It assumes that the request has a valid user (i.e. is authenticated). The associated serializer ensures
    that the data iss in a correct form before being handled by this view.

    The view uses a Python library called OverPy (Python Overpass API) -
    https://python-overpy.readthedocs.io/en/latest/index.html

    The view process a POST request only.
    """
    permission_classes = [IsAuthenticated, ]
    serializer_class = serializers.OverpassSerializer

    def post(self, request, *args, **kwargs):
        try:
            # Create overpass API object
            api = overpy.Overpass()

            # Overpass has its own somewhat arcane query language. Fortunately we can make some assumptions and creat
            # a shell which can be 'filled in'. Thus we make a beginning, middle and end of the query. The middle part
            # will be modified to get the details of our query.
            api_query_top = \
                """
                [out:json][timeout:25];
                (
                """

            api_query_bottom = \
                """
                );
                out body;
                >;
                out skel qt;
                """

            api_middle = ""

            # Run our incoming data through the serializer to validate and pre-process it.
            my_serializer = serializers.OverpassSerializer(data=request.data)
            if my_serializer.is_valid():
                bbox = my_serializer.validated_data["bbox"]
                for item in my_serializer.validated_data["query"]:
                    if item == "*":
                        api_middle += f'node["amenity"]{tuple(bbox)};\nway["amenity"]{tuple(bbox)};\nrelation["amenity"]{tuple(bbox)};'
                        break
                    else:
                        api_middle += f'node["amenity"="{item}"]{tuple(bbox)};\nway["amenity"="{item}"]{tuple(bbox)};\nrelation["amenity"="{item}"]{tuple(bbox)};'

                # OpenStreetMap stores its data as 'Nodes' (Point objects), 'Ways' (Linestring or Polygon objects) or
                # 'Relations' (Used to define logical or geographic relationships between different objects,
                # for example a lake and its island, or several roads for a bus route. In this qquery type I'm focusing
                # on objects tagged as 'amenity' in the database such as cafes, bars, pubs, restaurants etc. You could
                # easily modify this for other types. A result which is a node will have a single point whereas a result
                # which is a way could be a polygon (e.g. the footprint of a pub). For this we need a single point so we
                # compute the centroid of the polygon and use it.
                api_query = f"{api_query_top}\n{api_middle}\n{api_query_bottom}\n"
                result = api.query(api_query)

                # The result should be returned as GeoJSON. A Python dictionarry with a list of 'features' can be easily
                # serialized as GeoJSON
                geojson_result = {
                    "type": "FeatureCollection",
                    "features": [],
                }

                # This next section iterates thriugh each 'way' and gets its centroid. It also keeps a record of the
                # points in the so that they are not duplicated when we process the 'nodes'
                nodes_in_way = []

                for way in result.ways:
                    geojson_feature = None
                    geojson_feature = {
                        "type": "Feature",
                        "id": "",
                        "geometry": "",
                        "properties": {}
                    }
                    poly = []
                    for node in way.nodes:
                        # Record the nodes and make the polygon
                        nodes_in_way.append(node.id)
                        poly.append([float(node.lon), float(node.lat)])
                    # Make a poly out of the nodes in way.
                    # Some ways are badly made so, if we can't succeed just ignore the way and move on.
                    try:
                        poly = Polygon(poly)
                    except:
                        continue
                    geojson_feature["id"] = f"way_{way.id}"
                    geojson_feature["geometry"] = json.loads(poly.centroid.geojson)
                    geojson_feature["properties"] = {}
                    for k, v in way.tags.items():
                        geojson_feature["properties"][k] = v

                    geojson_result["features"].append(geojson_feature)

                # Process results that are 'nodes'
                for node in result.nodes:
                    # Ignore nodes which are also in a 'way' as we will have already processed the 'way'.
                    if node.id in nodes_in_way:
                        continue
                    geojson_feature = None
                    geojson_feature = {
                        "type": "Feature",
                        "id": "",
                        "geometry": "",
                        "properties": {}
                    }
                    point = Point([float(node.lon), float(node.lat)])
                    geojson_feature["id"] = f"node_{node.id}"
                    geojson_feature["geometry"] = json.loads(point.geojson)
                    geojson_feature["properties"] = {}
                    for k, v in node.tags.items():
                        geojson_feature["properties"][k] = v

                    geojson_result["features"].append(geojson_feature)

                # Return the complete GeoJSON structure.
                return Response(geojson_result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": f"Error: {e}."}, status=status.HTTP_400_BAD_REQUEST)
