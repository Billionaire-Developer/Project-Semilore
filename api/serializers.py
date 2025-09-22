from rest_framework import serializers
from core.models import Faculty, Department, Location, Item, Inspection, Transfer

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        read_only_fields = ('uid','uuid','qr_code_image','last_inspection_at','average_condition')
        fields = '__all__'

class InspectionSerializer(serializers.ModelSerializer):
    inspector = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Inspection
        fields = '__all__'
        read_only_fields = ('inspected_at','inspector')
