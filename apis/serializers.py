import base64
from rest_framework import serializers
from .models import User, FingerprintTemplate, Course, Enrollment, ClassSession, AttendanceLog, ClassSession, Enrollment, User, AttendanceScore

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
"""
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'

class ClassSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassSession
        fields = '__all__'
        read_only_fields = ['SessionDateTime', 'SessionEndTime']

class StartClassSessionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    course_code = serializers.CharField()

    def validate(self, data):
        from .models import User, Course, ClassSession

        user = User.objects.filter(UserID=data['user_id'], User_Role='Lecturer').first()
        if not user:
            raise serializers.ValidationError("Invalid lecturer ID or role.")

        course = Course.objects.filter(CourseCode=data['course_code']).first()
        if not course:
            raise serializers.ValidationError("Invalid course code.")

        # Check if this lecturer is teaching this course
        is_valid_class = ClassSession.objects.filter(Course=course, Lecturer=user).exists()
        if not is_valid_class:
            raise serializers.ValidationError("This lecturer is not assigned to this course.")

        data['lecturer'] = user
        data['course'] = course
        return data

class AttendanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = '__all__'

    def validate(self, data):
        session = data['ClassSession']
        student = data['Student']

        if not session.IsActive:
            raise serializers.ValidationError("Session is not active.")

        # Ensure student is enrolled
        enrolled = Enrollment.objects.filter(Student=student, Course=session.Course).exists()
        if not enrolled:
            raise serializers.ValidationError("Student is not enrolled for this course.")

        return data

class EndClassSessionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    session_id = serializers.IntegerField()

    def validate(self, data):
        from .models import ClassSession, User

        user = User.objects.filter(UserID=data['user_id'], User_Role='Lecturer').first()
        if not user:
            raise serializers.ValidationError("Invalid lecturer fingerprint.")

        session = ClassSession.objects.filter(ClassSessionID=data['session_id'], IsActive=True, Lecturer=user).first()
        if not session:
            raise serializers.ValidationError("No active session found for this lecturer.")

        data['session'] = session
        return data

class AttendanceScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceScore
        fields = '__all__'
"""