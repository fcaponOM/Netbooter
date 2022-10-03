from .models import Image
from django.http import Http404, FileResponse
from rest_framework.views import APIView
from rest_framework import generics
from .serializers import ImageSerializer
import os

class ImageList(generics.ListCreateAPIView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer

class ImageDetail(APIView):
    queryset = Image.objects
    print("image requested")
    def get(self, request, version, format=None):
        image = self.queryset.filter(version=version)
        if image.exists():
            path = '/home/installnuc/Imageserver/media/' + str(image[0].image.name)
            if os.path.exists(path):
                response = FileResponse(open(path,'rb'))
                return response
        else:
            raise Http404
